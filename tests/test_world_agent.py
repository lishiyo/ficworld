import unittest
from unittest.mock import Mock, MagicMock, patch
import json
import random

from modules.world_agent import WorldAgent
from modules.models import WorldDefinition, Location, CharacterState


class TestWorldAgent(unittest.TestCase):
    def setUp(self):
        # Create a mock world definition
        self.world_definition = WorldDefinition(
            world_name="Test World",
            description="A test world for unit testing",
            global_lore={"magic_system": "None", "key_factions": []},
            locations=[
                Location(
                    id="town_square",
                    name="Town Square",
                    description="The central square of the town",
                    connections=["forest_path"]
                ),
                Location(
                    id="forest_path",
                    name="Forest Path",
                    description="A path leading into the forest",
                    connections=["town_square", "old_ruins"]
                ),
                Location(
                    id="old_ruins",
                    name="Old Ruins",
                    description="Ancient ruins in the forest",
                    connections=["forest_path"]
                )
            ],
            script_beats=[
                {
                    "scene_id": 1,
                    "beat_id": "arrival",
                    "description": "Characters arrive in town",
                    "required_location": "town_square"
                },
                {
                    "scene_id": 2,
                    "beat_id": "discovery",
                    "description": "Characters discover something in the ruins",
                    "required_location": "old_ruins",
                    "triggers_event": "ancient_artifact"
                }
            ],
            world_events_pool=[
                {
                    "event_id": "sudden_storm",
                    "description": "A sudden storm rolls in, bringing heavy rain.",
                    "effects": ["visibility_reduced"]
                },
                {
                    "event_id": "ancient_artifact",
                    "description": "A glowing artifact is discovered among the rubble.",
                    "effects": ["magical_presence"]
                }
            ]
        )
        
        # Mock LLM interface
        self.llm_interface = Mock()
        self.llm_interface.generate_response = MagicMock(return_value="A distant howl echoes through the trees.")
        
        # Character data with activity coefficients
        self.characters_data = {
            "Knight": {
                "persona": "A brave knight",
                "goals": ["protect the realm"],
                "activity": 0.8,
                "starting_mood": {"joy": 0.2, "fear": 0.1, "anger": 0.0,
                                  "sadness": 0.1, "surprise": 0.0, "trust": 0.6}
            },
            "Scholar": {
                "persona": "A curious scholar",
                "goals": ["discover ancient knowledge"],
                "activity": 0.6,
                "starting_mood": {"joy": 0.3, "fear": 0.2, "anger": 0.0,
                                  "sadness": 0.0, "surprise": 0.4, "trust": 0.3}
            },
            "Rogue": {
                "persona": "A sneaky rogue",
                "goals": ["find valuable treasures"],
                "activity": 1.0,
                "starting_mood": {"joy": 0.4, "fear": 0.1, "anger": 0.1,
                                 "sadness": 0.0, "surprise": 0.2, "trust": 0.1}
            }
        }
        
        # Create WorldAgent instance (relying on default config values for thresholds)
        self.world_agent = WorldAgent(
            world_definition=self.world_definition,
            llm_interface=self.llm_interface,
            characters_data=self.characters_data
        )
    
    def test_init(self):
        """Test WorldAgent initialization"""
        # Check that world_state was initialized correctly
        self.assertEqual(self.world_agent.world_state.current_scene_id, "scene_1")
        self.assertEqual(self.world_agent.world_state.turn_number, 0)
        self.assertEqual(self.world_agent.world_state.time_of_day, "morning")
        self.assertEqual(self.world_agent.world_state.environment_description, self.world_definition.description)
        
        # Check that all characters are active
        self.assertEqual(set(self.world_agent.world_state.active_characters), set(self.characters_data.keys()))
        
        # Check character states
        for char_name in self.characters_data:
            self.assertIn(char_name, self.world_agent.world_state.character_states)
            character_state_obj = self.world_agent.world_state.character_states[char_name]
            self.assertEqual(character_state_obj.location, "town_square")
            self.assertEqual(character_state_obj.current_mood, self.characters_data[char_name]["starting_mood"])
        
        # Check configurable parameters are set to defaults
        self.assertEqual(self.world_agent.max_turns_per_scene, 20)
        self.assertEqual(self.world_agent.stagnation_detection_threshold, 3)
        self.assertEqual(self.world_agent.llm_event_injection_override_chance, 0.05)
        self.assertEqual(self.world_agent.fallback_event_injection_chance, 0.15)
        self.assertEqual(self.world_agent.recent_events_history_limit, 10)
    
    def test_init_scene(self):
        """Test initializing a new scene"""
        # First, modify the current state a bit
        self.world_agent.world_state.turn_number = 5
        self.world_agent.world_state.recent_events_summary = ["Event 1", "Event 2"]
        
        # Initialize scene 2
        new_state = self.world_agent.init_scene(2)
        
        # Check that scene was updated correctly
        self.assertEqual(new_state.current_scene_id, "scene_2")
        self.assertEqual(new_state.turn_number, 0)  # Reset
        self.assertEqual(new_state.recent_events_summary, [])  # Reset
        
        # Test auto-increment scene number
        self.world_agent.init_scene()
        self.assertEqual(self.world_agent.world_state.current_scene_id, "scene_3")
    
    def test_judge_scene_end_by_turn_count(self):
        """Test scene ending due to high turn count"""
        # Set a high turn number, exceeding the configured max
        self.world_agent.world_state.turn_number = self.world_agent.max_turns_per_scene + 1
        
        # Empty log
        scene_log = []
        
        # Should end due to high turn count
        self.assertTrue(self.world_agent.judge_scene_end(scene_log))
    
    def test_judge_scene_end_llm_decision(self):
        """Test scene ending based on LLM decision"""
        # Mock the LLM to return "yes"
        self.llm_interface.generate_response.return_value = "yes"
        
        # Create a log with a few events
        scene_log = [
            {"outcome": "Knight draws his sword."},
            {"outcome": "Scholar examines the ancient text."},
            {"outcome": "Rogue sneaks around the perimeter."}
        ]
        
        # Ensure turn count is below max_turns_per_scene for this test
        self.world_agent.world_state.turn_number = 5
        
        # Should end due to LLM saying "yes"
        self.assertTrue(self.world_agent.judge_scene_end(scene_log))
        
        # Verify LLM was called with appropriate prompts
        self.llm_interface.generate_response.assert_called_once()
        args, kwargs = self.llm_interface.generate_response.call_args
        self.assertIn("evaluate", kwargs.get("system_prompt", ""))
        self.assertIn("scene has reached", kwargs.get("system_prompt", ""))
        
        # Reset mock and test "no" response
        self.llm_interface.generate_response.reset_mock()
        self.llm_interface.generate_response.return_value = "no"
        
        # Should not end when LLM says "no"
        self.assertFalse(self.world_agent.judge_scene_end(scene_log))
        
        # Test fallback behavior with LLM exception
        self.llm_interface.generate_response.reset_mock()
        self.llm_interface.generate_response.side_effect = Exception("LLM error")
        
        # Should use fallback stagnation checks
        # Create a log that would trigger stagnation fallback
        stagnant_log = [
            {"outcome": "Short."},
            {"outcome": "Also short."},
            {"outcome": "Very short."}
        ] * self.world_agent.stagnation_threshold # Ensure enough for threshold
        self.assertTrue(self.world_agent.judge_scene_end(stagnant_log))
        
        # Reset side effect
        self.llm_interface.generate_response.side_effect = None
    
    def test_choose_pov_character_llm(self):
        """Test POV character selection using LLM"""
        # Mock the LLM to return a specific character
        self.llm_interface.generate_response.return_value = "Scholar"
        
        # Get POV character
        pov_name, pov_info = self.world_agent.choose_pov_character_for_scene()
        
        # Should match the LLM's choice
        self.assertEqual(pov_name, "Scholar")
        
        # Verify LLM was called with appropriate prompts
        self.llm_interface.generate_response.assert_called_once()
        args, kwargs = self.llm_interface.generate_response.call_args
        self.assertIn("select which character", kwargs.get("system_prompt", ""))
        self.assertIn("compelling viewpoint", kwargs.get("system_prompt", ""))
        
        # Test with partial match
        self.llm_interface.generate_response.reset_mock()
        self.llm_interface.generate_response.return_value = "I think the Knight would be best because..."
        
        pov_name, pov_info = self.world_agent.choose_pov_character_for_scene()
        self.assertEqual(pov_name, "Knight")
        
        # Test with no match (should fall back to first character)
        self.llm_interface.generate_response.reset_mock()
        self.llm_interface.generate_response.return_value = "Someone else"
        
        pov_name, pov_info = self.world_agent.choose_pov_character_for_scene()
        self.assertEqual(pov_name, self.world_agent.world_state.active_characters[0])
        
        # Test with exception (should fall back to random)
        self.llm_interface.generate_response.reset_mock()
        self.llm_interface.generate_response.side_effect = Exception("LLM error")
        
        pov_name, pov_info = self.world_agent.choose_pov_character_for_scene()
        self.assertIn(pov_name, self.world_agent.world_state.active_characters)
        
        # Reset side effect
        self.llm_interface.generate_response.side_effect = None
        
        # Test with empty active characters
        self.world_agent.world_state.active_characters = []
        pov_name, pov_info = self.world_agent.choose_pov_character_for_scene()
        self.assertEqual(pov_name, "Narrator")  # Default to Narrator
    
    def test_decide_next_actor_llm(self):
        """Test actor selection using LLM"""
        # Mock the LLM to return a specific character
        self.llm_interface.generate_response.return_value = "Rogue"
        
        # Get next actor
        actor_name, actor_state = self.world_agent.decide_next_actor()
        
        # Should match the LLM's choice
        self.assertEqual(actor_name, "Rogue")
        
        # Verify LLM was called with appropriate prompts
        self.llm_interface.generate_response.assert_called_once()
        args, kwargs = self.llm_interface.generate_response.call_args
        self.assertIn("select which character should act next", kwargs.get("system_prompt", ""))
        
        # Test with partial match
        self.llm_interface.generate_response.reset_mock()
        self.llm_interface.generate_response.return_value = "I believe Knight should act next because..."
        
        actor_name, actor_state = self.world_agent.decide_next_actor()
        self.assertEqual(actor_name, "Knight")
        
        # Test with no match (should fall back to activity-based selection)
        self.llm_interface.generate_response.reset_mock()
        self.llm_interface.generate_response.return_value = "Someone else"
        
        # Set a fixed random seed for predictable selection in fallback
        with patch('random.random', return_value=0.5):
            actor_name, actor_state = self.world_agent.decide_next_actor()
            self.assertIn(actor_name, self.world_agent.world_state.active_characters)
        
        # Test with exception (should fall back to activity-based selection)
        self.llm_interface.generate_response.reset_mock()
        self.llm_interface.generate_response.side_effect = Exception("LLM error")
        
        with patch('random.random', return_value=0.5):
            actor_name, actor_state = self.world_agent.decide_next_actor()
            self.assertIn(actor_name, self.world_agent.world_state.active_characters)
        
        # Reset side effect
        self.llm_interface.generate_response.side_effect = None
        
        # Test script mode with required actor
        self.world_agent.script_mode = True
        self.world_agent.current_beat = {"beat_id": "discovery", "required_actor": "Scholar"}
        
        actor_name, actor_state = self.world_agent.decide_next_actor()
        self.assertEqual(actor_name, "Scholar")  # Should use required actor from beat
        
        # Reset script mode
        self.world_agent.script_mode = False
        self.world_agent.current_beat = None
    
    def test_should_inject_event_llm(self):
        """Test event injection decision using LLM"""
        # Mock the LLM to return "yes"
        self.llm_interface.generate_response.return_value = "yes"
        
        # Should inject when LLM says "yes"
        self.assertTrue(self.world_agent.should_inject_event())
        
        # Verify LLM was called with appropriate prompts
        self.llm_interface.generate_response.assert_called_once()
        args, kwargs = self.llm_interface.generate_response.call_args
        self.assertIn("evaluate if injecting", kwargs.get("system_prompt", ""))
        
        # Test with "no" response
        self.llm_interface.generate_response.reset_mock()
        self.llm_interface.generate_response.return_value = "no"
        
        # Force the random chance to be above threshold for llm_event_injection_override_chance
        with patch('random.random', return_value=self.world_agent.llm_event_injection_override_chance + 0.01):
            self.assertFalse(self.world_agent.should_inject_event())
        
        # Test random injection chance even with "no"
        with patch('random.random', return_value=self.world_agent.llm_event_injection_override_chance - 0.01):
            self.assertTrue(self.world_agent.should_inject_event())
        
        # Test fallback with exception
        self.llm_interface.generate_response.reset_mock()
        self.llm_interface.generate_response.side_effect = Exception("LLM error")
        
        # Should use fallback random chance
        with patch('random.random', return_value=self.world_agent.fallback_event_injection_chance - 0.01):
            self.assertTrue(self.world_agent.should_inject_event())
            
        with patch('random.random', return_value=self.world_agent.fallback_event_injection_chance + 0.01):
            self.assertFalse(self.world_agent.should_inject_event())
        
        # Reset side effect
        self.llm_interface.generate_response.side_effect = None
        
        # Test script mode trigger
        self.world_agent.script_mode = True
        self.world_agent.current_beat = {"beat_id": "discovery", "triggers_event": "ancient_artifact"}
        
        self.assertTrue(self.world_agent.should_inject_event())
    
    def test_generate_event_llm(self):
        """Test event generation using LLM and other approaches"""
        # Test LLM-based event generation
        self.llm_interface.generate_response.return_value = "A distant howl echoes through the trees."
        
        # Mock the event pool to force LLM route
        original_events = self.world_definition.world_events_pool
        self.world_definition.world_events_pool = []
        
        event = self.world_agent.generate_event()
        
        # Should use the LLM response
        self.assertEqual(event, "A distant howl echoes through the trees.")
        
        # Verify LLM was called with appropriate prompts
        self.llm_interface.generate_response.assert_called_once()
        args, kwargs = self.llm_interface.generate_response.call_args
        self.assertIn("generate a small, contextual environmental event", kwargs.get("system_prompt", ""))
        
        # Restore event pool
        self.world_definition.world_events_pool = original_events
        
        # Test random selection from event pool
        self.llm_interface.generate_response.reset_mock()
        
        # Since we're selecting randomly, just verify it returns a string
        event = self.world_agent.generate_event()
        self.assertIsInstance(event, str)
        
        # Test script-triggered event
        self.world_agent.script_mode = True
        self.world_agent.current_beat = {
            "beat_id": "discovery",
            "triggers_event": "ancient_artifact"
        }
        
        event = self.world_agent.generate_event()
        
        # Should match the predefined event description
        self.assertEqual(event, "A glowing artifact is discovered among the rubble.")
        
        # Test exception handling
        self.llm_interface.generate_response.reset_mock()
        self.llm_interface.generate_response.side_effect = Exception("LLM error")
        
        # Reset script mode and event pool to force fallback
        self.world_agent.script_mode = False
        self.world_agent.current_beat = None
        self.world_definition.world_events_pool = []
        
        # Should fall back to predefined events
        event = self.world_agent.generate_event()
        self.assertIsInstance(event, str)
        
        # Reset state
        self.llm_interface.generate_response.side_effect = None
        self.world_definition.world_events_pool = original_events
    
    def test_update_from_outcome_llm(self):
        """Test world state updates from outcome using LLM extraction"""
        # Mock LLM to return a JSON with state changes
        changes_json = """
        {
            "location_changes": {"Knight": "old_ruins"},
            "condition_changes": {"Scholar": ["fascinated", "curious"]},
            "time_changes": {"time_of_day": "evening"}
        }
        """
        self.llm_interface.generate_response.return_value = changes_json
        
        # Initial empty recent events
        self.world_agent.world_state.recent_events_summary = []
        
        # Initial state
        self.world_agent.world_state.character_states["Knight"].location = "town_square"
        self.world_agent.world_state.character_states["Scholar"].conditions = []
        self.world_agent.world_state.time_of_day = "morning"
        
        # Update with outcome
        self.world_agent.update_from_outcome("Knight travels to the old ruins while Scholar becomes fascinated by the ancient text. Evening approaches.")
        
        # Check recent events was updated, considering the limit
        self.assertLessEqual(len(self.world_agent.world_state.recent_events_summary), self.world_agent.recent_events_history_limit)
        
        # Verify LLM was called
        self.llm_interface.generate_response.assert_called_once()
        
        # Check state changes were applied
        self.assertEqual(self.world_agent.world_state.character_states["Knight"].location, "old_ruins")
        self.assertIn("fascinated", self.world_agent.world_state.character_states["Scholar"].conditions)
        self.assertEqual(self.world_agent.world_state.time_of_day, "evening")
        
        # Test with invalid JSON response
        self.llm_interface.generate_response.reset_mock()
        self.llm_interface.generate_response.return_value = "Not valid JSON"
        
        self.world_agent.update_from_outcome("Another event happens.")
        
        # Should still add to recent events even if JSON parsing fails
        self.assertLessEqual(len(self.world_agent.world_state.recent_events_summary), self.world_agent.recent_events_history_limit)
        
        # Test with exception
        self.llm_interface.generate_response.reset_mock()
        self.llm_interface.generate_response.side_effect = Exception("LLM error")
        
        self.world_agent.update_from_outcome("A third event occurs.")
        
        # Should still add to recent events even if LLM fails
        self.assertLessEqual(len(self.world_agent.world_state.recent_events_summary), self.world_agent.recent_events_history_limit)
        
        # Reset side effect
        self.llm_interface.generate_response.side_effect = None
    
    def test_apply_plan_llm(self):
        """Test applying action plans using LLM for outcome generation"""
        # Test speak action (keep this part as it also affects world_state turn_number etc.)
        speak_plan = {
            "action": "speak",
            "details": {"text": "Hello, world!"},
            "tone_of_action": "friendly"
        }
        self.llm_interface.generate_response.return_value = 'Knight says: "Hello, world!" with a friendly smile.'
        outcome_speak = self.world_agent.apply_plan("Knight", speak_plan)
        self.llm_interface.generate_response.assert_called_once()
        args, kwargs = self.llm_interface.generate_response.call_args
        self.assertIn("World Agent", kwargs.get("system_prompt", ""))
        self.assertIn("Knight", kwargs.get("user_prompt", ""))
        self.assertIn("Hello, world!", kwargs.get("user_prompt", ""))
        self.assertEqual(outcome_speak, 'Knight says: "Hello, world!" with a friendly smile.')
        self.assertEqual(self.world_agent.world_state.turn_number, 1)
        self.assertIn(outcome_speak, self.world_agent.world_state.recent_events_summary)
        
        # Test move action for Scholar
        self.llm_interface.generate_response.reset_mock()
        move_plan = {
            "action": "move",
            "details": {"target_location": "old_ruins"},
            "tone_of_action": "determined"
        }
        
        expected_outcome_text = "Scholar moves to the old ruins, carefully watching each step."
        self.llm_interface.generate_response.return_value = expected_outcome_text
        
        scholar_state_obj_at_start = self.world_agent.world_state.character_states["Scholar"]
        initial_scholar_location = scholar_state_obj_at_start.location
        print(f"TEST DEBUG (test_apply_plan_llm): START - Scholar State ID: {id(scholar_state_obj_at_start)}, Initial Location: {initial_scholar_location}")

        outcome_move = self.world_agent.apply_plan("Scholar", move_plan) 
        self.assertEqual(outcome_move, expected_outcome_text)

        scholar_state_obj_after_apply_plan = self.world_agent.world_state.character_states["Scholar"]
        location_after_apply_plan = scholar_state_obj_after_apply_plan.location
        print(f"TEST DEBUG (test_apply_plan_llm): AFTER apply_plan - Scholar State ID: {id(scholar_state_obj_after_apply_plan)}, Location: {location_after_apply_plan}")
        self.assertIs(scholar_state_obj_at_start, scholar_state_obj_after_apply_plan, "CharacterState object for Scholar was unexpectedly replaced by apply_plan")
        # At this point, location should NOT have changed yet, as apply_plan doesn't change it.
        self.assertEqual(location_after_apply_plan, initial_scholar_location, "apply_plan should not change location directly")

        # Manually set location to something different IF NEEDED for a clean test of update_from_outcome, 
        # but it should be initial_scholar_location (e.g. town_square)
        # For this specific test flow, let's ensure it's town_square for clarity if initial was different for some reason
        scholar_state_obj_after_apply_plan.location = "town_square" 
        print(f"TEST DEBUG (test_apply_plan_llm): AFTER manual reset - Scholar State ID: {id(scholar_state_obj_after_apply_plan)}, Location: {scholar_state_obj_after_apply_plan.location}")

        self.llm_interface.generate_response.reset_mock() 
        changes_json_for_move = '{"location_changes": {"Scholar": "old_ruins"}}' 
        self.llm_interface.generate_response.return_value = changes_json_for_move
        
        self.world_agent.update_from_outcome(outcome_move) 
        
        scholar_state_obj_after_update = self.world_agent.world_state.character_states["Scholar"]
        location_value_at_assertion_point = scholar_state_obj_after_update.location # Get it once
        
        print(f"TEST DEBUG (test_apply_plan_llm): BEFORE ASSERT - Scholar State ID: {id(scholar_state_obj_after_update)}, Location for assert: '{location_value_at_assertion_point}' (type: {type(location_value_at_assertion_point)})")

        self.assertIs(scholar_state_obj_after_apply_plan, scholar_state_obj_after_update, "CharacterState object for Scholar was unexpectedly replaced by update_from_outcome")

        self.assertEqual(location_value_at_assertion_point, "old_ruins", "Location not updated as expected by update_from_outcome")
        
        # Test exception handling with LLM failure in apply_plan
        self.llm_interface.generate_response.reset_mock()
        self.llm_interface.generate_response.side_effect = Exception("LLM API error")
        action_plan = {
            "action": "jump",
            "details": {"height": "very high"},
            "tone_of_action": "excited"
        }
        outcome_fallback = self.world_agent.apply_plan("Knight", action_plan)
        self.assertEqual(outcome_fallback, "Knight attempts to jump.")
        self.assertIn(outcome_fallback, self.world_agent.world_state.recent_events_summary)
        self.llm_interface.generate_response.side_effect = None


if __name__ == '__main__':
    unittest.main() 