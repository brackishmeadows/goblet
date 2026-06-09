import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from goblet.arithmetic import arithmetic_expression, trace_arithmetic_expression
from goblet.compare import compare
from goblet.divide import divide_expression, trace_divide_expression
from goblet.increment import increment
from goblet.multiply import multiply_expression, trace_multiply_expression
from goblet.normalize import parse_number
from goblet.prime import prime_expression, trace_prime_expression
from goblet.random_range import (
    parse_lower_bound,
    parse_upper_bound,
    random_number_between,
    values_between,
)
from goblet.render import render_fraction, render_mixed, render_number
from goblet.relation import relation_expression, trace_relation_expression
from goblet.subtract import subtract
from random import Random


class SymbolicArithmeticTests(unittest.TestCase):
    def assert_divides(self, expression, expected):
        self.assertEqual(divide_expression(expression), expected)

    def test_parse_and_render(self):
        examples = [
            "zero",
            "one",
            "ten",
            "nineteen",
            "twenty seven",
            "one hundred",
            "one hundred and five",
            "nine hundred and ninety nine",
        ]
        for phrase in examples:
            with self.subTest(phrase=phrase):
                self.assertEqual(render_number(parse_number(phrase)), phrase)
        self.assertEqual(render_number(parse_number("an unknown number")), "an unknown number")

    def test_parse_normalizes_and_and_hyphens(self):
        self.assertEqual(render_number(parse_number("a hundred and five")), "one hundred and five")
        self.assertEqual(render_number(parse_number("twenty-seven")), "twenty seven")

    def test_compare(self):
        self.assertEqual(compare(parse_number("seven"), parse_number("three")), "greater")
        self.assertEqual(compare(parse_number("one hundred"), parse_number("ninety nine")), "greater")
        self.assertEqual(compare(parse_number("forty two"), parse_number("forty two")), "equal")
        self.assertEqual(compare(parse_number("six"), parse_number("ten")), "less")

    def test_relation_examples(self):
        cases = [
            ("seven is greater than three", "true"),
            ("seven is less than three", "false"),
            ("forty two equals forty two", "true"),
            ("seven divided by three is greater than two", "true"),
            ("twenty seven divided by five is greater than five", "true"),
            ("a large number divided by five is greater than one hundred", "true"),
            (
                "a large number divided by five is greater than two hundred",
                "true unless it is two hundred",
            ),
            ("six divided by a large number is less than one", "true"),
            ("six divided by a large number equals zero", "false"),
            ("at least two hundred is greater than one hundred", "true"),
            ("at least two hundred is greater than two hundred", "true unless it is two hundred"),
            ("at most five is less than six", "true"),
            ("at most five is less than five", "likely true; false only if it is five"),
            (
                "at most five is greater than four",
                "likely false; true for values greater than four and at most five",
            ),
            ("at most five equals five", "likely false; true only if it is five"),
            ("at least five equals five", "true only if it is five"),
            ("six divided by a large number is at most one", "true"),
            ("a large number divided by five is at least two hundred", "true"),
            ("an unknown number is greater than five", "unknown"),
            ("an unknown number equals an unknown number", "unknown"),
        ]
        for expression, expected in cases:
            with self.subTest(expression=expression):
                self.assertEqual(relation_expression(expression), expected)

    def test_relation_trace_explains_unknowns(self):
        self.assertEqual(
            trace_relation_expression("a large number divided by five is greater than two hundred"),
            [
                "a large number divided by five is greater than two hundred",
                "left range: at least two hundred",
                "right range: exactly two hundred",
                "comparison becomes true unless it is two hundred",
                "not guaranteed because the ranges overlap",
                "could be true if the left value lands above the right value",
                "could be false if the left value lands at or below the right value",
            ],
        )

        self.assertEqual(
            trace_relation_expression("at most five is less than five"),
            [
                "at most five is less than five",
                "left range: at most five",
                "right range: exactly five",
                "comparison becomes likely true; false only if it is five",
                "true region: at least zero and less than five",
                "false region: at least five and at most five",
                "not guaranteed because the ranges overlap",
                "could be true if the left value lands below the right value",
                "could be false if the left value lands at or above the right value",
            ],
        )

        self.assertEqual(
            trace_relation_expression("at most five is greater than four"),
            [
                "at most five is greater than four",
                "left range: at most five",
                "right range: exactly four",
                "comparison becomes likely false; true for values greater than four and at most five",
                "true region: greater than four and at most five",
                "false region: at least zero and at most four",
                "not guaranteed because the ranges overlap",
                "could be true if the left value lands above the right value",
                "could be false if the left value lands at or below the right value",
            ],
        )

        self.assertEqual(
            trace_relation_expression("an unknown number is greater than five"),
            [
                "an unknown number is greater than five",
                "left range: an unknown number",
                "right range: exactly five",
                "comparison becomes unknown",
                "unknown because a value could not be placed",
                "an unknown number may be less than, equal to, or greater than the other side",
            ],
        )

    def test_subtract(self):
        cases = [
            ("seven", "three", "four"),
            ("one hundred five", "six", "ninety nine"),
            ("one hundred", "one", "ninety nine"),
            ("nine hundred ninety nine", "twenty seven", "nine hundred and seventy two"),
        ]
        for left, right, expected in cases:
            with self.subTest(left=left, right=right):
                result = subtract(parse_number(left), parse_number(right))
                self.assertEqual(render_number(result), expected)

    def test_public_addition_and_subtraction(self):
        cases = [
            ("seven plus three", "ten"),
            ("seven minus three", "four"),
            ("nine hundred and ninety nine plus one", "a large number"),
            ("one half plus one third", "five sixths"),
            ("one half plus one half", "one"),
            ("two thirds minus one third", "one third"),
            ("one and one half plus two thirds", "two and one sixth"),
            ("five and two fifths plus one third", "five and eleven fifteenths"),
            (
                "one over nine hundred and ninety nine plus one over nine hundred and ninety eight",
                "an unknown number",
            ),
            ("at most five plus three", "at least three and at most eight"),
            ("at least five plus three", "at least eight"),
            ("at most five plus at most three", "at most eight"),
            ("at least five plus at most three", "at least five"),
            ("at least five minus three", "at least two"),
            ("at most five minus three", "at most two when the left value is at least three"),
            (
                "at most five minus at most three",
                "at most five when the left value is at least the right value",
            ),
        ]
        for expression, expected in cases:
            with self.subTest(expression=expression):
                self.assertEqual(arithmetic_expression(expression), expected)

        with self.assertRaisesRegex(ValueError, "subtraction would be less than zero"):
            arithmetic_expression("at most two minus five")

        with self.assertRaisesRegex(ValueError, "subtraction would be less than zero"):
            arithmetic_expression("one third minus one half")

        with self.assertRaisesRegex(ValueError, "cannot subtract an unbounded symbolic value"):
            arithmetic_expression("five minus at least three")

    def test_fraction_trace_mode(self):
        self.assertEqual(
            trace_arithmetic_expression("one half plus one third"),
            [
                "one half plus one third",
                "one half needs three to share a denominator",
                "one times three becomes three",
                "two times three becomes six",
                "one half becomes three sixths",
                "one third needs two to share a denominator",
                "one times two becomes two",
                "three times two becomes six",
                "one third becomes two sixths",
                "three sixths plus two sixths becomes five sixths",
                "five sixths is already reduced",
                "one half plus one third becomes five sixths",
            ],
        )

        self.assertEqual(
            trace_arithmetic_expression("two thirds minus one half"),
            [
                "two thirds minus one half",
                "two thirds needs two to share a denominator",
                "two times two becomes four",
                "three times two becomes six",
                "two thirds becomes four sixths",
                "one half needs three to share a denominator",
                "one times three becomes three",
                "two times three becomes six",
                "one half becomes three sixths",
                "four sixths minus three sixths becomes one sixth",
                "one sixth is already reduced",
                "two thirds minus one half becomes one sixth",
            ],
        )

    def test_division_examples(self):
        cases = [
            ("zero divided by one", "zero"),
            ("seven divided by three", "two and one third"),
            ("twenty seven divided by five", "five and two fifths"),
            ("one divided by nine", "one ninth"),
            ("nine divided by three", "three"),
            ("one hundred divided by ten", "ten"),
            ("one hundred five divided by six", "seventeen and one half"),
            ("one divided by two", "one half"),
            ("two divided by four", "one half"),
            ("four divided by six", "two thirds"),
            ("one divided by four", "one quarter"),
            ("three divided by four", "three quarters"),
            ("ten divided by four", "two and one half"),
            ("twenty divided by eight", "two and one half"),
            ("one divided by one hundred", "one hundredth"),
            ("one divided by twenty one", "one over twenty one"),
            ("two divided by twenty one", "two over twenty one"),
            ("two divided by one hundred five", "two over one hundred and five"),
            ("nine hundred ninety nine divided by twenty seven", "thirty seven"),
            ("nine hundred ninety nine divided by one", "nine hundred and ninety nine"),
            (
                "a large number divided by five",
                "at least two hundred",
            ),
            (
                "a large number divided by six",
                "at least one hundred and sixty six and two thirds",
            ),
            (
                "six divided by a large number",
                "at most six over a large number",
            ),
            (
                "zero divided by a large number",
                "zero",
            ),
        ]
        for expression, expected in cases:
            with self.subTest(expression=expression):
                self.assert_divides(expression, expected)

    def test_multiplication_examples(self):
        cases = [
            ("zero times nine", "zero"),
            ("seven times six", "forty two"),
            ("twelve times twelve", "one hundred and forty four"),
            ("thirty seven multiplied by twenty seven", "nine hundred and ninety nine"),
            ("one hundred times ten", "a large number"),
            ("nine hundred and ninety nine times two", "a large number"),
        ]
        for expression, expected in cases:
            with self.subTest(expression=expression):
                self.assertEqual(multiply_expression(expression), expected)

    def test_prime_examples(self):
        cases = [
            ("zero", "zero is not prime"),
            ("one", "one is not prime"),
            ("two", "two is prime"),
            ("seven", "seven is prime"),
            ("nine", "nine is not prime; divisor is three"),
            ("forty nine", "forty nine is not prime; divisor is seven"),
            ("nine hundred and ninety seven", "nine hundred and ninety seven is prime"),
        ]
        for phrase, expected in cases:
            with self.subTest(phrase=phrase):
                self.assertEqual(prime_expression(phrase), expected)

    def test_errors(self):
        with self.assertRaisesRegex(ValueError, "division by zero"):
            divide_expression("six divided by zero")

        with self.assertRaisesRegex(ValueError, "cannot divide two unbounded symbolic values"):
            divide_expression("a large number divided by a large number")

        with self.assertRaisesRegex(ValueError, "unsupported number phrase"):
            divide_expression("one thousand divided by one")

    def test_trace_mode(self):
        self.assertEqual(
            trace_divide_expression("twenty seven divided by five"),
            [
                "twenty seven divided by five",
                "twenty seven minus five becomes twenty two; quotient becomes one",
                "twenty two minus five becomes seventeen; quotient becomes two",
                "seventeen minus five becomes twelve; quotient becomes three",
                "twelve minus five becomes seven; quotient becomes four",
                "seven minus five becomes two; quotient becomes five",
                "two is less than five",
                "two fifths is already reduced",
                "twenty seven divided by five becomes five and two fifths",
            ],
        )

        trace = trace_divide_expression("four divided by six")
        self.assertIn("greatest common divisor becomes two", trace)
        self.assertEqual(trace[-1], "four divided by six becomes two thirds")

        self.assertEqual(
            trace_divide_expression("a large number divided by five"),
            [
                "a large number divided by five",
                "a large number means at least one more than nine hundred and ninety nine",
                "a large number divided by five becomes at least two hundred",
            ],
        )

        self.assertEqual(
            trace_divide_expression("six divided by a large number"),
            [
                "six divided by a large number",
                "a large number means at least one more than nine hundred and ninety nine",
                "six divided by a large number becomes at most six over a large number",
            ],
        )

    def test_multiplication_trace_mode(self):
        self.assertEqual(
            trace_multiply_expression("three times four"),
            [
                "three times four",
                "zero plus three becomes three; count becomes one",
                "three plus three becomes six; count becomes two",
                "six plus three becomes nine; count becomes three",
                "nine plus three becomes twelve; count becomes four",
                "three times four becomes twelve",
            ],
        )

        trace = trace_multiply_expression("one hundred times ten")
        self.assertEqual(trace[-1], "one hundred times ten becomes a large number")

    def test_prime_trace_mode(self):
        self.assertEqual(
            trace_prime_expression("nine"),
            [
                "nine is at least two",
                "nine divided by two leaves one",
                "nine divided by three leaves zero",
                "nine is not prime; divisor is three",
            ],
        )

        trace = trace_prime_expression("seven")
        self.assertEqual(trace[-1], "seven is prime")

    def test_random_range(self):
        values = values_between(parse_number("eight"), parse_number("twelve"))
        self.assertEqual(
            [render_number(value) for value in values],
            ["eight", "nine", "ten", "eleven", "twelve"],
        )
        result = random_number_between("one hundred and five", "one hundred and ten", Random(7))
        self.assertEqual(result, "one hundred and seven")

        with self.assertRaisesRegex(ValueError, "lower bound is greater"):
            random_number_between("ten", "one", Random(1))

    def test_random_range_with_bounds(self):
        self.assertEqual(render_number(parse_lower_bound("at least eight")), "eight")
        self.assertEqual(render_number(parse_upper_bound("at most twelve")), "twelve")
        self.assertEqual(
            render_number(parse_upper_bound("at most a large number")),
            "nine hundred and ninety nine",
        )

        result = random_number_between("at least eight", "at most twelve", Random(7))
        self.assertEqual(result, "ten")

        with self.assertRaisesRegex(ValueError, "lower bound cannot use at most"):
            random_number_between("at most eight", "twelve", Random(1))

        with self.assertRaisesRegex(ValueError, "upper bound cannot use at least"):
            random_number_between("eight", "at least twelve", Random(1))

        with self.assertRaisesRegex(ValueError, "lower bound has no supported finite values"):
            random_number_between("at least a large number", "a large number", Random(1))

    def test_large_number_rendering(self):
        large = increment(parse_number("nine hundred and ninety nine"))
        unknown = parse_number("an unknown number")
        self.assertEqual(render_number(large), "a large number")
        self.assertEqual(render_number(increment(large)), "a large number")
        self.assertEqual(render_number(increment(unknown)), "an unknown number")
        self.assertEqual(render_fraction(large, parse_number("five")), "a large number")
        self.assertEqual(render_fraction(unknown, parse_number("five")), "an unknown number")
        self.assertEqual(render_fraction(parse_number("one"), large), "one over a large number")
        self.assertEqual(
            render_mixed(
                parse_number("nine hundred and ninety nine"),
                parse_number("one"),
                parse_number("nine hundred and ninety nine"),
            ),
            "nine hundred and ninety nine and one over nine hundred and ninety nine",
        )


if __name__ == "__main__":
    unittest.main()
