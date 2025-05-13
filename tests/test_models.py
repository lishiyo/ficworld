"""
Unit tests for data models in modules/models.py.
"""
import unittest
from datetime import datetime

from modules.models import (
    MoodVector,
    RoleArchetype,
    Location,
    ScriptBeat,
    WorldEvent,
    FactionInfo,
    GlobalLore,
    WorldDefinition,
    Preset,
    CharacterState,
    CharacterPlanOutput,
    WorldState,
    MemoryEntry,
    LogEntry
)

class TestMoodVector(unittest.TestCase):
    def test_mood_vector_creation_defaults(self):
        mood = MoodVector()
        self.assertEqual(mood.joy, 0.0)
        self.assertEqual(mood.fear, 0.0)
        self.assertEqual(mood.anger, 0.0)
        self.assertEqual(mood.sadness, 0.0)
        self.assertEqual(mood.surprise, 0.0)
        self.assertEqual(mood.trust, 0.0)

    def test_mood_vector_creation_custom(self):
        mood = MoodVector(joy=0.5, fear=0.2, trust=0.8)
        self.assertEqual(mood.joy, 0.5)
        self.assertEqual(mood.fear, 0.2)
        self.assertEqual(mood.trust, 0.8)
        self.assertEqual(mood.anger, 0.0) # Default

    def test_mood_vector_clamping_upper(self):
        mood = MoodVector(joy=1.5, fear=-0.5)
        self.assertEqual(mood.joy, 1.0) # Clamped
        self.assertEqual(mood.fear, 0.0) # Clamped

    def test_mood_vector_clamping_lower(self):
        mood = MoodVector(sadness=-1.0, surprise=0.5)
        self.assertEqual(mood.sadness, 0.0) # Clamped
        self.assertEqual(mood.surprise, 0.5)

class TestRoleArchetype(unittest.TestCase):
    def test_role_archetype_creation(self):
        data = {
            "archetype_name": "Test Scholar",
            "persona_template": "A curious scholar.",
            "goal_templates": ["Discover {topic}."],
            "starting_mood_template": {"joy": 0.6, "surprise": 0.7},
            "activity_coefficient": 0.7,
            "icon": "📚"
        }
        archetype = RoleArchetype(**data)
        self.assertEqual(archetype.archetype_name, "Test Scholar")
        self.assertEqual(archetype.activity_coefficient, 0.7)
        self.assertIn("Discover {topic}.", archetype.goal_templates)

    def test_role_archetype_to_mood_vector(self):
        data = {
            "archetype_name": "Test Knight",
            "persona_template": "A brave knight.",
            "goal_templates": ["Protect the innocent."],
            "starting_mood_template": {"trust": 0.9, "fear": 0.1, "anger": 0.2},
            "activity_coefficient": 0.9
        }
        archetype = RoleArchetype(**data)
        mood_vector = archetype.to_mood_vector()
        self.assertIsInstance(mood_vector, MoodVector)
        self.assertEqual(mood_vector.trust, 0.9)
        self.assertEqual(mood_vector.fear, 0.1)
        self.assertEqual(mood_vector.anger, 0.2)
        self.assertEqual(mood_vector.joy, 0.0) # Default

