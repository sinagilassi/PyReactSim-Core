# import libs
import logging
from typing import List, Dict, Optional
from pythermodb_settings.models import Component, CustomProperty, Pressure, Temperature, Volume, CustomProp, ComponentKey
from pythermodb_settings.utils import measure_time
# locals
from .docs.rate_adapter import RateAdapter
from .models import ReactionRateExpressionSource, ReactionRateSource

# NOTE: logger setup
logger = logging.getLogger(__name__)

# SECTION: Load reaction rate expressions
# NOTE: import your reaction rate expressions here


@measure_time
def load_reaction_rate_expression(
        components: List[Component],
        reaction_rate_expression: str,
        component_key: ComponentKey = "Name-Formula",
        state_key: ComponentKey = "Formula-State",
        **kwargs
) -> Optional[ReactionRateSource]:
    """
    Load a reaction rate expression from a ReactionRateExpression model.

    Parameters
    ----------
    components : List[Component]
        The list of components involved in the reaction for which the rate expression is defined.
    reaction_rate_expression : str
        Reaction rate expression in yaml format as a string containing the necessary information to construct a ReactionRateExpression model.
    component_key : ComponentKey, optional
        The key to use for identifying components in the reaction rate expression. This should match the keys used in the state (Xi) and parameters (rParams) dictionaries. Default is "Name-Formula".
    state_key : ComponentKey, optional
        The key to use for identifying components in the state (Xi) dictionary. This should match the keys used in the reaction and parameters (rParams) dictionaries. Default is "Formula-State".
    **kwargs
        Additional keyword arguments to pass to the ReactionRateExpression model.
        - mode : Literal['silent', 'log', 'attach'], optional
            Mode for time measurement logging. Default is 'silent'.

    Returns
    -------
    ReactionRateSource | None
        The loaded reaction rate source model, or None if there was an error loading the model.
    """
    try:
        # NOTE: load reaction rate expression using the RateAdapter
        adapter = RateAdapter.from_yaml_string(
            reaction_rate_expression,
            components,
            component_key=component_key,
            state_key=state_key,
        )

        # NOTE: convert to ReactionRateExpression model
        rate_expressions = adapter.to_rate_expressions()

        # >> check
        if not rate_expressions:
            raise ValueError(
                "No reaction rate expressions found in YAML content."
            )

        # NOTE: wrap as ReactionRateSource (includes parsed expression + original YAML source)
        rate_expression = rate_expressions[0]
        return ReactionRateSource(
            name=rate_expression.name,
            basis=rate_expression.basis,
            description=rate_expression.description,
            source=reaction_rate_expression,
            reaction_rate_expression=rate_expression
        )
    except Exception as e:
        logger.error(f"Error loading reaction rate expression: {e}")
        return None
