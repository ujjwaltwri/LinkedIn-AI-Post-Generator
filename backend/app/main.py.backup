from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from pydantic_settings import BaseSettings, SettingsConfigDict

# This class will automatically read variables from your .env file
class Settings(BaseSettings):
    linkedin_client_id: str
    linkedin_client_secret: str

    # Tells Pydantic to look for a .env file
    model_config = SettingsConfigDict(env_file=".env")

# Create an instance of the Settings class
settings = Settings()

# Define the Redirect URI
REDIRECT_URI = "http://127.0.0.1:8000/auth/callback"

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Influence OS Agent Backend is running."}

@app.get("/login/linkedin")
def login_linkedin():
    scopes = "profile email openid"
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={settings.linkedin_client_id}" # Use settings here
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={scopes}"
    )
    return RedirectResponse(url=auth_url)