#!/usr/bin/env python3
"""
Quick OneDrive API test with working authentication
"""

import asyncio
import os
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient

load_dotenv()

async def test_onedrive_access():
    """Test OneDrive access with working authentication"""
    print("🔍 Testing OneDrive File Access...")
    
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
            print(f"📋 Testing with user: {first_user.display_name}")
            
            # Test OneDrive access
            try:
                # Get user's drive
                drive = await graph_client.users.by_user_id(first_user.id).drive.get()
                print(f"✅ OneDrive accessible: {drive.name}")
                
                # Try to list root items
                try:
                    items = await graph_client.users.by_user_id(first_user.id).drive.root.children.get()
                    print(f"✅ SUCCESS: Found {len(items.value) if items.value else 0} items in OneDrive root")
                    
                    if items.value:
                        print("📁 OneDrive contents:")
                        for item in items.value[:5]:  # Show first 5 items
                            item_type = "📁" if item.folder else "📄"
                            print(f"   {item_type} {item.name}")
                            
                            # Check for University folder
                            if item.name.lower() == 'university' and item.folder:
                                print(f"\n🎓 Testing University folder...")
                                try:
                                    uni_items = await graph_client.users.by_user_id(first_user.id).drive.items.by_drive_item_id(item.id).children.get()
                                    print(f"✅ University folder contains {len(uni_items.value) if uni_items.value else 0} items")
                                except Exception as e:
                                    print(f"⚠️ University folder access issue: {e}")
                                    
                    return True
                    
                except Exception as e:
                    print(f"❌ Error listing OneDrive contents: {e}")
                    return False
                    
            except Exception as e:
                print(f"❌ Error accessing user's OneDrive: {e}")
                return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_onedrive_access())
