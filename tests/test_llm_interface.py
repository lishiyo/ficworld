"""
Unit tests for LLMInterface in modules/llm_interface.py.
"""
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import os
import json
import asyncio

# Add project root to sys.path if necessary
from pathlib import Path
import sys
if str(Path.cwd()) not in sys.path:
    sys.path.insert(0, str(Path.cwd()))

from modules.llm_interface import LLMInterface

# Tests for the LLMInterface module

class TestLLMInterface(unittest.TestCase):

    def setUp(self):
        """Set up for each test."""
        # Mock environment variable for API key
        self.patcher = patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_api_key"})
        self.patcher.start()
        self.llm_interface = LLMInterface(model_name="test_model/test_model_v1")

    def tearDown(self):
        """Clean up after each test."""
        self.patcher.stop()

    def test_initialization_success(self):
        """Test successful initialization."""
        self.assertEqual(self.llm_interface.model_name, "test_model/test_model_v1")
        self.assertEqual(self.llm_interface.api_key, "test_api_key")

    def test_initialization_no_api_key(self):
        """Test initialization when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('modules.llm_interface.load_dotenv') as mock_load_dotenv:
                with self.assertRaisesRegex(ValueError, "OPENROUTER_API_KEY not found"):
                    LLMInterface()
                mock_load_dotenv.assert_called_once()

    @patch('httpx.AsyncClient.post', new_callable=AsyncMock)
    def test_generate_response_success(self, mock_post):
        """Test successful text response generation."""
        mock_response_content = {
            "choices": [
                {"message": {"role": "assistant", "content": "Hello, world!"}}
            ]
        }
        mock_post.return_value = MagicMock(
            status_code=200, 
            json=MagicMock(return_value=mock_response_content)
        )

        system_prompt = "Be helpful."
        user_prompt = "Say hello."
        
        response = asyncio.run(self.llm_interface.generate_response(system_prompt, user_prompt))
        
        self.assertEqual(response, "Hello, world!")
        mock_post.assert_called_once()
        called_args, called_kwargs = mock_post.call_args
        self.assertEqual(called_kwargs['json']['model'], "test_model/test_model_v1")
        self.assertIn({"role": "system", "content": system_prompt}, called_kwargs['json']['messages'])
        self.assertIn({"role": "user", "content": user_prompt}, called_kwargs['json']['messages'])

    @patch('httpx.AsyncClient.post', new_callable=AsyncMock)
    def test_generate_json_response_success(self, mock_post):
        """Test successful JSON response generation."""
        mock_json_payload = {"key": "value", "number": 123}
        mock_response_content = {
            "choices": [
                {"message": {"role": "assistant", "content": json.dumps(mock_json_payload)}}
            ]
        }
        mock_post.return_value = MagicMock(
            status_code=200, 
            json=MagicMock(return_value=mock_response_content)
        )

        system_prompt = "Respond in JSON."
        user_prompt = "Give me data."

        response = asyncio.run(self.llm_interface.generate_json_response(system_prompt, user_prompt))

        self.assertEqual(response, mock_json_payload)
        mock_post.assert_called_once()
        called_args, called_kwargs = mock_post.call_args
        self.assertTrue(called_kwargs['json']['response_format']['type'] == "json_object")

    @patch('httpx.AsyncClient.post', new_callable=AsyncMock)
    def test_generate_response_api_error(self, mock_post):
        """Test API error during response generation."""
        mock_post.return_value = MagicMock(status_code=500, text="Internal Server Error")

        with self.assertRaisesRegex(Exception, "API error: 500 - Internal Server Error"):
            asyncio.run(self.llm_interface.generate_response("sys", "usr"))

    @patch('httpx.AsyncClient.post', new_callable=AsyncMock)
    def test_generate_json_response_parsing_error(self, mock_post):
        """Test error when JSON response is malformed."""
        mock_response_content = {
            "choices": [
                {"message": {"role": "assistant", "content": "This is not JSON"}}
            ]
        }
        mock_post.return_value = MagicMock(
            status_code=200, 
            json=MagicMock(return_value=mock_response_content)
        )
        with self.assertRaisesRegex(ValueError, "Failed to parse JSON response: This is not JSON"):
            asyncio.run(self.llm_interface.generate_json_response("sys", "usr"))

    @patch('httpx.AsyncClient.post', new_callable=AsyncMock)
    def test_generate_json_response_heuristic_parsing_success(self, mock_post):
        """Test successful JSON parsing with heuristics (e.g. markdown code block)."""
        mock_json_payload = {"data": "valid"}
        response_str_with_markdown = f"```json\n{json.dumps(mock_json_payload)}\n```"
        mock_response_content = {
            "choices": [
                {"message": {"role": "assistant", "content": response_str_with_markdown}}
            ]
        }
        mock_post.return_value = MagicMock(
            status_code=200, 
            json=MagicMock(return_value=mock_response_content)
        )
        response = asyncio.run(self.llm_interface.generate_json_response("sys", "usr"))
        self.assertEqual(response, mock_json_payload)

    # --- Synchronous wrapper tests ---
    @patch.object(LLMInterface, 'generate_response', new_callable=AsyncMock)
    def test_generate_response_sync_wrapper(self, mock_async_gen_response):
        """Test the synchronous wrapper for generate_response."""
        mock_async_gen_response.return_value = "sync success"
        
        response = self.llm_interface.generate_response_sync("s", "u", temperature=0.1, max_tokens=10, json_mode=True)
        self.assertEqual(response, "sync success")
        mock_async_gen_response.assert_called_once_with(
            system_prompt="s", user_prompt="u", temperature=0.1, max_tokens=10, json_mode=True
        )

    @patch.object(LLMInterface, 'generate_json_response', new_callable=AsyncMock)
    def test_generate_json_response_sync_wrapper(self, mock_async_gen_json_response):
        """Test the synchronous wrapper for generate_json_response."""
        mock_async_gen_json_response.return_value = {"sync_json": "success"}
        
        response = self.llm_interface.generate_json_response_sync("s_json", "u_json", temperature=0.2, max_tokens=20)
        self.assertEqual(response, {"sync_json": "success"})
        mock_async_gen_json_response.assert_called_once_with(
            system_prompt="s_json", user_prompt="u_json", temperature=0.2, max_tokens=20
        )

if __name__ == '__main__':
    unittest.main() 