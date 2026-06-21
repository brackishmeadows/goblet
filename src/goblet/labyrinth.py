from __future__ import annotations
from dataclasses import dataclass, field
import random
import re
from typing import Any, Iterator

from .compare import compare
from .divide import divide_expression
from .increment import increment
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


@dataclass
class AgentMemory:
    entries: list[MemoryEntry] = field(default_factory=list)
    by_subject: dict[str, list[str]] = field(default_factory=dict)
    known_propositions: set[str] = field(default_factory=set)
    trust: dict[str, str] = field(default_factory=dict)
    trust_evidence: dict[str, list[str]] = field(default_factory=dict)

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
    escaped: bool = False


@dataclass
class CommandOutcome:
    lines: list[str]
    advances: bool = True


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
    write("commands: ask, tell, sip, move, push, slap, look, quit")
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
        lines.append(f"- {render_name(cup.name)}: {render_fraction(cup.fifths, FIVE)} full")
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
        return CommandOutcome(render_help(), advances=False)
    if command.startswith("look "):
        return CommandOutcome(resolve_look(state, command), advances=False)
    if command.startswith("recall ") or command.startswith("remember "):
        return CommandOutcome(resolve_recall(state, command), advances=False)

    validation_error = validate_player_command(state, command)
    if validation_error:
        return CommandOutcome([validation_error], advances=False)

    return CommandOutcome(resolve_turn(state, command), advances=True)


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


def render_help() -> list[str]:
    return [
        "actions:",
        "- ask NAME about THING",
        "- ask NAME what/if GOBLET QUESTION",
        "- tell NAME CLAIM",
        "- tell NAME [to] ACTION",
        "- sip CUP (or drink CUP)",
        "- move DOOR (or go DOOR)",
        "- push NAME through DOOR",
        "- slap NAME",
        "- recall THING (or remember THING)",
        "- look NAME",
        "- look",
        "- quit",
    ]


def resolve_look(state: LabyrinthState, command: str) -> list[str]:
    target_raw = command.removeprefix("look ").strip()
    if not target_raw:
        return ["look at whom?"]
    target, error = resolve_agent_name(state, target_raw)
    if error:
        return [error]
    if target is None:
        return [f"you cannot see {render_topic(target_raw)} here"]
    return [f"{render_agent(target)} looks {render_condition_word(target)}."]


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

    return f"unknown action: {command}"


def validate_ask_command(state: LabyrinthState, command: str) -> str | None:
    goblet_parsed = parse_goblet_ask_command(state, command)
    if isinstance(goblet_parsed, GobletAsk):
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
        return None

    parsed = parse_ask_command(state, command)
    if isinstance(parsed, str):
        return parsed
    return None


def validate_tell_command(state: LabyrinthState, command: str) -> str | None:
    parsed = parse_tell_command(state, command)
    if isinstance(parsed, str):
        return parsed
    if isinstance(parsed, TellInstruction):
        if not goal_action_is_available(state, parsed.target, parsed.action):
            return f"{render_agent(parsed.target)} cannot {render_action(parsed.action)} from here"
        return None
    if parsed.subject is None or parsed.proposition is None:
        return f"{render_agent(parsed.target)} does not know how to use that. Tell them a claim about a known thing."
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


RECALL_MEMORY_KINDS = {"heard_claim", "claim_made", "reported_claim", "goblet_claim", "action", "outcome"}


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
        if recall_entry_matches(entry, subject, raw_forms):
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


def recall_entry_matches(entry: MemoryEntry, subject: str, raw_forms: set[str]) -> bool:
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
    return any(form and (form in searchable or singularize_topic(form) in searchable) for form in raw_forms)


def recall_topic_forms(raw_topic: str) -> set[str]:
    normalized = normalize_alias(raw_topic)
    forms = {normalized, compact_alias(raw_topic), singularize_topic(normalized)}
    return {form for form in forms if form}


def singularize_topic(topic: str) -> str:
    if topic.endswith("ies") and len(topic) > 3:
        return topic[:-3] + "y"
    if topic.endswith("s") and len(topic) > 1:
        return topic[:-1]
    return topic


