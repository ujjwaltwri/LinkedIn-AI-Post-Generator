import os
import requests
import secrets
import urllib.parse
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path

from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from . import models, database

models.Base.metadata.create_all(bind=database.engine)

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    linkedin_client_id: str
    linkedin_client_secret: str
    google_api_key: str
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH)

settings = Settings()
REDIRECT_URI = "http://127.0.0.1:8000/auth/callback"

app = FastAPI()

origins = ["http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

class PostCreate(BaseModel):
    user_id: int
    prompt: str

# --- NEW: Pydantic model for displaying User data ---
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    linkedin_id: str
    class Config:
        orm_mode = True

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Influence OS Agent Backend is running."}

@app.get("/login/linkedin")
def login_linkedin():
    state = secrets.token_urlsafe(16)
    scopes = "profile email openid w_member_social"
    auth_url = (f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={settings.linkedin_client_id}&redirect_uri={REDIRECT_URI}&scope={scopes}&state={state}")
    return RedirectResponse(url=auth_url)

@app.get("/auth/callback")
def auth_callback(code: Optional[str] = Query(None), db: Session = Depends(get_db)):
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")
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

        print("\n--- DEBUG: PROFILE DATA RECEIVED ---")
        print(profile_data)
        
        db_user = db.query(models.User).filter(models.User.linkedin_id == profile_data["sub"]).first()
        if db_user:
            print(f"--- DEBUG: Updating existing user with ID: {db_user.id} ---")
            db_user.access_token = access_token
        else:
            print("--- DEBUG: Creating new user ---")
            db_user = models.User(linkedin_id=profile_data["sub"], email=profile_data["email"], name=profile_data["name"], access_token=access_token)
            db.add(db_user)
        
        db.commit()
        db.refresh(db_user)
        print(f"--- DEBUG: User saved/updated. DB User ID is: {db_user.id} ---\n")
        
        user_name_encoded = urllib.parse.quote(db_user.name)
        frontend_url = f"http://localhost:5173?user_id={db_user.id}&name={user_name_encoded}"
        return RedirectResponse(url=frontend_url)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# --- NEW: Endpoint to view all users in the database ---
@app.get("/users", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db)):
    """
    Retrieves all users from the database for debugging purposes.
    """
    users = db.query(models.User).all()
    return users

@app.post("/posts/create")
def create_linkedin_post(post_data: PostCreate, db: Session = Depends(get_db)):
    print("\n--- DEBUG: /posts/create called ---")
    print(f"--- DEBUG: Received request for user_id: {post_data.user_id} ---")
    
    user = db.query(models.User).filter(models.User.id == post_data.user_id).first()
    if not user:
        print("--- DEBUG: User not found in database! ---")
        raise HTTPException(status_code=404, detail="User not found")
    
    print(f"--- DEBUG: Found user '{user.name}' in database. ---")
    
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=settings.google_api_key)
    template = "You are an expert LinkedIn thought leader writing for {user_name}. Your tone should be professional, insightful, and engaging. Based on the following prompt, write a LinkedIn post. The post should be concise, well-structured, and include 3-5 relevant hashtags at the end.\n\nPROMPT: \"{user_prompt}\"\n\nLINKEDIN POST:"
    prompt_template = PromptTemplate(template=template, input_variables=["user_name", "user_prompt"])
    llm_chain = LLMChain(prompt=prompt_template, llm=llm)
    generated_text = llm_chain.run(user_name=user.name, user_prompt=post_data.prompt)
    post_url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {"Authorization": f"Bearer {user.access_token}", "Content-Type": "application/json", "X-Restli-Protocol-Version": "2.0.0"}
    post_body = {"author": f"urn:li:person:{user.linkedin_id}", "lifecycleState": "PUBLISHED", "specificContent": {"com.linkedin.ugc.ShareContent": {"shareCommentary": {"text": generated_text}, "shareMediaCategory": "NONE"}}, "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}}
    response = requests.post(post_url, headers=headers, json=post_body)
    response.raise_for_status()
    return {"status": "success", "message": "Post successfully created and published on LinkedIn.", "linkedin_response": response.json()}
