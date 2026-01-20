"""
Pydantic Models for Request/Response Validation
Ensures type safety and data validation
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class FileFormat(str, Enum):
    """Supported file formats"""
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"


class ProcessingStatus(str, Enum):
    """Processing status for candidates"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============= Job Description Models =============

class JobDescriptionCreate(BaseModel):
    """Request model for creating/setting job description"""
    jd_text: str = Field(..., min_length=50, max_length=10000)
    position_title: Optional[str] = Field(None, max_length=200)
    
    @validator('jd_text')
    def validate_jd_text(cls, v):
        if not v.strip():
            raise ValueError("Job description cannot be empty")
        return v.strip()


class JobRequirements(BaseModel):
    """Parsed job requirements"""
    skills: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    experience_years: Optional[int] = None
    keywords: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)


class JobDescriptionResponse(BaseModel):
    """Response model for job description"""
    id: int
    jd_text: str
    position_title: Optional[str]
    requirements: JobRequirements
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============= Candidate Models =============

class CandidateCreate(BaseModel):
    """Request model for creating candidate"""
    name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    experience_years: Optional[str] = None
    current_location: Optional[str] = Field(None, max_length=200)
    notice_period: Optional[str] = Field(None, max_length=100)
    
    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()
    
    @validator('phone')
    def validate_phone(cls, v):
        # Remove common phone number characters
        cleaned = ''.join(c for c in v if c.isdigit() or c in ['+', '-', '(', ')'])
        if len(cleaned) < 10:
            raise ValueError("Phone number must have at least 10 digits")
        return cleaned


class ScoringBreakdown(BaseModel):
    """Detailed scoring breakdown"""
    skills_match: float = Field(..., ge=0, le=100)
    experience_match: float = Field(..., ge=0, le=100)
    education_match: float = Field(..., ge=0, le=100)
    keywords_match: float = Field(..., ge=0, le=100)
    overall_score: float = Field(..., ge=0, le=100)


class ScoringExplanation(BaseModel):
    """AI-generated explanations for scores"""
    skills: str
    experience: str
    education: str
    keywords: str
    overall: str
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)


class ExtractedInfo(BaseModel):
    """Information extracted from resume"""
    contact_info: Dict[str, Optional[str]] = Field(default_factory=dict)
    skills: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    experience_years: Optional[int] = None
    certifications: List[str] = Field(default_factory=list)


class CandidateResponse(BaseModel):
    """Response model for candidate (list view)"""
    id: int
    rank: Optional[int] = None
    name: str
    email: str
    phone: str
    experience_years: Optional[str]
    current_location: Optional[str]
    notice_period: Optional[str]
    overall_score: float
    skills_match: float
    experience_match: float
    education_match: float
    keywords_match: float
    upload_date: datetime
    resume_filename: str
    status: ProcessingStatus
    
    class Config:
        from_attributes = True


class CandidateDetailResponse(CandidateResponse):
    """Detailed candidate response including full data"""
    resume_text: str
    extracted_info: Optional[ExtractedInfo] = None
    scoring_breakdown: ScoringBreakdown
    scoring_explanation: Optional[ScoringExplanation] = None
    
    class Config:
        from_attributes = True


# ============= Upload Response Models =============

class UploadResponse(BaseModel):
    """Response after uploading a candidate"""
    success: bool
    message: str
    candidate_id: int
    scores: ScoringBreakdown
    explanation: Optional[ScoringExplanation] = None


class BatchUploadResult(BaseModel):
    """Result for single file in batch upload"""
    filename: str
    success: bool
    candidate_id: Optional[int] = None
    scores: Optional[ScoringBreakdown] = None
    error: Optional[str] = None


class BatchUploadResponse(BaseModel):
    """Response for batch upload"""
    total_files: int
    successful: int
    failed: int
    results: List[BatchUploadResult]


# ============= Statistics Models =============

class Statistics(BaseModel):
    """System statistics"""
    total_candidates: int
    average_score: float
    top_score: float
    lowest_score: float
    jd_set: bool
    total_processed_today: int
    score_distribution: Dict[str, int] = Field(default_factory=dict)


# ============= Error Models =============

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# ============= Health Check =============

class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    app_name: str
    version: str
    groq_api_available: bool
    ocr_available: bool
    database_connected: bool