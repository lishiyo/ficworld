import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add project root to sys.path if necessary
if str(Path.cwd().parent) not in sys.path: # Assuming tests are in a 'tests' subdirectory
    sys.path.insert(0, str(Path.cwd().parent))
if str(Path.cwd()) not in sys.path: # If tests are in the root, Path.cwd() is the project root
    sys.path.insert(0, str(Path.cwd()))


from modules.memory import MemoryManager
from modules.models import LogEntry # For creating dummy LogEntry objects


class TestMemoryManagerV1Features(unittest.TestCase):

    def setUp(self):
        self.memory_manager = MemoryManager()
        # Manually add some scene summaries for testing
        self.memory_manager.scene_summaries = {
            1: "Scene 1 summary: Alice met Bob.",
            2: "Scene 2 summary: Bob revealed a secret.",
            3: "Scene 3 summary: Alice was shocked.",
            4: "Scene 4 summary: They decided to investigate further."
        }

    def test_get_recent_scene_summaries_default_count(self):
        summaries_str = self.memory_manager.get_recent_scene_summaries()
        # Expects last 3 summaries (default count), oldest of the 3 first
        self.assertIn("Summary of Scene 2:\nScene 2 summary: Bob revealed a secret.", summaries_str)
        self.assertIn("Summary of Scene 3:\nScene 3 summary: Alice was shocked.", summaries_str)
        self.assertIn("Summary of Scene 4:\nScene 4 summary: They decided to investigate further.", summaries_str)
        self.assertNotIn("Scene 1 summary", summaries_str)
        self.assertTrue(summaries_str.startswith("Summary of Scene 2:"))
        # Check separator
        self.assertEqual(summaries_str.count("\n\n---\n\n"), 2) 

    def test_get_recent_scene_summaries_custom_count(self):
        summaries_str = self.memory_manager.get_recent_scene_summaries(count=2)
        self.assertIn("Summary of Scene 3:", summaries_str)
        self.assertIn("Summary of Scene 4:", summaries_str)
        self.assertNotIn("Scene 1 summary", summaries_str)
        self.assertNotIn("Scene 2 summary", summaries_str)
        self.assertTrue(summaries_str.startswith("Summary of Scene 3:"))
        self.assertEqual(summaries_str.count("\n\n---\n\n"), 1)

    def test_get_recent_scene_summaries_more_than_available(self):
        summaries_str = self.memory_manager.get_recent_scene_summaries(count=10)
        # Should return all 4 available, Scene 1 first
        self.assertIn("Scene 1 summary", summaries_str)
        self.assertIn("Scene 2 summary", summaries_str)
        self.assertIn("Scene 3 summary", summaries_str)
        self.assertIn("Scene 4 summary", summaries_str)
        self.assertTrue(summaries_str.startswith("Summary of Scene 1:"))
        self.assertEqual(summaries_str.count("\n\n---\n\n"), 3)

    def test_get_recent_scene_summaries_zero_count(self):
        summaries_str = self.memory_manager.get_recent_scene_summaries(count=0)
        self.assertEqual(summaries_str, "No scene summaries are available yet.") # Or empty string depending on impl.

    def test_get_recent_scene_summaries_no_summaries_exist(self):
        empty_manager = MemoryManager() # Fresh instance with no summaries
        summaries_str = empty_manager.get_recent_scene_summaries()
        self.assertEqual(summaries_str, "No scene summaries are available yet.")

    def test_get_recent_scene_summaries_one_summary_custom_count(self):
        single_summary_manager = MemoryManager()
        single_summary_manager.scene_summaries = {1: "Only one summary here."}
        summaries_str = single_summary_manager.get_recent_scene_summaries(count=3)
        self.assertIn("Summary of Scene 1:\nOnly one summary here.", summaries_str)
        self.assertFalse("\n\n---\n\n" in summaries_str)

    # Test the existing summarise_scene briefly to ensure it populates for get_recent_scene_summaries
    def test_summarise_scene_populates_for_get_recent(self):
        manager = MemoryManager()
        # Dummy LogEntry requires actor and outcome. Create simple ones.
        log_entry1 = LogEntry(scene=1, turn=1, actor="TestActor", outcome="Event 1 occurred.")
        log_entry2 = LogEntry(scene=1, turn=2, actor="TestActor", outcome="Event 2 happened.")
        scene_log = [log_entry1, log_entry2]
        
        manager.summarise_scene(scene_number=1, scene_log=scene_log)
        summaries_str = manager.get_recent_scene_summaries(count=1)
        self.assertIn("Summary of Scene 1:", summaries_str)
        self.assertIn("Event by TestActor: Event 1 occurred.", summaries_str)
        self.assertIn("Event by TestActor: Event 2 happened.", summaries_str)


if __name__ == '__main__':
    unittest.main() 