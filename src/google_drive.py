import os
import io
import shutil
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from src.config import Config


class DriveService:
    """
    Handles all interactions with Google Drive API:
    - Listing files
    - Downloading audio
    - Copying files between folders
    - Uploading transcripts
    """

    def __init__(self):
        self.creds = service_account.Credentials.from_service_account_file(
            Config.GOOGLE_CREDENTIALS_FILE,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        self.service = build('drive', 'v3', credentials=self.creds)

    def list_audio_files(self, folder_id: str) -> list:
        """
        Scans the specific Google Drive folder for audio files.
        Returns a list of file objects (id, name).
        """
        print(f"DEBUG: Scanning folder {folder_id}...")
        try:
            query = f"'{folder_id}' in parents and trashed = false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType)",
                pageSize=100
            ).execute()

            files = results.get('files', [])
            audio_extensions = ('.mp3', '.wav', '.m4a', '.ogg')
            audio_files = [f for f in files if f['name'].lower().endswith(audio_extensions)]

            print(f"DEBUG: Found {len(audio_files)} audio files.")
            return audio_files
        except Exception as e:
            print(f"ERROR: Failed to list files. Reason: {e}")
            return []

    def download_file(self, file_id: str, file_name: str) -> str:
        """
        Downloads a file from Drive to the local 'temp' folder.
        Returns the local path to the downloaded file.
        """
        local_folder = "temp_audio"
        if not os.path.exists(local_folder):
            os.makedirs(local_folder)

        local_path = os.path.join(local_folder, file_name)

        if os.path.exists(local_path):
            print(f"DEBUG: File {file_name} already exists locally. Skipping download.")
            return local_path

        print(f"DEBUG: Downloading {file_name}...")
        request = self.service.files().get_media(fileId=file_id)
        fh = io.FileIO(local_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while done is False:
            status, done = downloader.next_chunk()

        print(f"DEBUG: Download complete: {local_path}")
        return local_path

    def copy_file_to_work_folder(self, file_id: str, destination_folder_id: str) -> str:
        """
        Copies a file from the Source Folder to the Work Folder.
        Requirements state: 'Transfer them to your working Google Doc folder'.
        Returns the new file ID in the destination folder.
        """
        try:
            file_metadata = {
                'parents': [destination_folder_id]
            }
            copied_file = self.service.files().copy(
                fileId=file_id,
                body=file_metadata,
                fields='id'
            ).execute()
            print(f"DEBUG: Copied file {file_id} to work folder.")
            return copied_file.get('id')
        except Exception as e:
            print(f"ERROR: Failed to copy file. Reason: {e}")
            return None

    def upload_text_file(self, text_content: str, file_name: str, folder_id: str):
        """
        Creates a text file with the transcription/analysis and uploads it
        to the specified Google Drive folder (Work Folder).
        Requirement: 'Transcription files should be placed next to audio files'.
        """
        try:
            local_path = "temp_transcript.txt"
            with open(local_path, "w", encoding="utf-8") as f:
                f.write(text_content)

            file_metadata = {
                'name': file_name,
                'parents': [folder_id]
            }
            media = MediaFileUpload(local_path, mimetype='text/plain')

            new_file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            print(f"DEBUG: Uploaded transcript {file_name} to Drive.")
            return new_file.get('id')
        except Exception as e:
            print(f"ERROR: Failed to upload transcript. Reason: {e}")
            return None
