"""
Resume Screening API - Main Application
FastAPI application with robust error handling and validation
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
from pathlib import Path

from app.config import settings, validate_settings
from app.models.schemas import (
    HealthCheck, ErrorResponse, JobDescriptionCreate,
    CandidateCreate, UploadResponse, Statistics
)
from app.services.text_extractor import TextExtractor, TextExtractionError
from app.services.groq_service import GroqService, GroqServiceError
from app.services.google_drive_service import GoogleDriveService, GoogleDriveError
from app.services.google_sheets_service import GoogleSheetsService, GoogleSheetsError
from app.utils.logger import log_info, log_error, log_exception, app_logger


# ============= Application Lifecycle =============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown events
    Validates configuration and initializes services
    """
    log_info("="*60)
    log_info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    log_info("="*60)
    
    # Validate configuration
    try:
        validate_settings()
        log_info("✓ Configuration validated")
    except Exception as e:
        log_error(f"Configuration validation failed: {e}")
        raise
    
    # Create necessary directories
    Path(settings.UPLOAD_DIR).mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    log_info("✓ Directories created")
    
    # Test Groq connection
    try:
        groq_service = GroqService()
        if groq_service.test_connection():
            log_info("✓ Groq API connection successful")
        else:
            log_error("✗ Groq API connection failed")
    except Exception as e:
        log_error(f"✗ Groq initialization failed: {e}")
    
    # Test OCR availability
    if settings.OCR_ENABLED:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            log_info("✓ OCR (Tesseract) available")
        except Exception as e:
            log_error(f"✗ OCR not available: {e}")
    
    log_info("Application startup complete")
    log_info("="*60)
    
    yield
    
    # Shutdown
    log_info("Shutting down application...")


