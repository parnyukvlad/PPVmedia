import logging
from telethon import TelegramClient, functions, types

from config import STACCERBOT_USERNAME, KIMFEETGURU_BOT_USERNAME

logger = logging.getLogger(__name__)


async def switch_to_staccerbot(client: TelegramClient) -> bool:
    """
    Switch the connected business bot to staccerbot.
    
    Returns True on success, raises exception on failure.
    """
    return await _switch_business_bot(client, STACCERBOT_USERNAME)


async def switch_to_kimfeetguru(client: TelegramClient) -> bool:
    """
    Switch the connected business bot back to kimfeetguru_bot.
    
    Returns True on success, raises exception on failure.
    """
    return await _switch_business_bot(client, KIMFEETGURU_BOT_USERNAME)


async def _switch_business_bot(client: TelegramClient, bot_username: str) -> bool:
    """
    Switch connected business bot using account.UpdateConnectedBotRequest.
    
    Args:
        client: Connected Telethon client
        bot_username: Username of the bot to connect
        
    Returns:
        True on success
    """
    logger.info(f"Switching business bot to @{bot_username}")
    
    try:
        # Get the bot entity
        bot_entity = await client.get_entity(bot_username)
        logger.debug(f"Found bot entity: {bot_entity.id}")
        
        # First, try to disconnect any existing business bot
        # We do this by calling update with deleted=True for the current bot
        # But since we might not know the current bot, we'll just connect the new one
        
        # Connect the new business bot
        result = await client(functions.account.UpdateConnectedBotRequest(
            bot=bot_entity,
            recipients=types.InputBusinessBotRecipients(
                existing_chats=True,
                new_chats=True,
                contacts=True,
                non_contacts=True,
                exclude_selected=False
            ),
            rights=types.BusinessBotRights(
                reply=True,
                read_messages=True
            )
        ))
        
        logger.info(f"Successfully connected @{bot_username} as business bot")
        return True
        
    except Exception as e:
        logger.error(f"Failed to switch business bot to @{bot_username}: {e}")
        raise


async def disconnect_business_bot(client: TelegramClient, bot_username: str) -> bool:
    """
    Disconnect a business bot.
    
    Args:
        client: Connected Telethon client
        bot_username: Username of the bot to disconnect
        
    Returns:
        True on success
    """
    logger.info(f"Disconnecting business bot @{bot_username}")
    
    try:
        bot_entity = await client.get_entity(bot_username)
        
        result = await client(functions.account.UpdateConnectedBotRequest(
            bot=bot_entity,
            recipients=types.InputBusinessBotRecipients(),
            deleted=True
        ))
        
        logger.info(f"Successfully disconnected @{bot_username}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to disconnect business bot @{bot_username}: {e}")
        raise


async def test_switch():
    """Test function for verifying business bot switching."""
    from telegram_client import ensure_connected
    
    client = await ensure_connected()
    
    print("Testing business bot switch...")
    
    # Switch to staccerbot
    print(f"1. Switching to @{STACCERBOT_USERNAME}...")
    await switch_to_staccerbot(client)
    print("   ✓ Success!")
    
    input("Press Enter to switch back to kimfeetguru_bot...")
    
    # Switch back to kimfeetguru_bot
    print(f"2. Switching to @{KIMFEETGURU_BOT_USERNAME}...")
    await switch_to_kimfeetguru(client)
    print("   ✓ Success!")
    
    print("\nBusiness bot switching test completed!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_switch())
