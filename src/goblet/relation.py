from __future__ import annotations

from dataclasses import dataclass
from functools import cache

from .add import add
from .compare import compare
from .divide import (
    divide,
    divide_large_lower_bound,
    parse_division_expression,
    quotient_and_remainder,
    reduce_fraction,
)
from .fraction import parse_rational as parse_fraction_rational
from .increment import increment
from .multiply import multiply
from .normalize import parse_number
from .render import render_fraction, render_mixed, render_number
from .words import LARGE_NUMBER, ONE, SymbolicNumber, WordNumber, ZERO, is_large_number, is_unknown_number

TWO = WordNumber("zero", "zero", "two")
ROOT_CANDIDATE_CEILING = WordNumber("zero", "three", "two")


@dataclass(frozen=True)
class Rational:
    numerator: WordNumber
    denominator: WordNumber


@dataclass(frozen=True)
class Bound:
    kind: str
    value: Rational | WordNumber | None = None


@dataclass(frozen=True)
class Interval:
    lower: Bound
    upper: Bound
    lower_open: bool = False
    upper_open: bool = False


@dataclass(frozen=True)
class RootBounds:
    radicand: WordNumber
    exact: Rational | None
    lower: Rational | None
    upper: Rational | None


def relation_expression(expression: str) -> str:
    left_text, operator, right_text = parse_relation_expression(expression)
    left = parse_interval(left_text)
    right = parse_interval(right_text)
    return explain_relation(left, operator, right)


def trace_relation_expression(expression: str) -> list[str]:
    left_text, operator, right_text = parse_relation_expression(expression)
    left = parse_interval(left_text)
    right = parse_interval(right_text)
    result = evaluate_relation(left, operator, right)
    explanation = explain_relation(left, operator, right)
    steps = [expression]
    steps.extend(irrational_trace_steps(left_text))
    steps.extend(irrational_trace_steps(right_text))
    steps.extend(
        [
            f"left range: {render_interval(left)}",
            f"right range: {render_interval(right)}",
            f"comparison becomes {explanation}",
        ]
    )
    if result == "unknown":
        if has_unknown_bound(left) or has_unknown_bound(right):
            steps.append("unknown because a value could not be placed")
            steps.append("an unknown number may be less than, equal to, or greater than the other side")
        else:
            regions = truth_regions(left, operator, right)
            if regions:
                true_region, false_region = regions
                steps.append(f"true region: {true_region}")
                steps.append(f"false region: {false_region}")
            true_case, false_case = uncertainty_cases(operator)
            steps.append("not guaranteed because the ranges overlap")
            steps.append(f"could be true if {true_case}")
            steps.append(f"could be false if {false_case}")
    return steps


def explain_relation(left: Interval, operator: str, right: Interval) -> str:
    result = evaluate_relation(left, operator, right)
    if result != "unknown":
        return result

    likelihood = finite_likelihood_explanation(left, operator, right)
    if likelihood:
        return likelihood

    exception = endpoint_exception(left, operator, right)
    if exception:
        return exception
    return "unknown"


def parse_relation_expression(expression: str) -> tuple[str, str, str]:
    lowered = expression.lower()
    operators = (
        (" is greater than ", "greater than"),
        (" is less than ", "less than"),
        (" is equal to ", "equals"),
        (" equals ", "equals"),
        (" is at least ", "at least"),
        (" is at most ", "at most"),
    )
    for marker, operator in operators:
        if marker in lowered:
            left, right = lowered.split(marker, 1)
            return left.strip(), operator, right.strip()
    raise ValueError("expected symbolic comparison expression")


def parse_interval(text: str) -> Interval:
    if text.startswith("square root of "):
        return square_root_interval(parse_square_root_radicand(text))
    if text.startswith("at least "):
        base = parse_interval(text[len("at least ") :])
        return Interval(base.lower, infinity_bound(), lower_open=base.lower_open)
    if text.startswith("at most "):
        base = parse_interval(text[len("at most ") :])
        return Interval(finite_bound(ZERO), base.upper, upper_open=base.upper_open)
    if " divided by " in text:
        return parse_division_interval(text)

    try:
        value = parse_number(text)
    except ValueError:
        return exact_interval(rational_from_fraction_text(text))
    if is_unknown_number(value):
        return Interval(unknown_bound(), unknown_bound())
    if is_large_number(value):
        return Interval(large_floor_bound(), infinity_bound())
    return exact_interval(rational_from_whole(value))