def recall_entry_summary(state: LabyrinthState, entry: MemoryEntry) -> str:
    if entry.kind == "heard_claim" and entry.source:
        return f"{render_source_name(state, entry.source)} said: {strip_recalled_claim_prefix(state, entry)}"
    if entry.kind == "goblet_claim" and entry.source:
        return f"{render_source_name(state, entry.source)} answered: {entry.text}"
    if entry.kind == "reported_claim" and entry.source:
        return f"{render_source_name(state, entry.source)} reported: {entry.text}"
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

    subject, topic_error = resolve_topic_subject(state, topic)
    if topic_error:
        return topic_error
    if subject is None:
        return f"{render_agent(target)} would not know what {render_topic(topic)} means"

    return target, topic, subject


def is_health_topic(topic: str) -> bool:
    normalized = normalize_alias(topic)
    return normalized in {"health", "condition", "status", "state", "wounds", "hurt"}


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
    return [ask_line, claim]


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
    claim = answer_world_subject(state, question.target, question.subject, question.proposition)
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
    return [question_text, claim]


def resolve_ask(state: LabyrinthState, asker: Agent, command: str) -> list[str]:
    parsed = parse_ask_command_for_agent(state, asker, command)
    if isinstance(parsed, str):
        return [parsed]
    target, topic, subject = parsed

    claim = answer_world_subject(state, target, subject)

    rendered_topic = render_ask_topic(topic, subject)
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

    if asker.name == "You":
        return [f"you ask {render_agent(target)} about {rendered_topic}", claim]
    return [f"{render_agent_verb(asker, 'ask')} {render_agent(target)} about {rendered_topic}", claim]


def render_ask_topic(topic: str, subject: str) -> str:
    if is_health_topic(topic):
        return "health"
    return render_name(subject) if has_camel_boundary(subject) else render_topic(subject)


def answer_world_subject(state: LabyrinthState, target: Agent, subject: str, proposition: str | None = None) -> str:
    subject_agent = state.claimants.get(subject)
    if subject_agent is not None and not subject_agent.animal:
        return f"{render_agent(target)} claims {subject_agent.name} looks {render_condition_word(subject_agent)}."
    material_claim = material_identity_claim(state, target, subject, proposition)
    if material_claim is not None:
        return material_claim
    memory_answer = answer_from_memory(state, target, subject)
    deck_answer = topic_relevant_round_claim(state, target, subject)
    if memory_answer:
        return speak_claim(target, memory_answer, distort_world_claim(state, target, memory_answer, subject))
    if deck_answer:
        return deck_answer
    return ignorance_claim(target, subject)


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
        return generic_distorted_claim(agent, claim)
    body = claim[len(prefix):].rstrip(".")
    normalized = normalize_alias(body)
    if subject in state.claimants or subject == state.player.name:
        if "not trusted" in normalized or "untrusted" in normalized or "unreliable" in normalized:
            return f"{prefix}{render_name(subject) if has_camel_boundary(subject) else subject} is trusted."
        if "trusted" in normalized or "honest" in normalized:
            return f"{prefix}{render_name(subject) if has_camel_boundary(subject) else subject} is not trusted."
        if "liar" in normalized or "lies" in normalized:
            return f"{prefix}{render_name(subject) if has_camel_boundary(subject) else subject} is honest."
        if "reckless" in normalized:
            return f"{prefix}{render_name(subject) if has_camel_boundary(subject) else subject} is cautious."
    if is_cup_subject(state, subject):
        rendered = render_name(subject)
        if "poison" in normalized:
            return f"{prefix}{rendered} is safe."
        if "antidote" in normalized:
            return f"{prefix}{rendered} is poison."
        if "elixir" in normalized or "restores" in normalized or "full health" in normalized:
            return f"{prefix}{rendered} is poison."
        if "empty" in normalized:
            return f"{prefix}{rendered} is full."
        if "full" in normalized:
            return f"{prefix}{rendered} is empty."
        if "grants haste" in normalized or "haste" in normalized or "quick" in normalized:
            return f"{prefix}{rendered} slows the drinker."
        if "sharpens truth" in normalized or "truth" in normalized or "clear" in normalized:
            return f"{prefix}{rendered} dulls truth."
        if "stupor" in normalized or "slow" in normalized:
            return f"{prefix}{rendered} grants haste."
        if "sleep" in normalized or "asleep" in normalized or "drowsy" in normalized:
            return f"{prefix}{rendered} grants haste."
        if "safe" in normalized:
            return f"{prefix}{rendered} is poison."
    if is_door_subject(state, subject):
        rendered = render_name(subject)
        if "leads to peril" in normalized or "unsafe" in normalized or "hungry" in normalized:
            return f"{prefix}{rendered} is safe."
        if "safe" in normalized or "kind" in normalized:
            return f"{prefix}{rendered} leads to peril."
        if "leads onward" in normalized or "advances" in normalized:
            return f"{prefix}{rendered} leads to peril."
        if "exit" in normalized:
            return f"{prefix}{rendered} leads to peril."
    if "was refuted" in normalized:
        return claim.replace(" was refuted", " seems true")
    if "seems true" in normalized:
        return claim.replace(" seems true", " was refuted")
    if "testing whether" in normalized:
        return claim
    return generic_distorted_claim(agent, claim)


