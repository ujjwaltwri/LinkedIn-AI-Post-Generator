import os
import requests
import secrets
import urllib.parse
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import RedirectResponse
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel
from typing import Optional
from pathlib import Path

from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
# Use absolute imports for Render deployment
from . import models,database

models.Base.metadata.create_all(bind=database.engine)

# This configuration explicitly tells the server where to find the .env file
class Settings(BaseSettings):
    linkedin_client_id: str
    linkedin_client_secret: str
    google_api_key: str
    
    # For Render, it will use environment variables.
    # For local, it will look for a file named '.env' in the 'backend' folder.
    model_config = SettingsConfigDict(env_file="backend/.env")

settings = Settings()
# Use the live Render URLs for the final version
REDIRECT_URI = "https://influence-os-project.onrender.com/auth/callback"
FRONTEND_URL = "https://influence-os-frontend.onrender.com"

app = FastAPI(
    title="Influence OS Agent Backend",
    description="Backend API for LinkedIn OAuth and AI Content Generation",
    version="1.0.0"
)

# Allow the live frontend to communicate with the backend
origins = [FRONTEND_URL]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

class PostCreate(BaseModel):
    prompt: str
    access_token: str
    linkedin_id: str
    user_name: str

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/login/linkedin")
def login_linkedin():
    state = secrets.token_urlsafe(16)
    scopes = "profile email openid w_member_social"
    auth_url = (f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={settings.linkedin_client_id}&redirect_uri={REDIRECT_URI}&scope={scopes}&state={state}")
    return RedirectResponse(url=auth_url)

@app.get("/auth/callback")
def auth_callback(code: Optional[str] = Query(None), db: Session = Depends(get_db)):
    try:
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        data = {"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI, "client_id": settings.linkedin_client_id, "client_secret": settings.linkedin_client_secret}
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        token_json = response.json()
        access_token = token_json.get("access_token")

        profile_response = requests.get("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {access_token}"})
        profile_response.raise_for_status()
        profile_data = profile_response.json()
        
        user_name_encoded = urllib.parse.quote(profile_data["name"])
        linkedin_id = profile_data["sub"]
        
        # Redirect to frontend with all necessary info
        final_frontend_url = f"{FRONTEND_URL}?name={user_name_encoded}&access_token={access_token}&linkedin_id={linkedin_id}"
        return RedirectResponse(url=final_frontend_url)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.post("/posts/create")
def create_linkedin_post(post_data: PostCreate):
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=settings.google_api_key)
    template = "You are an expert LinkedIn thought leader writing for {user_name}. Your tone should be professional and insightful. Based on the following prompt, write a concise LinkedIn post with 3-5 relevant hashtags.\n\nPROMPT: \"{user_prompt}\"\n\nLINKEDIN POST:"
    prompt_template = PromptTemplate(template=template, input_variables=["user_name", "user_prompt"])
    llm_chain = LLMChain(prompt=prompt_template, llm=llm)
    
    generated_text = llm_chain.run(user_name=post_data.user_name, user_prompt=post_data.prompt)

    post_url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {"Authorization": f"Bearer {post_data.access_token}", "Content-Type": "application/json", "X-Restli-Protocol-Version": "2.0.0"}
    post_body = {
        "author": f"urn:li:person:{post_data.linkedin_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": {"shareCommentary": {"text": generated_text}, "shareMediaCategory": "NONE"}},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    
    response = requests.post(post_url, headers=headers, json=post_body)
    response.raise_for_status()
    return {"status": "success", "message": "Post successfully created and published on LinkedIn.", "linkedin_response": response.json()}
