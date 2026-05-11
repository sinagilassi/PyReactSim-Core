from pathlib import Path
import sys

from rich import print

from pyreactsim_core import load_reaction_rate_expression
from pyreactsim_core.models import ReactionRateSource

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from examples.source.gas_load_model_source import CO2, H2, CH3OH, H2O, CO  # noqa: E402


# SECTION: Load from YAML string via app helper
components = [CO2, H2, CO, CH3OH, H2O]

yaml_path = Path(__file__).with_name("methanol_1.yaml")
yaml_text = yaml_path.read_text(encoding="utf-8")

rate_loaded: list[ReactionRateSource] | None = load_reaction_rate_expression(
    components=components,
    reaction_rate_expression=yaml_text,
    mode="log",
)

print("rate loaded:")
print(rate_loaded)

if not rate_loaded:
    raise ValueError(
        "Failed to load reaction rate expressions from YAML content.")

assert len(rate_loaded) == 3, f"Expected 3 reactions, got {len(rate_loaded)}."

print("\nLoaded reaction summary:")
for idx, rate_source in enumerate(rate_loaded, start=1):
    exp = rate_source.reaction_rate_expression
    participant_ids = [
        f"{c.formula}-{c.state}" for c in exp.reaction.available_components]
    print(
        f"[{idx}] name={rate_source.name}, basis={rate_source.basis}, "
        f"participants={participant_ids}"
    )
