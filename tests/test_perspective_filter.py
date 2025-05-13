import pytest
from unittest.mock import MagicMock, patch
from typing import List, Optional, Dict, Any
from datetime import datetime

from pydantic import ValidationError

# Assuming your modules are structured like this:
# from ..modules.perspective_filter import PerspectiveFilter # If running from a higher-level test runner
# from ..modules.data_models import WorldState, CharacterState, LocationState, ObjectState, SubjectiveWorldView, SubjectiveEvent, VisibleCharacterState, VisibleObjectState # Same as above

# For direct execution or if modules are in PYTHONPATH:
from modules.perspective_filter import PerspectiveFilter
from modules.data_models import (
    SubjectiveWorldView,
    SubjectiveEvent,
    VisibleCharacterState,
    VisibleObjectState,
    LocationState,
    ObjectState,
)
from modules.models import (
    WorldState,
    CharacterState,
    RoleArchetype,
    MemoryEntry,
)
from modules.llm_interface import LLMInterface
from modules.memory_manager import MemoryManager

# Sample Data (can be expanded and moved to a conftest.py later)
@pytest.fixture
def mock_llm_interface():
    mock = MagicMock(spec=LLMInterface)
    # mock.config = LLMConfig(model_name="test-model", temperature=0.7, max_tokens=150) # Add if needed
    return mock

@pytest.fixture
def mock_memory_manager():
    mock = MagicMock(spec=MemoryManager)
    return mock

@pytest.fixture
def perspective_filter(mock_llm_interface, mock_memory_manager):
    return PerspectiveFilter(llm_interface=mock_llm_interface, memory_manager=mock_memory_manager)

@pytest.fixture
def sample_world_state():
    return WorldState(
        global_event_log=[],
        character_states={
            "char1": CharacterState(
                id="char1",
                name="Alice",
                description="A curious adventurer.",
                current_mood="inquisitive",
                current_location_id="loc1",
                role_archetype=RoleArchetype(name="Adventurer", backstory="Lost in a strange land.", initial_goals={"short_term": ["find exit"], "long_term": ["understand this world"]}),
                inventory=[],
                relationships={},
                available_actions=[],
                current_plan_action=None,
                current_plan_target=None,
                current_plan_target_detail=None,
                current_plan_reasoning=None
            ),
            "char2": CharacterState(
                id="char2",
                name="Bob",
                description="A cautious observer.",
                current_mood="wary",
                current_location_id="loc1",
                role_archetype=RoleArchetype(name="Observer", backstory="Always watching.", initial_goals={"short_term": ["stay safe"], "long_term": ["document findings"]}),
                inventory=[],
                relationships={},
                available_actions=[],
                current_plan_action=None,
                current_plan_target=None,
                current_plan_target_detail=None,
                current_plan_reasoning=None
            ),
            "char3": CharacterState(
                id="char3",
                name="Charlie",
                description="A distant figure.",
                current_mood="neutral",
                current_location_id="loc2", # Different location
                role_archetype=RoleArchetype(name="Hermit", backstory="Prefers solitude.", initial_goals={"short_term": ["be left alone"], "long_term": ["find peace"]}),
                inventory=[],
                relationships={},
                available_actions=[],
                current_plan_action=None,
                current_plan_target=None,
                current_plan_target_detail=None,
                current_plan_reasoning=None
            )
        },
        location_states={
            "loc1": LocationState(id="loc1", name="Forest Clearing", description="A sun-dappled clearing.", objects_present=["obj1"], characters_present=["char1", "char2"]),
            "loc2": LocationState(id="loc2", name="Dark Cave", description="A damp, dark cave.", objects_present=[], characters_present=["char3"])
        },
        object_states={
            "obj1": ObjectState(id="obj1", name="Mysterious Box", description="A small, wooden box.", state="closed", is_interactive=True)
        },
        narrative_time="Day 1, Noon",
        current_focus_character_id="char1"
    )

