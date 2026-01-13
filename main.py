import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from config import PORT
from telegram_client import ensure_connected, disconnect
from business_settings import switch_to_staccerbot, switch_to_kimfeetguru
from ppv_flow import send_ppv, PPVFlowError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


# Request/Response models
class SendPPVRequest(BaseModel):
    photo_url: str = Field(..., description="URL of the photo to send (e.g., ibb.co link)")
    username: str = Field(..., description="Target username to send PPV to")
    stars: int = Field(..., ge=1, description="Number of stars to charge")


class SendPPVResponse(BaseModel):
    status: str
    message: str
    username: str


class ErrorResponse(BaseModel):
    status: str = "error"
    message: str


class HealthResponse(BaseModel):
    status: str = "ok"


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Telegram PPV Bot service...")
    try:
        await ensure_connected()
        logger.info("Telegram client connected successfully")
    except RuntimeError as e:
        logger.warning(f"Telegram client not authorized: {e}")
        logger.info("Run 'python telegram_client.py' to generate SESSION_STRING")
    except Exception as e:
        logger.error(f"Failed to connect Telegram client: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Telegram PPV Bot service...")
    await disconnect()
    logger.info("Telegram client disconnected")


# Create FastAPI app
app = FastAPI(
    title="Telegram PPV Bot",
    description="Automates sending Pay-Per-View media through Telegram",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint for Railway."""
    return HealthResponse(status="ok")


@app.post(
    "/send-ppv",
    response_model=SendPPVResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    tags=["PPV"]
)
async def send_ppv_endpoint(request: SendPPVRequest):
    """
    Send a PPV (Pay-Per-View) media to a Telegram user.
    
    This endpoint:
    1. Switches the business bot to staccerbot
    2. Executes the PPV flow (upload photo, set price, select user)
    3. Switches the business bot back to kimfeetguru_bot
    4. Returns success/error response
    """
    logger.info(f"Received PPV request: photo={request.photo_url}, user=@{request.username}, stars={request.stars}")
    
    try:
        # Get connected client
        client = await ensure_connected()
        
        # Step 1: Switch to staccerbot
        logger.info("Step 1: Switching to staccerbot")
        await switch_to_staccerbot(client)
        
        try:
            # Step 2: Execute PPV flow
            logger.info("Step 2: Executing PPV flow")
            result = await send_ppv(
                client,
                photo_url=request.photo_url,
                username=request.username,
                stars=request.stars
            )
            
        finally:
            # Step 3: Always switch back to kimfeetguru_bot
            logger.info("Step 3: Switching back to kimfeetguru_bot")
            try:
                await switch_to_kimfeetguru(client)
            except Exception as e:
                logger.error(f"Failed to switch back to kimfeetguru_bot: {e}")
                # Don't raise - we still want to return the PPV result
        
        logger.info(f"PPV sent successfully to @{request.username}")
        return SendPPVResponse(**result)
        
    except RuntimeError as e:
        logger.error(f"Client not authorized: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    except PPVFlowError as e:
        logger.error(f"PPV flow error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.detail}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
