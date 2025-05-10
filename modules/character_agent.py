"""
CharacterAgent for FicWorld.

This module defines the character agent class, with its reflect() and plan() methods
following the two-step thinking process outlined in systemPatterns.md.
"""
from typing import Dict, List, Any, Optional, Tuple
import json
import logging

from .models import MoodVector, RoleArchetype, WorldState


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
        role_archetype: RoleArchetype,
        llm_interface: Any,  # LLMInterface
        memory_manager: Any,  # MemoryManager
        initial_world_state: Optional[WorldState] = None
    ):
        """
        Initialize a character agent with its defining characteristics.
        
        Args:
            role_archetype: The archetype defining this character's persona and initial state.
            llm_interface: Interface for making LLM calls.
            memory_manager: Manager for accessing and storing memories.
            initial_world_state: Initial world state (optional).
        """
        # Core identity
        self.name = role_archetype.archetype_name
        self.persona = role_archetype.persona_template
        self.goals = role_archetype.goal_templates
        self.activity_coefficient = role_archetype.activity_coefficient
        
        # Initial emotional state
        self.current_mood = role_archetype.to_mood_vector()
        
        # Dependencies
        self.llm_interface = llm_interface
        self.memory_manager = memory_manager
        
        # Internal state
        self.latest_reflection = ""  # Most recent private thought
        
        logging.info(f"Character Agent '{self.name}' initialized with mood: {self.current_mood}")
        
    async def reflect(self, world_state: WorldState, relevant_memories: List[Any]) -> Dict[str, Any]:
        """
        First step of the two-step thinking process: private reflection and mood update.
        
        The character processes the current world state and memories to form internal
        thoughts and update their emotional state (mood vector). This private reflection
        influences the subsequent public planning but is not directly revealed.
        
        Args:
            world_state: The current state of the simulation world.
            relevant_memories: List of relevant MemoryEntry objects for this character.
            
        Returns:
            A dictionary with the updated mood vector and internal thought:
            {
                "updated_mood": MoodVector(...),
                "internal_thought": "..."
            }
        """
        # Prepare the system prompt for reflection
        system_prompt = self._prepare_character_system_prompt(
            relevant_memories=relevant_memories,
            world_state=world_state
        )
        
        # Prepare the user prompt with world state and memories context
        user_prompt = self._prepare_reflection_prompt(world_state, relevant_memories)
        
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
            
            logging.info(f"{self.name} reflected on the situation. Mood updated to: {updated_mood}")
            
            return {
                "updated_mood": updated_mood,
                "internal_thought": internal_thought
            }
            
        except Exception as e:
            logging.error(f"Error during {self.name}'s reflection: {str(e)}")
            # In case of error, return the current mood and a generic thought
            return {
                "updated_mood": self.current_mood,
                "internal_thought": f"[Error processing reflection: {str(e)}]"
            }
    
    def _prepare_character_system_prompt(self, relevant_memories=None, world_state=None) -> str:
        """
        Prepare the CHARACTER_SYSTEM prompt for this character.
        
        Args:
            memory_summary: A summary of relevant memories for the character (optional).
            world_state_summary: A summary of relevant world state details (optional).
            
        Returns:
            The system prompt string.
        """
        
        # Format any relevant memories if provided
        memory_summary = "No significant memories to recall." 
        if memory_summary:
            memory_summary = self._format_memories_for_prompt(relevant_memories)
           
        # Format world state summary if provided
        world_state_summary = ""
        if world_state:
           world_state_summary = f"Current location: {world_state.environment_description}"
           
        # In a more robust implementation, this would load from a template file
        return f"""You are {self.name}.

**Persona:**
{self.persona}

**Your Goals:**
{', '.join(self.goals)}

**Current Emotional State (Mood Vector):**
{self.current_mood}

**Key Information & Memories:**
{memory_summary}
{world_state_summary}

You must always act and speak in accordance with this persona, your goals, and your current emotional state.
"""
    
    def _prepare_reflection_prompt(self, world_state: WorldState, relevant_memories: List[Any]) -> str:
        """
        Prepare the CHARACTER_REFLECT user prompt.
        
        Args:
            world_state: The current world state.
            relevant_memories: List of relevant memories.
            
        Returns:
            The user prompt string.
        """
        # Format relevant memories into a concise summary
        memory_summary = self._format_memories_for_prompt(relevant_memories)
        
        # Extract recent events from world state
        recent_events = "\n".join(world_state.recent_events_summary)
        
        return f"""Considering the current situation:
{world_state.environment_description}

And recent events:
{recent_events}

Your relevant memories:
{memory_summary}

Your current mood is: {self.current_mood}

Reflect silently. How do these events make you, {self.name}, feel, given your persona and goals? What are your secret thoughts, desires, or fears right now?

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
        internal_thought_summary: str
    ) -> Dict[str, Any]:
        """
        Second step of the two-step thinking process: public action planning.
        
        Based on the character's persona, goals, current mood (as updated by reflect()),
        and the internal thoughts from reflect(), this method generates a structured 
        JSON plan for a public action (e.g., speaking, moving, interacting).
        
        Args:
            world_state: The current state of the simulation world.
            relevant_memories: List of relevant MemoryEntry objects for this character.
            internal_thought_summary: Summary of the character's private reflection.
            
        Returns:
            A structured plan JSON object following the CharacterPlanOutput schema:
            {
                "action": string (e.g., "speak", "move", "interact_object"),
                "details": { ... },  # Content varies by action type
                "tone_of_action": string (e.g., "cautious", "angry", "determined")
            }
        """
        # Prepare the system prompt for planning
        system_prompt = self._prepare_character_system_prompt(
            relevant_memories=relevant_memories,
            world_state=world_state
        )
        
        # Prepare the user prompt for planning
        user_prompt = self._prepare_plan_prompt(world_state, relevant_memories, internal_thought_summary)
        
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
            logging.info(f"{self.name} planned action: {plan_json['action']} with tone: {plan_json['tone_of_action']}")
            
            return plan_json
            
        except Exception as e:
            logging.error(f"Error during {self.name}'s planning: {str(e)}")
            # In case of error, return a default "speak" action explaining confusion
            return {
                "action": "speak",
                "details": {
                    "text": f"I... hmm, let me gather my thoughts."
                },
                "tone_of_action": "confused"
            }
    
    def _prepare_plan_prompt(
        self, 
        world_state: WorldState, 
        relevant_memories: List[Any], 
        internal_thought_summary: str
    ) -> str:
        """
        Prepare the CHARACTER_PLAN user prompt.
        
        Args:
            world_state: The current world state.
            relevant_memories: List of relevant memories.
            internal_thought_summary: The character's private reflection summary.
            
        Returns:
            The user prompt string.
        """
        # Format relevant memories and recent events
        memory_summary = self._format_memories_for_prompt(relevant_memories)
        recent_events = "\n".join(world_state.recent_events_summary)
        
        # Get current location and characters present
        current_location = "unknown"
        characters_present = []
        if self.name in world_state.character_states:
            current_location = world_state.character_states[self.name].get("location", "unknown")
            characters_present = [
                name for name, state in world_state.character_states.items() 
                if state.get("location") == current_location and name != self.name
            ]
        
        characters_present_str = ", ".join(characters_present) if characters_present else "no one else"
        
        return f"""Current situation:
{world_state.environment_description}