# ============= FastAPI App Initialization =============

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered resume screening and candidate ranking system",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============= Global Exception Handlers =============

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle all unhandled exceptions"""
    log_exception(exc, f"Unhandled exception on {request.url}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc) if settings.DEBUG else None
        ).dict()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    log_error(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=None
        ).dict()
    )


# ============= Service Instances =============

text_extractor = TextExtractor()
groq_service = GroqService()

# In-memory storage (will move to database in Phase 4)
current_jd = None
jd_requirements = None
candidates_db = []
failed_candidates = []  # Track candidates that failed to process

# Google services (initialized lazily)
google_drive_service = None
google_sheets_service = None

def get_google_services():
    """Lazily initialize Google services"""
    global google_drive_service, google_sheets_service
    if google_drive_service is None:
        google_drive_service = GoogleDriveService()
    if google_sheets_service is None:
        google_sheets_service = GoogleSheetsService()
    return google_drive_service, google_sheets_service


# ============= Helper Functions =============

def validate_file(filename: str, file_size: int) -> None:
    """Validate uploaded file"""
    # Check extension
    file_ext = Path(filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_ext} not supported. Allowed: {settings.ALLOWED_EXTENSIONS}"
        )
    
    # Check size
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE/1024/1024}MB"
        )


# ============= API Endpoints =============

@app.get("/", response_model=HealthCheck)
async def root():
    """Health check endpoint"""
    log_info("Health check requested")
    
    # Test Groq availability
    groq_available = False
    try:
        groq_available = groq_service.test_connection()
    except:
        pass
    
    # Test OCR availability
    ocr_available = False
    if settings.OCR_ENABLED:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            ocr_available = True
        except:
            pass
    
    return HealthCheck(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        groq_api_available=groq_available,
        ocr_available=ocr_available,
        database_connected=True  # Will check actual DB in Phase 4
    )


@app.post("/api/jd/set")
async def set_job_description(jd_text: str = Form(...)):
    """
    Set job description for candidate scoring
    AI will parse requirements from the JD
    """
    global current_jd, jd_requirements
    
    log_info(f"Setting job description ({len(jd_text)} chars)")
    
    # Validate JD length
    if len(jd_text.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description too short. Minimum 50 characters required."
        )
    
    if len(jd_text) > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description too long. Maximum 10,000 characters."
        )
    
    try:
        # Store JD
        current_jd = jd_text.strip()
        
        # Parse requirements using Groq AI
        jd_requirements = groq_service.parse_job_requirements(current_jd)
        
        log_info(f"JD set successfully. Found {len(jd_requirements.get('skills', []))} skills")
        
        return {
            "success": True,
            "message": "Job description set successfully",
            "requirements_found": jd_requirements
        }
        
    except GroqServiceError as e:
        log_error(f"JD parsing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse job description: {str(e)}"
        )


@app.get("/api/jd/get")
async def get_job_description():
    """Retrieve current job description"""
    if not current_jd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No job description set. Please set JD first."
        )
    
    return {
        "jd_text": current_jd,
        "requirements": jd_requirements
    }


@app.post("/api/candidates/upload", response_model=UploadResponse)
async def upload_candidate(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    experience_years: str = Form(None),
    current_location: str = Form(None),
    notice_period: str = Form(None),
    resume: UploadFile = File(...)
):
    """
    Upload and process single candidate resume
    Extracts text, scores against JD, stores in database
    """
    log_info(f"Processing candidate: {name} ({resume.filename})")
    
    # Validate JD is set
    if not current_jd:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please set job description first"
        )
    
    # Read file content
    file_content = await resume.read()
    file_size = len(file_content)
    
    # Validate file
    validate_file(resume.filename, file_size)
    
    try:
        # Extract text from resume
        log_info(f"Extracting text from {resume.filename}")
        resume_text = text_extractor.extract(file_content, resume.filename)
        
        log_info(f"Extracted {len(resume_text)} characters")
        
        # Score candidate using Groq AI
        log_info("Scoring candidate with AI")
        scores = groq_service.score_candidate(current_jd, resume_text, jd_requirements)
        
        # Create candidate record
        candidate = {
            "id": len(candidates_db) + 1,
            "name": name,
            "email": email,
            "phone": phone,
            "experience_years": experience_years,
            "current_location": current_location,
            "notice_period": notice_period,
            "resume_filename": resume.filename,
            "resume_text": resume_text,
            "upload_date": "2026-01-18T10:30:00",  # Use datetime.now() in production
            "scores": scores,
            "overall_score": scores["overall_score"],
            "skills_match": scores["skills_match"],
            "experience_match": scores["experience_match"],
            "education_match": scores["education_match"],
            "keywords_match": scores["keywords_match"],
            "status": "completed"
        }
        
        candidates_db.append(candidate)
        
        log_info(f"Candidate {name} processed successfully. Score: {scores['overall_score']}")
        
        return UploadResponse(
            success=True,
            message="Candidate processed successfully",
            candidate_id=candidate["id"],
            scores=scores,
            explanation=scores.get("explanation")
        )
        
    except TextExtractionError as e:
        log_error(f"Text extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract text from resume: {str(e)}"
        )
    
    except GroqServiceError as e:
        log_error(f"Scoring failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to score candidate: {str(e)}"
        )


@app.get("/api/candidates/list")
async def list_candidates():
    """Get all candidates ranked by score"""
    # Sort by overall score
    sorted_candidates = sorted(
        candidates_db, 
        key=lambda x: x["overall_score"], 
        reverse=True
    )
    
    # Assign ranks
    for idx, candidate in enumerate(sorted_candidates, 1):
        candidate["rank"] = idx
    
    # Return summary (without full resume text)
    candidates_summary = []
    for c in sorted_candidates:
        candidates_summary.append({
            "id": c["id"],
            "rank": c["rank"],
            "name": c["name"],
            "email": c["email"],
            "phone": c["phone"],
            "experience_years": c.get("experience_years"),
            "current_location": c.get("current_location"),
            "notice_period": c.get("notice_period"),
            "overall_score": c["overall_score"],
            "skills_match": c["skills_match"],
            "experience_match": c["experience_match"],
            "education_match": c["education_match"],
            "keywords_match": c["keywords_match"],
            "upload_date": c["upload_date"],
            "resume_filename": c["resume_filename"],
            "status": c.get("status", "completed")
        })
    
    log_info(f"Returned {len(candidates_summary)} candidates")
    
    return {
        "candidates": candidates_summary,
        "total": len(candidates_summary)
    }


@app.get("/api/candidates/{candidate_id}")
async def get_candidate_details(candidate_id: int):
    """Get full candidate details including resume text and scoring"""
    candidate = next((c for c in candidates_db if c["id"] == candidate_id), None)
    
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate with ID {candidate_id} not found"
        )
    
    log_info(f"Retrieved details for candidate {candidate_id}")
    return candidate


@app.delete("/api/candidates/{candidate_id}")
async def delete_candidate(candidate_id: int):
    """Delete a candidate"""
    global candidates_db
    
    initial_count = len(candidates_db)
    candidates_db = [c for c in candidates_db if c["id"] != candidate_id]
    
    if len(candidates_db) == initial_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate with ID {candidate_id} not found"
        )
    
    log_info(f"Deleted candidate {candidate_id}")
    
    return {
        "success": True,
        "message": f"Candidate {candidate_id} deleted successfully"
    }


@app.get("/api/stats", response_model=Statistics)
async def get_statistics():
    """Get system statistics"""
    if not candidates_db:
        return Statistics(
            total_candidates=0,
            average_score=0.0,
            top_score=0.0,
            lowest_score=0.0,
            jd_set=current_jd is not None,
            total_processed_today=0,
            score_distribution={}
        )
    
    scores = [c["overall_score"] for c in candidates_db]
    
    # Score distribution
    distribution = {
        "90-100": len([s for s in scores if s >= 90]),
        "80-89": len([s for s in scores if 80 <= s < 90]),
        "70-79": len([s for s in scores if 70 <= s < 80]),
        "60-69": len([s for s in scores if 60 <= s < 70]),
        "0-59": len([s for s in scores if s < 60]),
    }
    
    return Statistics(
        total_candidates=len(candidates_db),
        average_score=round(sum(scores) / len(scores), 2),
        top_score=max(scores),
        lowest_score=min(scores),
        jd_set=current_jd is not None,
        total_processed_today=len(candidates_db),  # Will track by date in DB
        score_distribution=distribution
    )


@app.delete("/api/candidates/clear")
async def clear_all_candidates():
    """Clear all candidates (useful for testing)"""
    global candidates_db
    count = len(candidates_db)
    candidates_db = []
    
    log_info(f"Cleared {count} candidates")
    
    return {
        "success": True,
        "message": f"Cleared {count} candidates"
    }


# ============= Google Sheets Integration Endpoints =============

@app.post("/api/sheets/upload")
async def upload_and_process_sheet(
    sheet_file: UploadFile = File(...)
):
    """
    Upload and process Google Sheet file (Excel/CSV) with candidate data and Drive resume links.
    
    1. Parse uploaded file (Excel or CSV)
    2. For each candidate: extract resume link, download from Drive, process with AI
    3. Track failures for manual handling
    4. Return processing results
    """
    global failed_candidates
    
    log_info(f"Processing uploaded sheet: {sheet_file.filename}")
    
    # Validate JD is set
    if not current_jd:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please set job description first"
        )
    
    # Validate file type
    filename = sheet_file.filename.lower()
    if not (filename.endswith('.xlsx') or filename.endswith('.xls') or filename.endswith('.csv')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload an Excel (.xlsx, .xls) or CSV file"
        )
    
    # Read file content
    file_content = await sheet_file.read()
    
    # Parse the file
    try:
        import io
        import pandas as pd
        
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(file_content))
        else:
            df = pd.read_excel(io.BytesIO(file_content))
        
        log_info(f"Parsed {len(df)} rows from {sheet_file.filename}")
        
        # Normalize column names (lowercase, replace spaces with underscores)
        df.columns = [col.lower().strip().replace(' ', '_').replace('.', '') for col in df.columns]
        
        log_info(f"Columns found: {list(df.columns)}")
        
    except Exception as e:
        log_error(f"Failed to parse sheet: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse file: {str(e)}"
        )
    
    # Column mapping
    column_map = {
        'name': ['name', 'candidate_name', 'full_name', 'candidate'],
        'email': ['email', 'email_address', 'e-mail', 'mail'],
        'phone': ['phone', 'phone_no', 'phone_number', 'mobile', 'contact'],
        'experience': ['experience', 'exp', 'years_of_experience', 'experience_years', 'work_experience'],
        'expected_ctc': ['expected_ctc', 'expected_salary', 'ctc', 'salary_expectation', 'expected_package'],
        'resume_link': ['resume_link', 'resume', 'resume_url', 'drive_link', 'cv_link', 'cv', 'resume_drive_link']
    }
    
    def find_column(df, possible_names):
        for name in possible_names:
            if name in df.columns:
                return name
        return None
    
    # Find actual column names
    col_name = find_column(df, column_map['name'])
    col_email = find_column(df, column_map['email'])
    col_phone = find_column(df, column_map['phone'])
    col_exp = find_column(df, column_map['experience'])
    col_ctc = find_column(df, column_map['expected_ctc'])
    col_resume = find_column(df, column_map['resume_link'])
    
    if not col_resume:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not find 'Resume Link' column. Make sure your sheet has a column named: Resume Link, Resume, Drive Link, or CV Link"
        )
    
    # Initialize Google Drive service
    try:
        drive_service, _ = get_google_services()
    except (GoogleDriveError, GoogleSheetsError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize Google Drive service: {str(e)}"
        )
    
    # Process each row
    success_count = 0
    fail_count = 0
    failed_candidates = []  # Reset
    
    from datetime import datetime
    
    for idx, row in df.iterrows():
        row_number = idx + 2  # +2 because row 1 is header, and idx is 0-based
        candidate_name = str(row.get(col_name, 'Unknown')) if col_name else 'Unknown'
        resume_link = str(row.get(col_resume, '')) if col_resume else ''
        
        log_info(f"Processing candidate: {candidate_name} (Row {row_number})")
        
        # Get optional fields
        email = str(row.get(col_email, '')) if col_email else ''
        phone = str(row.get(col_phone, '')) if col_phone else ''
        experience = str(row.get(col_exp, '')) if col_exp else ''
        expected_ctc = str(row.get(col_ctc, '')) if col_ctc else ''
        
        # Check if resume link exists
        if not resume_link or resume_link == 'nan' or pd.isna(row.get(col_resume)):
            log_error(f"No resume link for {candidate_name}")
            failed_candidates.append({
                "row_number": row_number,
                "name": candidate_name,
                "email": email,
                "phone": phone,
                "experience": experience,
                "expected_ctc": expected_ctc,
                "resume_link": "",
                "error": "No resume link provided",
                "status": "failed"
            })
            fail_count += 1
            continue
        
        try:
            # Download resume from Drive
            log_info(f"Downloading resume from: {resume_link}")
            file_content_resume, filename = drive_service.download_from_url(resume_link)
            
            # Extract text from resume
            log_info(f"Extracting text from {filename}")
            resume_text = text_extractor.extract(file_content_resume, filename)
            
            # Score candidate
            log_info(f"Scoring candidate {candidate_name}")
            scores = groq_service.score_candidate(current_jd, resume_text, jd_requirements)
            
            # Create candidate record
            candidate = {
                "id": len(candidates_db) + 1,
                "name": candidate_name,
                "email": email,
                "phone": phone,
                "experience_years": experience,
                "expected_ctc": expected_ctc,
                "current_location": "",
                "notice_period": "",
                "resume_filename": filename,
                "resume_text": resume_text,
                "upload_date": datetime.now().isoformat(),
                "scores": scores,
                "overall_score": scores["overall_score"],
                "skills_match": scores["skills_match"],
                "experience_match": scores["experience_match"],
                "education_match": scores["education_match"],
                "keywords_match": scores["keywords_match"],
                "status": "completed",
                "source": "google_sheets_upload"
            }
            
            candidates_db.append(candidate)
            success_count += 1
            log_info(f"Successfully processed {candidate_name} - Score: {scores['overall_score']}")
            
        except GoogleDriveError as e:
            log_error(f"Failed to download resume for {candidate_name}: {e}")
            failed_candidates.append({
                "row_number": row_number,
                "name": candidate_name,
                "email": email,
                "phone": phone,
                "experience": experience,
                "expected_ctc": expected_ctc,
                "resume_link": resume_link,
                "error": f"Failed to download resume: {str(e)}",
                "status": "failed"
            })
            fail_count += 1
            
        except TextExtractionError as e:
            log_error(f"Failed to extract text for {candidate_name}: {e}")
            failed_candidates.append({
                "row_number": row_number,
                "name": candidate_name,
                "email": email,
                "phone": phone,
                "experience": experience,
                "expected_ctc": expected_ctc,
                "resume_link": resume_link,
                "error": f"Failed to extract text from resume: {str(e)}",
                "status": "failed"
            })
            fail_count += 1
            
        except GroqServiceError as e:
            log_error(f"Failed to score {candidate_name}: {e}")
            failed_candidates.append({
                "row_number": row_number,
                "name": candidate_name,
                "email": email,
                "phone": phone,
                "experience": experience,
                "expected_ctc": expected_ctc,
                "resume_link": resume_link,
                "error": f"Failed to score candidate: {str(e)}",
                "status": "failed"
            })
            fail_count += 1
            
        except Exception as e:
            log_exception(e, f"Unexpected error processing {candidate_name}")
            failed_candidates.append({
                "row_number": row_number,
                "name": candidate_name,
                "email": email,
                "phone": phone,
                "experience": experience,
                "expected_ctc": expected_ctc,
                "resume_link": resume_link,
                "error": f"Unexpected error: {str(e)}",
                "status": "failed"
            })
            fail_count += 1
    
    log_info(f"Sheet processing complete. Success: {success_count}, Failed: {fail_count}")
    
    return {
        "success": True,
        "message": f"Processed {success_count} candidates successfully, {fail_count} failed",
        "total_processed": len(df),
        "success_count": success_count,
        "fail_count": fail_count,
        "failed_candidates": failed_candidates
    }


@app.get("/api/sheets/failed")
async def get_failed_candidates():
    """Get list of candidates that failed to process - for manual upload"""
    return {
        "failed_candidates": failed_candidates,
        "total": len(failed_candidates)
    }


@app.delete("/api/sheets/failed/clear")
async def clear_failed_candidates():
    """Clear the failed candidates list"""
    global failed_candidates
    count = len(failed_candidates)
    failed_candidates = []
    
    return {
        "success": True,
        "message": f"Cleared {count} failed candidates"
    }


# ============= Run Server =============

if __name__ == "__main__":
    import uvicorn
    
    log_info(f"Starting server on {settings.HOST}:{settings.PORT}")
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
