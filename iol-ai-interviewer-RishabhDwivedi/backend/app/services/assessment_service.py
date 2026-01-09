"""
Assessment Service - Multi-dimensional candidate evaluation
Evaluates candidates in real-time across multiple dimensions with evidence collection
"""
import yaml
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import logger
from app.models import (
    Interview, DimensionScore, InterviewReport, 
    RecommendationType, InterviewStatus
)
from app.schemas.assessment import (
    AssessmentRubrics, DimensionRubric, EvidenceItem,
    DimensionScoreCreate, DimensionScoreUpdate,
    ComprehensiveReport, ReportDimensionScore,
    ReportStrength, ReportConcern, QuoteHighlight,
    FollowUpQuestion, EvaluateAnswerResponse
)
from app.services.llm_service import LLMService


class AssessmentService:
    """Service for real-time candidate assessment and scoring"""
    
    def __init__(self, db: Session, llm_service: Optional[LLMService] = None):
        self.db = db
        self.llm_service = llm_service or LLMService()
        self.rubrics_cache: Dict[str, AssessmentRubrics] = {}
        
    # ========================================================================
    # RUBRIC MANAGEMENT
    # ========================================================================
    
    def load_rubrics(self, template_name: str) -> AssessmentRubrics:
        """Load assessment rubrics from YAML file"""
        if template_name in self.rubrics_cache:
            return self.rubrics_cache[template_name]
        
        # Try multiple paths to find the rubric file
        rubric_paths = [
            Path(f"templates/{template_name}-assessment.yaml"),
            Path(f"../../templates/{template_name}-assessment.yaml"),
            Path(f"phase2/templates/{template_name}-assessment.yaml")
        ]
        
        for rubric_path in rubric_paths:
            if rubric_path.exists():
                with open(rubric_path, 'r') as f:
                    data = yaml.safe_load(f)
                
                rubrics = AssessmentRubrics(**data)
                self.rubrics_cache[template_name] = rubrics
                logger.info(f"Loaded assessment rubrics for {template_name} from {rubric_path}")
                return rubrics
        
        raise FileNotFoundError(f"Assessment rubrics not found for template: {template_name}")
    
    def get_dimension_criteria(self, template_name: str, dimension: str, score: int) -> str:
        """Get the description for a specific score level in a dimension"""
        rubrics = self.load_rubrics(template_name)
        dim_rubric = rubrics.get_dimension_rubric(dimension)
        
        if not dim_rubric:
            return ""
        
        for level in dim_rubric.score_levels:
            if level.score == score:
                return level.description
        
        return ""
    
    # ========================================================================
    # REAL-TIME ANSWER EVALUATION
    # ========================================================================
    
    async def evaluate_answer(
        self,
        interview_id: int,
        question: str,
        answer: str,
        question_number: int,
        expected_topics: List[str] = None
    ) -> EvaluateAnswerResponse:
        """
        Evaluate a candidate's answer in real-time across all dimensions
        Returns updated scores and collected evidence
        """
        interview = self.db.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            raise ValueError(f"Interview {interview_id} not found")
        
        rubrics = self.load_rubrics(interview.template_name)
        
        # Build evaluation prompt for LLM
        eval_prompt = self._build_evaluation_prompt(
            question, answer, rubrics, expected_topics or []
        )
        
        # Get AI evaluation
        evaluation_result = await self._get_ai_evaluation(eval_prompt, rubrics)
        
        # Update dimension scores in database
        updated_scores = []
        evidence_items = []
        
        for dim_name, score_data in evaluation_result['dimension_scores'].items():
            # Create or update dimension score
            result = await self.db.execute(select(DimensionScore).filter(
                DimensionScore.interview_id == interview_id,
                DimensionScore.dimension_name == dim_name
            ))
            existing_score = result.scalar_one_or_none()
            
            if existing_score:
                # Update existing score (running average or weighted update)
                existing_score.score = self._update_score(
                    existing_score.score, 
                    score_data['score'],
                    question_number
                )
                existing_score.reasoning = score_data.get('reasoning', '')
                existing_score.evidence = existing_score.evidence + score_data.get('evidence', [])
            else:
                # Create new score
                new_score = DimensionScore(
                    interview_id=interview_id,
                    dimension_name=dim_name,
                    score=score_data['score'],
                    reasoning=score_data.get('reasoning', ''),
                    evidence=score_data.get('evidence', [])
                )
                self.db.add(new_score)
                existing_score = new_score
            
            updated_scores.append(DimensionScoreUpdate(
                score=existing_score.score,
                reasoning=existing_score.reasoning,
                evidence=existing_score.evidence
            ))
            
            # Collect evidence
            for evidence_text in score_data.get('evidence', []):
                evidence_items.append(EvidenceItem(
                    quote=evidence_text,
                    dimension=dim_name,
                    score_impact=score_data['score'],
                    question_number=question_number,
                    analysis=score_data.get('reasoning', '')
                ))
        
        await self.db.commit()
        
        return EvaluateAnswerResponse(
            scores=updated_scores,
            evidence=evidence_items,
            feedback=evaluation_result.get('overall_feedback')
        )
    
    def _build_evaluation_prompt(
        self,
        question: str,
        answer: str,
        rubrics: AssessmentRubrics,
        expected_topics: List[str]
    ) -> str:
        """Build prompt for LLM to evaluate answer"""
        
        # Build dimension descriptions
        dim_descriptions = []
        for dim in rubrics.dimensions:
            dim_descriptions.append(
                f"\n**{dim.dimension_name}** (weight: {dim.weight}):\n"
                f"{dim.description}\n"
                f"Keywords to look for: {', '.join(dim.keywords)}\n"
                f"Score 1: {dim.score_levels[0].description}\n"
                f"Score 3: {dim.score_levels[2].description}\n"
                f"Score 5: {dim.score_levels[4].description}"
            )
        
        prompt = f"""You are an expert technical interviewer evaluating a candidate's answer.

**Question Asked:**
{question}

**Candidate's Answer:**
{answer}

**Expected Topics:** {', '.join(expected_topics) if expected_topics else 'General technical discussion'}

**Assessment Dimensions:**
{''.join(dim_descriptions)}

**Your Task:**
Evaluate this answer across ALL dimensions listed above. For each dimension:
1. Assign a score from 1-5 based on the rubric
2. Provide brief reasoning (2-3 sentences)
3. Extract 1-3 direct quotes or paraphrases as evidence

**Output Format (JSON):**
{{
  "dimension_scores": {{
    "Technical Knowledge": {{
      "score": 3,
      "reasoning": "Demonstrates solid understanding...",
      "evidence": ["quote1", "quote2"]
    }},
    "Problem-Solving Approach": {{
      "score": 4,
      "reasoning": "Shows systematic approach...",
      "evidence": ["quote1"]
    }},
    ... (all dimensions)
  }},
  "overall_feedback": "Brief summary of answer quality"
}}

Provide ONLY the JSON output, no additional text."""
        
        return prompt
    
    async def _get_ai_evaluation(
        self,
        prompt: str,
        rubrics: AssessmentRubrics
    ) -> Dict:
        """Get AI evaluation via LLM"""
        try:
            # Call LLM service
            response = await self.llm_service.generate_response(
                prompt=prompt,
                system_prompt="You are an expert technical interviewer. Evaluate answers objectively and provide scores with evidence.",
                temperature=0.3  # Lower temperature for consistent evaluation
            )
            
            # Parse JSON response
            # Remove markdown code blocks if present
            response_text = response.strip()
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
            
            evaluation = json.loads(response_text)
            
            # Ensure all dimensions are present
            for dim in rubrics.dimensions:
                if dim.dimension_name not in evaluation['dimension_scores']:
                    evaluation['dimension_scores'][dim.dimension_name] = {
                        'score': 3,
                        'reasoning': 'No specific assessment for this dimension',
                        'evidence': []
                    }
            
            return evaluation
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM evaluation response: {e}")
            # Return neutral scores on parse error
            return self._get_neutral_scores(rubrics)
        except Exception as e:
            logger.error(f"Error getting AI evaluation: {e}")
            return self._get_neutral_scores(rubrics)
    
    def _get_neutral_scores(self, rubrics: AssessmentRubrics) -> Dict:
        """Return neutral scores as fallback"""
        scores = {}
        for dim in rubrics.dimensions:
            scores[dim.dimension_name] = {
                'score': 3,
                'reasoning': 'Unable to evaluate automatically',
                'evidence': []
            }
        return {
            'dimension_scores': scores,
            'overall_feedback': 'Automatic evaluation unavailable'
        }
    
    def _update_score(
        self,
        current_score: float,
        new_score: float,
        question_number: int
    ) -> float:
        """
        Update score using weighted average
        Later questions have slightly more weight as they may show deeper understanding
        """
        weight = 1.0 + (question_number * 0.05)  # Slight increase per question
        total_weight = question_number + weight
        
        updated = (current_score * question_number + new_score * weight) / total_weight
        return round(updated, 2)
    
    # ========================================================================
    # REPORT GENERATION
    # ========================================================================
    
    async def generate_comprehensive_report(
        self,
        interview_id: int
    ) -> ComprehensiveReport:
        """Generate complete evaluation report with all dimensions and evidence"""
        result = await self.db.execute(
            select(Interview)
            .options(selectinload(Interview.job), selectinload(Interview.candidate))
            .filter(Interview.id == interview_id)
        )
        interview = result.scalar_one_or_none()
        if not interview:
            raise ValueError(f"Interview {interview_id} not found")
        
        if interview.status != InterviewStatus.COMPLETED:
            logger.warning(f"Generating report for non-completed interview {interview_id}")
        
        rubrics = self.load_rubrics(interview.template_name)
        
        # Get all dimension scores
        result = await self.db.execute(select(DimensionScore).filter(
            DimensionScore.interview_id == interview_id
        ))
        dimension_scores = result.scalars().all()
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(dimension_scores, rubrics)
        
        # Determine recommendation
        recommendation = self._determine_recommendation(overall_score, dimension_scores, rubrics)
        
        # Build dimension score reports
        report_dim_scores = []
        for dim_score in dimension_scores:
            percentage = (dim_score.score / dim_score.max_score) * 100
            level = self._get_score_level(dim_score.score)
            
            report_dim_scores.append(ReportDimensionScore(
                dimension_name=dim_score.dimension_name,
                score=dim_score.score,
                max_score=dim_score.max_score,
                percentage=round(percentage, 1),
                level=level,
                reasoning=dim_score.reasoning or "No reasoning provided",
                evidence=dim_score.evidence or []
            ))
        
        # Extract strengths and concerns
        strengths = self._extract_strengths(dimension_scores, rubrics)
        concerns = self._extract_concerns(dimension_scores, rubrics)
        
        # Get notable quotes
        notable_quotes = self._extract_notable_quotes(interview, dimension_scores)
        
        # Generate follow-up questions
        follow_ups = await self._generate_follow_up_questions(interview, dimension_scores, rubrics)
        
        # Build transcript
        transcript = self._build_transcript(interview)
        summary = await self._generate_summary(interview, overall_score)
        
        # Get candidate name from candidate record
        candidate_name = f"{interview.candidate.first_name} {interview.candidate.last_name}" if interview.candidate else "Unknown Candidate"
        position = interview.job.title if interview.job else "Unknown Position"
        
        # Calculate duration
        duration_minutes = None
        if interview.started_at and interview.completed_at:
            duration_seconds = (interview.completed_at - interview.started_at).total_seconds()
            duration_minutes = round(duration_seconds / 60, 1)
        
        # Determine confidence level
        confidence = self._calculate_confidence_level(
            len(interview.conversation_history),
            dimension_scores
        )
        
        report = ComprehensiveReport(
            interview_id=interview_id,
            candidate_name=candidate_name,
            position=position,
            interview_date=interview.started_at or interview.created_at,
            duration_minutes=duration_minutes,
            recommendation=recommendation.value,
            overall_score=overall_score,
            confidence_level=confidence,
            dimension_scores=report_dim_scores,
            key_strengths=strengths,
            areas_of_concern=concerns,
            notable_quotes=notable_quotes,
            suggested_follow_ups=follow_ups,
            summary=summary,
            full_transcript=transcript
        )
        
        # Save report to database
        await self._save_report_to_db(interview_id, report)
        
        return report
    
    def _calculate_overall_score(
        self,
        dimension_scores: List[DimensionScore],
        rubrics: AssessmentRubrics
    ) -> float:
        """Calculate weighted overall score"""
        if not dimension_scores:
            return 0.0
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for dim_score in dimension_scores:
            dim_rubric = rubrics.get_dimension_rubric(dim_score.dimension_name)
            weight = dim_rubric.weight if dim_rubric else 1.0
            
            weighted_sum += dim_score.score * weight
            total_weight += weight
        
        return round(weighted_sum / total_weight, 2) if total_weight > 0 else 0.0
    
    def _determine_recommendation(
        self,
        overall_score: float,
        dimension_scores: List[DimensionScore],
        rubrics: AssessmentRubrics
    ) -> RecommendationType:
        """Determine hiring recommendation based on scores"""
        
        # Count dimensions at different thresholds
        dims_at_4_plus = sum(1 for ds in dimension_scores if ds.score >= 4.0)
        dims_at_3_plus = sum(1 for ds in dimension_scores if ds.score >= 3.0)
        
        # Strong Hire: Excellent overall with most dimensions strong
        if overall_score >= 4.3 and dims_at_4_plus >= 4:
            return RecommendationType.STRONG_HIRE
        
        # Hire: Good overall performance
        if overall_score >= 3.5 and dims_at_3_plus >= 4:
            return RecommendationType.HIRE
        
        # Strong No Hire: Below basic requirements
        if overall_score < 2.0:
            return RecommendationType.STRONG_NO_HIRE
        
        # No Hire: Default for scores in between
        return RecommendationType.NO_HIRE
    
    def _get_score_level(self, score: float) -> str:
        """Get score level label (Poor, Fair, Good, Very Good, Excellent)"""
        if score < 1.5:
            return "Poor"
        elif score < 2.5:
            return "Fair"
        elif score < 3.5:
            return "Good"
        elif score < 4.5:
            return "Very Good"
        else:
            return "Excellent"
    
    def _extract_strengths(
        self,
        dimension_scores: List[DimensionScore],
        rubrics: AssessmentRubrics
    ) -> List[ReportStrength]:
        """Extract key strengths from high-scoring dimensions"""
        strengths = []
        
        # Get dimensions with score >= 4.0
        high_scores = sorted(
            [ds for ds in dimension_scores if ds.score >= 4.0],
            key=lambda x: x.score,
            reverse=True
        )
        
        for dim_score in high_scores[:3]:  # Top 3 strengths
            strengths.append(ReportStrength(
                title=f"Strong {dim_score.dimension_name}",
                description=dim_score.reasoning or f"Scored {dim_score.score}/5.0 in {dim_score.dimension_name}",
                evidence=dim_score.evidence[:3]  # Top 3 pieces of evidence
            ))
        
        return strengths
    
    def _extract_concerns(
        self,
        dimension_scores: List[DimensionScore],
        rubrics: AssessmentRubrics
    ) -> List[ReportConcern]:
        """Extract areas of concern from low-scoring dimensions"""
        concerns = []
        
        # Get dimensions with score < 3.0
        low_scores = sorted(
            [ds for ds in dimension_scores if ds.score < 3.0],
            key=lambda x: x.score
        )
        
        for dim_score in low_scores:
            severity = "Major" if dim_score.score < 2.0 else "Moderate"
            
            concerns.append(ReportConcern(
                title=f"Improvement Needed in {dim_score.dimension_name}",
                description=dim_score.reasoning or f"Scored {dim_score.score}/5.0 in {dim_score.dimension_name}",
                evidence=dim_score.evidence[:3],
                severity=severity
            ))
        
        return concerns
    
    def _extract_notable_quotes(
        self,
        interview: Interview,
        dimension_scores: List[DimensionScore]
    ) -> List[QuoteHighlight]:
        """Extract notable quotes from conversation"""
        quotes = []
        
        # Get candidate messages from conversation
        for msg in interview.conversation_history:
            if msg.get('role') == 'user':
                content = msg.get('content', '')
                # Look for quotes longer than 100 chars (substantive answers)
                if len(content) > 100:
                    # Truncate if too long
                    quote_text = content[:300] + "..." if len(content) > 300 else content
                    
                    quotes.append(QuoteHighlight(
                        quote=quote_text,
                        context="Candidate response demonstrating technical thinking",
                        dimension=None  # Could be enhanced to match to dimension
                    ))
                    
                    if len(quotes) >= 5:  # Limit to 5 quotes
                        break
        
        return quotes
    
    async def _generate_follow_up_questions(
        self,
        interview: Interview,
        dimension_scores: List[DimensionScore],
        rubrics: AssessmentRubrics
    ) -> List[FollowUpQuestion]:
        """Generate suggested follow-up questions for next round"""
        follow_ups = []
        
        # Focus on dimensions with borderline scores (2.5-3.5)
        borderline_dims = [ds for ds in dimension_scores if 2.5 <= ds.score <= 3.5]
        
        for dim_score in borderline_dims[:3]:  # Top 3 areas to probe
            dim_rubric = rubrics.get_dimension_rubric(dim_score.dimension_name)
            if not dim_rubric:
                continue
            
            # Generate specific follow-up question
            prompt = f"""Based on a candidate who scored {dim_score.score}/5.0 in {dim_score.dimension_name} 
({dim_rubric.description}), suggest ONE specific follow-up question that would help assess this dimension more deeply.

Reasoning for current score: {dim_score.reasoning}

Provide ONLY the question, no additional text."""
            
            try:
                question = await self.llm_service.generate_response(
                    prompt=prompt,
                    system_prompt="You are an expert technical interviewer. Generate precise, probing questions.",
                    temperature=0.7
                )
                
                follow_ups.append(FollowUpQuestion(
                    question=question.strip(),
                    reason=f"Further assess {dim_score.dimension_name} (current score: {dim_score.score}/5.0)",
                    dimension=dim_score.dimension_name
                ))
            except Exception as e:
                logger.error(f"Failed to generate follow-up question: {e}")
        
        return follow_ups
    
    def _build_transcript(self, interview: Interview) -> str:
        """Build formatted transcript from conversation history"""
        lines = []
        lines.append(f"Interview Transcript - {interview.session_id}")
        lines.append(f"Started: {interview.started_at}")
        lines.append("=" * 80)
        lines.append("")
        
        for i, msg in enumerate(interview.conversation_history, 1):
            role = "Interviewer" if msg.get('role') == 'assistant' else "Candidate"
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            
            lines.append(f"[{i}] {role} ({timestamp}):")
            lines.append(content)
            lines.append("")
        
        return "\n".join(lines)
    
    async def _generate_summary(self, interview: Interview, overall_score: float) -> str:
        """Generate executive summary using LLM"""
        # Build context
        context = f"""Interview for {interview.job.title if interview.job else 'position'}
Overall Score: {overall_score}/5.0
Questions Asked: {len([m for m in interview.conversation_history if m.get('role') == 'assistant'])}

Generate a 2-3 sentence executive summary of this candidate's performance."""
        
        try:
            summary = await self.llm_service.generate_response(
                prompt=context,
                system_prompt="You are an expert technical interviewer writing concise summaries.",
                temperature=0.5
            )
            return summary.strip()
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return f"Candidate scored {overall_score}/5.0 overall in the interview."
    
    def _calculate_confidence_level(
        self,
        num_questions: int,
        dimension_scores: List[DimensionScore]
    ) -> str:
        """Calculate confidence level in the assessment"""
        # More questions and consistent scores = higher confidence
        if num_questions >= 8 and len(dimension_scores) >= 5:
            return "High"
        elif num_questions >= 5 and len(dimension_scores) >= 4:
            return "Medium"
        else:
            return "Low"
    
    async def _save_report_to_db(self, interview_id: int, report: ComprehensiveReport):
        """Save generated report to database"""
        # Check if report already exists
        result = await self.db.execute(select(InterviewReport).filter(
            InterviewReport.interview_id == interview_id
        ))
        existing_report = result.scalar_one_or_none()
        
        report_data = {
            'interview_id': interview_id,
            'recommendation': RecommendationType(report.recommendation),
            'overall_score': report.overall_score,
            'key_strengths': [s.dict() for s in report.key_strengths],
            'areas_of_concern': [c.dict() for c in report.areas_of_concern],
            'notable_quotes': [q.dict() for q in report.notable_quotes],
            'suggested_follow_ups': [f.dict() for f in report.suggested_follow_ups],
            'summary': report.summary,
            'full_transcript': report.full_transcript,
            'generated_at': datetime.utcnow()
        }
        
        if existing_report:
            # Update existing report
            for key, value in report_data.items():
                if key != 'interview_id':
                    setattr(existing_report, key, value)
        else:
            # Create new report
            new_report = InterviewReport(**report_data)
            self.db.add(new_report)
        
        await self.db.commit()
        logger.info(f"Saved comprehensive report for interview {interview_id}")
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    async def get_current_scores(self, interview_id: int) -> List[DimensionScore]:
        """Get current dimension scores for an interview"""
        result = await self.db.execute(select(DimensionScore).filter(
            DimensionScore.interview_id == interview_id
        ))
        return result.scalars().all()
    
    async def initialize_dimensions(self, interview_id: int, template_name: str):
        """Initialize all dimensions with neutral scores at interview start"""
        rubrics = self.load_rubrics(template_name)
        
        for dim in rubrics.dimensions:
            result = await self.db.execute(select(DimensionScore).filter(
                DimensionScore.interview_id == interview_id,
                DimensionScore.dimension_name == dim.dimension_name
            ))
            existing = result.scalar_one_or_none()
            
            if not existing:
                score = DimensionScore(
                    interview_id=interview_id,
                    dimension_name=dim.dimension_name,
                    score=0.0,  # Start at 0, will be updated with first answer
                    reasoning="Assessment in progress",
                    evidence=[]
                )
                self.db.add(score)
        
        await self.db.commit()
        logger.info(f"Initialized {len(rubrics.dimensions)} dimensions for interview {interview_id}")
