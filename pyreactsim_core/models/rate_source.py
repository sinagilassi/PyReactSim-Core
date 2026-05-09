# import libs
from pydantic import BaseModel, Field, PrivateAttr, model_validator
from typing import Dict, List, Literal, Optional, Callable
from pythermodb_settings.models import Component, CustomProperty, Pressure, Temperature, ComponentKey


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
