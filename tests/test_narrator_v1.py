import unittest
from unittest.mock import MagicMock
import sys
from pathlib import Path

# Add project root to sys.path if necessary
if str(Path.cwd().parent) not in sys.path: # Assuming tests are in a 'tests' subdirectory
    sys.path.insert(0, str(Path.cwd().parent))
if str(Path.cwd()) not in sys.path: # If tests are in the root, Path.cwd() is the project root
    sys.path.insert(0, str(Path.cwd()))

from modules.narrator import Narrator
from modules.ficworld_config import DEFAULT_NARRATOR_TENSE_INSTRUCTIONS # Keep if used by TestNarratorV1

class TestNarratorV1(unittest.TestCase):

    def setUp(self):
        self.mock_llm_interface = MagicMock()
        self.narrator = Narrator(llm_interface=self.mock_llm_interface)

        self.sample_scene_log = [
            {"actor": "Alice", "outcome": "Alice opens the mysterious box.", "mood_during_action": {"curiosity": 0.8}},
            {"actor": "Alice", "outcome": "Inside, she finds a glowing amulet.", "mood_during_action": {"surprise": 0.9}}
        ]
        self.pov_char_name = "Alice"
        self.pov_char_info = {
            "persona": "A curious adventurer.",
            "goals": ["Discover ancient secrets"],
            "current_mood": {"joy": 0.3, "curiosity": 0.7} # Matches format from Narrator.render
        }

    def test_render_with_author_style(self):
        author_style = "Edgar Allan Poe"
        expected_llm_response = "It was a dark and stormy night... a very Poe-like narration."
        self.mock_llm_interface.generate_response_sync.return_value = expected_llm_response

        # Call render with the author style
        self.narrator.render(
            scene_log=self.sample_scene_log,
            pov_character_name=self.pov_char_name,
            pov_character_info=self.pov_char_info,
            author_style=author_style
        )

        # Check that generate_response_sync was called once
        self.mock_llm_interface.generate_response_sync.assert_called_once()
        
        # Get the arguments passed to generate_response_sync
        args, kwargs = self.mock_llm_interface.generate_response_sync.call_args
        system_prompt_actual = kwargs.get("system_prompt")
        
        self.assertIsNotNone(system_prompt_actual)
        self.assertIn(f"Emulate the literary writing style of: {author_style}.", system_prompt_actual)
        self.assertIn(DEFAULT_NARRATOR_TENSE_INSTRUCTIONS, system_prompt_actual)
        self.assertIn(f"focusing on {self.pov_char_name}", system_prompt_actual)

    def test_render_without_author_style(self):
        expected_llm_response = "A standard narration of events."
        self.mock_llm_interface.generate_response_sync.return_value = expected_llm_response

        # Call render without the author style
        self.narrator.render(
            scene_log=self.sample_scene_log,
            pov_character_name=self.pov_char_name,
            pov_character_info=self.pov_char_info
            # author_style is omitted
        )
        
        self.mock_llm_interface.generate_response_sync.assert_called_once()
        args, kwargs = self.mock_llm_interface.generate_response_sync.call_args
        system_prompt_actual = kwargs.get("system_prompt")

        self.assertIsNotNone(system_prompt_actual)
        self.assertIn("Write in a clear, engaging, standard literary style.", system_prompt_actual)
        self.assertNotIn("Emulate the literary writing style of: None", system_prompt_actual) # Ensure None isn't literally inserted

    def test_render_returns_llm_response_text(self):
        # Test various ways the LLM response might be structured
        test_cases = [
            "Direct string response.",
            MagicMock(text="Response from object with .text attribute."),
            {"text": "Response from dict with 'text' key."}
        ]

        for i, llm_return_val in enumerate(test_cases):
            with self.subTest(f"LLM response format case {i}"):
                self.mock_llm_interface.generate_response_sync.reset_mock()
                self.mock_llm_interface.generate_response_sync.return_value = llm_return_val

                result = self.narrator.render(self.sample_scene_log, self.pov_char_name, self.pov_char_info)
                
                if isinstance(llm_return_val, str):
                    self.assertEqual(result, llm_return_val)
                elif hasattr(llm_return_val, 'text'):
                    self.assertEqual(result, llm_return_val.text)
                elif isinstance(llm_return_val, dict):
                    self.assertEqual(result, llm_return_val['text'])
    
    def test_render_handles_llm_exception(self):
        self.mock_llm_interface.generate_response_sync.side_effect = Exception("LLM API Error")
        result = self.narrator.render(self.sample_scene_log, self.pov_char_name, self.pov_char_info)
        self.assertIn("Error: Could not generate narration. Details: LLM API Error", result)

if __name__ == '__main__':
    unittest.main() 