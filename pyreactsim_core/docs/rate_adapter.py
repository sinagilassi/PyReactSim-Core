from __future__ import annotations

# SECTION: Imports
import ast
import logging
import math
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Literal, cast

import yaml
from pyreactlab_core.models.reaction import Reaction
from pythermodb_settings.models import Component, ComponentKey, CustomProperty
from pythermodb_settings.utils import set_component_id

from pyreactsim_core.docs.rate_adapter_validation import (
    OrderInferer,
    RateExpressionError,
    RestrictedExpressionValidator,
    SAFE_FUNCTIONS,
    STATE_REF_RE,
    StateValues,
)
from pyreactsim_core.models import ReactionRateExpression, X, rArgs, rParams, rRet, rXs

# NOTE: Module logger used for non-fatal inference warnings.
logger = logging.getLogger(__name__)


# NOTE: Keys that describe metadata rather than parameter/state names.
_META_KEYS = {
    "name",
    "description",
    "value",
    "unit",
    "units",
    "symbol",
    "expression",
    "order",
}


# SECTION: Rate Adapter
class RateAdapter:
    """
    Convert YAML reaction-rate definitions into ReactionRateExpression objects.

    The adapter accepts YAML text or files with a REFERENCES mapping and compiles each
    EXPRESSION into a restricted callable with signature ``eq(Xs, args, params)``.
    """

    def __init__(
        self,
        data: Dict[str, Any],
        components: List[Component],
        *,
        component_key: ComponentKey = "Name-Formula",
        state_key: ComponentKey = "Formula-State",
    ) -> None:
        # NOTE: Store raw YAML data and caller-provided component objects.
        self.data = data
        self.components = components
        self.component_key = component_key
        self.state_key = state_key

        # NOTE: YAML state ids are matched to Component instances by state_key.
        self._component_by_state_id = {
            set_component_id(component, state_key): component for component in components
        }

    # SECTION: Public constructors
    @classmethod
    def from_yaml_string(
        cls,
        yaml_text: str,
        components: List[Component],
        *,
        component_key: ComponentKey = "Name-Formula",
        state_key: ComponentKey = "Formula-State",
    ) -> "RateAdapter":
        # NOTE: Parse YAML once and keep the adapter immutable from caller input.
        data = yaml.safe_load(yaml_text)
        if not isinstance(data, dict):
            raise RateExpressionError(
                "YAML reaction-rate content must be a mapping.")
        return cls(
            data,
            components,
            component_key=component_key,
            state_key=state_key,
        )

    @classmethod
    def from_yaml_file(
        cls,
        path: str | Path,
        components: List[Component],
        *,
        component_key: ComponentKey = "Name-Formula",
        state_key: ComponentKey = "Formula-State",
    ) -> "RateAdapter":
        # NOTE: File loading delegates to the string constructor for one parse path.
        return cls.from_yaml_string(
            Path(path).read_text(encoding="utf-8"),
            components,
            component_key=component_key,
            state_key=state_key,
        )

    # SECTION: Public conversion API
    def to_rate_expressions(self) -> List[ReactionRateExpression]:
        # NOTE: Accept either a full REFERENCES document or a direct references map.
        references = self.data.get("REFERENCES", self.data)
        if not isinstance(references, dict):
            raise RateExpressionError("REFERENCES must be a mapping.")

        rate_expressions: List[ReactionRateExpression] = []
        for index, (_, raw_reference) in enumerate(references.items(), start=1):
            if not isinstance(raw_reference, dict):
                raise RateExpressionError(
                    "Each reaction-rate reference must be a mapping.")
            rate_expressions.append(
                self._build_rate_expression(raw_reference, index))
        return rate_expressions

    # SECTION: ReactionRateExpression assembly
    def _build_rate_expression(
        self,
        raw_reference: Dict[str, Any],
        index: int,
    ) -> ReactionRateExpression:
        # NOTE: Normalize top-level YAML keys while preserving nested user keys.
        reference = {str(key).upper(): value for key,
                     value in raw_reference.items()}
        expression_lines = self._normalize_expression_lines(
            reference.get("EXPRESSION"))
        if not expression_lines:
            raise RateExpressionError(
                "EXPRESSION must contain at least one assignment.")

        assignment_nodes = self._parse_assignment_nodes(expression_lines)
        state_refs = self._state_references(expression_lines)
        basis = self._basis(reference.get("BASIS"), state_refs)

        # NOTE: Convert YAML metadata sections into PyReactSim model dictionaries.
        params = self._custom_property_mapping(
            reference.get("PARAMETERS"), default_unit="")
        args = self._custom_property_mapping(
            reference.get("ARGS"), default_unit="")

        return_var = self._return_variable(reference.get("RETURN"))
        inferred_orders = self._infer_orders(assignment_nodes, return_var)
        state = self._create_state(reference.get(
            "STATE"), state_refs, basis, inferred_orders, reference.get("UNIT"))
        ret = self._create_return(reference.get("RETURN"), index)
        eq = self._compile_eq(assignment_nodes, ret, return_var, basis)

        name = str(reference.get("NAME") or f"reaction {index}")
        reaction_text = reference.get("REACTION")
        if not reaction_text:
            raise RateExpressionError(f"{name} is missing REACTION.")

        # NOTE: Reaction keeps the original reaction string and supplied components.
        reaction = Reaction(
            name=name,
            reaction=str(reaction_text),
            components=self.components,
        )

        return ReactionRateExpression(
            name=name,
            basis=basis,
            components=self.components,
            component_key=cast(ComponentKey, self.component_key),
            reaction=reaction,
            params=params,
            args=args,
            ret=ret,
            state=state,
            state_key=cast(ComponentKey, self.state_key),
            eq=eq,
        )

    # SECTION: Expression parsing helpers
    @staticmethod
    def _normalize_expression_lines(value: Any) -> List[str]:
        # NOTE: Expressions may be a YAML block string or list of assignment lines.
        if value is None:
            return []
        if isinstance(value, str):
            return [line.strip() for line in value.splitlines() if line.strip()]
        if isinstance(value, list):
            lines = []
            for item in value:
                if not isinstance(item, str):
                    raise RateExpressionError(
                        "EXPRESSION items must be strings.")
                if item.strip():
                    lines.append(item.strip())
            return lines
        raise RateExpressionError(
            "EXPRESSION must be a string or list of strings.")

    @staticmethod
    def _parse_assignment_nodes(lines: List[str]) -> List[ast.Assign]:
        nodes: List[ast.Assign] = []
        validator = RestrictedExpressionValidator()
        for line in lines:
            # NOTE: Validate each assignment before compiling or evaluating it.
            module = ast.parse(line, mode="exec")
            if len(module.body) != 1 or not isinstance(module.body[0], ast.Assign):
                raise RateExpressionError(
                    "Each EXPRESSION line must be an assignment.")
            node = module.body[0]
            validator.visit(node)
            nodes.append(node)
        return nodes

    @staticmethod
    def _state_references(lines: List[str]) -> Dict[str, set[str]]:
        # NOTE: Track C[...] and P[...] independently so basis can be inferred.
        refs = {"C": set(), "P": set()}
        for line in lines:
            for basis_symbol, _, state_id in STATE_REF_RE.findall(line):
                refs[basis_symbol].add(state_id)
        return refs

    # SECTION: Basis and metadata normalization
    @staticmethod
    def _basis(
        raw_basis: Any,
        state_refs: Dict[str, set[str]],
    ) -> Literal["concentration", "pressure"]:
        # NOTE: Explicit BASIS wins, but it must agree with C/P expression usage.
        if raw_basis:
            basis = str(raw_basis).lower()
            if basis not in {"concentration", "pressure"}:
                raise RateExpressionError(
                    "BASIS must be 'concentration' or 'pressure'.")
            if basis == "concentration" and state_refs["P"]:
                raise RateExpressionError(
                    "BASIS is concentration but P[...] references were used.")
            if basis == "pressure" and state_refs["C"]:
                raise RateExpressionError(
                    "BASIS is pressure but C[...] references were used.")
            return basis  # type: ignore[return-value]

        has_c = bool(state_refs["C"])
        has_p = bool(state_refs["P"])
        if has_c and has_p:
            raise RateExpressionError(
                "Cannot infer BASIS when both C[...] and P[...] are used.")
        if has_c:
            return "concentration"
        if has_p:
            return "pressure"
        raise RateExpressionError(
            "Cannot infer BASIS without C[...] or P[...] references.")

    @staticmethod
    def _custom_property_mapping(value: Any, *, default_unit: str) -> Dict[str, CustomProperty]:
        # NOTE: Convert PARAMETERS and ARGS sections into CustomProperty mappings.
        out: Dict[str, CustomProperty] = {}
        for key, meta in RateAdapter._iter_named_metadata(value):
            out[key] = RateAdapter._custom_property_from_meta(
                key,
                meta,
                default_unit=default_unit,
            )
        return out

    @staticmethod
    def _iter_named_metadata(value: Any) -> Iterable[tuple[str, Dict[str, Any]]]:
        # NOTE: Supports preferred mapping style and legacy one-key list style.
        if value is None:
            return []
        if isinstance(value, dict):
            return [
                (str(key), meta if isinstance(meta, dict) else {"value": meta})
                for key, meta in value.items()
            ]
        if isinstance(value, list):
            items: List[tuple[str, Dict[str, Any]]] = []
            for entry in value:
                if not isinstance(entry, dict):
                    raise RateExpressionError(
                        "List metadata entries must be mappings.")
                candidates = [
                    key
                    for key in entry
                    if str(key).lower() not in _META_KEYS and entry[key] is None
                ]
                if not candidates:
                    candidates = [
                        key
                        for key in entry
                        if str(key).lower() not in _META_KEYS
                    ]
                if not candidates:
                    raise RateExpressionError(
                        "Could not find a name in list metadata entry.")
                name = str(candidates[0])
                meta = {key: value for key, value in entry.items()
                        if key != candidates[0]}
                items.append((name, meta))
            return items
        raise RateExpressionError(
            "Metadata must be a mapping or list of mappings.")

    @staticmethod
    def _custom_property_from_meta(
        key: str,
        meta: Dict[str, Any],
        *,
        default_unit: str,
    ) -> CustomProperty:
        # NOTE: YAML uses "unit" canonically, but legacy "units" is accepted.
        unit = meta.get("unit", meta.get("units", default_unit))
        return CustomProperty(
            name=meta.get("name"),
            description=meta.get("description"),
            value=meta.get("value", 0.0),
            unit=str(unit),
            symbol=str(meta.get("symbol", key)),
        )

    # SECTION: Return and state model creation
    @staticmethod
    def _return_variable(value: Any) -> str:
        # NOTE: RETURN.expression selects the final variable; "r" is default.
        if isinstance(value, dict) and value.get("expression"):
            return str(value["expression"])
        return "r"

    @staticmethod
    def _create_return(value: Any, index: int) -> rRet:
        # NOTE: Return metadata becomes the CustomProperty template for eq output.
        meta = value if isinstance(value, dict) else {}
        key = str(meta.get("symbol") or meta.get("name") or f"r{index}")
        return RateAdapter._custom_property_from_meta(
            key,
            meta,
            default_unit="mol/m3.s",
        )

    def _infer_orders(
        self,
        assignment_nodes: List[ast.Assign],
        return_var: str,
    ) -> Dict[str, float]:
        # NOTE: Inference is best-effort; explicit STATE.order overrides later.
        inferer = OrderInferer()
        orders = inferer.infer(assignment_nodes, return_var)
        if inferer.complex:
            logger.warning(
                "Some reaction orders could not be inferred confidently; "
                "referenced states without explicit orders default to 0."
            )
        return orders

    def _create_state(
        self,
        value: Any,
        state_refs: Dict[str, set[str]],
        basis: Literal["concentration", "pressure"],
        inferred_orders: Dict[str, float],
        raw_unit: Any,
    ) -> rXs:
        # NOTE: Build state entries from explicit YAML plus expression references.
        explicit_state = value if isinstance(value, dict) else {}
        state_ids = set(state_refs["C"]) | set(
            state_refs["P"]) | set(map(str, explicit_state))
        basis_unit_default = "mol/m3" if basis == "concentration" else "bar"
        if raw_unit is None:
            unit_default = basis_unit_default
        elif isinstance(raw_unit, str):
            unit_default = raw_unit
        else:
            raise RateExpressionError("UNIT must be a string when provided.")

        states: rXs = {}
        for state_id in sorted(state_ids):
            # NOTE: Adapter cannot invent components; caller must provide them.
            component = self._component_by_state_id.get(state_id)
            if component is None:
                raise RateExpressionError(
                    f"State '{state_id}' does not match any supplied component "
                    f"using state_key '{self.state_key}'."
                )
            meta = explicit_state.get(state_id, {})
            if meta is None:
                meta = {}
            if not isinstance(meta, dict):
                raise RateExpressionError(
                    f"STATE metadata for '{state_id}' must be a mapping.")

            order = meta.get("order", inferred_orders.get(state_id, 0))
            unit = meta.get("unit", meta.get("units", unit_default))
            states[state_id] = X(
                component=component,
                order=order,
                value=meta.get("value", 0.0),
                unit=str(unit),
            )
        return states

    # SECTION: Runtime evaluator
    def _compile_eq(
        self,
        assignment_nodes: List[ast.Assign],
        ret_template: rRet,
        return_var: str,
        basis: Literal["concentration", "pressure"],
    ) -> Callable[[rXs, rArgs, rParams], rRet]:
        # NOTE: Only validated expression values are compiled for runtime eval.
        code_objects = [
            compile(ast.Expression(node.value),
                    "<reaction-rate-expression>", "eval")
            for node in assignment_nodes
        ]
        targets = [cast(ast.Name, node.targets[0]).id for node in assignment_nodes]
        state_symbol = "C" if basis == "concentration" else "P"

        def eq(Xs: rXs, args: rArgs, params: rParams) -> rRet:
            # NOTE: Namespace exposes state values, args, params, and safe math only.
            namespace: Dict[str, Any] = {
                "math": math,
                state_symbol: StateValues(Xs, state_symbol),
                **SAFE_FUNCTIONS,
            }
            namespace.update({key: prop.value for key, prop in params.items()})
            namespace.update({key: prop.value for key, prop in args.items()})

            # NOTE: Expose symbols as aliases without overriding canonical keys.
            for key, prop in params.items():
                namespace.setdefault(prop.symbol, prop.value)
            for key, prop in args.items():
                namespace.setdefault(prop.symbol, prop.value)

            for target, code in zip(targets, code_objects):
                namespace[target] = eval(code, {"__builtins__": {}}, namespace)

            # NOTE: The selected return variable must be assigned by EXPRESSION.
            if return_var not in namespace:
                raise RateExpressionError(
                    f"Return expression '{return_var}' was not produced by EXPRESSION."
                )

            return CustomProperty(
                name=ret_template.name,
                description=ret_template.description,
                value=namespace[return_var],
                unit=ret_template.unit,
                symbol=ret_template.symbol,
            )

        return eq


# SECTION: Public exports
__all__ = ["RateAdapter", "RateExpressionError"]
