"""
Groq AI Service
Handles all interactions with Groq API for resume scoring
"""
import json
import re
from typing import Dict, Optional
from groq import Groq

from app.config import settings
from app.models.schemas import ScoringBreakdown, ScoringExplanation
from app.utils.logger import log_info, log_error, log_exception


class GroqServiceError(Exception):
    """Custom exception for Groq service errors"""
    pass


class GroqService:
    """
    Service for interacting with Groq API
    Handles resume analysis and scoring
    """
    
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
        self.temperature = settings.GROQ_TEMPERATURE
        self.max_tokens = settings.GROQ_MAX_TOKENS
    
    def test_connection(self) -> bool:
        """Test if Groq API is accessible"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            log_error(f"Groq API connection test failed: {e}")
            return False
    
    def score_candidate(
        self, 
        jd_text: str, 
        resume_text: str,
        jd_requirements: Optional[Dict] = None
    ) -> Dict:
        """
        Score candidate resume against job description using Groq AI
        
        Args:
            jd_text: Job description text
            resume_text: Candidate resume text
            jd_requirements: Pre-parsed JD requirements (optional)
            
        Returns:
            Dictionary with scoring breakdown and explanations
        """
        log_info("Starting AI-powered candidate scoring")
        
        try:
            # Build the prompt
            prompt = self._build_scoring_prompt(jd_text, resume_text, jd_requirements)
            
            # Call Groq API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert HR recruiter and resume analyst. Analyze resumes objectively and provide detailed, fair scoring."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            # Extract and parse response
            result_text = response.choices[0].message.content
            log_info(f"Groq API response received ({len(result_text)} chars)")
            
            # Parse JSON from response
            parsed_result = self._parse_groq_response(result_text)
            
            # Validate and calculate overall score
            scores = self._validate_and_calculate_scores(parsed_result)
            
            log_info(f"Candidate scored: {scores['overall_score']:.2f}")
            return scores
            
        except Exception as e:
            log_exception(e, "Groq scoring failed")
            raise GroqServiceError(f"AI scoring failed: {str(e)}")
    
    def _build_scoring_prompt(
        self, 
        jd_text: str, 
        resume_text: str,
        jd_requirements: Optional[Dict] = None
    ) -> str:
        """Build comprehensive prompt for Groq"""
        
        # Truncate texts if too long to fit in context
        max_jd_length = 2000
        max_resume_length = 3000
        
        if len(jd_text) > max_jd_length:
            jd_text = jd_text[:max_jd_length] + "..."
            log_info(f"JD truncated to {max_jd_length} chars")
        
        if len(resume_text) > max_resume_length:
            resume_text = resume_text[:max_resume_length] + "..."
            log_info(f"Resume truncated to {max_resume_length} chars")
        
        prompt = f"""Analyze this candidate's resume against the job description and provide detailed scoring.

JOB DESCRIPTION:
{jd_text}

CANDIDATE RESUME:
{resume_text}

SCORING GUIDELINES:
- skills_match (0-100): How well technical skills match requirements. Weight: {settings.SKILLS_WEIGHT*100}%
- experience_match (0-100): Relevant work experience and years. Weight: {settings.EXPERIENCE_WEIGHT*100}%
- education_match (0-100): Education level and field alignment. Weight: {settings.EDUCATION_WEIGHT*100}%
- keywords_match (0-100): Important domain keywords and terminology. Weight: {settings.KEYWORDS_WEIGHT*100}%

Be strict but fair. A perfect match is rare (90-100). Good matches are 70-85. Partial matches 50-70.

Respond ONLY with valid JSON in this EXACT format:
{{
    "skills_match": <number 0-100>,
    "experience_match": <number 0-100>,
    "education_match": <number 0-100>,
    "keywords_match": <number 0-100>,
    "explanation": {{
        "skills": "<2-3 sentence explanation>",
        "experience": "<2-3 sentence explanation>",
        "education": "<2-3 sentence explanation>",
        "keywords": "<2-3 sentence explanation>",
        "overall": "<overall assessment in 2-3 sentences>",
        "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
        "weaknesses": ["<weakness 1>", "<weakness 2>"]
    }}
}}

