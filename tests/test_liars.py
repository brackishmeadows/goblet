import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

ROOT = pathlib.Path(__file__).resolve().parents[1]

from goblet.liars import liars_expression, parse_liars, trace_liars_expression


ASTER_BRAM = """\
people:
  Aster
  Bram

statements:
  Aster calls Bram a liar
  Bram calls Aster a liar
"""


class LiarTests(unittest.TestCase):
    def test_parse_tiny_liar_file(self):
        puzzle = parse_liars(ASTER_BRAM)

        self.assertEqual(puzzle.people, ("Aster", "Bram"))
        self.assertEqual(puzzle.statements[0].speaker, "Aster")
        self.assertEqual(puzzle.statements[0].target, "Bram")
        self.assertEqual(puzzle.statements[0].target_kind, "liar")

    def test_ambiguous_two_person_puzzle(self):
        self.assertEqual(
            liars_expression(ASTER_BRAM),
            "\n".join(
                [
                    "ambiguous",
                    "possible worlds:",
                    "- Aster honest, Bram liar",
                    "- Aster liar, Bram honest",
                ]
            ),
        )

    def test_trace_rejected_and_surviving_worlds(self):
        trace = trace_liars_expression(ASTER_BRAM)

        self.assertEqual(
            trace[0],
            "There are two claimants, Aster and Bram. "
            "Aster calls Bram a liar. Bram calls Aster a liar. How can this be?",
        )
        self.assertIn("first: suppose that Aster is honest and Bram is honest.", trace)
        self.assertIn("Aster calls Bram a liar", trace)
        self.assertIn("but we supposed Aster honest, so we cannot allow this", trace)
        self.assertIn("second: suppose that Aster is honest and Bram is a liar.", trace)
        self.assertIn("this case holds", trace)
        self.assertIn("rejected worlds:", trace)
        self.assertIn("Aster calls Bram a liar", trace)
        self.assertIn(
            "- if this is false, we must reject the first world "
            "(where Aster is honest and Bram is honest)",
            trace,
        )
        self.assertIn(
            "- if this is true, we must reject the fourth world "
            "(where Aster is a liar and Bram is a liar)",
            trace,
        )
        surviving_index = trace.index("surviving worlds:")
        self.assertEqual(
            trace[surviving_index : surviving_index + 3],
            [
                "surviving worlds:",
                "- Aster honest, Bram liar",
                "- Aster liar, Bram honest",
            ],
        )

    def test_contradiction(self):
        self.assertEqual(
            liars_expression(
                """\
people:
  Aster
  Bram

statements:
  Aster calls Bram a liar
  Bram calls Bram a liar
"""
            ),
            "\n".join(
                [
                    "contradiction",
                    "no possible worlds",
                ]
            ),
        )

    def test_unknown_people_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown target: Bram"):
            parse_liars(
                """\
people:
  Aster

statements:
  Aster calls Bram a liar
"""
            )

    def test_example_files(self):
        cases = {
            "single-claim.goblet-liars": "\n".join(
                [
                    "ambiguous",
                    "possible worlds:",
                    "- Aster honest, Bram honest",
                    "- Aster liar, Bram liar",
                ]
            ),
            "self-snare.goblet-liars": "\n".join(
                [
                    "contradiction",
                    "no possible worlds",
                ]
            ),
            "three-witnesses.goblet-liars": "\n".join(
                [
                    "ambiguous",
                    "possible worlds:",
                    "- Aster honest, Bram liar, Vey liar",
                    "- Aster liar, Bram honest, Vey honest",
                ]
            ),
            "echo-pair.goblet-liars": "\n".join(
                [
                    "ambiguous",
                    "possible worlds:",
                    "- Aster honest, Bram honest",
                    "- Aster liar, Bram liar",
                ]
            ),
            "free-third.goblet-liars": "\n".join(
                [
                    "ambiguous",
                    "possible worlds:",
                    "- Aster honest, Bram liar, Vey honest",
                    "- Aster honest, Bram liar, Vey liar",
                    "- Aster liar, Bram honest, Vey honest",
                    "- Aster liar, Bram honest, Vey liar",
                ]
            ),
            "cross-snare.goblet-liars": "\n".join(
                [
                    "contradiction",
                    "no possible worlds",
                ]
            ),
        }
        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                text = (ROOT / "examples" / filename).read_text(encoding="utf-8")
                self.assertEqual(liars_expression(text), expected)


if __name__ == "__main__":
    unittest.main()
