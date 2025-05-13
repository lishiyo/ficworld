"""
PerspectiveFilter for FicWorld V1.

This module is responsible for generating a character-specific, subjective view
of the world state based on their senses, location, memory, and relationships.
It filters the objective ground truth to simulate individual perception.
"""
from typing import List, Dict, Optional, Any
import json # Added for parsing potential JSON list from LLM

from .models import WorldState, CharacterState # Assuming Pydantic models
from .data_models import SubjectiveWorldView, SubjectiveEvent, VisibleCharacterState, VisibleObjectState
# We might need CharacterState from models.py if it holds location, etc.
from .memory_manager import MemoryManager
from .llm_interface import LLMInterface # Added import
import logging # Added for logging


class PerspectiveFilter:
    """
    Generates subjective world views for characters using LLM-based inference.
    """

    def __init__(self, memory_manager: MemoryManager, llm_interface: LLMInterface):
        """
        Initialize the PerspectiveFilter.
        
        Args:
            memory_manager: An instance of MemoryManager.
            llm_interface: An instance of LLMInterface.
        """
        self.memory_manager = memory_manager
        self.llm_interface = llm_interface
        self.logger = logging.getLogger(__name__)

    def get_view_for(
        self,
        character_id: str,
        ground_truth_world_state: WorldState,
    ) -> SubjectiveWorldView:
        """
        Constructs and returns a SubjectiveWorldView for a given character using an LLM.

        Args:
            character_id: The ID of the character for whom to generate the view.
            ground_truth_world_state: The objective state of the world.
            
        Returns:
            A SubjectiveWorldView instance for the character.
        """
        self.logger.debug(f"Getting subjective view for character: {character_id}")

        char_state = ground_truth_world_state.character_states.get(character_id)
        if not char_state:
            self.logger.error(f"Character {character_id} not found in world state for get_view_for. Returning minimal view.")
            return SubjectiveWorldView(
                character_id=character_id,
                timestamp=f"scene_{ground_truth_world_state.current_scene_id}_turn_{ground_truth_world_state.turn_number}",
                perceived_location_id="unknown",
                perceived_location_description="Error: Character state missing.",
                inferred_context="Error: Character state missing, cannot generate full subjective view."
            )

        # Fetch character context (persona, goals, memories, mood, relationships)
        # Persona & Goals are directly in char_state from CharacterConfig via main.py
        persona_str = char_state.persona
        goals_str = f"Long-term: {char_state.goals}, Short-term: (Refer to CharacterConfig if more detailed structure is needed here or pass it in)"
        current_mood_str = str(char_state.current_mood)
        
        # Memory retrieval (placeholder - a real implementation would fetch relevant memories)
        # relevant_memories = self.memory_manager.retrieve_pertinent_memories(character_id, ground_truth_world_state)
        # memory_summary_str = self._format_memories_for_subjective_view_prompt(relevant_memories)
        memory_summary_str = "(Memory summary not yet implemented for subjective view context)"

        # Relationship context (placeholder - needs access to RelationshipManager)
        # For now, this is a significant simplification. A real version needs RM integration.
        # relationship_context_str = self.relationship_manager.get_context_for_perception(character_id, ground_truth_world_state)
        relationship_context_str = "(Relationship context not yet implemented for subjective view context)"

        # Prepare details of all characters for the LLM to filter from
        all_character_details_list = []
        for cid, cstate in ground_truth_world_state.character_states.items():
            all_character_details_list.append(
                f"  - ID: {cid}, Location: {cstate.location}, Conditions: {cstate.conditions}, Mood (approx): {str(cstate.current_mood)}"
            )
        all_character_details_str = "\n".join(all_character_details_list)
        
        # Object states (if available and structured in ground_truth_world_state)
        # For now, assuming object states are part of environment_description or handled by LLM implicitly.
        # object_details_str = self._format_object_states_for_prompt(ground_truth_world_state.object_states)
        object_details_str = "(Detailed object states not explicitly provided in this view generation step)"
        
        recent_objective_events_str = "\n".join([f"  - {event}" for event in ground_truth_world_state.recent_events_summary[-5:]])

        system_prompt = (
            "You are an AI expert in simulating human-like perception and generating subjective viewpoints. "
            "Given the objective state of a world and comprehensive details about a specific character "
            "(their persona, goals, memories, mood, relationships), your task is to construct their subjective "
            "understanding of the current moment. This includes what they perceive about their location, other "
            "characters, and objects, as well as their inferred context and focus. The output must be a valid JSON "
            "object matching the SubjectiveWorldView schema."
        )

        # The SubjectiveWorldView schema needs to be part of the prompt for the LLM to follow.
        # This is a simplified representation. A more robust way is to provide the full JSON schema.
        subjective_view_schema_example = """
{{
  "character_id": "{character_id}", // Fixed
  "timestamp": "scene_{ground_truth_world_state.current_scene_id}_turn_{ground_truth_world_state.turn_number}", // Fixed
  "perceived_location_id": "...string (character's current location ID)...",
  "perceived_location_description": "...string (what the character sees/hears/smells of the location)...",
  "visible_characters": [ // List of characters the character can currently perceive
    {{ "character_id": "...string...", "estimated_condition": ["...string..."], "apparent_mood": "...string...", "observed_action": "...string..." }} 
  ],
  "visible_objects": [ // List of objects the character can currently perceive
    {{ "object_id": "...string...", "observed_state": "...string...", "perceived_usability": "...string..." }}
  ],
  "recent_perceived_events": [ // List of recent events filtered through the character's perception
    {{ "timestamp": "...", "observer_id": "{character_id}", "perceived_description": "...", "inferred_actor": "...", "inferred_target": "..." }}
  ],
  "inferred_context": "...string (character's brief assessment of the situation, danger, opportunity, etc.)...",
  "active_focus_or_goal": "...string (what specific goal or detail is currently occupying their attention)..."
}}
"""

        user_prompt = f"""Generate a SubjectiveWorldView JSON object for the character '{character_id}'.

**Character '{character_id}' Context:**
- Persona: {persona_str}
- Goals: {goals_str}
- Current Mood: {current_mood_str}
- Memory Summary: {memory_summary_str}
- Relationship Context: {relationship_context_str}

**Objective Ground Truth World State:**
- Current Scene ID: {ground_truth_world_state.current_scene_id}, Turn: {ground_truth_world_state.turn_number}
- Time of Day: {ground_truth_world_state.time_of_day}
- Environment Description (general): {ground_truth_world_state.environment_description}
- Character '{character_id}' is at Location ID: {char_state.location}

- All Characters in the World (for visibility assessment):
{all_character_details_str}

- Objective Object States (if relevant and available):
{object_details_str}

- Recent Objective Events (last 5 for general awareness):
{recent_objective_events_str}

**Task:**
Based *only* on what '{character_id}' would realistically perceive, know, and infer given their context and the objective state, construct their `SubjectiveWorldView`.

Consider:
- **Location Perception:** How would they describe their current location ({char_state.location}) based on their senses?
- **Visibility:** Which other characters and key objects would they be aware of? They can only perceive things in their current location unless there's a strong sensory reason otherwise (e.g., a loud explosion elsewhere).
- **Character Perception:** For visible characters, what conditions, mood, or actions would '{character_id}' likely perceive or infer?
- **Object Perception:** For visible objects, what state or usability would they notice?
- **Event Perception:** How would recent objective events be filtered or interpreted from their POV? (For `recent_perceived_events`, you might simplify this for now, or describe 1-2 key recent events as perceived by '{character_id}').
- **Inferred Context:** What is their immediate understanding or assessment of the situation?
- **Focus:** What might be their current primary focus or active short-term goal influencing their perception?

Return ONLY the JSON object conforming to the SubjectiveWorldView schema. An example structure (you must fill in the actual perceived details):
{subjective_view_schema_example}
"""

        default_view = SubjectiveWorldView(
            character_id=character_id,
            timestamp=f"scene_{ground_truth_world_state.current_scene_id}_turn_{ground_truth_world_state.turn_number}",
            perceived_location_id=char_state.location if char_state else "unknown",
            perceived_location_description=f"(Default basic perception) You are in {char_state.location if char_state else 'an unknown place'}.",
            inferred_context="Awaiting detailed subjective perception from LLM."
        )

        try:
            response_json = self.llm_interface.generate_json_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.6 # Allow for some inferential creativity
            )
            self.logger.debug(f"LLM response for get_view_for for {character_id}: {response_json}")

            if response_json and isinstance(response_json, dict):
                # Validate and construct SubjectiveWorldView from response_json
                # Pydantic will raise validation errors if schema doesn't match.
                return SubjectiveWorldView(**response_json)
            else:
                self.logger.warning(f"LLM response for subjective view for {character_id} was not a dict or was empty. Using default. Response: {response_json}")
                return default_view

        except Exception as e:
            self.logger.error(f"Error in get_view_for LLM call for {character_id}: {e}. Using default.")
            return default_view

    def get_observers(
        self, 
        factual_outcome: str,
        ground_truth_world_state: WorldState,
        event_location_id: Optional[str] = None 
    ) -> List[str]:
        """
        Determines which characters likely perceived an objective factual_outcome using an LLM.
        
        Args:
            factual_outcome: The objective outcome string.
            ground_truth_world_state: The current objective world state.
            event_location_id: The location ID where the event primarily occurred.

        Returns:
            A list of character IDs who likely observed the event.
        """
        self.logger.debug(f"Getting observers for outcome: '{factual_outcome}' at location: {event_location_id}")
        
        character_details_list = []
        for char_id, char_state in ground_truth_world_state.character_states.items():
            character_details_list.append(f"- {char_id} (Location: {char_state.location}, Conditions: {char_state.conditions})")
        character_details_str = "\n".join(character_details_list)

        system_prompt = (
            "You are an expert observer assessing a scene. Given a factual event and character locations, "
            "determine which characters likely perceived this event. Consider proximity, potential line of sight "
            "(based on being in the same location), and the nature of the event (e.g., a loud explosion vs. a whisper)."
        )

        user_prompt = (
            f"Objective Factual Event: '{factual_outcome}'\n"
            f"Event Location ID: {event_location_id if event_location_id else 'Not explicitly specified, assume actor\'s location if discernible from event, or general proximity if not.'}\n\n"
            f"Scene Context:\n"
            f"Environment: {ground_truth_world_state.environment_description}\n"
            f"Time: {ground_truth_world_state.time_of_day}\n\n"
            f"Characters Present in World (and their current states):\n"
            f"{character_details_str}\n\n"
            "Based on all this, who likely observed this event? List only their character IDs. "
            "If anyone, return a JSON list of character ID strings, e.g., [\"Alice\", \"Bob\"]. "
            "If no one likely observed it, return an empty list []."
        )

        try:
            response_str = self.llm_interface.generate_response_sync(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2 # Low temp for more deterministic output
            )
            self.logger.debug(f"LLM response for get_observers: {response_str}")
            
            # Attempt to parse as JSON list
            try:
                observers = json.loads(response_str)
                if isinstance(observers, list) and all(isinstance(obs_id, str) for obs_id in observers):
                    # Validate that observer IDs are actual characters in the world state
                    valid_observers = [obs_id for obs_id in observers if obs_id in ground_truth_world_state.character_states]
                    if len(valid_observers) != len(observers):
                        self.logger.warning(f"LLM listed non-existent characters as observers: {set(observers) - set(valid_observers)}. Filtered.")
                    return valid_observers
                else:
                    self.logger.warning(f"LLM response for observers was not a list of strings: {response_str}. Falling back to rule-based.")
            except json.JSONDecodeError:
                self.logger.warning(f"LLM response for observers was not valid JSON: {response_str}. Falling back to rule-based.")

            # Fallback to rule-based if LLM fails or returns invalid format
            # This is the previous rule-based logic
            if event_location_id:
                rule_based_observers = []
                for char_id, char_state in ground_truth_world_state.character_states.items():
                    if char_state.location == event_location_id:
                        rule_based_observers.append(char_id)
                self.logger.info(f"Fell back to rule-based observers for event at {event_location_id}: {rule_based_observers}")
                return rule_based_observers
            return [] # If no event_location_id and LLM failed, return empty list by default for rule-based.

        except Exception as e:
            self.logger.error(f"Error in get_observers LLM call: {e}. Falling back to rule-based.")
            # Fallback (same as above)
            if event_location_id:
                rule_based_observers = []
                for char_id, char_state in ground_truth_world_state.character_states.items():
                    if char_state.location == event_location_id:
                        rule_based_observers.append(char_id)
                self.logger.info(f"Error fallback to rule-based observers for event at {event_location_id}: {rule_based_observers}")
                return rule_based_observers
            return []

    def get_subjective_event(
        self,
        observer_id: str,
        factual_outcome: str, # The objective event description
        ground_truth_world_state: WorldState, # To get observer's state, location etc.
        actor_id: Optional[str] = None,
        target_id: Optional[str] = None
    ) -> SubjectiveEvent:
        """
        Generates the SubjectiveEvent data for a specific observer based on an objective outcome using an LLM.
        Filters or rephrases the factual_outcome based on the observer's likely perception.

        Args:
            observer_id: The ID of the character observing the event.
            factual_outcome: The objective string description of what happened.
            ground_truth_world_state: The current objective world state.
            actor_id: The ID of the character who performed the action (optional).
            target_id: The ID of the character targeted by the action (optional).

        Returns:
            A SubjectiveEvent instance.
        """
        self.logger.debug(f"Getting subjective event for observer: {observer_id}, outcome: '{factual_outcome}'")

        observer_state = ground_truth_world_state.character_states.get(observer_id)
        if not observer_state:
            self.logger.warning(f"Observer {observer_id} not found in world state. Returning generic subjective event.")
            return SubjectiveEvent(
                timestamp=f"scene_{ground_truth_world_state.current_scene_id}_turn_{ground_truth_world_state.turn_number}",
                observer_id=observer_id,
                perceived_description=f"(Unable to determine precise perception for {observer_id}): {factual_outcome}",
                inferred_actor=actor_id,
                inferred_target=target_id
            )

        # Basic observer context (more can be added, e.g., relationships, memories via self.memory_manager)
        observer_context_parts = [
            f"Observer: {observer_id}",
            f"Observer's Location: {observer_state.location}",
            f"Observer's Current Conditions: {observer_state.conditions}",
            f"Observer's Current Mood (approx): {str(observer_state.current_mood)}", # Basic string representation
            f"Event Actor (if known): {actor_id if actor_id else 'Unknown'}",
            f"Event Target (if known): {target_id if target_id else 'N/A'}"
        ]
        observer_context_str = "\n".join(observer_context_parts)
        
        system_prompt = (
            "You are an expert in human perception and narrative. Given an objective event, an observer's context, "
            "and the overall world state, describe how the observer would subjectively perceive that event. "
            "Consider their physical senses, emotional state, relationship to those involved, and potential biases. "
            "The output must be a JSON object matching the SubjectiveEvent schema."
        )

        user_prompt = f"""Objective Factual Event: '{factual_outcome}'

Observer Context:
{observer_context_str}

Overall World Context:
Environment: {ground_truth_world_state.environment_description}
Time: {ground_truth_world_state.time_of_day}

Task: Generate a JSON object describing this event from the observer's perspective. Fill in the following fields:

- perceived_description: How would '{observer_id}' describe what they saw/heard/felt? Make it concise and in the first person from their perspective if appropriate, or third person descriptive of their perception.

- inferred_actor: Who does '{observer_id}' think caused the event? (string ID or "someone unknown")

- inferred_target: Who does '{observer_id}' think was the target of the event? (string ID, "self" if observer_id is target, or "N/A")

Return ONLY the JSON object for SubjectiveEvent (excluding timestamp and observer_id, which are fixed).

Example JSON structure for output (fill in the ... values):

{{
  "perceived_description": "...",
  "inferred_actor": "...",
  "inferred_target": "..."
}}
""" # End of f-string

        default_subjective_event = SubjectiveEvent(
            timestamp=f"scene_{ground_truth_world_state.current_scene_id}_turn_{ground_truth_world_state.turn_number}",
            observer_id=observer_id,
            perceived_description=f"(Standard perception for {observer_id}): {factual_outcome}",
            inferred_actor=actor_id,
            inferred_target=target_id
        )

        try:
            response_json = self.llm_interface.generate_json_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.5 # Moderate temp for some interpretive ability
            )
            self.logger.debug(f"LLM response for get_subjective_event for {observer_id}: {response_json}")

            if response_json and isinstance(response_json, dict):
                return SubjectiveEvent(
                    timestamp=default_subjective_event.timestamp,
                    observer_id=observer_id,
                    perceived_description=response_json.get("perceived_description", default_subjective_event.perceived_description),
                    inferred_actor=response_json.get("inferred_actor", default_subjective_event.inferred_actor),
                    inferred_target=response_json.get("inferred_target", default_subjective_event.inferred_target)
                )
            else:
                self.logger.warning(f"LLM response for subjective event for {observer_id} was not a dict or was empty. Using default. Response: {response_json}")
                return default_subjective_event

        except Exception as e:
            self.logger.error(f"Error in get_subjective_event LLM call for {observer_id}: {e}. Using default.")
            return default_subjective_event 