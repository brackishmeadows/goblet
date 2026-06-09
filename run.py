import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))

from goblet.divide import divide_expression, trace_divide_expression
from goblet.arithmetic import arithmetic_expression, trace_arithmetic_expression
from goblet.multiply import multiply_expression, trace_multiply_expression
from goblet.prime import prime_expression, trace_prime_expression
from goblet.random_range import random_number_between
from goblet.relation import relation_expression, trace_relation_expression


def main() -> int:
    if len(sys.argv) < 2:
        print('usage: python run.py [--trace] "twenty seven divided by five"')
        print('       python run.py --random "one" "twenty"')
        print('       python run.py [--trace] --prime "seven"')
        return 2

    args = sys.argv[1:]
    trace = False
    if args and args[0] == "--trace":
        trace = True
        args = args[1:]

    if args and args[0] == "--random":
        if len(args) != 3:
            print('usage: python run.py --random "one" "twenty"')
            return 2
        try:
            print(random_number_between(args[1], args[2]))
        except ValueError as exc:
            print(f"error: {exc}")
            return 1
        return 0

    if args and args[0] == "--prime":
        if len(args) < 2:
            print('usage: python run.py [--trace] --prime "seven"')
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
        print('usage: python run.py [--trace] "twenty seven divided by five"')
        print('       python run.py --random "one" "twenty"')
        print('       python run.py [--trace] --prime "seven"')
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


if __name__ == "__main__":
    raise SystemExit(main())
