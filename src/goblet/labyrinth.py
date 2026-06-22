from __future__ import annotations
from dataclasses import dataclass, field
import pickle
import random
import re
from typing import Any, Iterator

from .compare import compare
from .divide import divide_expression
from .increment import increment
from .liars import enumerate_worlds, parse_liars, render_world, surviving_worlds
from .multiply import multiply_expression
from .prime import prime_expression
from .relation import relation_expression
from .render import render_fraction, render_number
from .subtract import subtract
from .words import ONE, ZERO, WordNumber, is_zero


@dataclass(frozen=True)
class LieRate:
    lies: WordNumber
    out_of: WordNumber


@dataclass(frozen=True)
class ClaimCard:
    truth: str
    lie: str


@dataclass
class MemoryEntry:
    id: str
    turn: str
    phase: str
    observer: str
    kind: str
    text: str
    source: str | None = None
    subject: str | None = None
    proposition: str | None = None
    certainty: str = "heard"
    sequence: int = 0
    subjects: list[str] = field(default_factory=list)
    initial_rating: str = ""
    initial_reason: str = ""
    current_rating: str = ""
    outcome_turn: str | None = None
    outcome_reason: str = ""


@dataclass
class AgentMemory:
    entries: list[MemoryEntry] = field(default_factory=list)
    by_subject: dict[str, list[str]] = field(default_factory=dict)
    known_propositions: set[str] = field(default_factory=set)
    trust: dict[str, str] = field(default_factory=dict)
    trust_evidence: dict[str, list[str]] = field(default_factory=dict)
    social_weight: dict[str, int] = field(default_factory=dict)
    social_evidence: dict[str, list[str]] = field(default_factory=dict)

    def remember(self, entry: MemoryEntry) -> None:
        self.entries.append(entry)
        for subject in entry.subjects:
            self.by_subject.setdefault(subject, []).append(entry.id)

    def entries_about(self, subject: str) -> list[MemoryEntry]:
        ids = set(self.by_subject.get(subject, []))
        return [entry for entry in self.entries if entry.id in ids]


@dataclass
class Hypothesis:
    id: str
    subject: str
    proposition: str
    source: str | None
    status: str = "active"
    certainty: str = "weakly inferred"
    created_turn: str = "zero"
    evidence_ids: list[str] = field(default_factory=list)
    test_action: str | None = None
    reason: str = ""


@dataclass
class Goal:
    id: str
    action: str
    subject: str
    reason: str
    hypothesis_id: str | None = None
    status: str = "active"
    created_turn: str = "zero"


@dataclass
class Agent:
    name: str
    hp: WordNumber = field(default_factory=lambda: FOUR)
    max_hp: WordNumber = field(default_factory=lambda: FOUR)
    speed: WordNumber = field(default_factory=lambda: ONE)
    lie_rate: LieRate = field(default_factory=lambda: LieRate(TWO, FOUR))
    truth_rate: str = "mixed"
    belief_rate: str = "mixed"
    room_index: int = 0
    stationary: bool = False
    animal: bool = False
    alive: bool = True
    sleeping: bool = False
    sleep_turns_remaining: WordNumber = field(default_factory=lambda: ZERO)
    truth_bound: bool = False
    fixed_question_count: WordNumber = field(default_factory=lambda: ZERO)
    fixed_question_limit: WordNumber = field(default_factory=lambda: TWO)
    fixed_sleep_duration: WordNumber = field(default_factory=lambda: ONE)
    poisoned: bool = False
    poison_grace: bool = False
    poison_bites: WordNumber = field(default_factory=lambda: ZERO)
    poison_runs_course: bool = True
    observances: list[str] = field(default_factory=list)
    claims: list[ClaimCard] = field(default_factory=list)
    claim_truth_cycle: list[str] = field(default_factory=list)
    tried_actions: set[str] = field(default_factory=set)
    memory: AgentMemory = field(default_factory=AgentMemory)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    goals: list[Goal] = field(default_factory=list)
    push_resistance_cycle: list[str] = field(default_factory=list)
    push_resistance_hp: str = ""


@dataclass
class Door:
    name: str
    result: str


@dataclass
class Cup:
    name: str
    fifths: WordNumber
    effect: str


@dataclass
class Room:
    name: str
    doors: dict[str, Door]
    cups: dict[str, Cup]
    intentions: dict[str, str]


@dataclass
class LabyrinthState:
    room_index: int
    rooms: list[Room]
    player: Agent
    claimants: dict[str, Agent]
    round_number: WordNumber = field(default_factory=lambda: ONE)
    round_claims: dict[str, str] = field(default_factory=dict)
    player_turn_budget: WordNumber = field(default_factory=lambda: ONE)
    player_turns_taken: WordNumber = field(default_factory=lambda: ZERO)
    slapped_this_round: str | None = None
    player_changed_room_this_turn: bool = False
    memory_sequence: int = 0
    hypothesis_sequence: int = 0
    goal_sequence: int = 0
    recorded_round_memory: set[str] = field(default_factory=set)
    sleep_tick_suppressed: set[str] = field(default_factory=set)
    escaped: bool = False


@dataclass
class CommandOutcome:
    lines: list[str]
    advances: bool = True


@dataclass
class LabyrinthPostSession:
    state: LabyrinthState
    should_render_room: bool = True
    random_seed: str | None = None
    resigned: bool = False


@dataclass(frozen=True)
class TellClaim:
    target: Agent
    message: str
    subject: str | None
    proposition: str | None


@dataclass(frozen=True)
class TellInstruction:
    target: Agent
    message: str
    action: str


@dataclass(frozen=True)
class GobletAsk:
    target: Agent
    mode: str
    expression: str


@dataclass(frozen=True)
class LiarsAsk:
    target: Agent
    raw_text: str
    puzzle_text: str


@dataclass(frozen=True)
class AssessmentAsk:
    target: Agent
    raw_subject: str
    subject: str


@dataclass(frozen=True)
class AssessmentEvidence:
    source: str
    proposition: str
    entry_id: str
    kind: str
    certainty: str
    initial_rating: str = ""
    current_rating: str = ""


@dataclass(frozen=True)
class AssessmentScore:
    proposition: str
    weight: int


@dataclass(frozen=True)
class AssessmentSourceWeight:
    source: str
    weight: int
    label: str


@dataclass(frozen=True)
class AssessmentReport:
    subject: str
    evidence: tuple[AssessmentEvidence, ...]
    likely: str | None
    alternatives: tuple[str, ...]
    supporters: tuple[str, ...]
    opponents: tuple[str, ...]
    direct_evidence: tuple[str, ...]
    scores: tuple[AssessmentScore, ...]
    source_weights: tuple[AssessmentSourceWeight, ...]


@dataclass(frozen=True)
class WorldAsk:
    target: Agent
    expression: str
    subject: str
    proposition: str


TWO = WordNumber("zero", "zero", "two")
THREE = WordNumber("zero", "zero", "three")
FOUR = WordNumber("zero", "zero", "four")
FIVE = WordNumber("zero", "zero", "five")

TRUTH = "truth"
LIE = "lie"

CLAIM_ASSESSMENT_PREFIX = "__claim__:"
WITNESSES_ASSESSMENT_SUBJECT = "__witnesses__"


def lie_rate_fraction(lies: WordNumber) -> LieRate:
    return LieRate(lies, FOUR)


def claim_card(truth: str, lie: str | None = None) -> ClaimCard:
    return ClaimCard(truth=truth, lie=lie or truth)


def increment_count(value: WordNumber) -> WordNumber:
    result = increment(value)
    if not isinstance(result, WordNumber):
        raise ValueError("labyrinth count grew beyond the supported room scale")
    return result


def decrement_count(value: WordNumber) -> WordNumber:
    return subtract(value, ONE)


def count_greater_than(left: WordNumber, right: WordNumber) -> bool:
    return compare(left, right) == "greater"


def count_at_least(left: WordNumber, right: WordNumber) -> bool:
    return compare(left, right) != "less"


def render_cup_fullness(value: WordNumber) -> str:
    if is_zero(value):
        return "empty"
    if value == ONE:
        return "nearly empty"
    if value == TWO:
        return "half empty"
    if value == THREE:
        return "half full"
    if value == FOUR:
        return "mostly full"
    if count_at_least(value, FIVE):
        return "very full"
    return "strangely full"


def count_up_to(value: WordNumber) -> Iterator[WordNumber]:
    remaining = value
    current = ONE
    while not is_zero(remaining):
        yield current
        remaining = decrement_count(remaining)
        current = increment_count(current)


def run_labyrinth_script(commands: list[str], random_seed: str | int | None = None) -> list[str]:
    state = new_random_labyrinth(random_seed) if random_seed is not None else new_labyrinth()
    lines: list[str] = []
    command_index = 0
    should_render_room = True
    while command_index < len(commands):
        if state.escaped or not state.player.alive:
            break
        if state.player.sleeping:
            if should_run_agent_phase(state):
                resolve_agent_phase(state)
            resolve_poison_ticks(state)
            lines.extend(resolve_sleep_phase(state, state.player))
            if state.player.alive and not state.escaped:
                advance_round(state)
            lines.append("")
            continue
        if should_render_room:
            lines.extend(render_turn(state))
            should_render_room = False
        command = commands[command_index]
        command_index += 1
        lines.append(f"> {command}")
        if command.strip() in ("quit", "exit"):
            lines.append("you leave the labyrinth unresolved")
            return lines
        if command.strip() == "look":
            lines.extend(render_turn(state))
            lines.append("")
            continue
        outcome = resolve_turn_checked(state, command)
        lines.extend(outcome.lines)
        if outcome.advances:
            finish_player_action(state)
            changed_room = state.player_changed_room_this_turn
            if should_end_player_phase(state):
                if state.player.sleeping:
                    if should_run_agent_phase(state):
                        resolve_agent_phase(state)
                    resolve_poison_ticks(state)
                elif should_run_agent_phase(state):
                    lines.extend(resolve_agent_phase(state))
                    lines.extend(resolve_poison_ticks(state))
                else:
                    lines.extend(resolve_poison_ticks(state))
                if state.player.alive and not state.escaped:
                    advance_round(state)
            if changed_room and state.player.alive and not state.escaped:
                lines.extend(render_turn(state))
                should_render_room = False
        lines.append("")
    lines.extend(render_ending(state))
    return lines


def run_labyrinth_interactive(input_func=input, print_func=print, random_seed: str | int | None = None) -> None:
    state = new_random_labyrinth(random_seed) if random_seed is not None else new_labyrinth()
    write = lambda line="": print_func(colorize_interactive_line(line))
    write("Liar's Labyrinth")
    write("commands: ask, tell, sip, move, push, slap, look, recall, help, quit")
    write("")
    should_render_room = True
    while state.player.alive and not state.escaped:
        if state.player.sleeping:
            if should_run_agent_phase(state):
                resolve_agent_phase(state)
            resolve_poison_ticks(state)
            for line in resolve_sleep_phase(state, state.player):
                write(line)
            if state.player.alive and not state.escaped:
                advance_round(state)
            write("")
            continue
        if should_render_room:
            for line in render_turn(state):
                write(line)
            should_render_room = False
        command = input_func(colorize_prompt("> ")).strip()
        if command in ("quit", "exit"):
            write("you leave the labyrinth unresolved")
            return
        if command == "look":
            for line in render_turn(state):
                write(line)
            write("")
            continue
        outcome = resolve_turn_checked(state, command)
        for line in outcome.lines:
            write(line)
        if outcome.advances:
            finish_player_action(state)
            changed_room = state.player_changed_room_this_turn
            if should_end_player_phase(state):
                if state.player.sleeping:
                    if should_run_agent_phase(state):
                        resolve_agent_phase(state)
                    resolve_poison_ticks(state)
                elif should_run_agent_phase(state):
                    for line in resolve_agent_phase(state):
                        write(line)
                    for line in resolve_poison_ticks(state):
                        write(line)
                else:
                    for line in resolve_poison_ticks(state):
                        write(line)
                if state.player.alive and not state.escaped:
                    advance_round(state)
            if changed_room and state.player.alive and not state.escaped:
                for line in render_turn(state):
                    write(line)
                should_render_room = False
        write("")
    for line in render_ending(state):
        write(line)


def new_labyrinth_post_session(random_seed: str | int | None = None) -> LabyrinthPostSession:
    seed = None if random_seed is None else str(random_seed)
    state = new_random_labyrinth(seed) if seed is not None else new_labyrinth()
    return LabyrinthPostSession(state=state, random_seed=seed)


def save_labyrinth_post_session(path: str, session: LabyrinthPostSession) -> None:
    with open(path, "wb") as handle:
        pickle.dump(session, handle)


def load_labyrinth_post_session(path: str) -> LabyrinthPostSession:
    with open(path, "rb") as handle:
        session = pickle.load(handle)
    if not isinstance(session, LabyrinthPostSession):
        raise ValueError("not a labyrinth post session file")
    return session


def start_labyrinth_post(path: str, random_seed: str | int | None = None) -> list[str]:
    session = new_labyrinth_post_session(random_seed)
    lines: list[str] = []
    if session.random_seed is not None:
        lines.append(f"random seed: {session.random_seed}")
    lines.append("Liar's Labyrinth")
    lines.append(f"play-by-post state: {path}")
    lines.append("commands: python -m goblet --labyrinth-post STATE COMMAND")
    lines.append("")
    lines.extend(step_labyrinth_post_session(session, None))
    save_labyrinth_post_session(path, session)
    append_labyrinth_post_log(path, lines, mode="w")
    return lines


def show_labyrinth_post(path: str) -> list[str]:
    session = load_labyrinth_post_session(path)
    return render_labyrinth_post_session(session)


def render_labyrinth_post_session(session: LabyrinthPostSession) -> list[str]:
    state = session.state
    if session.resigned:
        return ["you have already left the labyrinth unresolved"]
    if state.escaped or not state.player.alive:
        return render_ending(state)
    return render_turn(state)


def step_labyrinth_post(path: str, command: str) -> list[str]:
    session = load_labyrinth_post_session(path)
    lines = step_labyrinth_post_session(session, command)
    save_labyrinth_post_session(path, session)
    append_labyrinth_post_log(path, lines)
    return lines


def append_labyrinth_post_log(path: str, lines: list[str], mode: str = "a") -> None:
    log_path = path + ".log"
    with open(log_path, mode, encoding="utf-8") as handle:
        for line in lines:
            handle.write(line + "\n")
        handle.write("\n")


def step_labyrinth_post_session(session: LabyrinthPostSession, command: str | None) -> list[str]:
    state = session.state
    lines: list[str] = []

    if session.resigned:
        return ["you have already left the labyrinth unresolved"]

    lines.extend(resolve_post_sleep_until_ready(state))

    if state.escaped or not state.player.alive:
        session.should_render_room = False
        lines.extend(render_ending(state))
        return lines

    if session.should_render_room:
        lines.extend(render_turn(state))
        session.should_render_room = False

    if command is None or not command.strip():
        return lines

    command = command.strip()
    lines.append(f"> {command}")
    if command in ("quit", "exit"):
        session.resigned = True
        lines.append("you leave the labyrinth unresolved")
        return lines

    if command == "look":
        lines.extend(render_turn(state))
        return lines

    outcome = resolve_turn_checked(state, command)
    lines.extend(outcome.lines)
    if outcome.advances:
        finish_player_action(state)
        changed_room = state.player_changed_room_this_turn
        if should_end_player_phase(state):
            if state.player.sleeping:
                if should_run_agent_phase(state):
                    resolve_agent_phase(state)
                resolve_poison_ticks(state)
            elif should_run_agent_phase(state):
                lines.extend(resolve_agent_phase(state))
                lines.extend(resolve_poison_ticks(state))
            else:
                lines.extend(resolve_poison_ticks(state))
            if state.player.alive and not state.escaped:
                advance_round(state)
        if changed_room and state.player.alive and not state.escaped:
            lines.extend(render_turn(state))
            session.should_render_room = False

    if state.escaped or not state.player.alive:
        session.should_render_room = False
        lines.extend(render_ending(state))
    return lines


def resolve_post_sleep_until_ready(state: LabyrinthState) -> list[str]:
    lines: list[str] = []
    guard = 0
    while state.player.alive and not state.escaped and state.player.sleeping:
        guard += 1
        if guard > 10:
            lines.append("sleep folds strangely and refuses to end")
            break
        if should_run_agent_phase(state):
            resolve_agent_phase(state)
        resolve_poison_ticks(state)
        lines.extend(resolve_sleep_phase(state, state.player))
        if state.player.alive and not state.escaped:
            advance_round(state)
    return lines



PLAYER_COLOR = "\033[96m"
RESET_COLOR = "\033[0m"


def colorize_prompt(prompt: str) -> str:
    return f"{PLAYER_COLOR}{prompt}{RESET_COLOR}"


def colorize_interactive_line(line: str) -> str:
    if is_player_line(line):
        return f"{PLAYER_COLOR}{line}{RESET_COLOR}"
    return line


def is_player_line(line: str) -> bool:
    return (
        line.startswith("you ")
        or line.startswith("your ")
        or line.startswith("> ")
        or line.startswith("condition: ")
    )


def new_labyrinth() -> LabyrinthState:
    rooms = [
        Room(
            name="first room",
            doors={
                "BrassDoor": Door("BrassDoor", "peril"),
                "IronDoor": Door("IronDoor", "next"),
            },
            cups={
                "BoneCup": Cup("BoneCup", FIVE, "poison"),
                "GlassCup": Cup("GlassCup", FIVE, "haste"),
            },
            intentions={
                "Aster": "move BrassDoor",
                "Bram": "sip GlassCup",
                "Vey": "ask Bram about BoneCup",
            },
        ),
        Room(
            name="second room",
            doors={
                "SilverDoor": Door("SilverDoor", "next"),
                "BoneDoor": Door("BoneDoor", "peril"),
            },
            cups={
                "IronCup": Cup("IronCup", FIVE, "truth"),
                "WaxCup": Cup("WaxCup", FIVE, "venom"),
                "OakCup": Cup("OakCup", FIVE, "sleep"),
            },
            intentions={
                "Aster": "move BoneDoor",
                "Bram": "sip IronCup",
                "Vey": "move SilverDoor",
            },
        ),
        Room(
            name="third room",
            doors={
                "GlassDoor": Door("GlassDoor", "exit"),
                "CopperDoor": Door("CopperDoor", "peril"),
            },
            cups={
                "PewterCup": Cup("PewterCup", FIVE, "antidote"),
                "SaltCup": Cup("SaltCup", FIVE, "stupor"),
                "GoldCup": Cup("GoldCup", FIVE, "elixir"),
            },
            intentions={
                "Aster": "move CopperDoor",
                "Bram": "move GlassDoor",
                "Vey": "sip PewterCup",
            },
        ),
    ]
    claimants = {
        "Aster": Agent(
            "Aster",
            lie_rate=lie_rate_fraction(THREE),
            truth_rate="low",
            belief_rate="high",
            claims=[
                claim_card(
                    "Aster claims the brass door leads to peril.",
                    "Aster claims the brass door is safe.",
                ),
                claim_card(
                    "Aster claims Bram wants the glass cup.",
                    "Aster claims Bram fears the glass cup.",
                ),
                claim_card(
                    "Aster claims the bone door leads to peril.",
                    "Aster claims the bone door is safe.",
                ),
                claim_card(
                    "Aster claims the copper door leads to peril.",
                    "Aster claims the copper door is safe.",
                ),
            ],
        ),
        "Bram": Agent(
            "Bram",
            lie_rate=lie_rate_fraction(ZERO),
            truth_rate="high",
            belief_rate="medium",
            claims=[
                claim_card(
                    "Bram claims the bone cup is poison.",
                    "Bram claims the bone cup is safe.",
                ),
                claim_card(
                    "Bram claims the glass cup grants haste.",
                    "Bram claims the glass cup is poison.",
                ),
                claim_card(
                    "Bram claims the iron cup sharpens truth.",
                    "Bram claims the iron cup dulls truth.",
                ),
                claim_card(
                    "Bram claims the glass door is the exit.",
                    "Bram claims the glass door leads to peril.",
                ),
            ],
        ),
        "Vey": Agent(
            "Vey",
            lie_rate=lie_rate_fraction(ONE),
            truth_rate="mixed",
            belief_rate="low",
            claims=[
                claim_card(
                    "Vey claims Aster often lies.",
                    "Vey claims Aster is a liar.",
                ),
                claim_card(
                    "Vey claims Bram is useful but reckless.",
                    "Vey claims Bram is useless and cautious.",
                ),
                claim_card(
                    "Vey claims the silver door advances.",
                    "Vey claims the silver door leads to peril.",
                ),
                claim_card(
                    "Vey claims the pewter cup is antidote.",
                    "Vey claims the pewter cup is poison.",
                ),
            ],
        ),
        "WaxMoth": Agent(
            "WaxMoth",
            lie_rate=lie_rate_fraction(ZERO),
            truth_rate="high",
            belief_rate="low",
            stationary=True,
            animal=True,
            fixed_question_limit=TWO,
            fixed_sleep_duration=ONE,
            claims=[
                claim_card(
                    "the wax moth claims the iron door leads onward.",
                    "the wax moth claims the iron door leads to peril.",
                ),
                claim_card(
                    "the wax moth claims the bone cup is poison.",
                    "the wax moth claims the bone cup is safe.",
                ),
            ],
        ),
        "IronRook": Agent(
            "IronRook",
            lie_rate=lie_rate_fraction(TWO),
            truth_rate="mixed",
            belief_rate="low",
            room_index=1,
            stationary=True,
            animal=True,
            fixed_question_limit=ONE,
            fixed_sleep_duration=TWO,
            claims=[
                claim_card(
                    "the iron rook claims the wax cup is poison.",
                    "the iron rook claims the wax cup is antidote.",
                ),
                claim_card(
                    "the iron rook claims Aster passed this way in a dream.",
                    "the iron rook claims Aster never dreamed of this room.",
                ),
            ],
        ),
        "GlassCrow": Agent(
            "GlassCrow",
            lie_rate=lie_rate_fraction(THREE),
            truth_rate="low",
            belief_rate="low",
            room_index=2,
            stationary=True,
            animal=True,
            fixed_question_limit=TWO,
            fixed_sleep_duration=TWO,
            claims=[
                claim_card(
                    "the glass crow claims the salt cup slows the drinker.",
                    "the glass crow claims the salt cup grants haste.",
                ),
                claim_card(
                    "the glass crow claims the gold cup is elixir.",
                    "the glass crow claims the gold cup is poison.",
                ),
                claim_card(
                    "the glass crow claims the copper door is hungry.",
                    "the glass crow claims the copper door is kind.",
                ),
            ],
        ),
    }
    state = LabyrinthState(
        room_index=0,
        rooms=rooms,
        player=Agent("You", lie_rate=lie_rate_fraction(ZERO), truth_rate="player", belief_rate="player"),
        claimants=claimants,
    )
    begin_player_round(state)
    prepare_round_claims(state)
    record_round_observations(state)
    return state


PERSON_A_NAMES = ["Aster", "Ash", "Aven", "Alder"]
PERSON_B_NAMES = ["Bram", "Briar", "Bex", "Brindle"]
PERSON_THIRD_NAMES = ["Vey", "Cato", "Della", "Edda", "Fenn", "Iris", "Jory", "Mira", "Nox", "Sable"]
BEAST_NAMES = ["WaxMoth", "IronRook", "GlassCrow", "SaltHare", "BoneFinch", "CopperToad", "PewterWasp", "FlintMarten", "OakEel"]
DOOR_MATERIALS = ["Brass", "Iron", "Bone", "Silver", "Glass", "Copper", "Oak", "Pewter", "Flint", "Salt", "Gold", "Wax"]
CUP_MATERIALS = ["Bone", "Glass", "Iron", "Wax", "Pewter", "Salt", "Gold", "Copper", "Oak", "Flint", "Silver", "Brass"]
ROOM_ADJECTIVES = ["first", "red", "hollow", "tilted", "low", "blue", "ashen", "quiet", "crooked"]
ROOM_NOUNS = ["room", "hall", "cellar", "gallery", "kitchen", "chapel", "parlor", "vault"]
LIE_COUNTS = [ZERO, ONE, TWO, THREE, FOUR]
BELIEF_RATES = ["low", "medium", "high"]
TRUTH_RATES = ["low", "mixed", "high"]


def new_random_labyrinth(seed: str | int | None = None) -> LabyrinthState:
    rng = random.Random(seed)
    extra_travelers = rng.sample(PERSON_THIRD_NAMES, 4)
    traveler_names = [
        rng.choice(PERSON_A_NAMES),
        rng.choice(PERSON_B_NAMES),
        *extra_travelers,
    ]
    # Random courses work better when the first room is socially crowded, but
    # later rooms already have people to meet. The first two names remain A/B
    # coded; two extra travellers start with the player; the remaining two form
    # little forward parties in rooms two and three.
    traveler_start_rooms = {
        name: (0 if index < 4 else min(index - 3, 2))
        for index, name in enumerate(traveler_names)
    }
    beast_names = rng.sample(BEAST_NAMES, 3)
    rooms = random_rooms(rng)
    claimants: dict[str, Agent] = {}

    for index, name in enumerate(traveler_names):
        start_room = traveler_start_rooms[name]
        claimants[name] = Agent(
            name,
            lie_rate=lie_rate_fraction(rng.choice(LIE_COUNTS)),
            truth_rate=rng.choice(TRUTH_RATES),
            belief_rate=rng.choice(BELIEF_RATES),
            room_index=start_room,
            claims=random_claim_cards_for_agent(rng, name, rooms, traveler_names, preferred_room_index=start_room),
        )

    for index, name in enumerate(beast_names):
        claimants[name] = Agent(
            name,
            lie_rate=lie_rate_fraction(rng.choice(LIE_COUNTS)),
            truth_rate=rng.choice(TRUTH_RATES),
            belief_rate="low",
            room_index=index,
            stationary=True,
            animal=True,
            fixed_question_limit=rng.choice([ONE, TWO]),
            fixed_sleep_duration=rng.choice([ONE, TWO]),
            claims=random_claim_cards_for_agent(rng, name, rooms, traveler_names, preferred_room_index=index),
        )

    for room_index, room in enumerate(rooms):
        room.intentions = random_room_intentions(rng, room, room_index, traveler_names, beast_names)

    state = LabyrinthState(
        room_index=0,
        rooms=rooms,
        player=Agent("You", lie_rate=lie_rate_fraction(ZERO), truth_rate="player", belief_rate="player"),
        claimants=claimants,
    )
    begin_player_round(state)
    prepare_round_claims(state)
    record_round_observations(state)
    return state


def random_rooms(rng: random.Random) -> list[Room]:
    door_materials = rng.sample(DOOR_MATERIALS, 6)
    cup_materials = rng.sample(CUP_MATERIALS, 8)
    room_names = random_room_names(rng, 3)
    course_results = [("next", "peril"), ("next", "peril"), ("exit", "peril")]
    cup_effect_sets = [
        ["poison", "haste"],
        ["venom", "truth", "sleep"],
        ["antidote", "stupor", "elixir"],
    ]
    rooms: list[Room] = []
    door_index = 0
    cup_index = 0
    for room_index, (good_result, bad_result) in enumerate(course_results):
        good_door = f"{door_materials[door_index]}Door"
        bad_door = f"{door_materials[door_index + 1]}Door"
        door_index += 2
        door_pairs = [(good_door, good_result), (bad_door, bad_result)]
        rng.shuffle(door_pairs)
        doors = {name: Door(name, result) for name, result in door_pairs}

        effects = cup_effect_sets[room_index][:]
        rng.shuffle(effects)
        cups: dict[str, Cup] = {}
        for effect in effects:
            name = f"{cup_materials[cup_index]}Cup"
            cup_index += 1
            cups[name] = Cup(name, FIVE, effect)
        rooms.append(Room(name=room_names[room_index], doors=doors, cups=cups, intentions={}))
    return rooms


def random_room_names(rng: random.Random, count: int) -> list[str]:
    names: list[str] = []
    while len(names) < count:
        candidate = f"{rng.choice(ROOM_ADJECTIVES)} {rng.choice(ROOM_NOUNS)}"
        if candidate not in names:
            names.append(candidate)
    return names


def random_room_intentions(
    rng: random.Random,
    room: Room,
    room_index: int,
    traveler_names: list[str],
    beast_names: list[str],
) -> dict[str, str]:
    intentions: dict[str, str] = {}
    witness = beast_names[room_index]
    subjects = list(room.doors) + list(room.cups)
    for traveler in traveler_names:
        style = rng.choice(["ask", "sip", "move"])
        if style == "ask":
            intentions[traveler] = f"ask {witness} about {rng.choice(subjects)}"
        elif style == "sip" and room.cups:
            intentions[traveler] = f"sip {rng.choice(list(room.cups))}"
        else:
            intentions[traveler] = f"move {rng.choice(list(room.doors))}"
    return intentions


def random_claim_cards_for_agent(
    rng: random.Random,
    agent_name: str,
    rooms: list[Room],
    traveler_names: list[str],
    preferred_room_index: int | None = None,
) -> list[ClaimCard]:
    cards: list[ClaimCard] = []
    world_cards: list[ClaimCard] = []
    preferred_cards: list[ClaimCard] = []
    for index, room in enumerate(rooms):
        room_cards: list[ClaimCard] = []
        for door in room.doors.values():
            room_cards.append(door_claim_card(agent_name, door))
        for cup in room.cups.values():
            room_cards.append(cup_claim_card(agent_name, cup))
        if preferred_room_index is not None and index == preferred_room_index:
            preferred_cards.extend(room_cards)
        else:
            world_cards.extend(room_cards)
    rng.shuffle(preferred_cards)
    rng.shuffle(world_cards)
    preferred_count = 4 if agent_name in BEAST_NAMES else 3
    cards.extend(preferred_cards[:preferred_count])
    cards.extend(world_cards[: max(0, 5 - len(cards))])

    others = [name for name in traveler_names if name != agent_name]
    if others:
        other = rng.choice(others)
        cards.append(claim_card(
            f"{render_agent_name(agent_name)} claims {other} is worth watching.",
            f"{render_agent_name(agent_name)} claims {other} is harmless.",
        ))
    return cards


def render_agent_name(name: str) -> str:
    if name in {"WaxMoth", "IronRook", "GlassCrow", "SaltHare", "BoneFinch", "CopperToad", "PewterWasp", "FlintMarten", "OakEel"}:
        return render_name(name)
    return name


def door_claim_card(speaker: str, door: Door) -> ClaimCard:
    rendered = render_name(door.name)
    prefix = render_agent_name(speaker)
    if door.result == "peril":
        return claim_card(
            f"{prefix} claims {rendered} leads to peril.",
            f"{prefix} claims {rendered} is safe.",
        )
    if door.result == "exit":
        return claim_card(
            f"{prefix} claims {rendered} is the exit.",
            f"{prefix} claims {rendered} leads to peril.",
        )
    return claim_card(
        f"{prefix} claims {rendered} leads onward.",
        f"{prefix} claims {rendered} leads to peril.",
    )


