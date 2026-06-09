import ast
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "goblet"


ARITHMETIC_MODULES = [
    "add.py",
    "arithmetic.py",
    "compare.py",
    "divide.py",
    "fraction.py",
    "increment.py",
    "multiply.py",
    "normalize.py",
    "prime.py",
    "random_range.py",
    "relation.py",
    "render.py",
    "subtract.py",
    "words.py",
]


class NoCheatingTests(unittest.TestCase):
    def test_no_numeric_parsing_or_forbidden_arithmetic_operators(self):
        offenders = []
        for module in ARITHMETIC_MODULES:
            path = SRC / module
            tree = ast.parse(path.read_text(), filename=str(path))
            visitor = CheatVisitor(module)
            visitor.visit(tree)
            offenders.extend(visitor.offenders)

        self.assertEqual(offenders, [])


class CheatVisitor(ast.NodeVisitor):
    forbidden_calls = {
        "abs",
        "divmod",
        "eval",
        "float",
        "int",
        "round",
        "sum",
    }

    forbidden_binops = (
        ast.Div,
        ast.FloorDiv,
        ast.Mod,
        ast.Mult,
        ast.Pow,
    )

    def __init__(self, module: str):
        self.module = module
        self.offenders: list[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        name = call_name(node.func)
        if name in self.forbidden_calls:
            self.offenders.append(f"{self.module}:{node.lineno} forbidden call {name}()")
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if isinstance(node.op, self.forbidden_binops):
            op_name = type(node.op).__name__
            self.offenders.append(f"{self.module}:{node.lineno} forbidden operator {op_name}")
        self.generic_visit(node)


def call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


if __name__ == "__main__":
    unittest.main()