def resolve_tell(state: LabyrinthState, speaker: Agent, command: str) -> list[str]:
    parsed = parse_tell_command(state, command)
    if isinstance(parsed, str):
        return [parsed]
    if isinstance(parsed, TellInstruction):
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
        agent.sleeping = True
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
    agent.sleeping = False
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
    wake_text = "you wake" if agent.name == "You" else f"{render_agent(agent)} wakes"
    return [text, wake_text]


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
        return not isinstance(parsed, str)
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
    present = [agent for agent in present_agents(state) if agent.name not in {observer.name, source}]
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
    return supports_outcome(supposed, observed)


def contradicts_hypothesis(supposed: str, observed: str) -> bool:
    if "is safe" in supposed and "leads to peril" in observed:
        return True
    if "leads onward" in supposed and "leads to peril" in observed:
        return True
    if "is poison" in supposed and "is antidote" in observed:
        return True
    if "grants haste" in supposed and "is poison" in observed:
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
        f"cups: {', '.join(render_name(cup.name) + ' ' + render_fraction(cup.fifths, FIVE) + ' full' for cup in room.cups.values())}; "
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
        subjects=sorted(entry_subjects),
    )
    observer.memory.remember(entry)
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
        elif supports_outcome(claim_text, proposition):
            observer.memory.trust[trust_key] = "trusted"
            observer.memory.trust_evidence.setdefault(trust_key, []).extend([claim.id, outcome.id])


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
    if topic in {"pushing", "violence", "coercion"}:
        return topic
    return render_name(topic)


def answer_from_trust(agent: Agent, subject: str) -> str | None:
    for trust_key, judgement in agent.memory.trust.items():
        source, topic = trust_key.split(":", 1)
        if source != subject:
            continue
        source_text = "you" if source == "You" else source
        topic_text = render_trust_topic(topic)
        if judgement == "distrusted":
            if source == "You":
                return f"you are not trusted about {topic_text}"
            return f"{source_text} is not trusted about {topic_text}"
        if judgement == "trusted":
            if source == "You":
                return f"you are trusted about {topic_text}"
            return f"{source_text} is trusted about {topic_text}"
    return None

def answer_from_memory(state: LabyrinthState, agent: Agent, raw_topic: str) -> str | None:
    subject = raw_topic if raw_topic in all_subject_names(state) else canonicalize_topic(state, raw_topic)
    entries = relevant_memory_entries(agent, subject, raw_topic)
    if not entries:
        return None
    entries = sorted(entries, key=lambda entry: (certainty_rank(entry.certainty), entry.sequence), reverse=True)
    focused_entries = [entry for entry in entries if entry.proposition and proposition_focuses_on(entry.proposition, subject)]

    # Person-subject questions are usually asking for a judgement, not a raw
    # action log. Prefer trust/person reports before generic observed actions
    # like "Bram asked Vey about a door."
    if subject in state.claimants or subject == state.player.name:
        trust_claim = answer_from_trust(agent, subject)
        if trust_claim:
            return f"{render_agent(agent)} claims {trust_claim}."
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
        trust_claim = answer_from_trust(agent, subject)
        if trust_claim:
            return f"{render_agent(agent)} claims {trust_claim}."

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