def cup_claim_card(speaker: str, cup: Cup) -> ClaimCard:
    rendered = render_name(cup.name)
    prefix = render_agent_name(speaker)
    if cup.effect in ("poison", "venom"):
        return claim_card(
            f"{prefix} claims {rendered} is poison.",
            f"{prefix} claims {rendered} is safe.",
        )
    if cup.effect == "haste":
        return claim_card(
            f"{prefix} claims {rendered} grants haste.",
            f"{prefix} claims {rendered} is poison.",
        )
    if cup.effect == "truth":
        return claim_card(
            f"{prefix} claims {rendered} sharpens truth.",
            f"{prefix} claims {rendered} dulls truth.",
        )
    if cup.effect == "stupor":
        return claim_card(
            f"{prefix} claims {rendered} slows the drinker.",
            f"{prefix} claims {rendered} grants haste.",
        )
    if cup.effect == "sleep":
        return claim_card(
            f"{prefix} claims {rendered} is sleeping potion.",
            f"{prefix} claims {rendered} grants haste.",
        )
    if cup.effect == "antidote":
        return claim_card(
            f"{prefix} claims {rendered} is antidote.",
            f"{prefix} claims {rendered} is poison.",
        )
    if cup.effect == "elixir":
        return claim_card(
            f"{prefix} claims {rendered} is elixir.",
            f"{prefix} claims {rendered} is poison.",
        )
    return claim_card(
        f"{prefix} claims {rendered} is strange.",
        f"{prefix} claims {rendered} is ordinary.",
    )


def render_turn(state: LabyrinthState) -> list[str]:
    room = current_room(state)
    lines = [f"round {render_number(state.round_number)}: {room.name}"]
    lines.append(render_hp(state))
    if count_greater_than(state.player_turn_budget, ONE):
        lines.append(render_player_turns(state))
    lines.append("present:")
    lines.extend(f"- {render_agent(agent)}" for agent in present_agents(state))
    prepare_round_claims(state)
    lines.append("claims:")
    for agent in present_agents(state):
        lines.append(f"- {round_claim(state, agent)}")
    lines.append("cups:")
    for cup in room.cups.values():
        lines.append(f"- {render_name(cup.name)}: {render_cup_fullness(cup.fifths)}")
    lines.append("doors:")
    lines.extend(f"- {render_name(door.name)}" for door in room.doors.values())
    lines.append("intentions:")
    for name in room.intentions.keys():
        agent = state.claimants[name]
        if agent.alive and agent.room_index == state.room_index:
            intention = current_agent_intention(state, agent)
            turn_count = render_turn_count(agent.speed)
            if intention is None:
                lines.append(f"- {name} has {turn_count}; has no clear intention")
            else:
                lines.append(f"- {name} has {turn_count}; intends to {render_action(intention)}")
    return lines


def resolve_turn_checked(state: LabyrinthState, command: str) -> CommandOutcome:
    command = command.strip()
    if not command:
        return CommandOutcome(["say what?"], advances=False)
    command = normalize_player_command(command)
    if command in ("actions", "help"):
        return CommandOutcome(render_help(state), advances=False)
    if command.startswith("help "):
        return CommandOutcome(resolve_help(state, command), advances=False)
    if command.startswith("look "):
        return CommandOutcome(resolve_look(state, command), advances=False)
    if command.startswith("recall ") or command.startswith("remember "):
        return CommandOutcome(resolve_recall(state, command), advances=False)

    command = normalize_bare_agent_instruction(state, command)
    validation_error = validate_player_command(state, command)
    if validation_error:
        return CommandOutcome([validation_error], advances=False)

    return CommandOutcome(resolve_turn(state, command), advances=True)


def normalize_bare_agent_instruction(state: LabyrinthState, command: str) -> str:
    words = command.split()
    if len(words) < 2:
        return command
    if words[0] in {"ask", "tell", "sip", "move", "push", "slap", "look", "recall", "remember", "help"}:
        return command

    for length in range(min(3, len(words) - 1), 0, -1):
        possible_agent = " ".join(words[:length])
        agent, _ = resolve_agent_name(state, possible_agent)
        if agent is None or not agent.alive or agent.room_index != state.room_index:
            continue
        instruction = " ".join(words[length:]).strip()
        if tell_instruction_text(instruction) is not None:
            return f"tell {agent.name} {instruction}"
    return command


def normalize_player_command(command: str) -> str:
    if command == "go":
        return "move"
    if command.startswith("go "):
        return "move " + command.removeprefix("go ").strip()
    if command == "drink":
        return "sip"
    if command.startswith("drink "):
        return "sip " + command.removeprefix("drink ").strip()
    return command


def example_agent(state: LabyrinthState) -> str:
    agents = present_agents(state)
    return render_agent(agents[0]) if agents else "NAME"


def example_other_agent(state: LabyrinthState) -> str:
    agents = present_agents(state)
    if len(agents) > 1:
        return render_agent(agents[1])
    return "OTHER"


def example_cup(state: LabyrinthState) -> str:
    room = current_room(state)
    cups = list(room.cups.values())
    return render_name(cups[0].name) if cups else "CUP"


def example_cup_short(state: LabyrinthState) -> str:
    cup = example_cup(state)
    return cup.removeprefix("the ")


def example_door(state: LabyrinthState) -> str:
    room = current_room(state)
    doors = list(room.doors.values())
    return render_name(doors[0].name) if doors else "DOOR"


def example_door_short(state: LabyrinthState) -> str:
    door = example_door(state)
    return door.removeprefix("the ")


def example_world_subject(state: LabyrinthState) -> str:
    room = current_room(state)
    if room.cups:
        return example_cup(state)
    if room.doors:
        return example_door(state)
    return example_agent(state)


def agent_kind(agent: Agent) -> str:
    if agent.stationary:
        return "fixed witness"
    return "traveller"


def agent_capability_line(agent: Agent) -> str:
    rendered = render_agent(agent)
    if agent.stationary:
        return f"{rendered} is a fixed witness: it can answer, lie, remember, hear claims, and be slapped, but it cannot move or take actions."
    return f"{rendered} is a traveller: they can answer, lie, remember, form goals, move, sip, ask, and consider instructions."


def render_help(state: LabyrinthState) -> list[str]:
    agent = example_agent(state)
    cup = example_cup(state)
    door = example_door(state)
    return [
        "actions:",
        "- ask NAME about THING",
        f"- ask {agent} about {door}",
        f"- ask {agent} to assess {cup}",
        f"- ask {agent} if/whether {cup} is poison",
        f"- ask {agent} if seven is prime",
        f"- ask {agent} what twenty seven divided by five is",
        f"- ask {agent} liars: Ash calls Bex a liar; Bex calls Ash honest",
        "- tell NAME [to] ACTION",
        f"- tell {agent} {door} leads onward",
        f"- tell {agent} to go {example_door_short(state)}",
        "- sip CUP (or drink CUP)",
        f"- sip {example_cup_short(state)} (or drink {example_cup_short(state)})",
        "- move DOOR (or go DOOR)",
        f"- move {example_door_short(state)} (or go {example_door_short(state)})",
        f"- push {agent} through {example_door_short(state)}",
        f"- slap {agent}",
        "- recall THING (or remember THING)",
        f"- recall {door} (or remember {cup})",
        f"- look {agent}",
        "- help TOPIC",
        "- look",
        "- quit",
        f"try: help ask, help tell, help cup, help door, help agent, help world, help claim, help question, help goblet, help {agent}, help {door}",
    ]


def render_help_help_manual(state: LabyrinthState) -> list[str]:
    agent = example_agent(state)
    cup = example_cup(state)
    door = example_door(state)
    other = example_other_agent(state)
    return [
        "ok, yes. you've asked for help about the help system. well...",
        "help does not spend a turn. it explains commands, objects, claims, and suspicious little abstractions.",
        "forms:",
        "- help",
        "- help TOPIC",
        "- help COMMAND",
        "- help THING",
        "- help CLAIM",
        "useful command pages:",
        "- help ask",
        "- help tell",
        "- help sip",
        "- help move",
        "- help push",
        "- help slap",
        "- help look",
        "- help recall",
        "useful concept pages:",
        "- help cup",
        "- help door",
        "- help name",
        "- help agent",
        "- help witness",
        "- help fixed witness",
        "- help world",
        "- help claim",
        "- help world claim",
        "- help question",
        "- help goblet",
        "- help goblet question",
        "- help liars",
        "- help assessment",
        "- help health",
        "- help poison",
        "- help antidote",
        "- help elixir",
        "- help haste",
        "- help sleep",
        "- help truth",
        "- help trust",
        "- help goals",
        "examples from here:",
        f"- help {agent}",
        f"- help {cup}",
        f"- help {door}",
        f"- help {cup} is poison",
        f"- help {door} leads onward",
        f"- help {agent} go {example_door_short(state)}",
        f"- help {other} is unreliable",
        "it is normal to ask help about help. embarrassing, but normal.",
    ]


def render_health_manual(state: LabyrinthState) -> list[str]:
    agent = example_agent(state)
    return [
        "health is shown as a rough condition, not a combat ledger.",
        "your health is shown as full, three quarters, half, one quarter, or zero.",
        "other agents are described as proud, uneasy, unsure, grim, or gone.",
        "conditions can matter for resistance and survival.",
        f"try: look {agent}",
        f"try: recall {agent}",
        "poison can lower health over time. elixir restores full health.",
    ]


def render_effect_manual(state: LabyrinthState, effect: str) -> list[str]:
    agent = example_agent(state)
    cup = example_cup(state)
    door = example_door(state)
    if effect == "poison":
        return [
            "poison is a lingering status, not just a slap of damage.",
            "a mild poison may stir once, bite once, then run its course. harsher venom can keep biting until cured.",
            "antidote clears poison. elixir clears poison and restores health.",
            "sleeping while poisoned is risky because time still passes.",
            "examples from here:",
            f"- ask {agent} whether {cup} is poison",
            f"- tell {agent} {cup} is poison",
            f"- recall {cup}",
        ]
    if effect == "antidote":
        return [
            "antidote clears poison but does not restore lost health.",
            "agents who know a current cup is antidote may try to drink it when poisoned.",
            "examples from here:",
            f"- ask {agent} whether {cup} is antidote",
            f"- tell {agent} {cup} is antidote",
            f"- recall {cup}",
        ]
    if effect == "elixir":
        return [
            "elixir restores full health and clears poison.",
            "it is stronger than antidote, and also more precious if the cup is running low.",
            "examples from here:",
            f"- ask {agent} whether {cup} is elixir",
            f"- tell {agent} {cup} is elixir",
            f"- drink {example_cup_short(state)}",
        ]
    if effect == "haste":
        return [
            "haste gives more actions starting next round.",
            "it does not let you discover haste and immediately drink the whole cup in the same breath.",
            "haste can make agents act more often too, which is useful until it becomes nonsense with shoes.",
            "examples from here:",
            f"- ask {agent} whether {cup} grants haste",
            f"- tell {agent} {cup} grants haste",
            f"- drink {example_cup_short(state)}",
        ]
    if effect == "truth":
        return [
            "truth effects make a drinker clearer and more truthful.",
            "that can make their later testimony more useful, especially for Goblet questions and dangerous doors.",
            "if you drink it, false claims catch in your throat; you can still repeat uncertain things, but you cannot knowingly tell an object-claim the potion knows is false.",
            "truth is not the same as omniscience; a clear witness still only knows what they know.",
            "examples from here:",
            f"- ask {agent} whether {cup} sharpens truth",
            f"- ask {agent} if seven is prime",
            f"- ask {agent} whether {door} leads onward",
        ]
    if effect == "sleep":
        return [
            "sleeping potion makes the drinker miss their next chance to act.",
            "fixed witnesses also nap after too many questions; their little oracle battery is bad.",
            "you can slap sleepers awake. fixed witnesses may need more than one slap if their sleep is still deep.",
            "sleeping agents cannot resist being pushed. yes, that is awful. the labyrinth noticed.",
            "sleep does not cure poison.",
            "examples from here:",
            f"- ask {agent} whether {cup} is sleeping potion",
            f"- tell {agent} {cup} is sleeping potion",
            f"- push {agent} through {example_door_short(state)}",
        ]
    if effect == "stupor":
        return [
            "stupor slows the drinker.",
            "it is not poison, but it can make an agent less able to act usefully.",
            "examples from here:",
            f"- ask {agent} whether {cup} brings stupor",
            f"- tell {agent} {cup} brings stupor",
            f"- recall {cup}",
        ]
    return render_help(state)


def render_social_manual(state: LabyrinthState, topic: str) -> list[str]:
    agent = example_agent(state)
    other = example_other_agent(state)
    door = example_door(state)
    cup = example_cup(state)
    return [
        "agents can tell the truth, lie, repeat hearsay, remember badly, or speak from partial evidence.",
        "lie profiles distort claims. a wrong answer might be a lie, a mistake, or borrowed nonsense.",
        "trust is scoped: someone may be unreliable about a door without being useless about everything.",
        "memories are stronger than bare trust labels because they say why: who moved, who drank, who slapped, who pushed.",
        "when asked about a person, witnesses prefer recent memory and whereabouts before vague condition gossip.",
        "known-answer Goblet questions can help calibrate a witness.",
        "examples from here:",
        f"- ask {agent} if seven is prime",
        f"- ask {agent} whether {door} leads onward",
        f"- ask {agent} about {other}",
        f"- tell {agent} {other} is unreliable",
        f"- recall {agent}",
        f"- recall {cup}",
    ]


def render_intention_manual(state: LabyrinthState) -> list[str]:
    agent = example_agent(state)
    cup = example_cup(state)
    door = example_door(state)
    return [
        "intentions are what agents currently mean to do when time advances.",
        "agents form goals from claims, memories, witnessed crossings, danger, poison, and instructions.",
        "you can influence intentions, but not command perfect obedience.",
        "examples from here:",
        f"- tell {agent} to go {example_door_short(state)}",
        f"- tell {agent} {door} leads onward",
        f"- tell {agent} {cup} is poison",
        f"- look {agent}",
        f"- recall {agent}",
    ]



def render_question_manual(state: LabyrinthState) -> list[str]:
    agent = example_agent(state)
    cup = example_cup(state)
    door = example_door(state)
    return [
        "questions come in three useful species: world questions, Goblet questions, and classic liars puzzles.",
        "world questions ask about the labyrinth's current people, doors, cups, and states.",
        "Goblet questions ask the symbolic arithmetic engine about numbers, primes, fractions, roots, and comparisons.",
        "classic liars puzzles ask which people are honest or liars, given a little knot of testimony.",
        "forms:",
        f"- ask {agent} about {door}",
        f"- ask {agent} whether {door} leads onward",
        f"- ask {agent} whether {cup} is poison",
        f"- ask {agent} if seven is prime",
        f"- ask {agent} what twenty seven divided by five is",
        f"- ask {agent} liars: Ash calls Bex a liar; Bex calls Ash honest",
        "related help pages:",
        "- help ask",
        "- help world",
        "- help claim",
        "- help goblet",
        "- help goblet question",
        "- help liars",
        "a question can gather testimony, calibrate a witness, or reveal that everyone is confidently useless.",
    ]

def resolve_help(state: LabyrinthState, command: str) -> list[str]:
    topic = command.removeprefix("help ").strip()
    if not topic:
        return render_help(state)
    normalized = normalize_alias(topic)

    if normalized == "help":
        return render_help_help_manual(state)
    if normalized in {"actions", "action", "commands", "command"}:
        return render_help(state)
    if normalized == "ask":
        return render_action_manual(state, "ask")
    if normalized in {"question", "questions"}:
        return render_question_manual(state)
    if normalized in {"tell", "instruction", "instructions"}:
        return render_action_manual(state, "tell")
    if normalized in {"sip", "drink"}:
        return render_action_manual(state, "sip")
    if normalized in {"move", "go"}:
        return render_action_manual(state, "move")
    if normalized == "push":
        return render_action_manual(state, "push")
    if normalized == "slap":
        return render_action_manual(state, "slap")
    if normalized in {"recall", "remember", "memory"}:
        return render_action_manual(state, "recall")
    if normalized == "look":
        return render_action_manual(state, "look")
    if normalized in {"quit", "exit"}:
        return ["quit leaves the labyrinth unresolved."]

    words = normalized.split()
    if words and words[0] in {"ask", "tell", "sip", "drink", "move", "go", "push", "slap", "recall", "remember", "look"}:
        if words[0] == "tell" and len(words) > 1:
            instruction_help = render_instruction_like_manual(state, topic.removeprefix("tell").strip())
            if instruction_help is not None:
                return instruction_help
        action_name = {"drink": "sip", "go": "move", "remember": "recall"}.get(words[0], words[0])
        return render_action_manual(state, action_name)

    if normalized in {
        "name",
        "names",
        "agent",
        "agents",
        "claimant",
        "claimants",
        "person",
        "people",
        "creature",
        "creatures",
        "witness",
        "witnesses",
        "traveller",
        "travellers",
        "traveler",
        "travelers",
        "actor",
        "actors",
    }:
        return render_name_manual(state)
    if normalized in {"fixed", "fixed witness", "fixed witnesses", "stationary", "stationary witness", "stationary witnesses", "oracle", "oracles"}:
        return render_fixed_witness_manual(state)
    if normalized in {"cup", "cups", "potion", "potions"}:
        return render_cup_manual(state)
    if normalized in {"door", "doors", "gate", "gates"}:
        return render_door_manual(state)
    if normalized in {"world", "worlds", "claim", "claims", "world claim", "world claims", "thing", "things"}:
        return render_claim_manual(state, None)
    if normalized in {"goblet", "goblets", "goblet question", "goblet questions", "math", "math question", "math questions", "number", "numbers", "prime", "primes", "fraction", "fractions"}:
        return render_goblet_question_manual(state, None)
    if normalized in {"liars", "liars puzzle", "liar puzzle", "classic liars", "knights", "knaves", "honest liar", "honest liars"}:
        return render_liars_manual(state, None)
    if normalized in {"assess", "assessment", "assessments", "evaluate", "evaluation", "judge", "judgement", "judgment", "weigh claims", "weigh testimony"}:
        return render_assessment_manual(state)
    if normalized in {"health", "hp", "condition", "conditions"}:
        return render_health_manual(state)
    if normalized in {"poison", "poisoned", "venom"}:
        return render_effect_manual(state, "poison")
    if normalized in {"antidote", "cure", "cures"}:
        return render_effect_manual(state, "antidote")
    if normalized in {"elixir", "heal", "healing"}:
        return render_effect_manual(state, "elixir")
    if normalized in {"haste", "speed", "quick"}:
        return render_effect_manual(state, "haste")
    if normalized in {"truth", "clear", "clarity", "truth cup"}:
        return render_effect_manual(state, "truth")
    if normalized in {"sleep", "sleeping", "sleeping potion", "asleep"}:
        return render_effect_manual(state, "sleep")
    if normalized in {"stupor", "slow", "slowness"}:
        return render_effect_manual(state, "stupor")
    if normalized in {"lie", "lies", "lying", "liar", "liars", "trust", "trusted", "unreliable", "reliability"}:
        return render_social_manual(state, normalized)
    if normalized in {"intention", "intentions", "goal", "goals"}:
        return render_intention_manual(state)
    if normalized in {"manual", "manual pages", "topics", "help topics"}:
        return render_help_help_manual(state)

    agent, agent_error = resolve_agent_name(state, topic)
    if agent_error:
        return [agent_error]
    if agent is not None:
        return render_agent_manual(state, agent)

    cup, cup_error = resolve_cup_name(state, state.player, topic)
    if cup_error:
        return [cup_error]
    if cup is not None:
        return render_specific_cup_manual(state, cup)

    door, door_error = resolve_door_name(state, state.player, topic)
    if door_error:
        return [door_error]
    if door is not None:
        return render_specific_door_manual(state, door)

    if topic_looks_like_goblet_question(topic):
        return render_goblet_question_manual(state, topic)
    if topic_looks_like_liars_question(topic):
        return render_liars_manual(state, topic)

    instruction_help = render_instruction_like_manual(state, topic)
    if instruction_help is not None:
        return instruction_help

    subject, proposition = interpret_tell_message(state, topic)
    if subject is not None and proposition is not None:
        return render_claim_manual(state, topic)

    subject, subject_error = resolve_topic_subject(state, topic)
    if subject_error:
        return [subject_error]
    if subject is not None:
        return [
            f"{render_topic(subject)} is a known subject.",
            f"try: recall {render_topic(subject)}",
            f"try: ask NAME about {render_topic(subject)}",
            f"try: tell NAME {render_topic(subject)} is safe / poison / trusted / peril",
        ]

    return [
        f"no manual page for {render_topic(topic)}.",
        "try: help actions, help cup, help door, help world, help claim, help question, help goblet, or recall THING",
    ]


def render_action_manual(state: LabyrinthState, action: str) -> list[str]:
    agent = example_agent(state)
    other = example_other_agent(state)
    cup = example_cup(state)
    cup_short = example_cup_short(state)
    door = example_door(state)
    door_short = example_door_short(state)
    if action == "ask":
        return [
            "ask gets testimony without spending a body.",
            "forms:",
            f"- ask {agent} about {door}",
            f"- ask {agent} to assess {cup}",
            f"- ask {agent} if/whether {cup} is poison",
            f"- ask {agent} if seven is prime",
            f"- ask {agent} what twenty seven divided by five is",
        f"- ask {agent} liars: Ash calls Bex a liar; Bex calls Ash honest",
            "examples from here:",
            f"- ask {agent} about {door}",
            f"- ask {agent} to assess {cup}",
            f"- ask {agent} assess {cup}",
            f"- ask {agent} whether {cup} is poison",
            f"- ask {agent} if seven is prime",
            f"- ask {agent} what twenty seven divided by five is",
        f"- ask {agent} liars: Ash calls Bex a liar; Bex calls Ash honest",
        ]
    if action == "tell":
        return [
            "tell gives another agent a claim or an instruction.",
            "claim forms:",
            f"- tell {agent} {cup} is poison",
            f"- tell {agent} {door} leads onward",
            f"- tell {agent} {other} is unreliable",
            "instruction forms:",
            f"- tell {agent} to move {door_short}",
            f"- tell {agent} go {door_short}",
            f"- tell {agent} drink {cup_short}",
            f"- tell {agent} ask {other} about {door}",
            "agents may consider instructions, but they do not become puppets.",
        ]
    if action == "sip":
        return [
            "sip/drink tests a visible cup with your own body.",
            "forms:",
            f"- sip {cup_short}",
            f"- drink {cup_short}",
            "known cup effects include haste, poison, venom, antidote, elixir, truth, sleep, and stupor.",
            f"try recall {cup} first if you have heard claims about it.",
        ]
    if action == "move":
        return [
            "move/go passes through a visible door.",
            "forms:",
            f"- move {door_short}",
            f"- go {door_short}",
            "safe crossings are strong evidence, and agents may follow them.",
            f"try asking about, recalling, or pushing before body-testing {door}.",
        ]
    if action == "push":
        return [
            "push forces another present agent toward a visible door.",
            f"form: push {agent} through {door_short}",
            "healthy agents usually resist; sleeping or grim agents resist poorly.",
            "witnesses remember push attempts as coercive, even when they fail.",
        ]
    if action == "slap":
        return [
            "slap is a rude interruption of a present named creature.",
            f"form: slap {agent}",
            "travellers lose their current action for this round.",
            "fixed witnesses can be slapped too, but they have no action to stop; if they are asleep, a slap is a wake attempt.",
            "sleeping travellers wake easily; fixed witnesses may need more than one slap if the sleep is still deep.",
            "witnesses remember slaps as violence, because of course they do.",
            "useful when someone is about to drink or enter something stupid. morally crunchy when they are just a toad.",
        ]
    if action == "recall":
        return [
            "recall/remember searches your own memory archive.",
            "forms:",
            f"- recall {door}",
            f"- remember {agent}",
            "examples from here:",
            f"- recall {door}",
            f"- recall {cup}",
            f"- recall {agent}",
        ]
    if action == "look":
        return [
            "look repeats the current room without spending a turn.",
            f"look {agent} inspects a present agent.",
            "forms:",
            "- look",
            f"- look {agent}",
            f"For objects, use help or recall: help {cup}; recall {door}.",
        ]
    return render_help(state)

def render_name_manual(state: LabyrinthState) -> list[str]:
    agents = present_agents(state)
    agent = example_agent(state)
    traveller = next((candidate for candidate in agents if not candidate.stationary), agents[0] if agents else None)
    witness = next((candidate for candidate in agents if candidate.stationary), None)
    active_agent = render_agent(traveller) if traveller is not None else agent
    fixed_agent = render_agent(witness) if witness is not None else "a fixed witness"
    cup = example_cup(state)
    door = example_door(state)
    lines = [
        "agents are the named people and creatures in the room.",
        "travellers can answer questions, lie, remember, form goals, move, sip, ask, and consider instructions.",
        "fixed witnesses can answer, lie, remember, and hear claims, but they cannot move or take actions.",
        "animals count too: a toad, hare, moth, rook, or crow can still be a witness.",
        "related words: name, person, claimant, witness, traveller, creature, actor, fixed witness.",
    ]
    if agents:
        lines.append("present agents:")
        for present in agents:
            lines.append(f"- {render_agent(present)}: {agent_kind(present)}")
    lines.extend([
        "useful forms:",
        f"- ask {agent} about {door}",
        f"- ask {agent} whether {door} leads onward",
        f"- tell {agent} {cup} is poison",
        f"- look {agent}",
        f"- recall {agent}",
    ])
    if traveller is not None:
        lines.extend([
            "traveller instruction forms:",
            f"- tell {active_agent} to go {example_door_short(state)}",
            f"- {active_agent} go {example_door_short(state)}",
        ])
    if witness is not None:
        lines.extend([
            "fixed witness forms:",
            f"- ask {fixed_agent} about {door}",
            f"- ask {fixed_agent} to assess {cup}",
            f"- tell {fixed_agent} {cup} is poison",
            f"- help {fixed_agent}",
        ])
    lines.append("help does not promise they will obey. agents are not handles; they are troublesome little archives.")
    return lines


def render_fixed_witness_manual(state: LabyrinthState) -> list[str]:
    witnesses = [agent for agent in present_agents(state) if agent.stationary]
    agent = render_agent(witnesses[0]) if witnesses else "a fixed witness"
    cup = example_cup(state)
    door = example_door(state)
    lines = [
        "fixed witnesses are stationary named creatures.",
        "they can answer questions, lie, remember, hear claims, and be slapped.",
        "they cannot move, sip cups, ask other people, follow safe crossings, or carry out instructions.",
        "so a toad can be a witness without being a little adventurer in a damp waistcoat.",
        "after a small number of questions, they go to sleep for a short while.",
        "slapping one is allowed, socially noticed, and can wake them if they are asleep; deep fixed-witness sleep may take more than one slap.",
    ]
    if witnesses:
        lines.append("fixed witnesses here:")
        lines.extend(f"- {render_agent(witness)}" for witness in witnesses)
    lines.extend([
        "useful forms:",
        f"- ask {agent} about {door}",
        f"- ask {agent} to assess {cup}",
        f"- ask {agent} whether {cup} is poison",
        f"- tell {agent} {cup} is poison",
        f"- look {agent}",
        f"- recall {agent}",
        f"- slap {agent}",
        "not useful:",
        f"- tell {agent} to go {example_door_short(state)}",
        f"- {agent} go {example_door_short(state)}",
        "slap caveat:",
        f"- slap {agent} is accepted; it can wake them if asleep, but it will not stop an action because there is no action to stop.",
    ])
    return lines


def render_agent_manual(state: LabyrinthState, agent: Agent) -> list[str]:
    rendered = render_agent(agent)
    cup = example_cup(state)
    door = example_door(state)
    door_short = example_door_short(state)
    lines = [f"{rendered} is here and looks {render_condition_word(agent)}."]
    lines.append(agent_capability_line(agent))
    if agent.sleeping:
        lines.append(f"{rendered} is sleeping.")
    if agent.poisoned:
        lines.append(f"{rendered} is poisoned.")
    if not agent.stationary:
        intention = current_agent_intention(state, agent)
        if intention is not None:
            lines.append(f"current intention: {render_action(intention)}")
    lines.extend([
        "useful forms:",
        f"- ask {rendered} about {door}",
        f"- ask {rendered} to assess {cup}",
        f"- ask {rendered} if/whether {cup} is poison",
        f"- tell {rendered} {cup} is poison",
        f"- look {rendered}",
        f"- recall {rendered}",
    ])
    if agent.stationary:
        lines.extend([
            f"- slap {rendered}",
            "not useful:",
            f"- tell {rendered} to go {door_short}",
            f"- {rendered} go {door_short}",
            "fixed witnesses do not take actions; they sit there full of damp opinions.",
            "sleep caveat:",
            "- fixed witnesses may go to sleep after too many questions.",
            f"- slap {rendered} can wake them, but deep fixed-witness sleep may take more than one slap.",
        ])
    else:
        lines.extend([
            "instruction forms:",
            f"- tell {rendered} to go {door_short}",
            f"- {rendered} go {door_short}",
        ])
    return lines


def render_cup_manual(state: LabyrinthState) -> list[str]:
    room = current_room(state)
    agent = example_agent(state)
    cup = example_cup(state)
    cup_short = example_cup_short(state)
    lines = ["cups can be sipped, asked about, recalled, or used in claims."]
    if room.cups:
        lines.append("visible cups:")
        for cup_obj in room.cups.values():
            lines.append(f"- {render_name(cup_obj.name)}: {render_cup_fullness(cup_obj.fifths)}")
    lines.extend([
        "try:",
        f"- drink {cup_short}",
        f"- ask {agent} about {cup}",
        f"- ask {agent} to assess {cup}",
        f"- ask {agent} whether {cup} is poison",
        f"- tell {agent} {cup} grants haste",
        f"- recall {cup}",
    ])
    return lines

def render_specific_cup_manual(state: LabyrinthState, cup: Cup) -> list[str]:
    rendered = render_name(cup.name)
    agent = example_agent(state)
    return [
        f"{rendered}: {render_cup_fullness(cup.fifths)}.",
        "possible commands:",
        f"- drink {rendered}",
        f"- ask {agent} about {rendered}",
        f"- ask {agent} whether {rendered} is poison / safe / antidote / elixir / sleeping potion",
        f"- tell {agent} {rendered} is poison / safe / antidote / elixir / sleeping potion",
        f"- recall {rendered}",
        "help does not reveal the cup's true effect; testimony and testing do.",
    ]

def render_door_manual(state: LabyrinthState) -> list[str]:
    room = current_room(state)
    agent = example_agent(state)
    door = example_door(state)
    door_short = example_door_short(state)
    lines = ["doors can lead onward, to the exit, or to peril."]
    if room.doors:
        lines.append("visible doors:")
        lines.extend(f"- {render_name(door_obj.name)}" for door_obj in room.doors.values())
    lines.extend([
        "try:",
        f"- go {door_short}",
        f"- ask {agent} about {door}",
        f"- ask {agent} whether {door} leads onward",
        f"- tell {agent} {door} leads to peril",
        f"- push {agent} through {door_short}",
        f"- recall {door}",
    ])
    return lines

def render_specific_door_manual(state: LabyrinthState, door: Door) -> list[str]:
    rendered = render_name(door.name)
    agent = example_agent(state)
    return [
        f"{rendered} is a visible door.",
        "possible commands:",
        f"- go {rendered}",
        f"- ask {agent} about {rendered}",
        f"- ask {agent} whether {rendered} leads onward / to peril / to the exit",
        f"- tell {agent} {rendered} leads onward / to peril / to the exit",
        f"- push {agent} through {rendered}",
        f"- recall {rendered}",
        "help does not reveal where the door truly leads; testimony and crossings do.",
    ]


