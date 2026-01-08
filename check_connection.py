import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from src.config import Config


def test_google_drive():
    print("--- STARTING CONNECTION TEST ---")

    try:
        creds = service_account.Credentials.from_service_account_file(
            Config.GOOGLE_CREDENTIALS_FILE,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=creds)
        print("✅ Authentication successful.")
    except Exception as e:
        print(f"❌ Authentication FAILED: {e}")
        return

    print(f"\n📂 Testing READ access to Source Folder ID: {Config.SOURCE_FOLDER_ID}...")
    try:
        results = service.files().list(
            q=f"'{Config.SOURCE_FOLDER_ID}' in parents",
            pageSize=5,
            fields="files(id, name)"
        ).execute()
        files = results.get('files', [])

        if not files:
            print("⚠️ Connection OK, but folder is empty or ID is wrong.")
        else:
            print(f"✅ Success! Found {len(files)} files:")
            for f in files:
                print(f"   - {f['name']} (ID: {f['id']})")
    except Exception as e:
        print(f"❌ READ access FAILED. Check if you shared the folder with the bot email. Error: {e}")

    print(f"\n💾 Testing WRITE access to Work Folder ID: {Config.WORK_FOLDER_ID}...")
    try:
        file_metadata = {
            'name': 'bot_connection_test.txt',
            'parents': [Config.WORK_FOLDER_ID]
        }
        # Create a dummy file
        service.files().create(body=file_metadata).execute()
        print("✅ Success! Created 'bot_connection_test.txt' in your folder.")
    except Exception as e:
        print(f"❌ WRITE access FAILED. Make sure the bot has EDITOR rights. Error: {e}")

    print("\n--- TEST FINISHED ---")


if __name__ == "__main__":
    test_google_drive()
