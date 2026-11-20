"""Independent experiment tests; does not import any private Shaelvien code."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "experiments" / "continuity_ecology"
sys.path.insert(0, str(ROOT))
from engine import advance, delete_agent, imagine, inspect, load, new_world, save, verify  # noqa: E402


class EcologyTests(unittest.TestCase):
    def test_initial_generation_and_parentage(self):
        w = new_world()
        self.assertEqual([a["id"] for a in w["agents"]], ["A", "B", "C"])
        self.assertEqual(w["agents"][2]["parents"], ["A", "B"])
        self.assertTrue(verify(w))

    def test_deterministic_resumption_and_persistence(self):
        original = new_world(seed=33)
        advance(original, 75)
        with tempfile.TemporaryDirectory() as d:
            name = Path(d) / "world.json"
            save(original, name)
            restored = load(name)
            advance(restored, 80)
        straight = new_world(seed=33)
        advance(straight, 155)
        self.assertEqual(straight, restored)
        self.assertGreater(sum(len(a["q"]) for a in straight["agents"]), 0)

    def test_imagination_is_read_only(self):
        actual = new_world()
        before = copy.deepcopy(actual)
        projection = imagine(actual, 18)
        self.assertEqual(actual, before)
        self.assertEqual(projection["classification"], "HYPOTHESIS")

    def test_parent_deletion_preserves_lineage(self):
        w = new_world()
        delete_agent(w, "A")
        self.assertEqual(len([a for a in w["agents"] if a["status"] == "deleted"]), 1)
        self.assertEqual(len(w["agents"][2]["parents"]), 2)
        self.assertEqual(len([a for a in w["agents"] if a["id"] == "B" and a["status"] == "alive"]), 1)
        advance(w, 1)
        self.assertNotIn("independence", [e["kind"] for e in w["history"]])
        delete_agent(w, "B")
        advance(w, 1)
        self.assertIn("independence", [e["kind"] for e in w["history"]])
        self.assertTrue(verify(w))

    def test_hash_chain_detects_tampering(self):
        w = new_world()
        w["history"][0]["details"]["seed"] = 999
        self.assertFalse(verify(w))

    def test_plant_anchors_do_not_move(self):
        w = new_world()
        coords = {p["id"]: (p["x"], p["y"]) for p in w["plants"]}
        advance(w, 160)
        self.assertEqual(coords, {p["id"]: (p["x"], p["y"]) for p in w["plants"]})

    def test_seed_changes_world(self):
        self.assertNotEqual(new_world(seed=1)["cells"], new_world(seed=2)["cells"])

    def test_bounded_execution(self):
        with self.assertRaises(ValueError):
            advance(new_world(), 1001)


if __name__ == "__main__":
    unittest.main()