def render_instruction_like_manual(state: LabyrinthState, topic: str) -> list[str] | None:
    normalized_topic = normalize_alias(topic)
    if not normalized_topic:
        return None
    for agent in present_agents(state):
        names = derive_aliases(agent.name, agent) | {normalize_alias(render_agent(agent))}
        for name in names:
            if not name:
                continue
            if normalized_topic == name:
                continue
            if normalized_topic.startswith(name + " "):
                rest = normalized_topic.removeprefix(name).strip()
                if rest.startswith("to "):
                    rest = rest.removeprefix("to ").strip()
                words = rest.split()
                if not words:
                    continue
                if words[0] not in {"go", "move", "sip", "drink", "ask", "push", "slap"}:
                    continue
                rendered_agent = render_agent(agent)
                if agent.stationary:
                    return [
                        f"this looks like an instruction for {rendered_agent}, but {rendered_agent} is a fixed witness.",
                        "fixed witnesses can answer, lie, remember, and hear claims, but they cannot move or take actions.",
                        "useful forms:",
                        f"- ask {rendered_agent} about {example_door(state)}",
                        f"- ask {rendered_agent} whether {example_cup(state)} is poison",
                        f"- tell {rendered_agent} {example_cup(state)} is poison",
                        f"- recall {rendered_agent}",
                    ]
                if words[0] in {"go", "move"}:
                    target = " ".join(words[1:])
                    door, _ = resolve_door_name(state, state.player, target)
                    rendered_target = render_name(door.name) if door is not None else target or example_door(state)
                    typed_target = target or rendered_target
                    direct_alias = f"{rendered_agent} {words[0]} {typed_target}"
                    return [
                        f"this looks like an instruction for {rendered_agent}.",
                        f"{direct_alias} is accepted as shorthand for: tell {rendered_agent} to go {rendered_target}",
                        "other useful forms:",
                        f"- tell {rendered_agent} to go {rendered_target}",
                        f"- tell {rendered_agent} go {rendered_target}",
                        f"- ask {rendered_agent} about {rendered_target}",
                        f"- recall {rendered_target}",
                    ]
                if words[0] in {"sip", "drink"}:
                    target = " ".join(words[1:])
                    cup, _ = resolve_cup_name(state, state.player, target)
                    rendered_target = render_name(cup.name) if cup is not None else target or example_cup(state)
                    verb = "drink" if words[0] == "drink" else "sip"
                    typed_target = target or rendered_target
                    direct_alias = f"{rendered_agent} {verb} {typed_target}"
                    return [
                        f"this looks like an instruction for {rendered_agent}.",
                        f"{direct_alias} is accepted as shorthand for: tell {rendered_agent} to {verb} {rendered_target}",
                        "other useful forms:",
                        f"- tell {rendered_agent} to drink {rendered_target}",
                        f"- tell {rendered_agent} drink {rendered_target}",
                        f"- ask {rendered_agent} about {rendered_target}",
                        f"- recall {rendered_target}",
                    ]
                return [
                    f"this looks like an instruction for {rendered_agent}.",
                    "try:",
                    f"- tell {rendered_agent} to {rest}",
                    f"- tell {rendered_agent} {rest}",
                    "agents may consider instructions, but they do not become puppets.",
                ]
    return None

def render_claim_manual(state: LabyrinthState, claim: str | None) -> list[str]:
    agent = example_agent(state)
    cup = example_cup(state)
    door = example_door(state)
    other = example_other_agent(state)
    if claim:
        subject, proposition = interpret_tell_message(state, claim)
        if subject is not None and proposition is not None:
            rendered_subject = render_topic(subject)
            return [
                f"this looks like a usable world claim about {rendered_subject}.",
                f"claim text: {render_proposition(proposition)}",
                "try:",
                f"- tell {agent} {claim}",
                f"- ask {agent} whether {claim}",
                f"- recall {rendered_subject}",
            ]
    return [
        "world claims are statements about the labyrinth, its people, doors, cups, and states.",
        "agents can hear them, remember them, believe them, doubt them, repeat them, or lie about them.",
        "useful claim shapes:",
        "- CUP is poison / safe / antidote / elixir / sleeping potion / empty",
        "- CUP grants haste / sharpens truth",
        "- DOOR leads onward / to peril / to the exit / is safe",
        "- NAME is trusted / unreliable / a liar / poisoned / sleeping",
        "examples from here:",
        f"- tell {agent} {cup} is poison",
        f"- ask {agent} whether {door} leads onward",
        f"- tell {agent} {door} leads to peril",
        f"- ask {agent} whether {other} is unreliable",
        f"- recall {door}",
        "world claims are not always true; testimony and crossings do the work.",
    ]

def render_goblet_question_manual(state: LabyrinthState, expression: str | None) -> list[str]:
    sample_name = example_agent(state)
    door = example_door(state)
    lines = [
        "Goblet questions use the symbolic arithmetic engine inside the labyrinth.",
        "They are not about the current room directly, but agents can answer them, lie about them, and remember them.",
        "forms:",
        f"- ask {sample_name} if seven is prime",
        f"- ask {sample_name} whether three hundred and seventeen is prime",
        f"- ask {sample_name} what twenty seven divided by five is",
        f"- ask {sample_name} if at most five is greater than four",
        "A Goblet question can calibrate a witness. A world claim can get you killed.",
        f"world claim example: ask {sample_name} whether {door} leads onward",
        f"Goblet question example: ask {sample_name} whether seven is prime",
    ]
    if expression:
        mode = bare_goblet_question_mode(clean_goblet_expression("if", expression)) or bare_goblet_question_mode(clean_goblet_expression("what", expression))
        if mode == "what":
            lines.insert(0, "this looks like a Goblet expression question.")
            lines.append(f"try: ask {sample_name} what {clean_goblet_expression('what', expression)} is")
        elif mode == "if":
            lines.insert(0, "this looks like a Goblet yes/no question.")
            lines.append(f"try: ask {sample_name} if {clean_goblet_expression('if', expression)}")
    return lines


def render_assessment_manual(state: LabyrinthState) -> list[str]:
    agent = example_agent(state)
    other = example_other_agent(state)
    cup = example_cup(state)
    door = example_door(state)
    return [
        "assessment asks a witness to weigh testimony, memory, reputation, and body evidence.",
        "it can assess cups, doors, people, witnesses, or a whole claim. it is not direct truth: the assessor weighs the pile, then may still lie about the weighing.",
        "witness weights shift socially: truth-tellers tend to reward true claims, frequent liars tend to admire successful lying, and arbitrary liars are difficult little weather systems.",
        "body evidence outweighs gossip, but gossip still piles up in useful little heaps.",
        "forms:",
        f"- ask {agent} to assess {cup}",
        f"- ask {agent} assess {door}",
        f"- ask {agent} assess {other}",
        f"- ask {agent} assess witnesses",
        f"- ask {agent} assess {cup} is poison",
        "what it can sound like:",
        f"- {other} is a good witness; Nox is a notorious liar",
        f"- by weight, {cup} is poison comes out heaviest",
        f"- likely {cup} is poison, unless Ash and Bex are lying or badly wrong",
        f"- the claim has two support and three against",
        "assessment is useful when recall has a pile of claims and you want a witness to do the little consistency dance for you.",
        f"try: recall {cup}",
    ]


def render_liars_manual(state: LabyrinthState, expression: str | None) -> list[str]:
    visible_agents = [render_agent(agent) for agent in present_agents(state)]
    agent = visible_agents[0] if visible_agents else "Ash"
    other = visible_agents[1] if len(visible_agents) > 1 else "Bex"
    third = visible_agents[2] if len(visible_agents) > 2 else "Della"
    sample = f"{agent} calls {other} a liar; {other} calls {agent} honest"
    lines = [
        "classic liars puzzles are small honest/liar logic knots.",
        "They are separate from the labyrinth's fractional lie profiles: here, each named person is assumed honest or a liar for the puzzle only.",
        "forms:",
        f"- ask {agent} liars: {sample}",
        f"- ask {agent} liar puzzle: {agent} calls {other} a liar; {other} calls {third} honest; {third} calls {agent} a liar",
        "statement forms:",
        "- NAME calls NAME honest",
        "- NAME calls NAME a liar",
        "what comes back:",
        "- forced: only one possible honest/liar assignment survives",
        "- ambiguous: more than one assignment survives",
        "- contradictory: no assignment survives",
        "agents can answer these puzzles, lie about the solution, and remember the exchange.",
        "This lets liars.py shake hands with Liar's Labyrinth without pretending they are the same beast.",
    ]
    if expression:
        lines.insert(0, "this looks like a classic liars puzzle question.")
        lines.append(f"try: ask {agent} liars: {expression.removeprefix('liars:').strip()}")
    return lines


def topic_looks_like_liars_question(topic: str) -> bool:
    normalized = normalize_alias(topic).strip()
    if normalized.startswith(("liars:", "liar puzzle:", "liars puzzle:")):
        return True
    return " calls " in normalized and (" a liar" in normalized or " honest" in normalized)


def topic_looks_like_goblet_question(topic: str) -> bool:
    expression = topic.strip().rstrip("?.")
    lowered = expression.lower()
    if lowered.startswith("if "):
        expression = expression[3:].strip()
    if lowered.startswith("whether "):
        expression = expression[8:].strip()
    if lowered.startswith("what "):
        expression = clean_goblet_expression("what", expression[5:].strip())
    return bare_goblet_question_mode(expression) is not None


def resolve_look(state: LabyrinthState, command: str) -> list[str]:
    target_raw = command.removeprefix("look ").strip()
    if not target_raw:
        return ["look at what?"]

    normalized = normalize_alias(target_raw)
    room = current_room(state)

    if normalized in {"door", "doors"}:
        lines = ["visible doors:"]
        lines.extend(f"- {render_name(door.name)}" for door in room.doors.values())
        return lines

    if normalized in {"cup", "cups"}:
        lines = ["visible cups:"]
        lines.extend(f"- {render_name(cup.name)}: {render_cup_fullness(cup.fifths)}" for cup in room.cups.values())
        return lines

    target, agent_error = resolve_agent_name(state, target_raw)
    if target is not None:
        return [f"{render_agent(target)} looks {render_condition_word(target)}."]

    cup, cup_error = resolve_cup_name(state, state.player, target_raw)
    if cup is not None:
        return [f"{render_name(cup.name)}: {render_cup_fullness(cup.fifths)}."]
    if cup_error and "which cup" in cup_error:
        return [cup_error]

    door, door_error = resolve_door_name(state, state.player, target_raw)
    if door is not None:
        return [f"{render_name(door.name)} stands here."]
    if door_error and "which door" in door_error:
        return [door_error]

    if agent_error:
        return [agent_error]
    return [f"you cannot see {render_topic(target_raw)} here"]


def validate_player_command(state: LabyrinthState, command: str) -> str | None:
    if command.startswith("slap "):
        target_raw = command.removeprefix("slap ").strip()
        if not target_raw:
            return "slap whom?"
        target, error = resolve_agent_name(state, target_raw)
        if error:
            return error
        if target is None:
            return f"you cannot slap {render_topic(target_raw)}; no one by that name is here"
        return None

    if command.startswith("push "):
        parsed = parse_push_command(state, command)
        if isinstance(parsed, str):
            return parsed
        return None

    if command.startswith("ask "):
        return validate_ask_command(state, command)

    if command.startswith("tell "):
        return validate_tell_command(state, command)

    if command.startswith("sip "):
        cup_name = parse_target(command, "sip ")
        if not cup_name:
            return "sip what?"
        cup, error = resolve_cup_name(state, state.player, cup_name)
        if error:
            return error
        if cup is None:
            return f"you cannot sip {render_topic(command.removeprefix('sip ').strip())}; no such cup is here"
        return None

    if command.startswith("move "):
        door_name = parse_target(command, "move ")
        if not door_name:
            return "move where?"
        door, error = resolve_door_name(state, state.player, door_name)
        if error:
            return error
        if door is None:
            return f"you cannot move through {render_topic(command.removeprefix('move ').strip())}; no such door is here"
        return None

    if command == "assess" or command.startswith("assess "):
        return "ask whom to assess what? Try: ask Aster to assess Vey"

    return f"unknown action: {command}"


def validate_ask_command(state: LabyrinthState, command: str) -> str | None:
    assessment_parsed = parse_assessment_ask_command(state, command)
    if isinstance(assessment_parsed, AssessmentAsk):
        if assessment_parsed.target.sleeping:
            return f"{render_agent(assessment_parsed.target)} is sleeping; slap them if you need them awake"
        return None
    if isinstance(assessment_parsed, str):
        return assessment_parsed

    liars_parsed = parse_liars_ask_command(state, command)
    if isinstance(liars_parsed, LiarsAsk):
        if liars_parsed.target.sleeping:
            return f"{render_agent(liars_parsed.target)} is sleeping; slap them if you need them awake"
        try:
            evaluate_liars_claim_pair(liars_parsed)
        except ValueError as exc:
            return f"that does not seem like a liars puzzle: {exc}"
        return None
    if isinstance(liars_parsed, str):
        return liars_parsed

    goblet_parsed = parse_goblet_ask_command(state, command)
    if isinstance(goblet_parsed, GobletAsk):
        if goblet_parsed.target.sleeping:
            return f"{render_agent(goblet_parsed.target)} is sleeping; slap them if you need them awake"
        try:
            evaluate_goblet_ask(goblet_parsed)
        except ValueError as exc:
            return f"that does not seem like a Goblet question: {exc}"
        return None
    if isinstance(goblet_parsed, str):
        return goblet_parsed

    world_parsed = parse_world_ask_command(state, command)
    if isinstance(world_parsed, str):
        return world_parsed
    if isinstance(world_parsed, WorldAsk):
        if world_parsed.target.sleeping:
            return f"{render_agent(world_parsed.target)} is sleeping; slap them if you need them awake"
        return None

    parsed = parse_ask_command(state, command)
    if isinstance(parsed, str):
        return parsed
    target, _, _ = parsed
    if target.sleeping:
        return f"{render_agent(target)} is sleeping; slap them if you need them awake"
    return None


def validate_tell_command(state: LabyrinthState, command: str) -> str | None:
    parsed = parse_tell_command(state, command)
    if isinstance(parsed, str):
        return parsed
    if isinstance(parsed, TellInstruction):
        if parsed.target.stationary:
            return f"{render_agent(parsed.target)} is a fixed witness and cannot take actions"
        if not goal_action_is_available(state, parsed.target, parsed.action):
            return f"{render_agent(parsed.target)} cannot {render_action(parsed.action)} from here"
        return None
    if parsed.subject is None or parsed.proposition is None:
        return f"{render_agent(parsed.target)} does not know how to use that. Tell them a claim about a known thing."
    truth_error = validate_truth_bound_tell(state, parsed)
    if truth_error:
        return truth_error
    return None



def parse_assessment_ask_command(state: LabyrinthState, command: str) -> AssessmentAsk | str | None:
    body = command.removeprefix("ask ").strip()
    if not body:
        return None
    lowered = body.lower()

    target_name = ""
    raw_subject = ""
    for marker in (" to assess ", " assess "):
        marker_index = lowered.find(marker)
        if marker_index >= 0:
            target_name = body[:marker_index].strip()
            raw_subject = body[marker_index + len(marker):].strip()
            break
    if not target_name and lowered.startswith("assess "):
        return "ask whom to assess what? Try: ask the copper toad to assess the silver cup"
    if not target_name:
        return None
    if not raw_subject:
        return "ask whom to assess what?"

    target, error = resolve_agent_name(state, target_name)
    if error:
        return error
    if target is None:
        return f"you ask {render_topic(target_name)}, but no one by that name is here"
    if not target.alive or target.room_index != state.room_index:
        return f"you ask {render_topic(target_name)}, but they are not here"

    subject, subject_error = resolve_assessment_subject(state, target, raw_subject)
    if subject_error:
        return subject_error
    if subject is None:
        return f"{render_agent(target)} cannot assess {render_topic(raw_subject)}; no known cup or door by that name is here"
    return AssessmentAsk(target=target, raw_subject=raw_subject, subject=subject)


def resolve_assessment_subject(state: LabyrinthState, target: Agent, raw_subject: str) -> tuple[str | None, str | None]:
    # Prefer the assessor's current room so bare words like "cup" or "silver"
    # do not summon every object in the whole labyrinth unless no local object fits.
    room = state.rooms[agent_room_index(state, target)]
    local_candidates: dict[str, Any] = {}
    local_candidates.update(room.cups)
    local_candidates.update(room.doors)
    entity, error = resolve_named_entity(raw_subject, local_candidates, "cup or door")
    if error:
        return None, error
    if entity is not None and hasattr(entity, "name"):
        return entity.name, None

    normalized = normalize_alias(raw_subject)
    if normalized in {"witness", "witnesses", "agent", "agents", "person", "people", "claimant", "claimants", "traveller", "travellers", "traveler", "travelers", "creature", "creatures", "actor", "actors"}:
        return WITNESSES_ASSESSMENT_SUBJECT, None

    subject, subject_error = resolve_topic_subject(state, raw_subject)
    if subject_error:
        return None, subject_error
    if subject is not None:
        return subject, None

    claim_subject, claim_proposition = interpret_tell_message(state, raw_subject)
    if claim_subject is not None and claim_proposition is not None:
        canonical = canonical_claim_proposition(state, claim_proposition, claim_subject) or claim_proposition
        return make_claim_assessment_subject(claim_subject, canonical), None

    return None, None


def make_claim_assessment_subject(subject: str, proposition: str) -> str:
    return f"{CLAIM_ASSESSMENT_PREFIX}{subject}::{proposition}"


def is_claim_assessment_subject(subject: str) -> bool:
    return subject.startswith(CLAIM_ASSESSMENT_PREFIX)


def claim_assessment_parts(subject: str) -> tuple[str, str]:
    body = subject.removeprefix(CLAIM_ASSESSMENT_PREFIX)
    claim_subject, proposition = body.split("::", 1)
    return claim_subject, proposition


def is_person_assessment_subject(state: LabyrinthState, subject: str) -> bool:
    return subject == state.player.name or subject in state.claimants

def parse_liars_ask_command(state: LabyrinthState, command: str) -> LiarsAsk | str | None:
    body = command.removeprefix("ask ").strip()
    lowered = body.lower()
    markers = (" liars:", " liar puzzle:", " liars puzzle:")
    marker_index = -1
    marker = ""
    for candidate in markers:
        marker_index = lowered.find(candidate)
        if marker_index >= 0:
            marker = candidate
            break
    if marker_index < 0:
        return None

    target_name = body[:marker_index].strip()
    raw_text = body[marker_index + len(marker):].strip()
    if not target_name or not raw_text:
        return "ask whom which liars puzzle?"

    target, error = resolve_agent_name(state, target_name)
    if error:
        return error
    if target is None:
        return f"you ask {render_topic(target_name)}, but no one by that name is here"
    if not target.alive or target.room_index != state.room_index:
        return f"you ask {render_topic(target_name)}, but they are not here"

    puzzle_text, puzzle_error = inline_liars_puzzle_text(state, raw_text)
    if puzzle_error:
        return puzzle_error
    return LiarsAsk(target=target, raw_text=raw_text, puzzle_text=puzzle_text)


def inline_liars_puzzle_text(state: LabyrinthState, raw_text: str) -> tuple[str, str | None]:
    if "\n" in raw_text and "people:" in raw_text.lower() and "statements:" in raw_text.lower():
        return raw_text, None

    people: list[str] = []
    statements: list[str] = []
    clauses = [clause.strip().rstrip(".") for clause in re.split(r";|\n", raw_text) if clause.strip()]
    for clause in clauses:
        lowered = clause.lower()
        if lowered.startswith("people:"):
            for raw_name in re.split(r",| and ", clause[len("people:"):].strip()):
                name = canonical_liars_person_name(state, raw_name.strip())
                if name and name not in people:
                    people.append(name)
            continue
        if lowered.startswith("statements:"):
            clause = clause[len("statements:"):].strip()
            if not clause:
                continue
        statement, names, error = parse_inline_liars_statement(state, clause)
        if error:
            return "", error
        for name in names:
            if name not in people:
                people.append(name)
        statements.append(statement)

    if not statements:
        return "", "liars puzzle needs at least one statement"
    return "people:\n" + "\n".join(people) + "\nstatements:\n" + "\n".join(statements), None


def parse_inline_liars_statement(state: LabyrinthState, clause: str) -> tuple[str, list[str], str | None]:
    match = re.fullmatch(r"(.+?)\s+calls\s+(.+?)\s+(a liar|honest)", clause.strip(), flags=re.IGNORECASE)
    if not match:
        return "", [], f"unsupported liars statement: {clause}"
    speaker = canonical_liars_person_name(state, match.group(1).strip())
    target = canonical_liars_person_name(state, match.group(2).strip())
    kind = match.group(3).lower()
    if speaker is None or target is None:
        return "", [], f"unsupported liars names in: {clause}"
    if kind == "a liar":
        return f"{speaker} calls {target} a liar", [speaker, target], None
    return f"{speaker} calls {target} honest", [speaker, target], None


def canonical_liars_person_name(state: LabyrinthState, raw_name: str) -> str | None:
    normalized = normalize_alias(raw_name)
    if not normalized:
        return None
    candidates: dict[str, Agent] = dict(state.claimants)
    candidates[state.player.name] = state.player
    matches: list[str] = []
    for name, agent in candidates.items():
        aliases = {normalize_alias(alias) for alias in derive_aliases(name, agent)}
        if normalized in aliases:
            matches.append(name)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return None
    words = raw_name.strip().split()
    if len(words) == 1 and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", words[0]):
        return words[0][0].upper() + words[0][1:]
    return None


def parse_goblet_ask_command(state: LabyrinthState, command: str) -> GobletAsk | str | None:
    body = command.removeprefix("ask ").strip()
    lowered = body.lower()
    markers = ((" if ", "if"), (" whether ", "if"), (" what ", "what"))
    for marker, mode in markers:
        marker_index = lowered.find(marker)
        if marker_index < 0:
            continue
        target_name = body[:marker_index].strip()
        expression = body[marker_index + len(marker):].strip()
        if not target_name or not expression:
            return "ask whom what Goblet question?"

        target, error = resolve_agent_name(state, target_name)
        if error:
            return error
        if target is None:
            return f"you ask {render_topic(target_name)}, but no one by that name is here"
        if not target.alive or target.room_index != state.room_index:
            return f"you ask {render_topic(target_name)}, but they are not here"

        expression = clean_goblet_expression(mode, expression)
        if not expression:
            return "ask what Goblet question?"
        if not expression_is_goblet_question(mode, expression):
            return None
        return GobletAsk(target=target, mode=mode, expression=expression)
    bare_question = parse_bare_goblet_ask_command(state, body)
    if bare_question is not None:
        return bare_question
    return None


def parse_bare_goblet_ask_command(state: LabyrinthState, body: str) -> GobletAsk | str | None:
    parts = body.split(maxsplit=1)
    if len(parts) != 2:
        return None

    target_name, expression = parts
    mode = bare_goblet_question_mode(expression)
    if mode is None:
        return None

    target, error = resolve_agent_name(state, target_name)
    if error:
        return error
    if target is None:
        return None
    if not target.alive or target.room_index != state.room_index:
        return f"you ask {render_topic(target_name)}, but they are not here"
    expression = clean_goblet_expression(mode, expression)
    if not expression:
        return "ask what Goblet question?"
    return GobletAsk(target=target, mode=mode, expression=expression)


def bare_goblet_question_mode(expression: str) -> str | None:
    lowered = expression.lower()
    if any(marker in lowered for marker in (" plus ", " minus ", " divided by ", " times ", " multiplied by ")):
        return "what"
    if lowered.endswith(" is prime") or lowered.endswith(" is not prime"):
        return "if"
    if any(marker in lowered for marker in (
        " is greater than ",
        " is less than ",
        " is equal to ",
        " equals ",
        " is at least ",
        " is at most ",
    )):
        return "if"
    return None


def expression_is_goblet_question(mode: str, expression: str) -> bool:
    return bare_goblet_question_mode(expression) == mode


def parse_world_ask_command(state: LabyrinthState, command: str) -> WorldAsk | str | None:
    body = command.removeprefix("ask ").strip()
    lowered = body.lower()
    for marker in (" if ", " whether "):
        marker_index = lowered.find(marker)
        if marker_index < 0:
            continue
        target_name = body[:marker_index].strip()
        expression = body[marker_index + len(marker):].strip().rstrip("?.")
        if not target_name or not expression:
            return "ask whom what?"

        target, error = resolve_agent_name(state, target_name)
        if error:
            return error
        if target is None:
            return f"you ask {render_topic(target_name)}, but no one by that name is here"
        if not target.alive or target.room_index != state.room_index:
            return f"you ask {render_topic(target_name)}, but they are not here"

        resolved_expression = resolve_world_ask_expression(expression, target)
        subject, proposition = interpret_tell_message(state, resolved_expression)
        if subject is None or proposition is None:
            return f"{render_agent(target)} would not know what {render_topic(expression)} means"
        return WorldAsk(target=target, expression=expression, subject=subject, proposition=proposition)
    return None


def resolve_world_ask_expression(expression: str, target: Agent) -> str:
    normalized = normalize_alias(expression)
    if normalized.startswith("it "):
        return render_agent(target) + " " + expression.split(maxsplit=1)[1]
    if normalized == "it":
        return render_agent(target)
    return expression


def resolve_recall(state: LabyrinthState, command: str) -> list[str]:
    topic = recall_topic(command)
    if not topic:
        return ["recall what?"]

    subject = canonicalize_topic(state, topic)
    entries = recall_entries(state, subject, topic)
    if not entries:
        return [f"you remember no claims from or about {render_topic(topic)}"]

    lines = [f"you remember these things from or about {render_topic(subject)}:"]
    seen: set[str] = set()
    for entry in entries:
        summary = recall_entry_summary(state, entry)
        if summary in seen:
            continue
        seen.add(summary)
        lines.append(f"- {summary}")
    if len(lines) == 1:
        return [f"you remember nothing from or about {render_topic(topic)}"]
    return lines


def recall_topic(command: str) -> str:
    if command.startswith("recall "):
        return command.removeprefix("recall ").strip()
    if command.startswith("remember "):
        return command.removeprefix("remember ").strip()
    return ""


RECALL_MEMORY_KINDS = {"heard_claim", "claim_made", "reported_claim", "goblet_claim", "liars_claim", "action", "outcome"}


def recall_entries(state: LabyrinthState, subject: str, raw_topic: str) -> list[MemoryEntry]:
    player = state.player
    raw_forms = recall_topic_forms(raw_topic)
    entries: list[MemoryEntry] = []
    for entry in player.memory.entries:
        if entry.kind not in RECALL_MEMORY_KINDS:
            continue
        if entry.source == player.name:
            if entry.kind != "action":
                continue
        if entry.kind in {"action", "outcome"} and not recall_direct_memory_is_relevant(entry, subject, raw_forms):
            continue
        if recall_entry_matches(state, entry, subject, raw_forms):
            entries.append(entry)
    return entries


def recall_direct_memory_is_relevant(entry: MemoryEntry, subject: str, raw_forms: set[str]) -> bool:
    if subject and (entry.subject == subject or subject in entry.subjects):
        return True
    if is_broad_cup_topic(raw_forms) and recall_entry_mentions_cup(entry):
        return True
    return False


def is_broad_cup_topic(raw_forms: set[str]) -> bool:
    return "cup" in raw_forms


def recall_entry_mentions_cup(entry: MemoryEntry) -> bool:
    searchable = normalize_alias(" ".join(
        part for part in (entry.subject or "", entry.text, entry.proposition or "", " ".join(entry.subjects))
        if part
    ))
    return "cup" in searchable or any(subject.endswith("Cup") for subject in entry.subjects)


def recall_entry_matches(state: LabyrinthState, entry: MemoryEntry, subject: str, raw_forms: set[str]) -> bool:
    if entry.kind in {"heard_claim", "claim_made", "reported_claim"}:
        if subject and entry.source == subject:
            return True
        focus = claim_focus_subject(state, entry)
        if subject and focus == subject:
            return True
        return bool(focus and is_broad_cup_topic(raw_forms) and focus.endswith("Cup"))

    if is_broad_cup_topic(raw_forms) and recall_entry_mentions_cup(entry):
        return True

    if subject and (entry.source == subject or entry.subject == subject or subject in entry.subjects):
        return True
    searchable = normalize_alias(" ".join(
        part for part in (
            entry.source or "",
            entry.subject or "",
            entry.text,
            entry.proposition or "",
            " ".join(entry.subjects),
        )
        if part
    ))
    return any(topic_form_matches(searchable, form) for form in raw_forms)


def topic_form_matches(searchable: str, form: str) -> bool:
    if not form:
        return False
    if " " in form:
        return f" {form} " in f" {searchable} "
    if len(form) < 4:
        return False
    return re.search(rf"\b{re.escape(form)}\b", searchable) is not None


def recall_topic_forms(raw_topic: str) -> set[str]:
    normalized = normalize_alias(raw_topic)
    forms = {normalized, compact_alias(raw_topic), singularize_topic(normalized)}
    return {form for form in forms if form}


def singularize_topic(topic: str) -> str:
    if topic.endswith("ies") and len(topic) > 3:
        return topic[:-3] + "y"
    if topic.endswith("s") and len(topic) > 4:
        return topic[:-1]
    return topic


def recall_entry_summary(state: LabyrinthState, entry: MemoryEntry) -> str:
    if entry.kind == "heard_claim" and entry.source:
        return f"{render_source_name(state, entry.source)} said: {strip_recalled_claim_prefix(state, entry).rstrip('.')}{claim_audit_suffix(entry)}"
    if entry.kind == "goblet_claim" and entry.source:
        return f"{render_source_name(state, entry.source)} answered: {entry.text}"
    if entry.kind == "liars_claim" and entry.source:
        return f"{render_source_name(state, entry.source)} solved: {entry.text}"
    if entry.kind == "reported_claim" and entry.source:
        return f"{render_source_name(state, entry.source)} reported: {entry.text.rstrip('.')}{claim_audit_suffix(entry)}"
    if entry.kind == "action":
        if entry.source == "You":
            return f"you did: {entry.text.rstrip('.')}"
        if entry.source:
            return f"you saw {render_source_name(state, entry.source)} act: {entry.text.rstrip('.')}"
        return f"you saw: {entry.text.rstrip('.')}"
    if entry.kind == "outcome":
        return f"you learned: {entry.text.rstrip('.')}"
    return entry.text


def strip_recalled_claim_prefix(state: LabyrinthState, entry: MemoryEntry) -> str:
    if not entry.source:
        return entry.text
    text = entry.text.strip()
    source = render_source_name(state, entry.source)
    prefixes = (
        f"{source} claims ",
        f"{entry.source} claims ",
    )
    normalized_text = normalize_alias(text)
    for prefix in prefixes:
        if text.startswith(prefix):
            return text.removeprefix(prefix)
        normalized_prefix = normalize_alias(prefix)
        if normalized_text.startswith(normalized_prefix + " "):
            return text[len(prefix):] if len(text) >= len(prefix) else text
    return text


def clean_goblet_expression(mode: str, expression: str) -> str:
    cleaned = expression.strip().rstrip("?.")
    lowered = cleaned.lower()
    if mode == "what":
        if lowered.startswith("is "):
            cleaned = cleaned[3:].strip()
            lowered = cleaned.lower()
        if lowered.endswith(" is"):
            cleaned = cleaned[:-3].strip()
    return cleaned


