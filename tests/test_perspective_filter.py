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
    MoodVector,
)
from modules.llm_interface import LLMInterface
from modules.memory_manager import MemoryManager

# Sample Data (can be expanded and moved to a conftest.py later)
@pytest.fixture
def mock_llm_interface():
    mock = MagicMock(spec=LLMInterface)
    # Mock the new methods used by PerspectiveFilter
    mock.generate_json_response = MagicMock()
    mock.generate_response_sync = MagicMock()
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
        character_states={
            "char1": CharacterState(
                name="Alice",
                persona="A curious adventurer, lost in a strange land, seeks to understand this world and find an exit.",
                goals=["find exit", "understand this world"],
                current_mood=MoodVector(joy=0.2, fear=0.1, anger=0.0, sadness=0.1, surprise=0.3, trust=0.2),
                activity_coefficient=0.8,
                location="loc1",
                inventory={},
                conditions=["healthy"]
            ),
            "char2": CharacterState(
                name="Bob",
                persona="A cautious observer, always watching, aims to stay safe and document findings.",
                goals=["stay safe", "document findings"],
                current_mood=MoodVector(joy=0.1, fear=0.4, anger=0.1, sadness=0.2, surprise=0.1, trust=0.3),
                activity_coefficient=0.6,
                location="loc1",
                inventory={},
                conditions=["healthy", "alert"]
            ),
            "char3": CharacterState(
                name="Charlie",
                persona="A distant figure, prefers solitude, wishes to be left alone and find peace.",
                goals=["be left alone", "find peace"],
                current_mood=MoodVector(joy=0.1, fear=0.1, anger=0.0, sadness=0.1, surprise=0.0, trust=0.5),
                activity_coefficient=0.3,
                location="loc2",
                inventory={},
                conditions=["calm"]
            )
        },
        location_states={
            "loc1": LocationState(
                id="loc1",
                name="Forest Clearing",
                description="A sun-dappled clearing surrounded by tall, ancient trees. A narrow path leads north.",
                objects_present=["obj1", "obj2"],
                characters_present=["char1", "char2"]
            ),
            "loc2": LocationState(
                id="loc2",
                name="Dark Cave Entrance",
                description="A shadowy entrance to a cave, a cool breeze emanates from within.",
                objects_present=["obj3"],
                characters_present=["char3"]
            )
        },
        object_states={
            "obj1": ObjectState(
                id="obj1",
                name="Mysterious Box",
                description="A small, ornate wooden box. It seems locked.",
                location_id="loc1",
                state="closed",
                is_interactive=True
            ),
            "obj2": ObjectState(
                id="obj2",
                name="Old Oak Tree",
                description="A massive, ancient oak tree with sprawling branches.",
                location_id="loc1",
                state="standing",
                is_interactive=False
            ),
            "obj3": ObjectState(
                id="obj3",
                name="Loose Rocks",
                description="A pile of loose rocks near the cave mouth.",
                location_id="loc2",
                state="piled",
                is_interactive=True
            )
        },
        current_scene_id="scene1",
        turn_number=1,
        time_of_day="Noon",
        environment_description="The forest is quiet, sunlight filtering through the canopy.",
        active_characters=["char1", "char2"],
        recent_events_summary=[
            "The wind rustled the leaves.",
            "A bird chirped in the distance."
        ]
    )

# --- Tests for get_observers ---

