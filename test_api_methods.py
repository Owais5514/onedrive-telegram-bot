#!/usr/bin/env python3
"""
OneDrive API test with corrected syntax for latest msgraph-sdk
"""

import asyncio
import os
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient

load_dotenv()

async def test_corrected_onedrive_api():
    """Test OneDrive with corrected API syntax"""
    print("🔍 Testing OneDrive with Corrected API...")
    
    # Initialize Graph client
    credential = ClientSecretCredential(
        tenant_id=os.getenv('AZURE_TENANT_ID'),
        client_id=os.getenv('AZURE_CLIENT_ID'),
        client_secret=os.getenv('AZURE_CLIENT_SECRET')
    )
    
    graph_client = GraphServiceClient(
        credentials=credential,
        scopes=['https://graph.microsoft.com/.default']
    )
    
    try:
        # Get users
        users = await graph_client.users.get()
        print(f"✅ Found {len(users.value)} users")
        
        if users.value:
            first_user = users.value[0]
            user_id = first_user.id
            print(f"📋 Testing with user: {first_user.display_name} ({user_id})")
            
            # Method 1: Try accessing drive via users endpoint
            try:
                user_drive = await graph_client.users.by_user_id(user_id).drive.get()
                print(f"✅ User drive accessible: {user_drive.name}")
                
                # Try to get drive root children
                try:
                    drive_items = await graph_client.users.by_user_id(user_id).drive.root.children.get()
                    print(f"✅ SUCCESS: Found {len(drive_items.value) if drive_items.value else 0} items in user's OneDrive")
                    
                    if drive_items.value:
                        print("📁 User's OneDrive contents:")
                        for item in drive_items.value[:5]:
                            item_type = "📁" if item.folder else "📄"
                            print(f"   {item_type} {item.name}")
                        return True
                        
                except Exception as e:
                    print(f"❌ Error accessing user drive contents: {e}")
                    
            except Exception as e:
                print(f"⚠️ User drive access failed: {e}")
            
            # Method 2: Try accessing via drives endpoint
            try:
                all_drives = await graph_client.drives.get()
                print(f"✅ Found {len(all_drives.value) if all_drives.value else 0} total drives")
                
                if all_drives.value:
                    for drive in all_drives.value:
                        print(f"📁 Drive: {drive.name} (Type: {drive.drive_type})")
                        
                        # Try to access this drive's contents
                        try:
                            drive_contents = await graph_client.drives.by_drive_id(drive.id).root.children.get()
                            item_count = len(drive_contents.value) if drive_contents.value else 0
                            print(f"   ✅ Contains {item_count} items")
                            
                            if drive_contents.value and item_count > 0:
                                print(f"   📄 Sample items in {drive.name}:")
                                for item in drive_contents.value[:3]:
                                    item_type = "📁" if item.folder else "📄"
                                    print(f"      {item_type} {item.name}")
                                return True
                                
                        except Exception as e:
                            print(f"   ❌ Cannot access drive contents: {e}")
                            
            except Exception as e:
                print(f"❌ Error accessing drives: {e}")
            
            # Method 3: Try sites endpoint
            try:
                sites = await graph_client.sites.get()
                print(f"✅ Found {len(sites.value) if sites.value else 0} sites")
                
                if sites.value:
                    for site in sites.value[:2]:  # Check first 2 sites
                        try:
                            site_drive = await graph_client.sites.by_site_id(site.id).drive.get()
                            print(f"📁 Site '{site.display_name}' has drive: {site_drive.name}")
                            
                            site_items = await graph_client.sites.by_site_id(site.id).drive.root.children.get()
                            print(f"   ✅ Contains {len(site_items.value) if site_items.value else 0} items")
                            
                            if site_items.value:
                                return True
                                
                        except Exception as e:
                            print(f"   ⚠️ Site drive access failed: {e}")
                            
            except Exception as e:
                print(f"❌ Error accessing sites: {e}")
                
        print("❌ Could not access any OneDrive content")
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_corrected_onedrive_api())
