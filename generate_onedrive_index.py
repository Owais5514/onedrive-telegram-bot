import os
import json
import asyncio
import aiohttp
from dotenv import load_dotenv
from azure.identity.aio import ClientSecretCredential # Use async version
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
DEFAULT_BASE_FOLDER = "University"
DEFAULT_RESTRICTED_MODE = True
OUTPUT_DIR = "docs"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "onedrive_index.json")
PREFERRED_USER_DISPLAY_NAME = "Owais Ahmed"

# --- Environment Variable Loading ---
def load_env_vars():
    """Loads environment variables from .env file and checks for required ones."""
    load_dotenv()
    required_vars = ['AZURE_CLIENT_ID', 'AZURE_CLIENT_SECRET', 'AZURE_TENANT_ID']
    env_vars = {var: os.getenv(var) for var in required_vars}
    missing_vars = [var for var, value in env_vars.items() if value is None]
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")
    logging.info("Environment variables loaded successfully.")
    return env_vars

# --- Authentication ---
class MSGraphAuth:
    """Handles authentication with Microsoft Graph API."""
    def __init__(self, client_id, client_secret, tenant_id):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.credentials = ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        self._token = None # Using _token to indicate it's internally managed

    async def get_access_token(self):
        """Retrieves an access token for Microsoft Graph API."""
        if self._token: # Basic caching, token expiry is handled by the library
            return self._token.token
        try:
            logging.info("Attempting to acquire new access token.")
            self._token = await self.credentials.get_token('https://graph.microsoft.com/.default')
            logging.info("Access token acquired successfully.")
            return self._token.token
        except Exception as e:
            logging.error(f"Error acquiring access token: {e}")
            raise

    async def get_headers(self):
        """Returns headers required for Graph API requests."""
        token = await self.get_access_token()
        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

# --- User Fetching ---
async def fetch_user_id(auth_handler: MSGraphAuth, session: aiohttp.ClientSession) -> str:
    """Fetches users and returns the ID of the preferred user or the first user found."""
    headers = await auth_handler.get_headers()
    users_url = "https://graph.microsoft.com/v1.0/users?$select=id,displayName"
    try:
        async with session.get(users_url, headers=headers) as response:
            response.raise_for_status()
            users_data = await response.json()
            users = users_data.get('value', [])
            if not users:
                raise ValueError("No users found in the organization.")

            # Try to find the preferred user
            for user in users:
                if PREFERRED_USER_DISPLAY_NAME in user.get('displayName', ''):
                    logging.info(f"Found preferred user: {user['displayName']} with ID: {user['id']}")
                    return user['id']
            
            # Fallback to the first user if preferred user not found
            default_user = users[0]
            logging.info(f"Preferred user not found. Using first user: {default_user['displayName']} with ID: {default_user['id']}")
            return default_user['id']
    except aiohttp.ClientResponseError as e:
        logging.error(f"Error fetching users: {e.status} - {e.message}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred while fetching users: {e}")
        raise

