import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    AD_SERVER = os.getenv("AD_SERVER")
    AD_USER = os.getenv("AD_USER")
    AD_PASSWORD = os.getenv("AD_PASSWORD")
    AD_BASE_DN = os.getenv("AD_BASE_DN")
    AD_GROUP_FILTER = os.getenv("AD_GROUP_FILTER", "AWS_*")