# --- Tests for get_observers ---

def test_get_observers_basic(perspective_filter, mock_llm_interface, sample_world_state):
    factual_outcome = "A loud crash was heard near the old oak tree."
    event_location_id = "loc1"
    mock_llm_interface.call_llm.return_value = '''{"observers": ["char1", "char2"]}'''

    observers = perspective_filter.get_observers(factual_outcome, sample_world_state, event_location_id)

    assert observers == ["char1", "char2"]
    mock_llm_interface.call_llm.assert_called_once()
    call_args = mock_llm_interface.call_llm.call_args
    prompt = call_args[0][0] # First argument of the first call

    assert "Determine which characters likely perceived the event" in prompt
    assert factual_outcome in prompt
    assert "Character Locations:" in prompt
    assert "Alice (char1) at Forest Clearing (loc1)" in prompt
    assert "Bob (char2) at Forest Clearing (loc1)" in prompt
    assert "Charlie (char3) at Dark Cave (loc2)" in prompt # All characters should be in context for LLM
    assert "Event Location: Forest Clearing (loc1)" in prompt
    assert "Return a JSON object with a single key 'observers' containing a list of character IDs." in prompt

def test_get_observers_no_event_location(perspective_filter, mock_llm_interface, sample_world_state):
    factual_outcome = "A whisper was heard."
    mock_llm_interface.call_llm.return_value = '''{"observers": ["char1"]}'''

    observers = perspective_filter.get_observers(factual_outcome, sample_world_state)

    assert observers == ["char1"]
    mock_llm_interface.call_llm.assert_called_once()
    prompt = mock_llm_interface.call_llm.call_args[0][0]
    assert "Event Location: Not specified" in prompt
    assert "A whisper was heard." in prompt

def test_get_observers_malformed_json(perspective_filter, mock_llm_interface, sample_world_state):
    factual_outcome = "Something happened."
    mock_llm_interface.call_llm.return_value = "not a json"

    observers = perspective_filter.get_observers(factual_outcome, sample_world_state)
    assert observers == [] # Expect empty list on parse error

def test_get_observers_llm_error(perspective_filter, mock_llm_interface, sample_world_state):
    factual_outcome = "Something happened."
    mock_llm_interface.call_llm.side_effect = Exception("LLM API Error")

    observers = perspective_filter.get_observers(factual_outcome, sample_world_state)
    assert observers == [] # Expect empty list on LLM error

# --- Tests for get_subjective_event ---

@pytest.fixture
def sample_subjective_event_data() -> Dict[str, Any]:
    return {
        "timestamp": "Day 1, Noon",
        "observer_id": "char1",
        "perceived_description": "I saw Bob examining a strange, glowing rock.",
        "inferred_actor": "char2",
        "inferred_target": "glowing_rock_id"
    }

def test_get_subjective_event_basic(perspective_filter, mock_llm_interface, sample_world_state, sample_subjective_event_data):
    observer_id = "char1"
    factual_outcome = "Bob picked up a rock."
    actor_id = "char2"
    target_id = "glowing_rock_id"

    mock_llm_interface.call_llm.return_value = '''{
        "timestamp": "Day 1, Noon",
        "observer_id": "char1",
        "perceived_description": "I saw Bob examining a strange, glowing rock.",
        "inferred_actor": "char2",
        "inferred_target": "glowing_rock_id"
    }'''

    subjective_event = perspective_filter.get_subjective_event(observer_id, factual_outcome, sample_world_state, actor_id, target_id)

    assert subjective_event is not None
    assert subjective_event.observer_id == observer_id
    assert subjective_event.perceived_description == sample_subjective_event_data["perceived_description"]
    assert subjective_event.inferred_actor == actor_id
    assert subjective_event.inferred_target == target_id

    mock_llm_interface.call_llm.assert_called_once()
    prompt = mock_llm_interface.call_llm.call_args[0][0]

    assert "Re-interpret the factual event from the perspective of Alice (char1)" in prompt
    assert f"Observer's Name: Alice" in prompt
    assert f"Observer's Backstory: Lost in a strange land." in prompt
    assert f"Observer's Current Mood: inquisitive" in prompt
    assert f"Observer's Short-term Goals: find exit" in prompt
    assert f"Observer's Long-term Goals: understand this world" in prompt
    assert f"Factual Event: {factual_outcome}" in prompt
    assert f"Identified Actor: Bob (char2)" in prompt
    assert f"Identified Target: glowing_rock_id" in prompt
    assert "Provide your response as a JSON object matching the SubjectiveEvent schema" in prompt
    assert "perceived_description" in prompt # Check for schema fields

