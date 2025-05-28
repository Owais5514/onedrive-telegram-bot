#!/usr/bin/env python3
"""
Verify that Owais Ahmed is set as the default user
"""

import asyncio
import os
import aiohttp
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential

load_dotenv()

async def verify_default_user():
    """Verify that Owais Ahmed is the default user"""
    
    # Get credentials
    client_id = os.getenv('AZURE_CLIENT_ID')
    client_secret = os.getenv('AZURE_CLIENT_SECRET')
    tenant_id = os.getenv('AZURE_TENANT_ID')
    
    print("🔍 Verifying default user settings...")
    
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
        
        # Get users
        async with aiohttp.ClientSession() as session:
            headers = {'Authorization': f'Bearer {access_token}'}
            
            async with session.get('https://graph.microsoft.com/v1.0/users', headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    users = data.get('value', [])
                    
                    print(f"📊 Total users found: {len(users)}")
                    print("\n👥 All users in organization:")
                    
                    owais_user = None
                    for i, user in enumerate(users):
                        is_owais = 'owais ahmed' in user['displayName'].lower()
                        marker = "🎯 DEFAULT" if is_owais else f"  {i+1:2d}."
                        print(f"{marker} {user['displayName']} ({user['userPrincipalName']})")
                        
                        if is_owais:
                            owais_user = user
                    
                    if owais_user:
                        print(f"\n✅ Owais Ahmed found and will be used as default user")
                        print(f"   📧 Email: {owais_user['userPrincipalName']}")
                        print(f"   🆔 User ID: {owais_user['id'][:8]}...")
                        
                        # Test OneDrive access for Owais
                        print(f"\n🔍 Testing Owais Ahmed's OneDrive...")
                        onedrive_url = f"https://graph.microsoft.com/v1.0/users/{owais_user['id']}/drive/root/children"
                        
                        async with session.get(onedrive_url, headers=headers) as onedrive_response:
                            if onedrive_response.status == 200:
                                onedrive_data = await onedrive_response.json()
                                items = onedrive_data.get('value', [])
                                print(f"✅ Owais Ahmed's OneDrive: {len(items)} items accessible")
                                
                                print(f"\n📁 Owais Ahmed's OneDrive folders:")
                                for item in items[:8]:
                                    item_type = "📁" if 'folder' in item else "📄"
                                    print(f"   {item_type} {item['name']}")
                            else:
                                print(f"❌ Could not access Owais Ahmed's OneDrive: {onedrive_response.status}")
                    else:
                        print(f"\n❌ Owais Ahmed not found in the organization")
                        print(f"   The bot will use the first user as fallback")
                    
                else:
                    print(f"❌ Failed to get users: {response.status}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    asyncio.run(verify_default_user())
