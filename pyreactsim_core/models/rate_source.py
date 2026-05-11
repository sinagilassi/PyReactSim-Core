# import libs
from pydantic import BaseModel, Field, PrivateAttr, model_validator
from typing import Dict, List, Literal, Optional, Callable
from pythermodb_settings.models import Component, CustomProperty, Pressure, Temperature, ComponentKey
# locals
from .rate_exp import ReactionRateExpression


# SECTION: reaction rate expression source
class ReactionRateExpressionSource(BaseModel):
    """
    A model representing the source of a reaction rate expression, such as a YAML string defining the reaction rate expression with the necessary information to construct a ReactionRateExpression model.

    Attributes
    ----------
    components : List[Component]
        The list of components involved in the reaction for which the rate expression is defined.
    source : str
        The source of the reaction rate expression, such as a YAML string defining the reaction rate expression with the necessary information to construct a ReactionRateExpression model.
    """
    components: List[Component] = Field(
        ...,
        description="The list of components involved in the reaction for which the rate expression is defined."
    )
    source: str = Field(
        ...,
        description="The source of the reaction rate expression, such as a YAML string defining the reaction rate expression with the necessary information to construct a ReactionRateExpression model."
    )


class ReactionRateSource(BaseModel):
    """
    A model representing the source of a reaction rate expression, such as a YAML string defining the reaction rate expression with the necessary information to construct a ReactionRateExpression model.

    Attributes
    ----------
    components : List[Component]
        The list of components involved in the reaction for which the rate expression is defined.
    source : str
        The source of the reaction rate expression, such as a YAML string defining the reaction rate expression with the necessary information to construct a ReactionRateExpression model.
    """
    name: str = Field(
        ...,
        description="The name of the reaction rate expression source, which can be used for identification and reference purposes."
    )
    basis: Literal["concentration", "pressure"] = Field(
        ...,
        description="The basis of the reaction rate expression, indicating whether the reaction rate is defined based on concentration or pressure of the components involved in the reaction."
    )
    description: Optional[str] = Field(
        default=None,
        description="An optional description providing additional information about the reaction rate expression source."
    )
    source: str = Field(
        ...,
        description="The source of the reaction rate expression, such as a YAML string defining the reaction rate expression with the necessary information to construct a ReactionRateExpression model."
    )
    reaction_rate_expression: ReactionRateExpression = Field(
        ...,
        description="The reaction rate expression model constructed from the source, which can be used for calculations and simulations involving the reaction."
    )
