import asyncio
import logging
import io
import json
from typing import Optional

import httpx
from telethon import TelegramClient
from telethon.tl.types import (
    KeyboardButtonCallback, 
    KeyboardButtonSwitchInline,
    KeyboardButtonUrl,
    KeyboardButtonRequestPhone,
    KeyboardButtonRequestGeoLocation,
    KeyboardButtonGame,
    KeyboardButtonBuy,
    KeyboardButtonRequestPoll,
    KeyboardButtonUserProfile,
    KeyboardButtonWebView,
    KeyboardButtonSimpleWebView,
    KeyboardButtonRequestPeer,
    ReplyInlineMarkup,
    ReplyKeyboardMarkup,
    InputPeerUser,
)
from telethon.tl.functions.messages import SendBotRequestedPeerRequest

from config import STACCERBOT_USERNAME, BOT_RESPONSE_TIMEOUT, PHOTO_DOWNLOAD_TIMEOUT

logger = logging.getLogger(__name__)

# Set to DEBUG for maximum verbosity
logging.getLogger(__name__).setLevel(logging.DEBUG)


class PPVFlowError(Exception):
    """Custom exception for PPV flow errors."""
    pass


def log_message_details(message, step_name: str):
    """Log detailed information about a message including buttons."""
    logger.info(f"=== {step_name} - Message Details ===")
    logger.info(f"Message ID: {message.id}")
    logger.info(f"Message text: {message.text}")
    logger.info(f"Message raw_text: {message.raw_text}")
    
    # Log reply markup type
    if message.reply_markup:
        markup_type = type(message.reply_markup).__name__
        logger.info(f"Reply markup type: {markup_type}")
        
        if isinstance(message.reply_markup, ReplyInlineMarkup):
            logger.info("This is an INLINE keyboard")
        elif isinstance(message.reply_markup, ReplyKeyboardMarkup):
            logger.info("This is a REPLY keyboard")
    else:
        logger.info("No reply markup on this message")
    
    # Log buttons in detail
    if message.buttons:
        logger.info(f"Total button rows: {len(message.buttons)}")
        for row_idx, row in enumerate(message.buttons):
            logger.info(f"  Row {row_idx}: {len(row)} buttons")
            for btn_idx, button in enumerate(row):
                log_button_details(button, row_idx, btn_idx)
    else:
        logger.info("No buttons on this message")
    
    logger.info(f"=== End {step_name} ===")


def log_button_details(button, row_idx: int, btn_idx: int):
    """Log detailed information about a single button."""
    prefix = f"    Button [{row_idx}][{btn_idx}]"
    
    logger.info(f"{prefix} Text: '{button.text}'")
    logger.info(f"{prefix} Button type: {type(button.button).__name__}")
    
    # Get the underlying button object
    btn = button.button
    
    if isinstance(btn, KeyboardButtonCallback):
        logger.info(f"{prefix} -> CALLBACK button")
        logger.info(f"{prefix}    Data (bytes): {btn.data}")
        try:
            data_str = btn.data.decode('utf-8')
            logger.info(f"{prefix}    Data (string): {data_str}")
        except:
            logger.info(f"{prefix}    Data (hex): {btn.data.hex()}")
            
    elif isinstance(btn, KeyboardButtonSwitchInline):
        logger.info(f"{prefix} -> SWITCH INLINE button")
        logger.info(f"{prefix}    Query: '{btn.query}'")
        logger.info(f"{prefix}    Same peer: {btn.same_peer}")
        if hasattr(btn, 'peer_types'):
            logger.info(f"{prefix}    Peer types: {btn.peer_types}")
            
    elif isinstance(btn, KeyboardButtonUrl):
        logger.info(f"{prefix} -> URL button")
        logger.info(f"{prefix}    URL: {btn.url}")
        
    elif isinstance(btn, KeyboardButtonWebView):
        logger.info(f"{prefix} -> WEB VIEW button")
        logger.info(f"{prefix}    URL: {btn.url}")
        
    elif isinstance(btn, KeyboardButtonSimpleWebView):
        logger.info(f"{prefix} -> SIMPLE WEB VIEW button")
        logger.info(f"{prefix}    URL: {btn.url}")
        
    elif isinstance(btn, KeyboardButtonUserProfile):
        logger.info(f"{prefix} -> USER PROFILE button")
        logger.info(f"{prefix}    User ID: {btn.user_id}")
        
    elif isinstance(btn, KeyboardButtonRequestPeer):
        logger.info(f"{prefix} -> REQUEST PEER button")
        logger.info(f"{prefix}    Button ID: {btn.button_id}")
        logger.info(f"{prefix}    Peer type: {btn.peer_type}")
        logger.info(f"{prefix}    Max quantity: {btn.max_quantity}")
        
    elif isinstance(btn, KeyboardButtonBuy):
        logger.info(f"{prefix} -> BUY button")
        
    elif isinstance(btn, KeyboardButtonGame):
        logger.info(f"{prefix} -> GAME button")
        logger.info(f"{prefix}    Text: {btn.text}")
        
    else:
        logger.info(f"{prefix} -> OTHER button type: {type(btn)}")
        # Try to log all attributes
        try:
            attrs = {k: v for k, v in vars(btn).items() if not k.startswith('_')}
            logger.info(f"{prefix}    Attributes: {attrs}")
        except:
            pass


