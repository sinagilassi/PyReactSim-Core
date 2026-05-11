from __future__ import annotations

# SECTION: Imports
import ast
import math
import re
from typing import Any, Callable, Dict, Iterable, Literal, Optional, cast

from pyreactsim_core.models import rXs


# SECTION: Expression constants
# NOTE: Regex extracts state references such as C["CO2-g"] and P["H2-g"].
STATE_REF_RE = re.compile(r"\b([CP])\s*\[\s*(['\"])(.*?)\2\s*\]")
COMPONENT_ID_RE = re.compile(r"^[A-Za-z0-9()+\-]+-[A-Za-z0-9]+$")

# NOTE: Functions exposed directly inside YAML expression evaluation.
SAFE_FUNCTIONS: Dict[str, Callable[..., Any]] = {
    "abs": abs,
    "acos": math.acos,
    "acosh": math.acosh,
    "asin": math.asin,
    "asinh": math.asinh,
    "atan": math.atan,
    "atan2": math.atan2,
    "atanh": math.atanh,
    "ceil": math.ceil,
    "copysign": math.copysign,
    "cos": math.cos,
    "cosh": math.cosh,
    "degrees": math.degrees,
    "erf": math.erf,
    "erfc": math.erfc,
    "exp": math.exp,
    "expm1": math.expm1,
    "fabs": math.fabs,
    "factorial": math.factorial,
    "floor": math.floor,
    "fmod": math.fmod,
    "gamma": math.gamma,
    "hypot": math.hypot,
    "isfinite": math.isfinite,
    "isinf": math.isinf,
    "isnan": math.isnan,
    "ldexp": math.ldexp,
    "lgamma": math.lgamma,
    "log": math.log,
    "log10": math.log10,
    "log1p": math.log1p,
    "log2": math.log2,
    "radians": math.radians,
    "remainder": math.remainder,
    "sin": math.sin,
    "sinh": math.sinh,
    "pow": pow,
    "sqrt": math.sqrt,
    "tan": math.tan,
    "tanh": math.tanh,
    "trunc": math.trunc,
}

# NOTE: Attribute access is restricted to non-private names on math.
SAFE_MATH_NAMES: Dict[str, Any] = {
    name: value
    for name, value in vars(math).items()
    if not name.startswith("_")
}


# SECTION: Exceptions
class RateExpressionError(ValueError):
    """Raised when a YAML reaction-rate expression is invalid or unsafe."""


def validate_component_ids(value: Any) -> list[str]:
    """
    Validate COMPONENTS metadata and normalize it to a list of formula-state ids.

    Expected format:
    - list of strings, e.g. ["CO2-g", "H2-g", "CH3OH-g"]
    """
    if value is None:
        return []
    if not isinstance(value, list):
        raise RateExpressionError("COMPONENTS must be a list of strings.")

    ids: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise RateExpressionError("COMPONENTS entries must be strings.")
        comp_id = item.strip()
        if not comp_id:
            raise RateExpressionError("COMPONENTS entries must be non-empty strings.")
        if not COMPONENT_ID_RE.match(comp_id):
            raise RateExpressionError(
                f"Invalid COMPONENTS entry '{comp_id}'. Expected format 'Formula-State'."
            )
        if comp_id not in seen:
            seen.add(comp_id)
            ids.append(comp_id)
    return ids


# SECTION: Runtime state access
class StateValues(dict):
    # NOTE: Provides C["id"] or P["id"] access to current X.value entries.
    def __init__(self, Xs: rXs, expected_basis: Literal["C", "P"]):
        super().__init__()
        self._xs = Xs
        self._expected_basis = expected_basis

    def __getitem__(self, key: str) -> float | int:
        if key not in self._xs:
            raise KeyError(
                f"State '{key}' is not available in this rate expression.")
        return self._xs[key].value


# SECTION: Restricted AST validator
class RestrictedExpressionValidator(ast.NodeVisitor):
    # NOTE: Keep YAML expressions to assignment, arithmetic, state refs, and math.
    allowed_nodes = (
        ast.Expression,
        ast.Assign,
        ast.Name,
        ast.Load,
        ast.Store,
        ast.Constant,
        ast.BinOp,
        ast.UnaryOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.Mod,
        ast.USub,
        ast.UAdd,
        ast.Subscript,
        ast.Call,
        ast.Attribute,
    )

    def visit(self, node: ast.AST) -> Any:
        # NOTE: Reject unsupported Python syntax before runtime compilation.
        if not isinstance(node, self.allowed_nodes):
            raise RateExpressionError(
                f"Unsupported expression syntax: {node.__class__.__name__}"
            )
        return super().visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        # NOTE: Each expression line must bind exactly one normal variable name.
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            raise RateExpressionError(
                "Only simple variable assignments are allowed.")
        target = cast(ast.Name, node.targets[0])
        if target.id.startswith("__"):
            raise RateExpressionError(
                f"Unsafe name '{target.id}' is not allowed.")
        self.visit(node.value)

    def visit_Name(self, node: ast.Name) -> None:
        # NOTE: Dunder names are blocked to prevent Python object escape hatches.
        if node.id.startswith("__"):
            raise RateExpressionError(
                f"Unsafe name '{node.id}' is not allowed.")

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # NOTE: Attribute access is only allowed for safe math.<name> members.
        if not isinstance(node.value, ast.Name) or node.value.id != "math":
            raise RateExpressionError(
                "Only math.<function> attribute access is allowed.")
        if node.attr.startswith("_") or node.attr not in SAFE_MATH_NAMES:
            raise RateExpressionError(f"math.{node.attr} is not allowed.")

    def visit_Call(self, node: ast.Call) -> None:
        # NOTE: Only known safe functions may be called; no kwargs or dynamic calls.
        if node.keywords:
            raise RateExpressionError(
                "Keyword arguments are not allowed in expressions.")

        func = node.func
        if isinstance(func, ast.Name):
            if func.id not in SAFE_FUNCTIONS:
                raise RateExpressionError(
                    f"Function '{func.id}' is not allowed.")
        elif isinstance(func, ast.Attribute):
            self.visit(func)
        else:
            raise RateExpressionError("Only named math functions are allowed.")

        for arg in node.args:
            self.visit(arg)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        # NOTE: Subscripts are limited to C["state-id"] and P["state-id"].
        if not isinstance(node.value, ast.Name) or node.value.id not in {"C", "P"}:
            raise RateExpressionError(
                "Only C['state-id'] and P['state-id'] are allowed.")
        if not isinstance(node.slice, ast.Constant) or not isinstance(node.slice.value, str):
            raise RateExpressionError(
                "State references must use string literal keys.")


