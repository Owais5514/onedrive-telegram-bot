#!/usr/bin/env python3
"""
Test OneDrive API access with the working authentication
"""

import asyncio
import os
import aiohttp
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential

load_dotenv()

async def test_onedrive_access():
    """Test direct OneDrive API access"""
    
    # Get credentials
    client_id = os.getenv('AZURE_CLIENT_ID')
    client_secret = os.getenv('AZURE_CLIENT_SECRET')
    tenant_id = os.getenv('AZURE_TENANT_ID')
    
    print("🔧 Testing OneDrive API access...")
    
    try:
        # Authenticate
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
        
        # Get access token
        token = credential.get_token('https://graph.microsoft.com/.default')
        access_token = token.token
        
        print("✅ Authentication successful!")
        
        # Get users
        async with aiohttp.ClientSession() as session:
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Test 1: Get users
            async with session.get('https://graph.microsoft.com/v1.0/users', headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    users = data.get('value', [])
                    print(f"✅ Found {len(users)} users")
                    
                    if users:
                        # Try to find Owais Ahmed as default user
                        owais_user = None
                        for user in users:
                            if 'owais ahmed' in user['displayName'].lower():
                                owais_user = user
                                break
                        
                        if owais_user:
                            default_user = owais_user
                            print(f"👤 Default user: {default_user['displayName']} (Found Owais Ahmed)")
                        else:
                            default_user = users[0]
                            print(f"👤 Default user: {default_user['displayName']} (Owais Ahmed not found, using first user)")
                            
                        user_id = default_user['id']
                        
                        # Test 2: Get OneDrive root
                        print("\n🔍 Testing OneDrive access...")
                        onedrive_url = f'https://graph.microsoft.com/v1.0/users/{user_id}/drive/root/children'
                        
                        async with session.get(onedrive_url, headers=headers) as onedrive_response:
                            if onedrive_response.status == 200:
                                onedrive_data = await onedrive_response.json()
                                items = onedrive_data.get('value', [])
                                print(f"✅ Found {len(items)} items in OneDrive root")
                                
                                for item in items[:5]:  # Show first 5 items
                                    item_type = "📁" if 'folder' in item else "📄"
                                    print(f"  {item_type} {item['name']}")
                                    
                                # Test 3: Try accessing University folder if it exists
                                university_items = [item for item in items if item['name'].lower() == 'university']
                                if university_items:
                                    print("\n🎓 Testing University folder access...")
                                    uni_url = f'https://graph.microsoft.com/v1.0/users/{user_id}/drive/root:/University:/children'
                                    
                                    async with session.get(uni_url, headers=headers) as uni_response:
                                        if uni_response.status == 200:
                                            uni_data = await uni_response.json()
                                            uni_items = uni_data.get('value', [])
                                            print(f"✅ Found {len(uni_items)} items in University folder")
                                            
                                            for item in uni_items[:5]:
                                                item_type = "📁" if 'folder' in item else "📄"
                                                print(f"  {item_type} {item['name']}")
                                        else:
                                            print(f"❌ University folder access failed: {uni_response.status}")
                                            
                            else:
                                print(f"❌ OneDrive access failed: {onedrive_response.status}")
                                error_text = await onedrive_response.text()
                                print(f"Error: {error_text}")
                else:
                    print(f"❌ Users access failed: {response.status}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    asyncio.run(test_onedrive_access())
