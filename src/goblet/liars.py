from dataclasses import dataclass
from itertools import product


HONEST = "honest"
LIAR = "liar"
KINDS = (HONEST, LIAR)


@dataclass(frozen=True)
class Statement:
    speaker: str
    target: str
    target_kind: str
    source: str


@dataclass(frozen=True)
class LiarPuzzle:
    people: tuple[str, ...]
    statements: tuple[Statement, ...]


def liars_expression(text: str) -> str:
    puzzle = parse_liars(text)
    worlds = surviving_worlds(puzzle)
    if not worlds:
        return "contradiction\nno possible worlds"
    if len(worlds) == 1:
        return "forced\npossible world:\n- " + render_world(worlds[0], puzzle.people)
    lines = ["ambiguous", "possible worlds:"]
    lines.extend(f"- {render_world(world, puzzle.people)}" for world in worlds)
    return "\n".join(lines)


def trace_liars_expression(text: str) -> list[str]:
    puzzle = parse_liars(text)
    lines: list[str] = render_question(puzzle)
    rejected: dict[str, dict[bool, list[tuple[str, dict[str, str]]]]] = {}
    for index, world in enumerate(enumerate_worlds(puzzle.people), start=1):
        case_name = render_ordinal(index)
        if lines:
            lines.append("")
        lines.append(f"{case_name}: suppose that {render_supposition(world, puzzle.people)}.")
        contradiction = first_contradiction(puzzle, world)
        if contradiction is None:
            lines.append("this case holds")
            continue
        statement, statement_truth = contradiction
        statement_key = render_statement(statement)
        rejected.setdefault(statement_key, {}).setdefault(statement_truth, []).append(
            (case_name, world)
        )
        lines.append(render_statement(statement))
        lines.append(
            f"but we supposed {statement.speaker} "
            f"{render_kind(world[statement.speaker])}, so we cannot allow this"
        )
    survivors = surviving_worlds(puzzle)
    lines.append("")
    if not survivors:
        lines.append("contradiction")
        lines.append("no possible worlds")
    elif len(survivors) == 1:
        lines.append("forced")
        lines.append(f"surviving world: {render_world(survivors[0], puzzle.people)}")
    else:
        lines.append("ambiguous")
        lines.append("surviving worlds:")
        lines.extend(f"- {render_world(world, puzzle.people)}" for world in survivors)
    if rejected:
        lines.append("")
        lines.append("rejected worlds:")
        for statement_text, truth_groups in rejected.items():
            lines.append(statement_text)
            for statement_truth in (True, False):
                worlds = truth_groups.get(statement_truth)
                if not worlds:
                    continue
                lines.append(
                    f"- if this is {render_truth(statement_truth)}, "
                    f"we must reject {render_world_reference(worlds, puzzle.people)}"
                )
    return lines


def parse_liars(text: str) -> LiarPuzzle:
    people: list[str] = []
    statements: list[Statement] = []
    section: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.endswith(":"):
            section = line[:-1].lower()
            if section not in ("people", "statements"):
                raise ValueError(f"unsupported liars section: {line[:-1]}")
            continue
        if section == "people":
            if line in people:
                raise ValueError(f"duplicate person: {line}")
            people.append(line)
            continue
        if section == "statements":
            statements.append(parse_statement(line))
            continue
        raise ValueError("expected people: or statements: section")

    if not people:
        raise ValueError("liars puzzle needs at least one person")
    if not statements:
        raise ValueError("liars puzzle needs at least one statement")

    known_people = set(people)
    for statement in statements:
        if statement.speaker not in known_people:
            raise ValueError(f"unknown speaker: {statement.speaker}")
        if statement.target not in known_people:
            raise ValueError(f"unknown target: {statement.target}")

    return LiarPuzzle(tuple(people), tuple(statements))


