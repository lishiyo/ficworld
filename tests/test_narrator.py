import unittest
from unittest.mock import MagicMock, patch

from modules.narrator import Narrator
from modules.llm_interface import LLMInterface
from modules.ficworld_config import DEFAULT_NARRATOR_LITERARY_TONE, DEFAULT_NARRATOR_TENSE_INSTRUCTIONS

class TestNarrator(unittest.TestCase):
    """
    Unit tests for the Narrator class.
    """

    def setUp(self):
        """
        Set up common resources for tests.
        """
        self.mock_llm_interface = MagicMock(spec=LLMInterface)
        self.narrator = Narrator(llm_interface=self.mock_llm_interface)
        self.pov_character_name = "Alice"
        self.pov_character_info = {
            "persona": "A curious adventurer.",
            "goals": ["Explore Wonderland", "Find the white rabbit"],
            "mood": {"joy": 0.5, "surprise": 0.7, "fear": 0.1}
        }
        self.scene_log = [
            {"actor": "Alice", "outcome": "Alice saw a talking rabbit.", "mood_during_action": {"surprise": 0.8}},
            {"actor": "World", "outcome": "The rabbit hopped down a large hole."}
        ]

    def test_narrator_initialization(self):
        """
        Tests that the Narrator class initializes correctly and stores the llm_interface.
        """
        self.assertIsNotNone(self.narrator)
        self.assertEqual(self.narrator.llm_interface, self.mock_llm_interface)

    def test_render_successful_narration(self):
        """
        Tests the render method for successful narration.
        """
        expected_prose = "Alice, full of surprise, saw a talking rabbit. The world seemed to conspire as the rabbit then hopped down a large hole."
        self.mock_llm_interface.generate_response_sync.return_value = expected_prose

        prose = self.narrator.render(self.scene_log, self.pov_character_name, self.pov_character_info)

        self.assertEqual(prose, expected_prose)
        self.mock_llm_interface.generate_response_sync.assert_called_once()
        
        # Verify prompt contents (simplified check for key elements)
        args, kwargs = self.mock_llm_interface.generate_response_sync.call_args
        
        # generate_response_sync expects keyword arguments system_prompt and user_prompt
        system_prompt_arg = kwargs.get("system_prompt")
        user_prompt_arg = kwargs.get("user_prompt")

        self.assertIn("You are a masterful storyteller", system_prompt_arg)
        self.assertIn(f"focusing on {self.pov_character_name}", system_prompt_arg)
        self.assertIn(DEFAULT_NARRATOR_TENSE_INSTRUCTIONS, system_prompt_arg)
        self.assertIn(DEFAULT_NARRATOR_LITERARY_TONE, system_prompt_arg)

        self.assertIn(self.pov_character_name, user_prompt_arg)
        self.assertIn(self.pov_character_info["persona"], user_prompt_arg)
        self.assertIn(self.scene_log[0]["outcome"], user_prompt_arg)
        self.assertIn(self.scene_log[1]["outcome"], user_prompt_arg)

    def test_render_empty_scene_log(self):
        """
        Tests the render method with an empty scene log.
        """
        expected_prose = "Alice wondered what to do next in the quiet forest."
        self.mock_llm_interface.generate_response_sync.return_value = expected_prose

        empty_scene_log = []
        prose = self.narrator.render(empty_scene_log, self.pov_character_name, self.pov_character_info)
        self.assertEqual(prose, expected_prose)

        args, kwargs = self.mock_llm_interface.generate_response_sync.call_args
        user_prompt_arg = kwargs.get("user_prompt")
        self.assertIn("No specific events occurred in this scene.", user_prompt_arg)

    def test_render_llm_exception(self):
        """
        Tests the render method when the LLM interface raises an exception.
        """
        self.mock_llm_interface.generate_response_sync.side_effect = Exception("LLM API Error")

        prose = self.narrator.render(self.scene_log, self.pov_character_name, self.pov_character_info)
        self.assertIn("Error: Could not generate narration.", prose)
        self.assertIn("LLM API Error", prose)

    def test_render_llm_unexpected_response_format(self):
        """
        Tests render method with an unexpected response format from LLM.
        """
        self.mock_llm_interface.generate_response_sync.return_value = [{"some_unexpected_key": "value"}]
        prose = self.narrator.render(self.scene_log, self.pov_character_name, self.pov_character_info)
        self.assertEqual(prose, "Error: Could not generate narration due to unexpected LLM response format.")

    def test_render_llm_response_object_with_text_attribute(self):
        """
        Tests render method when LLM returns an object with a .text attribute.
        """
        class MockResponse:
            def __init__(self, text_content):
                self.text = text_content
        
        expected_prose = "Narrated text from object."
        self.mock_llm_interface.generate_response_sync.return_value = MockResponse(expected_prose)
        prose = self.narrator.render(self.scene_log, self.pov_character_name, self.pov_character_info)
        self.assertEqual(prose, expected_prose)

    def test_render_llm_response_dict_with_text_key(self):
        """
        Tests render method when LLM returns a dict with a 'text' key.
        """
        expected_prose = "Narrated text from dict."
        self.mock_llm_interface.generate_response_sync.return_value = {"text": expected_prose, "other_key": "value"}
        prose = self.narrator.render(self.scene_log, self.pov_character_name, self.pov_character_info)
        self.assertEqual(prose, expected_prose)


if __name__ == '__main__':
    unittest.main() 