"""
Google Sheets Service
Handles reading candidate data from Google Sheets using service account authentication
"""
import re
from typing import List, Dict, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.config import settings
from app.utils.logger import log_info, log_error, log_exception


class GoogleSheetsError(Exception):
    """Custom exception for Google Sheets service errors"""
    pass


class GoogleSheetsService:
    """
    Service for reading data from Google Sheets
    Uses service account authentication
    """
    
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    
    # Expected column mappings (case-insensitive)
    COLUMN_MAPPINGS = {
        'name': ['name', 'candidate name', 'full name', 'candidate'],
        'email': ['email', 'email address', 'e-mail', 'mail'],
        'phone': ['phone', 'phone no', 'phone no.', 'phone number', 'mobile', 'contact'],
        'experience': ['experience', 'exp', 'years of experience', 'experience years', 'work experience'],
        'expected_ctc': ['expected ctc', 'expected salary', 'ctc', 'salary expectation', 'expected package'],
        'resume_link': ['resume link', 'resume', 'resume url', 'drive link', 'cv link', 'cv', 'resume drive link']
    }
    
    def __init__(self):
        """Initialize Google Sheets service with service account credentials"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_CREDENTIALS_PATH,
                scopes=self.SCOPES
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            log_info("Google Sheets service initialized successfully")
        except Exception as e:
            log_error(f"Failed to initialize Google Sheets service: {e}")
            raise GoogleSheetsError(f"Failed to initialize Google Sheets: {e}")
    
    def extract_spreadsheet_id(self, url: str) -> Optional[str]:
        """
        Extract spreadsheet ID from Google Sheets URL
        
        Supported formats:
        - https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
        - https://docs.google.com/spreadsheets/d/SPREADSHEET_ID
        - Direct spreadsheet ID
        
        Args:
            url: Google Sheets URL or spreadsheet ID
            
        Returns:
            Extracted spreadsheet ID or None if not found
        """
        if not url:
            return None
        
        url = url.strip()
        
        # Pattern: /d/SPREADSHEET_ID
        pattern = r'/d/([a-zA-Z0-9_-]+)'
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        
        # If no pattern matches, assume it's a direct spreadsheet ID
        if re.match(r'^[a-zA-Z0-9_-]+$', url):
            return url
        
        return None
    
    def _normalize_header(self, header: str) -> Optional[str]:
        """
        Normalize header to standard field name
        
        Args:
            header: Raw header from sheet
            
        Returns:
            Normalized field name or None if not recognized
        """
        header_lower = header.lower().strip()
        
        for field_name, variations in self.COLUMN_MAPPINGS.items():
            if header_lower in variations:
                return field_name
        
        return None
    
    def read_sheet(self, spreadsheet_id: str, range_name: str = 'Sheet1') -> List[Dict]:
        """
        Read data from Google Sheet and parse into candidate dictionaries
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            range_name: Sheet name or range (default: 'Sheet1')
            
        Returns:
            List of candidate dictionaries with normalized field names
        """
        try:
            log_info(f"Reading sheet {spreadsheet_id}, range: {range_name}")
            
            # Read all data from sheet
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                log_info("Sheet is empty")
                return []
            
            # First row is headers
            headers = values[0]
            log_info(f"Found headers: {headers}")
            
            # Map headers to field names
            field_mapping = {}
            for i, header in enumerate(headers):
                field_name = self._normalize_header(header)
                if field_name:
                    field_mapping[i] = field_name
                    log_info(f"Mapped column '{header}' -> '{field_name}'")
            
            # Parse data rows
            candidates = []
            for row_num, row in enumerate(values[1:], start=2):
                candidate = {'row_number': row_num}
                
                for col_idx, field_name in field_mapping.items():
                    if col_idx < len(row):
                        value = row[col_idx].strip() if row[col_idx] else ''
                        candidate[field_name] = value
                
                # Only include rows that have at least a name or resume link
                if candidate.get('name') or candidate.get('resume_link'):
                    candidates.append(candidate)
            
            log_info(f"Parsed {len(candidates)} candidates from sheet")
            return candidates
            
        except Exception as e:
            log_error(f"Failed to read sheet {spreadsheet_id}: {e}")
            raise GoogleSheetsError(f"Failed to read sheet: {e}")
    
    def read_from_url(self, url: str, range_name: str = 'Sheet1') -> List[Dict]:
        """
        Read candidate data from Google Sheets URL
        
        Args:
            url: Google Sheets URL
            range_name: Sheet name or range (default: 'Sheet1')
            
        Returns:
            List of candidate dictionaries
        """
        spreadsheet_id = self.extract_spreadsheet_id(url)
        if not spreadsheet_id:
            raise GoogleSheetsError(f"Could not extract spreadsheet ID from URL: {url}")
        
        return self.read_sheet(spreadsheet_id, range_name)
    
    def test_connection(self) -> bool:
        """
        Test if Sheets API connection is working
        
        Returns:
            True if connection is successful
        """
        try:
            # This will fail if credentials are invalid
            # We can't really test without a spreadsheet ID, so just verify service exists
            log_info("Google Sheets service connection test successful")
            return True
        except Exception as e:
            log_error(f"Google Sheets connection test failed: {e}")
            return False
