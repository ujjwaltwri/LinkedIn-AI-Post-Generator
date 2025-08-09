from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic_settings import BaseSettings, SettingsConfigDict
import requests
from typing import Optional
import urllib.parse

class Settings(BaseSettings):
    linkedin_client_id: str
    linkedin_client_secret: str
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
REDIRECT_URI = "http://127.0.0.1:8000/auth/callback"

app = FastAPI(
    title="Influence OS Agent Backend",
    description="Backend API for LinkedIn OAuth integration using Basic Profile",
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
        "oauth_version": "LinkedIn Basic Profile (no approval required)",
        "endpoints": [
            {"method": "GET", "path": "/", "description": "Root endpoint"},
            {"method": "GET", "path": "/test", "description": "Test endpoint"},
            {"method": "GET", "path": "/login/linkedin", "description": "LinkedIn OAuth login"},
            {"method": "GET", "path": "/auth/callback", "description": "LinkedIn OAuth callback"},
            {"method": "GET", "path": "/health", "description": "Health check"},
            {"method": "GET", "path": "/debug/auth-url", "description": "Debug auth URL"},
        ]
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Influence OS Agent Backend",
        "endpoints_available": True,
        "linkedin_client_configured": bool(settings.linkedin_client_id),
        "oauth_version": "LinkedIn Basic Profile"
    }

@app.get("/login/linkedin")
def login_linkedin():
    # Use only basic profile scope (no approval required)
    scopes = ""  # Empty scope - basic auth only    
    # Generate state parameter for security
    state = "random_state_string_123"
    
    # LinkedIn OAuth 2.0 authorization URL
    auth_params = {
        "response_type": "code",
        "client_id": settings.linkedin_client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": scopes,
        "state": state
    }
    
    # Construct the authorization URL
    base_url = "https://www.linkedin.com/oauth/v2/authorization"
    auth_url = f"{base_url}?{urllib.parse.urlencode(auth_params)}"
    
    return RedirectResponse(url=auth_url)

@app.get("/auth/callback")
def auth_callback(code: str, state: Optional[str] = None, error: Optional[str] = None):
    """
    Handle the LinkedIn OAuth callback using basic profile scope
    """
    # Check for OAuth errors
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"LinkedIn OAuth error: {error}"
        )
    
    if not code:
        raise HTTPException(
            status_code=400,
            detail="No authorization code received from LinkedIn"
        )
    
    try:
        # Exchange authorization code for access token
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": settings.linkedin_client_id,
            "client_secret": settings.linkedin_client_secret,
        }
        
        token_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        # Request access token
        token_response = requests.post(
            token_url, 
            data=token_data, 
            headers=token_headers,
            timeout=30
        )
        
        if token_response.status_code != 200:
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": "Failed to get access token",
                    "status_code": token_response.status_code,
                    "response": token_response.text
                }
            )
        
        token_json = token_response.json()
        access_token = token_json.get("access_token")
        
        if not access_token:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "No access token in response",
                    "token_response": token_json
                }
            )
        
        # Get user profile using basic profile scope
        profile_headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        # Get basic profile info
        profile_response = requests.get(
            "https://api.linkedin.com/v2/me",
            headers=profile_headers,
            timeout=30
        )
        
        profile_data = {}
        
        if profile_response.status_code == 200:
            profile_data = profile_response.json()
        else:
            profile_data = {
                "error": "Could not fetch profile data",
                "status_code": profile_response.status_code,
                "response": profile_response.text
            }
        
        # Email scope not available without approval
        email_data = {
            "note": "Email scope requires LinkedIn product approval",
            "to_get_email": "Request access to 'Sign In with LinkedIn using OpenID Connect' product"
        }
        
        return {
            "status": "success",
            "message": "LinkedIn OAuth successful using basic profile scope",
            "access_token": access_token,
            "token_type": token_json.get("token_type", "Bearer"),
            "expires_in": token_json.get("expires_in"),
            "scope": token_json.get("scope"),
            "profile": profile_data,
            "email": email_data,
            "state": state,
            "api_version": "basic_profile_only"
        }
        
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=500,
            detail="Request to LinkedIn API timed out"
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Request to LinkedIn API failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/debug/auth-url")
def debug_auth_url():
    """
    Debug endpoint to see the generated LinkedIn auth URL using basic profile scope
    """
    scopes = ""  # Empty scope - basic auth only
    state = "debug_state_123"
    
    auth_params = {
        "response_type": "code",
        "client_id": settings.linkedin_client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": scopes,
        "state": state
    }
    
    base_url = "https://www.linkedin.com/oauth/v2/authorization"
    auth_url = f"{base_url}?{urllib.parse.urlencode(auth_params)}"
    
    return {
        "auth_url": auth_url,
        "parameters": auth_params,
        "client_id": settings.linkedin_client_id,
        "redirect_uri": REDIRECT_URI,
        "scopes": scopes,
        "note": "Using basic profile scope only - no LinkedIn product approval required"
    }
