import unittest
from unittest.mock import MagicMock
import sys
from pathlib import Path
import json

# Add project root to sys.path if necessary
if str(Path.cwd().parent) not in sys.path: # Assuming tests are in a 'tests' subdirectory
    sys.path.insert(0, str(Path.cwd().parent))
if str(Path.cwd()) not in sys.path: # If tests are in the root, Path.cwd() is the project root
    sys.path.insert(0, str(Path.cwd()))

from modules.character_agent import CharacterAgent
from modules.models import MoodVector, WorldState # Assuming WorldState is used here
from modules.data_models import CharacterConfig, InitialGoals


class TestCharacterAgentV1(unittest.TestCase):

    def setUp(self):
        self.mock_llm_interface = MagicMock()
        self.mock_memory_manager = MagicMock()

        self.char_v1_config_data = {
            "full_name": "Sir Kaelan the Bold",
            "persona": "A brave knight, haunted by a past failure.",
            "backstory": "Once the King's champion, he failed to protect the prince. Now seeks redemption.",
            "initial_goals": {
                "long_term": ["Redeem his honor", "Find the true culprit"],
                "short_term": ["Gather clues about the prince's disappearance", "Protect the innocent"]
            },
            "activity_coefficient": 0.9,
            "starting_mood": {"determination": 0.8, "sadness": 0.4, "joy": 0.1}
        }
        self.character_config_v1 = CharacterConfig(**self.char_v1_config_data)

        self.agent_v1 = CharacterAgent(
            character_config=self.character_config_v1,
            llm_interface=self.mock_llm_interface,
            memory_manager=self.mock_memory_manager
        )

        # Dummy world state for prompt context (simplified)
        self.dummy_world_state = WorldState(
            current_scene_id="scene_1", turn_number=1, time_of_day="noon",
            environment_description="a bustling marketplace",
            active_characters=["Sir Kaelan the Bold", "Mysterious Merchant"],
            character_states={ # Simplified for testing prompts
                "Sir Kaelan the Bold": MagicMock(location="marketplace_center"),
                "Mysterious Merchant": MagicMock(location="stall_3")
            },
            recent_events_summary=["A child bumps into Sir Kaelan.", "The Mysterious Merchant eyes Sir Kaelan curiously."]
        )
        self.dummy_memories = [
            MagicMock(event_description="Recalled the King's stern words about failure."),
            MagicMock(event_description="Saw a hooded figure near the prince's chambers years ago.")
        ]

    def test_v1_character_agent_initialization(self):
        self.assertEqual(self.agent_v1.full_name, "Sir Kaelan the Bold")
        self.assertEqual(self.agent_v1.persona, self.char_v1_config_data["persona"])
        self.assertEqual(self.agent_v1.backstory, self.char_v1_config_data["backstory"])
        self.assertIsInstance(self.agent_v1.initial_goals, InitialGoals)
        self.assertEqual(self.agent_v1.initial_goals.long_term, ["Redeem his honor", "Find the true culprit"])
        self.assertEqual(self.agent_v1.initial_goals.short_term, ["Gather clues about the prince's disappearance", "Protect the innocent"])
        self.assertEqual(self.agent_v1.activity_coefficient, 0.9)
        
        # The CharacterAgent's __init__ will convert the starting_mood dict
        # to a MoodVector. It will only pick out the standard mood keys.
        # "determination" is not a standard key in MoodVector, so it's ignored during conversion.
        expected_mood = MoodVector(joy=0.1, sadness=0.4, fear=0.0, anger=0.0, surprise=0.0, trust=0.0)
        
        self.assertEqual(self.agent_v1.current_mood.joy, expected_mood.joy)
        self.assertEqual(self.agent_v1.current_mood.sadness, expected_mood.sadness)
        self.assertEqual(self.agent_v1.current_mood.fear, expected_mood.fear)
        self.assertEqual(self.agent_v1.current_mood.anger, expected_mood.anger)
        self.assertEqual(self.agent_v1.current_mood.surprise, expected_mood.surprise)
        self.assertEqual(self.agent_v1.current_mood.trust, expected_mood.trust)
        # Ensure no other fields like 'determination' are present
        self.assertFalse(hasattr(self.agent_v1.current_mood, 'determination'))

    def test_v1_prepare_character_system_prompt(self):
        relationship_context = "Friendly with Guard Captain. Wary of the Court Jester."
        scene_summary_context = "Summary of Scene 1: Investigated the market, found a strange symbol."
        
        prompt = self.agent_v1._prepare_character_system_prompt(
            relevant_memories=self.dummy_memories,
            world_state=self.dummy_world_state, # For general context if used
            relationship_summary_context=relationship_context,
            scene_summary_context=scene_summary_context
        )

        self.assertIn(self.agent_v1.full_name, prompt)
        self.assertIn(self.agent_v1.persona, prompt)
        self.assertIn(self.agent_v1.backstory, prompt)
        self.assertIn("Redeem his honor", prompt) # Long-term goal
        self.assertIn("Protect the innocent", prompt) # Short-term goal
        self.assertIn(json.dumps(self.agent_v1.current_mood.__dict__), prompt)
        self.assertIn(relationship_context, prompt)
        self.assertIn(scene_summary_context, prompt)
        self.assertIn("Recalled the King's stern words", prompt) # Memory
        self.assertIn("You must always act, speak, and think internally", prompt)
        self.assertIn("your understanding of recent events", prompt)

    def test_v1_prepare_reflection_prompt(self):
        subjective_view = "{\"perceived_location\": \"market square - crowded\", \"visible_characters\": {\"Mysterious Merchant\": {\"action\": \"observing\"}}}"
        subjective_events = "A pickpocket tried to snatch your coin purse, but you stopped him."
        plot_context = "Current Beat: The Investigation Deepens. Objective: Find who sells these symbols."
        relationship_context = "You distrust the Merchant due to his shifty eyes."

        prompt = self.agent_v1._prepare_reflection_prompt(
            world_state=self.dummy_world_state, # Fallback if others are None
            relevant_memories=self.dummy_memories, # Fallback
            subjective_world_view_json=subjective_view,
            recent_subjective_events_str=subjective_events,
            plot_context_str=plot_context,
            relationship_context_str=relationship_context
        )
        self.assertIn(subjective_view, prompt)
        self.assertIn(subjective_events, prompt)
        self.assertIn(plot_context, prompt)
        self.assertIn(relationship_context, prompt)
        self.assertIn(self.agent_v1.full_name, prompt)
        self.assertIn("Reflect silently.", prompt)
        self.assertIn("your persona (`" + self.agent_v1.persona, prompt)
        self.assertIn("your backstory, your goals", prompt)
        self.assertIn(self.agent_v1.initial_goals.short_term[0], prompt)

    def test_v1_prepare_plan_prompt(self):
        internal_thought = "The Merchant knows something. I must approach him, but carefully."
        subjective_view = "{\"perceived_location\": \"market square - near Merchant's stall\", \"visible_characters\": {\"Mysterious Merchant\": {\"status\": \"idle\"}}}"
        subjective_events = "The pickpocket incident created a momentary distraction."
        plot_context = "Current Beat: Confronting Suspects. Objective: Get information from Merchant."
        relationship_context = "The Merchant seems wary of you."

        prompt = self.agent_v1._prepare_plan_prompt(
            world_state=self.dummy_world_state, # Fallback
            relevant_memories=self.dummy_memories, # Fallback
            internal_thought_summary=internal_thought,
            subjective_world_view_json=subjective_view,
            recent_public_exchanges_subjective_str=subjective_events,
            plot_context_str=plot_context,
            relationship_context_str=relationship_context
        )

        self.assertIn(subjective_view, prompt)
        self.assertIn(subjective_events, prompt)
        self.assertIn(plot_context, prompt)
        self.assertIn(relationship_context, prompt)
        self.assertIn(internal_thought, prompt)
        self.assertIn(self.agent_v1.full_name, prompt)
        self.assertIn("what is your next public action or dialogue?", prompt)
        self.assertIn("Advance your short-term or long-term goals.", prompt)
        self.assertIn("Interact with an object/environment", prompt)
        self.assertIn("Return your response ONLY as a JSON object", prompt)
        self.assertIn("target_char_id", prompt) # Check for V1 plan schema hint


if __name__ == '__main__':
    unittest.main() 