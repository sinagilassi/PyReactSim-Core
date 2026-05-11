# import libs
import logging
from typing import List, Optional
from pythermodb_settings.models import Component, ComponentKey
from pythermodb_settings.utils import measure_time
# locals
from .docs.rate_adapter import RateAdapter
from .models import ReactionRateExpressionSource, ReactionRateSource, ReactionRateExpression

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
) -> Optional[List[ReactionRateSource]]:
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
    Optional[List[ReactionRateSource]]
        A list of loaded reaction rate source models, or None if there was an error loading the model.
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
        rate_expressions: List[ReactionRateExpression] = adapter.to_rate_expressions(
        )

        # >> check
        if not rate_expressions:
            raise ValueError(
                "No reaction rate expressions found in YAML content."
            )

        # NOTE: wrap all parsed reactions as ReactionRateSource entries
        return [
            ReactionRateSource(
                name=rate_expression.name,
                components=rate_expression.reaction.components,
                basis=rate_expression.basis,
                description=rate_expression.description,
                source=reaction_rate_expression,
                reaction_rate_expression=rate_expression
            )
            for rate_expression in rate_expressions
        ]
    except Exception as e:
        logger.error(f"Error loading reaction rate expression: {e}")
        return None


# NOTE: load multiple reaction rate expressions from a list of YAML strings
def load_reaction_rate_expressions(
        reaction_rate_sources: List[ReactionRateExpressionSource],
        component_key: ComponentKey = "Name-Formula",
        state_key: ComponentKey = "Formula-State",
        **kwargs
) -> List[ReactionRateSource]:
    """
    Load multiple reaction rate expressions from a list of ReactionRateExpressionSource models.

    Parameters
    ----------
    reaction_rate_sources : List[ReactionRateExpressionSource]
        A list of ReactionRateExpressionSource models containing the components and YAML strings for each reaction rate expression to load.
    component_key : ComponentKey, optional
        The key to use for identifying components in the reaction rate expressions. This should match the keys used in the state (Xi) and parameters (rParams) dictionaries. Default is "Name-Formula".
    state_key : ComponentKey, optional
        The key to use for identifying components in the state (Xi) dictionary. This should match the keys used in the reaction and parameters (rParams) dictionaries. Default is "Formula-State".
    **kwargs
        Additional keyword arguments to pass to the ReactionRateExpression model.
        - mode : Literal['silent', 'log', 'attach'], optional
            Mode for time measurement logging. Default is 'silent'.

    Returns
    -------
    List[ReactionRateSource]
        A flat list of loaded ReactionRateSource models, or an empty list if there were errors loading any of the models.
    """
    try:
        # init list to hold loaded reaction rate expressions
        rate_sources: List[ReactionRateSource] = []

        # iterate over sources and load each reaction rate expression
        for source in reaction_rate_sources:
            loaded = load_reaction_rate_expression(
                components=source.components,
                reaction_rate_expression=source.source,
                component_key=component_key,
                state_key=state_key,
                **kwargs
            )

            # >> check and extend
            if loaded is not None:
                rate_sources.extend(loaded)

        # res
        return rate_sources
    except Exception as e:
        logger.error(f"Error loading reaction rate expressions: {e}")
        return []