def parse_ask_command(state: LabyrinthState, command: str) -> tuple[Agent, str, str] | str:
    body = command.removeprefix("ask ").strip()
    marker = " about "
    marker_index = body.lower().find(marker)
    if marker_index < 0:
        return "ask whom about what?"

    target_name = body[:marker_index].strip()
    topic = body[marker_index + len(marker):].strip()
    if not target_name or not topic:
        return "ask whom about what?"

    target, error = resolve_agent_name(state, target_name)
    if error:
        return error
    if target is None:
        return f"you ask {render_topic(target_name)}, but no one by that name is here"
    if not target.alive or target.room_index != state.room_index:
        return f"you ask {render_topic(target_name)}, but they are not here"

    if is_health_topic(topic):
        return target, topic, target.name

    qualified_person_topic = parse_qualified_person_topic(state, topic)
    if qualified_person_topic is not None:
        subject, qualifier = qualified_person_topic
        return target, qualifier, subject

    subject, topic_error = resolve_topic_subject(state, topic)
    if topic_error:
        return topic_error
    if subject is None:
        return f"{render_agent(target)} would not know what {render_topic(topic)} means"

    return target, topic, subject


def parse_ask_command_for_agent(state: LabyrinthState, asker: Agent, command: str) -> tuple[Agent, str, str] | str:
    body = command.removeprefix("ask ").strip()
    marker = " about "
    marker_index = body.lower().find(marker)
    if marker_index < 0:
        return "ask whom about what?"

    target_name = body[:marker_index].strip()
    topic = body[marker_index + len(marker):].strip()
    if not target_name or not topic:
        return "ask whom about what?"

    target, error = resolve_agent_name_from_room(state, target_name, asker.room_index)
    if error:
        return error
    if target is None:
        return f"{asker.name} cannot ask {render_topic(target_name)}; no one by that name is here"
    if not target.alive or target.room_index != asker.room_index:
        return f"{asker.name} cannot ask {render_topic(target_name)}; they are not here"

    if is_health_topic(topic):
        return target, topic, target.name

    qualified_person_topic = parse_qualified_person_topic(state, topic)
    if qualified_person_topic is not None:
        subject, qualifier = qualified_person_topic
        return target, qualifier, subject

    subject, topic_error = resolve_topic_subject(state, topic)
    if topic_error:
        return topic_error
    if subject is None:
        return f"{render_agent(target)} would not know what {render_topic(topic)} means"

    return target, topic, subject


def is_health_topic(topic: str) -> bool:
    normalized = normalize_alias(topic)
    return normalized in {"health", "condition", "status", "state", "wounds", "hurt"}


def parse_qualified_person_topic(state: LabyrinthState, raw_topic: str) -> tuple[str, str] | None:
    """Resolve topics like "Ash health" or "Ash's condition".

    Plain "ask Bex about Ash" should stay a broad person question, because
    players often want whereabouts/recent memory. Explicit qualifiers such as
    health/status still get the old condition answer.
    """
    normalized = normalize_alias(raw_topic)
    if not normalized:
        return None
    candidates: dict[str, Any] = {name: agent for name, agent in state.claimants.items()}
    candidates[state.player.name] = state.player
    for subject_name, entity in candidates.items():
        aliases = sorted(derive_aliases(subject_name, entity), key=len, reverse=True)
        for alias in aliases:
            if not alias or normalized == alias:
                continue
            for separator in (" ", " s "):
                prefix = alias + separator
                if normalized.startswith(prefix):
                    qualifier = normalized[len(prefix):].strip()
                    if is_health_topic(qualifier):
                        return subject_name, qualifier
    return None


def parse_tell_command(state: LabyrinthState, command: str) -> TellClaim | TellInstruction | str:
    body = command.removeprefix("tell ").strip()
    if not body:
        return "tell whom what?"

    words = body.split()
    target: Agent | None = None
    target_words = ""
    error: str | None = None
    for length in range(min(3, len(words)), 0, -1):
        possible = " ".join(words[:length])
        candidate, candidate_error = resolve_agent_name(state, possible)
        if candidate is not None:
            target = candidate
            target_words = possible
            break
        if candidate_error:
            error = candidate_error
    if target is None:
        return error or f"you tell {render_topic(words[0])}, but no one by that name is here"
    if not target.alive or target.room_index != state.room_index:
        return f"you tell {render_agent(target)}, but they are not here"

    message = body[len(target_words):].strip()
    if not message:
        return f"tell {render_agent(target)} what?"

    action_text = tell_instruction_text(message)
    if action_text is not None:
        action, action_error = parse_instruction_action(state, target, action_text)
        if action_error:
            return action_error
        return TellInstruction(target, message, action)

    subject, proposition = interpret_tell_message(state, message)
    return TellClaim(target, message, subject, proposition)


def tell_instruction_text(message: str) -> str | None:
    if message.startswith("to "):
        return message.removeprefix("to ").strip()
    normalized = normalize_player_command(message)
    if normalized.startswith(("move ", "sip ", "ask ")):
        return message
    return None


def parse_instruction_action(state: LabyrinthState, target: Agent, action_text: str) -> tuple[str, str | None]:
    command = normalize_player_command(action_text.strip())
    if not command:
        return "", "tell them to do what?"
    if command.startswith("move "):
        door_name = parse_target(command, "move ")
        if not door_name:
            return "", "tell them to move where?"
        door, error = resolve_door_name(state, target, door_name)
        if error:
            return "", error
        if door is None:
            return "", f"{render_agent(target)} cannot move through {render_topic(command.removeprefix('move ').strip())}; no such door is here"
        return f"move {door.name}", None
    if command.startswith("sip "):
        cup_name = parse_target(command, "sip ")
        if not cup_name:
            return "", "tell them to sip what?"
        cup, error = resolve_cup_name(state, target, cup_name)
        if error:
            return "", error
        if cup is None:
            return "", f"{render_agent(target)} cannot sip {render_topic(command.removeprefix('sip ').strip())}; no such cup is here"
        return f"sip {cup.name}", None
    if command.startswith("ask "):
        parsed = parse_ask_command_for_agent(state, target, command)
        if isinstance(parsed, str):
            return "", parsed
        ask_target, _, subject = parsed
        return f"ask {ask_target.name} about {subject}", None
    return "", "you can tell them to move, sip, drink, go, or ask"


def resolve_topic_subject(state: LabyrinthState, raw_topic: str) -> tuple[str | None, str | None]:
    candidates: dict[str, Any] = {name: agent for name, agent in state.claimants.items()}
    candidates[state.player.name] = state.player
    for room in state.rooms:
        candidates[room.name] = room
        for door in room.doors.values():
            candidates[door.name] = door
        for cup in room.cups.values():
            candidates[cup.name] = cup
    entity, error = resolve_named_entity(raw_topic, candidates, "subject")
    if error:
        return None, error
    if entity is not None and hasattr(entity, "name"):
        return entity.name, None
    return None, None


USABLE_TELL_WORDS = {
    "safe", "unsafe", "poison", "poisoned", "empty", "full", "antidote",
    "elixir", "heal", "heals", "health", "restores", "restored",
    "haste", "quick", "truth", "clear", "stupor", "slow", "sleep",
    "sleeping", "asleep", "drowsy", "dream", "peril",
    "onward", "exit", "liar", "lies", "honest", "trusted", "untrusted",
    "unreliable", "reckless", "useful", "cautious", "hungry", "kind",
    "ash", "bone", "brass", "copper", "flint", "glass", "gold", "iron",
    "oak", "pewter", "salt", "silver", "wax",
}



def validate_truth_bound_tell(state: LabyrinthState, parsed: TellClaim) -> str | None:
    if not state.player.truth_bound or parsed.subject is None or parsed.proposition is None:
        return None
    truth = objective_truth_for_proposition(state, parsed.subject, parsed.proposition)
    if truth is not False:
        return None
    true_prop = true_proposition_for_subject(state, parsed.subject)
    if true_prop:
        return f"the truth potion catches in your throat: you cannot say that; it knows {render_proposition(true_prop)}."
    return "the truth potion catches in your throat: you cannot make that claim."


def objective_truth_for_proposition(state: LabyrinthState, subject: str, proposition: str) -> bool | None:
    canonical = canonical_claim_proposition(state, proposition, subject)
    if canonical is None:
        return None
    true_props = objective_true_propositions(state, subject)
    false_props = objective_false_propositions(state, subject)
    if normalize_alias(canonical) in {normalize_alias(prop) for prop in true_props}:
        return True
    if normalize_alias(canonical) in {normalize_alias(prop) for prop in false_props}:
        return False
    return None


def objective_true_propositions(state: LabyrinthState, subject: str) -> list[str]:
    for room in state.rooms:
        cup = room.cups.get(subject)
        if cup is not None:
            props: list[str] = []
            if cup.effect in {"poison", "venom"}:
                props.append(f"{subject} is poison")
            if cup.effect == "haste":
                props.append(f"{subject} grants haste")
            if cup.effect == "truth":
                props.append(f"{subject} sharpens truth")
            if cup.effect == "sleep":
                props.append(f"{subject} is sleeping potion")
            if cup.effect == "stupor":
                props.append(f"{subject} brings stupor")
            if cup.effect == "antidote":
                props.append(f"{subject} is antidote")
            if cup.effect == "elixir":
                props.append(f"{subject} is elixir")
            if cup.effect not in {"poison", "venom", "sleep", "stupor"}:
                props.append(f"{subject} is safe")
            if is_zero(cup.fifths):
                props.append(f"{subject} is empty")
            return props
        door = room.doors.get(subject)
        if door is not None:
            props = []
            if door.result == "peril":
                props.append(f"{subject} leads to peril")
            if door.result == "next":
                props.append(f"{subject} leads onward")
                props.append(f"{subject} is safe")
            if door.result == "exit":
                props.append(f"{subject} is the exit")
                props.append(f"{subject} is safe")
            return props
    agent = state.claimants.get(subject) or (state.player if subject == state.player.name else None)
    if agent is not None:
        props = []
        props.append(f"{subject} is {'poisoned' if agent.poisoned else 'not poisoned'}")
        props.append(f"{subject} is {'sleeping' if agent.sleeping else 'not sleeping'}")
        props.append(f"{subject} is {'alive' if agent.alive else 'gone'}")
        return props
    return []


def objective_false_propositions(state: LabyrinthState, subject: str) -> list[str]:
    true_norms = {normalize_alias(prop) for prop in objective_true_propositions(state, subject)}
    options: list[str] = []
    if is_cup_subject(state, subject):
        options = [
            f"{subject} is poison",
            f"{subject} is safe",
            f"{subject} is antidote",
            f"{subject} is elixir",
            f"{subject} grants haste",
            f"{subject} sharpens truth",
            f"{subject} brings stupor",
            f"{subject} is sleeping potion",
            f"{subject} is empty",
        ]
    elif is_door_subject(state, subject):
        options = [
            f"{subject} leads to peril",
            f"{subject} leads onward",
            f"{subject} is safe",
            f"{subject} is the exit",
        ]
    elif subject in state.claimants or subject == state.player.name:
        options = [
            f"{subject} is poisoned",
            f"{subject} is not poisoned",
            f"{subject} is sleeping",
            f"{subject} is not sleeping",
            f"{subject} is alive",
            f"{subject} is gone",
        ]
    return [prop for prop in options if normalize_alias(prop) not in true_norms]


def true_proposition_for_subject(state: LabyrinthState, subject: str) -> str | None:
    props = objective_true_propositions(state, subject)
    return props[0] if props else None

def interpret_tell_message(state: LabyrinthState, message: str) -> tuple[str | None, str | None]:
    subjects = extract_subjects(state, message)
    if not subjects:
        subject = subject_from_identity_clause(state, message)
        if subject is None:
            return None, None
        subjects = {subject}
    normalized = normalize_alias(message)
    words = set(normalized.split())
    if not words.intersection(USABLE_TELL_WORDS):
        return None, None
    primary_subject = sorted(subjects, key=lambda name: normalize_alias(" ".join(words_from_name(name))))[0]
    return primary_subject, normalize_tell_proposition(state, message)


def subject_from_identity_clause(state: LabyrinthState, message: str) -> str | None:
    normalized = normalize_alias(message)
    for marker in (" is ", " are "):
        marker_index = normalized.find(marker)
        if marker_index < 0:
            continue
        raw_subject = normalized[:marker_index].strip()
        subject, error = resolve_topic_subject(state, raw_subject)
        if error is None and subject is not None:
            return subject
    return None


def normalize_tell_proposition(state: LabyrinthState, message: str) -> str:
    # Keep the user's wording, but replace any CamelCase subject mentions with
    # canonical names when we can find them. This keeps tells useful without
    # pretending we have a full semantic parser yet.
    return message.strip().rstrip(".")

def resolve_turn(state: LabyrinthState, command: str) -> list[str]:
    lines, slapped = resolve_player_turn(state, command)
    state.slapped_this_round = slapped
    return lines


def resolve_player_turn(state: LabyrinthState, command: str) -> tuple[list[str], str | None]:
    before_room_index = state.room_index
    lines: list[str] = []
    slapped = None
    command = command.strip()
    if command.startswith("slap "):
        slapped_raw = command.removeprefix("slap ").strip()
        slapped_agent, error = resolve_agent_name(state, slapped_raw)
        if slapped_agent is not None:
            room_index = state.room_index
            record_room_event(
                state,
                room_index,
                kind="action",
                text=f"slapped {render_agent(slapped_agent)}.",
                source="You",
                subject=slapped_agent.name,
                proposition=f"You slapped {slapped_agent.name}",
                certainty="seen directly",
            )
            mark_slap_social_consequence(state, state.player, slapped_agent, room_index)
            if slapped_agent.sleeping:
                lines.extend(resolve_slap_sleeping_agent(state, slapped_agent))
            elif slapped_agent.stationary:
                lines.append(f"you slap {render_agent(slapped_agent)}; {render_agent(slapped_agent)} remains exactly where it was, now with an opinion")
            else:
                slapped = slapped_agent.name
                lines.append(f"you slap {render_agent(slapped_agent)}; {render_agent(slapped_agent)}'s action is stopped")
        else:
            if error:
                lines.append(error)
            else:
                lines.append(f"you slap at {slapped_raw}, but no one is stopped")
    elif command.startswith("push "):
        parsed = parse_push_command(state, command)
        if isinstance(parsed, str):
            lines.append(parsed)
        else:
            target, door = parsed
            slapped = target.name
            lines.extend(resolve_push(state, state.player, target, door))
    else:
        lines.extend(resolve_player_action(state, command))
    state.player_changed_room_this_turn = state.room_index != before_room_index
    return lines, slapped


def resolve_agent_phase(state: LabyrinthState, slapped: str | None = None) -> list[str]:
    if slapped is None:
        slapped = state.slapped_this_round
    state.slapped_this_round = None
    lines: list[str] = []
    for name, agent in state.claimants.items():
        if not agent.alive or agent.stationary:
            continue
        if name == slapped:
            continue
        observed = agent.room_index == state.room_index
        if agent.sleeping:
            before = len(lines)
            lines.extend(resolve_sleep_phase(state, agent))
            if not observed:
                lines[before:] = []
            continue
        for turn_count in count_up_to(agent.speed):
            intention = current_agent_intention(state, agent)
            if intention is None:
                break
            before = len(lines)
            if observed and count_greater_than(agent.speed, ONE):
                lines.append(f"{name}'s {render_turn_ordinal(turn_count)} turn")
            lines.extend(resolve_agent_action(state, agent, intention))
            if not observed:
                lines[before:] = []
            if state.escaped or not agent.alive or agent.sleeping:
                break
        if state.escaped:
            break
    return lines


def begin_player_round(state: LabyrinthState) -> None:
    # Lock the player's action budget at the start of the round. If a haste
    # effect changes speed during this round, it affects the next budget, not
    # the current one.
    state.player_turn_budget = state.player.speed
    state.player_turns_taken = ZERO
    state.slapped_this_round = None
    state.player_changed_room_this_turn = False


def finish_player_action(state: LabyrinthState) -> None:
    state.player_turns_taken = increment_count(state.player_turns_taken)


def player_turns_remaining(state: LabyrinthState) -> WordNumber:
    if count_at_least(state.player_turns_taken, state.player_turn_budget):
        return ZERO
    return subtract(state.player_turn_budget, state.player_turns_taken)


def should_end_player_phase(state: LabyrinthState) -> bool:
    if state.escaped or not state.player.alive:
        return True
    return is_zero(player_turns_remaining(state))


def should_run_agent_phase(state: LabyrinthState) -> bool:
    if state.escaped or not state.player.alive:
        return False
    return is_zero(player_turns_remaining(state))



PUSH_RESIST = "resist"
PUSH_YIELD = "yield"


def hp_band(agent: Agent) -> str:
    if agent.sleeping:
        return "sleeping"
    if count_at_least(agent.hp, FOUR):
        return "four"
    if count_at_least(agent.hp, THREE):
        return "three"
    if agent.hp == TWO:
        return "two"
    return "one"


def push_resistance_cycle_for(agent: Agent) -> list[str]:
    # Deterministic fourths, not hidden dice: a full-health traveller resists
    # three pushes in four, then yields; wounded travellers resist less.
    band = hp_band(agent)
    if band == "sleeping":
        return [PUSH_YIELD, PUSH_YIELD, PUSH_YIELD, PUSH_YIELD]
    if band == "four":
        return [PUSH_RESIST, PUSH_RESIST, PUSH_RESIST, PUSH_YIELD]
    if band == "three":
        return [PUSH_RESIST, PUSH_RESIST, PUSH_YIELD, PUSH_YIELD]
    if band == "two":
        return [PUSH_RESIST, PUSH_YIELD, PUSH_YIELD, PUSH_YIELD]
    return [PUSH_YIELD, PUSH_YIELD, PUSH_YIELD, PUSH_YIELD]


def next_push_resistance(agent: Agent) -> str:
    band = hp_band(agent)
    if agent.push_resistance_hp != band or not agent.push_resistance_cycle:
        agent.push_resistance_hp = band
        agent.push_resistance_cycle = push_resistance_cycle_for(agent)
    result = agent.push_resistance_cycle.pop(0)
    agent.push_resistance_cycle.append(result)
    return result


def push_resistance_description(agent: Agent) -> str:
    band = hp_band(agent)
    if band == "sleeping":
        return "at all"
    if band == "four":
        return "strongly"
    if band == "three":
        return "firmly"
    if band == "two":
        return "weakly"
    return "barely"


def mark_push_social_consequence(state: LabyrinthState, pusher: Agent, target: Agent, room_index: int) -> None:
    # The social consequence is deliberately modest for now: witnesses do not
    # instantly attack, but they do mark the pusher as untrusted about pushing.
    for observer in observers_in_room(state, room_index):
        if observer.name == pusher.name:
            continue
        trust_key = f"{pusher.name}:pushing"
        observer.memory.trust[trust_key] = "distrusted"
        observer.memory.trust_evidence.setdefault(trust_key, []).append(f"pushed:{target.name}:{render_number(state.round_number)}")


def mark_slap_social_consequence(state: LabyrinthState, slapper: Agent, target: Agent, room_index: int) -> None:
    # A slap is smaller than a push, but still a public act of violence.
    for observer in observers_in_room(state, room_index):
        if observer.name == slapper.name:
            continue
        trust_key = f"{slapper.name}:slapping"
        observer.memory.trust[trust_key] = "distrusted"
        observer.memory.trust_evidence.setdefault(trust_key, []).append(f"slapped:{target.name}:{render_number(state.round_number)}")


def parse_push_command(state: LabyrinthState, command: str) -> tuple[Agent, Door] | str:
    body = command.removeprefix("push ").strip()
    if not body:
        return "push whom through which door?"

    target_raw = ""
    door_raw = ""
    lowered = body.lower()
    for marker in (" through ", " into ", " to "):
        marker_index = lowered.find(marker)
        if marker_index >= 0:
            target_raw = body[:marker_index].strip()
            door_raw = body[marker_index + len(marker):].strip()
            break

    if not target_raw or not door_raw:
        split_body = body.split(maxsplit=1)
        if len(split_body) == 2:
            target_raw, door_raw = split_body
        else:
            return "push whom through which door? Try: push Bram through the iron door"

    target, target_error = resolve_agent_name(state, target_raw)
    if target_error:
        return target_error
    if target is None:
        return f"you cannot push {render_topic(target_raw)}; no one by that name is here"
    if target.name == "You":
        return "you cannot push yourself through a door"
    if target.stationary:
        return f"{render_agent(target)} will not be pushed"

    door, door_error = resolve_door_name(state, state.player, door_raw)
    if door_error:
        return door_error
    if door is None:
        return f"you cannot push {render_agent(target)} through {render_topic(door_raw)}; no such door is here"
    return target, door


def resolve_push(state: LabyrinthState, pusher: Agent, target: Agent, door: Door) -> list[str]:
    room_index = state.room_index
    action_text = f"{render_agent(pusher)} push {render_agent(target)} toward {render_name(door.name)}"
    if pusher.name != "You":
        action_text = f"{render_agent(pusher)} pushes {render_agent(target)} toward {render_name(door.name)}"
    else:
        action_text = f"you push {render_agent(target)} toward {render_name(door.name)}"

    record_room_event(
        state,
        room_index,
        kind="forced_action",
        text=action_text + ".",
        source=pusher.name,
        subject=target.name,
        proposition=f"{pusher.name} pushed {target.name} toward {door.name}",
        certainty="seen directly",
    )
    mark_push_social_consequence(state, pusher, target, room_index)

    resistance = next_push_resistance(target)
    if resistance == PUSH_RESIST:
        resist_text = f"{render_agent(target)} resists {push_resistance_description(target)} and does not go through"
        record_room_event(
            state,
            room_index,
            kind="outcome",
            text=resist_text + ".",
            source=target.name,
            subject=target.name,
            proposition=f"{target.name} resisted being pushed through {door.name}",
            certainty="seen directly",
        )
        target.observances.append(f"{pusher.name} tried to push {target.name} through {door.name}, but {target.name} resisted")
        return [action_text, resist_text]

    yield_text = f"{render_agent(target)} cannot resist and stumbles through"
    record_room_event(
        state,
        room_index,
        kind="outcome",
        text=yield_text + ".",
        source=target.name,
        subject=target.name,
        proposition=f"{target.name} was pushed through {door.name}",
        certainty="seen directly",
    )
    target.observances.append(f"{pusher.name} pushed {target.name} through {door.name}")

    lines = [action_text, yield_text]
    lines.extend(resolve_move(state, target, door.name))
    return lines

def render_player_turns(state: LabyrinthState) -> str:
    remaining = player_turns_remaining(state)
    return f"your actions this round: {render_number(state.player_turns_taken)} used, {render_number(remaining)} remaining"


def resolve_player_action(state: LabyrinthState, command: str) -> list[str]:
    if command.startswith("push "):
        parsed = parse_push_command(state, command)
        if isinstance(parsed, str):
            return [parsed]
        target, door = parsed
        return resolve_push(state, state.player, target, door)
    if command.startswith("ask "):
        assessment_parsed = parse_assessment_ask_command(state, command)
        if isinstance(assessment_parsed, AssessmentAsk):
            return resolve_assessment_ask(state, state.player, assessment_parsed)
        liars_parsed = parse_liars_ask_command(state, command)
        if isinstance(liars_parsed, LiarsAsk):
            return resolve_liars_ask(state, state.player, liars_parsed)
        goblet_parsed = parse_goblet_ask_command(state, command)
        if isinstance(goblet_parsed, GobletAsk):
            return resolve_goblet_ask(state, state.player, goblet_parsed)
        world_parsed = parse_world_ask_command(state, command)
        if isinstance(world_parsed, WorldAsk):
            return resolve_world_ask(state, state.player, world_parsed)
        return resolve_ask(state, state.player, command)
    if command.startswith("tell "):
        return resolve_tell(state, state.player, command)
    if command.startswith("sip "):
        cup_name = parse_target(command, "sip ")
        cup, error = resolve_cup_name(state, state.player, cup_name)
        if cup is None:
            return [error or f"you cannot find {render_name(cup_name)}"]
        return resolve_sip(state, state.player, cup.name)
    if command.startswith("move "):
        door_name = parse_target(command, "move ")
        if door_name.startswith("through "):
            door_name = door_name.removeprefix("through ").strip()
        door, error = resolve_door_name(state, state.player, door_name)
        if door is None:
            return [error or f"you cannot find {render_name(door_name)}"]
        return resolve_move(state, state.player, door.name)
    return [f"unknown action: {command}"]



def resolve_assessment_ask(state: LabyrinthState, asker: Agent, question: AssessmentAsk) -> list[str]:
    spoke_lie = next_claim_kind(question.target) == LIE
    if is_claim_assessment_subject(question.subject):
        claim = render_claim_assessment_claim(state, question.target, question.subject, lie=spoke_lie)
        spoken_likely = None
    elif question.subject == WITNESSES_ASSESSMENT_SUBJECT:
        claim = render_witnesses_assessment_claim(state, question.target, lie=spoke_lie)
        spoken_likely = None
    elif is_person_assessment_subject(state, question.subject):
        claim = render_person_assessment_claim(state, question.target, question.subject, lie=spoke_lie)
        spoken_likely = None
    else:
        report = build_assessment_report(state, question.target, question.subject)
        truthful_claim = render_assessment_claim(state, question.target, report, lie=False)
        distorted_claim = render_assessment_claim(state, question.target, report, lie=True)
        claim = distorted_claim if spoke_lie else truthful_claim
        spoken_likely = distorted_assessment_proposition(state, report) if spoke_lie else report.likely

    subject_text = render_subject_name(state, question.subject)
    ask_line = (
        f"you ask {render_agent(question.target)} to assess {subject_text}"
        if asker.name == "You"
        else f"{render_agent_verb(asker, 'ask')} {render_agent(question.target)} to assess {subject_text}"
    )
    room_index = state.room_index
    record_room_event(
        state,
        room_index,
        kind="action",
        text=ask_line + ".",
        source=asker.name,
        subject=question.target.name,
        proposition=f"{asker.name} asked {question.target.name} to assess {question.subject}",
        certainty="seen directly",
        subjects=[question.subject],
    )
    record_claim_event(state, question.target, claim, room_index)
    if spoken_likely is not None:
        report = build_assessment_report(state, question.target, question.subject)
        update_social_weight_from_assessment(state, question.target, report, spoken_likely, room_index)
    asker.observances.append(f"{asker.name} asked {question.target.name} to assess {question.subject}")
    question.target.observances.append(f"{asker.name} asked {question.target.name} to assess {question.subject}")
    question.target.observances.append(claim)
    lines = [ask_line, claim]
    lines.extend(maybe_tire_fixed_witness(state, question.target))
    return lines

def evaluate_assessment_claim_pair(state: LabyrinthState, question: AssessmentAsk) -> tuple[str, str]:
    if is_claim_assessment_subject(question.subject):
        return (
            render_claim_assessment_claim(state, question.target, question.subject, lie=False),
            render_claim_assessment_claim(state, question.target, question.subject, lie=True),
        )
    if question.subject == WITNESSES_ASSESSMENT_SUBJECT:
        return (
            render_witnesses_assessment_claim(state, question.target, lie=False),
            render_witnesses_assessment_claim(state, question.target, lie=True),
        )
    if is_person_assessment_subject(state, question.subject):
        return (
            render_person_assessment_claim(state, question.target, question.subject, lie=False),
            render_person_assessment_claim(state, question.target, question.subject, lie=True),
        )
    report = build_assessment_report(state, question.target, question.subject)
    truthful = render_assessment_claim(state, question.target, report, lie=False)
    distorted = render_assessment_claim(state, question.target, report, lie=True)
    return truthful, distorted


def build_assessment_report(state: LabyrinthState, assessor: Agent, subject: str) -> AssessmentReport:
    entries = assessor.memory.entries_about(subject)
    evidence: list[AssessmentEvidence] = []
    direct_evidence: list[str] = []
    for entry in entries:
        if entry.kind in {"heard_claim", "claim_made", "reported_claim", "liars_claim"} and entry.source:
            if " assesses " in normalize_alias(entry.text):
                # Assessments are meta-testimony. They are remembered, but should
                # not become fresh object evidence and recursively fatten later assessments.
                continue
            proposition = canonical_claim_proposition(state, entry.proposition or entry.text, subject)
            if proposition is not None:
                evidence.append(AssessmentEvidence(
                    source=entry.source,
                    proposition=proposition,
                    entry_id=entry.id,
                    kind=entry.kind,
                    certainty=entry.certainty,
                    initial_rating=entry.initial_rating,
                    current_rating=entry.current_rating,
                ))
        elif entry.kind in {"outcome", "inference"} and entry.proposition:
            proposition = canonical_claim_proposition(state, entry.proposition, subject)
            if proposition is not None:
                direct_evidence.append(proposition)

    scores_by_proposition = assessment_scores_by_proposition(state, assessor, subject, evidence, direct_evidence)
    likely = likely_assessment_proposition_from_scores(scores_by_proposition)
    alternatives = tuple(
        proposition for proposition in sorted(scores_by_proposition, key=render_proposition)
        if likely is None or proposition != likely
    )
    supporters = tuple(sorted({item.source for item in evidence if likely and propositions_compatible(subject, item.proposition, likely)}))
    opponents = tuple(sorted({item.source for item in evidence if likely and propositions_conflict(subject, item.proposition, likely)}))
    source_weights = tuple(
        AssessmentSourceWeight(source, weight, witness_weight_label(weight))
        for source, weight in sorted(
            {item.source: witness_weight_for_subject(state, assessor, item.source, subject) for item in evidence}.items(),
            key=lambda pair: (pair[1], render_source_name(state, pair[0])),
        )
    )
    scores = tuple(
        AssessmentScore(proposition, weight)
        for proposition, weight in sorted(scores_by_proposition.items(), key=lambda pair: (-pair[1], render_proposition(pair[0])))
    )
    return AssessmentReport(
        subject=subject,
        evidence=tuple(evidence),
        likely=likely,
        alternatives=alternatives,
        supporters=supporters,
        opponents=opponents,
        direct_evidence=tuple(sorted(set(direct_evidence))),
        scores=scores,
        source_weights=source_weights,
    )


def assessment_scores_by_proposition(
    state: LabyrinthState,
    assessor: Agent,
    subject: str,
    evidence: list[AssessmentEvidence],
    direct_evidence: list[str],
) -> dict[str, int]:
    scores: dict[str, int] = {}
    for proposition in direct_evidence:
        scores[proposition] = scores.get(proposition, 0) + 6
    for item in evidence:
        weight = witness_weight_for_subject(state, assessor, item.source, subject)
        bucket = audit_bucket(item.current_rating)
        if bucket == "supported":
            weight += 2
        elif bucket == "refuted":
            weight = 1
        # Repeated testimony stacks naturally because each remembered claim is
        # processed separately. Notorious liars still count as a whisper, not as zero:
        # a bad source is information, just weaker and smellier information.
        scores[item.proposition] = scores.get(item.proposition, 0) + max(1, weight)
    return scores


def likely_assessment_proposition_from_scores(scores: dict[str, int]) -> str | None:
    if not scores:
        return None
    return sorted(scores.items(), key=lambda pair: (-pair[1], render_proposition(pair[0])))[0][0]


def witness_weight_for_subject(state: LabyrinthState, assessor: Agent, source: str, subject: str) -> int:
    if source == assessor.name:
        base = 3
    else:
        source_agent = state.claimants.get(source)
        if source_agent is None:
            base = 2
        else:
            base = base_witness_weight(source_agent)
    base += assessor.memory.social_weight.get(f"{source}:*", 0)
    base += assessor.memory.social_weight.get(f"{source}:{subject}", 0)
    trust = assessor.memory.trust.get(f"{source}:{subject}")
    if trust == "trusted":
        base += 2
    elif trust == "distrusted":
        base -= 2
    return min(5, max(1, base))


def base_witness_weight(agent: Agent) -> int:
    # Map the fourths-based lie profile into testimony weight. This is still
    # deliberately coarse: the assessor knows reputation bands, not a spreadsheet.
    if agent.lie_rate.lies == ZERO:
        return 4
    if agent.lie_rate.lies == ONE:
        return 3
    if agent.lie_rate.lies == TWO:
        return 2
    if agent.lie_rate.lies == THREE:
        return 1
    return 1


