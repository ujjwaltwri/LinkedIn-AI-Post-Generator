LinkedIn AI Post Generator
An autonomous AI agent that uses generative AI to create and publish engaging content for personal branding on LinkedIn. This project was developed as a full-stack application demonstrating secure authentication, AI integration, and automated social media workflows.

🚀 Live Demo
You can try the live application here:

https://linkedin-ai-post-generator.onrender.com

✨ Features
Secure LinkedIn Authentication: Connect your LinkedIn account securely using the official OAuth 2.0 protocol.

AI-Powered Content Generation: Provide a simple prompt, and the agent uses Google's Gemini model to write a professional and engaging LinkedIn post.

Automated Posting: Publish the AI-generated content directly to your LinkedIn profile with a single click.

Decoupled Architecture: Built with a modern full-stack architecture, featuring a React frontend and a FastAPI backend.

🛠️ Tech Stack
Backend: Python, FastAPI, SQLAlchemy, LangChain

Frontend: React, Vite

Database: PostgreSQL (hosted on Supabase)

AI Model: Google Gemini 1.5 Flash

Deployment: Render (for both backend and frontend)

⚙️ Setup and Installation
To run this project on your local machine, follow these steps.

Prerequisites

Python 3.9+

Node.js and npm

A LinkedIn Developer App with a Client ID and Secret

A Google AI API Key

A Supabase account for a PostgreSQL database

1. Clone the Repository

git clone https://github.com/ujjwaltwri/LinkedIn-AI-Post-Generator.git
cd LinkedIn-AI-Post-Generator

2. Backend Setup

# Navigate to the backend directory
cd backend

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the required Python libraries
pip install -r requirements.txt

3. Frontend Setup

# Navigate to the frontend directory
cd frontend

# Install the required npm packages
npm install

4. Environment Variables

Create a file named .env inside the backend directory and add the following keys:

LINKEDIN_CLIENT_ID="YOUR_LINKEDIN_CLIENT_ID"
LINKEDIN_CLIENT_SECRET="YOUR_LINKEDIN_CLIENT_SECRET"
GOOGLE_API_KEY="YOUR_GOOGLE_AI_API_KEY"
DATABASE_URL="YOUR_SUPABASE_POSTGRESQL_URI"

🏃 Running Locally
You will need to run the backend and frontend servers in two separate terminal windows.

To run the backend server:

Navigate to the main project directory (LinkedIn-AI-Post-Generator).

Run: uvicorn backend.main:app --reload

To run the frontend server:

Navigate to the frontend directory.

Run: npm run dev

The frontend will be available at http://localhost:5173 and the backend at http://localhost:8000.

