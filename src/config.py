import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    GOOGLE_CREDENTIALS_FILE = "service_account.json"
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


    SOURCE_FOLDER_ID = "1dpKG-eaFg2glOovkI4sYgLyPo3mW9Ilg"

    WORK_FOLDER_ID = "16-wguVrApMKUKqSpTGQP7b7NgWA7b0vU"

    SHEET_ID = "16I6nqmaD-AjkKF7sQWWQPRn0xnVdS9HBbwBFTe-_y0U"
