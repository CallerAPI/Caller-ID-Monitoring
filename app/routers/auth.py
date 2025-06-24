from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.services.caller_api import CallerAPIService
from app.services.monitor import set_api_key

router = APIRouter(prefix="/api/v1/auth")

class ApiKeyVerification(BaseModel):
    api_key: str

@router.post("/verify")
async def verify_api_key(verification: ApiKeyVerification):
    try:
        service = CallerAPIService(api_key=verification.api_key)
        account_info = service.get_account_info()
        return account_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/confirm")
async def confirm_account(request: Request, verification: ApiKeyVerification):
    try:
        # Verify one more time to ensure the key is still valid
        service = CallerAPIService(api_key=verification.api_key)
        service.get_account_info()
        
        # Store API key in session
        request.session["api_key"] = verification.api_key
        
        # Set up monitoring with this API key
        set_api_key(verification.api_key)
        
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 