def parse_statement(line: str) -> Statement:
    parts = line.split()
    if len(parts) < 4 or parts[1] != "calls":
        raise ValueError(f"unsupported statement: {line}")
    speaker, target = parts[0], parts[2]
    kind_phrase = " ".join(parts[3:])
    if kind_phrase == "a liar":
        target_kind = LIAR
    elif kind_phrase == HONEST:
        target_kind = HONEST
    else:
        raise ValueError(f"unsupported kind: {kind_phrase}")
    if target_kind not in KINDS:
        raise ValueError(f"unsupported kind: {target_kind}")
    return Statement(speaker, target, target_kind, line)


def surviving_worlds(puzzle: LiarPuzzle) -> list[dict[str, str]]:
    return [
        world
        for world in enumerate_worlds(puzzle.people)
        if first_contradiction(puzzle, world) is None
    ]


def enumerate_worlds(people: tuple[str, ...]) -> list[dict[str, str]]:
    return [
        dict(zip(people, kinds))
        for kinds in product(KINDS, repeat=len(people))
    ]


def first_contradiction(
    puzzle: LiarPuzzle, world: dict[str, str]
) -> tuple[Statement, bool] | None:
    for statement in puzzle.statements:
        statement_truth = world[statement.target] == statement.target_kind
        speaker_honest = world[statement.speaker] == HONEST
        if speaker_honest != statement_truth:
            return statement, statement_truth
    return None


def render_world(world: dict[str, str], people: tuple[str, ...]) -> str:
    return ", ".join(f"{person} {world[person]}" for person in people)


def render_case_world(case_name: str, world: dict[str, str], people: tuple[str, ...]) -> str:
    return f"{case_name}: {render_world(world, people)}"


def render_question(puzzle: LiarPuzzle) -> list[str]:
    claimant_count = render_count(len(puzzle.people))
    claimant_noun = "claimant"
    if len(puzzle.people) != 1:
        claimant_noun = "claimants"
    people = render_sentence_parts(list(puzzle.people))
    calls = " ".join(f"{render_statement(statement)}." for statement in puzzle.statements)
    return [f"There are {claimant_count} {claimant_noun}, {people}. {calls} How can this be?"]


def render_count(count: int) -> str:
    words = {
        1: "one",
        2: "two",
        3: "three",
        4: "four",
        5: "five",
        6: "six",
        7: "seven",
        8: "eight",
        9: "nine",
    }
    return words.get(count, str(count))


def render_ordinal(count: int) -> str:
    words = {
        1: "first",
        2: "second",
        3: "third",
        4: "fourth",
        5: "fifth",
        6: "sixth",
        7: "seventh",
        8: "eighth",
        9: "ninth",
    }
    return words.get(count, f"case {count}")


def render_statement(statement: Statement) -> str:
    return f"{statement.speaker} calls {statement.target} {render_kind(statement.target_kind)}"


def render_supposition(world: dict[str, str], people: tuple[str, ...]) -> str:
    return render_sentence_parts(
        [f"{person} is {render_kind(world[person])}" for person in people]
    )


def render_world_reference(
    entries: list[tuple[str, dict[str, str]]], people: tuple[str, ...]
) -> str:
    labels = [case_name for case_name, _world in entries]
    world_noun = "world"
    if len(entries) != 1:
        world_noun = "worlds"
    return (
        f"the {render_sentence_parts(labels)} {world_noun} "
        f"({render_shared_where_clause(entries, people)})"
    )


def render_shared_where_clause(
    entries: list[tuple[str, dict[str, str]]], people: tuple[str, ...]
) -> str:
    shared_parts: list[str] = []
    for person in people:
        values = {world[person] for _case_name, world in entries}
        if len(values) == 1:
            value = next(iter(values))
            shared_parts.append(f"{person} is {render_kind(value)}")
    if shared_parts:
        return "where " + render_sentence_parts(shared_parts)
    case_parts = [
        f"{case_name}: {render_supposition(world, people)}"
        for case_name, world in entries
    ]
    return "where " + "; ".join(case_parts)


def render_sentence_parts(parts: list[str]) -> str:
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def render_kind(kind: str) -> str:
    if kind == LIAR:
        return "a liar"
    return kind


def render_truth(value: bool) -> str:
    if value:
        return "true"
    return "false"
