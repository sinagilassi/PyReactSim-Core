# 🧪 PyReactSim-Core

[![PyPI Downloads](https://static.pepy.tech/badge/pyreactsim-core/month)](https://pepy.tech/projects/pyreactsim-core)
![PyPI](https://img.shields.io/pypi/v/pyreactsim-core)
![Python Version](https://img.shields.io/pypi/pyversions/pyreactsim-core.svg)
![License](https://img.shields.io/pypi/l/pyreactsim-core)
![Read the Docs](https://img.shields.io/readthedocs/pyreactsim-core)

**PyReactSim-Core** is a Python package for representing reaction rates. It provides a flexible and extensible framework for defining and working with reaction rates in chemical engineering applications.

It is the core reaction-rate layer of the PyReactSim ecosystem and is designed for practical kinetic modeling workflows, from simple power-law expressions to custom rate equations with user-defined parameters and arguments.

## ✨ Features

- **⚗️ Reaction Rate Representation**: Define and manipulate chemical reaction rates with ease.
- **🧩 Flexible Rate Expressions**: Build kinetic models with custom callables and typed state/argument/parameter containers.
- **🧪 Concentration or Pressure Basis**: Define rate equations on either concentration-based or pressure-based states.
- **📐 Unit-Aware Inputs**: Evaluate rates with `CustomProperty`-based values and automatic unit conversion support.
- **🔁 Reusable State Templates**: Predefine reaction orders and default state values using `X` and `rXs`.
- **🧱 Pydantic Validation**: Validate structure and component/state consistency before runtime.
- **📚 Ready-to-Run Examples**: Includes gas and liquid reaction examples, source-model setup scripts, and thermodynamic database assets.

## 🧠 Core Concepts

- **`ReactionRateExpression`**: Main model for a rate expression definition (`basis`, `components`, `reaction`, `params`, `args`, `state`, `eq`).
- **`X` / `rXs`**: State representation for each component (order, value, unit).
- **`rArgs` / `rParams` / `rRet`**: Typed dictionaries (and return model) used by rate-equation callables.
- **`calc(...)`**: Main execution path that evaluates the expression from current state and optional runtime arguments (e.g., temperature and pressure).

## 📦 Installation

You can install PyReactSim-Core using pip:

```bash
pip install pyreactsim-core
```

## 🚀 Quick Start

```python
from pythermodb_settings.models import CustomProperty
from pyreactsim_core.models import ReactionRateExpression, X, rArgs, rParams, rRet, rXs

# 1) Define your components/reaction and state map
states: rXs = {
	"A-g": X(component=A, order=1, unit="Pa"),
	"B-g": X(component=B, order=2, unit="Pa"),
}

# 2) Define parameters/arguments and return placeholder
params: rParams = {
	"k": CustomProperty(value=1.0e-11, unit="mol/m3.s.Pa2", symbol="k")
}
args: rArgs = {
	"T": CustomProperty(value=500.0, unit="K", symbol="T")
}
ret: rRet = CustomProperty(value=0.0, unit="mol/m3.s", symbol="r")

# 3) Provide your rate equation
def rate_eq(Xs, args, params):
	r = params["k"].value * (Xs["A-g"].value ** Xs["A-g"].order) * (Xs["B-g"].value ** Xs["B-g"].order)
	return CustomProperty(value=r, unit="mol/m3.s", symbol="r")

# 4) Build and evaluate
rate_model = ReactionRateExpression(
	name="example-rate",
	basis="pressure",
	components=[A, B],
	reaction=reaction,
	params=params,
	args=args,
	ret=ret,
	state=states,
	state_key="Formula-State",
	eq=rate_eq,
	component_key="Name-Formula",
)

result = rate_model.calc(
	xi={
		"A-g": CustomProperty(value=2.0e5, unit="Pa", symbol="P_A"),
		"B-g": CustomProperty(value=1.0e5, unit="Pa", symbol="P_B"),
	}
)

print(result)
```

## 🗂️ Package Content

Main package:

- **`pyreactsim_core/models/rate_exp.py`**: `ReactionRateExpression` model and validation.
- **`pyreactsim_core/models/rate.py`**: Runtime calculation engine and argument/state handling.
- **`pyreactsim_core/models/rate_exp_refs.py`**: Shared typed aliases and `X` state model.
- **`pyreactsim_core/configs/info.py`**: Package metadata.

Examples folder:

- **`examples/rates/`**: Rate-expression examples (gas and liquid kinetics).
- **`examples/source/`**: Model-source creation/loading scripts.
- **`examples/thermodb/`**: Thermodynamic database assets used by source scripts.

## 🧪 Examples Guide

Use the following scripts as starting points:

- **`examples/rates/rate_exp_1.py`**: Minimal pressure-based rate expression setup.
- **`examples/rates/methanol_1.py`**: Multi-reaction methanol synthesis kinetics (gas phase).
- **`examples/rates/esterification_acetic_acid_1.py`**: Liquid-phase reversible esterification example.
- **`examples/source/gas_load_model_source.py`**: Build/load gas-phase component model source from thermodb files.
- **`examples/source/liquid_load_model_source.py`**: Build/load liquid-phase component model source from thermodb files.

Run an example directly:

```bash
python examples/rates/rate_exp_1.py
```

> Note: Some examples rely on companion ecosystem packages and local thermodb assets.

## 🤝 Contributing

Contributions are highly welcome — bug fixes, new calculation routines, mixture models, extended unit tests, documentation, etc.

## 📝 License

This project is distributed under the Apache License, Version 2.0, which grants you broad freedom to use, modify, and integrate the software into your own applications or projects, provided that you comply with the conditions outlined in the license. Although Apache 2.0 does not require users to retain explicit author credit beyond standard copyright and license notices, I kindly request that if you incorporate this work into your own software, you acknowledge Sina Gilassi as the original author. Referencing the original repository or documentation is appreciated, as it helps recognize the effort invested in developing and maintaining this project.

## ❓ FAQ

For any question, contact me on [LinkedIn](https://www.linkedin.com/in/sina-gilassi/)

## 👨‍💻 Authors

- [@sinagilassi](https://www.github.com/sinagilassi)