def test_get_observers_basic(perspective_filter, mock_llm_interface, sample_world_state):
    factual_outcome = "A loud crash was heard near the old oak tree."
    event_location_id = "loc1"
    # Expected LLM response is a JSON string list
    mock_llm_interface.generate_response_sync.return_value = '["char1", "char2"]'

    observers = perspective_filter.get_observers(factual_outcome, sample_world_state, event_location_id)

    assert observers == ["char1", "char2"]
    mock_llm_interface.generate_response_sync.assert_called_once()
    call_args = mock_llm_interface.generate_response_sync.call_args
    
    # The call_args for a MagicMock are ((pos_arg1, pos_arg2, ...), {kwarg1: val1, ...})
    # Or if called with keyword arguments only, it's ((), {kwarg1: val1, ...})
    # generate_response_sync is called with system_prompt, user_prompt, temperature
    
    # We need to access the user_prompt from the keyword arguments
    kwargs = call_args[1] 
    user_prompt = kwargs.get('user_prompt')
    system_prompt = kwargs.get('system_prompt')

    assert "determine which characters likely perceived this event" in system_prompt.lower()
    assert factual_outcome in user_prompt
    assert f"Event Location ID: {event_location_id}" in user_prompt
    assert "Characters Present in World (and their current states):" in user_prompt
    assert "- char1 (Location: loc1, Conditions: ['healthy'])" in user_prompt # Example, check formatting
    assert "- char2 (Location: loc1, Conditions: ['healthy', 'alert'])" in user_prompt
    assert "- char3 (Location: loc2, Conditions: ['calm'])" in user_prompt
    assert "return a json list of character id strings" in user_prompt.lower()


def test_get_observers_no_event_location(perspective_filter, mock_llm_interface, sample_world_state):
    factual_outcome = "A whisper was heard."
    mock_llm_interface.generate_response_sync.return_value = '["char1"]'

    observers = perspective_filter.get_observers(factual_outcome, sample_world_state)

    assert observers == ["char1"]
    mock_llm_interface.generate_response_sync.assert_called_once()
    user_prompt = mock_llm_interface.generate_response_sync.call_args[1]['user_prompt']
    assert "Event Location ID: Not explicitly specified" in user_prompt
    assert factual_outcome in user_prompt

def test_get_observers_malformed_json_fallback_to_rule_based(perspective_filter, mock_llm_interface, sample_world_state):
    factual_outcome = "Something happened."
    event_location_id = "loc1" # Provide so rule-based fallback has a location
    mock_llm_interface.generate_response_sync.return_value = "not a json"

    # Rule-based fallback should find char1 and char2 at loc1
    observers = perspective_filter.get_observers(factual_outcome, sample_world_state, event_location_id)
    assert sorted(observers) == sorted(["char1", "char2"]) 

def test_get_observers_malformed_json_no_location_fallback(perspective_filter, mock_llm_interface, sample_world_state):
    factual_outcome = "Something happened."
    # No event_location_id provided for get_observers
    mock_llm_interface.generate_response_sync.return_value = "not a json"
    observers = perspective_filter.get_observers(factual_outcome, sample_world_state)
    assert observers == [] # Fallback with no location_id yields empty

def test_get_observers_llm_error_fallback_to_rule_based(perspective_filter, mock_llm_interface, sample_world_state):
    factual_outcome = "Something happened."
    event_location_id = "loc1" # Provide for rule-based
    mock_llm_interface.generate_response_sync.side_effect = Exception("LLM API Error")

    observers = perspective_filter.get_observers(factual_outcome, sample_world_state, event_location_id)
    assert sorted(observers) == sorted(["char1", "char2"]) # Rule-based fallback

def test_get_observers_llm_error_no_location_fallback(perspective_filter, mock_llm_interface, sample_world_state):
    factual_outcome = "Something happened."
    mock_llm_interface.generate_response_sync.side_effect = Exception("LLM API Error")
    observers = perspective_filter.get_observers(factual_outcome, sample_world_state) # No event_location_id
    assert observers == []


# --- Tests for get_subjective_event ---

@pytest.fixture
def sample_subjective_event_data_from_llm() -> Dict[str, Any]:
    # This is what the LLM is expected to return (no timestamp, no observer_id)
    return {
        "perceived_description": "I saw Bob examining a strange, glowing rock.",
        "inferred_actor": "char2",
        "inferred_target": "obj1" # Changed from glowing_rock_id to match sample_world_state
    }

