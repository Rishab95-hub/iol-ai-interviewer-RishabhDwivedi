"""
LLM Service for OpenAI integration (Azure OpenAI and Standard OpenAI)
"""
from typing import List, Dict, Optional, AsyncIterator
from openai import AsyncAzureOpenAI, AsyncOpenAI
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMService:
    """Service for interacting with OpenAI APIs"""
    
    def __init__(self):
        """Initialize OpenAI client based on provider"""
        if settings.llm_provider == "azure_openai":
            self.client = AsyncAzureOpenAI(
                api_key=settings.azure_openai_key,
                api_version=settings.azure_openai_api_version,
                azure_endpoint=settings.azure_openai_endpoint
            )
            self.model = settings.azure_model_gpt_4
        elif settings.llm_provider == "openai":
            self.client = AsyncOpenAI(
                api_key=settings.openai_api_key
            )
            self.model = settings.openai_model
        else:
            raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
        
        logger.info(
            "llm_service_initialized",
            provider=settings.llm_provider,
            model=self.model
        )
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """
        Generate a response from the LLM
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated response text
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            content = response.choices[0].message.content
            logger.info(
                "llm_response_generated",
                tokens_used=response.usage.total_tokens
            )
            return content
            
        except Exception as e:
            logger.error("llm_generation_failed", error=str(e))
            raise
    
    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AsyncIterator[str]:
        """
        Stream response from LLM
        
        Args:
            messages: List of message dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            
        Yields:
            Response chunks
        """
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error("llm_streaming_failed", error=str(e))
            raise
    
    async def get_interview_question(
        self,
        interview,
        question_number: int
    ) -> str:
        """
        Generate interview question based on context
        
        Args:
            interview: Interview model instance with job/candidate context
            question_number: Current question number (0-indexed)
            
        Returns:
            Interview question text
        """
        # Build context
        job_context = interview.job_context or {}
        candidate_context = interview.candidate_context or {}
        
        system_prompt = f"""You are an expert technical interviewer conducting a structured interview.

Job Details:
- Title: {job_context.get('title', 'N/A')}
- Department: {job_context.get('department', 'N/A')}
- Experience Level: {job_context.get('experience_level', 'N/A')}

Candidate:
- Name: {candidate_context.get('name', 'Candidate')}
- Resume: {candidate_context.get('resume_excerpt', 'Not available')[:500]}

Your role:
1. Ask clear, specific technical questions
2. Probe deeper based on responses
3. Assess technical knowledge, problem-solving, and communication
4. Maintain a professional yet friendly tone

This is question #{question_number + 1} of 10."""

        if question_number == 0:
            # First question
            user_prompt = "Start the interview with a warm greeting and the first technical question related to the job requirements."
        else:
            # Follow-up questions based on conversation history
            conversation_summary = "\n".join([
                f"{msg['role'].upper()}: {msg['content'][:200]}"
                for msg in (interview.conversation_history or [])[-4:]  # Last 4 messages
            ])
            
            user_prompt = f"""Based on the conversation so far:

{conversation_summary}

Ask the next interview question. Consider:
- Building on previous answers
- Exploring different technical areas
- Assessing depth of knowledge"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return await self.generate_response(messages, temperature=0.7, max_tokens=300)
    
    async def stream_interview_response(
        self,
        interview,
        candidate_response: str
    ) -> AsyncIterator[str]:
        """
        Stream interview question/response based on candidate's answer
        
        Args:
            interview: Interview instance
            candidate_response: Latest response from candidate
            
        Yields:
            Response chunks
        """
        job_context = interview.job_context or {}
        candidate_context = interview.candidate_context or {}
        
        system_prompt = f"""You are an expert technical interviewer.

Job: {job_context.get('title', 'N/A')}
Candidate: {candidate_context.get('name', 'Candidate')}

Analyze the candidate's response and:
1. Acknowledge their answer briefly
2. Ask a relevant follow-up question OR move to next topic
3. Keep responses concise (2-3 sentences max)
4. Be encouraging yet thorough

Question #{interview.current_question_index} of 10"""

        # Get recent conversation for context
        conversation_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in (interview.conversation_history or [])[-6:]  # Last 6 messages
        ]
        
        messages = [
            {"role": "system", "content": system_prompt},
            *conversation_history,
            {"role": "user", "content": candidate_response}
        ]
        
        async for chunk in self.stream_response(messages, temperature=0.7, max_tokens=300):
            yield chunk


# Global instance
llm_service = LLMService()