def lie_taste_for_truth(agent: Agent) -> int:
    """Positive means this observer likes truth; negative means they like lying."""
    if agent.lie_rate.lies == ZERO:
        return 2
    if agent.lie_rate.lies == ONE:
        return 1
    if agent.lie_rate.lies == TWO:
        return 0
    if agent.lie_rate.lies == THREE:
        return -1
    return -2


def social_delta_for_truth_event(observer: Agent, told_truth: bool) -> int:
    taste = lie_taste_for_truth(observer)
    if taste == 0:
        return 0
    raw = taste if told_truth else -taste
    magnitude = 2 if abs(taste) >= 2 else 1
    return magnitude if raw > 0 else -magnitude


def clamp_social_weight(value: int) -> int:
    return min(3, max(-3, value))


def adjust_social_weight(
    observer: Agent,
    source: str,
    subject: str,
    delta: int,
    evidence: str,
    update_verdict: bool = True,
) -> None:
    if delta == 0:
        return
    key = f"{source}:{subject}"
    current = observer.memory.social_weight.get(key, 0)
    new_value = clamp_social_weight(current + delta)
    observer.memory.social_weight[key] = new_value
    observer.memory.social_evidence.setdefault(key, []).append(evidence)
    if update_verdict and subject != "*":
        if new_value >= 2:
            observer.memory.trust[key] = "trusted"
            observer.memory.trust_evidence.setdefault(key, []).append(evidence)
        elif new_value <= -2:
            observer.memory.trust[key] = "distrusted"
            observer.memory.trust_evidence.setdefault(key, []).append(evidence)


def adjust_social_weight_for_truth_event(
    observer: Agent,
    source: str,
    subject: str,
    told_truth: bool,
    caller: str | None,
    evidence: str,
) -> None:
    delta = social_delta_for_truth_event(observer, told_truth)
    if delta == 0:
        return
    if caller is not None and caller != observer.name:
        # A trusted assessor's judgement lands harder. A notorious liar's judgement
        # still lands, but as a tap rather than a hammer.
        caller_weight = witness_weight_for_subject_placeholder(observer, caller, subject)
        if caller_weight >= 4:
            delta *= 2
        elif caller_weight <= 1:
            delta = 1 if delta > 0 else -1
    adjust_social_weight(observer, source, subject, delta, evidence)


def witness_weight_for_subject_placeholder(observer: Agent, source: str, subject: str) -> int:
    # Local version used where a full LabyrinthState is deliberately unavailable.
    # Existing social taste is enough here; the caller's objective lie profile is
    # handled by normal assessment weighting elsewhere.
    base = 3 if source == observer.name else 2
    base += observer.memory.social_weight.get(f"{source}:*", 0)
    base += observer.memory.social_weight.get(f"{source}:{subject}", 0)
    trust = observer.memory.trust.get(f"{source}:{subject}")
    if trust == "trusted":
        base += 2
    elif trust == "distrusted":
        base -= 2
    return min(5, max(1, base))


def maybe_update_social_weight_from_reputation_claim(state: LabyrinthState, observer: Agent, entry: MemoryEntry) -> None:
    if entry.kind not in {"heard_claim", "claim_made", "reported_claim"} or not entry.source:
        return
    accused, reputation = reputation_claim_target_and_kind(state, entry)
    if accused is None or reputation is None:
        return
    taste = lie_taste_for_truth(observer)
    if taste == 0:
        return
    if reputation == "liar":
        # Truth-lovers downgrade a person called a liar. Lie-lovers upgrade them.
        delta = -1 if taste > 0 else 1
    else:
        # Truth-lovers like honest/trusted people. Lie-lovers find them dreary.
        delta = 1 if taste > 0 else -1
    caller_weight = witness_weight_for_subject(state, observer, entry.source, accused)
    if caller_weight >= 4:
        delta *= 2
    elif caller_weight <= 1:
        delta = 1 if delta > 0 else -1
    adjust_social_weight(observer, accused, "*", delta, f"reputation:{entry.id}:{entry.source}", update_verdict=False)


def reputation_claim_target_and_kind(state: LabyrinthState, entry: MemoryEntry) -> tuple[str | None, str | None]:
    for subject in sorted(entry.subjects):
        if subject == entry.source or subject == entry.subject:
            continue
        if subject not in state.claimants and subject != state.player.name:
            continue
        proposition = canonical_claim_proposition(state, entry.proposition or entry.text, subject)
        if proposition is None:
            continue
        normalized = normalize_alias(proposition)
        if normalized.endswith(" lies") or " is unreliable" in normalized:
            return subject, "liar"
        if " is trusted" in normalized:
            return subject, "trusted"
    return None, None


def update_social_weight_from_assessment(
    state: LabyrinthState,
    assessor: Agent,
    report: AssessmentReport,
    spoken_likely: str | None,
    room_index: int,
) -> None:
    if spoken_likely is None:
        return
    observers = observers_in_room(state, room_index)
    for observer in observers:
        for item in report.evidence:
            if propositions_compatible(report.subject, item.proposition, spoken_likely):
                adjust_social_weight_for_truth_event(
                    observer,
                    item.source,
                    report.subject,
                    told_truth=True,
                    caller=assessor.name,
                    evidence=f"assessment-support:{assessor.name}:{item.entry_id}",
                )
            elif propositions_conflict(report.subject, item.proposition, spoken_likely):
                adjust_social_weight_for_truth_event(
                    observer,
                    item.source,
                    report.subject,
                    told_truth=False,
                    caller=assessor.name,
                    evidence=f"assessment-refute:{assessor.name}:{item.entry_id}",
                )


def witness_weight_label(weight: int) -> str:
    if weight >= 5:
        return "verified good witness"
    if weight == 4:
        return "good witness"
    if weight == 3:
        return "steady witness"
    if weight == 2:
        return "uncertain witness"
    return "notorious liar"


def likely_assessment_proposition(
    state: LabyrinthState,
    assessor: Agent,
    subject: str,
    evidence: list[AssessmentEvidence],
    direct_evidence: list[str],
) -> str | None:
    return likely_assessment_proposition_from_scores(
        assessment_scores_by_proposition(state, assessor, subject, evidence, direct_evidence)
    )

def propositions_compatible(subject: str, left: str, right: str) -> bool:
    if left == right:
        return True
    left_norm = normalize_alias(left)
    right_norm = normalize_alias(right)
    if subject in left and subject in right:
        if "is safe" in left_norm and ("leads onward" in right_norm or "is exit" in right_norm):
            return True
        if "is safe" in right_norm and ("leads onward" in left_norm or "is exit" in left_norm):
            return True
    return False


def propositions_conflict(subject: str, left: str, right: str) -> bool:
    if propositions_compatible(subject, left, right):
        return False
    left_norm = normalize_alias(left)
    right_norm = normalize_alias(right)
    if is_cup_name(subject):
        if "is empty" in left_norm or "is empty" in right_norm:
            return left_norm != right_norm
        if "is safe" in left_norm and any(hazard in right_norm for hazard in ("is poison", "sleeping potion", "brings stupor")):
            return True
        if "is safe" in right_norm and any(hazard in left_norm for hazard in ("is poison", "sleeping potion", "brings stupor")):
            return True
        return left_norm != right_norm
    if is_door_name(subject):
        if "leads to peril" in left_norm and any(good in right_norm for good in ("is safe", "leads onward", "is exit")):
            return True
        if "leads to peril" in right_norm and any(good in left_norm for good in ("is safe", "leads onward", "is exit")):
            return True
        if "leads onward" in left_norm and "is exit" in right_norm:
            return False
        if "leads onward" in right_norm and "is exit" in left_norm:
            return False
        return left_norm != right_norm
    return left_norm != right_norm


def is_cup_name(subject: str) -> bool:
    return subject.endswith("Cup")


def is_door_name(subject: str) -> bool:
    return subject.endswith("Door")



def render_claim_assessment_claim(state: LabyrinthState, assessor: Agent, claim_subject: str, lie: bool) -> str:
    subject, proposition = claim_assessment_parts(claim_subject)
    canonical = canonical_claim_proposition(state, proposition, subject) or proposition
    report = build_assessment_report(state, assessor, subject)
    support_weight = claim_support_weight(report, canonical)
    oppose_weight = claim_oppose_weight(report, canonical)
    if lie:
        support_weight, oppose_weight = oppose_weight, support_weight
    subject_text = render_subject_name(state, subject)
    claim_text = render_proposition(canonical)
    lines = [f"{render_agent(assessor)} assesses the claim that {claim_text}:"]
    evidence_sentence = render_assessment_evidence_sentence(state, report)
    if evidence_sentence:
        lines.append(evidence_sentence)
    if support_weight or oppose_weight:
        lines.append(
            f"by weight, the claim has {render_weight_word(support_weight)} support and {render_weight_word(oppose_weight)} against."
        )
    else:
        lines.append(f"they have not heard enough about {subject_text} to weigh the claim.")
    if support_weight > oppose_weight:
        confidence = "strongly likely true" if support_weight >= oppose_weight + 5 else ("likely true" if support_weight >= oppose_weight + 2 else "barely likely true")
        supporters = sources_for_proposition(report.evidence, canonical, subject)
        if supporters:
            lines.append(f"{confidence}, unless {render_source_list(state, supporters)} {render_are_is(supporters)} lying or badly wrong.")
        else:
            lines.append(f"{confidence}.")
    elif oppose_weight > support_weight:
        confidence = "strongly likely false" if oppose_weight >= support_weight + 5 else ("likely false" if oppose_weight >= support_weight + 2 else "barely likely false")
        opponents = sorted({item.source for item in report.evidence if propositions_conflict(subject, item.proposition, canonical)})
        if opponents:
            lines.append(f"{confidence}, unless {render_source_list(state, opponents)} {render_are_is(opponents)} lying or badly wrong.")
        else:
            lines.append(f"{confidence}.")
    else:
        lines.append("the testimony balances badly; this claim sits on the fence and makes everyone look at it.")
    return " ".join(lines)


def claim_support_weight(report: AssessmentReport, proposition: str) -> int:
    total = 0
    for score in report.scores:
        if propositions_compatible(report.subject, score.proposition, proposition):
            total += score.weight
    return total


def claim_oppose_weight(report: AssessmentReport, proposition: str) -> int:
    total = 0
    for score in report.scores:
        if propositions_conflict(report.subject, score.proposition, proposition):
            total += score.weight
    return total


def render_person_assessment_claim(state: LabyrinthState, assessor: Agent, person_subject: str, lie: bool) -> str:
    person = state.player if person_subject == state.player.name else state.claimants.get(person_subject)
    if person is None:
        return f"{render_agent(assessor)} assesses {render_topic(person_subject)}: no such witness holds still long enough to judge."
    rendered_person = render_agent(person)
    entries = claims_by_source_about_things(state, assessor, person_subject)
    supported_count, refuted_count, unknown_count = claim_audit_counts(entries)
    memory_line = person_assessment_memory_line(state, assessor, person_subject)
    lines = [f"{render_agent(assessor)} assesses {rendered_person}:"]
    reliability_line = person_reliability_line(assessor, rendered_person, supported_count, refuted_count, lie)
    if reliability_line:
        lines.append(reliability_line)
    if entries:
        bits = []
        if supported_count:
            bits.append(f"{render_count_word(supported_count)} supported claim{'' if supported_count == 1 else 's'}")
        if refuted_count:
            bits.append(f"{render_count_word(refuted_count)} refuted claim{'' if refuted_count == 1 else 's'}")
        if unknown_count:
            bits.append(f"{render_count_word(unknown_count)} untested claim{'' if unknown_count == 1 else 's'}")
        if bits:
            lines.append(f"in memory: {render_labyrinth_list(bits)}.")
        recent = recent_claim_summary(state, entries)
        if recent:
            lines.append(recent)
    else:
        lines.append("there are no useful claims from them in memory yet.")
    if memory_line:
        lines.append(memory_line)
    return " ".join(lines)


def person_reliability_line(assessor: Agent, rendered_person: str, supported_count: int, refuted_count: int, lie: bool) -> str:
    if not supported_count and not refuted_count:
        return f"{render_agent(assessor)} has no proven reliability record for {rendered_person} yet."
    if supported_count > refuted_count:
        label = "good witness" if supported_count >= refuted_count + 2 else "tentatively reliable witness"
    elif refuted_count > supported_count:
        label = "notorious liar" if refuted_count >= supported_count + 2 else "doubtful witness"
    else:
        label = "uncertain witness"
    if lie:
        label = opposite_witness_label(label)
    return f"from tested memory, {render_agent(assessor)} weighs {rendered_person} as a {label}."


def opposite_witness_label(label: str) -> str:
    if label in {"verified good witness", "good witness"}:
        return "notorious liar"
    if label == "notorious liar":
        return "good witness"
    if label == "steady witness":
        return "uncertain witness"
    return "steady witness"


def claims_by_source_about_things(state: LabyrinthState, assessor: Agent, source: str) -> list[MemoryEntry]:
    entries = []
    for entry in assessor.memory.entries:
        if entry.source != source:
            continue
        if entry.kind not in {"heard_claim", "claim_made", "reported_claim"}:
            continue
        focus = claim_focus_subject(state, entry)
        if focus is None:
            continue
        entries.append(entry)
    return sorted(entries, key=lambda entry: entry.sequence, reverse=True)


def claim_audit_counts(entries: list[MemoryEntry]) -> tuple[int, int, int]:
    supported_count = refuted_count = unknown_count = 0
    for entry in entries:
        bucket = audit_bucket(entry.current_rating)
        if bucket == "supported":
            supported_count += 1
        elif bucket == "refuted":
            refuted_count += 1
        else:
            unknown_count += 1
    return supported_count, refuted_count, unknown_count


def recent_claim_summary(state: LabyrinthState, entries: list[MemoryEntry]) -> str:
    usable = []
    for entry in entries[:3]:
        focus = claim_focus_subject(state, entry)
        if focus is None:
            continue
        proposition = canonical_claim_proposition(state, entry.proposition or entry.text, focus) or (entry.proposition or entry.text)
        usable.append(render_proposition(proposition))
    if not usable:
        return ""
    return "recent claims from them include: " + render_labyrinth_list(usable) + "."


def person_assessment_memory_line(state: LabyrinthState, assessor: Agent, person_subject: str) -> str:
    entries = relevant_memory_entries(assessor, person_subject, person_subject)
    answer = answer_from_person_memory(state, assessor, person_subject, entries)
    if not answer:
        return ""
    return answer.rstrip(".") + "."


def render_witnesses_assessment_claim(state: LabyrinthState, assessor: Agent, lie: bool) -> str:
    witnesses = [agent for agent in present_agents(state) if agent.name != assessor.name]
    if state.player.alive and state.player.room_index == agent_room_index(state, assessor) and assessor.name != state.player.name:
        witnesses.insert(0, state.player)
    if not witnesses:
        return f"{render_agent(assessor)} assesses the witnesses: there is no one else here to weigh."
    parts = []
    for witness in witnesses[:6]:
        label = witness_weight_label(witness_weight_for_subject(state, assessor, witness.name, "*"))
        if lie:
            label = opposite_witness_label(label)
        parts.append(render_witness_label(state, witness, label))
    return f"{render_agent(assessor)} assesses the witnesses: " + render_labyrinth_list(parts) + "."


def render_witness_label(state: LabyrinthState, witness: Agent, label: str) -> str:
    if witness.name == state.player.name:
        return f"you are a {label}"
    return f"{render_agent(witness)} is a {label}"


def render_count_word(count: int) -> str:
    if count <= 0:
        return "zero"
    if count == 1:
        return "one"
    if count == 2:
        return "two"
    if count == 3:
        return "three"
    if count == 4:
        return "four"
    if count == 5:
        return "five"
    return "a heap of"

def render_assessment_claim(state: LabyrinthState, assessor: Agent, report: AssessmentReport, lie: bool) -> str:
    subject = report.subject
    subject_text = render_subject_name(state, subject)
    if not report.evidence and not report.direct_evidence:
        if lie:
            wrong = default_false_assessment(state, subject)
            return f"{render_agent(assessor)} assesses {subject_text}: likely {render_proposition(wrong)}."
        return f"{render_agent(assessor)} assesses {subject_text}: they have not heard enough claims to judge it."

    likely = report.likely
    if lie:
        likely = distorted_assessment_proposition(state, report)

    lines: list[str] = [f"{render_agent(assessor)} assesses {subject_text}:"]
    reputation_sentence = render_assessment_reputation_sentence(state, report)
    if reputation_sentence:
        lines.append(reputation_sentence)
    evidence_sentence = render_assessment_evidence_sentence(state, report)
    if evidence_sentence:
        lines.append(evidence_sentence)
    weight_sentence = render_assessment_weight_sentence(state, report, likely, lie=lie)
    if weight_sentence:
        lines.append(weight_sentence)
    if likely is None:
        lines.append("the claims do not point anywhere stable yet.")
    else:
        support_sources = sources_for_proposition(report.evidence, likely, report.subject)
        confidence = render_assessment_confidence(report, likely)
        if support_sources:
            lines.append(f"{confidence} {render_proposition(likely)}, unless {render_source_list(state, support_sources)} {render_are_is(support_sources)} lying or badly wrong.")
        else:
            lines.append(f"{confidence} {render_proposition(likely)}.")
        contradiction = render_assessment_contradiction(state, report, likely)
        if contradiction:
            lines.append(contradiction)
    return " ".join(lines)


def render_assessment_reputation_sentence(state: LabyrinthState, report: AssessmentReport) -> str:
    if not report.source_weights:
        return ""
    notable = [item for item in report.source_weights if item.label in {"verified good witness", "good witness", "notorious liar"}]
    if not notable:
        return ""
    parts = [f"{render_source_name(state, item.source)} is a {item.label}" for item in notable]
    return "the witness weights are: " + render_labyrinth_list(parts) + "."


def render_assessment_weight_sentence(state: LabyrinthState, report: AssessmentReport, likely: str | None, lie: bool = False) -> str:
    if not report.scores:
        return ""
    if lie and likely is not None:
        if len(report.scores) == 1:
            return f"the weighted testimony points toward {render_proposition(likely)}."
        return f"by weight, {render_proposition(likely)} comes out heaviest."
    if len(report.scores) == 1:
        score = report.scores[0]
        return f"the weighted testimony only names {render_proposition(score.proposition)}."
    top_items = list(report.scores[:3])
    parts = [f"{render_proposition(item.proposition)} has {render_weight_word(item.weight)} weight" for item in top_items]
    return "by weight, " + render_labyrinth_list(parts) + "."


def render_weight_word(weight: int) -> str:
    if weight <= 1:
        return "one"
    if weight == 2:
        return "two"
    if weight == 3:
        return "three"
    if weight == 4:
        return "four"
    if weight == 5:
        return "five"
    if weight <= 7:
        return "six or seven"
    return "a heap of"


def render_assessment_confidence(report: AssessmentReport, likely: str) -> str:
    scores = list(report.scores)
    if not scores:
        return "likely"
    top = next((score.weight for score in scores if score.proposition == likely), scores[0].weight)
    rivals = [score.weight for score in scores if score.proposition != likely]
    second = max(rivals) if rivals else 0
    if top >= second + 5:
        return "strongly likely"
    if top >= second + 2:
        return "likely"
    return "barely likely"


def render_assessment_evidence_sentence(state: LabyrinthState, report: AssessmentReport) -> str:
    if report.direct_evidence:
        return "body evidence says " + render_labyrinth_list([render_proposition(prop) for prop in report.direct_evidence]) + "."
    grouped: dict[str, dict[str, int]] = {}
    for item in report.evidence:
        counts = grouped.setdefault(item.proposition, {})
        counts[item.source] = counts.get(item.source, 0) + 1
    if not grouped:
        return ""
    parts = []
    for proposition, source_counts in sorted(grouped.items(), key=lambda pair: render_proposition(pair[0])):
        parts.append(f"{render_source_claim_counts(state, source_counts)} that {render_proposition(proposition)}")
    audit = render_assessment_audit_sentence(report.evidence)
    if audit:
        parts.append(audit)
    return render_labyrinth_list(parts) + "."


def render_assessment_audit_sentence(evidence: tuple[AssessmentEvidence, ...]) -> str:
    counts = {"supported": 0, "refuted": 0, "untested": 0}
    for item in evidence:
        if not item.initial_rating:
            continue
        bucket = audit_bucket(item.current_rating)
        counts[bucket] = counts.get(bucket, 0) + 1
    bits: list[str] = []
    if counts["supported"]:
        count = counts["supported"]
        bits.append(f"{render_count_word(count)} claim{'' if count == 1 else 's'} later proved true")
    if counts["refuted"]:
        count = counts["refuted"]
        bits.append(f"{render_count_word(count)} claim{'' if count == 1 else 's'} later failed")
    if counts["untested"]:
        count = counts["untested"]
        bits.append(f"{render_count_word(count)} claim{'' if count == 1 else 's'} still untested")
    if not bits:
        return ""
    return render_labyrinth_list(bits)


def render_source_claim_counts(state: LabyrinthState, source_counts: dict[str, int]) -> str:
    singles = [source for source, count in source_counts.items() if count <= 1]
    repeated = [(source, count) for source, count in source_counts.items() if count > 1]
    if repeated:
        parts: list[str] = []
        if singles:
            parts.append(f"{render_source_list(state, sorted(singles))} {render_are_is_saying(singles)}")
        for source, count in sorted(repeated, key=lambda pair: render_source_name(state, pair[0])):
            parts.append(f"{render_source_says(state, source)} {render_times_word(count)}")
        return render_labyrinth_list(parts)
    sources = sorted(singles)
    return f"{render_source_list(state, sources)} {render_say_says(sources)}"


def render_are_is_saying(sources: list[str]) -> str:
    if len(set(sources)) == 1 and sources[0] != "You":
        return "says"
    return "say"


def render_source_says(state: LabyrinthState, source: str) -> str:
    if source == "You":
        return "you say"
    return f"{render_source_name(state, source)} says"

def render_times_word(count: int) -> str:
    if count == 2:
        return "twice"
    if count == 3:
        return "three times"
    if count == 4:
        return "four times"
    return "many times"


def render_assessment_contradiction(state: LabyrinthState, report: AssessmentReport, likely: str) -> str:
    opponents = sorted({item.source for item in report.evidence if propositions_conflict(report.subject, item.proposition, likely)})
    if not opponents:
        return ""
    return f"that would make {render_source_list(state, opponents)} wrong or lying."


def sources_for_proposition(evidence: tuple[AssessmentEvidence, ...], proposition: str, subject: str) -> list[str]:
    return sorted({item.source for item in evidence if item.proposition == proposition or propositions_compatible(subject, item.proposition, proposition)})


def render_labyrinth_list(parts: list[str]) -> str:
    if not parts:
        return "no one"
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def render_source_list(state: LabyrinthState, sources: list[str] | tuple[str, ...]) -> str:
    rendered = [render_source_name(state, source) for source in sources]
    return render_labyrinth_list(rendered)


def render_say_says(sources: list[str]) -> str:
    return "says" if len(set(sources)) == 1 else "say"


def render_are_is(sources: list[str] | tuple[str, ...]) -> str:
    return "is" if len(set(sources)) == 1 else "are"

def distorted_assessment_proposition(state: LabyrinthState, report: AssessmentReport) -> str:
    if report.alternatives:
        return report.alternatives[lie_variant(report.subject + "assessment", len(report.alternatives))]
    return default_false_assessment(state, report.subject)


def default_false_assessment(state: LabyrinthState, subject: str) -> str:
    if is_cup_subject(state, subject):
        options = [
            f"{subject} is poison",
            f"{subject} is safe",
            f"{subject} grants haste",
            f"{subject} is sleeping potion",
        ]
    elif is_door_subject(state, subject):
        options = [
            f"{subject} leads to peril",
            f"{subject} leads onward",
            f"{subject} is safe",
        ]
    else:
        options = [f"{subject} is unreliable", f"{subject} is trusted"]
    return options[lie_variant(subject + "false", len(options))]

def resolve_liars_ask(state: LabyrinthState, asker: Agent, question: LiarsAsk) -> list[str]:
    truthful_claim, distorted_claim = evaluate_liars_claim_pair(question)
    claim = speak_claim(question.target, truthful_claim, distorted_claim)
    ask_line = (
        f"you ask {render_agent(question.target)} to solve a liars puzzle"
        if asker.name == "You"
        else f"{render_agent_verb(asker, 'ask')} {render_agent(question.target)} to solve a liars puzzle"
    )

    record_room_event(
        state,
        state.room_index,
        kind="action",
        text=ask_line + ".",
        source=asker.name,
        subject=f"Liars:{question.raw_text}",
        proposition=f"{asker.name} asked {question.target.name} to solve a liars puzzle",
        certainty="seen directly",
        subjects=["liars", "liar puzzle", f"Liars:{question.raw_text}"],
    )
    record_room_event(
        state,
        state.room_index,
        kind="liars_claim",
        text=claim,
        source=question.target.name,
        subject=f"Liars:{question.raw_text}",
        proposition=claim,
        certainty="spoken",
        subjects=["liars", "liar puzzle", f"Liars:{question.raw_text}"],
    )
    if claim != truthful_claim:
        remember(
            state,
            question.target,
            kind="private_calculation",
            text=truthful_claim,
            source=question.target.name,
            subject=f"Liars:{question.raw_text}",
            proposition=truthful_claim,
            certainty="computed",
            subjects=[f"Liars:{question.raw_text}"],
        )
    asker.observances.append(f"Liars puzzle: {question.raw_text}")
    question.target.observances.append(f"Liars puzzle: {question.raw_text}")
    lines = [ask_line, claim]
    lines.extend(maybe_tire_fixed_witness(state, question.target))
    return lines


def evaluate_liars_claim_pair(question: LiarsAsk) -> tuple[str, str]:
    puzzle = parse_liars(question.puzzle_text)
    survivors = surviving_worlds(puzzle)
    truthful = f"{render_agent(question.target)} claims this liars puzzle is {summarize_liars_worlds(puzzle, survivors)}."
    distorted = f"{render_agent(question.target)} claims this liars puzzle is {distort_liars_worlds(puzzle, survivors)}."
    return truthful, distorted


def summarize_liars_worlds(puzzle: Any, survivors: list[dict[str, str]]) -> str:
    if not survivors:
        return "contradictory: no possible worlds"
    if len(survivors) == 1:
        return f"forced: {render_world(survivors[0], puzzle.people)}"
    worlds = "; ".join(render_world(world, puzzle.people) for world in survivors[:THREE_VALUE])
    if len(survivors) > THREE_VALUE:
        worlds += "; and more"
    return f"ambiguous: {worlds}"


def distort_liars_worlds(puzzle: Any, survivors: list[dict[str, str]]) -> str:
    all_worlds = enumerate_worlds(puzzle.people)
    rejected = [world for world in all_worlds if world not in survivors]
    if len(survivors) == 1 and rejected:
        return f"forced: {render_world(rejected[0], puzzle.people)}"
    if len(survivors) == 1:
        return "ambiguous"
    if not survivors:
        return "ambiguous"
    if rejected:
        return f"forced: {render_world(rejected[0], puzzle.people)}"
    return "contradictory: no possible worlds"


THREE_VALUE = 3


def resolve_goblet_ask(state: LabyrinthState, asker: Agent, question: GobletAsk) -> list[str]:
    truthful_claim, distorted_claim = evaluate_goblet_claim_pair(question)
    claim = speak_claim(question.target, truthful_claim, distorted_claim)
    ask_line = (
        f"you ask {render_agent(question.target)} {question.mode} {question.expression}"
        if asker.name == "You"
        else f"{render_agent_verb(asker, 'ask')} {render_agent(question.target)} {question.mode} {question.expression}"
    )

    record_room_event(
        state,
        state.room_index,
        kind="action",
        text=ask_line + ".",
        source=asker.name,
        subject=f"Goblet:{question.expression}",
        proposition=f"{asker.name} asked {question.target.name} {question.mode} {question.expression}",
        certainty="seen directly",
    )
    record_room_event(
        state,
        state.room_index,
        kind="goblet_claim",
        text=claim,
        source=question.target.name,
        subject=f"Goblet:{question.expression}",
        proposition=claim,
        certainty="spoken",
    )
    if claim != truthful_claim:
        remember(
            state,
            question.target,
            kind="private_calculation",
            text=truthful_claim,
            source=question.target.name,
            subject=f"Goblet:{question.expression}",
            proposition=truthful_claim,
            certainty="computed",
            subjects=[f"Goblet:{question.expression}"],
        )
    question.target.observances.append(f"Goblet question: {question.expression}")
    lines = [ask_line, claim]
    lines.extend(maybe_tire_fixed_witness(state, question.target))
    return lines


def evaluate_goblet_ask(question: GobletAsk) -> str:
    truthful_claim, _ = evaluate_goblet_claim_pair(question)
    return truthful_claim


def evaluate_goblet_claim_pair(question: GobletAsk) -> tuple[str, str]:
    if question.mode == "what":
        answer = evaluate_goblet_expression(question.expression)
        truthful = f"{render_agent(question.target)} claims {question.expression} is {answer}."
        distorted = f"{render_agent(question.target)} claims {question.expression} is not {answer}."
        return truthful, distorted

    answer = evaluate_goblet_proposition(question.expression)
    truthful = f"{render_agent(question.target)} claims {answer}."
    distorted = f"{render_agent(question.target)} claims {distort_goblet_proposition_answer(answer)}."
    return truthful, distorted


def evaluate_goblet_proposition(expression: str) -> str:
    normalized = expression.lower().strip()
    if normalized.endswith(" is prime"):
        phrase = expression[: -len(" is prime")].strip()
        return prime_expression(phrase)
    if normalized.endswith(" is not prime"):
        phrase = expression[: -len(" is not prime")].strip()
        result = prime_expression(phrase)
        if " is not prime" in result:
            return result
        return f"{render_prime_phrase(phrase)} is prime"

    result = relation_expression(expression)
    if result == "true":
        return expression
    if result == "false":
        return f"it is false that {expression}"
    return f"{expression}: {result}"


def evaluate_goblet_expression(expression: str) -> str:
    lowered = expression.lower()
    if " plus " in lowered or " minus " in lowered:
        from .arithmetic import arithmetic_expression
        return arithmetic_expression(expression)
    if " divided by " in lowered:
        return divide_expression(expression)
    if " times " in lowered or " multiplied by " in lowered:
        return multiply_expression(expression)
    if any(marker in lowered for marker in (
        " is greater than ",
        " is less than ",
        " is equal to ",
        " equals ",
        " is at least ",
        " is at most ",
    )):
        return relation_expression(expression)
    if lowered.endswith(" is prime") or lowered.endswith(" is not prime"):
        return evaluate_goblet_proposition(expression)
    raise ValueError("expected prime, arithmetic, division, multiplication, or comparison")


def render_prime_phrase(phrase: str) -> str:
    return phrase.lower().strip()


def resolve_world_ask(state: LabyrinthState, asker: Agent, question: WorldAsk) -> list[str]:
    claim = answer_world_subject(state, question.target, question.subject, question.proposition, question.expression)
    question_text = (
        f"you ask {render_agent(question.target)} if {question.expression}"
        if asker.name == "You"
        else f"{render_agent_verb(asker, 'ask')} {render_agent(question.target)} if {question.expression}"
    )
    room_index = state.room_index
    record_room_event(
        state,
        room_index,
        kind="action",
        text=question_text + ".",
        source=asker.name,
        subject=question.target.name,
        proposition=f"{asker.name} asked {question.target.name} if {question.proposition}",
        certainty="seen directly",
    )
    record_claim_event(state, question.target, claim, room_index)
    asker.observances.append(f"{asker.name} asked {question.target.name} if {question.proposition}")
    question.target.observances.append(f"{asker.name} asked {question.target.name} if {question.proposition}")
    asker.observances.append(claim)
    lines = [question_text, claim]
    lines.extend(maybe_tire_fixed_witness(state, question.target))
    return lines