class TestOtherDataModels(unittest.TestCase):
    def test_location_creation(self):
        loc = Location(id="loc1", name="Forest Clearing", description="A sun-dappled clearing.", connections=["loc2"])
        self.assertEqual(loc.name, "Forest Clearing")
        self.assertIn("loc2", loc.connections)

    def test_script_beat_creation(self):
        beat = ScriptBeat(scene_id=1, beat_id="b1", description="Characters meet.", triggers_event="event1")
        self.assertEqual(beat.scene_id, 1)
        self.assertEqual(beat.triggers_event, "event1")

    def test_world_event_creation(self):
        event = WorldEvent(event_id="e1", description="A storm begins.", effects=["wet"])
        self.assertEqual(event.description, "A storm begins.")
        self.assertIn("wet", event.effects)

    def test_faction_info_creation(self):
        faction = FactionInfo(name="The Elders", details="Ancient and wise.")
        self.assertEqual(faction.name, "The Elders")

    def test_global_lore_creation(self):
        faction = FactionInfo(name="The Seekers", details="They search for truth.")
        lore = GlobalLore(magic_system="Elemental", key_factions=[faction])
        self.assertEqual(lore.magic_system, "Elemental")
        self.assertEqual(len(lore.key_factions), 1)
        self.assertEqual(lore.key_factions[0].name, "The Seekers")

    def test_world_definition_creation(self):
        loc = Location(id="l1", name="Cave Entrance", description="Dark and ominous.", connections=[])
        lore = GlobalLore(magic_system="None")
        world_def = WorldDefinition(
            world_name="The Dark Caves", 
            description="A network of treacherous caves.",
            locations=[loc],
            global_lore=lore
        )
        self.assertEqual(world_def.world_name, "The Dark Caves")
        self.assertEqual(len(world_def.locations), 1)

    def test_preset_creation(self):
        preset = Preset(
            world_file="worlds/cave.json",
            role_files=["roles/miner.json"],
            mode="free",
            max_scenes=3,
            llm="test_model"
        )
        self.assertEqual(preset.mode, "free")
        self.assertEqual(preset.llm, "test_model")

    def test_character_state_creation(self):
        mood = MoodVector(joy=0.7)
        char_state = CharacterState(
            name="TestCharacter",
            persona="A test persona.",
            goals=["Test goal"],
            activity_coefficient=0.5,
            location="tavern", 
            current_mood=mood, 
            conditions=["weary"]
        )
        self.assertEqual(char_state.location, "tavern")
        self.assertEqual(char_state.current_mood.joy, 0.7)
        self.assertIn("weary", char_state.conditions)

    def test_character_plan_output_creation(self):
        plan = CharacterPlanOutput(
            action="speak", 
            details={"text": "Hello!", "target": "everyone"}, 
            tone_of_action="friendly"
        )
        self.assertEqual(plan.action, "speak")
        self.assertEqual(plan.details["text"], "Hello!")

    def test_world_state_creation(self):
        mood = MoodVector(fear=0.5)
        char_state = CharacterState(
            name="Alice",
            persona="Curious",
            goals=["Explore"],
            activity_coefficient=0.8,
            location="forest", 
            current_mood=mood
        )
        world_s = WorldState(
            current_scene_id="s1",
            turn_number=1,
            time_of_day="noon",
            environment_description="A sunny forest path.",
            active_characters=["Alice"],
            character_states={"Alice": char_state},
            recent_events_summary=["Alice entered the forest."]
        )
        self.assertEqual(world_s.turn_number, 1)
        self.assertEqual(world_s.character_states["Alice"].location, "forest")

    def test_memory_entry_creation(self):
        ts = datetime.now()
        mood = MoodVector(sadness=0.8)
        entry = MemoryEntry(
            timestamp=ts,
            actor_name="Bob",
            event_description="Bob lost his hat.",
            mood_at_encoding=mood,
            significance=0.9
        )
        self.assertEqual(entry.actor_name, "Bob")
        self.assertEqual(entry.mood_at_encoding.sadness, 0.8)

    def test_log_entry_creation(self):
        plan_output = CharacterPlanOutput(action="move", details={"target_location": "cave"}, tone_of_action="cautious")
        log = LogEntry(
            scene=1,
            turn=1,
            actor="Charlie",
            plan=plan_output,
            outcome="Charlie moved to the cave."
        )
        self.assertEqual(log.actor, "Charlie")
        self.assertEqual(log.plan.action, "move")
        self.assertTrue(log.timestamp is not None)

if __name__ == '__main__':
    unittest.main() 