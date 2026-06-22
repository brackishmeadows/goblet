import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from goblet.labyrinth import (
    Agent,
    TWO,
    current_agent_intention,
    new_labyrinth,
    render_agent_verb,
    resolve_sip,
    run_labyrinth_interactive,
    run_labyrinth_script,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]


class LabyrinthTests(unittest.TestCase):
    def test_demo_script_reaches_exit(self):
        commands = [
            line.strip()
            for line in (ROOT / "examples" / "liars-labyrinth-demo.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

        output = "\n".join(run_labyrinth_script(commands))

        self.assertIn("round one: first room", output)
        self.assertIn("Aster has one turn; intends to move through the brass door", output)
        self.assertIn("Bram has one turn; intends to ask the wax moth about the brass door", output)
        self.assertIn("you slap Aster; Aster's action is stopped", output)
        self.assertIn("you move through the iron door", output)
        self.assertIn("round three: second room", output)
        self.assertIn("the iron rook claims the wax cup is poison.", output)
        self.assertNotIn("acts somewhere else", output)
        self.assertIn("you move through the glass door", output)
        self.assertIn("you escaped the labyrinth", output)

    def test_peril_door_kills_player(self):
        output = "\n".join(run_labyrinth_script(["move through the brass door"]))

        self.assertIn("you move through the brass door", output)
        self.assertIn("the brass door leads to peril; you die", output)
        self.assertIn("condition: health zero", output)
        self.assertIn("you did not survive", output)

    def test_poison_cup_hurts_player(self):
        output = "\n".join(run_labyrinth_script(["sip the bone cup"]))

        self.assertIn("you sip the bone cup", output)
        self.assertIn("the bone cup is poison; you become poisoned", output)
        self.assertIn("poison stirs in you, but does not bite yet", output)
        self.assertIn("condition: health full poisoned", output)

    def test_drink_aliases_to_sip(self):
        output = "\n".join(run_labyrinth_script(["drink the bone cup"]))

        self.assertIn("> drink the bone cup", output)
        self.assertIn("you sip the bone cup", output)
        self.assertIn("the bone cup is poison; you become poisoned", output)

    def test_actions_lists_available_actions_without_advancing(self):
        output = "\n".join(run_labyrinth_script(["actions"]))

        self.assertIn("> actions", output)
        self.assertIn("actions:", output)
        self.assertIn("- ask NAME about THING", output)
        self.assertIn("- tell NAME [to] ACTION", output)
        self.assertIn("- sip CUP (or drink CUP)", output)
        self.assertIn("- recall THING (or remember THING)", output)
        self.assertNotIn("Aster moves through the brass door", output)

    def test_help_aliases_to_actions(self):
        output = "\n".join(run_labyrinth_script(["help"]))

        self.assertIn("> help", output)
        self.assertIn("actions:", output)
        self.assertIn("- move DOOR (or go DOOR)", output)

    def test_non_move_actions_do_not_relist_room(self):
        output = "\n".join(run_labyrinth_script(["actions", "recall moth"]))

        self.assertEqual(output.count("round one: first room"), 1)
        self.assertIn("> actions", output)
        self.assertIn("> recall moth", output)

    def test_go_aliases_to_move(self):
        output = "\n".join(run_labyrinth_script(["go iron"]))

        self.assertIn("> go iron", output)
        self.assertIn("you move through the iron door", output)
        self.assertIn("you press deeper into the labyrinth", output)

    def test_condition_only_lists_player_health(self):
        output = "\n".join(run_labyrinth_script(["sip glass", "go iron", "look"]))

        second_room_start = output.index("round two: second room")
        second_room = output[second_room_start:output.index("> look", second_room_start)]
        condition_line = next(line for line in second_room.splitlines() if line.startswith("condition:"))

        self.assertEqual("condition: health full", condition_line)
        self.assertNotIn("Bram is proud", condition_line)
        self.assertNotIn("Vey is proud", condition_line)

    def test_player_health_renders_as_fraction_when_not_full(self):
        output = "\n".join(run_labyrinth_script(["sip the bone cup", "ask Bram about bone cup"]))

        self.assertIn("condition: health three quarters", output)

    def test_look_agent_reports_condition_word(self):
        output = "\n".join(run_labyrinth_script(["look Aster"]))

        self.assertIn("> look Aster", output)
        self.assertIn("Aster looks proud.", output)
        self.assertNotIn("Aster moves through the brass door", output)

    def test_ask_about_agent_reports_condition_word(self):
        output = "\n".join(run_labyrinth_script(["ask Bram about Aster"]))

        self.assertIn("you ask Bram about Aster", output)
        self.assertIn("Bram claims Aster looks proud.", output)

    def test_ask_about_health_reports_condition_word(self):
        output = "\n".join(run_labyrinth_script(["ask Aster about health"]))

        self.assertIn("you ask Aster about health", output)
        self.assertIn("Aster claims Aster looks proud.", output)

    def test_low_health_agents_act_with_adverb(self):
        agent = Agent("Aven", hp=TWO)

        self.assertEqual("Aven unsteadily moves", render_agent_verb(agent, "move"))

    def test_push_allows_bare_target_and_door(self):
        output = "\n".join(run_labyrinth_script(["push Aster iron"]))

        self.assertIn("> push Aster iron", output)
        self.assertIn("you push Aster toward the iron door", output)

    def test_bare_goblet_question_after_target(self):
        output = "\n".join(run_labyrinth_script(["ask Bram two plus two"]))

        self.assertIn("> ask Bram two plus two", output)
        self.assertIn("you ask Bram what two plus two", output)
        self.assertIn("Bram claims two plus two is four.", output)

    def test_ask_if_world_claim_is_not_goblet_question(self):
        output = "\n".join(run_labyrinth_script(["ask moth if iron door leads to peril"]))

        self.assertIn("> ask moth if iron door leads to peril", output)
        self.assertIn("you ask the wax moth if iron door leads to peril", output)
        self.assertIn("the wax moth claims the iron door leads onward.", output)
        self.assertNotIn("that does not seem like a Goblet question", output)

    def test_ask_if_world_safe_claim_is_not_goblet_question(self):
        output = "\n".join(run_labyrinth_script(["ask moth if iron door is safe"]))

        self.assertIn("> ask moth if iron door is safe", output)
        self.assertIn("you ask the wax moth if iron door is safe", output)
        self.assertIn("the wax moth claims the iron door leads onward.", output)
        self.assertNotIn("expected symbolic comparison expression", output)

    def test_ask_if_it_is_material_resolves_to_addressee(self):
        output = "\n".join(run_labyrinth_script([
            "sip glass",
            "move iron",
            "move silver",
            "ask glass crow if it is glass",
        ]))

        self.assertIn("you ask the glass crow if it is glass", output)
        self.assertIn("the glass crow claims the glass crow is glass.", output)

    def test_ask_if_the_creature_kind_is_material_resolves_alias(self):
        output = "\n".join(run_labyrinth_script([
            "sip glass",
            "move iron",
            "move silver",
            "ask glass crow if the crow is glass",
        ]))

        self.assertIn("you ask the glass crow if the crow is glass", output)
        self.assertIn("the glass crow claims the glass crow is glass.", output)

    def test_truth_cup_uses_player_agreement(self):
        output = "\n".join(run_labyrinth_script(["go iron", "drink iron"]))

        self.assertIn("you sip the iron cup", output)
        self.assertIn("the iron cup sharpens truth; you seem clearer and always tell the truth", output)

    def test_recall_lists_claims_from_or_about_topic(self):
        output = "\n".join(run_labyrinth_script(["recall moth"]))

        self.assertIn("> recall moth", output)
        self.assertIn("you remember these things from or about the wax moth:", output)
        self.assertIn("- the wax moth said: the iron door leads onward; it seemed untested then and is still untested", output)
        self.assertNotIn("Bram asks", output)

    def test_remember_aliases_to_recall(self):
        output = "\n".join(run_labyrinth_script(["remember iron door"]))

        self.assertIn("> remember iron door", output)
        self.assertIn("you remember these things from or about the iron door:", output)
        self.assertIn("the wax moth said: the iron door leads onward; it seemed untested then and is still untested", output)

    def test_recall_cup_includes_direct_drinking_memory(self):
        output = "\n".join(run_labyrinth_script(["drink glass", "recall cup"]))

        self.assertIn("you remember these things from or about cup:", output)
        self.assertIn("- you did: you sip the glass cup", output)
        self.assertIn("- you learned: the glass cup grants haste; you feel quick next round", output)
        self.assertIn("- the wax moth said: the bone cup is poison; it seemed untested then and is still untested", output)
        self.assertNotIn("the wax moth said: the wax moth claims", output)

    def test_recall_marks_claim_that_later_proved_true(self):
        output = "\n".join(run_labyrinth_script(["move iron", "sip wax cup", "recall wax cup"]))

        self.assertIn("you remember these things from or about the wax cup:", output)
        self.assertIn("the iron rook said: the wax cup is poison; it seemed untested then, and later proved true", output)

    def test_recall_marks_claim_that_later_failed(self):
        output = "\n".join(run_labyrinth_script(["move iron", "move silver", "sip salt cup", "recall salt cup"]))

        self.assertIn("you remember these things from or about the salt cup:", output)
        self.assertIn("the glass crow said: the salt cup grants haste; it seemed untested then, but later failed", output)

    def test_recall_specific_cup_includes_empty_memory(self):
        output = "\n".join(run_labyrinth_script([
            "drink glass",
            "drink glass",
            "drink glass",
            "drink glass",
            "drink glass",
            "recall glass cup",
        ]))

        self.assertIn("you remember these things from or about the glass cup:", output)
        self.assertIn("- you learned: the glass cup is empty", output)

    def test_tell_can_instruct_claimant_to_drink(self):
        output = "\n".join(run_labyrinth_script(["tell Bram to drink glass"]))

        self.assertIn("> tell Bram to drink glass", output)
        self.assertIn("you tell Bram to sip the glass cup; Bram considers it", output)
        self.assertIn("Bram sips the glass cup", output)
        self.assertIn("the glass cup grants haste; Bram feels quick next round", output)

    def test_tell_instruction_can_override_default_intention(self):
        output = "\n".join(run_labyrinth_script(["tell Aster to move iron"]))

        self.assertIn("you tell Aster to move through the iron door; Aster considers it", output)
        self.assertIn("Aster moves through the iron door", output)
        self.assertNotIn("the brass door leads to peril; Aster dies", output)

    def test_tell_instruction_to_is_optional(self):
        output = "\n".join(run_labyrinth_script(["tell Aster go iron"]))

        self.assertIn("> tell Aster go iron", output)
        self.assertIn("you tell Aster to move through the iron door; Aster considers it", output)
        self.assertIn("Aster moves through the iron door", output)

    def test_tell_instruction_accepts_go_through(self):
        output = "\n".join(run_labyrinth_script(["tell Aster go through iron"]))

        self.assertIn("you tell Aster to move through the iron door; Aster considers it", output)
        self.assertIn("Aster moves through the iron door", output)

    def test_sleeping_potion_skips_next_round_then_wakes_player(self):
        output = "\n".join(run_labyrinth_script(["move through the iron door", "sip oak cup", "look"]))

        self.assertIn("you sip the oak cup", output)
        self.assertIn("the oak cup is sleeping potion; you fall asleep", output)
        self.assertIn("you sleep through the round", output)
        self.assertIn("you wake", output)
        self.assertIn("round four: second room", output)
        self.assertNotIn("round three: second room", output)
        self.assertNotIn("Bram moves through the silver door", output)

    def test_player_does_not_remember_events_while_asleep(self):
        output = "\n".join(run_labyrinth_script(["move through the iron door", "sip oak cup", "recall wax cup"]))

        self.assertIn("you sleep through the round", output)
        self.assertNotIn("Bram asks Vey about the wax cup", output)
        self.assertNotIn("Vey said: Vey claims they are testing whether the wax cup is poison.", output)

    def test_agents_do_not_choose_sleeping_witnesses_for_questions(self):
        state = new_labyrinth()
        aster = state.claimants["Aster"]
        bram = state.claimants["Bram"]
        vey = state.claimants["Vey"]

        resolve_sip(state, bram, "GlassCup")
        bram.sleeping = True
        state.rooms[0].intentions[aster.name] = "ask Bram about BoneCup"

        intention = current_agent_intention(state, aster)

        self.assertNotEqual("ask Bram about BoneCup", intention)
        self.assertIsNotNone(intention)
        self.assertTrue(bram.sleeping)
        self.assertFalse(vey.sleeping)

    def test_claimants_can_be_elsewhere_and_animals_stay_put(self):
        output = "\n".join(run_labyrinth_script(["slap Aster", "move through the iron door", "tell IronRook hello"]))

        self.assertIn("round three: second room", output)
        self.assertIn("- the iron rook", output)
        self.assertIn("the iron rook claims the wax cup is poison.", output)
        self.assertNotIn("acts somewhere else", output)

    def test_interactive_mode_accepts_quit(self):
        outputs = []
        inputs = iter(["quit"])

        run_labyrinth_interactive(input_func=lambda _prompt: next(inputs), print_func=outputs.append)

        joined = "\n".join(outputs)
        self.assertIn("Liar's Labyrinth", joined)
        self.assertIn("round one: first room", joined)
        self.assertIn("you leave the labyrinth unresolved", joined)

    def test_random_labyrinth_uses_seeded_generation(self):
        first = "\n".join(run_labyrinth_script(["look"], random_seed="salt"))
        second = "\n".join(run_labyrinth_script(["look"], random_seed="salt"))

        self.assertEqual(first, second)
        self.assertIn("round one:", first)


if __name__ == "__main__":
    unittest.main()
