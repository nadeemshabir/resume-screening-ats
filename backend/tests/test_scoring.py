"""
Tests for scoring service
"""
import pytest
from app.services.scoring_service import ScoringService


class TestScoringService:
    """Test cases for ScoringService class"""
    
    def setup_method(self):
        """Setup test fixtures with rule-based scoring (no AI)"""
        self.scoring = ScoringService(use_ai=False)
    
    def test_parse_jd_skills(self):
        """Test skill extraction from job description"""
        jd = "Looking for Python developer with FastAPI and SQL experience"
        requirements = self.scoring.parse_jd(jd)
        
        assert "Python" in requirements["skills"]
        assert "FastAPI" in requirements["skills"]
        assert "SQL" in requirements["skills"]
    
    def test_parse_jd_experience_years(self):
        """Test experience years extraction"""
        jd = "Requires 5+ years of experience in software development"
        requirements = self.scoring.parse_jd(jd)
        
        assert requirements["experience_years"] == 5
    
    def test_parse_jd_education(self):
        """Test education requirements extraction"""
        jd = "Bachelor's degree in Computer Science required"
        requirements = self.scoring.parse_jd(jd)
        
        assert len(requirements["education"]) > 0
    
    def test_rule_based_scoring(self):
        """Test rule-based candidate scoring"""
        jd = "Python developer with 3 years experience, FastAPI skills"
        resume = """
        Experienced Python developer with 5 years experience.
        Skills: Python, FastAPI, Django, PostgreSQL
        Education: Bachelor's in Computer Science
        """
        
        scores = self.scoring.score_candidate(jd, resume)
        
        assert "overall_score" in scores
        assert "skills_match" in scores
        assert "experience_match" in scores
        assert "education_match" in scores
        assert "keywords_match" in scores
        assert 0 <= scores["overall_score"] <= 100
    
    def test_skills_matching(self):
        """Test skills matching returns proper percentages"""
        jd = "Need Python, JavaScript, SQL skills"
        resume = "I know Python and JavaScript very well"
        
        scores = self.scoring.score_candidate(jd, resume)
        
        # Should have matched 2 out of 3 skills
        assert scores["skills_match"] > 0
    
    def test_extract_keywords(self):
        """Test keyword extraction"""
        jd = "Development experience development skills required"
        keywords = self.scoring._extract_keywords(jd)
        
        assert "development" in keywords
        assert len(keywords) > 0


class TestExperienceExtraction:
    """Test experience extraction methods"""
    
    def setup_method(self):
        self.scoring = ScoringService(use_ai=False)
    
    def test_extract_experience_from_resume(self):
        """Test extracting years of experience from resume"""
        resume = "I have 7 years of experience in software development"
        years = self.scoring._extract_experience_from_resume(resume)
        
        assert years == 7
    
    def test_extract_experience_from_dates(self):
        """Test calculating experience from date ranges"""
        resume = """
        Software Engineer at Company A
        2020 - Present
        
        Junior Developer at Company B
        2018 - 2020
        """
        years = self.scoring._extract_experience_from_resume(resume)
        
        # Should calculate some years from the date ranges
        assert years > 0
