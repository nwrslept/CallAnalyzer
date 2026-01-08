import os
import google.auth
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from src.config import Config


class DriveService:
    """
    Клас для взаємодії з Google Drive API.
    Відповідає за авторизацію через Service Account, пошук та завантаження файлів.
    """

    def __init__(self):
        # Визначаємо область доступу (Scopes) для роботи з Drive
        SCOPES = ['https://www.googleapis.com/auth/drive']

        # Завантаження облікових даних із файлу сервісного акаунту
        self.creds = service_account.Credentials.from_service_account_file(
            Config.GOOGLE_CREDENTIALS_FILE,
            scopes=SCOPES
        )

        # Перевірка валідності токена та його оновлення за потреби
        if not self.creds.valid:
            self.creds.refresh(Request())

        # Ініціалізація клієнта API версії v3
        self.service = build('drive', 'v3', credentials=self.creds)

    def list_audio_files(self, folder_id: str) -> list:
        """
        Отримує список аудіофайлів (.mp3, .wav) із вказаної папки Google Drive.
        Фільтрує файли за MIME-типом або розширенням, ігноруючи кошик.
        """
        # Формування пошукового запиту (Q parameter)
        query = (
            f"'{folder_id}' in parents and "
            f"(mimeType contains 'audio/' or name contains '.mp3' or name contains '.wav') "
            f"and trashed=false"
        )

        # Виконання запиту до API
        results = self.service.files().list(
            q=query,
            fields="files(id, name)"  # Оптимізація: отримуємо лише ID та назву
        ).execute()

        return results.get('files', [])

    def download_file(self, file_id: str, file_name: str) -> str:
        """
        Завантажує файл за ID у локальну тимчасову директорію.
        Повертає абсолютний або відносний шлях до збереженого файлу.
        """
        # Створення запиту на отримання медіа-вмісту файлу
        request = self.service.files().get_media(fileId=file_id)

        # Формування локального шляху для збереження
        local_path = os.path.join(Config.TEMP_FOLDER, file_name)

        # Створення локальної папки, якщо вона відсутня
        os.makedirs(Config.TEMP_FOLDER, exist_ok=True)

        # Запис бінарних даних у файл
        with open(local_path, "wb") as f:
            f.write(request.execute())

        return local_path