You are at: {current_location}
Others present: {characters_present_str}

Recent public events:
{recent_events}

Your relevant memories:
{memory_summary}

Your current mood is: {self.current_mood}
Your private reflection was: "{internal_thought_summary}"

Based on all this, and staying in character as {self.name}, what is your next public action or dialogue?

Return your response ONLY as a JSON object following this schema:
{{
  "action": string,  // One of: "speak", "move", "interact_object", "use_skill", "observe_detail"
  "details": {{      // Content varies by action type:
    // For "speak": {{"text": "your dialogue here"}}
    // For "move": {{"target_location": "location_name"}}
    // For "interact_object": {{"object_name": "the object", "interaction_type": "pick up/examine/etc"}}
    // For "use_skill": {{"skill_name": "the skill", "target": "target of skill if any"}}
    // For "observe_detail": {{"focus": "what you're observing closely"}}
  }},
  "tone_of_action": string  // e.g., "cautious", "elated", "suspicious" - reflecting your current mood and the nature of the action
}}

Choose an action that naturally follows from the situation, your character, and your current emotional state.
"""
    
    # Synchronous versions for simpler usage scenarios
    
    def reflect_sync(self, world_state: WorldState, relevant_memories: List[Any]) -> Dict[str, Any]:
        """Synchronous wrapper for reflect()."""
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.reflect(world_state, relevant_memories))
        finally:
            loop.close()
    
    def plan_sync(
        self, 
        world_state: WorldState, 
        relevant_memories: List[Any], 
        internal_thought_summary: str
    ) -> Dict[str, Any]:
        """Synchronous wrapper for plan()."""
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.plan(world_state, relevant_memories, internal_thought_summary)
            )
        finally:
            loop.close() 