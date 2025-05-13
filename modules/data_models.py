from pydantic import BaseModel, Field
from typing import List, Dict

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