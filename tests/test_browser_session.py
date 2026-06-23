import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from goblet import browser_session


COMMANDS = [
    "help bex go silver",
    "bex go silver",
    "ask toad assess glass cup",
    "slap toad",
    "ask toad assess silver cup",
]


class BrowserSessionTests(unittest.TestCase):
    def test_default_session_uses_seed_zero(self):
        default_packet = browser_session.start()
        seeded_packet = browser_session.start("0")

        self.assertEqual(default_packet["seed"], "0")
        self.assertEqual(default_packet["lines"], seeded_packet["lines"])
        self.assertIn("random seed: 0", default_packet["transcript"])

    def test_seeded_session_is_deterministic(self):
        first = run_seeded_transcript("browser-seed")
        second = run_seeded_transcript("browser-seed")

        self.assertEqual(first, second)

    def test_show_does_not_advance_or_mutate_save(self):
        packet = browser_session.start("show-seed")

        shown = browser_session.show(packet["save_data"])
        shown_again = browser_session.show(packet["save_data"])

        self.assertEqual(shown["lines"], shown_again["lines"])
        self.assertEqual(shown["save_data"], shown_again["save_data"])

    def test_step_round_trips_save_and_exports_transcript(self):
        packet = browser_session.start("round-trip")
        packet = browser_session.step(packet["save_data"], "help")
        transcript = browser_session.export_transcript(packet["save_data"])

        self.assertEqual(packet["status"], "playing")
        self.assertIn("Liar's Labyrinth", transcript)
        self.assertIn("> help", transcript)
        self.assertIn("actions:", transcript)

    def test_quit_marks_session_resigned(self):
        packet = browser_session.start("quit-seed")
        packet = browser_session.step(packet["save_data"], "quit")

        self.assertEqual(packet["status"], "resigned")
        self.assertIn("you leave the labyrinth unresolved", packet["transcript"])


def run_seeded_transcript(seed: str) -> str:
    packet = browser_session.start(seed)
    for command in COMMANDS:
        packet = browser_session.step(packet["save_data"], command)
    return packet["transcript"]


if __name__ == "__main__":
    unittest.main()
