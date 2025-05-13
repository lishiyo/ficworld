"""
RelationshipManager for FicWorld V1.

Manages the dynamic relationships between characters, including trust, affinity,
and overall status (e.g., friend, enemy, ally).
"""
from typing import Dict, Tuple, Optional, List, FrozenSet
from pydantic import BaseModel, Field

class RelationshipState(BaseModel):
    """Represents the state of a relationship between two characters."""
    trust: float = Field(default=0.5, ge=0.0, le=1.0)  # Normalized 0.0 (no trust) to 1.0 (full trust)
    affinity: float = Field(default=0.0, ge=-1.0, le=1.0) # Normalized -1.0 (hate) to 1.0 (love/adore)
    status: str = Field(default="neutral") # e.g., neutral, friends, rivals, enemies, allies, lovers
    # Optional: history of significant events affecting this relationship?
    # history: List[str] = Field(default_factory=list)

class RelationshipManager:
    """
    Tracks and updates dynamic relationships between characters.
    Uses a dictionary where keys are frozensets of two character IDs (to ensure order doesn't matter)
    and values are RelationshipState objects.
    """
    def __init__(self):
        self._relationships: Dict[FrozenSet[str], RelationshipState] = {}

    def _get_relationship_key(self, char_a_id: str, char_b_id: str) -> FrozenSet[str]:
        """Helper to create a consistent, order-independent key for two character IDs."""
        if char_a_id == char_b_id:
            raise ValueError("Cannot have a relationship with oneself in this context.")
        return frozenset([char_a_id, char_b_id])

    def get_state(self, char_a_id: str, char_b_id: str) -> RelationshipState:
        """
        Retrieves the current relationship state between two characters.
        If no relationship exists, it returns a default neutral RelationshipState.
        """
        key = self._get_relationship_key(char_a_id, char_b_id)
        return self._relationships.get(key, RelationshipState()) # Return default if not found

    def update_state(self, char_a_id: str, char_b_id: str, new_state: RelationshipState) -> None:
        """
        Sets the relationship state between two characters to a new state.
        """
        key = self._get_relationship_key(char_a_id, char_b_id)
        self._relationships[key] = new_state
        # print(f"DEBUG: Relationship updated between {char_a_id} and {char_b_id}: {new_state}")

    def adjust_state(
        self, 
        char_a_id: str, 
        char_b_id: str, 
        trust_delta: float = 0.0,
        affinity_delta: float = 0.0,
        new_status: Optional[str] = None
    ) -> RelationshipState:
        """
        Adjusts the existing relationship state by deltas and optionally updates the status.
        Clamps trust (0-1) and affinity (-1 to 1).
        Returns the new state.
        """
        key = self._get_relationship_key(char_a_id, char_b_id)
        current_state = self._relationships.get(key, RelationshipState()) # Get current or default
        
        new_trust = min(1.0, max(0.0, current_state.trust + trust_delta))
        new_affinity = min(1.0, max(-1.0, current_state.affinity + affinity_delta))
        final_status = new_status if new_status is not None else current_state.status
        
        updated_rel_state = RelationshipState(
            trust=new_trust,
            affinity=new_affinity,
            status=final_status
            # history = current_state.history # if history is implemented
        )
        self._relationships[key] = updated_rel_state
        # print(f"DEBUG: Relationship adjusted between {char_a_id} and {char_b_id}: {updated_rel_state}")
        return updated_rel_state

    def get_context_for_character(self, character_id: str, num_relations_to_summarize: int = 5) -> str:
        """
        Generates a string summary of a character's most significant relationships for prompt injection.
        """
        relevant_relations: List[Tuple[str, RelationshipState]] = []
        for key, state in self._relationships.items():
            if character_id in key:
                other_char_id = list(key - {character_id})[0]
                relevant_relations.append((other_char_id, state))
        
        if not relevant_relations:
            return "You have no significant established relationships yet."

        # Sort by some measure of significance (e.g., absolute affinity, or extremity of trust)
        # For now, simple sort by affinity descending, then trust descending as a tie-breaker
        relevant_relations.sort(key=lambda x: (abs(x[1].affinity), x[1].trust), reverse=True)
        
        summary_parts = ["Your current relationships of note:"]
        for i, (other_char, state) in enumerate(relevant_relations):
            if i >= num_relations_to_summarize:
                break
            summary_parts.append(
                f"- With {other_char}: Status is '{state.status}'. Trust: {state.trust:.2f}/1.0. Affinity: {state.affinity:.2f}/1.0."
            )
        
        if not summary_parts:
            return "You have no significant established relationships yet."
            
        return "\n".join(summary_parts)

    def get_all_relationships(self) -> Dict[FrozenSet[str], RelationshipState]:
        """Returns all relationships. Useful for saving state or debugging."""
        return self._relationships

# Example Usage (for testing or direct script execution)
if __name__ == '__main__':
    manager = RelationshipManager()

    print("Initial state for Alice-Bob:", manager.get_state("Alice", "Bob"))

    # Adjusting state
    new_state_ab = manager.adjust_state("Alice", "Bob", trust_delta=0.2, affinity_delta=0.5, new_status="friends")
    print("Alice-Bob after adjustment:", new_state_ab)

    manager.adjust_state("Alice", "Carol", trust_delta=-0.3, affinity_delta=-0.7, new_status="rivals")
    manager.adjust_state("Bob", "Carol", trust_delta=0.1, affinity_delta=0.0, new_status=" wary colleagues")
    manager.adjust_state("Alice", "Dave", trust_delta=0.7, affinity_delta=0.9, new_status="lovers")
    manager.adjust_state("Alice", "Eve", trust_delta=-0.9, affinity_delta=-0.9, new_status="arch-enemies")
    manager.adjust_state("Alice", "Frank", trust_delta=0.0, affinity_delta=0.0, new_status="ignored_acquaintance")


    # Getting context for Alice
    alice_context = manager.get_context_for_character("Alice")
    print("\nAlice's relationship context:")
    print(alice_context)

    bob_context = manager.get_context_for_character("Bob")
    print("\nBob's relationship context:")
    print(bob_context)

    # Test setting a full state
    eve_frank_state = RelationshipState(trust=0.1, affinity=-0.5, status="disdainful")
    manager.update_state("Eve", "Frank", eve_frank_state)
    print("\nEve-Frank state (set directly):", manager.get_state("Eve", "Frank"))

    print("\nAll relationships:", manager.get_all_relationships()) 