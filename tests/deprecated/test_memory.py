# Tests for the MemoryManager module 

import unittest
from datetime import datetime
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

# Add project root to sys.path if necessary
if str(Path.cwd().parent) not in sys.path: # Assuming tests are in a 'tests' subdirectory
    sys.path.insert(0, str(Path.cwd().parent))

from modules.memory_manager import MemoryManager, MemoryEntry # Assuming MemoryEntry is in memory.py
from modules.models import MoodVector, LogEntry # For creating dummy LogEntry objects

class TestMemoryManager(unittest.TestCase):

    def setUp(self):
        """Set up for each test."""
        self.memory_manager = MemoryManager()
        self.actor1 = "Alice"
        self.actor2 = "Bob"
        self.mood_happy = MoodVector(joy=0.8, fear=0.1, anger=0.0, sadness=0.0, surprise=0.2, trust=0.5)
        self.mood_sad = MoodVector(joy=0.1, fear=0.2, anger=0.1, sadness=0.8, surprise=0.1, trust=0.3)

    def test_initialization(self):
        """Test that MemoryManager initializes with empty stores."""
        self.assertEqual(self.memory_manager.ltm_store, [])
        self.assertEqual(self.memory_manager.stm, {})
        self.assertEqual(self.memory_manager.scene_summaries, {})

    def test_remember_adds_to_ltm_and_stm(self):
        """Test that remember correctly adds a memory entry to LTM and STM."""
        entry = self.memory_manager.remember(self.actor1, "Event 1 for Alice", self.mood_happy)
        
        self.assertIn(entry, self.memory_manager.ltm_store)
        self.assertIn(entry, self.memory_manager.stm[self.actor1])
        self.assertEqual(len(self.memory_manager.ltm_store), 1)
        self.assertEqual(len(self.memory_manager.stm[self.actor1]), 1)
        self.assertEqual(entry.actor_name, self.actor1)
        self.assertEqual(entry.event_description, "Event 1 for Alice")
        self.assertEqual(entry.mood_at_encoding, self.mood_happy)

    def test_remember_stm_size_limit(self):
        """Test that STM for an actor respects the size limit (default 10)."""
        for i in range(15):
            self.memory_manager.remember(self.actor1, f"Event {i+1}", self.mood_happy)
        
        self.assertEqual(len(self.memory_manager.stm[self.actor1]), 10)
        self.assertEqual(self.memory_manager.stm[self.actor1][0].event_description, "Event 6") # 1-5 are popped
        self.assertEqual(self.memory_manager.stm[self.actor1][-1].event_description, "Event 15")
        self.assertEqual(len(self.memory_manager.ltm_store), 15) # LTM should have all

    def test_retrieve_mvp(self):
        """Test MVP retrieve: returns last N memories for the actor from LTM."""
        self.memory_manager.remember(self.actor1, "Alice Event 1", self.mood_happy)
        entry2 = self.memory_manager.remember(self.actor1, "Alice Event 2", self.mood_sad)
        self.memory_manager.remember(self.actor2, "Bob Event 1", self.mood_happy)
        entry3 = self.memory_manager.remember(self.actor1, "Alice Event 3", self.mood_happy)

        retrieved_alice = self.memory_manager.retrieve(self.actor1, max_results=2)
        self.assertEqual(len(retrieved_alice), 2)
        self.assertEqual(retrieved_alice[0], entry3) # Most recent
        self.assertEqual(retrieved_alice[1], entry2)

        retrieved_bob = self.memory_manager.retrieve(self.actor2, max_results=5)
        self.assertEqual(len(retrieved_bob), 1)
        self.assertEqual(retrieved_bob[0].event_description, "Bob Event 1")
        
        retrieved_none = self.memory_manager.retrieve("UnknownActor")
        self.assertEqual(len(retrieved_none), 0)

    def test_get_stm_for_actor(self):
        """Test getting STM for an actor."""
        entry1 = self.memory_manager.remember(self.actor1, "Alice STM 1", self.mood_happy)
        self.memory_manager.remember(self.actor2, "Bob STM 1", self.mood_sad)
        
        alice_stm = self.memory_manager.get_stm_for_actor(self.actor1)
        self.assertEqual(len(alice_stm), 1)
        self.assertEqual(alice_stm[0], entry1)
        
        bob_stm = self.memory_manager.get_stm_for_actor(self.actor2)
        self.assertEqual(len(bob_stm), 1)
        self.assertEqual(bob_stm[0].event_description, "Bob STM 1")

        unknown_stm = self.memory_manager.get_stm_for_actor("Unknown")
        self.assertEqual(len(unknown_stm), 0)

    def test_summarise_scene_mvp(self):
        """Test MVP summarise_scene: concatenates event descriptions."""
        log_entries = [
            LogEntry(actor=self.actor1, plan={}, outcome="Alice did something.", mood_during_action=self.mood_happy),
            LogEntry(actor=self.actor2, plan={}, outcome="Bob reacted.", mood_during_action=self.mood_sad)
        ]
        scene_num = 1
        summary = self.memory_manager.summarise_scene(scene_num, log_entries)
        
        expected_summary = "Event by Alice: Alice did something.\nEvent by Bob: Bob reacted."
        self.assertEqual(summary, expected_summary)
        self.assertIn(scene_num, self.memory_manager.scene_summaries)
        self.assertEqual(self.memory_manager.scene_summaries[scene_num], expected_summary)

    def test_summarise_scene_empty_log(self):
        """Test summarise_scene with an empty log."""
        summary = self.memory_manager.summarise_scene(1, [])
        self.assertIsNone(summary)
        self.assertNotIn(1, self.memory_manager.scene_summaries)

    def test_get_scene_summary(self):
        """Test retrieving a scene summary."""
        log_entries = [LogEntry(actor=self.actor1, plan={}, outcome="Test event.", mood_during_action=self.mood_happy)]
        self.memory_manager.summarise_scene(1, log_entries)
        
        summary = self.memory_manager.get_scene_summary(1)
        self.assertEqual(summary, "Event by Alice: Test event.")
        
        summary_none = self.memory_manager.get_scene_summary(2)
        self.assertIsNone(summary_none)

    def test_clear_stm_for_actor(self):
        """Test clearing STM for a specific actor."""
        self.memory_manager.remember(self.actor1, "Event A1", self.mood_happy)
        self.memory_manager.remember(self.actor2, "Event B1", self.mood_sad)
        
        self.memory_manager.clear_stm_for_actor(self.actor1)
        self.assertEqual(len(self.memory_manager.get_stm_for_actor(self.actor1)), 0)
        self.assertEqual(len(self.memory_manager.get_stm_for_actor(self.actor2)), 1) # Bob's STM remains

    def test_clear_all_stm(self):
        """Test clearing STM for all actors."""
        self.memory_manager.remember(self.actor1, "Event A1", self.mood_happy)
        self.memory_manager.remember(self.actor2, "Event B1", self.mood_sad)
        
        self.memory_manager.clear_all_stm()
        self.assertEqual(len(self.memory_manager.get_stm_for_actor(self.actor1)), 0)
        self.assertEqual(len(self.memory_manager.get_stm_for_actor(self.actor2)), 0)
        self.assertEqual(self.memory_manager.stm.get(self.actor1, []), [])
        self.assertEqual(self.memory_manager.stm.get(self.actor2, []), [])


    def test_reset_memory(self):
        """Test resetting all memory stores."""
        self.memory_manager.remember(self.actor1, "Event 1", self.mood_happy)
        self.memory_manager.summarise_scene(1, [LogEntry(actor=self.actor1, plan={}, outcome="Outcome", mood_during_action=self.mood_happy)])
        
        self.memory_manager.reset_memory()
        
        self.assertEqual(self.memory_manager.ltm_store, [])
        self.assertEqual(self.memory_manager.stm, {})
        self.assertEqual(self.memory_manager.scene_summaries, {})

if __name__ == '__main__':
    unittest.main() 