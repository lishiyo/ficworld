"""
Unit tests for ConfigLoader in modules/config_loader.py.
"""
import unittest
import json
import os
import shutil
from pathlib import Path
import pytest
from pydantic import ValidationError

from modules.config_loader import ConfigLoader
from modules.models import Preset, WorldDefinition, RoleArchetype
from modules.data_models import CharacterConfig

# Helper to create temp directory structure for tests
TEMP_TEST_DIR_BASE = Path("_temp_test_data_cl") # Shortened name

class TestConfigLoader(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up temporary directory structure once for all tests in this class."""
        cls.temp_base_dir = TEMP_TEST_DIR_BASE
        cls.roles_dir = cls.temp_base_dir / "data" / "roles"
        cls.presets_dir = cls.temp_base_dir / "presets" # For any existing tests
        cls.worlds_dir = cls.temp_base_dir / "data" / "worlds" # For any existing tests

        if cls.temp_base_dir.exists():
            shutil.rmtree(cls.temp_base_dir)
        
        cls.roles_dir.mkdir(parents=True, exist_ok=True)
        cls.presets_dir.mkdir(parents=True, exist_ok=True)
        cls.worlds_dir.mkdir(parents=True, exist_ok=True)

        # Valid V1 character config
        valid_char_data = {
            "full_name": "Valid Character", "persona": "Valid persona.", "backstory": "Valid backstory.",
            "initial_goals": {"long_term": ["Achieve greatness"], "short_term": ["Survive today"]},
            "activity_coefficient": 0.7, "starting_mood": {"happy": 0.9}
        }
        with open(cls.roles_dir / "valid_char_v1.json", "w") as f: json.dump(valid_char_data, f)
        
        # Malformed JSON file for V1 tests
        with open(cls.roles_dir / "malformed_v1.json", "w") as f: f.write("{\"name\": \"Test\", invalid_json") # Note: Corrected malformed JSON

        # Valid JSON but incorrect V1 schema (e.g., missing required field)
        incorrect_schema_data = {"persona": "Persona without full_name or backstory."}
        with open(cls.roles_dir / "incorrect_schema_v1.json", "w") as f: json.dump(incorrect_schema_data, f)
        
        # Add any dummy files needed for *existing* tests from the original setUp if necessary
        # For example, if there were V0 role files, presets, etc.
        dummy_v0_role_data = {
            "archetype_name": "Test Role V0", "persona_template": "A V0 persona.",
            "goal_templates": ["V0 goal"], "starting_mood_template": {"joy": 0.5},
            "activity_coefficient": 0.5, "icon": "V0"
        }
        with open(cls.roles_dir / "test_role_v0.json", "w") as f: json.dump(dummy_v0_role_data, f)

        dummy_world_data = {
            "world_name": "Test World V0", "description": "A V0 world.",
            "locations": [],"global_lore": {},
        }
        with open(cls.worlds_dir / "test_world_v0.json", "w") as f: json.dump(dummy_world_data, f)

        dummy_preset_data = {
            "world_file": "data/worlds/test_world_v0.json", # Adjusted path for consistency
            "role_files": ["data/roles/test_role_v0.json"], # Adjusted path
            "llm": {"model_name": "test_model"} # Using dict for LLM settings
        }
        with open(cls.presets_dir / "test_preset_v0.json", "w") as f: json.dump(dummy_preset_data, f)

    @classmethod
    def tearDownClass(cls):
        """Remove the temporary directory after all tests in this class have run."""
        if cls.temp_base_dir.exists():
            shutil.rmtree(cls.temp_base_dir)

    def setUp(self):
        """Initialize ConfigLoader for each test method."""
        self.loader = ConfigLoader(base_dir=str(self.temp_base_dir))

    # --- V0 tests (adapted from original structure if they existed) ---
    def test_load_preset_v0_example(self):
        # This test now assumes test_preset_v0.json exists from setUpClass
        preset = self.loader.load_preset("test_preset_v0.json")
        self.assertIsInstance(preset, Preset)
        self.assertEqual(preset.world_file, "data/worlds/test_world_v0.json")
        self.assertEqual(preset.llm.model_name, "test_model")
        self.assertIn("data/roles/test_role_v0.json", preset.role_files)

    def test_load_role_archetype_v0_example(self):
        role_arch = self.loader.load_role_archetype("test_role_v0.json")
        self.assertIsInstance(role_arch, RoleArchetype)
        self.assertEqual(role_arch.archetype_name, "Test Role V0")

    # --- General load_json tests (can use any valid JSON file created) ---
    def test_g_load_json_valid(self):
        # Using one of the V1 files as it's a valid JSON
        valid_json_path = self.roles_dir / "valid_char_v1.json"
        data = self.loader.load_json(valid_json_path)
        self.assertEqual(data["full_name"], "Valid Character")

    def test_g_load_json_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.loader.load_json(self.temp_base_dir / "non_existent.json")

    def test_g_load_json_invalid_format(self):
        # Using the V1 malformed file
        invalid_json_path = self.roles_dir / "malformed_v1.json"
        with self.assertRaises(json.JSONDecodeError):
            self.loader.load_json(invalid_json_path)
    
    # --- Tests for load_character_config_v1 (New V1 functionality) --- 
    def test_v1_load_character_config_valid(self):
        config = self.loader.load_character_config_v1("valid_char_v1.json")
        self.assertIsInstance(config, CharacterConfig)
        self.assertEqual(config.full_name, "Valid Character")
        self.assertEqual(config.persona, "Valid persona.")
        self.assertEqual(config.initial_goals.long_term, ["Achieve greatness"])
        self.assertEqual(config.activity_coefficient, 0.7)
        self.assertEqual(config.starting_mood, {"happy": 0.9})

    def test_v1_load_character_config_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.loader.load_character_config_v1("non_existent_v1.json")

    def test_v1_load_character_config_malformed_json(self):
        # This uses the V1 specific malformed file
        with self.assertRaises(json.JSONDecodeError):
            self.loader.load_character_config_v1("malformed_v1.json")

    def test_v1_load_character_config_incorrect_schema(self):
        # This uses the V1 specific incorrect schema file
        with self.assertRaises(ValidationError):
            self.loader.load_character_config_v1("incorrect_schema_v1.json")

if __name__ == '__main__':
    unittest.main() 