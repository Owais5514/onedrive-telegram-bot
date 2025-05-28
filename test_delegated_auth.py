#!/usr/bin/env python3
"""
Test script for delegated authentication approach
This uses user-based authentication instead of application permissions
"""

import asyncio
import os
from dotenv import load_dotenv
from azure.identity import InteractiveBrowserCredential
from msgraph import GraphServiceClient

# Load environment variables
load_dotenv()

async def test_delegated_auth():
    """Test OneDrive access using delegated permissions"""
    print("🔍 Testing delegated authentication for OneDrive access...")
    
    # Required for delegated permissions
    client_id = os.getenv('AZURE_CLIENT_ID')
    tenant_id = os.getenv('AZURE_TENANT_ID')
    
    if not client_id or not tenant_id:
        print("❌ Missing AZURE_CLIENT_ID or AZURE_TENANT_ID in .env file")
        return
    
    print(f"📋 Using Client ID: {client_id}")
    print(f"📋 Using Tenant ID: {tenant_id}")
    
    try:
        # Delegated permissions - requires user login
        credential = InteractiveBrowserCredential(
            client_id=client_id,
            tenant_id=tenant_id,
            redirect_uri="http://localhost:8000/auth/callback"
        )
        
        # Create Graph client with delegated auth
        scopes = [
            'https://graph.microsoft.com/Files.Read',
            'https://graph.microsoft.com/Files.ReadWrite',
            'https://graph.microsoft.com/User.Read'
        ]
        
        graph_client = GraphServiceClient(
            credentials=credential,
            scopes=scopes
        )
        
        print("✅ Graph client with delegated auth initialized")
        
        # Test accessing current user's OneDrive
        print("\n🔍 Testing access to current user's OneDrive...")
        me = await graph_client.me.get()
        print(f"✅ Current user: {me.display_name} ({me.user_principal_name})")
        
        # Test OneDrive access
        drive = await graph_client.me.drive.get()
        print(f"✅ OneDrive accessed: {drive.name}")
        
        # Test listing root folder
        items = await graph_client.me.drive.root.children.get()
        print(f"✅ Found {len(items.value) if items.value else 0} items in OneDrive root:")
        
        if items.value:
            for item in items.value[:5]:  # Show first 5 items
                item_type = "📁" if item.folder else "📄"
                print(f"   {item_type} {item.name}")
                
                # Test if University folder exists
                if item.name.lower() == 'university' and item.folder:
                    print(f"\n🎓 Found University folder! Testing access...")
                    uni_items = await graph_client.me.drive.items.by_drive_item_id(item.id).children.get()
                    print(f"✅ University folder contains {len(uni_items.value) if uni_items.value else 0} items")
        
        print("\n✅ Delegated authentication test completed successfully!")
        print("💡 This approach requires user login but doesn't need admin consent")
        
    except Exception as e:
        print(f"❌ Delegated authentication failed: {e}")
        print("💡 This might work better than application permissions for personal OneDrive")

if __name__ == "__main__":
    asyncio.run(test_delegated_auth())
