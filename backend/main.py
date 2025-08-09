import os
import requests
import secrets
import urllib.parse # NEW: Import for URL encoding
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import RedirectResponse
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel
from typing import Optional
from pathlib import Path

# --- NEW: Import CORS Middleware ---
from fastapi.middleware.cors import CORSMiddleware

# Database imports
from sqlalchemy.orm import Session
import models, database

# LangChain and AI imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# Create all database tables
models.Base.metadata.create_all(bind=database.engine)

# --- Environment and Settings Configuration ---
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    linkedin_client_id: str
    linkedin_client_secret: str
    google_api_key: str
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH)

settings = Settings()
REDIRECT_URI = "http://127.0.0.1:8000/auth/callback"

app = FastAPI(
    title="Influence OS Agent Backend",
    description="Backend API for LinkedIn OAuth and AI Content Generation",
    version="1.0.0"
)

# --- NEW: Configure CORS ---
# This allows your frontend (running on localhost:5173) to talk to your backend.
origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for API Input ---
class PostCreate(BaseModel):
    user_id: int
    prompt: str

# --- Database Dependency ---
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Authentication Endpoints ---
@app.get("/")
def read_root():
    return {"message": "Influence OS Agent Backend is running."}

@app.get("/login/linkedin")
def login_linkedin():
    state = secrets.token_urlsafe(16)
    scopes = "profile email openid w_member_social"
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code&client_id={settings.linkedin_client_id}"
        f"&redirect_uri={REDIRECT_URI}&scope={scopes}&state={state}"
    )
    return RedirectResponse(url=auth_url)

@app.get("/auth/callback")
def auth_callback(code: Optional[str] = Query(None), db: Session = Depends(get_db)):
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")
    try:
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        data = {
            "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI,
            "client_id": settings.linkedin_client_id, "client_secret": settings.linkedin_client_secret,
        }
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        token_json = response.json()
        access_token = token_json.get("access_token")

        profile_response = requests.get("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {access_token}"})
        profile_response.raise_for_status()
        profile_data = profile_response.json()

        db_user = db.query(models.User).filter(models.User.linkedin_id == profile_data["sub"]).first()
        if db_user:
            db_user.access_token = access_token
        else:
            db_user = models.User(
                linkedin_id=profile_data["sub"], email=profile_data["email"],
                name=profile_data["name"], access_token=access_token
            )
            db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # --- MODIFIED: Redirect user back to frontend with user info ---
        user_name_encoded = urllib.parse.quote(db_user.name)
        frontend_url = f"http://localhost:5173?user_id={db_user.id}&name={user_name_encoded}"
        return RedirectResponse(url=frontend_url)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


# --- AI Content Generation and Posting Endpoint ---
@app.post("/posts/create")
def create_linkedin_post(post_data: PostCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == post_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.access_token:
        raise HTTPException(status_code=400, detail="User does not have a valid access token")

    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=settings.google_api_key)
    
    template = """
    You are an expert LinkedIn thought leader writing for {user_name}.
    Your tone should be professional, insightful, and engaging.
    Based on the following prompt, write a LinkedIn post.
    The post should be concise, well-structured, and include 3-5 relevant hashtags at the end.

    PROMPT: "{user_prompt}"
    
    LINKEDIN POST:
    """
    prompt_template = PromptTemplate(template=template, input_variables=["user_name", "user_prompt"])
    llm_chain = LLMChain(prompt=prompt_template, llm=llm)

    try:
        generated_text = llm_chain.run(user_name=user.name, user_prompt=post_data.prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI content generation failed: {str(e)}")

    post_url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {user.access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    post_body = {
        "author": f"urn:li:person:{user.linkedin_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": generated_text
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    try:
        response = requests.post(post_url, headers=headers, json=post_body)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to post to LinkedIn: {e.response.text}")

    return {
        "status": "success",
        "message": "Post successfully created and published on LinkedIn.",
        "linkedin_response": response.json()
    }
