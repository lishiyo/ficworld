"""
Unit tests for main.py.
"""
import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import argparse
import json
from pathlib import Path
from io import StringIO

# Add project root to sys.path to allow importing main and modules
# This is often needed when running tests from a subdirectory or with certain test runners
if str(Path.cwd()) not in sys.path:
    sys.path.insert(0, str(Path.cwd()))

import main  # Import the main module
from modules.config_loader import ConfigLoader
from modules.models import Preset, WorldDefinition, RoleArchetype # Assuming these are used by main

class TestMain(unittest.TestCase):

    @patch('main.ConfigLoader')
    @patch('main.Path.mkdir') # Mock mkdir to avoid actual directory creation
    @patch('builtins.open', new_callable=mock_open) # Mock open for config_used.json
    @patch('main.parse_args')
    def test_main_successful_run(self, mock_parse_args, mock_file_open, mock_mkdir, MockConfigLoader):
        """Test main function with valid preset and successful loading."""
        # Setup mock for parse_args
        mock_args = argparse.Namespace(
            preset="test_preset", 
            output_dir=None, 
            debug=False
        )
        mock_parse_args.return_value = mock_args

        # Setup mock for ConfigLoader instance and its methods
        mock_loader_instance = MockConfigLoader.return_value
        mock_preset = Preset(world_file="w.json", role_files=["r.json"], mode="free", max_scenes=1, llm="m")
        mock_world = WorldDefinition(world_name="TestWorld", description="-", locations=[], global_lore=MagicMock())
        mock_role = RoleArchetype(archetype_name="TestRole", persona_template="-", goal_templates=[], starting_mood_template={}, activity_coefficient=0.5)
        
        mock_loader_instance.load_full_preset.return_value = {
            "preset": mock_preset,
            "world": mock_world,
            "roles": [mock_role]
        }

        # Capture print output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            return_code = main.main()
        
        self.assertEqual(return_code, 0)
        mock_parse_args.assert_called_once()
        MockConfigLoader.assert_called_once_with() # Check if ConfigLoader was initialized
        mock_loader_instance.load_full_preset.assert_called_once_with("test_preset")
        
        # Check if output directory setup was called
        expected_output_dir = Path('outputs') / "test_preset"
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        
        # Check if config_used.json was written
        mock_file_open.assert_called_once_with(expected_output_dir / 'config_used.json', 'w', encoding='utf-8')
        
        # Check some print outputs (optional, can be brittle)
        output = mock_stdout.getvalue()
        self.assertIn("Loading preset: test_preset", output)
        self.assertIn(f"Output will be saved to: {expected_output_dir}", output)
        self.assertIn("World: TestWorld", output)
        self.assertIn("Roles: TestRole", output)
        self.assertIn("Initial setup complete.", output)

    @patch('main.parse_args')
    def test_main_file_not_found(self, mock_parse_args):
        """Test main function when ConfigLoader raises FileNotFoundError."""
        mock_args = argparse.Namespace(preset="bad_preset", output_dir=None, debug=False)
        mock_parse_args.return_value = mock_args

        with patch('main.ConfigLoader') as MockConfigLoader:
            mock_loader_instance = MockConfigLoader.return_value
            mock_loader_instance.load_full_preset.side_effect = FileNotFoundError("Preset file not found")
            
            with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                return_code = main.main()
        
        self.assertEqual(return_code, 1)
        self.assertIn("Error: Preset file not found", mock_stderr.getvalue())

    @patch('main.parse_args')
    def test_main_json_decode_error(self, mock_parse_args):
        """Test main function when ConfigLoader raises JSONDecodeError."""
        mock_args = argparse.Namespace(preset="invalid_json_preset", output_dir=None, debug=False)
        mock_parse_args.return_value = mock_args

        with patch('main.ConfigLoader') as MockConfigLoader:
            mock_loader_instance = MockConfigLoader.return_value
            mock_loader_instance.load_full_preset.side_effect = json.JSONDecodeError("Bad JSON", "doc", 0)
            
            with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                return_code = main.main()
            
        self.assertEqual(return_code, 1)
        self.assertIn("Error parsing JSON: Bad JSON", mock_stderr.getvalue())

    def test_parse_args(self):
        """Test argument parsing logic in main.parse_args."""
        test_args = ['--preset', 'my_test_preset', '--debug']
        with patch('sys.argv', ['main.py'] + test_args):
            args = main.parse_args()
        self.assertEqual(args.preset, "my_test_preset")
        self.assertTrue(args.debug)
        self.assertIsNone(args.output_dir)
        
        test_args_with_output = ['--preset', 'another', '--output-dir', '/custom/path']
        with patch('sys.argv', ['main.py'] + test_args_with_output):
            args = main.parse_args()
        self.assertEqual(args.preset, "another")
        self.assertEqual(args.output_dir, '/custom/path')
        self.assertFalse(args.debug)

    @patch('main.Path.mkdir')
    def test_setup_output_directory_default(self, mock_mkdir):
        preset_name = "sample_preset"
        expected_path = Path('outputs') / preset_name
        returned_path = main.setup_output_directory(preset_name)
        self.assertEqual(returned_path, expected_path)
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('main.Path.mkdir')
    def test_setup_output_directory_custom(self, mock_mkdir):
        preset_name = "sample_preset"
        custom_dir = "my_outputs/run1"
        expected_path = Path(custom_dir)
        returned_path = main.setup_output_directory(preset_name, custom_dir)
        self.assertEqual(returned_path, expected_path)
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


if __name__ == '__main__':
    unittest.main() 