#!/usr/bin/env python3
"""
Test correct Microsoft Graph API calls for OneDrive access
"""

import asyncio
import os
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient

load_dotenv()

async def test_working_api():
    """Test with correct API syntax"""
    print("🔍 Testing Working Microsoft Graph API...")
    
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
        # Get users first
        users_response = await graph_client.users.get()
        users = users_response.value if users_response else []
        print(f"✅ Found {len(users)} users")
        
        if users:
            user = users[0]
            user_id = user.id
            print(f"📋 Testing with: {user.display_name}")
            
            # Try to get user's OneDrive drive
            try:
                drive_response = await graph_client.users.by_user_id(user_id).drive.get()
                print(f"✅ Drive found: {drive_response.name}")
                drive_id = drive_response.id
                
                # Method 1: Access drive items via drive ID
                try:
                    items_response = await graph_client.drives.by_drive_id(drive_id).root.children.get()
                    items = items_response.value if items_response else []
                    print(f"✅ SUCCESS! Found {len(items)} items in OneDrive")
                    
                    if items:
                        print("📁 OneDrive contents:")
                        for item in items[:5]:
                            item_type = "📁" if hasattr(item, 'folder') and item.folder else "📄"
                            print(f"   {item_type} {item.name}")
                            
                        # Test specific folder access
                        for item in items:
                            if item.name.lower() == 'university' and hasattr(item, 'folder') and item.folder:
                                print(f"\n🎓 Found University folder! Testing access...")
                                try:
                                    uni_response = await graph_client.drives.by_drive_id(drive_id).items.by_drive_item_id(item.id).children.get()
                                    uni_items = uni_response.value if uni_response else []
                                    print(f"✅ University folder contains {len(uni_items)} items")
                                    
                                    if uni_items:
                                        print("📚 University folder contents:")
                                        for uni_item in uni_items[:3]:
                                            uni_type = "📁" if hasattr(uni_item, 'folder') and uni_item.folder else "📄"
                                            print(f"   {uni_type} {uni_item.name}")
                                            
                                except Exception as e:
                                    print(f"⚠️ University folder access failed: {e}")
                                break
                    
                    print(f"\n✅ OneDrive API is working correctly!")
                    print(f"🔑 Drive ID: {drive_id}")
                    print(f"👤 User ID: {user_id}")
                    return True
                    
                except Exception as e:
                    print(f"❌ Error accessing drive items: {e}")
                    return False
                    
            except Exception as e:
                print(f"❌ Error getting user drive: {e}")
                return False
                
    except Exception as e:
        print(f"❌ API Error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_working_api())
