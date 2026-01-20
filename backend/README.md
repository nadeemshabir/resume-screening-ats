# Resume Screening ATS Backend

AI-powered resume screening system using Groq LLM for candidate ranking.

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app with all routes
│   ├── config.py             # Environment configuration
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py        # All Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── text_extractor.py # PDF/Word/OCR extraction
│   │   └── groq_service.py   # Groq AI scoring
│   └── utils/
│       ├── __init__.py
│       └── logger.py         # Loguru configuration
├── tests/
│   ├── test_file_processor.py
│   └── test_scoring.py
├── .env
├── requirements.txt
└── README.md
```

## Installation

1. Create virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
- Copy `.env` and set your `GROQ_API_KEY`
- Install Tesseract OCR for scanned PDF/image support

## Running the Server

```bash
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/api/jd/set` | Set job description |
| GET | `/api/jd/get` | Get current JD |
| POST | `/api/candidates/upload` | Upload resume |
| GET | `/api/candidates/list` | Get ranked candidates |
| GET | `/api/candidates/{id}` | Get candidate details |
| DELETE | `/api/candidates/{id}` | Delete candidate |
| GET | `/api/stats` | Get statistics |
| DELETE | `/api/candidates/clear` | Clear all candidates |

## Technologies

- **FastAPI** - Web framework
- **Groq** - LLM for AI scoring
- **pdfplumber/PyPDF2** - PDF extraction
- **pytesseract** - OCR
- **loguru** - Logging