def resolve_ask(state: LabyrinthState, asker: Agent, command: str) -> list[str]:
    parsed = parse_ask_command_for_agent(state, asker, command)
    if isinstance(parsed, str):
        return [parsed]
    target, topic, subject = parsed
    if target.sleeping:
        if asker.name == "You":
            return [f"{render_agent(target)} is sleeping; slap them if you need them awake"]
        return [f"{render_agent_verb(asker, 'ask')} {render_agent(target)}, but {render_agent(target)} is sleeping and does not answer"]

    claim = answer_world_subject(state, target, subject, raw_topic=topic)

    rendered_topic = render_ask_topic(state, topic, subject)
    question_text = f"{render_agent(asker)} asked {render_agent(target)} about {rendered_topic}."
    claim_text = claim

    room_index = state.room_index
    record_room_event(
        state,
        room_index,
        kind="action",
        text=question_text,
        source=asker.name,
        subject=target.name,
        proposition=f"{asker.name} asked {target.name} about {subject}",
        certainty="seen directly",
    )
    record_claim_event(state, target, claim_text, room_index)

    observance = f"{asker.name} asked {target.name} about {subject}"
    asker.observances.append(observance)
    target.observances.append(observance)
    asker.observances.append(claim)

    lines = ([f"you ask {render_agent(target)} about {rendered_topic}", claim]
             if asker.name == "You"
             else [f"{render_agent_verb(asker, 'ask')} {render_agent(target)} about {rendered_topic}", claim])
    lines.extend(maybe_tire_fixed_witness(state, target))
    return lines


def render_ask_topic(state: LabyrinthState, topic: str, subject: str) -> str:
    if is_health_topic(topic):
        return "health"
    return render_name(subject) if has_camel_boundary(subject) else render_topic(subject)


def answer_world_subject(
    state: LabyrinthState,
    target: Agent,
    subject: str,
    proposition: str | None = None,
    raw_topic: str | None = None,
) -> str:
    material_claim = material_identity_claim(state, target, subject, proposition)
    if material_claim is not None:
        return speak_claim(target, material_claim, distort_world_claim(state, target, material_claim, subject))

    subject_agent = state.claimants.get(subject)
    if subject_agent is not None:
        person_answer = answer_person_subject(state, target, subject_agent, proposition, raw_topic)
        if person_answer is not None:
            return speak_claim(target, person_answer, distort_world_claim(state, target, person_answer, subject))

    memory_answer = answer_from_memory(state, target, subject)
    deck_answer = topic_relevant_round_claim(state, target, subject)
    if memory_answer:
        return speak_claim(target, memory_answer, distort_world_claim(state, target, memory_answer, subject))
    if deck_answer:
        return deck_answer
    return ignorance_claim(target, subject)


def answer_person_subject(
    state: LabyrinthState,
    target: Agent,
    subject_agent: Agent,
    proposition: str | None,
    raw_topic: str | None,
) -> str | None:
    rendered_subject = render_agent(subject_agent)
    if raw_topic is not None and is_health_topic(raw_topic):
        return f"{render_agent(target)} claims {rendered_subject} looks {render_condition_word(subject_agent)}."

    if proposition is not None:
        status_answer = answer_person_status_claim(state, target, subject_agent, proposition)
        if status_answer is not None:
            return status_answer

    if subject_agent.alive and subject_agent.room_index == agent_room_index(state, target):
        return f"{render_agent(target)} claims {rendered_subject} looks {render_condition_word(subject_agent)}."

    memory_answer = answer_from_memory(state, target, subject_agent.name)
    if memory_answer:
        return memory_answer

    return None


def answer_person_status_claim(state: LabyrinthState, target: Agent, subject_agent: Agent, proposition: str) -> str | None:
    normalized = normalize_alias(proposition)
    rendered_subject = render_agent(subject_agent)
    if "poison" in normalized:
        return f"{render_agent(target)} claims {rendered_subject} is {'poisoned' if subject_agent.poisoned else 'not poisoned'}."
    if "sleep" in normalized or "asleep" in normalized or "drowsy" in normalized:
        return f"{render_agent(target)} claims {rendered_subject} is {'sleeping' if subject_agent.sleeping else 'not sleeping'}."
    if "dead" in normalized or "alive" in normalized or "gone" in normalized:
        return f"{render_agent(target)} claims {rendered_subject} is {'alive' if subject_agent.alive else 'gone'}."
    if "trusted" in normalized or "untrusted" in normalized or "unreliable" in normalized or "liar" in normalized or "lies" in normalized:
        memory_answer = answer_from_memory(state, target, subject_agent.name)
        if memory_answer is not None:
            return memory_answer
    return None


def material_identity_claim(state: LabyrinthState, target: Agent, subject: str, proposition: str | None) -> str | None:
    if proposition is None:
        return None
    material = subject_material(subject)
    if material is None:
        return None
    asked_material = material_from_proposition(proposition)
    if asked_material is None:
        return None
    rendered_subject = render_subject_name(state, subject)
    if asked_material == material:
        return f"{render_agent(target)} claims {rendered_subject} is {material}."
    return f"{render_agent(target)} claims {rendered_subject} is not {asked_material}."


def material_from_proposition(proposition: str) -> str | None:
    normalized = normalize_alias(proposition)
    words = normalized.split()
    for material in MATERIAL_WORDS:
        if normalized.endswith(f" is {material}") or normalized.endswith(f" are {material}") or (
            "is" in words and words[-1] == material
        ):
            return material
    return None


def subject_material(subject: str) -> str | None:
    subject_words = normalize_alias(" ".join(words_from_name(subject))).split()
    for material in MATERIAL_WORDS:
        if material in subject_words:
            return material
    return None


MATERIAL_WORDS = {
    "ash", "bone", "brass", "copper", "flint", "glass", "gold", "iron",
    "oak", "pewter", "salt", "silver", "wax",
}


def render_subject_name(state: LabyrinthState, subject: str) -> str:
    if subject == WITNESSES_ASSESSMENT_SUBJECT:
        return "the witnesses"
    if is_claim_assessment_subject(subject):
        _, proposition = claim_assessment_parts(subject)
        return f"the claim that {render_proposition(proposition)}"
    if subject == state.player.name:
        return "you"
    agent = state.claimants.get(subject)
    if agent is not None:
        return render_agent(agent)
    if has_camel_boundary(subject):
        return render_name(subject)
    return render_topic(subject)


def speak_claim(agent: Agent, truthful_claim: str, distorted_claim: str | None = None) -> str:
    if next_claim_kind(agent) == LIE:
        return distorted_claim or generic_distorted_claim(agent, truthful_claim)
    return truthful_claim


def generic_distorted_claim(agent: Agent, claim: str) -> str:
    if "claims they know nothing useful" in claim:
        return claim
    if " claims " not in claim:
        return f"{render_agent(agent)} claims it is false that {claim.rstrip('.')} .".replace(" .", ".")
    prefix, body = claim.split(" claims ", 1)
    body = body.rstrip(".")
    if body.startswith("it is false that "):
        body = body.removeprefix("it is false that ")
        return f"{prefix} claims {body}."
    return f"{prefix} claims it is false that {body}."


def distort_goblet_proposition_answer(answer: str) -> str:
    stripped = answer.strip().rstrip(".")
    lower = stripped.lower()
    if lower.startswith("it is false that "):
        return stripped[len("it is false that "):]
    if lower.endswith(" is prime"):
        return stripped[: -len(" is prime")] + " is not prime"
    if lower.endswith(" is not prime"):
        return stripped[: -len(" is not prime")] + " is prime"
    if ":" in stripped:
        expression, result = stripped.split(":", 1)
        result = result.strip()
        if result.startswith("likely true"):
            return f"{expression}: likely false"
        if result.startswith("likely false"):
            return f"{expression}: likely true"
        if result == "unknown":
            return f"{expression}: known"
    return f"it is false that {stripped}"


def distort_world_claim(state: LabyrinthState, agent: Agent, claim: str, subject: str) -> str:
    if "claims they know nothing useful" in claim:
        return claim
    prefix = f"{render_agent(agent)} claims "
    if not claim.startswith(prefix):
        return richer_generic_distorted_claim(state, agent, claim, subject)
    body = claim[len(prefix):].rstrip(".")
    normalized = normalize_alias(body)

    source_lie = distort_reported_source_claim(state, prefix, body, subject)
    if source_lie is not None:
        return source_lie

    if subject in state.claimants or subject == state.player.name:
        subject_lie = distort_person_claim(state, agent, prefix, normalized, subject)
        if subject_lie is not None:
            return subject_lie

    if is_cup_subject(state, subject):
        cup_lie = distort_cup_claim(state, agent, prefix, normalized, subject)
        if cup_lie is not None:
            return cup_lie

    if is_door_subject(state, subject):
        door_lie = distort_door_claim(state, agent, prefix, normalized, subject)
        if door_lie is not None:
            return door_lie

    if "was refuted" in normalized:
        return claim.replace(" was refuted", " seems true")
    if "seems true" in normalized:
        return claim.replace(" seems true", " was refuted")
    if "testing whether" in normalized:
        return claim
    return richer_generic_distorted_claim(state, agent, claim, subject)


def richer_generic_distorted_claim(state: LabyrinthState, agent: Agent, claim: str, subject: str) -> str:
    prefix = f"{render_agent(agent)} claims "
    if is_door_subject(state, subject):
        return distort_door_claim(state, agent, prefix, normalize_alias(claim), subject) or generic_distorted_claim(agent, claim)
    if is_cup_subject(state, subject):
        return distort_cup_claim(state, agent, prefix, normalize_alias(claim), subject) or generic_distorted_claim(agent, claim)
    if subject in state.claimants or subject == state.player.name:
        return distort_person_claim(state, agent, prefix, normalize_alias(claim), subject) or generic_distorted_claim(agent, claim)
    return generic_distorted_claim(agent, claim)


def distort_reported_source_claim(state: LabyrinthState, prefix: str, body: str, subject: str) -> str | None:
    visible_sources = known_agent_subjects(state, None, exclude={subject})
    for source in visible_sources:
        rendered_source = render_agent(state.claimants[source])
        marker = f"{rendered_source} said "
        if body.startswith(marker):
            other = choose_lie_subject([name for name in visible_sources if name != source], subject + body)
            if other is None:
                return None
            return f"{prefix}{render_agent(state.claimants[other])} said {body[len(marker):]}."
    if body.startswith("you said "):
        other = choose_lie_subject(visible_sources, subject + body)
        if other is None:
            return None
        return f"{prefix}{render_agent(state.claimants[other])} said {body[len('you said '):]}."
    return None


def distort_person_claim(state: LabyrinthState, agent: Agent, prefix: str, normalized: str, subject: str) -> str | None:
    other = choose_lie_subject(known_agent_subjects(state, agent, exclude={subject}), subject + normalized + agent.name)
    rendered_subject = render_subject_name(state, subject)
    if "slap" in normalized:
        if other is not None:
            return f"{prefix}{render_agent(state.claimants[other])} slapped {rendered_subject}."
        return f"{prefix}{rendered_subject} was not slapped."
    if "push" in normalized or "pushed" in normalized:
        door = choose_lie_subject(all_door_subjects(state), subject + normalized + "door")
        if other is not None and door is not None:
            return f"{prefix}{render_agent(state.claimants[other])} pushed {rendered_subject} toward {render_name(door)}."
        return f"{prefix}{rendered_subject} went willingly."
    if "moved through" in normalized or "left through" in normalized or "went through" in normalized:
        door = choose_lie_subject(all_door_subjects(state), subject + normalized)
        if door is not None:
            return f"{prefix}{rendered_subject} moved through {render_name(door)}."
    if "not trusted" in normalized or "untrusted" in normalized or "unreliable" in normalized:
        return f"{prefix}{rendered_subject} is trusted."
    if "trusted" in normalized or "honest" in normalized:
        return f"{prefix}{rendered_subject} is not trusted."
    if "liar" in normalized or "lies" in normalized:
        return f"{prefix}{rendered_subject} is honest."
    if "poisoned" in normalized:
        return f"{prefix}{rendered_subject} is not poisoned."
    if "sleeping" in normalized or "asleep" in normalized:
        return f"{prefix}{rendered_subject} is not sleeping."
    if "here" in normalized and other is not None:
        return f"{prefix}{render_agent(state.claimants[other])} is here instead."
    if other is not None:
        return f"{prefix}{render_agent(state.claimants[other])} is worth asking about instead."
    return None


def distort_cup_claim(state: LabyrinthState, agent: Agent, prefix: str, normalized: str, subject: str) -> str | None:
    rendered = render_name(subject)
    wrong_cup = choose_lie_subject([cup for cup in all_cup_subjects(state) if cup != subject], subject + normalized + agent.name)
    focus = render_name(wrong_cup) if wrong_cup is not None and lie_variant(subject + normalized, 3) != 0 else rendered
    if "poison" in normalized:
        return f"{prefix}{focus} is safe."
    if "antidote" in normalized:
        return f"{prefix}{focus} is poison."
    if "elixir" in normalized or "restores" in normalized or "full health" in normalized:
        return f"{prefix}{focus} is poison."
    if "empty" in normalized:
        return f"{prefix}{focus} is full."
    if "full" in normalized:
        return f"{prefix}{focus} is empty."
    if "grants haste" in normalized or "haste" in normalized or "quick" in normalized:
        return f"{prefix}{focus} slows the drinker."
    if "sharpens truth" in normalized or "truth" in normalized or "clear" in normalized:
        return f"{prefix}{focus} dulls truth."
    if "stupor" in normalized or "slow" in normalized:
        return f"{prefix}{focus} grants haste."
    if "sleep" in normalized or "asleep" in normalized or "drowsy" in normalized:
        return f"{prefix}{focus} grants haste."
    if "safe" in normalized:
        return f"{prefix}{focus} is poison."
    if wrong_cup is not None:
        return f"{prefix}{focus} is the cup that matters."
    return None


def distort_door_claim(state: LabyrinthState, agent: Agent, prefix: str, normalized: str, subject: str) -> str | None:
    rendered = render_name(subject)
    wrong_door = choose_lie_subject([door for door in all_door_subjects(state) if door != subject], subject + normalized + agent.name)
    focus = render_name(wrong_door) if wrong_door is not None and lie_variant(subject + normalized, 3) != 0 else rendered
    if "leads to peril" in normalized or "unsafe" in normalized or "hungry" in normalized:
        return f"{prefix}{focus} is safe."
    if "safe" in normalized or "kind" in normalized:
        return f"{prefix}{focus} leads to peril."
    if "leads onward" in normalized or "advances" in normalized:
        if wrong_door is not None and focus != rendered:
            return f"{prefix}{focus} leads onward."
        return f"{prefix}{focus} leads to peril."
    if "exit" in normalized:
        if wrong_door is not None:
            return f"{prefix}{focus} is the exit."
        return f"{prefix}{focus} leads to peril."
    if wrong_door is not None:
        return f"{prefix}{focus} is the door to watch."
    return None


def known_agent_subjects(state: LabyrinthState, agent: Agent | None, exclude: set[str] | None = None) -> list[str]:
    excluded = exclude or set()
    room_index = agent_room_index(state, agent) if agent is not None else state.room_index
    names = {candidate.name for candidate in state.claimants.values() if candidate.alive and candidate.room_index == room_index}
    if agent is not None:
        for entry in agent.memory.entries:
            names.update(subject for subject in entry.subjects if subject in state.claimants)
    return sorted(name for name in names if name not in excluded)


def all_door_subjects(state: LabyrinthState) -> list[str]:
    return [door.name for room in state.rooms for door in room.doors.values()]


def all_cup_subjects(state: LabyrinthState) -> list[str]:
    return [cup.name for room in state.rooms for cup in room.cups.values()]


def choose_lie_subject(candidates: list[str], seed_text: str) -> str | None:
    if not candidates:
        return None
    ordered = sorted(candidates, key=normalize_alias)
    return ordered[lie_variant(seed_text, len(ordered))]


def lie_variant(seed_text: str, count: int) -> int:
    if count <= 0:
        return 0
    return sum(ord(char) for char in seed_text) % count


def resolve_tell(state: LabyrinthState, speaker: Agent, command: str) -> list[str]:
    parsed = parse_tell_command(state, command)
    if isinstance(parsed, str):
        return [parsed]
    if isinstance(parsed, TellInstruction):
        if parsed.target.stationary:
            return [f"{render_agent(parsed.target)} is a fixed witness and cannot take actions"]
        add_instruction_goal(state, speaker, parsed.target, parsed.action)
        text = f"{render_agent(speaker)} told {render_agent(parsed.target)} to {render_action(parsed.action)}."
        record_room_event(
            state,
            state.room_index,
            kind="instruction",
            text=text,
            source=speaker.name,
            subject=parsed.target.name,
            proposition=f"{speaker.name} told {parsed.target.name} to {parsed.action}",
            certainty="seen directly",
        )
        parsed.target.observances.append(f"{speaker.name} told {parsed.target.name} to {parsed.action}")
        return [f"you tell {render_agent(parsed.target)} to {render_action(parsed.action)}; {render_agent(parsed.target)} considers it"]

    if parsed.subject is None or parsed.proposition is None:
        return [f"{render_agent(parsed.target)} does not know how to use that. Tell them a claim about a known thing."]

    if speaker.name == "You":
        truth_error = validate_truth_bound_tell(state, parsed)
        if truth_error:
            return [truth_error]

    text = f"{render_agent(speaker)} told {render_agent(parsed.target)}: {parsed.message}."
    record_room_event(
        state,
        state.room_index,
        kind="reported_claim",
        text=text,
        source=speaker.name,
        subject=parsed.subject,
        proposition=parsed.proposition,
        certainty="reported",
    )
    parsed.target.observances.append(f"{speaker.name} said: {parsed.proposition}")
    return [f"you tell {render_agent(parsed.target)} {parsed.message}; {render_agent(parsed.target)} remembers this"]


def add_instruction_goal(state: LabyrinthState, speaker: Agent, target: Agent, action: str) -> None:
    state.goal_sequence += 1
    subject = action_subject(action) or target.name
    target.goals.insert(0, Goal(
        id=f"goal-{state.goal_sequence}",
        action=action,
        subject=subject,
        reason=f"instruction from {speaker.name}",
        hypothesis_id=None,
        created_turn=render_number(state.round_number),
    ))

def resolve_agent_action(state: LabyrinthState, agent: Agent, intention: str) -> list[str]:
    if intention in agent.tried_actions and not should_repeat_action(state, agent, intention):
        mark_goal_attempted(agent, intention, "blocked")
        recovery_action = create_recovery_goal_action(state, agent, intention)
        if recovery_action is not None and recovery_action != intention:
            return resolve_agent_action(state, agent, recovery_action)
        return [f"{agent.name} remembers trying to {render_action(intention)} and hesitates"]
    agent.tried_actions.add(intention)
    mark_goal_attempted(agent, intention, "testing")
    if intention.startswith("move "):
        return resolve_move(state, agent, intention.removeprefix("move ").strip())
    if intention.startswith("sip "):
        return resolve_sip(state, agent, intention.removeprefix("sip ").strip())
    if intention.startswith("ask "):
        return resolve_ask(state, agent, intention)
    return [f"{agent.name} hesitates"]


def should_repeat_action(state: LabyrinthState, agent: Agent, intention: str) -> bool:
    if intention.startswith("sip "):
        cup_name = intention.removeprefix("sip ").strip()
        cup, _ = resolve_cup_name(state, agent, cup_name)
        return cup is not None and not is_zero(cup.fifths) and not agent_knows_property(agent, cup.name, "is empty")
    if "exit" in " ".join(agent.observances).lower():
        return True
    return False


def resolve_move(state: LabyrinthState, agent: Agent, door_name: str) -> list[str]:
    room_index = agent_room_index(state, agent)
    room = state.rooms[room_index]
    door = room.doors.get(door_name)
    if door is None:
        return [f"{agent.name} cannot find {render_name(door_name)}"]

    action_text = f"{render_agent_verb(agent, 'move')} through {render_name(door.name)}"
    record_room_event(
        state,
        room_index,
        kind="action",
        text=action_text + ".",
        source=agent.name,
        subject=door.name,
        proposition=f"{agent.name} moved through {door.name}",
        certainty="seen directly",
    )

    if door.result == "peril":
        kill(agent)
        outcome_text = f"{render_name(door.name)} leads to peril; {render_agent_verb(agent, 'die')}"
        record_room_event(
            state,
            room_index,
            kind="outcome",
            text=outcome_text + ".",
            source=door.name,
            subject=door.name,
            proposition=f"{door.name} leads to peril",
            certainty="seen directly",
        )
        return [action_text, outcome_text]
    if door.result == "next":
        if agent.name == "You":
            state.room_index += 1
            agent.room_index = state.room_index
            outcome_text = "you press deeper into the labyrinth"
            record_room_event(
                state,
                room_index,
                kind="outcome",
                text=outcome_text + ".",
                source=door.name,
                subject=door.name,
                proposition=f"{door.name} leads onward",
                certainty="seen directly",
            )
            create_follow_goals_for_safe_move(state, agent, room_index, door)
            return [action_text, outcome_text]
        agent.room_index = min(agent.room_index + 1, len(state.rooms) - 1)
        record_room_event(
            state,
            room_index,
            kind="outcome",
            text=f"{render_agent(agent)} left through {render_name(door.name)}.",
            source=door.name,
            subject=door.name,
            proposition=f"{door.name} leads onward",
            certainty="seen directly",
        )
        create_follow_goals_for_safe_move(state, agent, room_index, door)
        return [action_text]
    if door.result == "exit":
        if agent.name == "You":
            state.escaped = True
            outcome_text = "you find the exit"
            record_room_event(
                state,
                room_index,
                kind="outcome",
                text=outcome_text + ".",
                source=door.name,
                subject=door.name,
                proposition=f"{door.name} is the exit",
                certainty="seen directly",
            )
            return [action_text, outcome_text]
        record_room_event(
            state,
            room_index,
            kind="outcome",
            text=f"{render_agent(agent)} found the exit and shouted back.",
            source=door.name,
            subject=door.name,
            proposition=f"{door.name} is the exit",
            certainty="seen directly",
        )
        create_follow_goals_for_safe_move(state, agent, room_index, door)
        return [f"{agent.name} finds the exit and shouts back"]
    return [action_text]


def create_follow_goals_for_safe_move(state: LabyrinthState, mover: Agent, room_index: int, door: Door) -> None:
    if door.result not in {"next", "exit"}:
        return
    action = f"move {door.name}"
    for observer in observers_in_room(state, room_index):
        if observer.name in {mover.name, "You"}:
            continue
        if observer.stationary or not observer.alive:
            continue
        if observer.room_index != room_index:
            continue
        if agent_knows_property(observer, door.name, "leads to peril"):
            continue
        if action in observer.tried_actions:
            continue
        existing = [goal for goal in observer.goals if goal.action == action and goal.status == "active"]
        if existing:
            continue
        state.goal_sequence += 1
        observer.goals.insert(0, Goal(
            id=f"goal-{state.goal_sequence}",
            action=action,
            subject=door.name,
            reason=f"follow {render_agent(mover)} through {render_name(door.name)} after no peril",
            hypothesis_id=None,
            created_turn=render_number(state.round_number),
        ))


def resolve_sip(state: LabyrinthState, agent: Agent, cup_name: str) -> list[str]:
    room_index = agent_room_index(state, agent)
    room = state.rooms[room_index]
    cup = room.cups.get(cup_name)
    if cup is None:
        return [f"{agent.name} cannot find {render_name(cup_name)}"]
    if is_zero(cup.fifths):
        text = f"{render_name(cup.name)} is empty"
        record_room_event(
            state,
            room_index,
            kind="outcome",
            text=text + ".",
            source=cup.name,
            subject=cup.name,
            proposition=f"{cup.name} is empty",
            certainty="seen directly",
        )
        return [text]

    action_text = f"{render_agent_verb(agent, 'sip')} {render_name(cup.name)}"
    record_room_event(
        state,
        room_index,
        kind="action",
        text=action_text + ".",
        source=agent.name,
        subject=cup.name,
        proposition=f"{agent.name} sipped {cup.name}",
        certainty="seen directly",
    )
    cup.fifths = decrement_count(cup.fifths)
    lines = [action_text]
    if cup.effect in ("poison", "venom"):
        agent.poisoned = True
        agent.poison_grace = True
        agent.poison_bites = ZERO
        agent.poison_runs_course = cup.effect == "poison"
        outcome_text = f"{render_name(cup.name)} is poison; {render_agent_verb(agent, 'become')} poisoned"
        record_room_event(
            state,
            room_index,
            kind="outcome",
            text=outcome_text + ".",
            source=cup.name,
            subject=cup.name,
            proposition=f"{cup.name} is poison",
            certainty="seen directly",
        )
        record_room_event(
            state,
            room_index,
            kind="outcome",
            text=f"{render_agent(agent)} is poisoned.",
            source=cup.name,
            subject=agent.name,
            proposition=f"{agent.name} is poisoned",
            certainty="seen directly",
        )
        lines.append(outcome_text)
    elif cup.effect == "antidote":
        if agent.poisoned:
            clear_poison(agent)
            if agent.name == "You":
                outcome_text = f"{render_name(cup.name)} is antidote; you are no longer poisoned"
            else:
                outcome_text = f"{render_name(cup.name)} is antidote; {agent.name} is no longer poisoned"
            record_room_event(state, room_index, "outcome", outcome_text + ".", cup.name, cup.name, f"{cup.name} is antidote", "seen directly")
            record_room_event(state, room_index, "outcome", f"{render_agent(agent)} is no longer poisoned.", cup.name, agent.name, f"{agent.name} is not poisoned", "seen directly")
        else:
            outcome_text = f"{render_name(cup.name)} is antidote; {render_agent_verb(agent, 'steady')}"
            record_room_event(state, room_index, "outcome", outcome_text + ".", cup.name, cup.name, f"{cup.name} is antidote", "seen directly")
        lines.append(outcome_text)
    elif cup.effect == "elixir":
        was_poisoned = agent.poisoned
        agent.hp = agent.max_hp
        clear_poison(agent)
        if agent.name == "You":
            if was_poisoned:
                outcome_text = f"{render_name(cup.name)} is elixir; you are restored to full health and no longer poisoned"
            else:
                outcome_text = f"{render_name(cup.name)} is elixir; you are restored to full health"
        else:
            if was_poisoned:
                outcome_text = f"{render_name(cup.name)} is elixir; {agent.name} is restored to full health and no longer poisoned"
            else:
                outcome_text = f"{render_name(cup.name)} is elixir; {agent.name} is restored to full health"
        record_room_event(state, room_index, "outcome", outcome_text + ".", cup.name, cup.name, f"{cup.name} is elixir", "seen directly")
        record_room_event(state, room_index, "outcome", f"{render_agent(agent)} is restored to full health.", cup.name, agent.name, f"{agent.name} has full health", "seen directly")
        if was_poisoned:
            record_room_event(state, room_index, "outcome", f"{render_agent(agent)} is no longer poisoned.", cup.name, agent.name, f"{agent.name} is not poisoned", "seen directly")
        lines.append(outcome_text)
    elif cup.effect == "sleep":
        start_sleep(agent, ONE)
        outcome_text = f"{render_name(cup.name)} is sleeping potion; {render_agent_verb(agent, 'fall')} asleep"
        record_room_event(state, room_index, "outcome", outcome_text + ".", cup.name, cup.name, f"{cup.name} is sleeping potion", "seen directly")
        record_room_event(state, room_index, "outcome", f"{render_agent(agent)} is sleeping.", cup.name, agent.name, f"{agent.name} is sleeping", "seen directly")
        lines.append(outcome_text)
        if agent.name == "You":
            # Drinking sleep ends the rest of the current player phase. The
            # next player phase is skipped by resolve_sleep_phase, then the
            # player wakes.
            state.player_turns_taken = decrement_count(state.player_turn_budget) if not is_zero(state.player_turn_budget) else ZERO
    elif cup.effect == "haste":
        agent.speed = increment_count(agent.speed)
        outcome_text = f"{render_name(cup.name)} grants haste; {render_agent_verb(agent, 'feel')} quick next round"
        record_room_event(state, room_index, "outcome", outcome_text + ".", cup.name, cup.name, f"{cup.name} grants haste", "seen directly")
        lines.append(outcome_text)
    elif cup.effect == "truth":
        set_lie_rate(agent, lie_rate_fraction(ZERO))
        agent.truth_rate = "high"
        agent.truth_bound = True
        lie_profile = "always tell the truth" if agent.name == "You" else render_lie_profile(agent.lie_rate)
        outcome_text = (
            f"{render_name(cup.name)} sharpens truth; "
            f"{render_agent_verb(agent, 'seem')} clearer and {lie_profile}"
        )
        record_room_event(state, room_index, "outcome", outcome_text + ".", cup.name, cup.name, f"{cup.name} sharpens truth", "seen directly")
        lines.append(outcome_text)
    elif cup.effect == "stupor":
        outcome_text = f"{render_name(cup.name)} brings stupor; {render_agent_verb(agent, 'slow')}"
        record_room_event(state, room_index, "outcome", outcome_text + ".", cup.name, cup.name, f"{cup.name} brings stupor", "seen directly")
        lines.append(outcome_text)
    if is_zero(cup.fifths):
        empty_text = f"{render_name(cup.name)} is empty"
        record_room_event(state, room_index, "outcome", empty_text + ".", cup.name, cup.name, f"{cup.name} is empty", "seen directly")
        lines.append(empty_text)
    return lines




def start_sleep(agent: Agent, duration: WordNumber) -> None:
    agent.sleeping = True
    agent.sleep_turns_remaining = duration


def wake_agent(state: LabyrinthState, agent: Agent, room_index: int | None = None) -> None:
    agent.sleeping = False
    agent.sleep_turns_remaining = ZERO
    if room_index is None:
        room_index = agent_room_index(state, agent)
    record_room_event(
        state,
        room_index,
        kind="outcome",
        text=f"{render_agent(agent)} wakes.",
        source="sleep",
        subject=agent.name,
        proposition=f"{agent.name} is not sleeping",
        certainty="seen directly",
    )


def fixed_witness_internal_sleep_duration(agent: Agent) -> WordNumber:
    # Stationary witnesses need to remain unavailable for at least one visible
    # player round after the question that tired them out. Advance-round ticking
    # happens immediately after most actions, so add one hidden tick.
    return increment_count(agent.fixed_sleep_duration)


def maybe_tire_fixed_witness(state: LabyrinthState, agent: Agent) -> list[str]:
    if not agent.stationary or not agent.alive or agent.sleeping:
        return []
    agent.fixed_question_count = increment_count(agent.fixed_question_count)
    if count_greater_than(agent.fixed_question_limit, agent.fixed_question_count):
        return []
    agent.fixed_question_count = ZERO
    start_sleep(agent, fixed_witness_internal_sleep_duration(agent))
    room_index = agent_room_index(state, agent)
    text = f"{render_agent(agent)} has answered enough questions and goes to sleep"
    record_room_event(
        state,
        room_index,
        kind="outcome",
        text=text + ".",
        source="sleep",
        subject=agent.name,
        proposition=f"{agent.name} is sleeping",
        certainty="seen directly",
    )
    return [text]


