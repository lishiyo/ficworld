"""
LLM Interface for interacting with language models.
"""
import json
import os
from typing import Dict, List, Any, Optional, Union
import httpx
from dotenv import load_dotenv
from .ficworld_config import LLM_MODEL_NAME


class LLMInterface:
    """Interface for interacting with language models."""
    
    def __init__(self, model_name: str = LLM_MODEL_NAME):
        """
        Initialize the LLM interface.
        
        Args:
            model_name: Name of the LLM to use.
        """
        load_dotenv()
        self.model_name = model_name
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
    
    async def _make_openai_request(
        self, 
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Make a request to the OpenAI API.
        
        Args:
            messages: List of message dictionaries.
            temperature: Temperature parameter.
            max_tokens: Maximum tokens to generate.
            json_mode: Whether to force JSON output.
            
        Returns:
            The response from the API.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
            
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0
            )
            
            if response.status_code != 200:
                error_msg = f"API error: {response.status_code} - {response.text}"
                raise Exception(error_msg)
            
            return response.json()
    
    async def generate_response(
        self, 
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            system_prompt: System message.
            user_prompt: User message.
            temperature: Temperature parameter.
            max_tokens: Maximum tokens to generate.
            json_mode: Whether to force JSON output.
            
        Returns:
            The generated text response.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self._make_openai_request(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode
        )
        
        return response["choices"][0]["message"]["content"]
    
    async def generate_json_response(
        self, 
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.5,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate a response from the LLM and parse it as JSON.
        
        Args:
            system_prompt: System message.
            user_prompt: User message.
            temperature: Temperature parameter.
            max_tokens: Maximum tokens to generate.
            
        Returns:
            The parsed JSON response.
        """
        response_text = await self.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True
        )
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from the response using simple heuristics
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    raise ValueError(f"Failed to parse JSON response: {response_text}")
            else:
                raise ValueError(f"Failed to parse JSON response: {response_text}")
    
    # Synchronous versions for simpler usage scenarios
    
    def generate_response_sync(
        self, 
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        """
        Synchronous version of generate_response.
        """
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.generate_response(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode
                )
            )
        finally:
            loop.close()
    
    def generate_json_response_sync(
        self, 
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.5,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Synchronous version of generate_json_response.
        """
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.generate_json_response(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            )
        finally:
            loop.close() 