def test_get_subjective_event_no_actor_target(perspective_filter, mock_llm_interface, sample_world_state):
    observer_id = "char1"
    factual_outcome = "The wind howled."
    mock_llm_interface.call_llm.return_value = '''{
        "timestamp": "Day 1, Noon",
        "observer_id": "char1",
        "perceived_description": "The wind howled eerily."
    }'''

    subjective_event = perspective_filter.get_subjective_event(observer_id, factual_outcome, sample_world_state)
    assert subjective_event is not None
    assert subjective_event.perceived_description == "The wind howled eerily."
    assert subjective_event.inferred_actor is None
    assert subjective_event.inferred_target is None

    prompt = mock_llm_interface.call_llm.call_args[0][0]
    assert "Identified Actor: None" in prompt
    assert "Identified Target: None" in prompt


def test_get_subjective_event_malformed_json(perspective_filter, mock_llm_interface, sample_world_state):
    observer_id = "char1"
    factual_outcome = "A sound was heard."
    mock_llm_interface.call_llm.return_value = "this is not json"


    with pytest.raises(ValidationError): # Pydantic model validation will fail
        perspective_filter.get_subjective_event(observer_id, factual_outcome, sample_world_state)

def test_get_subjective_event_llm_error(perspective_filter, mock_llm_interface, sample_world_state):
    observer_id = "char1"
    factual_outcome = "A sound was heard."
    mock_llm_interface.call_llm.side_effect = Exception("LLM API Error")

    with pytest.raises(Exception, match="LLM API Error"): # Or expect None if we catch and return None
        perspective_filter.get_subjective_event(observer_id, factual_outcome, sample_world_state)


# --- Tests for get_view_for ---

@pytest.fixture
def sample_subjective_world_view_data() -> Dict[str, Any]:
    return {
        "character_id": "char1",
        "timestamp": "Day 1, Noon",
        "perceived_location_id": "loc1",
        "perceived_location_description": "A sunny clearing, feels a bit eerie.",
        "visible_characters": [
            {"character_id": "char2", "estimated_condition": ["healthy"], "apparent_mood": "wary", "observed_action": "looking around"}
        ],
        "visible_objects": [
            {"object_id": "obj1", "observed_state": "closed, untouched", "perceived_usability": "might contain something useful"}
        ],
        "recent_perceived_events": [], # Assuming empty for simplicity, or mock MemoryManager.get_recent_events_for_character
        "inferred_context": "I'm in a clearing with Bob. There's a strange box. I need to find a way out.",
        "active_focus_or_goal": "Examine the mysterious box."
    }