def tick_stationary_sleepers(state: LabyrinthState) -> None:
    for agent in state.claimants.values():
        if not agent.stationary or not agent.sleeping or not agent.alive:
            continue
        if agent.name in state.sleep_tick_suppressed:
            state.sleep_tick_suppressed.discard(agent.name)
            continue
        if not is_zero(agent.sleep_turns_remaining):
            agent.sleep_turns_remaining = decrement_count(agent.sleep_turns_remaining)
        if is_zero(agent.sleep_turns_remaining):
            wake_agent(state, agent, agent_room_index(state, agent))


def resolve_slap_sleeping_agent(state: LabyrinthState, target: Agent) -> list[str]:
    if target.stationary and count_greater_than(target.sleep_turns_remaining, ONE):
        target.sleep_turns_remaining = decrement_count(target.sleep_turns_remaining)
        state.sleep_tick_suppressed.add(target.name)
        text = f"you slap {render_agent(target)}; {render_agent(target)} sinks deeper into sleep and does not wake"
        record_room_event(
            state,
            state.room_index,
            kind="outcome",
            text=text + ".",
            source="sleep",
            subject=target.name,
            proposition=f"{target.name} is sleeping",
            certainty="seen directly",
        )
        return [text]
    wake_agent(state, target, state.room_index)
    return [f"you slap {render_agent(target)} awake"]

def all_living_agents(state: LabyrinthState) -> list[Agent]:
    agents = [state.player]
    agents.extend(state.claimants.values())
    return [agent for agent in agents if agent.alive]


def resolve_sleep_phase(state: LabyrinthState, agent: Agent) -> list[str]:
    if not agent.sleeping or not agent.alive:
        return []
    room_index = agent_room_index(state, agent)
    if agent.name == "You":
        text = "you sleep through the round"
        state.player_turns_taken = state.player_turn_budget
    else:
        text = f"{render_agent(agent)} sleeps and cannot act"
    record_room_event(
        state,
        room_index,
        kind="outcome",
        text=text + ".",
        source="sleep",
        subject=agent.name,
        proposition=f"{agent.name} is sleeping",
        certainty="seen directly",
    )
    if not is_zero(agent.sleep_turns_remaining):
        agent.sleep_turns_remaining = decrement_count(agent.sleep_turns_remaining)
    if is_zero(agent.sleep_turns_remaining):
        wake_agent(state, agent, room_index)
        wake_text = "you wake" if agent.name == "You" else f"{render_agent(agent)} wakes"
        return [text, wake_text]
    return [text]


def resolve_poison_ticks(state: LabyrinthState) -> list[str]:
    lines: list[str] = []
    for agent in all_living_agents(state):
        if not agent.poisoned or agent.animal:
            continue
        room_index = agent_room_index(state, agent)
        visible = state.player.alive and state.player.room_index == room_index
        if agent.poison_grace:
            agent.poison_grace = False
            text = f"poison stirs in {render_agent(agent)}, but does not bite yet"
            record_room_event(
                state,
                room_index,
                kind="outcome",
                text=text + ".",
                source="poison",
                subject=agent.name,
                proposition=f"{agent.name} is poisoned",
                certainty="seen directly",
            )
            if visible:
                lines.append(text)
            continue

        damage(agent, ONE)
        agent.poison_bites = increment_count(agent.poison_bites)
        if agent.alive:
            text = f"poison bites {render_agent(agent)}; {render_agent_verb(agent, 'lose')} one hp"
        else:
            text = f"poison claims {render_agent(agent)}; {render_agent_verb(agent, 'die')}"
        record_room_event(
            state,
            room_index,
            kind="outcome",
            text=text + ".",
            source="poison",
            subject=agent.name,
            proposition=f"{agent.name} is poisoned",
            certainty="seen directly",
        )
        if visible:
            lines.append(text)
        if agent.alive and agent.poison_runs_course and count_at_least(agent.poison_bites, ONE):
            clear_poison(agent)
            clear_text = f"poison runs its course in {render_agent(agent)}"
            record_room_event(
                state,
                room_index,
                kind="outcome",
                text=clear_text + ".",
                source="poison",
                subject=agent.name,
                proposition=f"{agent.name} is not poisoned",
                certainty="seen directly",
            )
            if visible:
                lines.append(clear_text)
    return lines

def clear_poison(agent: Agent) -> None:
    agent.poisoned = False
    agent.poison_grace = False
    agent.poison_bites = ZERO
    agent.poison_runs_course = True


def damage(agent: Agent, amount: WordNumber) -> None:
    if agent.animal:
        return
    if compare(agent.hp, amount) == "less":
        agent.hp = ZERO
    else:
        agent.hp = subtract(agent.hp, amount)
    if is_zero(agent.hp):
        agent.alive = False
        agent.sleeping = False
        clear_poison(agent)


def kill(agent: Agent) -> None:
    if agent.animal:
        return
    agent.hp = ZERO
    agent.alive = False
    agent.sleeping = False
    clear_poison(agent)


def render_ending(state: LabyrinthState) -> list[str]:
    lines = ["final state:", render_hp(state, visible_only=False)]
    if state.escaped:
        lines.append("you escaped the labyrinth")
    elif not state.player.alive:
        lines.append("you did not survive")
    else:
        lines.append("the labyrinth continues")
    return lines


def render_hp(state: LabyrinthState, visible_only: bool = True) -> str:
    player_status = render_player_health(state.player)
    player_states = []
    if state.player.poisoned and state.player.alive:
        player_states.append("poisoned")
    if state.player.sleeping and state.player.alive:
        player_states.append("sleeping")
    if player_states:
        player_status += " " + " and ".join(player_states)
    return "condition: " + player_status


def render_player_health(agent: Agent) -> str:
    if not agent.alive:
        return "health zero"
    if agent.hp == agent.max_hp:
        return "health full"
    return f"health {render_fraction(agent.hp, agent.max_hp)}"


def render_condition(agent: Agent) -> str:
    if not agent.alive:
        return "is gone"

    condition = render_condition_word(agent)

    states = []
    if agent.poisoned:
        states.append("poisoned")
    if agent.sleeping:
        states.append("sleeping")
    if len(states) == 1:
        return f"is {condition} and {states[0]}"
    if len(states) > 1:
        return f"is {condition}, " + ", and ".join(states)
    return f"is {condition}"


def render_condition_word(agent: Agent) -> str:
    if not agent.alive:
        return "gone"
    if count_at_least(agent.hp, FOUR):
        return "proud"
    if count_at_least(agent.hp, THREE):
        return "uneasy"
    if agent.hp == TWO:
        return "unsure"
    return "grim"


def advance_round(state: LabyrinthState) -> None:
    tick_stationary_sleepers(state)
    state.round_number = increment_count(state.round_number)
    begin_player_round(state)
    state.round_claims.clear()
    prepare_round_claims(state)
    record_round_observations(state)


def prepare_round_claims(state: LabyrinthState) -> None:
    for agent in present_agents(state):
        if agent.name not in state.round_claims:
            state.round_claims[agent.name] = next_claim(agent)


def round_claim(state: LabyrinthState, agent: Agent) -> str:
    prepare_round_claims(state)
    claim = state.round_claims.get(agent.name)
    if claim is None:
        claim = next_claim(agent)
        state.round_claims[agent.name] = claim
    return claim


def next_claim(agent: Agent) -> str:
    # The claims section is for public claims, not an inbox. Observances still
    # live in agent memory and can be retrieved through ask, but they no longer
    # leak into round claims as "remembers:" diary sludge.
    if not agent.claims:
        return f"{render_agent(agent)} makes no claim."
    claim = agent.claims.pop(0)
    agent.claims.append(claim)
    claim_kind = next_claim_kind(agent)
    if claim_kind == LIE:
        return claim.lie
    return claim.truth


def next_claim_kind(agent: Agent) -> str:
    if not agent.claim_truth_cycle:
        agent.claim_truth_cycle = claim_truth_pattern(agent.lie_rate)
    claim_kind = agent.claim_truth_cycle.pop(0)
    agent.claim_truth_cycle.append(claim_kind)
    return claim_kind


def claim_truth_pattern(lie_rate: LieRate) -> list[str]:
    if lie_rate.out_of != FOUR:
        raise ValueError("labyrinth lie rates currently resolve over four claims")
    if lie_rate.lies == ZERO:
        return [TRUTH, TRUTH, TRUTH, TRUTH]
    if lie_rate.lies == ONE:
        return [LIE, TRUTH, TRUTH, TRUTH]
    if lie_rate.lies == TWO:
        return [TRUTH, LIE, TRUTH, LIE]
    if lie_rate.lies == THREE:
        return [LIE, TRUTH, LIE, LIE]
    if lie_rate.lies == FOUR:
        return [LIE, LIE, LIE, LIE]
    raise ValueError(f"unsupported lie count: {render_number(lie_rate.lies)}")


def set_lie_rate(agent: Agent, lie_rate: LieRate) -> None:
    agent.lie_rate = lie_rate
    agent.claim_truth_cycle.clear()


def render_lie_profile(lie_rate: LieRate) -> str:
    if lie_rate.out_of != FOUR:
        return f"lies on {render_lie_fraction(lie_rate)} claims"
    if lie_rate.lies == ZERO:
        return "always tells the truth"
    if lie_rate.lies == ONE:
        return "often tells the truth"
    if lie_rate.lies == TWO:
        return "lies arbitrarily"
    if lie_rate.lies == THREE:
        return "often lies"
    if lie_rate.lies == FOUR:
        return "is a liar"
    return f"lies on {render_lie_fraction(lie_rate)} claims"


def render_lie_fraction(lie_rate: LieRate) -> str:
    if lie_rate.out_of == FOUR:
        denominator = "fourth" if lie_rate.lies == ONE else "fourths"
        return f"{render_number(lie_rate.lies)} {denominator}"
    return render_fraction(lie_rate.lies, lie_rate.out_of)




def current_survival_action(state: LabyrinthState, agent: Agent) -> str | None:
    room = state.rooms[agent.room_index]
    if agent.poisoned:
        for cup in room.cups.values():
            if is_zero(cup.fifths):
                continue
            if agent_knows_property(agent, cup.name, "is antidote") or agent_knows_property(agent, cup.name, "is elixir"):
                action = f"sip {cup.name}"
                if action not in agent.tried_actions:
                    return action
    if compare(agent.hp, agent.max_hp) == "less":
        for cup in room.cups.values():
            if is_zero(cup.fifths):
                continue
            if agent_knows_property(agent, cup.name, "is elixir"):
                action = f"sip {cup.name}"
                if action not in agent.tried_actions:
                    return action
    return None


def current_agent_intention(state: LabyrinthState, agent: Agent) -> str | None:
    survival_action = current_survival_action(state, agent)
    if survival_action is not None:
        return survival_action
    goal_action = current_goal_action(state, agent)
    if goal_action is not None:
        return goal_action
    room = state.rooms[agent.room_index]
    default_intention = room.intentions.get(agent.name)
    if default_intention is None:
        return None
    if action_is_reasonable_for_agent(state, agent, default_intention):
        return default_intention
    recovery_action = create_recovery_goal_action(state, agent, default_intention)
    if recovery_action is not None:
        return recovery_action
    return None


def current_goal_action(state: LabyrinthState, agent: Agent) -> str | None:
    # Follow-goals are social evidence, not cautious speculation. Even a proud
    # agent is tempted to follow someone who just crossed a door without peril.
    follow_goal = first_available_follow_goal(state, agent)
    if follow_goal is not None:
        return follow_goal

    instruction_goal = first_available_instruction_goal(state, agent)
    if instruction_goal is not None:
        return instruction_goal

    # Agents with low belief_rate are more likely to test before following the
    # room script. High-belief agents, like Aster, keep charging into their own
    # awful certainty unless they saw a clean crossing.
    if agent.belief_rate == "high":
        return None
    for goal in agent.goals:
        if goal.status != "active":
            continue
        if goal.action in agent.tried_actions:
            goal.status = "done"
            continue
        if not goal_action_is_available(state, agent, goal.action):
            goal.status = "blocked"
            continue
        return goal.action
    return None


def first_available_instruction_goal(state: LabyrinthState, agent: Agent) -> str | None:
    for goal in agent.goals:
        if goal.status != "active" or not goal.reason.startswith("instruction from "):
            continue
        if goal.action in agent.tried_actions:
            goal.status = "done"
            continue
        if not goal_action_is_available(state, agent, goal.action):
            goal.status = "blocked"
            continue
        return goal.action
    return None


def first_available_follow_goal(state: LabyrinthState, agent: Agent) -> str | None:
    for goal in agent.goals:
        if goal.status != "active" or not goal.reason.startswith("follow "):
            continue
        if goal.action in agent.tried_actions:
            goal.status = "done"
            continue
        if not goal_action_is_available(state, agent, goal.action):
            goal.status = "blocked"
            continue
        return goal.action
    return None


def goal_action_is_available(state: LabyrinthState, agent: Agent, action: str) -> bool:
    if action.startswith("ask "):
        parsed = parse_ask_command_for_agent(state, agent, action)
        return not isinstance(parsed, str) and not parsed[0].sleeping
    if action.startswith("sip "):
        cup_name = action.removeprefix("sip ").strip()
        cup, _ = resolve_cup_name(state, agent, cup_name)
        return (
            cup is not None
            and not is_zero(cup.fifths)
            and not agent_knows_property(agent, cup.name, "is poison")
            and not agent_knows_property(agent, cup.name, "is sleeping potion")
        )
    if action.startswith("move "):
        door_name = action.removeprefix("move ").strip()
        door, _ = resolve_door_name(state, agent, door_name)
        return door is not None and not agent_knows_property(agent, door.name, "leads to peril")
    return False


def action_is_reasonable_for_agent(state: LabyrinthState, agent: Agent, action: str) -> bool:
    if action.startswith("ask "):
        parsed = parse_ask_command_for_agent(state, agent, action)
        return not isinstance(parsed, str) and not parsed[0].sleeping
    if action.startswith("sip "):
        cup_name = action.removeprefix("sip ").strip()
        cup, _ = resolve_cup_name(state, agent, cup_name)
        if cup is None:
            return False
        if agent_knows_property(agent, cup.name, "is empty"):
            return False
        if agent_knows_property(agent, cup.name, "is poison"):
            return False
        if agent_knows_property(agent, cup.name, "is sleeping potion"):
            return False
        return True
    if action.startswith("move "):
        door_name = action.removeprefix("move ").strip()
        door, _ = resolve_door_name(state, agent, door_name)
        if door is None:
            return False
        if agent_knows_property(agent, door.name, "leads to peril"):
            return False
        return True
    return True


def create_recovery_goal_action(state: LabyrinthState, agent: Agent, blocked_action: str) -> str | None:
    action = choose_recovery_action(state, agent, blocked_action)
    if action is None:
        return None
    if any(goal.action == action and goal.status == "active" for goal in agent.goals):
        return action
    state.goal_sequence += 1
    subject = action_subject(action) or "unknown"
    agent.goals.append(Goal(
        id=f"goal-{state.goal_sequence}",
        action=action,
        subject=subject,
        reason=f"recover after {render_action(blocked_action)} stopped making sense",
        hypothesis_id=None,
        created_turn=render_number(state.round_number),
    ))
    return action


def choose_recovery_action(state: LabyrinthState, agent: Agent, blocked_action: str) -> str | None:
    room = state.rooms[agent.room_index]
    # Prefer useful cups the agent has reason to trust and that are still in the room.
    for cup in room.cups.values():
        if is_zero(cup.fifths):
            continue
        if agent_knows_property(agent, cup.name, "is poison") or agent_knows_property(agent, cup.name, "is sleeping potion"):
            continue
        if any(agent_knows_property(agent, cup.name, property_name) for property_name in ("grants haste", "sharpens truth", "is antidote", "is elixir")):
            action = f"sip {cup.name}"
            if action not in agent.tried_actions:
                return action

    # If the old plan was a spent or unsafe cup, ask a witness about another real option.
    for cup in room.cups.values():
        if is_zero(cup.fifths):
            continue
        if blocked_action == f"sip {cup.name}":
            continue
        if agent_knows_property(agent, cup.name, "is poison") or agent_knows_property(agent, cup.name, "is sleeping potion"):
            continue
        witness = choose_witness_for_subject(state, agent, cup.name, agent.name)
        if witness is not None:
            action = f"ask {witness.name} about {cup.name}"
            if action not in agent.tried_actions:
                return action

    # Then try doors the agent has positive evidence for.
    for door in room.doors.values():
        if agent_knows_property(agent, door.name, "leads to peril"):
            continue
        if any(agent_knows_property(agent, door.name, property_name) for property_name in ("leads onward", "is safe", "is the exit")):
            action = f"move {door.name}"
            if action not in agent.tried_actions:
                return action

    for door in room.doors.values():
        if agent_knows_property(agent, door.name, "leads to peril"):
            continue
        witness = choose_witness_for_subject(state, agent, door.name, agent.name)
        if witness is not None:
            action = f"ask {witness.name} about {door.name}"
            if action not in agent.tried_actions:
                return action

    return None


def action_subject(action: str) -> str | None:
    if action.startswith("sip "):
        return action.removeprefix("sip ").strip()
    if action.startswith("move "):
        return action.removeprefix("move ").strip()
    if action.startswith("ask ") and " about " in action:
        return action.rsplit(" about ", 1)[1].strip()
    return None


def agent_knows_property(agent: Agent, subject: str, property_text: str) -> bool:
    needle = normalize_alias(f"{subject} {property_text}")
    for entry in agent.memory.entries_about(subject):
        if entry.kind not in {"inference", "outcome", "action", "claim_made"}:
            continue
        if entry.proposition and normalize_alias(entry.proposition) == needle:
            return True
    return False


def mark_goal_attempted(agent: Agent, action: str, status: str) -> None:
    for goal in agent.goals:
        if goal.action == action and goal.status == "active":
            goal.status = status
            break


def maybe_form_hypothesis_from_entry(state: LabyrinthState, observer: Agent, entry: MemoryEntry) -> None:
    if entry.kind not in {"heard_claim", "reported_claim"}:
        return
    if not entry.proposition:
        return
    normalized_entry = normalize_alias(entry.proposition)
    if "testing whether" in normalized_entry or "wonders whether" in normalized_entry or "know nothing useful" in normalized_entry:
        return
    subject = claim_focus_subject(state, entry)
    if subject is None:
        return
    if not subject_is_in_room(state, subject, observer.room_index):
        return
    proposition = canonical_claim_proposition(state, entry.proposition, subject)
    if proposition is None:
        return
    if any(h.proposition == proposition and h.subject == subject and h.status == "active" for h in observer.hypotheses):
        return

    test_action = test_action_for_hypothesis(state, observer, subject, proposition, entry.source)
    state.hypothesis_sequence += 1
    hypothesis = Hypothesis(
        id=f"hypothesis-{state.hypothesis_sequence}",
        subject=subject,
        proposition=proposition,
        source=entry.source,
        created_turn=render_number(state.round_number),
        evidence_ids=[entry.id],
        test_action=test_action,
        reason=f"heard {entry.source or 'someone'} claim {render_proposition(proposition)}",
    )
    observer.hypotheses.append(hypothesis)
    remember_hypothesis_birth(state, observer, hypothesis)

    if test_action is not None and not any(goal.action == test_action and goal.status == "active" for goal in observer.goals):
        state.goal_sequence += 1
        observer.goals.append(Goal(
            id=f"goal-{state.goal_sequence}",
            action=test_action,
            subject=subject,
            reason=f"test whether {render_proposition(proposition)}",
            hypothesis_id=hypothesis.id,
            created_turn=render_number(state.round_number),
        ))


def remember_hypothesis_birth(state: LabyrinthState, observer: Agent, hypothesis: Hypothesis) -> None:
    state.memory_sequence += 1
    text = f"{observer.name} wonders whether {render_proposition(hypothesis.proposition)}."
    if hypothesis.test_action:
        text = f"{observer.name} wonders whether {render_proposition(hypothesis.proposition)} and wants to {render_action(hypothesis.test_action)}."
    entry = MemoryEntry(
        id=f"memory-{state.memory_sequence}",
        turn=render_number(state.round_number),
        phase="hypothesis",
        observer=observer.name,
        kind="hypothesis",
        text=text,
        source=hypothesis.source,
        subject=hypothesis.subject,
        proposition=hypothesis.proposition,
        certainty=hypothesis.certainty,
        sequence=state.memory_sequence,
        subjects=sorted({hypothesis.subject, *(extract_subjects(state, hypothesis.proposition))}),
    )
    observer.memory.remember(entry)




def subject_is_in_room(state: LabyrinthState, subject: str, room_index: int) -> bool:
    if subject == state.player.name:
        return state.player.alive and state.player.room_index == room_index
    agent = state.claimants.get(subject)
    if agent is not None:
        return agent.alive and agent.room_index == room_index
    room = state.rooms[room_index]
    if subject == room.name:
        return True
    return subject in room.cups or subject in room.doors


def claim_focus_subject(state: LabyrinthState, entry: MemoryEntry) -> str | None:
    candidates = [subject for subject in entry.subjects if subject != entry.source and subject != entry.subject]
    # Prefer testable objects over people, because "Aster claims BrassDoor is
    # safe" should create a BrassDoor hypothesis, not just another Aster note.
    for subject in candidates:
        if is_door_subject(state, subject) or is_cup_subject(state, subject):
            return subject
    for subject in candidates:
        if subject in state.claimants or subject == state.player.name:
            return subject
    return None


def canonical_claim_proposition(state: LabyrinthState, claim_text: str, subject: str) -> str | None:
    text = normalize_alias(claim_text)
    if is_door_subject(state, subject):
        if "exit" in text:
            return f"{subject} is the exit"
        if "leads onward" in text or "advances" in text or "press deeper" in text:
            return f"{subject} leads onward"
        if "leads to peril" in text or "hungry" in text or "unsafe" in text:
            return f"{subject} leads to peril"
        if "safe" in text or "kind" in text:
            return f"{subject} is safe"
    if is_cup_subject(state, subject):
        if "empty" in text:
            return f"{subject} is empty"
        if "poison" in text:
            return f"{subject} is poison"
        if "antidote" in text:
            return f"{subject} is antidote"
        if "elixir" in text or "restores" in text or "full health" in text or "heals" in text:
            return f"{subject} is elixir"
        if "grants haste" in text or "haste" in text or "quick" in text:
            return f"{subject} grants haste"
        if "sharpens truth" in text or "truth" in text or "clear" in text:
            return f"{subject} sharpens truth"
        if "stupor" in text or "slow" in text or "slows" in text:
            return f"{subject} brings stupor"
        if "sleep" in text or "asleep" in text or "drowsy" in text:
            return f"{subject} is sleeping potion"
        if "safe" in text:
            return f"{subject} is safe"
    if subject in state.claimants or subject == state.player.name:
        if "not poisoned" in text or "no longer poisoned" in text:
            return f"{subject} is not poisoned"
        if "poisoned" in text:
            return f"{subject} is poisoned"
        if "not sleeping" in text or "awake" in text:
            return f"{subject} is not sleeping"
        if "sleeping" in text or "asleep" in text:
            return f"{subject} is sleeping"
        if "untrusted" in text or "unreliable" in text:
            return f"{subject} is unreliable"
        if "trusted" in text or "honest" in text:
            return f"{subject} is trusted"
        if "liar" in text or "lies" in text:
            return f"{subject} lies"
        if "reckless" in text:
            return f"{subject} is reckless"
    return None


def test_action_for_hypothesis(
    state: LabyrinthState,
    observer: Agent,
    subject: str,
    proposition: str,
    source: str | None,
) -> str | None:
    text = normalize_alias(proposition)

    # Only object hypotheses become active goals for now. Person/social
    # hypotheses are archived, but they should not make agents chase witnesses
    # about "the bram" or "the vey" while a room still has real hazards.
    if not (is_cup_subject(state, subject) or is_door_subject(state, subject)):
        return None

    # First try a social test: ask another present witness. This keeps fragile
    # agents from instantly testing every door with their body.
    witness = choose_witness_for_subject(state, observer, subject, source)
    if witness is not None:
        return f"ask {witness.name} about {subject}"

    if is_cup_subject(state, subject):
        if "poison" in text or "empty" in text or "sleep" in text:
            return None
        return f"sip {subject}"
    if is_door_subject(state, subject):
        if "leads to peril" in text:
            return None
        if "safe" in text or "leads onward" in text or "exit" in text:
            return f"move {subject}"
    return None


def choose_witness_for_subject(state: LabyrinthState, observer: Agent, subject: str, source: str | None) -> Agent | None:
    present = [
        agent
        for agent in present_agents(state)
        if agent.name not in {observer.name, source} and not agent.sleeping
    ]
    if not present:
        return None
    # Prefer stationary creatures as oracles, then truthier-looking agents.
    present.sort(key=lambda agent: (not agent.stationary, agent.belief_rate != "low", agent.name))
    return present[0]


def update_hypotheses_from_entry(observer: Agent, entry: MemoryEntry) -> None:
    if entry.kind != "outcome" or not entry.proposition or not entry.subject:
        return
    observed = normalize_alias(entry.proposition)
    for hypothesis in observer.hypotheses:
        if hypothesis.subject != entry.subject or hypothesis.status not in {"active", "testing"}:
            continue
        supposed = normalize_alias(hypothesis.proposition)
        if supports_hypothesis(supposed, observed):
            hypothesis.status = "supported"
            hypothesis.certainty = "strongly inferred"
            hypothesis.evidence_ids.append(entry.id)
            finish_goals_for_hypothesis(observer, hypothesis.id, "done")
        elif contradicts_hypothesis(supposed, observed):
            hypothesis.status = "refuted"
            hypothesis.certainty = "contradicted"
            hypothesis.evidence_ids.append(entry.id)
            finish_goals_for_hypothesis(observer, hypothesis.id, "done")


def finish_goals_for_hypothesis(agent: Agent, hypothesis_id: str, status: str) -> None:
    for goal in agent.goals:
        if goal.hypothesis_id == hypothesis_id and goal.status in {"active", "testing", "blocked"}:
            goal.status = status


def supports_hypothesis(supposed: str, observed: str) -> bool:
    if supposed == observed:
        return True
    if "is safe" in supposed and "leads to peril" not in observed and ("leads onward" in observed or "is exit" in observed):
        return True
    if "is safe" in supposed and not any(hazard in observed for hazard in ("is poison", "is sleeping potion", "brings stupor")):
        if any(benefit in observed for benefit in ("grants haste", "sharpens truth", "is antidote", "is elixir")):
            return True
    return supports_outcome(supposed, observed)


def contradicts_hypothesis(supposed: str, observed: str) -> bool:
    if "is safe" in supposed and "leads to peril" in observed:
        return True
    if "is safe" in supposed and any(hazard in observed for hazard in ("is poison", "is sleeping potion", "brings stupor")):
        return True
    if "leads onward" in supposed and "leads to peril" in observed:
        return True
    if "is poison" in supposed and any(benefit in observed for benefit in ("is antidote", "is elixir", "grants haste", "sharpens truth")):
        return True
    if "grants haste" in supposed and any(hazard in observed for hazard in ("is poison", "is sleeping potion", "brings stupor")):
        return True
    if "sharpens truth" in supposed and any(hazard in observed for hazard in ("is poison", "is sleeping potion", "brings stupor")):
        return True
    if "is antidote" in supposed and any(other in observed for other in ("is poison", "grants haste", "sharpens truth", "is sleeping potion", "brings stupor")):
        return True
    if "is elixir" in supposed and any(other in observed for other in ("is poison", "grants haste", "sharpens truth", "is sleeping potion", "brings stupor")):
        return True
    if "is sleeping potion" in supposed and any(other in observed for other in ("is poison", "grants haste", "sharpens truth", "is antidote", "is elixir")):
        return True
    if "brings stupor" in supposed and any(other in observed for other in ("is poison", "grants haste", "sharpens truth", "is antidote", "is elixir")):
        return True
    return contradicts_outcome(supposed, observed)


def answer_from_hypothesis(agent: Agent, subject: str) -> str | None:
    relevant = [hypothesis for hypothesis in agent.hypotheses if hypothesis.subject == subject]
    if not relevant:
        return None
    relevant.sort(key=lambda hypothesis: status_rank(hypothesis.status), reverse=True)
    hypothesis = relevant[0]
    proposition = render_proposition(hypothesis.proposition)
    if hypothesis.status == "supported":
        return f"{proposition} seems true"
    if hypothesis.status == "refuted":
        return f"{proposition} was refuted"
    if hypothesis.test_action:
        return f"they are testing whether {proposition}"
    return f"they wonder whether {proposition}"


def status_rank(status: str) -> int:
    return {
        "supported": 4,
        "refuted": 4,
        "testing": 3,
        "active": 2,
        "blocked": 1,
        "done": 0,
    }.get(status, 0)


def is_cup_subject(state: LabyrinthState, subject: str) -> bool:
    return any(subject in room.cups for room in state.rooms)


def is_door_subject(state: LabyrinthState, subject: str) -> bool:
    return any(subject in room.doors for room in state.rooms)

def topic_relevant_round_claim(state: LabyrinthState, agent: Agent, subject: str) -> str | None:
    claim = round_claim(state, agent)
    if subject in extract_subjects(state, claim):
        return claim
    return None


def ignorance_claim(agent: Agent, subject: str) -> str:
    return f"{render_agent(agent)} claims they know nothing useful about {render_name(subject) if has_camel_boundary(subject) else render_topic(subject)}."


CLAIM_AUDIT_KINDS = {"heard_claim", "reported_claim", "claim_made"}


def claim_is_auditable(proposition: str) -> bool:
    normalized = normalize_alias(proposition)
    return not any(
        phrase in normalized
        for phrase in (
            "testing whether",
            "wonders whether",
            "know nothing useful",
            "evidence for",
            "mixed",
            "said this",
            "no one has disproved",
            " assesses ",
        )
    )


def rate_claim_when_heard(
    state: LabyrinthState,
    observer: Agent,
    kind: str,
    source: str | None,
    proposition: str,
    subjects: list[str],
) -> tuple[str, str]:
    if kind == "claim_made" and source == observer.name:
        return "asserted", "speaker's own claim"

    focus = claim_focus_subject_from_subjects(state, subjects, source)
    if focus is None:
        return "unsupported", "no testable subject was clear when heard"

    canonical = canonical_claim_proposition(state, proposition, focus)
    if canonical is None:
        return "unsupported", "the claim was too vague to test when heard"

    observed = latest_direct_proposition_about(observer, focus)
    if observed:
        observed_normalized = normalize_alias(observed)
        canonical_normalized = normalize_alias(canonical)
        if supports_hypothesis(canonical_normalized, observed_normalized):
            return "already supported", f"{render_proposition(observed)} was already known"
        if contradicts_hypothesis(canonical_normalized, observed_normalized):
            return "already contradicted", f"{render_proposition(observed)} was already known"

    if source:
        stats = source_audit_counts(observer, source, claim_domain_for_subject(state, focus))
        supported = stats.get("supported", 0)
        refuted = stats.get("refuted", 0)
        if supported > refuted and supported > 0:
            return "plausible", f"{render_source_name(state, source)} had more supported than failed claims in this domain"
        if refuted > supported and refuted > 0:
            return "doubtful", f"{render_source_name(state, source)} had more failed than supported claims in this domain"

    return "untested", "no matching outcome had been observed yet"


