import os
from dotenv import load_dotenv

load_dotenv()

class GLOBAL_SETTINGS:
    ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")
    DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"


SETTINGS = GLOBAL_SETTINGS()
