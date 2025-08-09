from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic_settings import BaseSettings, SettingsConfigDict
import requests
import secrets
from typing import Optional

# This class will automatically read variables from your .env file
class Settings(BaseSettings):
    linkedin_client_id: str
    linkedin_client_secret: str
    # Tells Pydantic to look for a .env file
    model_config = SettingsConfigDict(env_file=".env")

# Create an instance of the Settings class
settings = Settings()

# Define the Redirect URI - exactly as configured in LinkedIn
REDIRECT_URI = "http://127.0.0.1:8000/auth/callback"

app = FastAPI(
    title="Influence OS Agent Backend",
    description="Backend API for LinkedIn OAuth integration",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"message": "Influence OS Agent Backend is running."}

@app.get("/test")
def test_endpoint():
    return {
        "status": "API is working", 
        "linkedin_client_id": settings.linkedin_client_id,
        "redirect_uri": REDIRECT_URI,
        "endpoints": [
            {"method": "GET", "path": "/", "description": "Root endpoint"},
            {"method": "GET", "path": "/test", "description": "Test endpoint"},
            {"method": "GET", "path": "/login/linkedin", "description": "LinkedIn OAuth login"},
            {"method": "GET", "path": "/auth/callback", "description": "LinkedIn OAuth callback"},
        ]
    }

@app.get("/login/linkedin")
def login_linkedin():
    # Generate a random state parameter for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Start with just profile scope - simpler for testing
    scopes = "profile"
    
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={settings.linkedin_client_id}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={scopes}"
        f"&state={state}"
    )
    
    # Debug information
    print(f"Generated state: {state}")
    print(f"Client ID: {settings.linkedin_client_id}")
    print(f"Redirect URI: {REDIRECT_URI}")
    print(f"Full auth URL: {auth_url}")
    
    return RedirectResponse(url=auth_url)

@app.get("/auth/callback")
def auth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None)
):
    """
    Handle the LinkedIn OAuth callback
    """
    
    # Check if there was an OAuth error
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"OAuth error: {error}. Description: {error_description or 'No description provided'}"
        )
    
    # Check if authorization code is present
    if not code:
        raise HTTPException(
            status_code=400,
            detail="Authorization code not provided"
        )
    
    # In a real application, you should validate the state parameter here
    # to prevent CSRF attacks
    
    try:
        # Exchange authorization code for access token
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": settings.linkedin_client_id,
            "client_secret": settings.linkedin_client_secret,
        }
        
        response = requests.post(
            token_url, 
            data=data, 
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to get access token: {response.text}"
            )
        
        token_json = response.json()
        access_token = token_json.get("access_token")
        
        if not access_token:
            raise HTTPException(
                status_code=400,
                detail=f"No access token in response: {token_json}"
            )
        
        # Get user profile information
        profile_response = requests.get(
            "https://api.linkedin.com/v2/userinfo",  # Updated to v2 userinfo endpoint
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if profile_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to get user profile: {profile_response.text}"
            )
        
        profile_data = profile_response.json()
        
        return {
            "status": "success",
            "message": "LinkedIn OAuth successful",
            "access_token": access_token,
            "token_type": token_json.get("token_type"),
            "expires_in": token_json.get("expires_in"),
            "profile": profile_data,
            "state_received": state  # Include for debugging
        }
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Request failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/debug/config")
def debug_config():
    return {
        "client_id": "8614ek1cyrkfze",
        "client_id_from_env": settings.linkedin_client_id,
        "redirect_uri": REDIRECT_URI,
        "has_client_secret": bool(settings.linkedin_client_secret),
        "client_secret_prefix": settings.linkedin_client_secret[:10] + "..." if settings.linkedin_client_secret else "NOT SET",
        "auth_url_sample": (
            f"https://www.linkedin.com/oauth/v2/authorization"
            f"?response_type=code"
            f"&client_id=8614ek1cyrkfze"
            f"&redirect_uri={REDIRECT_URI}"
            f"&scope=profile%20email%20openid"
            f"&state=sample_state"
        ),
        "status": "Check LinkedIn Developer Portal for this client_id"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Influence OS Agent Backend",
        "endpoints_available": True,
        "linkedin_client_configured": bool(settings.linkedin_client_id)
    }
    # Add this endpoint to your existing main.py file, before the @app.get("/health") line

@app.get("/debug/config")
def debug_config():
    return {
        "client_id": "8614ek1cyrkfze",
        "client_id_from_env": settings.linkedin_client_id,
        "redirect_uri": REDIRECT_URI,
        "has_client_secret": bool(settings.linkedin_client_secret),
        "client_secret_prefix": settings.linkedin_client_secret[:10] + "..." if settings.linkedin_client_secret else "NOT SET",
        "auth_url_sample": (
            f"https://www.linkedin.com/oauth/v2/authorization"
            f"?response_type=code"
            f"&client_id=8614ek1cyrkfze"
            f"&redirect_uri={REDIRECT_URI}"
            f"&scope=profile"
            f"&state=sample_state"
        ),
        "status": "Check LinkedIn Developer Portal for this client_id"
    }