# Telegram PPV Automation Bot

A Python service that automates sending Pay-Per-View (PPV) media through Telegram using Telethon and staccerbot.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Generate Session String (First Time Only)
```bash
python telegram_client.py
```
This will:
- Prompt for your phone number
- Send a verification code
- Generate a SESSION_STRING for Railway

### 4. Run Locally
```bash
uvicorn main:app --reload
```

### 5. Test the API
```bash
# Health check
curl http://localhost:8000/health

# Send PPV
curl -X POST http://localhost:8000/send-ppv \
  -H "Content-Type: application/json" \
  -d '{"photo_url": "https://i.ibb.co/xxx/photo.jpg", "username": "target_user", "stars": 200}'
```

## Railway Deployment

1. Push code to GitHub
2. Create new Railway project from repo
3. Add environment variables:
   - `API_ID`
   - `API_HASH`
   - `SESSION_STRING` (from step 3 above)
4. Deploy

## API Endpoints

### POST /send-ppv
Send PPV content to a user.

**Request:**
```json
{
  "photo_url": "https://i.ibb.co/xxxxx/photo.jpg",
  "username": "target_username",
  "stars": 200
}
```

**Response:**
```json
{
  "status": "success",
  "message": "PPV sent successfully",
  "username": "target_username"
}
```

### GET /health
Health check endpoint.

## Flow Overview

1. **Switch to staccerbot** - Connect staccerbot as business bot
2. **Execute PPV flow** - `/sell` → photo → "Empty" → stars → select user
3. **Switch back** - Reconnect kimfeetguru_bot

## Project Structure
```
├── main.py              # FastAPI endpoints
├── telegram_client.py   # Telethon client singleton
├── business_settings.py # Business bot switching
├── ppv_flow.py          # PPV sending flow
├── config.py            # Configuration
├── requirements.txt
├── Dockerfile
├── railway.toml
└── .env.example
```
