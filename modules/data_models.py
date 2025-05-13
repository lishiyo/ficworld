from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class InitialGoals(BaseModel):
    long_term: List[str] = Field(default_factory=list)
    short_term: List[str] = Field(default_factory=list)

class CharacterConfig(BaseModel):
    full_name: str
    persona: str
    backstory: str
    initial_goals: InitialGoals = Field(default_factory=InitialGoals)
    activity_coefficient: float = 0.8  # Defaulting as per notes
    starting_mood: Dict[str, float] = Field(default_factory=dict) # Example: {"joy": 0.5, "sadness": 0.1}

# Future models from systemPatterns.md will be added here, e.g.:
# class WorldState(BaseModel): ...
# class SubjectiveWorldView(BaseModel): ...
# class RelationshipState(BaseModel): ...
# class PlotStructure(BaseModel): ...
# class NarrativeThread(BaseModel): ... 

class VisibleCharacterState(BaseModel):
    """Represents the perceived state of a visible character."""
    character_id: str
    estimated_condition: List[str] = Field(default_factory=list) 
    apparent_mood: Optional[str] = None 
    observed_action: Optional[str] = None 

class VisibleObjectState(BaseModel):
    """Represents the perceived state of a visible object."""
    object_id: str 
    observed_state: str 
    perceived_usability: Optional[str] = None

class SubjectiveEvent(BaseModel):
    """Represents a character's filtered perception of an objective FactualOutcome."""
    timestamp: str 
    observer_id: str
    perceived_description: str 
    inferred_actor: Optional[str] = None 
    inferred_target: Optional[str] = None 

class SubjectiveWorldView(BaseModel):
    """A character's subjective perception of the world at a moment."""
    character_id: str 
    timestamp: str 
    perceived_location_id: str
    perceived_location_description: str 
    visible_characters: List[VisibleCharacterState] = Field(default_factory=list)
    visible_objects: List[VisibleObjectState] = Field(default_factory=list)
    recent_perceived_events: List[SubjectiveEvent] = Field(default_factory=list)
    inferred_context: str = "No specific inferences drawn at this moment."
    active_focus_or_goal: Optional[str] = None 