"""
Pydantic schemas for assessment and scoring
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# DIMENSION SCORING SCHEMAS
# ============================================================================

class ScoreLevel(BaseModel):
    """Individual score level definition (1-5 scale)"""
    score: int = Field(..., ge=1, le=5)
    label: str  # e.g., "Poor", "Fair", "Good", "Very Good", "Excellent"
    description: str  # Detailed criteria for this score level


class DimensionRubric(BaseModel):
    """Rubric for a single assessment dimension"""
    dimension_name: str  # e.g., "Technical Knowledge"
    description: str  # What this dimension measures
    weight: float = Field(default=1.0, ge=0.0, le=1.0)  # Relative importance
    score_levels: List[ScoreLevel]  # 5 levels with descriptions
    keywords: List[str] = Field(default_factory=list)  # Keywords to look for in answers


class AssessmentRubrics(BaseModel):
    """Complete assessment rubrics for an interview"""
    template_name: str  # e.g., "backend-engineer"
    version: str = "1.0"
    dimensions: List[DimensionRubric]
    
    def get_dimension_names(self) -> List[str]:
        """Get list of dimension names"""
        return [d.dimension_name for d in self.dimensions]
    
    def get_dimension_rubric(self, dimension_name: str) -> Optional[DimensionRubric]:
        """Get rubric for a specific dimension"""
        for dim in self.dimensions:
            if dim.dimension_name == dimension_name:
                return dim
        return None


# ============================================================================
# EVIDENCE COLLECTION SCHEMAS
# ============================================================================

class EvidenceItem(BaseModel):
    """Evidence item from candidate response"""
    quote: str  # Direct quote or paraphrase from candidate
    dimension: str  # Which dimension this supports
    score_impact: int  # 1-5, how this affects the score
    question_number: int  # Which question this came from
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    analysis: Optional[str] = None  # AI's reasoning for this evidence


class EvidenceCollection(BaseModel):
    """Collection of evidence items for an interview"""
    interview_id: int
    items: List[EvidenceItem] = Field(default_factory=list)
    
    def add_evidence(self, item: EvidenceItem):
        """Add an evidence item"""
        self.items.append(item)
    
    def get_evidence_for_dimension(self, dimension: str) -> List[EvidenceItem]:
        """Get all evidence for a specific dimension"""
        return [item for item in self.items if item.dimension == dimension]


# ============================================================================
# SCORE SCHEMAS
# ============================================================================

class DimensionScoreCreate(BaseModel):
    """Schema for creating a dimension score"""
    dimension_name: str
    score: float = Field(..., ge=0.0, le=5.0)
    max_score: float = Field(default=5.0)
    reasoning: Optional[str] = None
    evidence: List[str] = Field(default_factory=list)  # List of quote strings


class DimensionScoreResponse(DimensionScoreCreate):
    """Schema for dimension score response"""
    id: int
    interview_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class DimensionScoreUpdate(BaseModel):
    """Schema for updating a dimension score during interview"""
    score: float = Field(..., ge=0.0, le=5.0)
    reasoning: Optional[str] = None
    evidence: Optional[List[str]] = None


# ============================================================================
# ASSESSMENT REPORT SCHEMAS
# ============================================================================

class ReportDimensionScore(BaseModel):
    """Dimension score in report format"""
    dimension_name: str
    score: float
    max_score: float
    percentage: float  # score/max_score * 100
    level: str  # Poor, Fair, Good, Very Good, Excellent
    reasoning: str
    evidence: List[str]  # Supporting quotes


class ReportStrength(BaseModel):
    """Key strength with supporting evidence"""
    title: str  # e.g., "Strong system design skills"
    description: str  # Detailed explanation
    evidence: List[str]  # Supporting quotes


class ReportConcern(BaseModel):
    """Area of concern with supporting evidence"""
    title: str  # e.g., "Limited database optimization experience"
    description: str  # Detailed explanation
    evidence: List[str]  # Supporting quotes
    severity: str  # Minor, Moderate, Major


class QuoteHighlight(BaseModel):
    """Notable quote from candidate"""
    quote: str
    context: str  # Why this quote is notable
    dimension: Optional[str] = None  # Related dimension


class FollowUpQuestion(BaseModel):
    """Suggested follow-up question for next round"""
    question: str
    reason: str  # Why this question is suggested
    dimension: str  # Which dimension it probes


class InterviewReportCreate(BaseModel):
    """Schema for creating an interview report"""
    interview_id: int
    recommendation: str  # strong_hire, hire, no_hire, strong_no_hire
    overall_score: float = Field(..., ge=0.0, le=5.0)
    key_strengths: List[Dict[str, Any]] = Field(default_factory=list)
    areas_of_concern: List[Dict[str, Any]] = Field(default_factory=list)
    notable_quotes: List[Dict[str, Any]] = Field(default_factory=list)
    suggested_follow_ups: List[Dict[str, Any]] = Field(default_factory=list)
    full_transcript: Optional[str] = None
    summary: Optional[str] = None


class InterviewReportResponse(InterviewReportCreate):
    """Schema for interview report response"""
    id: int
    generated_at: datetime
    report_version: str
    pdf_path: Optional[str] = None
    json_path: Optional[str] = None
    
    class Config:
        from_attributes = True


class ComprehensiveReport(BaseModel):
    """Complete interview evaluation report"""
    # Interview Metadata
    interview_id: int
    candidate_name: str
    position: str
    interview_date: datetime
    duration_minutes: Optional[float] = None
    
    # Overall Assessment
    recommendation: str  # STRONG_HIRE, HIRE, NO_HIRE, STRONG_NO_HIRE
    overall_score: float  # 0-5
    confidence_level: str  # Low, Medium, High
    
    # Dimension Scores
    dimension_scores: List[ReportDimensionScore]
    
    # Qualitative Analysis
    key_strengths: List[ReportStrength]
    areas_of_concern: List[ReportConcern]
    notable_quotes: List[QuoteHighlight]
    
    # Next Steps
    suggested_follow_ups: List[FollowUpQuestion]
    recommended_interviewers: List[str] = Field(default_factory=list)  # Who should interview next
    
    # Transcript
    summary: str
    full_transcript: Optional[str] = None
    
    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    report_version: str = "1.0"


class AssessmentProgress(BaseModel):
    """Real-time assessment progress during interview"""
    interview_id: int
    questions_completed: int
    total_questions: int
    current_dimension_scores: List[DimensionScoreResponse]
    recent_evidence: List[EvidenceItem]
    estimated_completion: Optional[datetime] = None


# ============================================================================
# EVALUATION REQUEST SCHEMAS
# ============================================================================

class EvaluateAnswerRequest(BaseModel):
    """Request to evaluate a candidate's answer"""
    interview_id: int
    question: str
    answer: str
    question_number: int
    expected_topics: List[str] = Field(default_factory=list)  # Topics this question probes


class EvaluateAnswerResponse(BaseModel):
    """Response from answer evaluation"""
    scores: List[DimensionScoreUpdate]  # Updated scores for each dimension
    evidence: List[EvidenceItem]  # New evidence collected
    feedback: Optional[str] = None  # Internal notes (not shown to candidate)


class GenerateReportRequest(BaseModel):
    """Request to generate final report"""
    interview_id: int
    include_transcript: bool = True
    export_format: str = "json"  # json, markdown, pdf
