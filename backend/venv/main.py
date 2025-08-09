import os
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

load_dotenv()

LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
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
        f"&client_id={LINKEDIN_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={scopes}"
    )
    return RedirectResponse(url=auth_url)