async def download_photo(url: str) -> bytes:
    """
    Download photo from URL (supports ibb.co and other image hosts).
    
    Args:
        url: URL of the image to download
        
    Returns:
        Image bytes
    """
    logger.info(f"Downloading photo from {url}")
    
    async with httpx.AsyncClient(timeout=PHOTO_DOWNLOAD_TIMEOUT, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        
        content_type = response.headers.get("content-type", "")
        logger.debug(f"Response headers: {dict(response.headers)}")
        
        if not content_type.startswith("image/"):
            logger.warning(f"Unexpected content type: {content_type}")
        
        logger.info(f"Downloaded {len(response.content)} bytes, content-type: {content_type}")
        return response.content


async def wait_for_response(conv, timeout: int = 30):
    """Wait for bot response with timeout (default 30 seconds)."""
    logger.debug(f"Waiting for response with timeout={timeout}s")
    try:
        response = await asyncio.wait_for(conv.get_response(), timeout=timeout)
        logger.debug(f"Received response in time")
        return response
    except asyncio.TimeoutError:
        logger.error(f"Timeout waiting for bot response after {timeout}s")
        raise PPVFlowError(f"Bot did not respond within {timeout} seconds")


async def find_and_click_button(message, button_text: str) -> bool:
    """
    Find and click an inline button by text.
    
    Args:
        message: Message with inline buttons
        button_text: Text to search for (case-insensitive, partial match)
        
    Returns:
        True if button was clicked
    """
    logger.info(f"Looking for button with text: '{button_text}'")
    
    if not message.buttons:
        logger.warning("Message has no buttons")
        return False
    
    for row_idx, row in enumerate(message.buttons):
        for btn_idx, button in enumerate(row):
            if button_text.lower() in button.text.lower():
                logger.info(f"Found matching button at [{row_idx}][{btn_idx}]: '{button.text}'")
                log_button_details(button, row_idx, btn_idx)
                logger.info(f"Clicking button: {button.text}")
                await button.click()
                logger.info(f"Button clicked successfully")
                return True
    
    logger.warning(f"Button with text '{button_text}' not found in {len(message.buttons)} rows")
    return False


async def handle_user_selection(client: TelegramClient, conv, message, username: str):
    """
    Handle the user selection step using SendBotRequestedPeerRequest.
    
    The "Select User" button is a KeyboardButtonRequestPeer which requires
    using the SendBotRequestedPeerRequest to respond with the selected user.
    
    Args:
        client: Telethon client
        conv: Active conversation with the bot
        message: Message with Select User button
        username: Target username to select
        
    Returns:
        Response message from the bot after selection
    """
    logger.info(f"=== Handling user selection for @{username} ===")
    
    # Log full message details to understand the interface
    log_message_details(message, "User Selection Step")
    
    # Clean username (remove @ if present)
    clean_username = username.lstrip("@")
    logger.debug(f"Clean username: {clean_username}")
    
    # Find the RequestPeer button
    button_id = None
    if message.reply_markup:
        for row in message.reply_markup.rows:
            for button in row.buttons:
                if isinstance(button, KeyboardButtonRequestPeer):
                    button_id = button.button_id
                    logger.info(f"Found RequestPeer button with ID: {button_id}")
                    logger.info(f"  Peer type: {button.peer_type}")
                    break
            if button_id is not None:
                break
    
    if button_id is None:
        logger.error("Could not find RequestPeer button in message")
        raise PPVFlowError("Could not find user selection button")
    
    # Get the target user entity
    try:
        target_user = await client.get_entity(clean_username)
        logger.info(f"Found target user: ID={target_user.id}, name={target_user.first_name}")
    except Exception as e:
        logger.error(f"Could not find user @{clean_username}: {e}")
        raise PPVFlowError(f"Could not find user @{clean_username}: {e}")
    
    # Get the bot entity (staccerbot)
    staccerbot = await client.get_entity(STACCERBOT_USERNAME)
    logger.info(f"Sending requested peer to bot (msg_id={message.id}, button_id={button_id})")
    
    # Send the selected peer to the bot using SendBotRequestedPeerRequest
    try:
        result = await client(SendBotRequestedPeerRequest(
            peer=staccerbot,
            msg_id=message.id,
            button_id=button_id,
            requested_peers=[InputPeerUser(
                user_id=target_user.id,
                access_hash=target_user.access_hash
            )]
        ))
        logger.info(f"SendBotRequestedPeerRequest successful: {result}")
    except Exception as e:
        logger.error(f"SendBotRequestedPeerRequest failed: {e}")
        raise PPVFlowError(f"Failed to select user: {e}")
    
    # Wait for bot confirmation
    logger.info("Waiting for bot response after user selection...")
    response = await wait_for_response(conv, timeout=30)
    log_message_details(response, "User Selection Response")
    
    return response


async def send_ppv(
    client: TelegramClient,
    photo_url: str,
    username: str,
    stars: int
) -> dict:
    """
    Execute the complete PPV sending flow with staccerbot.
    
    Args:
        client: Connected and authorized Telethon client
        photo_url: URL of the photo to send as PPV
        username: Target username to send PPV to
        stars: Number of stars to charge
        
    Returns:
        dict with status and message
    """
    logger.info("=" * 60)
    logger.info(f"STARTING PPV FLOW")
    logger.info(f"  Photo URL: {photo_url}")
    logger.info(f"  Target user: @{username}")
    logger.info(f"  Stars: {stars}")
    logger.info("=" * 60)
    
    # Download photo first
    try:
        photo_bytes = await download_photo(photo_url)
        logger.info(f"Photo downloaded: {len(photo_bytes)} bytes")
    except Exception as e:
        logger.exception(f"Failed to download photo: {e}")
        raise PPVFlowError(f"Failed to download photo: {e}")
    
    # Get staccerbot entity
    try:
        staccerbot = await client.get_entity(STACCERBOT_USERNAME)
        logger.info(f"Found staccerbot: ID={staccerbot.id}, username=@{staccerbot.username}")
    except Exception as e:
        logger.exception(f"Failed to find staccerbot: {e}")
        raise PPVFlowError(f"Failed to find @{STACCERBOT_USERNAME}: {e}")
    
    logger.info(f"Starting conversation with @{STACCERBOT_USERNAME}")
    
    async with client.conversation(staccerbot, timeout=30) as conv:
        # =====================
        # Step 1: Send /sell command
        # =====================
        logger.info("")
        logger.info("=" * 40)
        logger.info("STEP 1: Sending /sell command")
        logger.info("=" * 40)
        await conv.send_message("/sell")
        response = await wait_for_response(conv, timeout=30)
        log_message_details(response, "Step 1 Response")
        
        # Expected: "Will do. Send a photo or a video to start, boss."
        if "send a photo" not in response.text.lower() and "send" not in response.text.lower():
            logger.warning(f"Unexpected response to /sell: {response.text}")
        
        # =====================
        # Step 2: Send photo
        # =====================
        logger.info("")
        logger.info("=" * 40)
        logger.info("STEP 2: Sending photo")
        logger.info("=" * 40)
        # Create BytesIO with name attribute so Telethon recognizes it as an image
        photo_file = io.BytesIO(photo_bytes)
        photo_file.name = "photo.jpg"  # This tells Telethon it's an image
        
        await conv.send_file(
            photo_file,
            force_document=False  # Send as photo/image, not as document
        )
        logger.info("Photo sent, waiting for response...")
        response = await wait_for_response(conv, timeout=30)
        log_message_details(response, "Step 2 Response")
        
        # Expected: "Looks good to me. Now send a caption for the PPV or tap 'Empty'"
        
        # =====================
        # Step 3: Click "Empty" button for no caption
        # =====================
        logger.info("")
        logger.info("=" * 40)
        logger.info("STEP 3: Clicking 'Empty' button")
        logger.info("=" * 40)
        if not await find_and_click_button(response, "Empty"):
            logger.warning("Could not find 'Empty' button, sending 'Empty' as text")
            await conv.send_message("Empty")
        
        response = await wait_for_response(conv, timeout=30)
        log_message_details(response, "Step 3 Response")
        
        # Expected: "How many Stars we gon' take for the PPV?"
        
        # =====================
        # Step 4: Send stars amount
        # =====================
        logger.info("")
        logger.info("=" * 40)
        logger.info(f"STEP 4: Sending stars amount: {stars}")
        logger.info("=" * 40)
        await conv.send_message(str(stars))
        response = await wait_for_response(conv, timeout=30)
        log_message_details(response, "Step 4 Response")
        
        # Expected: "Bet. Who should I send the PPV to, boss?"
        # With "Select User" button
        
        # =====================
        # Step 5: Handle user selection (with retry logic)
        # =====================
        logger.info("")
        logger.info("=" * 40)
        logger.info(f"STEP 5: Selecting user @{username}")
        logger.info("=" * 40)
        
        max_retries = 2
        retry_count = 0
        
        while retry_count <= max_retries:
            # Handle the user selection using SendBotRequestedPeerRequest
            response = await handle_user_selection(client, conv, response, username)
            
            # Check for "no exchange in 48h" error
            if "no exchange" in response.text.lower() or "48h" in response.text.lower():
                retry_count += 1
                logger.warning(f"Got 'no exchange in 48h' error (retry {retry_count}/{max_retries})")
                
                if retry_count > max_retries:
                    logger.error("Max retries exceeded for establishing contact")
                    raise PPVFlowError("Cannot send PPV: no recent exchange with user and retries exhausted")
                
                # Need to establish contact first by sending a quick message
                logger.info(f"Establishing contact with @{username}...")
                
                try:
                    # Get target user entity
                    clean_username = username.lstrip("@")
                    target_user = await client.get_entity(clean_username)
                    
                    # Send a quick message to the target user
                    quick_msg = await client.send_message(target_user, "Hey! 👋")
                    logger.info(f"Sent quick message to @{username}, message ID: {quick_msg.id}")
                    
                    # Wait a bit
                    await asyncio.sleep(2)
                    
                    # Delete the message
                    await quick_msg.delete()
                    logger.info("Quick message deleted")
                    
                except Exception as e:
                    logger.error(f"Failed to send/delete quick message: {e}")
                    # Continue anyway, try the retry button
                
                # Click "Try again" button
                logger.info("Clicking 'Try again' button...")
                try:
                    await response.click(data=b"sell_refresh")
                    logger.info("Clicked 'Try again' button")
                except Exception as e:
                    logger.warning(f"Could not click by data, trying by text: {e}")
                    if not await find_and_click_button(response, "Try again"):
                        raise PPVFlowError("Could not find 'Try again' button")
                
                # Wait for bot to ask for user selection again
                response = await wait_for_response(conv, timeout=30)
                log_message_details(response, "After Try Again Response")
                
                # Continue the loop to try user selection again
                continue
            
            # If no error, break out of retry loop
            break
        
        # Expected: "On it boss, preparing your PPV now."
        
        # =====================
        # Wait for final confirmation
        # =====================
        logger.info("")
        logger.info("=" * 40)
        logger.info("Waiting for final confirmation...")
        logger.info("=" * 40)
        try:
            final_response = await wait_for_response(conv, timeout=60)
            log_message_details(final_response, "Final Response")
            
            # Expected: "Done deal, PPV sent."
            if "done" in final_response.text.lower() or "sent" in final_response.text.lower():
                logger.info("SUCCESS: PPV sent successfully!")
                return {
                    "status": "success",
                    "message": "PPV sent successfully",
                    "username": username
                }
        except PPVFlowError:
            # If we timeout waiting for final confirmation, check the last response
            if "preparing" in response.text.lower():
                logger.info("PPV appears to be preparing, assuming success")
                return {
                    "status": "success",
                    "message": "PPV submitted for sending",
                    "username": username
                }
    
    logger.info("PPV flow completed")
    return {
        "status": "success",
        "message": "PPV flow completed",
        "username": username
    }


async def test_ppv_flow():
    """Test function for PPV flow (requires real credentials)."""
    # Set up detailed logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    from telegram_client import ensure_connected
    
    client = await ensure_connected()
    
    # Test with a dummy URL and username
    result = await send_ppv(
        client,
        photo_url="https://i.ibb.co/placeholder/test.jpg",
        username="test_user",
        stars=100
    )
    
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(test_ppv_flow())
