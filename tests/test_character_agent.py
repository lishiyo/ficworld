"""
Unit tests for CharacterAgent in modules/character_agent.py.
"""
import unittest
from unittest.mock import patch, MagicMock
import logging
from pathlib import Path
import sys

# Add project root to sys.path if necessary
if str(Path.cwd()) not in sys.path:
    sys.path.insert(0, str(Path.cwd()))

from modules.character_agent import CharacterAgent
from modules.models import RoleArchetype, MoodVector, WorldState


class TestCharacterAgent(unittest.TestCase):
    
    def setUp(self):
        """Set up for each test."""
        # Mock dependencies
        self.mock_llm_interface = MagicMock()
        self.mock_memory_manager = MagicMock()
        
        # Create a sample role archetype
        self.test_role = RoleArchetype(
            archetype_name="Sir Rowan",
            persona_template="A stoic knight with a mysterious past. Bound by a code of honor, but haunted by previous failures.",
            goal_templates=["Protect the weak", "Redeem past failures"],
            activity_coefficient=0.8,
            starting_mood_template={"joy": 0.2, "fear": 0.1, "anger": 0.0, "sadness": 0.3, "surprise": 0.0, "trust": 0.7},
            icon="🛡️"
        )
        
        # Create a sample world state
        self.test_world_state = WorldState(
            current_scene_id="forest_entrance",
            turn_number=1,
            time_of_day="evening",
            environment_description="A dense, shadowy forest. A narrow path winds ahead.",
            active_characters=["Sir Rowan", "Scholar Elara"],
            character_states={
                "Sir Rowan": {
                    "location": "forest path",
                    "current_mood": MoodVector(joy=0.2, fear=0.1, anger=0.0, sadness=0.3, surprise=0.0, trust=0.7),
                    "conditions": []
                },
                "Scholar Elara": {
                    "location": "forest path",
                    "current_mood": MoodVector(joy=0.1, fear=0.4, anger=0.0, sadness=0.2, surprise=0.3, trust=0.5),
                    "conditions": []
                }
            },
            recent_events_summary=["Sir Rowan and Scholar Elara entered the forest as the sun began to set."]
        )
        
        # Sample memory entries
        self.test_memories = [
            MagicMock(event_description="Sir Rowan heard a wolf howl in the distance."),
            MagicMock(event_description="Sir Rowan noticed Scholar Elara seemed nervous.")
        ]

    def test_initialization(self):
        """Test that CharacterAgent.__init__ correctly initializes a character."""
        # Suppress logging during test
        logging.disable(logging.CRITICAL)
        
        # Create a CharacterAgent
        agent = CharacterAgent(
            role_archetype=self.test_role,
            llm_interface=self.mock_llm_interface,
            memory_manager=self.mock_memory_manager,
            initial_world_state=self.test_world_state
        )
        
        # Re-enable logging after test
        logging.disable(logging.NOTSET)
        
        # Verify core identity properties are set
        self.assertEqual(agent.name, "Sir Rowan")
        self.assertEqual(agent.persona, self.test_role.persona_template)
        self.assertEqual(agent.goals, self.test_role.goal_templates)
        self.assertEqual(agent.activity_coefficient, 0.8)
        
        # Verify emotional state is initialized from role
        expected_mood = self.test_role.to_mood_vector()
        self.assertEqual(agent.current_mood.joy, expected_mood.joy)
        self.assertEqual(agent.current_mood.fear, expected_mood.fear)
        self.assertEqual(agent.current_mood.anger, expected_mood.anger)
        self.assertEqual(agent.current_mood.sadness, expected_mood.sadness)
        self.assertEqual(agent.current_mood.surprise, expected_mood.surprise)
        self.assertEqual(agent.current_mood.trust, expected_mood.trust)
        
        # Verify dependencies are stored
        self.assertEqual(agent.llm_interface, self.mock_llm_interface)
        self.assertEqual(agent.memory_manager, self.mock_memory_manager)
        
        # Verify internal state is initialized
        self.assertEqual(agent.latest_reflection, "")

    def test_initialization_minimal(self):
        """Test initialization with minimal arguments (no initial_world_state)."""
        # Suppress logging during test
        logging.disable(logging.CRITICAL)
        
        # Create a CharacterAgent with minimal args
        agent = CharacterAgent(
            role_archetype=self.test_role,
            llm_interface=self.mock_llm_interface,
            memory_manager=self.mock_memory_manager
        )
        
        # Re-enable logging after test
        logging.disable(logging.NOTSET)
        
        # Verify basics are still set correctly
        self.assertEqual(agent.name, "Sir Rowan")
        
        # Verify mood is set from the role archetype
        expected_mood = self.test_role.to_mood_vector()
        self.assertEqual(agent.current_mood.joy, expected_mood.joy)
        self.assertEqual(agent.current_mood.fear, expected_mood.fear)
        self.assertEqual(agent.current_mood.anger, expected_mood.anger)
        self.assertEqual(agent.current_mood.sadness, expected_mood.sadness)
        self.assertEqual(agent.current_mood.surprise, expected_mood.surprise)
        self.assertEqual(agent.current_mood.trust, expected_mood.trust)
        
        # Verify dependencies are stored
        self.assertIsNotNone(agent.llm_interface)
        self.assertIsNotNone(agent.memory_manager)

    def test_prepare_character_system_prompt(self):
        """Test that _prepare_character_system_prompt correctly formats the prompt with memories and world state."""
        # Create a test agent
        agent = CharacterAgent(
            role_archetype=self.test_role,
            llm_interface=self.mock_llm_interface,
            memory_manager=self.mock_memory_manager
        )
        
        # Call the method with test data
        prompt = agent._prepare_character_system_prompt(
            relevant_memories=self.test_memories,
            world_state=self.test_world_state
        )
        
        # Verify basic structure
        self.assertIn(f"You are {agent.name}", prompt)
        self.assertIn(agent.persona, prompt)
        self.assertIn("**Key Information & Memories:**", prompt)
        
        # Verify memory content is included
        for memory in self.test_memories:
            self.assertIn(memory.event_description, prompt)
            
        # Verify world state content is included
        self.assertIn(self.test_world_state.environment_description, prompt)

    def test_prepare_character_system_prompt_defaults(self):
        """Test that _prepare_character_system_prompt works with default values."""
        # Create a test agent
        agent = CharacterAgent(
            role_archetype=self.test_role,
            llm_interface=self.mock_llm_interface,
            memory_manager=self.mock_memory_manager
        )
        
        # Call the method with no arguments
        prompt = agent._prepare_character_system_prompt()
        
        # Verify basic structure
        self.assertIn(f"You are {agent.name}", prompt)
        self.assertIn(agent.persona, prompt)
        self.assertIn("**Key Information & Memories:**", prompt)
        self.assertIn("You have no specific memories relevant to the current situation.", prompt)

    @patch('asyncio.new_event_loop')
    async def test_reflect_success(self, mock_loop):
        """Test that reflect() properly calls LLM and parses the response."""
        # Create a test agent
        agent = CharacterAgent(
            role_archetype=self.test_role,
            llm_interface=self.mock_llm_interface,
            memory_manager=self.mock_memory_manager
        )
        
        # Set up mock response from LLM
        mock_reflection = {
            "updated_mood": {
                "joy": 0.1,
                "fear": 0.3,
                "anger": 0.0,
                "sadness": 0.4,
                "surprise": 0.1,
                "trust": 0.6
            },
            "internal_thought": "I sense danger in these woods. I must remain vigilant to protect Scholar Elara."
        }
        
        # Configure the mock to return this response for any generate_json_response call
        self.mock_llm_interface.generate_json_response = MagicMock()
        self.mock_llm_interface.generate_json_response.return_value = mock_reflection
        
        # Call reflect
        result = await agent.reflect(self.test_world_state, self.test_memories)
        
        # Verify LLM was called with appropriate prompts
        self.mock_llm_interface.generate_json_response.assert_called_once()
        call_args = self.mock_llm_interface.generate_json_response.call_args[1]
        
        # Check that system prompt contains character info
        self.assertIn(agent.name, call_args['system_prompt'])
        self.assertIn(agent.persona, call_args['system_prompt'])
        
        # Check that system prompt contains memory and world state info
        for memory in self.test_memories:
            self.assertIn(memory.event_description, call_args['system_prompt'])
        self.assertIn(self.test_world_state.environment_description, call_args['system_prompt'])
        
        # Check that user prompt contains world state and memories
        self.assertIn(self.test_world_state.environment_description, call_args['user_prompt'])
        for memory in self.test_memories:
            self.assertIn(memory.event_description, call_args['user_prompt'])
        
        # Verify the returned reflection data
        self.assertEqual(result, mock_reflection)
        
        # Verify the agent's mood was updated
        self.assertEqual(agent.current_mood.fear, 0.3)  # Updated from 0.1 to 0.3
        self.assertEqual(agent.current_mood.sadness, 0.4)  # Updated from 0.3 to 0.4
        
        # Verify latest_reflection was updated
        self.assertEqual(agent.latest_reflection, mock_reflection['internal_thought'])

    @patch('asyncio.new_event_loop')
    async def test_reflect_error_handling(self, mock_loop):
        """Test that reflect() handles errors gracefully."""
        # Create a test agent
        agent = CharacterAgent(
            role_archetype=self.test_role,
            llm_interface=self.mock_llm_interface,
            memory_manager=self.mock_memory_manager
        )
        
        # Cause an error in the LLM call
        self.mock_llm_interface.generate_json_response = MagicMock(side_effect=Exception("API error"))
        
        # Call reflect
        with self.assertLogs(level='ERROR') as log:
            result = await agent.reflect(self.test_world_state, self.test_memories)
            
            # Verify error was logged
            self.assertTrue(any("Error during Sir Rowan's reflection" in message for message in log.output))
        
        # Verify the result falls back to current mood and error message
        self.assertEqual(result['updated_mood'], agent.current_mood)
        self.assertIn("Error processing reflection", result['internal_thought'])
        
        # Verify agent mood remains unchanged
        self.assertEqual(agent.current_mood, self.test_role.starting_mood)

    @patch('asyncio.new_event_loop')
    async def test_reflect_partial_response(self, mock_loop):
        """Test that reflect() handles a partial or malformed response from the LLM."""
        # Create a test agent
        agent = CharacterAgent(
            role_archetype=self.test_role,
            llm_interface=self.mock_llm_interface,
            memory_manager=self.mock_memory_manager
        )
        
        # Set up incomplete mock response from LLM (missing some mood components)
        mock_reflection = {
            "updated_mood": {
                "fear": 0.4,
                "surprise": 0.2
                # Missing other mood components
            },
            "internal_thought": "Something feels off in these woods."
        }
        
        self.mock_llm_interface.generate_json_response = MagicMock()
        self.mock_llm_interface.generate_json_response.return_value = mock_reflection
        
        # Call reflect
        result = await agent.reflect(self.test_world_state, self.test_memories)
        
        # Verify the agent's mood was partially updated but kept original values for missing components
        self.assertEqual(agent.current_mood.fear, 0.4)  # Updated from 0.1 to 0.4
        self.assertEqual(agent.current_mood.surprise, 0.2)  # Updated from 0.0 to 0.2
        self.assertEqual(agent.current_mood.joy, 0.2)  # Unchanged from starting value
        self.assertEqual(agent.current_mood.anger, 0.0)  # Unchanged from starting value
        self.assertEqual(agent.current_mood.sadness, 0.3)  # Unchanged from starting value
        self.assertEqual(agent.current_mood.trust, 0.7)  # Unchanged from starting value

    def test_reflect_sync_wrapper(self):
        """Test that the synchronous wrapper for reflect() works correctly."""
        # Create a test agent
        agent = CharacterAgent(
            role_archetype=self.test_role,
            llm_interface=self.mock_llm_interface,
            memory_manager=self.mock_memory_manager
        )
        
        # Configure a mock async reflect method
        mock_result = {
            "updated_mood": MoodVector(joy=0.1, fear=0.3, anger=0.0, sadness=0.4, surprise=0.1, trust=0.6),
            "internal_thought": "Test thought"
        }
        agent.reflect = MagicMock()
        agent.reflect.return_value = mock_result
        
        # Create a mock event loop to replace asyncio.new_event_loop
        mock_loop = MagicMock()
        mock_loop.run_until_complete = MagicMock(return_value=mock_result)
        
        # Replace asyncio.new_event_loop with our mock
        with patch('asyncio.new_event_loop', return_value=mock_loop):
            # Call the sync wrapper
            result = agent.reflect_sync(self.test_world_state, self.test_memories)
            
            # Verify the wrapper called the async method with the right args
            agent.reflect.assert_called_once_with(self.test_world_state, self.test_memories)
            
            # Verify the loop was used and then closed
            mock_loop.run_until_complete.assert_called_once()
            mock_loop.close.assert_called_once()
            
            # Verify the result is correct
            self.assertEqual(result, mock_result)
    
    @patch('asyncio.new_event_loop')
    async def test_plan_success(self, mock_loop):
        """Test that plan() properly calls LLM and parses the response."""
        # Create a test agent
        agent = CharacterAgent(
            role_archetype=self.test_role,
            llm_interface=self.mock_llm_interface,
            memory_manager=self.mock_memory_manager
        )
        
        # Mock an internal thought
        internal_thought = "I should guide us through the forest carefully."
        
        # Set up mock response from LLM
        mock_plan = {
            "action": "speak",
            "details": {
                "text": "We should proceed cautiously. This forest has many hidden dangers."
            },
            "tone_of_action": "determined"
        }
        
        # Configure the mock
        self.mock_llm_interface.generate_json_response = MagicMock()
        self.mock_llm_interface.generate_json_response.return_value = mock_plan
        
        # Call plan
        result = await agent.plan(self.test_world_state, self.test_memories, internal_thought)
        
        # Verify LLM was called with appropriate prompts
        self.mock_llm_interface.generate_json_response.assert_called_once()
        call_args = self.mock_llm_interface.generate_json_response.call_args[1]
        
        # Check that system prompt contains character info
        self.assertIn(agent.name, call_args['system_prompt'])
        self.assertIn(agent.persona, call_args['system_prompt'])
        
        # Check that system prompt contains memory and world state info
        for memory in self.test_memories:
            self.assertIn(memory.event_description, call_args['system_prompt'])
        self.assertIn(self.test_world_state.environment_description, call_args['system_prompt'])
        
        # Check that user prompt contains world state, memories, and internal thought
        self.assertIn(self.test_world_state.environment_description, call_args['user_prompt'])
        for memory in self.test_memories:
            self.assertIn(memory.event_description, call_args['user_prompt'])
        self.assertIn(internal_thought, call_args['user_prompt'])
        
        # Verify the returned plan is the mock plan
        self.assertEqual(result, mock_plan)
    
    @patch('asyncio.new_event_loop')
    async def test_plan_field_validation(self, mock_loop):
        """Test that plan() adds default values for missing fields in the response."""
        # Create a test agent
        agent = CharacterAgent(
            role_archetype=self.test_role,
            llm_interface=self.mock_llm_interface,
            memory_manager=self.mock_memory_manager
        )
        
        # Sample internal thought
        internal_thought = "I should check the surroundings."
        
        # Set up minimal mock response from LLM (missing details and tone)
        mock_plan = {
            "action": "observe_detail"
            # Missing "details" and "tone_of_action"
        }
        
        self.mock_llm_interface.generate_json_response = MagicMock()
        self.mock_llm_interface.generate_json_response.return_value = mock_plan
        
        # Call plan
        result = await agent.plan(self.test_world_state, self.test_memories, internal_thought)
        
        # Verify the result has the missing fields filled with defaults
        self.assertEqual(result["action"], "observe_detail")
        self.assertEqual(result["details"], {})  # Default empty dict
        self.assertEqual(result["tone_of_action"], "neutral")  # Default tone
    
    @patch('asyncio.new_event_loop')
    async def test_plan_error_handling(self, mock_loop):
        """Test that plan() handles errors gracefully."""
        # Create a test agent
        agent = CharacterAgent(
            role_archetype=self.test_role,
            llm_interface=self.mock_llm_interface,
            memory_manager=self.mock_memory_manager
        )
        
        # Sample internal thought
        internal_thought = "I should say something."
        
        # Cause an error in the LLM call
        self.mock_llm_interface.generate_json_response = MagicMock(side_effect=Exception("API error"))
        
        # Call plan
        with self.assertLogs(level='ERROR') as log:
            result = await agent.plan(self.test_world_state, self.test_memories, internal_thought)
            
            # Verify error was logged
            self.assertTrue(any("Error during Sir Rowan's planning" in message for message in log.output))
        
        # Verify the result falls back to a default "speak" action
        self.assertEqual(result["action"], "speak")
        self.assertIn("I... hmm", result["details"]["text"])  # Default confused response
        self.assertEqual(result["tone_of_action"], "confused")
    
    @patch('asyncio.new_event_loop')
    async def test_plan_missing_action_field(self, mock_loop):
        """Test that plan() handles a response missing the required 'action' field."""
        # Create a test agent
        agent = CharacterAgent(
            role_archetype=self.test_role,
            llm_interface=self.mock_llm_interface,
            memory_manager=self.mock_memory_manager
        )
        
        # Sample internal thought
        internal_thought = "I should do something."
        
        # Invalid response missing the required 'action' field
        mock_plan = {
            "details": {
                "text": "This is a response with no action field."
            },
            "tone_of_action": "normal"
        }
        
        self.mock_llm_interface.generate_json_response = MagicMock()
        self.mock_llm_interface.generate_json_response.return_value = mock_plan
        
        # Call plan - should raise ValueError which gets caught in the try/except
        with self.assertLogs(level='ERROR') as log:
            result = await agent.plan(self.test_world_state, self.test_memories, internal_thought)
            
            # Verify error was logged
            self.assertTrue(any("missing required 'action' field" in message for message in log.output))
        
        # Verify the result falls back to the default confused response
        self.assertEqual(result["action"], "speak")
        self.assertIn("I... hmm", result["details"]["text"])
        self.assertEqual(result["tone_of_action"], "confused")
    
    def test_plan_sync_wrapper(self):
        """Test that the synchronous wrapper for plan() works correctly."""
        # Create a test agent
        agent = CharacterAgent(
            role_archetype=self.test_role,
            llm_interface=self.mock_llm_interface,
            memory_manager=self.mock_memory_manager
        )
        
        # Sample internal thought
        internal_thought = "Test thought for planning."
        
        # Configure a mock async plan method
        mock_result = {
            "action": "speak",
            "details": {"text": "Hello there."},
            "tone_of_action": "friendly"
        }
        agent.plan = MagicMock()
        agent.plan.return_value = mock_result
        
        # Create a mock event loop to replace asyncio.new_event_loop
        mock_loop = MagicMock()
        mock_loop.run_until_complete = MagicMock(return_value=mock_result)
        
        # Replace asyncio.new_event_loop with our mock
        with patch('asyncio.new_event_loop', return_value=mock_loop):
            # Call the sync wrapper
            result = agent.plan_sync(self.test_world_state, self.test_memories, internal_thought)
            
            # Verify the wrapper called the async method with the right args
            agent.plan.assert_called_once_with(self.test_world_state, self.test_memories, internal_thought)
            
            # Verify the loop was used and then closed
            mock_loop.run_until_complete.assert_called_once()
            mock_loop.close.assert_called_once()
            
            # Verify the result is correct
            self.assertEqual(result, mock_result)


if __name__ == '__main__':
    unittest.main() 