import random
import sys

from .arithmetic import arithmetic_expression, trace_arithmetic_expression
from .divide import divide_expression, trace_divide_expression
from .labyrinth import (
    run_labyrinth_interactive,
    run_labyrinth_script,
    show_labyrinth_post,
    start_labyrinth_post,
    step_labyrinth_post,
)
from .liars import liars_expression, trace_liars_expression
from .multiply import multiply_expression, trace_multiply_expression
from .prime import prime_expression, trace_prime_expression
from .random_range import random_number_between
from .relation import relation_expression, trace_relation_expression


def main() -> int:
    if len(sys.argv) < 2:
        print('usage: python -m goblet [--trace] "twenty seven divided by five"')
        print('       python -m goblet --random "one" "twenty"')
        print('       python -m goblet [--trace] --prime "seven"')
        print("       python -m goblet [--trace] --liars puzzle.goblet-liars")
        print("       python -m goblet --labyrinth script.txt")
        print("       python -m goblet --labyrinth-play")
        print("       python -m goblet --labyrinth-random script.txt [seed]")
        print("       python -m goblet --labyrinth-random-play [seed]")
        print("       python -m goblet --labyrinth-post state.goblet start [seed]")
        print("       python -m goblet --labyrinth-post state.goblet show")
        print("       python -m goblet --labyrinth-post state.goblet COMMAND...")
        return 2

    args = sys.argv[1:]
    trace = False
    if args and args[0] == "--trace":
        trace = True
        args = args[1:]

    if args and args[0] == "--random":
        if len(args) != 3:
            print('usage: python -m goblet --random "one" "twenty"')
            return 2
        try:
            print(random_number_between(args[1], args[2]))
        except ValueError as exc:
            print(f"error: {exc}")
            return 1
        return 0

    if args and args[0] == "--liars":
        if len(args) != 2:
            print("usage: python -m goblet [--trace] --liars puzzle.goblet-liars")
            return 2
        try:
            text = read_text(args[1])
            if trace:
                print("\n".join(trace_liars_expression(text)))
            else:
                print(liars_expression(text))
        except OSError as exc:
            print(f"error: {exc}")
            return 1
        except ValueError as exc:
            print(f"error: {exc}")
            return 1
        return 0

    if args and args[0] == "--labyrinth":
        if len(args) != 2:
            print("usage: python -m goblet --labyrinth script.txt")
            return 2
        try:
            commands = read_script(args[1])
            print("\n".join(run_labyrinth_script(commands)))
        except OSError as exc:
            print(f"error: {exc}")
            return 1
        return 0

    if args and args[0] == "--labyrinth-play":
        run_labyrinth_interactive()
        return 0

    if args and args[0] == "--labyrinth-random":
        if len(args) not in (2, 3):
            print("usage: python -m goblet --labyrinth-random script.txt [seed]")
            return 2
        seed = args[2] if len(args) == 3 else random_seed_text()
        try:
            commands = read_script(args[1])
            print(f"random seed: {seed}")
            print("\n".join(run_labyrinth_script(commands, random_seed=seed)))
        except OSError as exc:
            print(f"error: {exc}")
            return 1
        return 0

    if args and args[0] == "--labyrinth-random-play":
        if len(args) not in (1, 2):
            print("usage: python -m goblet --labyrinth-random-play [seed]")
            return 2
        seed = args[1] if len(args) == 2 else random_seed_text()
        print(f"random seed: {seed}")
        run_labyrinth_interactive(random_seed=seed)
        return 0

    if args and args[0] == "--labyrinth-post":
        if len(args) < 3:
            print("usage: python -m goblet --labyrinth-post state.goblet start [seed]")
            print("       python -m goblet --labyrinth-post state.goblet show")
            print("       python -m goblet --labyrinth-post state.goblet COMMAND...")
            return 2
        state_path = args[1]
        action = args[2]
        try:
            if action == "start":
                if len(args) > 4:
                    print("usage: python -m goblet --labyrinth-post state.goblet start [seed]")
                    return 2
                seed = args[3] if len(args) == 4 else None
                print("\n".join(start_labyrinth_post(state_path, seed)))
                return 0
            if action == "reset":
                if len(args) > 4:
                    print("usage: python -m goblet --labyrinth-post state.goblet reset [seed]")
                    return 2
                seed = args[3] if len(args) == 4 else None
                print("\n".join(start_labyrinth_post(state_path, seed)))
                return 0
            if action == "show":
                if len(args) != 3:
                    print("usage: python -m goblet --labyrinth-post state.goblet show")
                    return 2
                print("\n".join(show_labyrinth_post(state_path)))
                return 0
            command = " ".join(args[2:])
            print("\n".join(step_labyrinth_post(state_path, command)))
            return 0
        except OSError as exc:
            print(f"error: {exc}")
            return 1
        except ValueError as exc:
            print(f"error: {exc}")
            return 1

    if args and args[0] == "--prime":
        if len(args) < 2:
            print('usage: python -m goblet [--trace] --prime "seven"')
            return 2
        phrase = " ".join(args[1:])
        try:
            if trace:
                print("\n".join(trace_prime_expression(phrase)))
            else:
                print(prime_expression(phrase))
        except ValueError as exc:
            print(f"error: {exc}")
            return 1
        return 0

    if not args:
        print('usage: python -m goblet [--trace] "twenty seven divided by five"')
        print('       python -m goblet --random "one" "twenty"')
        print('       python -m goblet [--trace] --prime "seven"')
        print("       python -m goblet [--trace] --liars puzzle.goblet-liars")
        print("       python -m goblet --labyrinth script.txt")
        print("       python -m goblet --labyrinth-play")
        print("       python -m goblet --labyrinth-random script.txt [seed]")
        print("       python -m goblet --labyrinth-random-play [seed]")
        print("       python -m goblet --labyrinth-post state.goblet start [seed]")
        print("       python -m goblet --labyrinth-post state.goblet show")
        print("       python -m goblet --labyrinth-post state.goblet COMMAND...")
        return 2

    expression = " ".join(args)
    try:
        if trace:
            print("\n".join(trace_expression(expression)))
        else:
            print(evaluate_expression(expression))
    except ValueError as exc:
        print(f"error: {exc}")
        return 1
    return 0


