"""
Google Drive Service
Handles downloading files from Google Drive using service account authentication
"""
import io
import re
from typing import Optional, Tuple
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.config import settings
from app.utils.logger import log_info, log_error, log_exception


class GoogleDriveError(Exception):
    """Custom exception for Google Drive service errors"""
    pass


class GoogleDriveService:
    """
    Service for downloading files from Google Drive
    Uses service account authentication
    """
    
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    def __init__(self):
        """Initialize Google Drive service with service account credentials"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_CREDENTIALS_PATH,
                scopes=self.SCOPES
            )
            self.service = build('drive', 'v3', credentials=credentials)
            log_info("Google Drive service initialized successfully")
        except Exception as e:
            log_error(f"Failed to initialize Google Drive service: {e}")
            raise GoogleDriveError(f"Failed to initialize Google Drive: {e}")
    
    def extract_file_id(self, url: str) -> Optional[str]:
        """
        Extract file ID from various Google Drive URL formats
        
        Supported formats:
        - https://drive.google.com/file/d/FILE_ID/view
        - https://drive.google.com/open?id=FILE_ID
        - https://docs.google.com/document/d/FILE_ID/edit
        - https://drive.google.com/uc?id=FILE_ID
        - Direct file ID
        
        Args:
            url: Google Drive URL or file ID
            
        Returns:
            Extracted file ID or None if not found
        """
        if not url:
            return None
        
        url = url.strip()
        
        # Pattern 1: /d/FILE_ID/
        pattern1 = r'/d/([a-zA-Z0-9_-]+)'
        match = re.search(pattern1, url)
        if match:
            return match.group(1)
        
        # Pattern 2: id=FILE_ID
        pattern2 = r'id=([a-zA-Z0-9_-]+)'
        match = re.search(pattern2, url)
        if match:
            return match.group(1)
        
        # If no patterns match, assume it's a direct file ID
        if re.match(r'^[a-zA-Z0-9_-]+$', url):
            return url
        
        return None
    
    def get_file_metadata(self, file_id: str) -> dict:
        """
        Get file metadata from Google Drive
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            Dictionary with file name and MIME type
        """
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields='name, mimeType, size'
            ).execute()
            
            log_info(f"Retrieved metadata for file: {file.get('name')}")
            return {
                'name': file.get('name'),
                'mime_type': file.get('mimeType'),
                'size': file.get('size')
            }
        except Exception as e:
            log_error(f"Failed to get file metadata for {file_id}: {e}")
            raise GoogleDriveError(f"Failed to get file metadata: {e}")
    
    def download_file(self, file_id: str) -> Tuple[bytes, str]:
        """
        Download file content from Google Drive
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            Tuple of (file content bytes, filename)
        """
        try:
            # Get file metadata first
            metadata = self.get_file_metadata(file_id)
            filename = metadata.get('name', 'unknown.pdf')
            
            log_info(f"Downloading file: {filename} (ID: {file_id})")
            
            # Download file content
            request = self.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    log_info(f"Download progress: {int(status.progress() * 100)}%")
            
            file_content = file_buffer.getvalue()
            log_info(f"Successfully downloaded {filename} ({len(file_content)} bytes)")
            
            return file_content, filename
            
        except Exception as e:
            log_error(f"Failed to download file {file_id}: {e}")
            raise GoogleDriveError(f"Failed to download file: {e}")
    
    def download_from_url(self, url: str) -> Tuple[bytes, str]:
        """
        Download file from Google Drive URL
        
        Args:
            url: Google Drive URL
            
        Returns:
            Tuple of (file content bytes, filename)
        """
        file_id = self.extract_file_id(url)
        if not file_id:
            raise GoogleDriveError(f"Could not extract file ID from URL: {url}")
        
        return self.download_file(file_id)
    
    def test_connection(self) -> bool:
        """
        Test if Drive API connection is working
        
        Returns:
            True if connection is successful
        """
        try:
            # Try to list files (limited to 1) to verify access
            self.service.files().list(pageSize=1).execute()
            log_info("Google Drive connection test successful")
            return True
        except Exception as e:
            log_error(f"Google Drive connection test failed: {e}")
            return False
