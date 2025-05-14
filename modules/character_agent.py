"""
CharacterAgent for FicWorld.

This module defines the character agent class, with its reflect() and plan() methods
following the two-step thinking process outlined in systemPatterns.md.
"""
from typing import Dict, List, Any, Optional, Tuple
import json
import logging

from .models import MoodVector, WorldState, ReflectionOutput, CharacterPlanOutput
from .data_models import CharacterConfig, InitialGoals
from .llm_interface import LLMInterface
from .memory_manager import MemoryManager


class CharacterAgent:
    """
    Represents a character agent in the story simulation.
    
    Each character has a persona, goals, emotional state (mood), and 
    uses a two-step thinking process:
    1. Private reflection (reflect): Updates internal mood and generates private thoughts
    2. Public planning (plan): Generates structured action plans influenced by mood and reflection
    """
    
    def __init__(
        self,
        character_config: CharacterConfig,
        llm_interface: LLMInterface,
        memory_manager: MemoryManager,
        initial_world_state: Optional[WorldState] = None
    ):
        """
        Initialize a character agent with its defining characteristics.
        
        Args:
            character_config: The V1 configuration defining this character's identity.
            llm_interface: Interface for making LLM calls.
            memory_manager: Manager for accessing and storing memories.
            initial_world_state: Initial world state (optional).
        """
        # Core identity from V1 CharacterConfig
        self.full_name = character_config.full_name
        self.persona = character_config.persona
        self.backstory = character_config.backstory
        self.initial_goals: InitialGoals = character_config.initial_goals
        self.activity_coefficient = character_config.activity_coefficient
        
        # Initial emotional state from V1 starting_mood (Dict[str, float])
        # Convert dict to MoodVector, similar to what role_archetype.to_mood_vector() would have done
        sm = character_config.starting_mood
        self.current_mood = MoodVector(
            joy=sm.get("joy", 0.0),
            fear=sm.get("fear", 0.0),
            anger=sm.get("anger", 0.0),
            sadness=sm.get("sadness", 0.0),
            surprise=sm.get("surprise", 0.0),
            trust=sm.get("trust", 0.0)
        )
        
        # Dependencies
        self.llm_interface = llm_interface
        self.memory_manager = memory_manager
        
        # Internal state
        self.latest_reflection = ""  # Most recent private thought
        
        logging.info(f"Character Agent '{self.full_name}' initialized with mood: {self.current_mood}")
        
    async def reflect(
        self, 
        world_state: WorldState, 
        relevant_memories: List[Any],
        relationship_context: Optional[str] = None, # V1 ADDED
        scene_summary_context: Optional[str] = None # V1 ADDED (placeholder for now)
    ) -> ReflectionOutput:
        """
        First step of the two-step thinking process: private reflection and mood update.
        
        The character processes the current world state and memories to form internal
        thoughts and update their emotional state (mood vector). This private reflection
        influences the subsequent public planning but is not directly revealed.
        
        Args:
            world_state: The current state of the simulation world.
            relevant_memories: List of relevant MemoryEntry objects for this character.
            relationship_context: Optional string summary of character's relationships.
            scene_summary_context: Optional string summary of recent scenes.
            
        Returns:
            A ReflectionOutput object containing the updated mood and internal thought.
        """
        # Prepare the system prompt for reflection
        # V1 Note: relationship_context is passed to system prompt for overall character definition
        system_prompt = self._prepare_character_system_prompt(
            relevant_memories=relevant_memories,
            world_state=world_state, # world_state provides general context for system prompt
            relationship_summary_context=relationship_context,
            scene_summary_context=scene_summary_context
        )
        
        # Prepare the user prompt with world state and memories context
        # V1 Note: specific V1 contexts (subjective view, plot, relationships) are passed here.
        # For now, passing relationship_context. Subjective view & plot context would come from WorldAgent/SimulationManager later.
        user_prompt = self._prepare_reflection_prompt(
            world_state, 
            relevant_memories, 
            relationship_context_str=relationship_context,
            # scene_summary_context could be part of subjective_world_view or a separate context here
            # plot_context_str=plot_context # This would be passed in from a higher orchestrator
        )
        
        try:
            # Call the LLM with json_mode=True to get structured output
            reflection_json = await self.llm_interface.generate_json_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7  # Allow for some creativity in reflection
            )
            
            # Extract the updated mood and internal thought from the response
            updated_mood_dict = reflection_json.get("updated_mood", {})
            internal_thought = reflection_json.get("internal_thought", "")
            
            # Convert the mood dictionary to a MoodVector
            updated_mood = MoodVector(
                joy=updated_mood_dict.get("joy", self.current_mood.joy),
                fear=updated_mood_dict.get("fear", self.current_mood.fear),
                anger=updated_mood_dict.get("anger", self.current_mood.anger),
                sadness=updated_mood_dict.get("sadness", self.current_mood.sadness),
                surprise=updated_mood_dict.get("surprise", self.current_mood.surprise),
                trust=updated_mood_dict.get("trust", self.current_mood.trust)
            )
            
            # Update the character's current mood
            self.current_mood = updated_mood
            
            # Store the internal thought for potential reference
            self.latest_reflection = internal_thought
            
            logging.info(f"{self.full_name} reflected on the situation. Mood updated to: {updated_mood}")
            
            return ReflectionOutput(
                updated_mood=updated_mood,
                internal_thought=internal_thought
            )
            
        except Exception as e:
            logging.error(f"Error during {self.full_name}'s reflection: {str(e)}")
            # In case of error, return the current mood and a generic thought
            return ReflectionOutput(
                updated_mood=self.current_mood,
                internal_thought=f"[Error processing reflection: {str(e)}]"
            )
    
    def _prepare_character_system_prompt(
        self, 
        relevant_memories=None, 
        world_state=None, 
        relationship_summary_context: Optional[str] = None,
        scene_summary_context: Optional[str] = None # V1 ADDED
    ) -> str:
        """
        Prepare the CHARACTER_SYSTEM prompt for this character, V1 focused.
        
        Args:
            relevant_memories: A list of relevant memory entries (optional).
            world_state: The current world state (optional, for context like location).
            relationship_summary_context: A string summarizing key relationships (optional, V1 feature).
            scene_summary_context: Optional string summary of recent scenes (V1 feature).
            
        Returns:
            The system prompt string.
        """
        
        memory_summary_str = "No significant personal memories to recall at this moment." 
        if relevant_memories:
            memory_summary_str = self._format_memories_for_prompt(relevant_memories)
           
        # For V1, world_state context in system prompt might be less critical if subjective view is passed to reflect/plan,
        # but can provide general environmental context if needed.
        # current_location_str = world_state.environment_description if world_state else "an unknown location"

        # Structured goals representation
        goals_dict = {
            "long_term": self.initial_goals.long_term,
            "short_term": self.initial_goals.short_term
        }
        goals_json_str = json.dumps(goals_dict, indent=2)

        # Persona and Backstory combined or distinct
        # prompt_design.md suggests combining. self.persona might already include some backstory elements.
        # For clarity, explicitly include self.backstory.
        persona_and_backstory_str = f"{self.persona}\n\n**Full Backstory Context:**\n{self.backstory}"

        mood_json_str = json.dumps(self.current_mood.__dict__) # Assuming MoodVector has __dict__ or similar

        relationship_str = relationship_summary_context if relationship_summary_context else "No specific relationship context available."
        scenes_summary_str = scene_summary_context if scene_summary_context else "No summaries of recent major events available."

        # Aligning with memory-bank/v1/prompt_design.md for CHARACTER_SYSTEM
        prompt = f"""You are {self.full_name}.

**Persona & Backstory:**
{persona_and_backstory_str}

**Your Goals:**
{goals_json_str}

**Current Emotional State (Mood Vector):**
{mood_json_str}

**Your Relationships (Overview):**
{relationship_str}

**Key Personal Memories (Recollections):**
{memory_summary_str}

**Summaries of Recent Major Events (Plot Context):**
{scenes_summary_str}

You must always act, speak, and think internally in accordance with this identity (your persona, backstory), your specific goals, your current emotions, your relationships, and your understanding of recent events.
"""
        return prompt
    
    def _prepare_reflection_prompt(
        self, 
        world_state: WorldState, # Kept for fallback if subjective view not yet piped through
        relevant_memories: List[Any], # Kept for fallback
        subjective_world_view_json: Optional[str] = None, # V1 input
        recent_subjective_events_str: Optional[str] = None, # V1 input
        plot_context_str: Optional[str] = None, # V1 input
        relationship_context_str: Optional[str] = None # V1 input
    ) -> str:
        """
        Prepare the CHARACTER_REFLECT user prompt, V1 focused.
        
        Args:
            world_state: The current world state (used for fallback).
            relevant_memories: List of relevant memories (used for fallback).
            subjective_world_view_json: JSON string of the character's subjective world view.
            recent_subjective_events_str: String listing recent events as perceived by the character.
            plot_context_str: String describing the current plot situation.
            relationship_context_str: String describing character's relationships.
            
        Returns:
            The user prompt string.
        """
        # V1 Contexts - use if provided, otherwise prepare fallbacks
        view_context = subjective_world_view_json if subjective_world_view_json else f"Current situation (general):\n{world_state.environment_description}"
        events_context = recent_subjective_events_str if recent_subjective_events_str else "Recent events (general):\n" + "\n".join(world_state.recent_events_summary)
        
        # Fallback for memories if specific subjective events aren't fully detailed yet
        memory_summary_str = self._format_memories_for_prompt(relevant_memories)
        
        # V1 Plot and Relationship context (optional for now)
        plot_str = plot_context_str if plot_context_str else "No specific plot context provided."
        relationships_str = relationship_context_str if relationship_context_str else "No specific relationship context provided."
        
        mood_json_str = json.dumps(self.current_mood.__dict__)

        # Aligning with memory-bank/v1/prompt_design.md for CHARACTER_REFLECT
        return f"""Based ONLY on what you currently perceive and know:

**Your Subjective View of the World:**
{view_context}

**Recent Events (As You Perceived Them):**
{events_context}

**Your Relationships:**
{relationships_str}

**Current Plot Situation:**
{plot_str}

**Relevant Personal Memories (Recollections):**
{memory_summary_str}

**Your Current Mood is:** {mood_json_str}

Reflect silently. Given your persona (`{self.persona}`), your backstory, your goals ({self.initial_goals.short_term}, {self.initial_goals.long_term}), your relationships, and the current plot situation, how does this make you, {self.full_name}, feel? What are your secret thoughts, plans, or fears based *only* on your perspective and what you currently know?

Based on this reflection, provide your updated mood vector and a brief summary of your internal thought.
Respond ONLY with a JSON object adhering to the following schema:
{{
  "updated_mood": {{"joy": float, "fear": float, "anger": float, "sadness": float, "surprise": float, "trust": float}},
  "internal_thought": "string"
}}

This reflection is for your internal state ONLY. Do NOT reveal the specifics of this internal thought or your mood reasoning in any subsequent public actions or dialogue.
"""
    
    def _format_memories_for_prompt(self, memories: List[Any]) -> str:
        """
        Format a list of memories into a string for inclusion in prompts.
        
        Args:
            memories: List of MemoryEntry objects.
            
        Returns:
            A formatted string summarizing the memories.
        """
        if not memories:
            return "You have no specific memories relevant to the current situation."
        
        memory_lines = []
        for memory in memories:
            memory_lines.append(f"- {memory.event_description}")
        
        return "\n".join(memory_lines)
        
    async def plan(
        self, 
        world_state: WorldState, 
        relevant_memories: List[Any], 
        internal_thought_summary: str,
        relationship_context: Optional[str] = None, # V1 ADDED
        scene_summary_context: Optional[str] = None # V1 ADDED (placeholder for now)
    ) -> CharacterPlanOutput:
        """
        Second step of the two-step thinking process: public action planning.
        
        Based on the character's persona, goals, current mood (as updated by reflect()),
        and the internal thoughts from reflect(), this method generates a structured 
        JSON plan for a public action (e.g., speaking, moving, interacting).
        
        Args:
            world_state: The current state of the simulation world.
            relevant_memories: List of relevant MemoryEntry objects for this character.
            internal_thought_summary: Summary of the character's private reflection.
            relationship_context: Optional string summary of character's relationships.
            scene_summary_context: Optional string summary of recent scenes.
            
        Returns:
            A CharacterPlanOutput object.
        """
        # Prepare the system prompt for planning
        # V1 Note: relationship_context is passed to system prompt for overall character definition
        system_prompt = self._prepare_character_system_prompt(
            relevant_memories=relevant_memories,
            world_state=world_state,
            relationship_summary_context=relationship_context,
            scene_summary_context=scene_summary_context
        )
        
        # Prepare the user prompt for planning
        # V1 Note: specific V1 contexts (subjective view, plot, relationships) are passed here.
        user_prompt = self._prepare_plan_prompt(
            world_state, 
            relevant_memories, 
            internal_thought_summary,
            relationship_context_str=relationship_context,
            # scene_summary_context could be part of subjective_world_view or a separate context here
            # plot_context_str=plot_context # This would be passed in from a higher orchestrator
        )
        
        try:
            # Call the LLM with json_mode=True to get structured output
            plan_json = await self.llm_interface.generate_json_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.6  # Slightly lower temperature for more focused action planning
            )
            
            # Validate the minimal required fields
            if "action" not in plan_json:
                raise ValueError("LLM response missing required 'action' field")
            if "details" not in plan_json:
                plan_json["details"] = {}
            if "tone_of_action" not in plan_json:
                plan_json["tone_of_action"] = "neutral"
                
            # Log the plan (without sensitive internal thought info)
            logging.info(f"{self.full_name} planned action: {plan_json['action']} with tone: {plan_json['tone_of_action']}")
            
            return CharacterPlanOutput(
                action=plan_json["action"],
                details=plan_json["details"],
                tone_of_action=plan_json["tone_of_action"]
            )
            
        except Exception as e:
            logging.error(f"Error during {self.full_name}'s planning: {str(e)}")
            # In case of error, return a default "speak" action explaining confusion
            return CharacterPlanOutput(
                action="speak",
                details={
                    "text": f"I... hmm, let me gather my thoughts."
                },
                tone_of_action="confused"
            )
    
    def _prepare_plan_prompt(
        self, 
        world_state: WorldState, # Kept for fallback
        relevant_memories: List[Any], # Kept for fallback
        internal_thought_summary: str,
        subjective_world_view_json: Optional[str] = None, # V1 input
        recent_public_exchanges_subjective_str: Optional[str] = None, # V1 input
        plot_context_str: Optional[str] = None, # V1 input
        relationship_context_str: Optional[str] = None # V1 input
    ) -> str:
        """
        Prepare the CHARACTER_PLAN user prompt, V1 focused.
        
        Args:
            world_state: The current world state (used for fallback).
            relevant_memories: List of relevant memories (used for fallback).
            internal_thought_summary: The character's private reflection summary.
            subjective_world_view_json: JSON string of the character's subjective world view.
            recent_public_exchanges_subjective_str: String of recent public events as perceived by the character.
            plot_context_str: String describing the current plot situation.
            relationship_context_str: String describing character's relationships.
            
        Returns:
            The user prompt string.
        """
        # V1 Contexts - use if provided, otherwise prepare fallbacks
        view_context = subjective_world_view_json
        if not view_context:
            # Fallback: Reconstruct parts of subjective view from world_state for the prompt
            current_location_fallback = "unknown"
            characters_present_fallback_list = []
            if self.full_name in world_state.character_states:
                char_state_obj = world_state.character_states[self.full_name]
                current_location_fallback = char_state_obj.location if char_state_obj else "unknown"
                characters_present_fallback_list = [
                    name for name, other_char_state_obj in world_state.character_states.items()
                    if (other_char_state_obj.location == current_location_fallback if other_char_state_obj else False) and name != self.full_name
                ]
            characters_present_fallback_str = ", ".join(characters_present_fallback_list) if characters_present_fallback_list else "no one else you recognize"
            view_context = f"""{{ \"perceived_location\": \"{world_state.environment_description} (You are at: {current_location_fallback})\", \"visible_characters\": {{ \"others_present\": \"{characters_present_fallback_str}\" }} }}"""

        events_context = recent_public_exchanges_subjective_str if recent_public_exchanges_subjective_str else "Recent public events (general):\n" + "\n".join(world_state.recent_events_summary)
        memory_summary_str = self._format_memories_for_prompt(relevant_memories)

        plot_str = plot_context_str if plot_context_str else "No specific plot context provided."
        relationships_str = relationship_context_str if relationship_context_str else "No specific relationship context provided."
        mood_json_str = json.dumps(self.current_mood.__dict__)
        
        # Structured goals for prompt
        goals_long_term_str = ", ".join(self.initial_goals.long_term) if self.initial_goals.long_term else "none defined"
        goals_short_term_str = ", ".join(self.initial_goals.short_term) if self.initial_goals.short_term else "none defined"

        # Aligning with memory-bank/v1/prompt_design.md for CHARACTER_PLAN
        return f"""Based ONLY on your current perspective and internal state:

**Your Subjective View of the World:**
{view_context}

**Recent Public Events (As You Perceived Them):**
{events_context}

**Your Relationships:**
{relationships_str}

**Current Plot Situation:**
{plot_str}

**Relevant Personal Memories (Recollections):**
{memory_summary_str}

**Your Current Mood is:** {mood_json_str}
**Your Private Reflection Was:** "{internal_thought_summary}"

Considering all this, your persona (`{self.persona}`), your backstory, your goals (Long-term: {goals_long_term_str}; Short-term: {goals_short_term_str}), the current plot beat objectives (if known from plot context), and staying in character as {self.full_name}, what is your next public action or dialogue?

Think about how your action might:
- Advance your short-term or long-term goals.
- Be influenced by or affect your relationships.
- Contribute to the current plot situation or beat objectives.
- Involve interacting with visible characters, objects, or your environment as per your subjective view.

Choose a specific and concrete action. This could be to:
- **Speak:** to a character or generally.
- **Move:** to a new location or position.
- **Interact with an object/environment:** examine, use, manipulate something.
- **Interact with a character:** a non-dialogue action towards them.
- **Use a skill/ability:** if applicable to your character.
- **Observe:** focus attention on a detail or character.
- **Wait/Do Nothing:** if strategically sound.

Return your response ONLY as a JSON object following this schema:
{{
  "action": string,  // e.g., "speak", "move", "interact_object", "interact_character", "use_skill", "observe_detail", "wait"
  "details": {{      // Provide specifics. E.g., for "speak": {{"text": "dialogue"}}. For "move": {{"target_location": "destination"}}. For "interact_object": {{"object_name": "item", "interaction_type": "examine"}}.
  }},
  "target_char_id": string, // Optional: ID of character targeted by action (if applicable)
  "tone_of_action": string  // e.g., "cautious", "elated", "suspicious" - reflecting your mood and action
}}

Be creative yet grounded in your character and subjective understanding.
"""
    
    # Synchronous versions for simpler usage scenarios
    
    def reflect_sync(
        self, 
        world_state: WorldState, 
        relevant_memories: List[Any],
        relationship_context: Optional[str] = None, # V1 ADDED
        scene_summary_context: Optional[str] = None # V1 ADDED
    ) -> ReflectionOutput:
        """Synchronous wrapper for reflect()."""
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.reflect(world_state, relevant_memories, relationship_context, scene_summary_context))
        finally:
            loop.close()
    
    def plan_sync(
        self, 
        world_state: WorldState, 
        relevant_memories: List[Any], 
        internal_thought_summary: str,
        relationship_context: Optional[str] = None, # V1 ADDED
        scene_summary_context: Optional[str] = None # V1 ADDED
    ) -> CharacterPlanOutput:
        """Synchronous wrapper for plan()."""
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.plan(world_state, relevant_memories, internal_thought_summary, relationship_context, scene_summary_context)
            )
        finally:
            loop.close() 