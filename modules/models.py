"""
Core data structures for FicWorld.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Any
from datetime import datetime


@dataclass
class MoodVector:
    """
    Mood representation with 6 core emotions on a scale of 0.0 to 1.0.
    Used for character emotional state and memory encoding.
    """
    joy: float = 0.0
    fear: float = 0.0
    anger: float = 0.0
    sadness: float = 0.0
    surprise: float = 0.0
    trust: float = 0.0

    def __post_init__(self):
        """Ensure all values are between 0 and 1"""
        for attr, value in self.__dict__.items():
            if not 0.0 <= value <= 1.0:
                setattr(self, attr, max(0.0, min(1.0, value)))


@dataclass
class RoleArchetype:
    """
    Character archetype loaded from data/roles/*.json
    Used as a template for creating individual character instances.
    """
    archetype_name: str
    persona_template: str
    goal_templates: List[str]
    starting_mood_template: Dict[str, float]
    activity_coefficient: float
    icon: Optional[str] = None

    def to_mood_vector(self) -> MoodVector:
        """Convert the mood template dictionary to a MoodVector object"""
        return MoodVector(
            joy=self.starting_mood_template.get("joy", 0.0),
            fear=self.starting_mood_template.get("fear", 0.0),
            anger=self.starting_mood_template.get("anger", 0.0),
            sadness=self.starting_mood_template.get("sadness", 0.0),
            surprise=self.starting_mood_template.get("surprise", 0.0),
            trust=self.starting_mood_template.get("trust", 0.0)
        )


@dataclass
class Location:
    """
    A location within a world definition.
    """
    id: str
    name: str
    description: str
    connections: List[str]


@dataclass
class ScriptBeat:
    """
    A scripted story beat for guiding the narrative in script mode.
    """
    scene_id: int
    beat_id: str
    description: str
    triggers_event: Optional[str] = None
    required_location: Optional[str] = None


@dataclass
class WorldEvent:
    """
    An event that can be triggered by the world agent.
    """
    event_id: str
    description: str
    effects: List[str]


@dataclass
class FactionInfo:
    """
    Information about a faction within the world lore.
    """
    name: str
    details: str


@dataclass
class GlobalLore:
    """
    World-level lore information.
    """
    magic_system: Optional[str] = None
    key_factions: List[FactionInfo] = field(default_factory=list)
    # Add additional lore fields as needed


@dataclass
class WorldDefinition:
    """
    World definition loaded from data/worlds/*.json
    Defines the environment, locations, and optional scripted events.
    """
    world_name: str
    description: str
    locations: List[Location]
    global_lore: GlobalLore
    script_beats: List[ScriptBeat] = field(default_factory=list)
    world_events_pool: List[WorldEvent] = field(default_factory=list)


@dataclass
class Preset:
    """
    Simulation configuration loaded from presets/*.json
    Specifies which world and character archetypes to use, along with simulation parameters.
    """
    world_file: str
    role_files: List[str]
    mode: str  # "free" or "script"
    max_scenes: int
    llm: str
    script_file: Optional[str] = None
    # Add additional configuration parameters as needed


@dataclass
class CharacterState:
    """
    Current state of a character within the world, as tracked by WorldAgent.
    """
    location: str
    current_mood: MoodVector
    conditions: List[str] = field(default_factory=list)


@dataclass
class CharacterPlanOutput:
    """
    Schema for the output of CharacterAgent.plan()
    Represents a structured action plan.
    """
    action: str  # e.g., "speak", "move", "interact_object", "attack"
    details: Dict[str, Any]  # content varies by action type
    tone_of_action: str  # e.g., "cautious", "angry", "joyful", "determined"


@dataclass
class WorldState:
    """
    Current state of the world, as managed by WorldAgent.
    """
    current_scene_id: str
    turn_number: int
    time_of_day: str
    environment_description: str
    active_characters: List[str]
    character_states: Dict[str, CharacterState]
    recent_events_summary: List[str] = field(default_factory=list)


@dataclass
class MemoryEntry:
    """
    A memory entry stored in the MemoryManager.
    """
    timestamp: datetime
    actor_name: str
    event_description: str
    mood_at_encoding: MoodVector
    embedding: Optional[List[float]] = None
    significance: float = 1.0


@dataclass
class LogEntry:
    """
    An entry in the simulation log.
    Used to track turns for narration and debugging.
    """
    actor: str
    plan: CharacterPlanOutput
    outcome: str
    mood_during_action: MoodVector
    timestamp: datetime = field(default_factory=datetime.now)
    is_world_event: bool = False 