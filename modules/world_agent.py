from typing import Dict, List, Tuple, Optional, Any
import random
from dataclasses import dataclass, field
import json

from .models import WorldDefinition, WorldState, CharacterState, MoodVector
from .llm_interface import LLMInterface
from .relationship_manager import RelationshipManager, RelationshipState
import logging

class WorldAgent:
    """
    The WorldAgent manages the environment, character actions, and story events.
    It acts as a director for the story, picking speakers, injecting events, and ending scenes.
    """
    
    def __init__(
        self, 
        world_definition: WorldDefinition, 
        llm_interface: LLMInterface, 
        character_states: Dict[str, CharacterState],
        relationship_manager: RelationshipManager,
        max_scene_turns: int = 20,
        stagnation_detection_threshold: int = 3,
        llm_event_injection_override_chance: float = 0.05,
        fallback_event_injection_chance: float = 0.15,
        recent_events_history_limit: int = 10
    ):
        """
        Initialize the WorldAgent.
        
        Args:
            world_definition: The WorldDefinition object containing world settings, locations, etc.
            llm_interface: The LLMInterface object for generating events (if used)
            character_states: Dictionary mapping character names to their data, including activity coefficients
            relationship_manager: The RelationshipManager object for managing character relationships
            max_scene_turns: Maximum turns before a scene is forced to end.
            stagnation_detection_threshold: Number of turns with minimal change to trigger stagnation in fallback.
            llm_event_injection_override_chance: Chance to inject event even if LLM says no.
            fallback_event_injection_chance: Chance to inject event if LLM fails.
            recent_events_history_limit: How many recent events to store in world_state.
        """
        self.world_definition = world_definition
        self.llm_interface = llm_interface
        self.character_states_initial_template = character_states
        self.relationship_manager = relationship_manager

        # Configurable parameters
        self.max_scene_turns = max_scene_turns
        self.stagnation_detection_threshold = stagnation_detection_threshold
        self.llm_event_injection_override_chance = llm_event_injection_override_chance
        self.fallback_event_injection_chance = fallback_event_injection_chance
        self.recent_events_history_limit = recent_events_history_limit
        
        # Initialize the world state
        self.world_state = WorldState(
            current_scene_id="scene_1",
            turn_number=0,
            time_of_day="morning",  # Default value, can be configured
            environment_description=world_definition.description,
            active_characters=list(character_states.keys()),
            character_states=character_states,
            recent_events_summary=[]
        )
        
        # Track stagnation for the scene_end logic
        self.previous_token_counts = []
        self.stagnation_threshold = self.stagnation_detection_threshold # Keep for existing use in judge_scene_end fallback
        
        # For script mode, if enabled in preset
        self.script_mode = False # This would typically be set from a preset config
        self.current_beat = None
        self.completed_beats = set()

    def init_scene(self, scene_number: int = None):
        """
        Initialize a new scene in the world state.
        
        Args:
            scene_number: Optional scene number. If None, increments the current scene number.
        """
        if scene_number is None:
            # Extract current scene number and increment
            try:
                current_num = int(self.world_state.current_scene_id.split('_')[-1])
                scene_number = current_num + 1
            except (ValueError, IndexError):
                scene_number = 1
                
        # Update scene id
        self.world_state.current_scene_id = f"scene_{scene_number}"
        self.world_state.turn_number = 0
        
        # Reset stagnation tracking
        self.previous_token_counts = []
        
        # Reset recent events for the new scene
        self.world_state.recent_events_summary = []
        
        # If in script mode, load relevant beats for this scene
        if self.script_mode and hasattr(self.world_definition, 'script_beats'):
            scene_beats = [beat for beat in self.world_definition.script_beats 
                          if beat.get('scene_id') == scene_number]
            if scene_beats:
                self.current_beat = scene_beats[0]  # Start with the first beat
            else:
                self.current_beat = None
                
        return self.world_state
    
    def judge_scene_end(self, scene_log: List[Dict]) -> bool:
        """
        Determine if the current scene should end based on narrative context.
        Uses LLM to evaluate scene progression unless in script mode.
        
        Args:
            scene_log: List of log entries for the current scene
            
        Returns:
            True if the scene should end, False otherwise
        """
        # If in script mode, check if all beats for this scene are completed
        if self.script_mode:
            current_scene_id = self.world_state.current_scene_id
            scene_number = int(current_scene_id.split('_')[-1])
            
            # Check if all beats for this scene are completed
            if self.current_beat is None:
                if hasattr(self.world_definition, 'script_beats') and self.world_definition.script_beats:
                    if not any(beat.get('scene_id') == scene_number 
                              and beat.get('beat_id') not in self.completed_beats 
                              for beat in self.world_definition.script_beats):
                        return True
                else: # No script beats for this world
                    pass # Fall through to other checks
        
        # Hard safety limit - prevent excessively long scenes
        if self.world_state.turn_number >= self.max_scene_turns:
            return True
            
        # If there are no events yet, continue the scene
        if len(scene_log) < 3:
            return False
            
        # Use LLM to decide if the scene should end based on narrative progression
        recent_events = [entry.get('outcome', '') for entry in scene_log[-5:]]
        recent_events_text = "\n".join(recent_events)
        
        # Create a summary of the scene progression
        scene_start_events = [entry.get('outcome', '') for entry in scene_log[:2]]
        scene_start_text = "\n".join(scene_start_events)
        
        # System prompt for scene end evaluation
        system_prompt = (
            "You are the World Agent for FicWorld, a story generation system. "
            "Your task is to evaluate whether the current scene has reached a natural conclusion "
            "or if it should continue. A good scene ending point should have some narrative closure "
            "but also leave hooks for future scenes."
        )
        
        # User prompt
        user_prompt = (
            f"Current scene: {self.world_state.current_scene_id}\n"
            f"Current turn number: {self.world_state.turn_number}\n\n"
            "Scene start events:\n"
            f"{scene_start_text}\n\n"
            "Recent events:\n"
            f"{recent_events_text}\n\n"
            "Based on these events, evaluate if this scene has reached a natural conclusion point. "
            "Consider these factors:\n"
            "1. Has the scene established and resolved a minor dramatic tension or question?\n"
            "2. Have key characters made meaningful choices or taken significant actions?\n"
            "3. Is there a natural transition point to a new location or time?\n"
            "4. Has the conversation reached a logical pause?\n"
            "5. Would ending now leave interesting threads for future scenes?\n\n"
            "Respond with ONLY 'yes' if the scene should end, or 'no' if it should continue."
        )
        
        try:
            # Get LLM decision
            response = self.llm_interface.generate_response_sync(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2  # Low temperature for more consistent decisions
            ).strip().lower()
            
            # Parse response - look for "yes" or variants
            should_end = response.startswith('yes') or 'yes' in response[:10]
            return should_end
            
        except Exception as e:
            # Fallback to simpler heuristics if LLM fails
            # Check for stagnation - minimal change in token counts across turns
            if len(scene_log) >= 3:
                # Get approximate token counts of the latest entries
                recent_tokens = [len(entry.get('outcome', '').split()) for entry in scene_log[-3:]]
                
                # If the last few entries have very little content, consider it stagnation
                if all(count < 5 for count in recent_tokens):
                    return True
                    
                # If the dialogue/events aren't changing much in length, might indicate stagnation
                token_diffs = [abs(recent_tokens[i] - recent_tokens[i-1]) for i in range(1, len(recent_tokens))]
                if all(diff < 3 for diff in token_diffs):
                    self.previous_token_counts.append(token_diffs)
                    # If we've seen minimal changes for several turns, end the scene
                    if len(self.previous_token_counts) >= self.stagnation_threshold: # Uses self.stagnation_threshold
                        return True
                else:
                    # Reset stagnation counter if we see significant changes
                    self.previous_token_counts = []
            
        # By default, continue the scene
        return False
    
    def choose_pov_character_for_scene(self, current_world_state=None) -> Tuple[str, Dict]:
        """
        Select a character to be the POV for narrating the current scene.
        Uses LLM to determine which character would make the most compelling viewpoint.
        
        Args:
            current_world_state: Optional current world state, uses self.world_state if None
            
        Returns:
            Tuple of (pov_character_name, pov_character_info)
        """
        if current_world_state is None:
            current_world_state = self.world_state
            
        active_chars = current_world_state.active_characters
        
        # If no active characters, default to Narrator
        if not active_chars:
            return "Narrator", {"persona": "Objective observer", "goals": [], "current_mood": MoodVector()}
            
        # If in script mode, we might have a predefined POV character
        # This would be an extension point for guided narrative
        
        # Use LLM to choose the most interesting POV character based on their involvement and state
        
        # Prepare character information for LLM
        character_info_list = []
        for char_name in active_chars:
            char_state = current_world_state.character_states.get(char_name)
            # char_data_from_template is a CharacterState object from the initial template
            char_data_from_template = self.character_states_initial_template.get(char_name)
            
            # Format mood for readability
            mood_str = ""
            if char_state and char_state.current_mood:
                # Convert MoodVector to a dictionary to sort by values
                mood_dict = char_state.current_mood.__dict__
                top_emotions = sorted(
                    mood_dict.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:2]  # Top 2 emotions
                mood_str = ", ".join([f"{emotion}: {value:.1f}" for emotion, value in top_emotions])
            
            persona = char_data_from_template.persona if char_data_from_template else "Unknown"
            goals = char_data_from_template.goals if char_data_from_template else ["Unknown"]

            char_info_text = (
                f"Character: {char_name}\\n"
                f"Persona: {persona}\\n"
                f"Current location: {char_state.location if char_state else 'Unknown'}\\n"
                f"Dominant mood: {mood_str}\\n"
                f"Goals: {', '.join(goals)}"
            )
            character_info_list.append(char_info_text) # Renamed from character_info to avoid conflict
        
        # Get recent events to provide context
        recent_events = current_world_state.recent_events_summary[-5:] if current_world_state.recent_events_summary else []
        recent_events_text = "\n".join(recent_events)
        
        # System prompt for POV selection
        system_prompt = (
            "You are the World Agent for FicWorld, a story generation system. "
            "Your task is to select which character would make the most compelling viewpoint "
            "character for narrating the current scene. Choose the character whose perspective "
            "would create the most engaging, emotionally resonant, or dramatically revealing narrative."
        )
        
        # User prompt
        user_prompt = (
            f"Current scene: {current_world_state.current_scene_id}\n\n"
            "Available characters and their states:\n\n"
            f"{'-'*40}\n"
            f"{('-'*40 + '\\n').join(character_info_list)}\n"
            f"{'-'*40}\n\n"
            "Recent events in the scene:\n"
            f"{recent_events_text}\n\n"
            "Based on this information, choose ONE character whose perspective would make the most "
            "compelling viewpoint for narrating this scene. Consider:\n"
            "1. Which character has the most at stake emotionally?\n"
            "2. Which character has been most active or central to recent events?\n"
            "3. Which character's perspective would reveal interesting thoughts or feelings?\n"
            "4. Which character's viewpoint would best highlight the current dramatic tensions?\n\n"
            "Respond with ONLY the name of the selected character, exactly as written above."
        )
        
        try:
            # Get LLM decision
            response = self.llm_interface.generate_response_sync(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3
            ).strip()
            
            # Try to find an exact match first
            selected_character = None
            for char_name in active_chars:
                if char_name.lower() == response.lower():
                    selected_character = char_name
                    break
                    
            # If no exact match, look for partial matches (name appears in response)
            if not selected_character:
                for char_name in active_chars:
                    if char_name.lower() in response.lower():
                        selected_character = char_name
                        break
                        
            # If still no match, default to first active character
            if not selected_character and active_chars:
                selected_character = active_chars[0]
                
            # Get character info
            char_state = current_world_state.character_states.get(selected_character)
            # char_data_from_template is a CharacterState object from the initial template
            char_data_from_template = self.character_states_initial_template.get(selected_character)
            
            pov_info = {
                "persona": char_data_from_template.persona if char_data_from_template else "",
                "goals": char_data_from_template.goals if char_data_from_template else [],
                "current_mood": char_state.current_mood if char_state and char_state.current_mood else MoodVector() # Return empty MoodVector if none
            }
            
            return selected_character, pov_info
            
        except Exception as e:
            # Fallback to random selection if LLM fails
            if not active_chars: # Ensure active_chars is not empty before random.choice
                return "Narrator", {"persona": "Objective observer", "goals": [], "current_mood": MoodVector()}
            selected_character = random.choice(active_chars)
            
            char_state = current_world_state.character_states.get(selected_character)
            # char_data_from_template is a CharacterState object from the initial template
            char_data_from_template = self.character_states_initial_template.get(selected_character)
            
            pov_info = {
                "persona": char_data_from_template.persona if char_data_from_template else "",
                "goals": char_data_from_template.goals if char_data_from_template else [],
                "current_mood": char_state.current_mood if char_state and char_state.current_mood else MoodVector()
            }
            
            return selected_character, pov_info

    def decide_next_actor(self, current_world_state=None):
        """
        Select the next character to act based on narrative flow and dramatic potential.
        Uses LLM to determine which character's action would advance the story most compellingly.
        
        Args:
            current_world_state: Optional current world state, uses self.world_state if None
            
        Returns:
            Tuple of (character_name, character_state)
        """
        if current_world_state is None:
            current_world_state = self.world_state
            
        active_chars = current_world_state.active_characters
        
        # If no active characters, return None
        if not active_chars:
            return None, None
            
        # If in script mode and there's a specific required actor for the current beat, use that
        if self.script_mode and self.current_beat and self.current_beat.get("required_actor"):
            required_actor = self.current_beat.get("required_actor")
            if required_actor in active_chars:
                char_state = current_world_state.character_states.get(required_actor)
                return required_actor, char_state
                
        # Use LLM to decide the next actor based on dramatic potential
        
        # Prepare character information for LLM
        character_descriptions = []
        for char_name in active_chars:
            char_state = current_world_state.character_states.get(char_name)
            # char_data is a CharacterState object from the initial template
            char_data_from_template = self.character_states_initial_template.get(char_name)
            
            # Format mood for readability
            mood_str = ""
            if char_state and char_state.current_mood:
                # Convert MoodVector to a dictionary to sort by values
                mood_dict = char_state.current_mood.__dict__
                top_emotions = sorted(
                    mood_dict.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:2]  # Top 2 emotions
                mood_str = ", ".join([f"{emotion}: {value:.1f}" for emotion, value in top_emotions])
            
            activity_coefficient = char_data_from_template.activity_coefficient if char_data_from_template else 1.0
            persona = char_data_from_template.persona if char_data_from_template else "Unknown"
            goals = char_data_from_template.goals if char_data_from_template else ["Unknown"]
            
            char_desc = (
                f"Character: {char_name}\\n"
                f"Persona: {persona}\\n"
                f"Current location: {char_state.location if char_state else 'Unknown'}\\n"
                f"Dominant mood: {mood_str}\\n"
                f"Activity coefficient: {activity_coefficient:.1f}\\n"
                f"Goals: {', '.join(goals)}"
            )
            character_descriptions.append(char_desc)
        
        # Get recent events for context
        recent_events = current_world_state.recent_events_summary[-5:] if current_world_state.recent_events_summary else []
        recent_events_text = "\n".join(recent_events)
        
        # Identify who acted last (if anyone)
        last_actor = None
        if recent_events:
            # Simple heuristic: look for character name at the start of the last event
            for char_name in active_chars:
                if recent_events[-1].startswith(char_name):
                    last_actor = char_name
                    break
        
        # System prompt for actor selection
        system_prompt = (
            "You are the World Agent for FicWorld, a story generation system. "
            "Your task is to select which character should act next in the narrative. "
            "Choose the character whose action would create the most interesting story development "
            "based on current character states, relationships, and recent events."
        )
        
        # User prompt
        parts = [
            f"Current scene: {current_world_state.current_scene_id}",
            f"Turn number: {current_world_state.turn_number}",
            "\nAvailable characters and their states:\n",
            f"{'-'*40}",
            *character_descriptions, # Unpack list here
            f"{'-'*40}",
            "\nRecent events in the scene:",
            recent_events_text
        ]

        if last_actor:
            parts.append(f"\nThe last character to act was: {last_actor}")
        
        parts.extend([
            "\nBased on this information, choose ONE character who should act next. Consider:",
            "1. Which character has the most reason to respond to recent events?",
            "2. Which character could introduce an interesting new element to the scene?",
            "3. Which character's goals or emotions would drive them to act now?",
            "4. Which character hasn't acted in a while but has a stake in the scene?",
            "5. Which character's action would create interesting dramatic tension?",
            "\nRespond with ONLY the name of the selected character, exactly as written above."
        ])
        user_prompt = "\n".join(parts)
        
        try:
            # Get LLM decision
            response = self.llm_interface.generate_response_sync(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3
            ).strip()
            
            # Try to find an exact match first
            selected_actor = None
            for char_name in active_chars:
                if char_name.lower() == response.lower():
                    selected_actor = char_name
                    break
                    
            # If no exact match, look for partial matches
            if not selected_actor:
                for char_name in active_chars:
                    if char_name.lower() in response.lower():
                        selected_actor = char_name
                        break
                        
            # If still no match, fallback to weighted random selection
            if not selected_actor:
                # Extract activity coefficients for active characters
                activity_weights = {}
                for char_name in active_chars:
                    # Default to 1.0 if not specified
                    char_data_template = self.character_states_initial_template.get(char_name)
                    activity_weights[char_name] = char_data_template.activity_coefficient if char_data_template else 1.0
                    
                # Normalize weights
                total_weight = sum(activity_weights.values())
                normalized_weights = {k: v/total_weight for k, v in activity_weights.items()}
                
                # Roulette wheel selection
                r = random.random()
                cumulative = 0.0
                selected_actor = active_chars[0]  # Default
                
                for char_name, weight in normalized_weights.items():
                    cumulative += weight
                    if r <= cumulative:
                        selected_actor = char_name
                        break
            
            # Get character's current state
            char_state = current_world_state.character_states.get(selected_actor)
            
            return selected_actor, char_state
            
        except Exception as e:
            # Fallback to weighted random selection if LLM fails
            # Extract activity coefficients for active characters
            activity_weights = {}
            for char_name in active_chars:
                # Default to 1.0 if not specified
                char_data_template = self.character_states_initial_template.get(char_name)
                activity_weights[char_name] = char_data_template.activity_coefficient if char_data_template else 1.0
                
            # Normalize weights
            total_weight = sum(activity_weights.values())
            normalized_weights = {k: v/total_weight for k, v in activity_weights.items()}
            
            # Roulette wheel selection
            r = random.random()
            cumulative = 0.0
            selected_actor = active_chars[0]  # Default
            
            for char_name, weight in normalized_weights.items():
                cumulative += weight
                if r <= cumulative:
                    selected_actor = char_name
                    break
            
            # Get character's current state
            char_state = current_world_state.character_states.get(selected_actor)
            
            return selected_actor, char_state
    
    def _interpret_outcome_for_relationship_update(
        self, 
        actor_name: str, 
        factual_outcome: str, 
        involved_characters: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Placeholder V1: Interprets factual_outcome to determine relationship changes based on simple keywords.
        A more advanced version would use LLM (RELATIONSHIP_UPDATE_INTERPRETATION prompt).
        
        Args:
            actor_name: The character who performed the action.
            factual_outcome: The resulting description of what happened.
            involved_characters: List of character names involved (actor + potentially target/others).
            
        Returns:
            List of relationship adjustments, e.g.:
            [{"char_a": "Alice", "char_b": "Bob", "trust_delta": 0.1, "affinity_delta": 0.05, "new_status": "allies"}, ...]
        """
        # logging.info(f"WORLD_AGENT_DEBUG: Interpreting outcome for relationships: '{factual_outcome}' involving {involved_characters}")
        updates = []
        if len(involved_characters) < 2:
            return updates # No relationship change if only one character involved

        # Simple keyword-based analysis
        outcome_lower = factual_outcome.lower()
        trust_delta = 0.0
        affinity_delta = 0.0

        # Positive interactions
        if any(verb in outcome_lower for verb in ["helps", "thanks", "praises", "agrees with", "comforts", "saves"]):
            trust_delta += 0.05
            affinity_delta += 0.02
        # Negative interactions
        elif any(verb in outcome_lower for verb in ["attacks", "insults", "threatens", "accuses", "ignores", "betrays"]):
            trust_delta -= 0.1
            affinity_delta -= 0.05
        elif "disagrees with" in outcome_lower:
            trust_delta -= 0.02
            affinity_delta -= 0.01

        if trust_delta != 0.0 or affinity_delta != 0.0:
            # Apply the delta between the actor and the first *other* involved character
            # This is a simplification. A real system might parse the target explicitly
            # or apply deltas between all pairs present based on the action.
            target_char = None
            for char in involved_characters:
                if char != actor_name:
                    target_char = char
                    break
            
            if target_char:
                 # Update Actor's view of Target
                updates.append({
                    "char_a": actor_name,
                    "char_b": target_char,
                    "trust_delta": trust_delta,
                    "affinity_delta": affinity_delta
                })
                 # Update Target's view of Actor (can be slightly different, e.g., less trust change if attacked)
                 # For simplicity, using the same delta for now. Could refine this.
                updates.append({
                    "char_a": target_char,
                    "char_b": actor_name,
                    "trust_delta": trust_delta * 0.8, # Example: target might react slightly differently
                    "affinity_delta": affinity_delta * 0.8
                })

        logging.info(f"DEBUG_WORLD_AGENT (_interpret_outcome_for_relationship_update): Returning updates: {updates}")
        return updates

    def apply_plan(self, actor_name: str, plan_json: Any, current_world_state=None) -> str:
        """
        Apply a character's plan to the world state and generate a factual outcome.
        Uses the LLM to interpret the plan in context and generate appropriate outcomes.
        Also updates relationships based on the outcome.
        
        Args:
            actor_name: Name of the character performing the action
            plan_json: The plan JSON object (or CharacterPlanOutput) from CharacterAgent.plan()
            current_world_state: Optional current world state, uses self.world_state if None
            
        Returns:
            A factual string describing the outcome of the action
        """
        if current_world_state is None:
            current_world_state = self.world_state
            
        # Increment turn counter
        current_world_state.turn_number += 1
        
        # Extract plan details (Handle if plan_json is CharacterPlanOutput dataclass)
        if hasattr(plan_json, 'action'): # Check if it looks like CharacterPlanOutput
            action_type = plan_json.action
            details = plan_json.details
            tone = plan_json.tone_of_action
        elif isinstance(plan_json, dict): # Fallback if it's still a dict
            action_type = plan_json.get("action", "unknown")
            details = plan_json.get("details", {})
            tone = plan_json.get("tone_of_action", "neutral")
        else:
            action_type = "unknown"
            details = {}
            tone = "neutral"
            logging.warning(f"apply_plan received unexpected plan_json type: {type(plan_json)}")
        
        # Create a textual representation of the plan for LLM processing
        plan_text = f"Action: {action_type}"
        if isinstance(details, dict):
            for key, value in details.items():
                plan_text += f"\n{key}: {value}"
        plan_text += f"\nTone: {tone}"
        
        # Prepare location and character context
        character_location = None
        if actor_name in current_world_state.character_states:
            character_location = current_world_state.character_states[actor_name].location
            
        current_location_obj = next(
            (loc for loc in self.world_definition.locations if loc.id == character_location),
            None
        )
        
        location_desc = current_location_obj.description if current_location_obj else "the current area"
        location_connections = current_location_obj.connections if current_location_obj else []
        
        # Build context for outcome generation
        character_context = f"{actor_name} is currently in {character_location} ({location_desc})."
        if location_connections:
            character_context += f" Connected locations: {', '.join(location_connections)}."
            
        # Characters in the same location
        chars_same_loc = [
            char_name for char_name, char_state in current_world_state.character_states.items()
            if char_state.location == character_location and char_name != actor_name
        ]
        
        if chars_same_loc:
            character_context += f" Other characters present: {', '.join(chars_same_loc)}."
        
        # System prompt for outcome generation
        system_prompt = (
            "You are the World Agent for FicWorld, a story generation system. "
            f"The current story is set in: {self.world_definition.description}\n"
            "Your task is to interpret a character's action plan and generate a realistic outcome "
            "based on the current world state. The outcome should be factual, concise, and "
            "expressed as a simple third-person statement of what happens."
        )
        
        # Recent context from world state
        recent_context = "\n".join(current_world_state.recent_events_summary[-3:]) if current_world_state.recent_events_summary else "This is the beginning of the scene."
        
        # User prompt
        parts = [
            f"Character: {actor_name}",
            f"Character Context: {character_context}",
            "\nRecent Events:",
            recent_context,
            "\nCharacter's Plan:",
            plan_text,
            "\nGenerate a single, concise, and factual description of the outcome of this action. "
            "The outcome should reflect what actually happens when the character attempts their planned action. "
            "If the action involves movement, update the character's location accordingly. "
            "If the action is impossible or implausible given the current context, describe a reasonable failure.",
            "\nOutput ONLY the outcome as a simple third-person statement, without any explanations or meta-commentary. "
            "Example: \"Sir Rowan moves to the old ruins.\" or \"Alice examines the strange book, finding cryptic symbols inside.\""
        ]
        user_prompt = "\n".join(parts)
        
        try:
            # Generate outcome using LLM
            outcome_response = self.llm_interface.generate_response_sync(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.4  # Lower temperature for more predictable, factual outcomes
            )
            
            # Clean up response if needed (remove quotes, extra spaces, etc.)
            factual_outcome = outcome_response.strip().strip('"\\\'')
            
            # V1: After factual_outcome, interpret for relationship updates
            # Identify involved characters: actor_name and any mentioned in plan details
            involved_for_relations = {actor_name} 
            if isinstance(details, dict):
                # Look for common keys indicating a target character
                target_char_keys = ["target_char_id", "target_character", "recipient", "target"]
                for key in target_char_keys:
                    target_char = details.get(key)
                    if target_char and isinstance(target_char, str):
                        if target_char in self.world_state.character_states: # Ensure target exists
                            involved_for_relations.add(target_char)
                        break # Found a target
            
            # Potentially parse factual_outcome for other mentioned characters (more complex)
            # For now, relies on actor + explicitly targeted character from plan
            
            if len(involved_for_relations) >= 2: # Only update if at least two distinct characters are involved
                relationship_adjustments = self._interpret_outcome_for_relationship_update(
                    actor_name,
                    factual_outcome,
                    list(involved_for_relations)
                )
                for adj in relationship_adjustments:
                    char_a = adj.get("char_a")
                    char_b = adj.get("char_b")
                    if char_a and char_b:
                        self.relationship_manager.adjust_state(
                            char_a_id=char_a,
                            char_b_id=char_b,
                            trust_delta=adj.get("trust_delta", 0.0),
                            affinity_delta=adj.get("affinity_delta", 0.0),
                            new_status=adj.get("new_status") # Pass status if provided
                        )
                        logging.info(f"Relationship adjusted: {char_a} -> {char_b}, TrustDelta: {adj.get('trust_delta', 0.0):.2f}, AffDelta: {adj.get('affinity_delta', 0.0):.2f}")
                    else:
                        logging.warning(f"Skipping relationship adjustment due to missing char_a/char_b: {adj}")

            return factual_outcome
            
        except Exception as e:
            # Fallback if LLM call fails
            fallback_outcome = f"{actor_name} attempts to {action_type}."
            return fallback_outcome
    
    def should_inject_event(self, current_world_state=None) -> bool:
        """
        Determine if a world event should be injected at this point for narrative impact.
        Uses LLM to evaluate if the scene needs additional environmental elements or events.
        
        Args:
            current_world_state: Optional current world state, uses self.world_state if None
            
        Returns:
            True if an event should be injected, False otherwise
        """
        if current_world_state is None:
            current_world_state = self.world_state
            
        # If in script mode and a beat has a triggered event, always inject
        if self.script_mode and self.current_beat and self.current_beat.get("triggers_event"):
            return True
            
        # Use LLM to decide if an event would enhance the narrative
        
        # Get recent events for context
        recent_events = current_world_state.recent_events_summary[-5:] if current_world_state.recent_events_summary else []
        recent_events_text = "\n".join(recent_events)
        
        # System prompt for event injection decision
        system_prompt = (
            "You are the World Agent for FicWorld, a story generation system. "
            "Your task is to evaluate if injecting an environmental event or detail would enhance "
            "the current narrative flow. Consider the pacing, tension, and engagement of the scene."
        )
        
        # User prompt
        user_prompt_parts = [
            f"Current scene: {current_world_state.current_scene_id}",
            f"Turn number: {current_world_state.turn_number}",
            "\nRecent events in the scene:",
            recent_events_text,
            "\nBased on these recent events, evaluate if injecting a world event or environmental detail would "
            "enhance the narrative at this moment. Consider these questions:",
            "1. Is the pacing becoming too slow or conversation stagnating?",
            "2. Could an environmental event create interesting new tensions or possibilities?",
            "3. Would an external event help reveal character traits or emotions?",
            "4. Has it been several turns since anything notable happened in the environment?",
            "5. Would a background detail add atmosphere or context to the scene?",
            "\nRespond with ONLY 'yes' if an event should be injected, or 'no' if it should not."
        ]
        user_prompt = "\n".join(user_prompt_parts)
        
        try:
            # Get LLM decision
            response = self.llm_interface.generate_response_sync(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2  # Low temperature for more consistent decisions
            ).strip().lower()
            
            # Parse response
            should_inject = response.startswith('yes') or 'yes' in response[:10]
            
            # Have a small chance of injection regardless of LLM response
            # This ensures some unpredictability and prevents stagnation
            if not should_inject and random.random() < self.llm_event_injection_override_chance:
                should_inject = True
                
            return should_inject
            
        except Exception as e:
            # Fallback to simpler heuristics if LLM fails
            
            # 1. Random chance
            if random.random() < self.fallback_event_injection_chance:
                return True
                
            # 2. If the scene is getting stagnant 
            if len(self.previous_token_counts) >= (self.stagnation_threshold - 1): # Uses self.stagnation_threshold
                return True
                
            # Default: don't inject
            return False
    
    def generate_event(self, current_world_state=None) -> str:
        """
        Generate a world event based on the current state.
        
        Args:
            current_world_state: Optional current world state, uses self.world_state if None
            
        Returns:
            A factual string describing the event outcome
        """
        if current_world_state is None:
            current_world_state = self.world_state
            
        # Approach 1: If in script mode and there's a triggered event, use that
        if self.script_mode and self.current_beat and self.current_beat.get("triggers_event"):
            event_id = self.current_beat.get("triggers_event")
            beat_id_to_complete = self.current_beat.get("beat_id") # Capture beat_id first
            
            # Ensure world_events_pool exists and is iterable
            if hasattr(self.world_definition, 'world_events_pool') and self.world_definition.world_events_pool:
                event = next((e for e in self.world_definition.world_events_pool if e.get("event_id") == event_id), None)
                if event:
                    event_desc = event.get("description") if event else "Something happens."
                    if beat_id_to_complete: # Check if we captured a beat_id
                        self.completed_beats.add(beat_id_to_complete)
                    self.current_beat = None 
                    return event_desc if event_desc else "Something happens." # Ensure fallback if desc is None/empty
            # If event not found in pool or no pool, fall through to other methods
                        
        # Approach 2: Pick randomly from event pool
        if hasattr(self.world_definition, 'world_events_pool') and self.world_definition.world_events_pool:
            event = random.choice(self.world_definition.world_events_pool)
            event_desc = event.get("description") if event else "Something unexpected happens."
            return event_desc if event_desc else "Something unexpected happens."
            
        # Approach 3: Use LLM to generate a contextual event
        if self.llm_interface:
            # Prepare world state summary
            current_location_id = None
            if current_world_state.active_characters:
                char_name = current_world_state.active_characters[0]
                char_state = current_world_state.character_states.get(char_name)
                current_location_id = char_state.location if char_state else None
                
            current_location = next(
                (loc for loc in self.world_definition.locations if loc.id == current_location_id), 
                None
            )
            
            location_desc = current_location.description if current_location else "the current area"
            
            # Build context for event generation
            world_state_summary = f"Current scene: {current_world_state.current_scene_id}\n"
            world_state_summary += f"Time of day: {current_world_state.time_of_day}\n"
            world_state_summary += f"Location: {location_desc}\n"
            world_state_summary += f"Characters present: {', '.join(current_world_state.active_characters)}"
            
            recent_events = "\n".join(current_world_state.recent_events_summary[-5:])
            
            # System prompt for event generation, following principles in prompt_design.md
            system_prompt = (
                "You are the World Agent for FicWorld, a story generation system. "
                f"The current story is set in: {self.world_definition.description}\n"
                "Your task is to generate a small, contextual environmental event or detail "
                "that fits the established tone and ongoing narrative. "
                "This event should be factual and brief."
            )
            
            # User prompt
            user_prompt = (
                "Current world state:\n"
                f"{world_state_summary}\n\n"
                "Recent story events:\n"
                f"{recent_events}\n\n"
                "Generate a single, concise, and neutral factual description of a new minor "
                "environmental detail or a small, contextual event that occurs now. "
                "Output as a simple string. Do not add any conversational fluff. "
                "Example: \"A floorboard creaks in the hallway.\" or \"The wind howls a little louder.\""
            )
            
            try:
                # Generate event using LLM
                event_response = self.llm_interface.generate_response_sync(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.7
                )
                
                # Clean up response if needed (remove quotes, extra spaces, etc.)
                event_text = event_response.strip().strip('"\\\'')
                return event_text
                
            except Exception as e:
                # Fallback if LLM call fails
                return "The environment shifts slightly, creating an unusual atmosphere."
                
        # Default fallback - simple random events
        fallback_events = [
            "A cool breeze blows through the area.",
            "Distant sounds can be heard from somewhere nearby.",
            "The lighting changes subtly, casting new shadows.",
            "There's a momentary silence that feels significant.",
            "Something catches the eye at the edge of vision, then vanishes."
        ]
        
        return random.choice(fallback_events)
    
    def update_from_outcome(self, factual_outcome: str) -> None:
        """
        Update the world state based on a factual outcome string.
        Uses LLM to extract structured state changes from the outcome text.
        
        Args:
            factual_outcome: The outcome string to parse
        """
        # Add to recent events
        self.world_state.recent_events_summary.append(factual_outcome)
        
        # Keep recent events list manageable
        if len(self.world_state.recent_events_summary) > self.recent_events_history_limit:
            self.world_state.recent_events_summary = self.world_state.recent_events_summary[-self.recent_events_history_limit:]
            
        # Use LLM to extract structured state changes from the outcome
        
        # System prompt for state update extraction
        system_prompt = (
            "You are the World Agent for FicWorld, a story generation system. "
            "Your task is to extract structured state changes from a factual outcome description. "
            "Focus on identifying changes to character locations, new conditions/states, and "
            "any other elements that should be reflected in the world state."
        )
        
        # User prompt
        user_prompt_parts = [
            "Current world state summary:",
            f"Scene: {self.world_state.current_scene_id}",
            f"Time: {self.world_state.time_of_day}",
            f"Active characters: {', '.join(self.world_state.active_characters)}",
            "\nCharacter locations:",
            "\n".join([f"{name}: {state.location if state else 'unknown'}"  # Use .location
                      for name, state in self.world_state.character_states.items()]),
            "\nNew event/outcome to process:",
            factual_outcome,
            "\nExtract structured state changes from this outcome. Respond with ONLY a JSON object containing "
            "the changes that should be applied to the world state. Include:",
            "- Any character location changes (format: {\"character_name\": \"new_location\"})",
            "- Any new character conditions (format: {\"character_name\": [\"condition1\", \"condition2\"]})",
            "- Any time changes (format: {\"time_of_day\": \"new_time\"})",
            "If no changes should be made, respond with empty objects {}.",
            "Example response format:",
            "{",
            "  \"location_changes\": {\"Knight\": \"forest_clearing\"},",
            "  \"condition_changes\": {\"Scholar\": [\"wounded\", \"tired\"]},",
            "  \"time_changes\": {\"time_of_day\": \"evening\"}",
            "}"
        ]
        user_prompt = "\n".join(user_prompt_parts)
        
        try:
            # Get LLM extraction
            response = self.llm_interface.generate_response_sync(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1  # Very low temperature for consistent, factual extraction
            )
            
            # Parse the JSON response
            try:
                changes = json.loads(response.strip())
                
                # Apply location changes
                if "location_changes" in changes and isinstance(changes["location_changes"], dict):
                    for char_name, new_location in changes["location_changes"].items():
                        if char_name in self.world_state.character_states:
                            logging.info(f"DEBUG: Updating location for {char_name} to {new_location}. Old loc: {self.world_state.character_states[char_name].location}") # DEBUG
                            self.world_state.character_states[char_name].location = new_location
                
                # Apply condition changes
                if "condition_changes" in changes and isinstance(changes["condition_changes"], dict):
                    for char_name, conditions in changes["condition_changes"].items():
                        if char_name in self.world_state.character_states:
                            # Add to existing conditions without duplicates
                            existing_conditions = self.world_state.character_states[char_name].conditions
                            for condition in conditions:
                                if condition not in existing_conditions:
                                    existing_conditions.append(condition)
                            self.world_state.character_states[char_name].conditions = existing_conditions
                
                # Apply time changes
                if "time_changes" in changes and isinstance(changes["time_changes"], dict):
                    if "time_of_day" in changes["time_changes"]:
                        self.world_state.time_of_day = changes["time_changes"]["time_of_day"]
            
            except (json.JSONDecodeError, AttributeError, TypeError) as json_err:
                # Failed to parse JSON or apply changes, but we've already added the event to history
                pass
                
        except Exception as e:
            # If LLM fails, just keep the event in history without structured updates
            # We already added the event to recent_events_summary above
            pass 

    # --- New methods required by main.py ---
    def get_world_state_view_for_actor(self, actor_name: str) -> WorldState:
        """
        Returns the current world state. 
        For now, it returns the full world state. This could be tailored later if needed.
        """
        # In a more complex scenario, this might filter or summarize the world state
        # based on the actor's perception or location.
        return self.world_state

    def get_character_mood(self, actor_name: str) -> Optional[MoodVector]:
        """
        Retrieves the current mood of a specified character.
        
        Args:
            actor_name: The name of the character.
            
        Returns:
            The MoodVector of the character, or None if character not found.
        """
        if actor_name in self.world_state.character_states:
            return self.world_state.character_states[actor_name].current_mood
        return None

    def update_character_mood(self, actor_name: str, updated_mood: MoodVector) -> None:
        """
        Updates the mood of a specified character in the world state.
        
        Args:
            actor_name: The name of the character.
            updated_mood: The new MoodVector for the character.
        """
        if actor_name in self.world_state.character_states:
            self.world_state.character_states[actor_name].current_mood = updated_mood
        else:
            # This case should ideally not happen if actor_name comes from decide_next_actor
            # which should only pick from active_characters present in character_states.
            # logging.warning(f"Attempted to update mood for non-existent character: {actor_name}")
            pass 