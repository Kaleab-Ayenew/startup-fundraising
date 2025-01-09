import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file

ADMIN_CREATION_TOKEN = os.getenv("ADMIN_CREATION_TOKEN", "changeme")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/fundraising")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STATIC_FILES_DIR = os.getenv("STATIC_FILES_DIR")
HOST_ADDRESS= os.getenv("HOST_ADDRESS")