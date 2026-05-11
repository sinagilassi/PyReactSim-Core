from rich import print
from pathlib import Path
import sys
from pythermodb_settings.models import Component, CustomProperty
# pyreactsim-core
from pyreactsim_core import load_reaction_rate_expression
from pyreactsim_core.models import ReactionRateExpression, ReactionRateSource

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# SECTION: Load from YAML string via app helper
CH3COOH = Component(name="acetic acid", formula="CH3COOH", state="l")
CH3OH = Component(name="methanol", formula="CH3OH", state="l")
C3H6O2 = Component(name="methyl acetate", formula="C3H6O2", state="l")
H2O = Component(name="water", formula="H2O", state="l")

# >> components
components = [CH3COOH, CH3OH, C3H6O2, H2O]

# NOTE: load YAML content from file for testing
yaml_path = Path(__file__).with_name("esterification_acetic_acid_1.yaml")
yaml_text = yaml_path.read_text(encoding="utf-8")

rate_loaded: ReactionRateSource | None = load_reaction_rate_expression(
    components=components,
    reaction_rate_expression=yaml_text,
    mode="log",  # log time measurement for loading the rate expression
)

print("rate loaded:")
print(rate_loaded)

# >> check
if rate_loaded is None:
    raise ValueError(
        "Failed to load reaction rate expression from YAML content.")

# set rate expression for testing
rate_expression: ReactionRateExpression = rate_loaded.reaction_rate_expression

# SECTION: Calculation Smoke Test
xi = {
    "CH3COOH-l": CustomProperty(value=1000.0, unit="mol/m3", symbol="C_acid"),
    "CH3OH-l": CustomProperty(value=800.0, unit="mol/m3", symbol="C_meoh"),
    "C3H6O2-l": CustomProperty(value=100.0, unit="mol/m3", symbol="C_meac"),
    "H2O-l": CustomProperty(value=50.0, unit="mol/m3", symbol="C_h2o"),
}

args = {
    "rho_B": CustomProperty(value=900.0, unit="kg/m3", symbol="rho_B"),
}

rate_result = rate_expression.calc(xi, args=args)

expected_rate = 900.0 * (
    1.0e-6 * 1000.0 * 800.0
    - 2.0e-7 * 100.0 * 50.0
)
assert abs(rate_result.value - expected_rate) < 1e-12

print(rate_result)