def parse_division_interval(text: str) -> Interval:
    dividend, divisor = parse_division_expression(text)
    if is_large_number(dividend) and is_large_number(divisor):
        raise ValueError("cannot compare division of two unbounded symbolic values")
    if is_large_number(dividend):
        quotient, numerator, denominator = divide_large_lower_bound(divisor)
        lower = rational_from_mixed(quotient, numerator, denominator)
        return Interval(finite_bound(lower), infinity_bound())
    if is_large_number(divisor):
        if dividend == ZERO:
            return exact_interval(rational_from_whole(ZERO))
        return Interval(above_zero_bound(), finite_over_large_bound(dividend))

    quotient, numerator, denominator = divide(dividend, divisor)
    return exact_interval(rational_from_mixed(quotient, numerator, denominator))


def evaluate_relation(left: Interval, operator: str, right: Interval) -> str:
    if operator == "greater than":
        return evaluate_greater_than(left, right)
    if operator == "less than":
        return evaluate_less_than(left, right)
    if operator == "equals":
        return evaluate_equals(left, right)
    if operator == "at least":
        return evaluate_at_least(left, right)
    if operator == "at most":
        return evaluate_at_most(left, right)
    raise ValueError(f"unsupported comparison operator: {operator}")


def endpoint_exception(left: Interval, operator: str, right: Interval) -> str | None:
    if operator == "less than" and starts_at_zero(left) and is_exact_finite(right):
        if compare_bounds(left.upper, right.lower) == "equal":
            return f"true unless it is {render_bound(right.lower)}"

    if operator == "greater than" and is_exact_finite(right) and left.upper.kind == "infinity":
        if compare_bounds(left.lower, right.lower) == "equal":
            return f"true unless it is {render_bound(right.lower)}"

    if operator == "equals" and starts_at_zero(left) and is_exact_finite(right):
        if compare_bounds(left.upper, right.lower) == "equal":
            return f"true only if it is {render_bound(right.lower)}"

    if operator == "equals" and is_exact_finite(right) and left.upper.kind == "infinity":
        if compare_bounds(left.lower, right.lower) == "equal":
            return f"true only if it is {render_bound(right.lower)}"

    return None


def finite_likelihood_explanation(left: Interval, operator: str, right: Interval) -> str | None:
    if not is_finite_bounded(left) or not is_exact_finite(right):
        return None
    threshold = _rational(right.lower)
    if compare_rationals(threshold, _rational(left.lower)) == "less":
        return None
    if compare_rationals(threshold, _rational(left.upper)) == "greater":
        return None

    if operator == "equals":
        return f"likely false; true only if it is {render_rational(threshold)}"

    midpoint = midpoint_rational(left)
    if midpoint is None:
        return None

    threshold_vs_midpoint = compare_rationals(threshold, midpoint)
    if operator in ("greater than", "at least"):
        return explain_likelihood_for_greater(left, threshold, threshold_vs_midpoint, operator)
    if operator in ("less than", "at most"):
        return explain_likelihood_for_less(left, threshold, threshold_vs_midpoint, operator)
    return None


def truth_regions(left: Interval, operator: str, right: Interval) -> tuple[str, str] | None:
    if not is_finite_bounded(left) or not is_exact_finite(right):
        return None
    threshold = _rational(right.lower)
    if compare_rationals(threshold, _rational(left.lower)) == "less":
        return None
    if compare_rationals(threshold, _rational(left.upper)) == "greater":
        return None

    if operator == "greater than":
        return render_greater_range(left, threshold, operator), render_at_most_range(left, threshold)
    if operator == "at least":
        return render_greater_range(left, threshold, operator), render_less_range(left, threshold, "less than")
    if operator == "less than":
        return render_less_range(left, threshold, operator), render_at_least_range(left, threshold)
    if operator == "at most":
        return render_less_range(left, threshold, operator), render_greater_range(left, threshold, "greater than")
    if operator == "equals":
        return f"exactly {render_rational(threshold)}", (
            f"anything else in {render_interval(left)}"
        )
    return None


