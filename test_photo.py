import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
import httpx
from dotenv import load_dotenv
import os

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

async def test():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()
    
    print("Downloading photo...")
    async with httpx.AsyncClient() as http:
        response = await http.get("https://i.ibb.co/27798Dwj/file.jpg")
        photo_bytes = response.content
        print(f"Downloaded {len(photo_bytes)} bytes")
    
    print("Getting staccerbot...")
    staccerbot = await client.get_entity("@staccerbot")
    print(f"Found: {staccerbot.id}")
    
    print("Sending /sell...")
    await client.send_message(staccerbot, "/sell")
    await asyncio.sleep(2)
    
    print("Sending photo...")
    result = await client.send_file(staccerbot, photo_bytes, caption="")
    print(f"Photo sent! Message ID: {result.id}")
    
    await asyncio.sleep(3)
    
    # Check last messages
    print("\nLast 5 messages in chat:")
    async for msg in client.iter_messages(staccerbot, limit=5):
        print(f"  [{msg.id}] {msg.sender_id}: {msg.text[:50] if msg.text else '[media]'}")
    
    await client.disconnect()

asyncio.run(test())