# SECTION: Reaction order inference
class OrderInferer(ast.NodeVisitor):
    # NOTE: Best-effort dependency tracker for simple products and powers.
    def __init__(self) -> None:
        self.deps: Dict[str, Dict[str, float]] = {}
        self.complex = False

    def infer(self, assignment_nodes: Iterable[ast.Assign], final_var: str) -> Dict[str, float]:
        # NOTE: Process assignments sequentially so later variables can reuse prior deps.
        for node in assignment_nodes:
            target = cast(ast.Name, node.targets[0]).id
            self.deps[target] = self._expr_deps(node.value)
        return self.deps.get(final_var, {})

    def _expr_deps(self, node: ast.AST) -> Dict[str, float]:
        # NOTE: State refs start with first-order dependency.
        if isinstance(node, ast.Subscript):
            if (
                isinstance(node.value, ast.Name)
                and node.value.id in {"C", "P"}
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                return {node.slice.value: 1.0}
            self.complex = True
            return {}

        if isinstance(node, ast.Name):
            # NOTE: Plain names inherit dependencies from previous assignments.
            return dict(self.deps.get(node.id, {}))

        if isinstance(node, ast.Constant):
            return {}

        if isinstance(node, ast.UnaryOp):
            # NOTE: Unary +/- does not change reaction-order dependencies.
            return self._expr_deps(node.operand)

        if isinstance(node, ast.BinOp):
            left = self._expr_deps(node.left)
            right = self._expr_deps(node.right)
            if isinstance(node.op, ast.Mult):
                # NOTE: Multiplication adds exponents.
                return self._combine_add(left, right)
            if isinstance(node.op, ast.Div):
                # NOTE: Division by state-dependent terms is treated as complex.
                if right:
                    self.complex = True
                return left
            if isinstance(node.op, (ast.Add, ast.Sub)):
                # NOTE: Sums use maximum observed order for each state.
                return self._combine_max(left, right)
            if isinstance(node.op, ast.Pow):
                power = self._constant_number(node.right)
                if power is None:
                    if left:
                        self.complex = True
                    return left
                return {key: value * power for key, value in left.items()}
            self.complex = True
            return self._combine_max(left, right)

        if isinstance(node, ast.Call):
            # NOTE: sqrt(x) is handled as x**0.5; other calls are complex.
            if self._is_sqrt(node):
                deps = self._expr_deps(node.args[0])
                return {key: value * 0.5 for key, value in deps.items()}
            deps: Dict[str, float] = {}
            for arg in node.args:
                deps = self._combine_max(deps, self._expr_deps(arg))
            if deps:
                self.complex = True
            return deps

        self.complex = True
        return {}

    @staticmethod
    def _constant_number(node: ast.AST) -> Optional[float]:
        # NOTE: Only literal numeric powers are considered inferable.
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if (
            isinstance(node, ast.UnaryOp)
            and isinstance(node.op, ast.USub)
            and isinstance(node.operand, ast.Constant)
            and isinstance(node.operand.value, (int, float))
        ):
            return -float(node.operand.value)
        return None

    @staticmethod
    def _is_sqrt(node: ast.Call) -> bool:
        # NOTE: Accept both sqrt(x) and math.sqrt(x).
        if len(node.args) != 1:
            return False
        if isinstance(node.func, ast.Name) and node.func.id == "sqrt":
            return True
        return (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "math"
            and node.func.attr == "sqrt"
        )

    @staticmethod
    def _combine_add(left: Dict[str, float], right: Dict[str, float]) -> Dict[str, float]:
        # NOTE: Used for product terms where powers add.
        out = dict(left)
        for key, value in right.items():
            out[key] = out.get(key, 0.0) + value
        return out

    @staticmethod
    def _combine_max(left: Dict[str, float], right: Dict[str, float]) -> Dict[str, float]:
        # NOTE: Used for sums/differences where a single order is approximate.
        out = dict(left)
        for key, value in right.items():
            out[key] = max(out.get(key, 0.0), value)
        return out


# SECTION: Public exports
__all__ = [
    "COMPONENT_ID_RE",
    "OrderInferer",
    "RateExpressionError",
    "RestrictedExpressionValidator",
    "SAFE_FUNCTIONS",
    "STATE_REF_RE",
    "StateValues",
    "validate_component_ids",
]