def explain_likelihood_for_greater(
    interval: Interval, threshold: Rational, threshold_vs_midpoint: str, operator: str
) -> str:
    if compare_rationals(threshold, _rational(interval.lower)) == "equal" and operator == "greater than":
        return f"likely true; false only if it is {render_rational(threshold)}"
    if threshold_vs_midpoint == "less":
        return f"likely true; false for values {render_at_most_range(interval, threshold)}"
    if threshold_vs_midpoint == "greater":
        return f"likely false; true for values {render_greater_range(interval, threshold, operator)}"
    return f"unknown; true for values {render_greater_range(interval, threshold, operator)}"


def explain_likelihood_for_less(
    interval: Interval, threshold: Rational, threshold_vs_midpoint: str, operator: str
) -> str:
    if compare_rationals(threshold, _rational(interval.upper)) == "equal" and operator == "less than":
        return f"likely true; false only if it is {render_rational(threshold)}"
    if threshold_vs_midpoint == "greater":
        return f"likely true; false for values {render_at_least_range(interval, threshold)}"
    if threshold_vs_midpoint == "less":
        return f"likely false; true for values {render_less_range(interval, threshold, operator)}"
    return f"unknown; true for values {render_less_range(interval, threshold, operator)}"


def evaluate_greater_than(left: Interval, right: Interval) -> str:
    lower_vs_upper = compare_bounds(left.lower, right.upper)
    if lower_vs_upper == "greater":
        return "true"
    if lower_vs_upper == "equal" and (left.lower_open or right.upper_open):
        return "true"
    upper_vs_lower = compare_bounds(left.upper, right.lower)
    if upper_vs_lower in ("less", "equal"):
        return "false"
    return "unknown"


def evaluate_less_than(left: Interval, right: Interval) -> str:
    upper_vs_lower = compare_bounds(left.upper, right.lower)
    if upper_vs_lower == "less":
        return "true"
    if upper_vs_lower == "equal" and (left.upper_open or right.lower_open):
        return "true"
    lower_vs_upper = compare_bounds(left.lower, right.upper)
    if lower_vs_upper in ("greater", "equal"):
        return "false"
    return "unknown"


def evaluate_equals(left: Interval, right: Interval) -> str:
    if is_exact_finite(left) and is_exact_finite(right):
        return "true" if compare_bounds(left.lower, right.lower) == "equal" else "false"
    if compare_bounds(left.upper, right.lower) == "less":
        return "false"
    if compare_bounds(left.upper, right.lower) == "equal" and (left.upper_open or right.lower_open):
        return "false"
    if compare_bounds(left.lower, right.upper) == "greater":
        return "false"
    if compare_bounds(left.lower, right.upper) == "equal" and (left.lower_open or right.upper_open):
        return "false"
    return "unknown"


def evaluate_at_least(left: Interval, right: Interval) -> str:
    lower_vs_upper = compare_bounds(left.lower, right.upper)
    if lower_vs_upper in ("greater", "equal"):
        return "true"
    upper_vs_lower = compare_bounds(left.upper, right.lower)
    if upper_vs_lower == "less":
        return "false"
    if upper_vs_lower == "equal" and (left.upper_open or right.lower_open):
        return "false"
    return "unknown"


def evaluate_at_most(left: Interval, right: Interval) -> str:
    upper_vs_lower = compare_bounds(left.upper, right.lower)
    if upper_vs_lower in ("less", "equal"):
        return "true"
    lower_vs_upper = compare_bounds(left.lower, right.upper)
    if lower_vs_upper == "greater":
        return "false"
    if lower_vs_upper == "equal" and (left.lower_open or right.upper_open):
        return "false"
    return "unknown"


def compare_bounds(left: Bound, right: Bound) -> str:
    if left.kind == "unknown" or right.kind == "unknown":
        return "unknown"

    if left.kind == "infinity" or right.kind == "infinity":
        if left.kind == right.kind:
            return "equal"
        return "greater" if left.kind == "infinity" else "less"

    if left.kind == "large_floor" or right.kind == "large_floor":
        if left.kind == right.kind:
            return "equal"
        return "greater" if left.kind == "large_floor" else "less"

    if left.kind == "above_zero" or right.kind == "above_zero":
        return compare_above_zero_bounds(left, right)

    if left.kind == "finite_over_large" or right.kind == "finite_over_large":
        return compare_large_denominator_bounds(left, right)

    if left.kind == "finite" and right.kind == "finite":
        return compare_rationals(_rational(left), _rational(right))

    return "unknown"