def evaluate_expression(expression: str) -> str:
    if is_arithmetic_expression(expression):
        return arithmetic_expression(expression)
    if is_relation_expression(expression):
        return relation_expression(expression)
    if " divided by " in expression.lower():
        return divide_expression(expression)
    if " times " in expression.lower() or " multiplied by " in expression.lower():
        return multiply_expression(expression)
    raise ValueError("expected addition, subtraction, division, multiplication, or comparison expression")


def trace_expression(expression: str) -> list[str]:
    if is_arithmetic_expression(expression):
        return trace_arithmetic_expression(expression)
    if is_relation_expression(expression):
        return trace_relation_expression(expression)
    if " divided by " in expression.lower():
        return trace_divide_expression(expression)
    if " times " in expression.lower() or " multiplied by " in expression.lower():
        return trace_multiply_expression(expression)
    raise ValueError("expected addition, subtraction, division, multiplication, or comparison expression")


def is_relation_expression(expression: str) -> bool:
    lowered = expression.lower()
    return any(
        marker in lowered
        for marker in (
            " is greater than ",
            " is less than ",
            " is equal to ",
            " equals ",
            " is at least ",
            " is at most ",
        )
    )


def is_arithmetic_expression(expression: str) -> bool:
    lowered = expression.lower()
    return " plus " in lowered or " minus " in lowered


def random_seed_text() -> str:
    return str(random.SystemRandom().randrange(1, 1000000))


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def read_script(path: str) -> list[str]:
    lines = []
    for line in read_text(path).splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(stripped)
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