def test_get_view_for_basic(perspective_filter, mock_llm_interface, mock_memory_manager, sample_world_state, sample_subjective_world_view_data):
    character_id = "char1"

    # Mock memory manager calls
    mock_memories = [
        MemoryEntry(
            timestamp=datetime.now(), 
            actor_name=character_id, 
            event_description="Recalls a faint rustling in the bushes earlier.", 
            mood_at_encoding={"curiosity": 0.7, "unease": 0.3}, # Example mood vector
            significance=0.6
        ),
        MemoryEntry(
            timestamp=datetime.now(),
            actor_name=character_id,
            event_description="Saw Bob looking at the sky.",
            mood_at_encoding={"neutral": 0.9},
            significance=0.4
        )
    ]
    mock_memory_manager.retrieve.return_value = mock_memories

    mock_llm_interface.call_llm.return_value = '''{
        "character_id": "char1",
        "timestamp": "Day 1, Noon",
        "perceived_location_id": "loc1",
        "perceived_location_description": "A sunny clearing, feels a bit eerie.",
        "visible_characters": [
            {"character_id": "char2", "estimated_condition": ["healthy"], "apparent_mood": "wary", "observed_action": "looking around"}
        ],
        "visible_objects": [
            {"object_id": "obj1", "observed_state": "closed, untouched", "perceived_usability": "might contain something useful"}
        ],
        "recent_perceived_events": [],
        "inferred_context": "I'm in a clearing with Bob. There's a strange box. I need to find a way out.",
        "active_focus_or_goal": "Examine the mysterious box."
    }'''

    subjective_view = perspective_filter.get_view_for(character_id, sample_world_state)

    assert subjective_view is not None
    assert subjective_view.character_id == character_id
    assert subjective_view.perceived_location_description == sample_subjective_world_view_data["perceived_location_description"]
    assert len(subjective_view.visible_characters) == 1
    assert subjective_view.visible_characters[0].character_id == "char2"
    assert subjective_view.inferred_context == sample_subjective_world_view_data["inferred_context"]

    mock_llm_interface.call_llm.assert_called_once()
    prompt = mock_llm_interface.call_llm.call_args[0][0]

    # Check for key information in the prompt
    assert "Generate a SubjectiveWorldView for Alice (char1)" in prompt
    assert "Character Profile (Alice):" in prompt
    assert "Name: Alice" in prompt
    assert "Backstory: Lost in a strange land." in prompt
    assert "Current Mood: inquisitive" in prompt
    assert "Short-term Goals: find exit" in prompt
    assert "Long-term Goals: understand this world" in prompt
    assert "Relevant Memories:" in prompt
    assert "- Recalls a faint rustling in the bushes earlier." in prompt
    assert "- Saw Bob looking at the sky." in prompt
    assert "Ground Truth World State:" in prompt
    assert "Global Event Log (last 5):" in prompt # Check if it's passed
    assert "Character States:" in prompt
    assert "Alice (char1) is at Forest Clearing (loc1)." in prompt # Self
    assert "Bob (char2) is at Forest Clearing (loc1)." in prompt # Other char at same location
    assert "Charlie (char3) is at Dark Cave (loc2)." in prompt # Other char at different location
    assert "Location States:" in prompt
    assert "Forest Clearing (loc1):" in prompt
    assert "Dark Cave (loc2):" in prompt
    assert "Object States:" in prompt
    assert "Mysterious Box (obj1):" in prompt
    assert "Current Narrative Time: Day 1, Noon" in prompt
    assert "Your task is to interpret this information from Alice's perspective" in prompt
    assert "Consider Alice's physical location, senses, knowledge, biases, goals, and emotional state." in prompt
    assert "The output must be a JSON object that strictly adheres to the SubjectiveWorldView Pydantic model" in prompt
    # Spot check some fields of SubjectiveWorldView schema in the prompt
    assert "perceived_location_description" in prompt
    assert "visible_characters" in prompt
    assert "VisibleCharacterState" in prompt
    assert "estimated_condition" in prompt
    assert "apparent_mood" in prompt
    assert "visible_objects" in prompt
    assert "VisibleObjectState" in prompt
    assert "perceived_usability" in prompt
    assert "recent_perceived_events" in prompt # From memory manager / to be filled by LLM
    assert "SubjectiveEvent" in prompt
    assert "inferred_context" in prompt
    assert "active_focus_or_goal" in prompt