def compare_above_zero_bounds(left: Bound, right: Bound) -> str:
    if left.kind == "above_zero" and right.kind == "above_zero":
        return "unknown"

    if left.kind == "above_zero" and right.kind == "finite":
        right_value = _rational(right)
        if compare_rationals(right_value, rational_from_whole(ZERO)) == "equal":
            return "greater"
        if compare_rationals(right_value, rational_from_whole(ONE)) in ("equal", "greater"):
            return "less"
        return "unknown"

    if left.kind == "finite" and right.kind == "above_zero":
        left_value = _rational(left)
        if compare_rationals(left_value, rational_from_whole(ZERO)) == "equal":
            return "less"
        if compare_rationals(left_value, rational_from_whole(ONE)) in ("equal", "greater"):
            return "greater"
        return "unknown"

    return "unknown"


def compare_large_denominator_bounds(left: Bound, right: Bound) -> str:
    if left.kind == "finite_over_large" and right.kind == "finite_over_large":
        return "unknown"

    if left.kind == "finite_over_large" and right.kind == "finite":
        right_value = _rational(right)
        if compare_rationals(right_value, rational_from_whole(ZERO)) == "equal":
            return "greater"
        if compare_rationals(right_value, rational_from_whole(ONE)) in ("equal", "greater"):
            return "less"
        return "unknown"

    if left.kind == "finite" and right.kind == "finite_over_large":
        left_value = _rational(left)
        if compare_rationals(left_value, rational_from_whole(ZERO)) == "equal":
            return "less"
        if compare_rationals(left_value, rational_from_whole(ONE)) in ("equal", "greater"):
            return "greater"
        return "unknown"

    return "unknown"


def compare_rationals(left: Rational, right: Rational) -> str:
    left_product = multiply(left.numerator, right.denominator)
    right_product = multiply(right.numerator, left.denominator)
    if is_large_number(left_product) and is_large_number(right_product):
        return "unknown"
    if is_large_number(left_product):
        return "greater"
    if is_large_number(right_product):
        return "less"
    return compare(left_product, right_product)


def irrational_trace_steps(text: str) -> list[str]:
    if not text.startswith("square root of "):
        return []
    radicand = parse_square_root_radicand(text)
    bounds = find_square_root_bounds(radicand)
    root_text = render_square_root(radicand)
    steps = [f"finding bounds for {root_text}"]
    if bounds.exact is not None:
        steps.extend(square_root_bound_steps(bounds.exact, radicand, "exactly"))
    else:
        if bounds.lower is not None:
            steps.extend(square_root_bound_steps(bounds.lower, radicand, "below"))
        if bounds.upper is not None:
            steps.extend(square_root_bound_steps(bounds.upper, radicand, "above"))
    steps.append(f"{root_text} is {render_interval(square_root_interval(radicand))}")
    return steps


def square_root_bound_steps(value: Rational, radicand: WordNumber, side: str) -> list[str]:
    numerator_square = multiply(value.numerator, value.numerator)
    denominator_square = multiply(value.denominator, value.denominator)
    scaled_denominator_square = multiply(radicand, denominator_square)
    comparison = compare_square_products(numerator_square, scaled_denominator_square)
    relation_word = "less than" if comparison == "less" else "greater than"
    if comparison == "equal":
        relation_word = "equal to"
    root_text = render_square_root(radicand)
    return [
        f"testing {render_improper_rational(value)}",
        (
            f"{render_number(value.numerator)} times {render_number(value.numerator)} "
            f"becomes {render_number(numerator_square)}"
        ),
        (
            f"{render_number(value.denominator)} times {render_number(value.denominator)} "
            f"becomes {render_number(denominator_square)}"
        ),
        (
            f"{render_number(radicand)} times {render_number(denominator_square)} "
            f"becomes {render_number(scaled_denominator_square)}"
        ),
        (
            f"{render_number(numerator_square)} is {relation_word} "
            f"{render_number(scaled_denominator_square)}"
        ),
        f"{render_improper_rational(value)} is {side} {root_text}",
    ]


def square_root_interval(radicand: WordNumber) -> Interval:
    bounds = find_square_root_bounds(radicand)
    if bounds.exact is not None:
        return exact_interval(bounds.exact)
    if bounds.lower is None or bounds.upper is None:
        raise ValueError(f"cannot place {render_square_root(radicand)}")
    return Interval(
        finite_bound(bounds.lower),
        finite_bound(bounds.upper),
        lower_open=True,
        upper_open=True,
    )


