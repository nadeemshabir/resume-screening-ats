"""
Tests for file processor service
"""
import pytest
from app.services.file_processor import FileProcessor


class TestFileProcessor:
    """Test cases for FileProcessor class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.processor = FileProcessor()
    
    def test_get_extension_pdf(self):
        """Test PDF extension extraction"""
        ext = self.processor.get_file_extension("test_resume.pdf")
        assert ext == ".pdf"
    
    def test_get_extension_docx(self):
        """Test DOCX extension extraction"""
        ext = self.processor.get_file_extension("document.docx")
        assert ext == ".docx"
    
    def test_get_extension_uppercase(self):
        """Test uppercase extension handling"""
        ext = self.processor.get_file_extension("RESUME.PDF")
        assert ext == ".pdf"
    
    def test_get_extension_no_extension(self):
        """Test file without extension"""
        ext = self.processor.get_file_extension("noextension")
        assert ext == ""
    
    def test_allowed_extensions(self):
        """Test that allowed extensions are configured"""
        assert ".pdf" in self.processor.allowed_extensions
        assert ".docx" in self.processor.allowed_extensions
        assert ".jpg" in self.processor.allowed_extensions


class TestFileValidation:
    """Test file validation logic"""
    
    def setup_method(self):
        self.processor = FileProcessor()
    
    def test_validate_internal_extension(self):
        """Test internal extension validation"""
        assert self.processor._get_extension("resume.pdf") == ".pdf"
        assert self.processor._get_extension("resume.doc") == ".doc"
        assert self.processor._get_extension("image.png") == ".png"
