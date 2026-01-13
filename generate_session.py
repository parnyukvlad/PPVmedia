"""
Generate Telegram session string for Railway deployment.

Run this script locally to authenticate and generate a SESSION_STRING
that can be used as an environment variable on Railway.

Usage:
    python generate_session.py
"""

import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

from config import API_ID, API_HASH


async def generate_session():
    """
    Interactive session generation for first-time setup.
    """
    print("=" * 60)
    print("Telegram Session Generator")
    print("=" * 60)
    print()
    print("This script will authenticate you with Telegram and generate")
    print("a SESSION_STRING for use with Railway deployment.")
    print()
    
    # Create client with empty session
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    
    await client.connect()
    
    if not await client.is_user_authorized():
        phone = input("Enter your phone number (with country code, e.g., +1234567890): ")
        phone = phone.strip()
        
        print(f"\nSending code to {phone}...")
        await client.send_code_request(phone)
        
        code = input("Enter the verification code you received: ")
        code = code.strip()
        
        try:
            await client.sign_in(phone, code)
        except Exception as e:
            error_msg = str(e).lower()
            if "two-steps verification" in error_msg or "password" in error_msg or "2fa" in error_msg:
                print("\nTwo-factor authentication is enabled.")
                password = input("Enter your 2FA password: ")
                await client.sign_in(password=password)
            else:
                raise
    
    # Get session string
    session_string = client.session.save()
    
    print()
    print("=" * 60)
    print("SUCCESS! Session generated.")
    print("=" * 60)
    print()
    print("Add this environment variable to Railway:")
    print()
    print(f"SESSION_STRING={session_string}")
    print()
    print("=" * 60)
    print()
    print("You can now deploy to Railway with this SESSION_STRING.")
    print("Keep this string secret - it grants access to your account!")
    print()
    
    await client.disconnect()
    return session_string


if __name__ == "__main__":
    asyncio.run(generate_session())