def parse_square_root_radicand(text: str) -> WordNumber:
    radicand = parse_number(text[len("square root of ") :])
    if is_unknown_number(radicand) or is_large_number(radicand):
        raise ValueError("square root needs a finite supported number")
    return radicand


@cache
def find_square_root_bounds(radicand: WordNumber) -> RootBounds:
    lower = None
    upper = None
    for denominator in root_candidate_words():
        if denominator == ZERO:
            continue
        for numerator in root_candidate_words():
            reduced_numerator, reduced_denominator = reduce_fraction(numerator, denominator)
            candidate = Rational(reduced_numerator, reduced_denominator)
            comparison = compare_fraction_square_to_radicand(candidate, radicand)
            if comparison == "equal":
                return RootBounds(radicand, candidate, None, None)
            if comparison == "less":
                if lower is None or compare_rationals(candidate, lower) == "greater":
                    lower = candidate
            if comparison == "greater":
                if upper is None or compare_rationals(candidate, upper) == "less":
                    upper = candidate
                break
            if comparison == "unknown":
                break
    return RootBounds(radicand, None, lower, upper)


@cache
def compare_fraction_square_to_radicand(value: Rational, radicand: WordNumber) -> str:
    numerator_square = multiply(value.numerator, value.numerator)
    denominator_square = multiply(value.denominator, value.denominator)
    scaled_denominator_square = multiply(radicand, denominator_square)
    return compare_square_products(numerator_square, scaled_denominator_square)


def compare_square_products(left: SymbolicNumber, right: SymbolicNumber) -> str:
    if is_large_number(left) and is_large_number(right):
        return "unknown"
    if is_large_number(left):
        return "greater"
    if is_large_number(right):
        return "less"
    return compare(left, right)


@cache
def root_candidate_words() -> tuple[WordNumber, ...]:
    values = []
    current = ZERO
    while compare(current, ROOT_CANDIDATE_CEILING) != "greater":
        values.append(current)
        current = increment(current)
    return tuple(values)


def render_square_root(radicand: WordNumber) -> str:
    return f"square root of {render_number(radicand)}"


def render_interval(value: Interval) -> str:
    if value.lower.kind == "unknown" or value.upper.kind == "unknown":
        return "an unknown number"
    if value.lower == value.upper and not value.lower_open and not value.upper_open:
        return f"exactly {render_bound(value.lower)}"
    if value.upper.kind == "infinity":
        return f"at least {render_bound(value.lower)}"
    if value.lower.kind == "above_zero":
        return f"greater than zero and at most {render_bound(value.upper)}"
    if value.lower_open and value.upper_open:
        return (
            f"greater than {render_open_bound(value.lower)} "
            f"and less than {render_open_bound(value.upper)}"
        )
    if value.lower_open:
        return f"greater than {render_open_bound(value.lower)} and at most {render_bound(value.upper)}"
    if value.upper_open:
        return f"at least {render_bound(value.lower)} and less than {render_open_bound(value.upper)}"
    if value.lower.kind == "finite" and compare_rationals(
        _rational(value.lower), rational_from_whole(ZERO)
    ) == "equal":
        return f"at most {render_bound(value.upper)}"
    return f"from {render_bound(value.lower)} through {render_bound(value.upper)}"


def render_bound(value: Bound) -> str:
    if value.kind == "finite":
        return render_rational(_rational(value))
    if value.kind == "finite_over_large":
        if isinstance(value.value, WordNumber):
            return f"{render_number(value.value)} over a large number"
        return "a finite number over a large number"
    if value.kind == "above_zero":
        return "more than zero"
    if value.kind == "large_floor":
        return "a large number"
    if value.kind == "infinity":
        return "unbounded above"
    if value.kind == "unknown":
        return "an unknown number"
    return "unknown"


def render_open_bound(value: Bound) -> str:
    if value.kind == "finite":
        return render_improper_rational(_rational(value))
    return render_bound(value)


def render_rational(value: Rational) -> str:
    quotient, remainder = quotient_and_remainder(value.numerator, value.denominator)
    return render_mixed(quotient, remainder, value.denominator)


def render_improper_rational(value: Rational) -> str:
    return render_fraction(value.numerator, value.denominator)


def render_greater_range(interval: Interval, threshold: Rational, operator: str) -> str:
    lower_word = "at least" if operator == "at least" else "greater than"
    return f"{lower_word} {render_rational(threshold)} and at most {render_bound(interval.upper)}"