def test_get_view_for_malformed_json(perspective_filter, mock_llm_interface, mock_memory_manager, sample_world_state):
    character_id = "char1"
    mock_memory_manager.retrieve.return_value = []


    mock_llm_interface.call_llm.return_value = "this is definitely not json"

    with pytest.raises(ValidationError): # Pydantic model validation will fail
        perspective_filter.get_view_for(character_id, sample_world_state)

def test_get_view_for_llm_error(perspective_filter, mock_llm_interface, mock_memory_manager, sample_world_state):
    character_id = "char1"
    mock_memory_manager.retrieve.return_value = []

    mock_llm_interface.call_llm.side_effect = Exception("LLM API Error")

    with pytest.raises(Exception, match="LLM API Error"): # Or expect None if we catch and return None
        perspective_filter.get_view_for(character_id, sample_world_state)

def test_get_view_for_character_not_in_world_state(perspective_filter, sample_world_state):
    character_id = "char_unknown" # This character is not in sample_world_state
    with pytest.raises(ValueError, match="Character char_unknown not found in world state."):
        perspective_filter.get_view_for(character_id, sample_world_state)

# Example of how to test the prompt for get_subjective_event more deeply if needed
def test_get_subjective_event_prompt_details(perspective_filter, mock_llm_interface, sample_world_state):
    observer_id = "char1" # Alice
    actor_id = "char2"    # Bob
    target_id = "obj1"  # Mysterious Box
    factual_outcome = "Bob cautiously poked the Mysterious Box with a stick."

    # Mock specific relationship context
    perspective_filter.memory_manager.get_relationship_context_for_observer.return_value = "Alice finds Bob's caution slightly amusing but is also wary of the box."

    mock_llm_interface.call_llm.return_value = '''{
        "timestamp": "Day 1, Noon",
        "observer_id": "char1",
        "perceived_description": "Bob was being super careful with that box, poking it like it might bite!",
        "inferred_actor": "char2",
        "inferred_target": "obj1"
    }'''

    perspective_filter.get_subjective_event(observer_id, factual_outcome, sample_world_state, actor_id, target_id)
    prompt = mock_llm_interface.call_llm.call_args[0][0]

    # Observer details
    assert "Observer's Name: Alice" in prompt
    assert "Observer's Role: Adventurer" in prompt
    assert "Observer's Backstory: Lost in a strange land." in prompt
    assert "Observer's Current Mood: inquisitive" in prompt
    assert "Observer's Short-term Goals: find exit" in prompt
    assert "Observer's Long-term Goals: understand this world" in prompt

    # Relationship context (assuming target is an object, so only actor relationship matters here)
    assert "Relationship Context with Actor (Bob): Alice finds Bob's caution slightly amusing but is also wary of the box." in prompt
    assert "Relationship Context with Target (Mysterious Box): N/A (target is not a character)" in prompt


    # Event details
    assert f"Factual Event: {factual_outcome}" in prompt
    assert "Identified Actor: Bob (char2)" in prompt
    assert "Identified Target: Mysterious Box (obj1)" in prompt # Assuming it fetches target name

    # Ground truth snippets for context
    assert "Relevant Ground Truth (Observer's Location - Forest Clearing):" in prompt
    assert "Objects present: Mysterious Box (obj1)" in prompt
    assert "Characters present: Alice (char1), Bob (char2)" in prompt
    assert "Relevant Ground Truth (Actor's State - Bob):" in prompt
    assert "Current Mood: wary" in prompt
    assert "Relevant Ground Truth (Target's State - Mysterious Box):" in prompt
    assert "State: closed" in prompt

    assert "Your output should be a JSON object strictly adhering to the SubjectiveEvent Pydantic model structure." in prompt
    assert "Fields to generate: timestamp, observer_id, perceived_description, inferred_actor (optional), inferred_target (optional)." in prompt 