def test_get_subjective_event_basic(perspective_filter, mock_llm_interface, sample_world_state, sample_subjective_event_data_from_llm):
    observer_id = "char1"
    factual_outcome = "Bob picked up a rock."
    actor_id = "char2"
    target_id = "obj1" # Changed to match sample_world_state object ID

    mock_llm_interface.generate_json_response.return_value = sample_subjective_event_data_from_llm

    subjective_event = perspective_filter.get_subjective_event(observer_id, factual_outcome, sample_world_state, actor_id, target_id)

    assert subjective_event is not None
    assert subjective_event.observer_id == observer_id
    # Timestamp is generated internally, check its format or existence
    assert f"scene_{sample_world_state.current_scene_id}_turn_{sample_world_state.turn_number}" in subjective_event.timestamp
    assert subjective_event.perceived_description == sample_subjective_event_data_from_llm["perceived_description"]
    assert subjective_event.inferred_actor == actor_id
    assert subjective_event.inferred_target == target_id

    mock_llm_interface.generate_json_response.assert_called_once()
    kwargs = mock_llm_interface.generate_json_response.call_args[1]
    user_prompt = kwargs['user_prompt']
    system_prompt = kwargs['system_prompt']

    assert "expert in human perception and narrative" in system_prompt
    assert f"Objective Factual Event: '{factual_outcome}'" in user_prompt
    assert f"Observer: {observer_id}" in user_prompt
    assert f"Observer's Location: {sample_world_state.character_states[observer_id].location}" in user_prompt
    assert f"Observer's Current Conditions: {sample_world_state.character_states[observer_id].conditions}" in user_prompt
    assert f"Observer's Current Mood (approx): {str(sample_world_state.character_states[observer_id].current_mood)}" in user_prompt
    assert f"Event Actor (if known): {actor_id}" in user_prompt
    assert f"Event Target (if known): {target_id}" in user_prompt
    assert "Return ONLY the JSON object for SubjectiveEvent (excluding timestamp and observer_id, which are fixed)." in user_prompt
    assert '"perceived_description": "..."' in user_prompt # Check for schema fields example


def test_get_subjective_event_no_actor_target(perspective_filter, mock_llm_interface, sample_world_state):
    observer_id = "char1"
    factual_outcome = "The wind howled."
    expected_llm_output = {"perceived_description": "The wind howled eerily."}
    mock_llm_interface.generate_json_response.return_value = expected_llm_output

    subjective_event = perspective_filter.get_subjective_event(observer_id, factual_outcome, sample_world_state)
    assert subjective_event is not None
    assert subjective_event.perceived_description == expected_llm_output["perceived_description"]
    assert subjective_event.inferred_actor is None # Based on LLM not returning it
    assert subjective_event.inferred_target is None # Based on LLM not returning it

    kwargs = mock_llm_interface.generate_json_response.call_args[1]
    user_prompt = kwargs['user_prompt']
    assert "Event Actor (if known): Unknown" in user_prompt
    assert "Event Target (if known): N/A" in user_prompt


def test_get_subjective_event_malformed_llm_response_returns_default(perspective_filter, mock_llm_interface, sample_world_state):
    observer_id = "char1"
    factual_outcome = "A sound was heard."
    mock_llm_interface.generate_json_response.return_value = None # Simulate malformed or empty response

    subjective_event = perspective_filter.get_subjective_event(observer_id, factual_outcome, sample_world_state)
    
    assert subjective_event is not None
    assert subjective_event.observer_id == observer_id
    assert subjective_event.perceived_description == f"(Standard perception for {observer_id}): {factual_outcome}"
    assert subjective_event.inferred_actor is None # Default when no actor_id passed
    assert subjective_event.inferred_target is None # Default when no target_id passed