def render_less_range(interval: Interval, threshold: Rational, operator: str) -> str:
    upper_word = "at most" if operator == "at most" else "less than"
    return f"at least {render_bound(interval.lower)} and {upper_word} {render_rational(threshold)}"


def render_at_most_range(interval: Interval, threshold: Rational) -> str:
    return f"at least {render_bound(interval.lower)} and at most {render_rational(threshold)}"


def render_at_least_range(interval: Interval, threshold: Rational) -> str:
    return f"at least {render_rational(threshold)} and at most {render_bound(interval.upper)}"


def midpoint_rational(interval: Interval) -> Rational | None:
    if not is_finite_bounded(interval):
        return None
    left = _rational(interval.lower)
    right = _rational(interval.upper)
    left_scaled = multiply(left.numerator, right.denominator)
    right_scaled = multiply(right.numerator, left.denominator)
    if is_large_number(left_scaled) or is_large_number(right_scaled):
        return None
    numerator = add(left_scaled, right_scaled)
    denominator_product = multiply(left.denominator, right.denominator)
    if is_large_number(numerator) or is_large_number(denominator_product):
        return None
    denominator = multiply(denominator_product, TWO)
    if is_large_number(denominator):
        return None
    return Rational(numerator, denominator)


def uncertainty_cases(operator: str) -> tuple[str, str]:
    if operator == "greater than":
        return "the left value lands above the right value", (
            "the left value lands at or below the right value"
        )
    if operator == "less than":
        return "the left value lands below the right value", (
            "the left value lands at or above the right value"
        )
    if operator == "equals":
        return "both values land on the same exact value", (
            "the values land on different exact values"
        )
    if operator == "at least":
        return "the left value lands on or above the right value", (
            "the left value lands below the right value"
        )
    if operator == "at most":
        return "the left value lands on or below the right value", (
            "the left value lands above the right value"
        )
    return "the relation holds", "the relation does not hold"


def rational_from_whole(value: WordNumber) -> Rational:
    return Rational(value, ONE)


def rational_from_mixed(
    quotient: SymbolicNumber, numerator: WordNumber, denominator: WordNumber
) -> Rational:
    if is_large_number(quotient):
        raise ValueError("cannot convert unbounded quotient to finite rational")
    whole = multiply(quotient, denominator)
    if is_large_number(whole):
        raise ValueError("finite rational overflowed")
    improper = add(whole, numerator)
    if is_large_number(improper):
        raise ValueError("finite rational overflowed")
    return Rational(improper, denominator)


def rational_from_fraction_text(text: str) -> Rational:
    value = parse_fraction_rational(text)
    if is_large_number(value.numerator) or is_large_number(value.denominator):
        raise ValueError("unbounded fraction is not supported in relation comparisons")
    return Rational(value.numerator, value.denominator)


def exact_interval(value: Rational) -> Interval:
    bound = finite_bound(value)
    return Interval(bound, bound)


def finite_bound(value: Rational | WordNumber) -> Bound:
    if isinstance(value, WordNumber):
        value = rational_from_whole(value)
    return Bound("finite", value)


def finite_over_large_bound(value: WordNumber) -> Bound:
    return Bound("finite_over_large", value)


def above_zero_bound() -> Bound:
    return Bound("above_zero")


def large_floor_bound() -> Bound:
    return Bound("large_floor")


def infinity_bound() -> Bound:
    return Bound("infinity")


def unknown_bound() -> Bound:
    return Bound("unknown")


def is_exact_finite(value: Interval) -> bool:
    return (
        value.lower == value.upper
        and value.lower.kind == "finite"
        and not value.lower_open
        and not value.upper_open
    )


def is_finite_bounded(value: Interval) -> bool:
    return value.lower.kind == "finite" and value.upper.kind == "finite"


def has_unknown_bound(value: Interval) -> bool:
    return value.lower.kind == "unknown" or value.upper.kind == "unknown"


def starts_at_zero(value: Interval) -> bool:
    if value.lower.kind != "finite":
        return False
    return compare_rationals(_rational(value.lower), rational_from_whole(ZERO)) == "equal"


def _rational(bound: Bound) -> Rational:
    if bound.kind != "finite" or not isinstance(bound.value, Rational):
        raise ValueError("expected finite rational bound")
    return bound.value
