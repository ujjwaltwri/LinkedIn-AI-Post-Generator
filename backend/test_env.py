import os
from dotenv import load_dotenv, find_dotenv

# Load the .env file
load_dotenv(find_dotenv())

# Get the variables
client_id = os.getenv("LINKEDIN_CLIENT_ID")
client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")

# Print what was found
print("--- Environment Test ---")
print(f"Client ID found: {client_id}")
print(f"Client Secret found: {client_secret}")
print("------------------------")