import logging
from telethon import TelegramClient
from telethon.sessions import StringSession

from config import API_ID, API_HASH, SESSION_STRING

logger = logging.getLogger(__name__)

# Singleton client instance
_client: TelegramClient | None = None


def get_client() -> TelegramClient:
    """Get or create the Telethon client singleton."""
    global _client
    
    if _client is None:
        if SESSION_STRING:
            session = StringSession(SESSION_STRING)
            logger.info("Using existing session from SESSION_STRING")
        else:
            session = StringSession()
            logger.warning("No SESSION_STRING provided - will need phone authentication")
        
        _client = TelegramClient(session, API_ID, API_HASH)
    
    return _client


async def ensure_connected() -> TelegramClient:
    """Ensure client is connected and return it."""
    client = get_client()
    
    if not client.is_connected():
        await client.connect()
        logger.info("Telegram client connected")
    
    if not await client.is_user_authorized():
        raise RuntimeError(
            "Client is not authorized. Please run generate_session() first "
            "to authenticate and generate a SESSION_STRING."
        )
    
    return client


async def disconnect():
    """Disconnect the client if connected."""
    global _client
    
    if _client and _client.is_connected():
        await _client.disconnect()
        logger.info("Telegram client disconnected")


async def generate_session():
    """
    Interactive session generation for first-time setup.
    Run this locally to generate SESSION_STRING for Railway.
    """
    client = get_client()
    
    await client.connect()
    
    if not await client.is_user_authorized():
        phone = input("Enter your phone number (with country code): ")
        await client.send_code_request(phone)
        
        code = input("Enter the code you received: ")
        try:
            await client.sign_in(phone, code)
        except Exception as e:
            if "Two-steps verification" in str(e) or "password" in str(e).lower():
                password = input("Enter your 2FA password: ")
                await client.sign_in(password=password)
            else:
                raise
    
    session_string = client.session.save()
    print("\n" + "=" * 60)
    print("SESSION_STRING generated successfully!")
    print("=" * 60)
    print("\nAdd this to your Railway environment variables:")
    print(f"\nSESSION_STRING={session_string}")
    print("\n" + "=" * 60)
    
    await client.disconnect()
    return session_string


if __name__ == "__main__":
    import asyncio
    asyncio.run(generate_session())