def test_get_subjective_event_llm_error_returns_default(perspective_filter, mock_llm_interface, sample_world_state):
    observer_id = "char1"
    factual_outcome = "A sound was heard."
    mock_llm_interface.generate_json_response.side_effect = Exception("LLM API Error")

    subjective_event = perspective_filter.get_subjective_event(observer_id, factual_outcome, sample_world_state)
    
    assert subjective_event is not None
    assert subjective_event.observer_id == observer_id
    assert subjective_event.perceived_description == f"(Standard perception for {observer_id}): {factual_outcome}"


# --- Tests for get_view_for ---

@pytest.fixture
def sample_subjective_world_view_data() -> Dict[str, Any]:
    # This is the full structure expected from the LLM for get_view_for
    return {
        "character_id": "char1", # This will be overridden by the method but good for LLM mock
        "timestamp": "scene1_turn1", # This will be overridden by the method
        "perceived_location_id": "loc1",
        "perceived_location_description": "A sunny clearing, feels a bit eerie.",
        "visible_characters": [
            {"character_id": "char2", "estimated_condition": ["healthy"], "apparent_mood": "wary", "observed_action": "looking around"}
        ],
        "visible_objects": [
            {"object_id": "obj1", "observed_state": "closed, untouched", "perceived_usability": "might contain something useful"}
        ],
        "recent_perceived_events": [ # Example of how LLM might fill this
             {"timestamp": "scene1_turn0_event1", "observer_id": "char1", "perceived_description": "I thought I heard a twig snap.", "inferred_actor": "unknown", "inferred_target": None}
        ],
        "inferred_context": "I'm in a clearing with Bob. There's a strange box. I need to find a way out.",
        "active_focus_or_goal": "Examine the mysterious box."
    }

def test_get_view_for_basic(perspective_filter, mock_llm_interface, mock_memory_manager, sample_world_state, sample_subjective_world_view_data):
    character_id = "char1"
    char_state = sample_world_state.character_states[character_id]

    # Mock LLM response (this should be the direct JSON dictionary)
    mock_llm_interface.generate_json_response.return_value = sample_subjective_world_view_data

    # Memory manager is not directly used for rich content in the current get_view_for prompt, but called.
    # mock_memory_manager.retrieve_pertinent_memories.return_value = [] # If it were called

    subjective_view = perspective_filter.get_view_for(character_id, sample_world_state)

    assert subjective_view is not None
    assert subjective_view.character_id == character_id # Should be set by the method
    assert subjective_view.timestamp == sample_subjective_world_view_data["timestamp"] # Internal
    assert subjective_view.perceived_location_description == sample_subjective_world_view_data["perceived_location_description"]
    assert len(subjective_view.visible_characters) == 1
    assert subjective_view.visible_characters[0].character_id == "char2"
    assert subjective_view.inferred_context == sample_subjective_world_view_data["inferred_context"]
    assert len(subjective_view.recent_perceived_events) == 1 # From mock data

    mock_llm_interface.generate_json_response.assert_called_once()
    kwargs = mock_llm_interface.generate_json_response.call_args[1]
    user_prompt = kwargs['user_prompt']
    system_prompt = kwargs['system_prompt']


    assert "expert in simulating human-like perception" in system_prompt
    assert f"Generate a SubjectiveWorldView JSON object for the character '{character_id}'." in user_prompt
    
    # Character Context Section
    assert f"**Character '{character_id}' Context:**" in user_prompt
    assert f"- Persona: {char_state.persona}" in user_prompt
    assert "- Goals:" in user_prompt
    assert "find exit" in user_prompt
    assert "understand this world" in user_prompt
    assert f"- Current Mood: {str(char_state.current_mood)}" in user_prompt
    assert "- Memory Summary: (Memory summary not yet implemented for subjective view context)" in user_prompt
    assert "- Relationship Context: (Relationship context not yet implemented for subjective view context)" in user_prompt

    # Objective Ground Truth World State Section
    assert "**Objective Ground Truth World State:**" in user_prompt
    assert f"- Current Scene ID: {sample_world_state.current_scene_id}, Turn: {sample_world_state.turn_number}" in user_prompt
    assert f"- Character '{character_id}' is at Location ID: {char_state.location}" in user_prompt
    
    # Location Details
    loc_state = sample_world_state.location_states[char_state.location]
    assert f"You are in '{loc_state.name}' ({loc_state.id}). Description: {loc_state.description}." in user_prompt
    
    # Object Details in Location
    obj1_state = sample_world_state.object_states["obj1"]
    assert f"- {obj1_state.name} ({obj1_state.id}): {obj1_state.description} Current state: {obj1_state.state}. Interactive: {obj1_state.is_interactive}." in user_prompt
    
    # All Characters
    assert "All Characters in the World (for visibility assessment):" in user_prompt
    assert f"  - ID: char1, Location: {sample_world_state.character_states['char1'].location}" in user_prompt # Check presence
    assert f"  - ID: char2, Location: {sample_world_state.character_states['char2'].location}" in user_prompt
    assert f"  - ID: char3, Location: {sample_world_state.character_states['char3'].location}" in user_prompt

    # Recent Events
    assert "Recent Objective Events (last 5 for general awareness):" in user_prompt
    for event_summary in sample_world_state.recent_events_summary:
        assert f"  - {event_summary}" in user_prompt
        
    assert "Return ONLY the JSON object conforming to the SubjectiveWorldView schema." in user_prompt
    assert '"perceived_location_description": "...string (what the character sees/hears/smells of the location)...",' in user_prompt # Schema example check


