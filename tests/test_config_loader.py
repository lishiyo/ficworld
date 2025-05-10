"""
Unit tests for ConfigLoader in modules/config_loader.py.
"""
import unittest
import json
import os
import shutil
from pathlib import Path

from modules.config_loader import ConfigLoader
from modules.models import Preset, WorldDefinition, RoleArchetype

class TestConfigLoader(unittest.TestCase):
    def setUp(self):
        """Set up a temporary directory structure for config files."""
        self.test_dir = Path("temp_test_config_dir")
        self.presets_dir = self.test_dir / "presets"
        self.data_dir = self.test_dir / "data"
        self.worlds_dir = self.data_dir / "worlds"
        self.roles_dir = self.data_dir / "roles"

        # Create directories
        self.presets_dir.mkdir(parents=True, exist_ok=True)
        self.worlds_dir.mkdir(parents=True, exist_ok=True)
        self.roles_dir.mkdir(parents=True, exist_ok=True)

        # Create dummy files
        self.dummy_role_data = {
            "archetype_name": "Test Role",
            "persona_template": "A test persona.",
            "goal_templates": ["Test goal 1"],
            "starting_mood_template": {"joy": 0.5, "trust": 0.5},
            "activity_coefficient": 0.5,
            "icon": "T"
        }
        with open(self.roles_dir / "test_role.json", 'w') as f:
            json.dump(self.dummy_role_data, f)

        self.dummy_world_data = {
            "world_name": "Test World",
            "description": "A world for testing.",
            "global_lore": {"magic_system": "None"},
            "locations": [
                {"id": "loc1", "name": "Start Point", "description": "-", "connections": []}
            ],
            "script_beats": [],
            "world_events_pool": []
        }
        with open(self.worlds_dir / "test_world.json", 'w') as f:
            json.dump(self.dummy_world_data, f)

        self.dummy_preset_data = {
            "world_file": "worlds/test_world.json",
            "role_files": ["roles/test_role.json"],
            "mode": "free",
            "max_scenes": 1,
            "llm": "test_llm"
        }
        with open(self.presets_dir / "test_preset.json", 'w') as f:
            json.dump(self.dummy_preset_data, f)
            
        # Initialize ConfigLoader with the test directory
        self.loader = ConfigLoader(base_dir=str(self.test_dir))

    def tearDown(self):
        """Remove the temporary directory after tests."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_load_preset_success(self):
        preset = self.loader.load_preset("test_preset")
        self.assertIsInstance(preset, Preset)
        self.assertEqual(preset.world_file, "worlds/test_world.json")
        self.assertEqual(preset.llm, "test_llm")
        self.assertIn("roles/test_role.json", preset.role_files)

    def test_load_preset_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.loader.load_preset("non_existent_preset")

    def test_load_world_definition_success(self):
        world_def = self.loader.load_world_definition("test_world.json") 
        self.assertIsInstance(world_def, WorldDefinition)
        self.assertEqual(world_def.world_name, "Test World")
        self.assertEqual(len(world_def.locations), 1)
        self.assertEqual(world_def.locations[0].name, "Start Point")

    def test_load_world_definition_with_full_path_success(self):
        world_def = self.loader.load_world_definition("worlds/test_world.json")
        self.assertIsInstance(world_def, WorldDefinition)
        self.assertEqual(world_def.world_name, "Test World")

    def test_load_world_definition_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.loader.load_world_definition("non_existent_world.json")

    def test_load_role_archetype_success(self):
        role_arch = self.loader.load_role_archetype("test_role.json")
        self.assertIsInstance(role_arch, RoleArchetype)
        self.assertEqual(role_arch.archetype_name, "Test Role")
        self.assertEqual(role_arch.activity_coefficient, 0.5)

    def test_load_role_archetype_with_full_path_success(self):
        role_arch = self.loader.load_role_archetype("roles/test_role.json")
        self.assertIsInstance(role_arch, RoleArchetype)
        self.assertEqual(role_arch.archetype_name, "Test Role")

    def test_load_role_archetype_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.loader.load_role_archetype("non_existent_role.json")

    def test_load_full_preset_success(self):
        full_config = self.loader.load_full_preset("test_preset")
        self.assertIn("preset", full_config)
        self.assertIn("world", full_config)
        self.assertIn("roles", full_config)
        self.assertIsInstance(full_config["preset"], Preset)
        self.assertIsInstance(full_config["world"], WorldDefinition)
        self.assertIsInstance(full_config["roles"], list)
        self.assertIsInstance(full_config["roles"][0], RoleArchetype)
        self.assertEqual(full_config["preset"].llm, "test_llm")
        self.assertEqual(full_config["world"].world_name, "Test World")
        self.assertEqual(full_config["roles"][0].archetype_name, "Test Role")

    def test_load_json_invalid_json(self):
        invalid_json_path = self.presets_dir / "invalid.json"
        with open(invalid_json_path, 'w') as f:
            f.write("this is not json")
        with self.assertRaises(json.JSONDecodeError):
            self.loader.load_json(invalid_json_path)

if __name__ == '__main__':
    unittest.main() 