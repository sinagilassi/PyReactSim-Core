# import libs
import logging
from typing import Dict, List, Literal, Optional, Callable
from pythermodb_settings.models import Component, CustomProperty, Pressure, Temperature, Volume, CustomProp, ComponentKey
from pythermodb_settings.utils import measure_time
# locals
from .models.rate_exp import ReactionRateExpression
from .models.rate import ReactionRate
from .docs.rate_adapter import RateAdapter

# NOTE: logger setup
logger = logging.getLogger(__name__)

# SECTION: Load reaction rate expressions
# NOTE: import your reaction rate expressions here


def load_reaction_rate_expression(
        components: List[Component],
        reaction_rate_expression: str,
        **kwargs
) -> Optional[ReactionRateExpression]:
    """
    Load a reaction rate expression from a ReactionRateExpression model.

    Parameters
    ----------
    components : List[Component]
        The list of components involved in the reaction for which the rate expression is defined.
    reaction_rate_expression : str
        Reaction rate expression in yaml format as a string containing the necessary information to construct a ReactionRateExpression model.
    **kwargs
        Additional keyword arguments to pass to the ReactionRateExpression model.

    Returns
    -------
    ReactionRateExpression | None
        The loaded reaction rate expression model, or None if there was an error loading the model.
    """
    try:
        # NOTE: default keys
        component_key_value: ComponentKey = "Name-Formula"
        state_key: ComponentKey = "Formula-State"

        # NOTE: load reaction rate expression using the RateAdapter
        adapter = RateAdapter.from_yaml_string(
            reaction_rate_expression,
            components,
            component_key=component_key_value,
            state_key=state_key,
        )

        # NOTE: convert to ReactionRateExpression model
        rate_expressions = adapter.to_rate_expressions()

        # >> check
        if not rate_expressions:
            raise ValueError(
                "No reaction rate expressions found in YAML content."
            )

        # res
        return rate_expressions[0]
    except Exception as e:
        logger.error(f"Error loading reaction rate expression: {e}")
        return None