def test_get_view_for_malformed_llm_response_returns_default(perspective_filter, mock_llm_interface, sample_world_state):
    character_id = "char1"
    mock_llm_interface.generate_json_response.return_value = None # Simulate malformed

    subjective_view = perspective_filter.get_view_for(character_id, sample_world_state)
    assert subjective_view is not None
    assert subjective_view.character_id == character_id
    assert subjective_view.perceived_location_id == sample_world_state.character_states[character_id].location
    assert "(Default basic perception)" in subjective_view.perceived_location_description
    assert subjective_view.inferred_context == "Awaiting detailed subjective perception from LLM."

def test_get_view_for_llm_error_returns_default(perspective_filter, mock_llm_interface, sample_world_state):
    character_id = "char1"
    mock_llm_interface.generate_json_response.side_effect = Exception("LLM API Error")

    subjective_view = perspective_filter.get_view_for(character_id, sample_world_state)
    assert subjective_view is not None
    assert subjective_view.character_id == character_id
    assert "(Default basic perception)" in subjective_view.perceived_location_description

def test_get_view_for_character_not_in_world_state_returns_minimal_view(perspective_filter, sample_world_state):
    character_id = "char_unknown" 
    # No mock for LLM needed as it should return early
    
    view = perspective_filter.get_view_for(character_id, sample_world_state)
    
    assert view is not None
    assert view.character_id == character_id
    assert view.timestamp == f"scene_{sample_world_state.current_scene_id}_turn_{sample_world_state.turn_number}"
    assert view.perceived_location_id == "unknown"
    assert "Error: Character state missing." in view.perceived_location_description
    assert view.inferred_context == "Error: Character state missing, cannot generate full subjective view."
    assert view.visible_characters == []
    assert view.visible_objects == []
    assert view.recent_perceived_events == []


# Remove or significantly overhaul test_get_subjective_event_prompt_details
# as its core premise of detailed relationship context from memory_manager is not
# currently reflected in perspective_filter.py (it uses placeholders).
# For now, let's remove it to avoid maintaining a test for non-existent functionality.
# If relationship context becomes a real feature, a similar test can be reinstated.

# def test_get_subjective_event_prompt_details(perspective_filter, mock_llm_interface, sample_world_state):
#     ... (Old test removed) ... 