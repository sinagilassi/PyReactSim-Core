# import packages/modules
from pyreactsim_core.docs.rate_adapter import RateAdapter
from pathlib import Path
import sys
from rich import print

from pythermodb_settings.models import Component, CustomProperty

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# SECTION: YAML Rate Adapter Example
CH3COOH = Component(name="acetic acid", formula="CH3COOH", state="l")
CH3OH = Component(name="methanol", formula="CH3OH", state="l")
C3H6O2 = Component(name="methyl acetate", formula="C3H6O2", state="l")
H2O = Component(name="water", formula="H2O", state="l")

components = [CH3COOH, CH3OH, C3H6O2, H2O]
yaml_path = Path(__file__).with_name("esterification_acetic_acid_1.yaml")

rate_adapter = RateAdapter.from_yaml_file(
    yaml_path,
    components,
    component_key="Name-Formula",
    state_key="Formula-State",
)

reaction_rates = rate_adapter.to_rate_expressions()
# log
print("rate expression:")
rate_expression = reaction_rates[0]


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

# NOTE: Expected value mirrors esterification_acetic_acid_1.py.
expected_rate = 900.0 * (
    1.0e-6 * 1000.0 * 800.0
    - 2.0e-7 * 100.0 * 50.0
)

assert abs(rate_result.value - expected_rate) < 1e-12

print(reaction_rates)
print(rate_result)
