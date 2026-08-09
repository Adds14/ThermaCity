import logging
import os
import io
from pathlib import Path
import glob
import json

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)

def get_drive_service():
    # Find the JSON key
    cred_dir = Path(__file__).resolve().parent.parent.parent / "credentials"
    json_keys = glob.glob(str(cred_dir / "*.json"))
    if not json_keys:
        raise FileNotFoundError("No Service Account JSON key found in credentials/")
    
    key_path = json_keys[0]
    logger.info(f"Using service account key: {key_path}")
    
    scopes = ['https://www.googleapis.com/auth/drive.readonly']
    credentials = service_account.Credentials.from_service_account_file(
        key_path, scopes=scopes)
    
    return build('drive', 'v3', credentials=credentials)

def download_csvs(out_dir: str):
    service = get_drive_service()
    
    # List all CSV files in the Drive
    results = service.files().list(
        q="mimeType='text/csv'",
        pageSize=100,
        fields="nextPageToken, files(id, name)"
    ).execute()
    items = results.get('files', [])

    if not items:
        logger.info("No CSV files found in the Service Account's Drive.")
        return

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for item in items:
        file_id = item['id']
        file_name = item['name']
        if not file_name.endswith('.csv'):
            file_name += '.csv'
            
        file_path = out_path / file_name
        logger.info(f"Downloading {file_name}...")
        
        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(file_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        logger.info(f"  Saved to {file_path}")

if __name__ == '__main__':
    out_dir = str(Path(__file__).resolve().parent.parent / "exports")
    download_csvs(out_dir)
