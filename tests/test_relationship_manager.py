import unittest

from modules.relationship_manager import RelationshipManager, RelationshipState

class TestRelationshipManager(unittest.TestCase):

    def setUp(self):
        self.manager = RelationshipManager()
        self.char_a = "Alice"
        self.char_b = "Bob"
        self.char_c = "Carol"

    def test_initial_state_is_default(self):
        state = self.manager.get_state(self.char_a, self.char_b)
        self.assertIsInstance(state, RelationshipState)
        self.assertEqual(state.trust, 0.5) # Default trust
        self.assertEqual(state.affinity, 0.0) # Default affinity
        self.assertEqual(state.status, "neutral") # Default status

    def test_update_and_get_state(self):
        new_state_data = {"trust": 0.8, "affinity": 0.6, "status": "friends"}
        new_state_obj = RelationshipState(**new_state_data)
        
        self.manager.update_state(self.char_a, self.char_b, new_state_obj)
        retrieved_state = self.manager.get_state(self.char_a, self.char_b)
        
        self.assertEqual(retrieved_state.trust, 0.8)
        self.assertEqual(retrieved_state.affinity, 0.6)
        self.assertEqual(retrieved_state.status, "friends")

        # Check order independence
        retrieved_state_reversed = self.manager.get_state(self.char_b, self.char_a)
        self.assertEqual(retrieved_state_reversed, retrieved_state)

    def test_adjust_state_creates_if_not_exists(self):
        adjusted_state = self.manager.adjust_state(self.char_a, self.char_b, trust_delta=0.1, affinity_delta=-0.2, new_status="rivals")
        self.assertAlmostEqual(adjusted_state.trust, 0.5 + 0.1)
        self.assertAlmostEqual(adjusted_state.affinity, 0.0 - 0.2)
        self.assertEqual(adjusted_state.status, "rivals")

        retrieved_state = self.manager.get_state(self.char_a, self.char_b)
        self.assertEqual(retrieved_state, adjusted_state)

    def test_adjust_state_modifies_existing(self):
        initial_state = RelationshipState(trust=0.7, affinity=0.3, status="allies")
        self.manager.update_state(self.char_a, self.char_b, initial_state)
        
        adjusted_state = self.manager.adjust_state(self.char_a, self.char_b, trust_delta=-0.4, affinity_delta=0.2, new_status="trusted_allies")
        self.assertAlmostEqual(adjusted_state.trust, 0.7 - 0.4)
        self.assertAlmostEqual(adjusted_state.affinity, 0.3 + 0.2)
        self.assertEqual(adjusted_state.status, "trusted_allies")

    def test_adjust_state_clamping(self):
        # Trust clamping (0.0 to 1.0)
        self.manager.adjust_state(self.char_a, self.char_b, trust_delta=10.0) # Way over
        state1 = self.manager.get_state(self.char_a, self.char_b)
        self.assertEqual(state1.trust, 1.0)

        self.manager.adjust_state(self.char_a, self.char_b, trust_delta=-20.0) # Way under (from 1.0)
        state2 = self.manager.get_state(self.char_a, self.char_b)
        self.assertEqual(state2.trust, 0.0)

        # Affinity clamping (-1.0 to 1.0)
        self.manager.adjust_state(self.char_a, self.char_c, affinity_delta=5.0)
        state3 = self.manager.get_state(self.char_a, self.char_c)
        self.assertEqual(state3.affinity, 1.0)

        self.manager.adjust_state(self.char_a, self.char_c, affinity_delta=-10.0) # Way under (from 1.0)
        state4 = self.manager.get_state(self.char_a, self.char_c)
        self.assertEqual(state4.affinity, -1.0)

    def test_get_context_for_character_no_relations(self):
        context = self.manager.get_context_for_character(" одинокий_персонаж ") # Using cyrillic to avoid accidental match with existing self.char_ vars
        self.assertEqual(context, "You have no significant established relationships yet.")

    def test_get_context_for_character_with_relations(self):
        self.manager.adjust_state(self.char_a, self.char_b, trust_delta=0.3, affinity_delta=0.7, new_status="best_friends") # A-B: T=0.8, A=0.7
        self.manager.adjust_state(self.char_a, self.char_c, trust_delta=-0.2, affinity_delta=-0.5, new_status="enemies")    # A-C: T=0.3, A=-0.5
        
        context_a = self.manager.get_context_for_character(self.char_a)
        self.assertIn(f"With {self.char_b}: Status is 'best_friends'. Trust: 0.80/1.0. Affinity: 0.70/1.0.", context_a)
        self.assertIn(f"With {self.char_c}: Status is 'enemies'. Trust: 0.30/1.0. Affinity: -0.50/1.0.", context_a)
        self.assertTrue(context_a.startswith("Your current relationships of note:"))

        # Test order for Bob (should only show relation with Alice)
        context_b = self.manager.get_context_for_character(self.char_b)
        self.assertIn(f"With {self.char_a}: Status is 'best_friends'. Trust: 0.80/1.0. Affinity: 0.70/1.0.", context_b)
        self.assertNotIn(self.char_c, context_b) # Bob has no direct relation with Carol set up here

    def test_get_context_for_character_limit_summaries(self):
        # Create 6 relationships for char_a
        chars = ["Zack", "Yara", "Xeno", "Will", "Vera", "Ulf"]
        for i, other_char in enumerate(chars):
            self.manager.adjust_state(self.char_a, other_char, trust_delta=0.1*i, affinity_delta=0.15*i, new_status=f"ally_{i}")

        context_limited = self.manager.get_context_for_character(self.char_a, num_relations_to_summarize=3)
        lines = context_limited.split('\n')
        self.assertEqual(len(lines), 1 + 3) # Header + 3 relations
        self.assertIn("Ulf", context_limited) # Ulf has highest affinity/trust due to loop
        self.assertNotIn("Zack", context_limited) # Zack would be lowest and cut off

    def test_get_all_relationships(self):
        self.manager.adjust_state(self.char_a, self.char_b, new_status="testing")
        all_rels = self.manager.get_all_relationships()
        self.assertEqual(len(all_rels), 1)
        key = frozenset([self.char_a, self.char_b])
        self.assertIn(key, all_rels)
        self.assertEqual(all_rels[key].status, "testing")

    def test_relationship_with_oneself_raises_error(self):
        with self.assertRaises(ValueError):
            self.manager.get_state(self.char_a, self.char_a)
        with self.assertRaises(ValueError):
            self.manager.adjust_state(self.char_a, self.char_a, trust_delta=0.1)

if __name__ == '__main__':
    unittest.main() 