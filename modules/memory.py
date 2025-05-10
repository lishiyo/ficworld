"""
Memory Manager for FicWorld agents.
Handles short-term and long-term memory, including emotional RAG.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any

from .models import MemoryEntry, MoodVector, LogEntry


class MemoryManager:
    """
    Manages agent memories, both short-term (STM) and long-term (LTM).
    MVP uses in-memory lists. Future versions will integrate vector stores.
    """

    def __init__(self):
        """Initialize the MemoryManager with in-memory stores."""
        self.stm: Dict[str, List[MemoryEntry]] = {}  # Actor name -> List of recent memories
        self.ltm_store: List[MemoryEntry] = []
        self.scene_summaries: Dict[int, str] = {} # Scene number -> Summary string

    def remember(
        self,
        actor_name: str,
        event_description: str,
        mood_at_encoding: MoodVector,
        significance: float = 1.0
    ) -> MemoryEntry:
        """
        Store a new memory entry in LTM and potentially STM.

        Args:
            actor_name: The name of the character agent experiencing the event.
            event_description: A textual description of the event.
            mood_at_encoding: The mood vector of the agent at the time of the event.
            significance: A float indicating the importance of the memory (default 1.0).

        Returns:
            The created MemoryEntry object.
        """
        entry = MemoryEntry(
            timestamp=datetime.now(),
            actor_name=actor_name,
            event_description=event_description,
            mood_at_encoding=mood_at_encoding,
            significance=significance
            # Embedding will be added in a later phase
        )
        self.ltm_store.append(entry)

        # Basic STM: keep last N memories per actor (can be refined)
        if actor_name not in self.stm:
            self.stm[actor_name] = []
        self.stm[actor_name].append(entry)
        # Keep STM to a manageable size, e.g., last 10 events per actor
        if len(self.stm[actor_name]) > 10:
            self.stm[actor_name].pop(0)
            
        return entry

    def retrieve(
        self,
        actor_name: str,
        query_text: Optional[str] = None, # Not used in MVP retrieval
        current_mood: Optional[MoodVector] = None, # Not used in MVP retrieval
        max_results: int = 5
    ) -> List[MemoryEntry]:
        """
        Retrieve relevant memories for an actor.
        MVP: Returns the last N memories for the actor from LTM or all from STM.
        Future: Will use query_text and current_mood for semantic and emotional RAG.

        Args:
            actor_name: The name of the character agent.
            query_text: The query to match against memories (unused in MVP).
            current_mood: The agent's current mood for emotional filtering (unused in MVP).
            max_results: The maximum number of memories to return.

        Returns:
            A list of relevant MemoryEntry objects.
        """
        # For MVP, let's return the most recent memories from LTM for this actor
        actor_memories = [mem for mem in reversed(self.ltm_store) if mem.actor_name == actor_name]
        return actor_memories[:max_results]
    
    def get_stm_for_actor(self, actor_name: str) -> List[MemoryEntry]:
        """
        Get the short-term memories for a specific actor.
        
        Args:
            actor_name: The name of the actor.
            
        Returns:
            A list of MemoryEntry objects from STM.
        """
        return self.stm.get(actor_name, [])

    def summarise_scene(
        self, 
        scene_number: int, 
        scene_log: List[LogEntry], 
        llm_interface: Optional[Any] = None # For future LLM-based summarization
    ) -> Optional[str]:
        """
        Create and store a summary of a completed scene.
        MVP: Concatenates event descriptions. Future: Use LLM for summarization.

        Args:
            scene_number: The number of the scene being summarized.
            scene_log: A list of LogEntry objects from the scene.
            llm_interface: An LLMInterface instance for LLM-based summarization (optional for MVP).

        Returns:
            The generated summary string, or None if no summary was made.
        """
        if not scene_log:
            return None

        # MVP summarization: concatenate all factual outcomes
        summary_parts = [
            f"Event by {log_entry.get('actor', 'Unknown Actor')}: {log_entry.get('outcome', 'Unknown Outcome')}" 
            for log_entry in scene_log
        ]
        summary = "\n".join(summary_parts)
        
        # Store the summary
        self.scene_summaries[scene_number] = summary
        
        # Optional: Create a MemoryEntry for the scene summary itself in LTM
        # This allows agents to recall high-level plot points of past scenes.
        # For MVP, we'll just store it in self.scene_summaries.
        # Example for future:
        # self.remember(
        #     actor_name="Narrator", # Or a special system actor
        #     event_description=f"Summary of Scene {scene_number}: {summary}",
        #     mood_at_encoding=MoodVector() # Neutral mood for summaries, or average mood of scene
        # )
        
        print(f"Scene {scene_number} summarized (MVP: concatenation). Logged {len(scene_log)} events.")
        return summary

    def get_scene_summary(self, scene_number: int) -> Optional[str]:
        """
        Retrieve the summary for a given scene number.

        Args:
            scene_number: The number of the scene.

        Returns:
            The summary string, or None if not found.
        """
        return self.scene_summaries.get(scene_number)

    def clear_stm_for_actor(self, actor_name: str):
        """
        Clear short-term memory for a specific actor.
        
        Args:
            actor_name: The name of the actor whose STM should be cleared.
        """
        if actor_name in self.stm:
            self.stm[actor_name] = []
            print(f"STM cleared for actor: {actor_name}")

    def clear_all_stm(self):
        """
        Clear short-term memory for all actors.
        """
        for actor_name in self.stm.keys():
            self.stm[actor_name] = []
        print("STM cleared for all actors.")

    def reset_memory(self):
        """
        Reset all memories (LTM, STM, scene summaries).
        Useful for starting a new simulation or testing.
        """
        self.ltm_store = []
        self.stm = {}
        self.scene_summaries = {}
        print("All memories (LTM, STM, Scene Summaries) have been reset.") 