# --- OneDrive Traversal ---
async def get_drive_items_recursive(user_id: str, auth_handler: MSGraphAuth, session: aiohttp.ClientSession,
                                    item_path: str = "/", base_folder_name: str = DEFAULT_BASE_FOLDER,
                                    restricted_mode: bool = DEFAULT_RESTRICTED_MODE, is_initial_call: bool = True):
    """
    Recursively fetches files and folders from OneDrive.
    """
    items = []
    headers = await auth_handler.get_headers()
    
    # Construct the initial request URL
    if is_initial_call and restricted_mode and base_folder_name:
        # Find the base folder ID first
        base_folder_search_url = f"https://graph.microsoft.com/v1.0/users/{user_id}/drive/root/search(q='{base_folder_name}')"
        logging.info(f"Searching for base folder: '{base_folder_name}'")
        try:
            async with session.get(base_folder_search_url, headers=headers) as response:
                response.raise_for_status()
                search_results = await response.json()
                
                found_base_folder = None
                for item in search_results.get("value", []):
                    if item.get("name") == base_folder_name and item.get("folder"):
                        found_base_folder = item
                        break
                
                if not found_base_folder:
                    logging.error(f"Base folder '{base_folder_name}' not found.")
                    return [] # Or raise an error
                
                base_folder_id = found_base_folder["id"]
                logging.info(f"Found base folder '{base_folder_name}' with ID: {base_folder_id}")
                # Now list children of this base folder
                request_url = f"https://graph.microsoft.com/v1.0/users/{user_id}/drive/items/{base_folder_id}/children?$select=id,name,webUrl,folder,file"
                # After the initial call, item_path will be relative to the base_folder_id if in restricted_mode
                # For subsequent calls, item_path will be the ID of the parent folder.
            
        except aiohttp.ClientResponseError as e:
            logging.error(f"API error searching for base folder '{base_folder_name}': {e.status} - {e.message}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error searching for base folder '{base_folder_name}': {e}")
            return []

    elif item_path == "/": # Root of the drive (used if not restricted or base_folder_name is empty)
        request_url = f"https://graph.microsoft.com/v1.0/users/{user_id}/drive/root/children?$select=id,name,webUrl,folder,file"
        logging.info("Fetching items from OneDrive root.")
    else: # Path is an item ID for subsequent recursive calls
        request_url = f"https://graph.microsoft.com/v1.0/users/{user_id}/drive/items/{item_path}/children?$select=id,name,webUrl,folder,file"
        logging.info(f"Fetching items from folder ID: {item_path}")

    try:
        async with session.get(request_url, headers=headers) as response:
            response.raise_for_status()
            drive_data = await response.json()
            
            for item in drive_data.get('value', []):
                item_info = {
                    "name": item.get("name"),
                    "id": item.get("id"),
                    "webUrl": item.get("webUrl")
                }
                if item.get("folder"):
                    item_info["type"] = "folder"
                    logging.info(f"Processing folder: {item_info['name']}")
                    # Recursively fetch children. The item_id is the new 'item_path' for the next call.
                    # For recursive calls, is_initial_call is False, restricted_mode and base_folder_name are passed along
                    # but the core logic for path construction inside this function will use item_id.
                    item_info["children"] = await get_drive_items_recursive(
                        user_id, auth_handler, session, 
                        item_path=item["id"], # Pass current folder's ID for recursion
                        base_folder_name=base_folder_name, # Keep passing for context if needed, though not directly used in URL construction past initial
                        restricted_mode=restricted_mode, 
                        is_initial_call=False # This is now a recursive call
                    )
                else: # It's a file
                    item_info["type"] = "file"
                    logging.info(f"Processing file: {item_info['name']}")
                
                items.append(item_info)
        
        # Handle pagination if present
        next_link = drive_data.get("@odata.nextLink")
        while next_link:
            logging.info(f"Fetching next page of items from: {next_link}")
            async with session.get(next_link, headers=headers) as response_page:
                response_page.raise_for_status()
                drive_data_page = await response_page.json()
                for item_page in drive_data_page.get('value', []):
                    item_info_page = {
                        "name": item_page.get("name"),
                        "id": item_page.get("id"),
                        "webUrl": item_page.get("webUrl")
                    }
                    if item_page.get("folder"):
                        item_info_page["type"] = "folder"
                        logging.info(f"Processing folder (paginated): {item_info_page['name']}")
                        item_info_page["children"] = await get_drive_items_recursive(
                            user_id, auth_handler, session, 
                            item_path=item_page["id"], 
                            base_folder_name=base_folder_name,
                            restricted_mode=restricted_mode,
                            is_initial_call=False
                        )
                    else:
                        item_info_page["type"] = "file"
                        logging.info(f"Processing file (paginated): {item_info_page['name']}")
                    items.append(item_info_page)
                next_link = drive_data_page.get("@odata.nextLink")

    except aiohttp.ClientResponseError as e:
        logging.error(f"API error fetching drive items from path '{item_path}': {e.status} - {e.message}")
        # Depending on desired behavior, you might want to return partial results or raise
    except Exception as e:
        logging.error(f"An unexpected error occurred while fetching drive items from path '{item_path}': {e}")

    return items

# --- Main Logic ---
async def main():
    """Main function to orchestrate OneDrive indexing."""
    logging.info("Starting OneDrive indexing process...")
    try:
        env_vars = load_env_vars()
        auth_handler = MSGraphAuth(
            client_id=env_vars['AZURE_CLIENT_ID'],
            client_secret=env_vars['AZURE_CLIENT_SECRET'],
            tenant_id=env_vars['AZURE_TENANT_ID']
        )

        async with aiohttp.ClientSession() as session:
            default_user_id = await fetch_user_id(auth_handler, session)
            
            # Get configuration for traversal
            base_folder_to_traverse = os.getenv("ONEDRIVE_BASE_FOLDER", DEFAULT_BASE_FOLDER)
            is_restricted_mode = os.getenv("ONEDRIVE_RESTRICTED_MODE", str(DEFAULT_RESTRICTED_MODE)).lower() == 'true'

            logging.info(f"Starting OneDrive traversal. User ID: {default_user_id}, Base Folder: '{base_folder_to_traverse}', Restricted Mode: {is_restricted_mode}")
            
            # The initial call to get_drive_items_recursive
            # If restricted_mode is True, it will find and start from base_folder_to_traverse.
            # If restricted_mode is False, it will start from the drive root (item_path="/").
            # The `item_path` for the initial call is effectively managed by `is_initial_call=True` logic.
            onedrive_structure = await get_drive_items_recursive(
                user_id=default_user_id,
                auth_handler=auth_handler,
                session=session,
                item_path="/", # This is a placeholder for the initial call, logic inside handles base_folder
                base_folder_name=base_folder_to_traverse if is_restricted_mode else "",
                restricted_mode=is_restricted_mode,
                is_initial_call=True
            )

            if not os.path.exists(OUTPUT_DIR):
                os.makedirs(OUTPUT_DIR)
                logging.info(f"Created output directory: {OUTPUT_DIR}")

            with open(OUTPUT_FILE, 'w') as f:
                json.dump(onedrive_structure, f, indent=2)
            
            logging.info(f"OneDrive index successfully generated at: {OUTPUT_FILE}")
            print(f"Success! OneDrive index generated at {OUTPUT_FILE}")

    except EnvironmentError as e:
        logging.error(f"Configuration error: {e}")
        print(f"Error: {e}. Please check your .env file or environment variables.")
    except ValueError as e:
        logging.error(f"Data error: {e}")
        print(f"Error: {e}.")
    except aiohttp.ClientResponseError as e:
        logging.error(f"Microsoft Graph API Error: Status {e.status}, Message: {e.message}")
        print(f"API Error: {e.message}. Check logs for details.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        print(f"An unexpected error occurred: {e}. Check logs for details.")

if __name__ == "__main__":
    asyncio.run(main())
