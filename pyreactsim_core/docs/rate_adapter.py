# import libs
import logging
import yaml
from typing import Dict, List, Optional, Tuple, Union, Any
from pythermodb_settings.models import Component, CustomProperty
from pyreactlab_core.models.reaction import Reaction
# locals
from pyreactsim_core.models import (
    rArgs,
    rParams,
    rRet,
    X,
    rXs,
    ReactionRateExpression
)

# NOTE: logger setup
logger = logging.getLogger(__name__)


class RateAdapter:
    """
    Adapter for reaction rate expressions. This class provides a standardized interface for defining and evaluating reaction rates based on user-defined expressions and parameters within the PyReactSim framework.

    Notes
    -----
    - The `reaction_rate_expression` should be a string that can be evaluated within the context of the PyReactSim framework, allowing for references to states, parameters, and arguments.
    - reaction rate expression should be concentration or pressure based, depending on the basis of the reaction defined as:
        For concentration-based rates, C[component-formula-state]
        For pressure-based rates, P[component-formula-state]
    """

    def __init__(
            self,
            reaction: Reaction,
            reaction_rate_expression: str,
            config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the ReactionRateAdapter with the given reaction and rate expression.

        Parameters
        ----------
        reaction : Reaction
            The reaction for which the rate expression is defined.
        reaction_rate_expression : str
            The user-defined reaction rate expression as a string. This expression should be compatible with the PyReactSim framework and can include references to states, parameters, and arguments.
        """
        # NOTE: store the reaction and rate expression
        self.reaction = reaction
        self.reaction_rate_expression = reaction_rate_expression

        # NOTE: components
        self.components: List[Component] = reaction.available_components

        # SECTION: config
        # NOTE: load any additional configuration from the provided config dictionary
        self.config = config or {}

        # ! default args
        self.rate_args_default: rArgs = self.config.get(
            "rate_args_default",
            {}
        )

    # SECTION: load reaction rate expression
    def _load_reaction_rate_expression(self) -> Dict[str, Any]:
        """
        Load the reaction rate expression from the provided string (yaml format).

        Returns
        -------
        Dict[str, Any]
            A dictionary containing the parsed reaction rate expression and any relevant metadata.
        """
        # NOTE: load the reaction rate expression from the provided string (yaml format)
        return {}

    # SECTION: create states
    def _create_states(self) -> rXs:
        """
        Create the states (concentrations or pressures) for the reaction based on the components and their states.

        Returns
        -------
        rXs
            A dictionary mapping state names to their corresponding X objects, which represent concentrations or pressures in the PyReactSim framework.
        """
        states: rXs = {}

        return states

    # SECTION: create rate args
    def _create_rate_args(self) -> rArgs:
        """
        Create the rate arguments (e.g., temperature, density) for the reaction.

        Returns
        -------
        rArgs
            A dictionary mapping argument names to their corresponding CustomProperty objects, which represent the arguments needed for evaluating the reaction rate expression.
        """
        rate_args: rArgs = {}

        return rate_args

    # SECTION: create rate params
    def _create_rate_params(self) -> rParams:
        """
        Create the rate parameters (e.g., rate constants, equilibrium constants) for the reaction.

        Returns
        -------
        rParams
            A dictionary mapping parameter names to their corresponding CustomProperty objects, which represent the parameters needed for evaluating the reaction rate expression.
        """
        rate_params: rParams = {}

        return rate_params

    # SECTION: create rate return
    def _create_rate_return(self) -> rRet:
        """
        Create the rate return object for the reaction.

        Returns
        -------
        rRet
            A CustomProperty object that represents the return value of the reaction rate expression, including its name, description, unit, and symbol.
        """
        rate_return: rRet = CustomProperty(
            value=0.0,
            unit="",
            symbol=""
        )

        return rate_return