def claim_focus_subject_from_subjects(state: LabyrinthState, subjects: list[str], source: str | None = None) -> str | None:
    candidates = [subject for subject in subjects if subject != source]
    for subject in candidates:
        if is_door_subject(state, subject) or is_cup_subject(state, subject):
            return subject
    for subject in candidates:
        if subject in state.claimants or subject == state.player.name:
            return subject
    return None


def latest_direct_proposition_about(agent: Agent, subject: str) -> str | None:
    for entry in sorted(agent.memory.entries_about(subject), key=lambda item: item.sequence, reverse=True):
        if entry.kind in {"outcome", "inference"} and entry.proposition and proposition_focuses_on(entry.proposition, subject):
            return entry.proposition
    return None


def claim_domain_for_subject(state: LabyrinthState, subject: str) -> str:
    if is_door_subject(state, subject):
        return "door"
    if is_cup_subject(state, subject):
        return "cup"
    if subject in state.claimants or subject == state.player.name:
        return "person"
    return "unknown"


def source_audit_counts(agent: Agent, source: str, domain: str | None = None) -> dict[str, int]:
    counts = {"supported": 0, "refuted": 0, "untested": 0}
    for entry in agent.memory.entries:
        if entry.kind not in CLAIM_AUDIT_KINDS or entry.source != source:
            continue
        if not entry.proposition or not claim_is_auditable(entry.proposition):
            continue
        if domain and claim_entry_domain(entry) != domain:
            continue
        bucket = audit_bucket(entry.current_rating)
        counts[bucket] = counts.get(bucket, 0) + 1
    return counts


def claim_entry_domain(entry: MemoryEntry) -> str:
    for subject in entry.subjects:
        if subject.endswith("Door"):
            return "door"
        if subject.endswith("Cup"):
            return "cup"
    return "person" if entry.subjects else "unknown"


def audit_bucket(rating: str) -> str:
    if rating in {"supported", "already supported"}:
        return "supported"
    if rating in {"refuted", "already contradicted"}:
        return "refuted"
    return "untested"


def audit_claims_from_outcome(state: LabyrinthState, observer: Agent, outcome: MemoryEntry) -> None:
    if outcome.kind != "outcome" or not outcome.proposition or not outcome.subject:
        return
    observed = normalize_alias(outcome.proposition)
    for claim in observer.memory.entries:
        if claim.kind not in CLAIM_AUDIT_KINDS or not claim.source or not claim.proposition:
            continue
        if not claim_is_auditable(claim.proposition):
            continue
        if outcome.subject not in claim.subjects:
            continue
        claimed = canonical_claim_proposition(state, claim.proposition, outcome.subject)
        if claimed is None:
            continue
        claimed_normalized = normalize_alias(claimed)
        if supports_hypothesis(claimed_normalized, observed):
            claim.current_rating = "supported"
            claim.outcome_turn = outcome.turn
            claim.outcome_reason = f"later, {render_proposition(outcome.proposition)} was observed"
        elif contradicts_hypothesis(claimed_normalized, observed):
            claim.current_rating = "refuted"
            claim.outcome_turn = outcome.turn
            claim.outcome_reason = f"later, {render_proposition(outcome.proposition)} was observed"


def claim_audit_suffix(entry: MemoryEntry) -> str:
    if not entry.initial_rating:
        return ""
    initial = entry.initial_rating.replace("already ", "")
    current = audit_bucket(entry.current_rating)
    if current == "supported":
        if entry.initial_rating in {"untested", "plausible", "doubtful", "unsupported"}:
            return f"; it seemed {initial} then, and later proved true"
        return "; it had already been supported"
    if current == "refuted":
        if entry.initial_rating in {"untested", "plausible", "doubtful", "unsupported"}:
            return f"; it seemed {initial} then, but later failed"
        return "; it had already been contradicted"
    return f"; it seemed {initial} then and is still untested"



CERTAINTY_ORDER = {
    "seen directly": 5,
    "four fourths sure": 5,
    "strongly inferred": 4,
    "three fourths sure": 4,
    "inferred": 3,
    "reported": 2,
    "heard": 2,
    "weakly inferred": 1,
    "unknown": 0,
}


def record_round_observations(state: LabyrinthState) -> None:
    room = current_room(state)
    round_key = f"round:{render_number(state.round_number)}:room:{state.room_index}"
    if round_key in state.recorded_round_memory:
        return
    state.recorded_round_memory.add(round_key)

    claims = [round_claim(state, agent) for agent in present_agents(state)]
    snapshot_text = (
        f"round {render_number(state.round_number)} in {room.name}; "
        f"present: {', '.join(render_agent(agent) for agent in present_agents(state))}; "
        f"cups: {', '.join(render_name(cup.name) + ' ' + render_cup_fullness(cup.fifths) for cup in room.cups.values())}; "
        f"doors: {', '.join(render_name(door.name) for door in room.doors.values())}."
    )
    for observer in observers_in_room(state, state.room_index):
        remember(
            state,
            observer,
            kind="snapshot",
            text=snapshot_text,
            source="room",
            subject=room.name,
            proposition=f"{observer.name} saw {room.name} during round {render_number(state.round_number)}",
            certainty="seen directly",
            subjects=[room.name],
        )
        for cup in room.cups.values():
            if is_zero(cup.fifths):
                remember(
                    state,
                    observer,
                    kind="outcome",
                    text=f"{render_name(cup.name)} is empty.",
                    source=cup.name,
                    subject=cup.name,
                    proposition=f"{cup.name} is empty",
                    certainty="seen directly",
                )
    for agent, claim_text in zip(present_agents(state), claims):
        record_claim_event(state, agent, claim_text, state.room_index)


def observers_in_room(state: LabyrinthState, room_index: int) -> list[Agent]:
    observers = [
        agent
        for agent in state.claimants.values()
        if agent.alive and not agent.sleeping and agent.room_index == room_index
    ]
    if state.player.alive and not state.player.sleeping and state.player.room_index == room_index:
        observers.insert(0, state.player)
    return observers


def record_room_event(
    state: LabyrinthState,
    room_index: int,
    kind: str,
    text: str,
    source: str | None = None,
    subject: str | None = None,
    proposition: str | None = None,
    certainty: str = "seen directly",
    subjects: list[str] | None = None,
) -> None:
    for observer in observers_in_room(state, room_index):
        remember(
            state,
            observer,
            kind=kind,
            text=text,
            source=source,
            subject=subject,
            proposition=proposition,
            certainty=certainty,
            subjects=subjects,
        )


def record_claim_event(state: LabyrinthState, speaker: Agent, claim_text: str, room_index: int) -> None:
    for observer in observers_in_room(state, room_index):
        kind = "claim_made" if observer.name == speaker.name else "heard_claim"
        certainty = "seen directly" if observer.name == speaker.name else "heard"
        remember(
            state,
            observer,
            kind=kind,
            text=claim_text,
            source=speaker.name,
            subject=speaker.name,
            proposition=claim_text,
            certainty=certainty,
        )


def remember(
    state: LabyrinthState,
    observer: Agent,
    kind: str,
    text: str,
    source: str | None = None,
    subject: str | None = None,
    proposition: str | None = None,
    certainty: str = "heard",
    subjects: list[str] | None = None,
) -> None:
    state.memory_sequence += 1
    entry_subjects = set(subjects or [])
    if subject:
        entry_subjects.add(subject)
    entry_subjects.update(extract_subjects(state, text))
    if proposition:
        entry_subjects.update(extract_subjects(state, proposition))

    initial_rating = ""
    initial_reason = ""
    current_rating = ""
    sorted_subjects = sorted(entry_subjects)
    if kind in CLAIM_AUDIT_KINDS and proposition and claim_is_auditable(proposition):
        initial_rating, initial_reason = rate_claim_when_heard(
            state,
            observer,
            kind,
            source,
            proposition,
            sorted_subjects,
        )
        current_rating = initial_rating

    entry = MemoryEntry(
        id=f"memory-{state.memory_sequence}",
        turn=render_number(state.round_number),
        phase="round",
        observer=observer.name,
        kind=kind,
        text=text,
        source=source,
        subject=subject,
        proposition=proposition,
        certainty=certainty,
        sequence=state.memory_sequence,
        subjects=sorted_subjects,
        initial_rating=initial_rating,
        initial_reason=initial_reason,
        current_rating=current_rating,
    )
    observer.memory.remember(entry)
    maybe_update_social_weight_from_reputation_claim(state, observer, entry)
    maybe_infer_from_entry(state, observer, entry)
    maybe_form_hypothesis_from_entry(state, observer, entry)


def maybe_infer_from_entry(state: LabyrinthState, observer: Agent, entry: MemoryEntry) -> None:
    if entry.kind == "inference" or not entry.proposition:
        return
    if entry.kind not in {"outcome", "action"}:
        return
    if entry.proposition in observer.memory.known_propositions:
        return
    observer.memory.known_propositions.add(entry.proposition)
    update_trust_from_outcome(observer, entry)
    audit_claims_from_outcome(state, observer, entry)
    update_hypotheses_from_entry(observer, entry)
    state.memory_sequence += 1
    subjects = set(entry.subjects)
    if entry.subject:
        subjects.add(entry.subject)
    inference = MemoryEntry(
        id=f"memory-{state.memory_sequence}",
        turn=render_number(state.round_number),
        phase="inference",
        observer=observer.name,
        kind="inference",
        text=f"{observer.name} infers: {render_proposition(entry.proposition)}.",
        source=entry.id,
        subject=entry.subject,
        proposition=entry.proposition,
        certainty="strongly inferred" if entry.kind == "outcome" else "inferred",
        sequence=state.memory_sequence,
        subjects=sorted(subjects),
    )
    observer.memory.remember(inference)


def extract_subjects(state: LabyrinthState, text: str) -> set[str]:
    normalized = normalize_alias(text)
    compacted = normalized.replace(" ", "")
    subjects: set[str] = set()
    for name in all_subject_names(state):
        spaced = normalize_alias(" ".join(words_from_name(name)))
        name_compact = spaced.replace(" ", "")
        plain = normalize_alias(name)
        if spaced and f" {spaced} " in f" {normalized} ":
            subjects.add(name)
        elif name_compact and name_compact in compacted:
            subjects.add(name)
        elif plain and f" {plain} " in f" {normalized} ":
            subjects.add(name)
    return subjects


def all_subject_names(state: LabyrinthState) -> list[str]:
    names = list(state.claimants.keys()) + [state.player.name]
    for room in state.rooms:
        names.append(room.name)
        names.extend(room.doors.keys())
        names.extend(room.cups.keys())
    return names



def update_trust_from_outcome(observer: Agent, outcome: MemoryEntry) -> None:
    if outcome.kind != "outcome" or not outcome.proposition or not outcome.subject:
        return
    proposition = normalize_alias(outcome.proposition)
    if "leads to peril" not in proposition and "is poison" not in proposition and "grants haste" not in proposition and "is empty" not in proposition:
        return
    for claim in observer.memory.entries:
        if claim.kind not in {"heard_claim", "claim_made"} or not claim.source:
            continue
        if outcome.subject not in claim.subjects:
            continue
        claim_text = normalize_alias(claim.text)
        trust_key = f"{claim.source}:{outcome.subject}"
        if contradicts_outcome(claim_text, proposition):
            observer.memory.trust[trust_key] = "distrusted"
            observer.memory.trust_evidence.setdefault(trust_key, []).extend([claim.id, outcome.id])
            adjust_social_weight_for_truth_event(
                observer,
                claim.source,
                outcome.subject,
                told_truth=False,
                caller=None,
                evidence=f"false:{claim.id}:{outcome.id}",
            )
        elif supports_outcome(claim_text, proposition):
            observer.memory.trust[trust_key] = "trusted"
            observer.memory.trust_evidence.setdefault(trust_key, []).extend([claim.id, outcome.id])
            adjust_social_weight_for_truth_event(
                observer,
                claim.source,
                outcome.subject,
                told_truth=True,
                caller=None,
                evidence=f"true:{claim.id}:{outcome.id}",
            )


def contradicts_outcome(claim_text: str, proposition: str) -> bool:
    if "leads to peril" in proposition and ("safe" in claim_text or "kind" in claim_text):
        return True
    if "is poison" in proposition and ("safe" in claim_text or "antidote" in claim_text):
        return True
    if "grants haste" in proposition and ("poison" in claim_text or "slows" in claim_text):
        return True
    if "is empty" in proposition and ("full" in claim_text or "grants" in claim_text):
        return True
    return False


def supports_outcome(claim_text: str, proposition: str) -> bool:
    if "leads to peril" in proposition and "leads to peril" in claim_text:
        return True
    if "is poison" in proposition and "poison" in claim_text:
        return True
    if "grants haste" in proposition and "grants haste" in claim_text:
        return True
    if "is empty" in proposition and "empty" in claim_text:
        return True
    return False


def render_trust_topic(topic: str) -> str:
    if topic in {"pushing", "slapping", "violence", "coercion"}:
        return topic
    return render_name(topic)


def render_trust_topic_from_evidence(state: LabyrinthState, topic: str, evidence: str | None) -> str:
    if not evidence:
        return render_trust_topic(topic)
    parts = evidence.split(":")
    if len(parts) < 2:
        return render_trust_topic(topic)
    act, target = parts[0], parts[1]
    target_agent = state.claimants.get(target)
    if act == "slapped":
        if target_agent is not None and target_agent.stationary:
            return "fixed witnesses"
        return "people who can be slapped"
    if act == "pushed":
        return "doors"
    return render_trust_topic(topic)


def answer_from_trust(agent: Agent, subject: str) -> str | None:
    for trust_key, judgement in agent.memory.trust.items():
        source, topic = trust_key.split(":", 1)
        if source != subject:
            continue
        source_text = "you" if source == "You" else source
        evidence = agent.memory.trust_evidence.get(trust_key, [])
        topic_text = render_trust_topic_from_evidence(state, topic, evidence[-1] if evidence else None)
        if judgement == "distrusted":
            if source == "You":
                return f"you are not trusted about {topic_text}"
            return f"{source_text} is not trusted about {topic_text}"
        if judgement == "trusted":
            if source == "You":
                return f"you are trusted about {topic_text}"
            return f"{source_text} is trusted about {topic_text}"
    return None

def answer_from_trust_with_evidence(state: LabyrinthState, agent: Agent, subject: str) -> str | None:
    for trust_key, judgement in agent.memory.trust.items():
        source, topic = trust_key.split(":", 1)
        if source != subject:
            continue
        evidence = agent.memory.trust_evidence.get(trust_key, [])
        last_evidence = evidence[-1] if evidence else None
        topic_text = render_trust_topic_from_evidence(state, topic, last_evidence)
        evidence_line = render_trust_evidence(state, source, last_evidence)
        if judgement == "distrusted":
            if source == "You":
                verdict = f"{render_agent(agent)} does not trust you around {topic_text}."
            else:
                verdict = f"{render_agent(agent)} does not trust {render_source_name(state, source)} around {topic_text}."
        elif judgement == "trusted":
            if source == "You":
                verdict = f"{render_agent(agent)} trusts you around {topic_text}."
            else:
                verdict = f"{render_agent(agent)} trusts {render_source_name(state, source)} around {topic_text}."
        else:
            continue
        if evidence_line:
            return f"{render_agent(agent)} remembers {evidence_line}. {verdict}"
        return verdict
    return None


def answer_from_trust_verdict(state: LabyrinthState, agent: Agent, subject: str) -> str | None:
    for trust_key, judgement in agent.memory.trust.items():
        source, topic = trust_key.split(":", 1)
        if source != subject:
            continue
        evidence = agent.memory.trust_evidence.get(trust_key, [])
        topic_text = render_trust_topic_from_evidence(state, topic, evidence[-1] if evidence else None)
        if judgement == "distrusted":
            if source == "You":
                return f"{render_agent(agent)} does not trust you around {topic_text}."
            return f"{render_agent(agent)} does not trust {render_source_name(state, source)} around {topic_text}."
        if judgement == "trusted":
            if source == "You":
                return f"{render_agent(agent)} trusts you around {topic_text}."
            return f"{render_agent(agent)} trusts {render_source_name(state, source)} around {topic_text}."
    return None


def render_trust_evidence(state: LabyrinthState, source: str, evidence: str | None) -> str | None:
    if not evidence:
        return None
    parts = evidence.split(":")
    if len(parts) < 2:
        return None
    act, target = parts[0], parts[1]
    source_text = "you" if source == "You" else render_source_name(state, source)
    target_text = render_source_name(state, target)
    if act == "slapped":
        return f"{source_text} slapped {target_text}"
    if act == "pushed":
        return f"{source_text} pushed {target_text}"
    return None


def answer_from_person_memory(state: LabyrinthState, agent: Agent, subject: str, entries: list[MemoryEntry]) -> str | None:
    person_entries = [
        entry for entry in entries
        if subject in entry.subjects and entry.kind in {"action", "outcome", "inference"}
    ]
    person_entries = sorted(person_entries, key=lambda entry: (certainty_rank(entry.certainty), entry.sequence), reverse=True)
    direct = next((entry for entry in person_entries if person_memory_entry_is_useful(entry, subject)), None)
    trust_answer = answer_from_trust_with_evidence(state, agent, subject)
    if direct is not None:
        memory_line = render_person_memory_answer(state, agent, direct, subject)
        trust_verdict = answer_from_trust_verdict(state, agent, subject)
        if trust_verdict:
            return f"{memory_line} {trust_verdict}"
        return memory_line
    if trust_answer:
        return trust_answer
    return None


def person_memory_entry_is_useful(entry: MemoryEntry, subject: str) -> bool:
    if entry.kind == "inference" and entry.proposition:
        return proposition_focuses_on(entry.proposition, subject)
    if entry.kind in {"action", "outcome"}:
        if entry.proposition and proposition_focuses_on(entry.proposition, subject):
            return True
        normalized = normalize_alias(entry.text)
        subject_forms = {normalize_alias(subject), normalize_alias(" ".join(words_from_name(subject)))}
        return any(form and form in normalized for form in subject_forms)
    return False


def render_person_memory_answer(state: LabyrinthState, agent: Agent, entry: MemoryEntry, subject: str) -> str:
    event = render_event_memory(state, entry, subject)
    if entry.kind == "inference":
        return f"{render_agent(agent)} believes that {event}."
    if entry.certainty in {"seen directly", "inferred", "strongly inferred"}:
        return f"{render_agent(agent)} says they saw that {event}."
    return f"{render_agent(agent)} says they heard that {event}."


def render_event_memory(state: LabyrinthState, entry: MemoryEntry, subject: str | None = None) -> str:
    if entry.proposition and (subject is None or proposition_focuses_on(entry.proposition, subject)):
        rendered = render_proposition(entry.proposition)
    else:
        rendered = entry.text.rstrip(".")
    if rendered.startswith("You "):
        rendered = "you " + rendered[len("You "):]
    if rendered.startswith("you "):
        return rendered
    return rendered

def answer_from_memory(state: LabyrinthState, agent: Agent, raw_topic: str) -> str | None:
    subject = raw_topic if raw_topic in all_subject_names(state) else canonicalize_topic(state, raw_topic)
    entries = relevant_memory_entries(agent, subject, raw_topic)
    if not entries:
        return None
    entries = sorted(entries, key=lambda entry: (certainty_rank(entry.certainty), entry.sequence), reverse=True)
    focused_entries = [entry for entry in entries if entry.proposition and proposition_focuses_on(entry.proposition, subject)]

    # Person-subject questions usually want whereabouts/recent history first.
    # Trust is still useful, but it reads better when it comes with the memory
    # that caused it.
    if subject in state.claimants or subject == state.player.name:
        person_memory = answer_from_person_memory(state, agent, subject, entries)
        if person_memory:
            return person_memory
        reported_person = next((entry for entry in focused_entries if entry.kind == "reported_claim" and entry.proposition), None)
        if reported_person and reported_person.proposition:
            source = render_source_name(state, reported_person.source)
            return f"{render_agent(agent)} claims {source} said {render_proposition(reported_person.proposition)}."
        own_person_claim = next((
            entry
            for entry in focused_entries
            if entry.kind == "claim_made" and entry.source == agent.name and entry.proposition
        ), None)
        if own_person_claim and own_person_claim.proposition:
            canonical = canonical_claim_proposition(state, own_person_claim.proposition, subject)
            if canonical:
                return f"{render_agent(agent)} claims {render_proposition(canonical)}."

    # First answer from what the agent directly observed or strongly inferred.
    # Reported claims stay lower in the stack so hearsay cannot dress itself up
    # as knowledge just because it mentions the right subject.
    inference = next((entry for entry in focused_entries if entry.kind == "inference"), None)
    if inference and inference.proposition:
        return f"{render_agent(agent)} claims {render_proposition(inference.proposition)}."

    direct = next((entry for entry in focused_entries if entry.kind in {"outcome", "action"}), None)
    if direct and direct.proposition:
        return f"{render_agent(agent)} claims {render_proposition(direct.proposition)}."

    if subject in state.claimants or subject == state.player.name:
        trust_answer = answer_from_trust_with_evidence(state, agent, subject)
        if trust_answer:
            return trust_answer

    hypothesis_answer = answer_from_hypothesis(agent, subject)
    if hypothesis_answer:
        return f"{render_agent(agent)} claims {hypothesis_answer}."

    own_claim = next((
        entry
        for entry in focused_entries
        if entry.kind == "claim_made" and entry.source == agent.name and entry.proposition
    ), None)
    if own_claim and own_claim.proposition:
        canonical = canonical_claim_proposition(state, own_claim.proposition, subject)
        if canonical:
            return f"{render_agent(agent)} claims {render_proposition(canonical)}."
        return f"{render_agent(agent)} claims they previously said {render_proposition(own_claim.proposition)}."

    reported = next((entry for entry in focused_entries if entry.kind == "reported_claim" and entry.proposition), None)
    if reported and reported.proposition:
        source = render_source_name(state, reported.source)
        return f"{render_agent(agent)} claims {source} said {render_proposition(reported.proposition)}."

    heard = next((entry for entry in focused_entries if entry.kind == "heard_claim" and entry.source and entry.proposition), None)
    if heard and heard.proposition:
        source = render_source_name(state, heard.source)
        return f"{render_agent(agent)} claims {source} said {render_proposition(heard.proposition)}."

    # Snapshots and generic memory scraps are archived and indexed, but they are
    # too raw to answer from directly. Let a topic-relevant claim card or
    # ignorance handle these until the larger inference/trust system exists.
    return None


def render_source_name(state: LabyrinthState, source: str | None) -> str:
    if source is None:
        return "someone"
    if source == state.player.name:
        return "you"
    agent = state.claimants.get(source)
    if agent is not None:
        return render_agent(agent)
    if has_camel_boundary(source):
        return render_name(source)
    return source



def proposition_focuses_on(proposition: str, subject: str) -> bool:
    normalized_proposition = normalize_alias(proposition)
    subject_forms = {
        normalize_alias(subject),
        normalize_alias(" ".join(words_from_name(subject))),
    }
    subject_forms = {form for form in subject_forms if form}
    return any(
        normalized_proposition == form or normalized_proposition.startswith(form + " ")
        for form in subject_forms
    )

def relevant_memory_entries(agent: Agent, subject: str, raw_topic: str) -> list[MemoryEntry]:
    entries = agent.memory.entries_about(subject)
    if entries:
        return entries
    topic = normalize_alias(raw_topic)
    if not topic:
        return []
    return [entry for entry in agent.memory.entries if topic in normalize_alias(entry.text)]


def canonicalize_topic(state: LabyrinthState, raw_topic: str) -> str:
    candidates: dict[str, Any] = {name: agent for name, agent in state.claimants.items()}
    candidates[state.player.name] = state.player
    for room in state.rooms:
        for door in room.doors.values():
            candidates[door.name] = door
        for cup in room.cups.values():
            candidates[cup.name] = cup
    entity, _ = resolve_named_entity(raw_topic, candidates, "subject")
    if entity is not None and hasattr(entity, "name"):
        return entity.name
    for name in all_subject_names(state):
        if normalize_alias(raw_topic) in {normalize_alias(name), normalize_alias(" ".join(words_from_name(name)))}:
            return name
    return raw_topic


def certainty_rank(certainty: str) -> int:
    return CERTAINTY_ORDER.get(certainty, 0)


def render_proposition(proposition: str) -> str:
    words = proposition.split()
    rendered_words = []
    for word in words:
        stripped = word.strip(".,;:!?()")
        punctuation = word[len(stripped):] if len(stripped) != len(word) else ""
        if stripped and has_camel_boundary(stripped):
            rendered_words.append(render_name(stripped) + punctuation)
        else:
            rendered_words.append(word)
    rendered = " ".join(rendered_words)
    if rendered.endswith("."):
        rendered = rendered[:-1]
    if rendered.startswith("You is not "):
        return "you are not " + rendered[len("You is not "):]
    if rendered.startswith("You is "):
        return "you are " + rendered[len("You is "):]
    return rendered



def has_camel_boundary(word: str) -> bool:
    return any(left.islower() and right.isupper() for left, right in zip(word, word[1:]))

def memory_summary(entry: MemoryEntry) -> str:
    if entry.kind == "heard_claim" and entry.source:
        return f"{entry.source} said, {entry.text}"
    if entry.kind == "snapshot":
        return f"they saw {entry.text}"
    return f"they remember {entry.text}"


def render_topic(topic: str) -> str:
    if has_camel_boundary(topic) and " " not in topic:
        return render_name(topic)
    if topic and topic[0].isupper() and " " not in topic:
        return topic
    return normalize_alias(topic) or topic

def render_turn_count(speed: WordNumber) -> str:
    if speed == ONE:
        return "one turn"
    return f"{render_number(speed)} turns"


def render_turn_ordinal(count: WordNumber) -> str:
    ordinals = {
        "one": "first",
        "two": "second",
        "three": "third",
        "four": "fourth",
        "five": "fifth",
        "six": "sixth",
        "seven": "seventh",
        "eight": "eighth",
        "nine": "ninth",
    }
    cardinal = render_number(count)
    return ordinals.get(cardinal, f"turn {cardinal}")


def present_agents(state: LabyrinthState) -> list[Agent]:
    return [
        agent
        for agent in state.claimants.values()
        if agent.alive and agent.room_index == state.room_index
    ]


def agent_room_index(state: LabyrinthState, agent: Agent) -> int:
    if agent.name == "You":
        return state.room_index
    return agent.room_index


def current_room(state: LabyrinthState) -> Room:
    return state.rooms[state.room_index]


def resolve_agent_name(state: LabyrinthState, raw_name: str) -> tuple[Agent | None, str | None]:
    return resolve_agent_name_from_room(state, raw_name, state.room_index)


def resolve_agent_name_from_room(state: LabyrinthState, raw_name: str, room_index: int) -> tuple[Agent | None, str | None]:
    candidates = {
        agent.name: agent
        for agent in state.claimants.values()
        if agent.alive and agent.room_index == room_index
    }
    entity, error = resolve_named_entity(raw_name, candidates, "person or creature")
    return entity, error


def resolve_cup_name(state: LabyrinthState, agent: Agent, raw_name: str) -> tuple[Cup | None, str | None]:
    room = state.rooms[agent_room_index(state, agent)]
    entity, error = resolve_named_entity(raw_name, room.cups, "cup")
    return entity, error


def resolve_door_name(state: LabyrinthState, agent: Agent, raw_name: str) -> tuple[Door | None, str | None]:
    room = state.rooms[agent_room_index(state, agent)]
    entity, error = resolve_named_entity(raw_name, room.doors, "door")
    return entity, error


def resolve_named_entity(
    raw_name: str,
    candidates: dict[str, Any],
    kind: str,
) -> tuple[Any | None, str | None]:
    alias_index = build_alias_index(candidates)
    normalized = normalize_alias(raw_name)
    compacted = compact_alias(raw_name)

    matches = alias_index.get(normalized)
    if matches is None and compacted != normalized:
        matches = alias_index.get(compacted)

    if not matches:
        return None, None
    if len(matches) == 1:
        return matches[0], None

    choices = ", ".join(render_name(entity.name) for entity in matches)
    return None, f"which {kind} do you mean: {choices}?"


def build_alias_index(candidates: dict[str, Any]) -> dict[str, list[Any]]:
    alias_index: dict[str, list[Any]] = {}
    for canonical_name, entity in candidates.items():
        for alias in derive_aliases(canonical_name, entity):
            alias_index.setdefault(alias, []).append(entity)
    return alias_index


def derive_aliases(canonical_name: str, entity: Any) -> set[str]:
    aliases: set[str] = set()
    names = [canonical_name]
    entity_name = getattr(entity, "name", None)
    if entity_name and entity_name not in names:
        names.append(entity_name)

    for name in names:
        spaced = " ".join(words_from_name(name))
        add_alias_forms(aliases, spaced)
        add_alias_forms(aliases, name)

        words = normalize_alias(spaced).split()
        if len(words) > 1:
            add_alias_forms(aliases, words[0])
            add_alias_forms(aliases, words[-1])

    return aliases


def add_alias_forms(aliases: set[str], text: str) -> None:
    normalized = normalize_alias(text)
    if normalized:
        aliases.add(normalized)
        aliases.add(normalized.replace(" ", ""))


def words_from_name(name: str) -> list[str]:
    words = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|[0-9]+", name)
    if words:
        return words
    return name.split()


def normalize_alias(text: str) -> str:
    lowered = text.lower()
    cleaned = re.sub(r"[^a-z0-9]+", " ", lowered)
    articles = {"a", "an", "the"}
    return " ".join(word for word in cleaned.split() if word not in articles)


def compact_alias(text: str) -> str:
    return normalize_alias(text).replace(" ", "")


def parse_target(command: str, prefix: str) -> str:
    target = command.removeprefix(prefix).strip()
    if target.startswith("through "):
        target = target.removeprefix("through ").strip()
    if target.startswith("the "):
        target = target.removeprefix("the ").strip()
    return "".join(part.capitalize() for part in target.split())


def render_agent(agent: Agent) -> str:
    if agent.name == "You":
        return "you"
    if agent.animal:
        return render_name(agent.name)
    return agent.name


def render_agent_verb(agent: Agent, verb: str) -> str:
    if agent.name == "You":
        return f"you {verb}"
    adverb = action_adverb(agent)
    if verb.endswith("y"):
        rendered_verb = f"{verb[:-1]}ies"
    else:
        suffix = "s"
        if verb.endswith("s"):
            suffix = "es"
        rendered_verb = f"{verb}{suffix}"
    if adverb and verb in {"move", "sip", "ask"}:
        return f"{agent.name} {adverb} {rendered_verb}"
    return f"{agent.name} {rendered_verb}"


def action_adverb(agent: Agent) -> str:
    condition = render_condition_word(agent)
    if condition == "unsure":
        return "unsteadily"
    if condition == "grim":
        return "grimly"
    return ""


def render_agent_action(action: str) -> str:
    if action.startswith("ask "):
        rendered = render_action(action)
        return "asks" + rendered.removeprefix("ask")
    return render_action(action)


def render_action(action: str) -> str:
    words = action.split()
    if not words:
        return action
    if len(words) >= 2 and words[0] == "move":
        return f"move through {render_name(words[1])}"
    if len(words) >= 2 and words[0] == "sip":
        return f"sip {render_name(words[1])}"
    if len(words) >= 4 and words[0] == "ask":
        return f"ask {render_action_subject(words[1])} about {render_action_subject(words[3])}"
    return action


def render_action_subject(name: str) -> str:
    if has_camel_boundary(name):
        return render_name(name)
    return name


def render_name(name: str) -> str:
    words: list[str] = []
    current = ""
    for char in name:
        if char.isupper() and current:
            words.append(current)
            current = char
        else:
            current += char
    if current:
        words.append(current)
    return "the " + " ".join(word.lower() for word in words)
