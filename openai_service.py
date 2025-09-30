"""
OpenAI service module for handling API interactions.
"""
from typing import List, Dict, Any, Optional
from openai import OpenAI
from config import config


class OpenAIService:
    """Service class for interacting with OpenAI API."""
    
    def __init__(self):
        """Initialize the OpenAI client."""
        config.validate()
        self.client = OpenAI(api_key=config.get_api_key())
        self.model = config.model
        # self.temperature = config.temperature
        # self.max_tokens = config.max_tokens
    
    def generate_completion(
        self,
        messages: List[Dict[str, str]],
        # temperature: Optional[float] = None,
        # max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate a completion using OpenAI API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Optional temperature override
            max_tokens: Optional max_tokens override
            
        Returns:
            Generated text response
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                # temperature=temperature or self.temperature,
                # max_tokens=max_tokens or self.max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Error generating completion: {str(e)}")
    
    def generate_presentation_content(
        self,
        topic: str,
        n_slides: int,
        tone: Optional[str] = None,
        verbosity: Optional[str] = None,
        instructions: Optional[str] = None,
        include_tsx: bool = True
    ) -> str:
        """
        Generate presentation content based on topic and parameters.
        
        Args:
            topic: Main topic for the presentation
            n_slides: Number of slides to generate
            tone: Tone of the presentation (professional, casual, technical, etc.)
            verbosity: Level of detail (concise, detailed, comprehensive)
            instructions: Additional instructions for content generation
            include_tsx: Whether to include TSX code examples
            
        Returns:
            Generated presentation content in JSON format
        """
        system_prompt = self._build_system_prompt(include_tsx)
        user_prompt = self._build_user_prompt(
            topic, n_slides, tone, verbosity, instructions
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return self.generate_completion(messages)
    
    def _build_system_prompt(self, include_tsx: bool) -> str:
        """Build the system prompt for presentation generation."""
        base_prompt = """You are a professional presentation content generator. 
Your task is to create engaging, well-structured presentation content in JSON format.

Return ONLY valid JSON with the following structure:
{
    "title": "Presentation Title",
    "slides": [
        {
            "slide_number": 1,
            "title": "Slide Title",
            "content": ["Bullet point 1", "Bullet point 2"],
            "notes": "Speaker notes for this slide"
        }
    ]
}"""
        
        if include_tsx:
            base_prompt += """

For technical presentations, include TSX code examples where appropriate:
{
    "slide_number": X,
    "title": "Code Example",
    "content": ["Introduction to the code"],
    "code": {
        "language": "tsx",
        "code": "// Your TSX code here\\nimport React from 'react';\\n\\nconst Component = () => {\\n  return <div>Hello</div>;\\n};"
    },
    "notes": "Explanation of the code"
}"""
        
        return base_prompt
    
    def _build_user_prompt(
        self,
        topic: str,
        n_slides: int,
        tone: Optional[str],
        verbosity: Optional[str],
        instructions: Optional[str]
    ) -> str:
        """Build the user prompt with all parameters."""
        prompt = f"Create a {n_slides}-slide presentation about: {topic}\n\n"
        
        if tone:
            prompt += f"Tone: {tone}\n"
        if verbosity:
            prompt += f"Verbosity: {verbosity}\n"
        if instructions:
            prompt += f"Additional instructions: {instructions}\n"
        
        prompt += "\nGenerate professional, engaging content with clear structure."
        return prompt