IMPORTANT: Return ONLY the JSON, no markdown, no code blocks, no explanations."""

        return prompt
    
    def _parse_groq_response(self, response_text: str) -> Dict:
        """
        Parse JSON from Groq response
        Handles various response formats including markdown code blocks
        """
        try:
            # Try direct JSON parsing first
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            json_pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
            match = re.search(json_pattern, response_text)
            
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
            
            # Try to find JSON object in text
            json_pattern2 = r'\{[\s\S]*\}'
            match2 = re.search(json_pattern2, response_text)
            
            if match2:
                return json.loads(match2.group(0))
            
            raise GroqServiceError(f"Could not parse JSON from response: {response_text[:200]}")
    
    def _validate_and_calculate_scores(self, parsed_result: Dict) -> Dict:
        """
        Validate scores and calculate weighted overall score
        Ensures all scores are within valid range
        """
        required_fields = ['skills_match', 'experience_match', 'education_match', 'keywords_match']
        
        # Validate presence of required fields
        for field in required_fields:
            if field not in parsed_result:
                raise GroqServiceError(f"Missing required field: {field}")
        
        # Validate and clamp scores to 0-100 range
        for field in required_fields:
            score = parsed_result[field]
            if not isinstance(score, (int, float)):
                raise GroqServiceError(f"{field} must be a number, got {type(score)}")
            
            # Clamp to valid range
            parsed_result[field] = max(0, min(100, float(score)))
        
        # Calculate weighted overall score
        overall_score = (
            parsed_result['skills_match'] * settings.SKILLS_WEIGHT +
            parsed_result['experience_match'] * settings.EXPERIENCE_WEIGHT +
            parsed_result['education_match'] * settings.EDUCATION_WEIGHT +
            parsed_result['keywords_match'] * settings.KEYWORDS_WEIGHT
        )
        
        parsed_result['overall_score'] = round(overall_score, 2)
        
        # Validate explanation structure
        if 'explanation' not in parsed_result:
            parsed_result['explanation'] = {
                "skills": "No explanation provided",
                "experience": "No explanation provided",
                "education": "No explanation provided",
                "keywords": "No explanation provided",
                "overall": "No explanation provided",
                "strengths": [],
                "weaknesses": []
            }
        
        return parsed_result
    
    def parse_job_requirements(self, jd_text: str) -> Dict:
        """
        Use Groq to intelligently parse job requirements
        Extracts skills, education, experience, etc.
        """
        log_info("Parsing job requirements with AI")
        
        prompt = f"""Analyze this job description and extract key requirements.

JOB DESCRIPTION:
{jd_text}

Extract and return ONLY valid JSON in this format:
{{
    "skills": ["skill1", "skill2", ...],
    "education": ["degree1", "degree2", ...],
    "experience_years": <number or null>,
    "certifications": ["cert1", "cert2", ...],
    "keywords": ["keyword1", "keyword2", ...]
}}

Be thorough but concise. Extract 5-15 skills, 1-3 education requirements, and 10-20 keywords."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing job descriptions and extracting key requirements."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,  # Lower temperature for more consistent extraction
                max_tokens=1000,
            )
            
            result_text = response.choices[0].message.content
            parsed = self._parse_groq_response(result_text)
            
            log_info(f"Extracted {len(parsed.get('skills', []))} skills, "
                    f"{len(parsed.get('keywords', []))} keywords")
            
            return parsed
            
        except Exception as e:
            log_exception(e, "Job requirements parsing failed")
            # Return empty structure on failure
            return {
                "skills": [],
                "education": [],
                "experience_years": None,
                "certifications": [],
                "keywords": []
            }