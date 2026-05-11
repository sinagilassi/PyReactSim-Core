import textwrap
import unittest

from pythermodb_settings.models import Component, CustomProperty

from pyreactsim_core import RateAdapter, RateExpressionError


class RateAdapterTest(unittest.TestCase):
    def setUp(self):
        self.acid = Component(name="acetic acid", formula="CH3COOH", state="l")
        self.meoh_l = Component(name="methanol", formula="CH3OH", state="l")
        self.meac = Component(name="methyl acetate", formula="C3H6O2", state="l")
        self.water_l = Component(name="water", formula="H2O", state="l")
        self.components_l = [self.acid, self.meoh_l, self.meac, self.water_l]

        self.co = Component(name="carbon monoxide", formula="CO", state="g")
        self.h2 = Component(name="hydrogen", formula="H2", state="g")
        self.meoh_g = Component(name="methanol", formula="CH3OH", state="g")
        self.components_g = [self.co, self.h2, self.meoh_g]

    def test_current_list_style_yaml_is_supported(self):
        yaml_text = """
        REFERENCES:
          REACTION-1:
            NAME: reaction 1
            BASIS: concentration
            REACTION: CH3COOH(l) + CH3OH(l) <=> C3H6O2(l) + H2O(l)
            PARAMETERS:
              - kf:
                value: 1.0e-6
                units: m3/mol.s
                symbol: kf
              - kr:
                value: 2.0e-7
                units: m3/mol.s
                symbol: kr
            EXPRESSION:
              - c_acid = C["CH3COOH-l"]
              - c_meoh = C["CH3OH-l"]
              - c_meac = C["C3H6O2-l"]
              - c_h2o = C["H2O-l"]
              - rf = c_acid * c_meoh
              - rr = c_meac * c_h2o
              - r = kf * rf - kr * rr
        """

        rate = RateAdapter.from_yaml_string(
            textwrap.dedent(yaml_text),
            self.components_l,
        ).to_rate_expressions()[0]

        self.assertEqual(rate.params["kf"].unit, "m3/mol.s")
        self.assertEqual(rate.state["CH3COOH-l"].unit, "mol/m3")
        self.assertEqual(rate.state["CH3OH-l"].order, 1)

    def test_expanded_yaml_matches_estherification_models_and_calc(self):
        yaml_text = """
        REFERENCES:
          REACTION-1:
            NAME: reaction 1
            DESCRIPTION: Artificial mild reversible esterification rate for debugging liquid PBR behavior
            BASIS: concentration
            REACTION: CH3COOH(l) + CH3OH(l) <=> C3H6O2(l) + H2O(l)
            PARAMETERS:
              kf:
                value: 1.0e-6
                unit: m3/mol.s
                symbol: k_f
              kr:
                value: 2.0e-7
                unit: m3/mol.s
                symbol: k_r
            ARGS:
              T:
                description: temperature
                value: 0.0
                unit: K
                symbol: T
              rho_B:
                description: catalyst-bed bulk density
                value: 0.0
                unit: kg/m3
                symbol: rho_B
            RETURN:
              name: r1
              description: Artificial mild reversible rate
              value: 0.0
              unit: mol/m3.s
              symbol: r1
              expression: r
            STATE:
              CH3COOH-l:
                order: 1
                unit: mol/m3
              CH3OH-l:
                order: 1
                unit: mol/m3
              C3H6O2-l:
                order: 1
                unit: mol/m3
              H2O-l:
                order: 1
                unit: mol/m3
            EXPRESSION:
              - c_acid = C["CH3COOH-l"]
              - c_meoh = C["CH3OH-l"]
              - c_meac = C["C3H6O2-l"]
              - c_h2o = C["H2O-l"]
              - rf = c_acid * c_meoh
              - rr = c_meac * c_h2o
              - r = rho_B * (kf * rf - kr * rr)
        """

        rate = RateAdapter.from_yaml_string(
            textwrap.dedent(yaml_text),
            self.components_l,
        ).to_rate_expressions()[0]

        self.assertEqual(rate.name, "reaction 1")
        self.assertEqual(
            rate.description,
            "Artificial mild reversible esterification rate for debugging liquid PBR behavior",
        )
        self.assertEqual(rate.basis, "concentration")
        self.assertEqual(set(rate.params), {"kf", "kr"})
        self.assertEqual(set(rate.args), {"T", "rho_B"})
        self.assertEqual(rate.ret.symbol, "r1")
        self.assertEqual(set(rate.state), {"CH3COOH-l", "CH3OH-l", "C3H6O2-l", "H2O-l"})

        xi = {
            "CH3COOH-l": CustomProperty(value=1000.0, unit="mol/m3", symbol="C_acid"),
            "CH3OH-l": CustomProperty(value=800.0, unit="mol/m3", symbol="C_meoh"),
            "C3H6O2-l": CustomProperty(value=100.0, unit="mol/m3", symbol="C_meac"),
            "H2O-l": CustomProperty(value=50.0, unit="mol/m3", symbol="C_h2o"),
        }
        args = {
            "rho_B": CustomProperty(value=900.0, unit="kg/m3", symbol="rho_B"),
        }

        result = rate.calc(xi, args=args)
        expected = 900.0 * (1.0e-6 * 1000.0 * 800.0 - 2.0e-7 * 100.0 * 50.0)
        self.assertAlmostEqual(result.value, expected)
        self.assertEqual(result.unit, "mol/m3.s")

    def test_args_description_is_optional(self):
        yaml_text = """
        REFERENCES:
          REACTION-1:
            NAME: reaction 1
            BASIS: concentration
            REACTION: CH3COOH(l) + CH3OH(l) <=> C3H6O2(l) + H2O(l)
            ARGS:
              T:
                value: 298.15
                unit: K
                symbol: T
            EXPRESSION:
              - r = C["CH3COOH-l"] * C["CH3OH-l"]
        """

        rate = RateAdapter.from_yaml_string(
            textwrap.dedent(yaml_text),
            self.components_l,
        ).to_rate_expressions()[0]
        self.assertIn("T", rate.args)

    def test_basis_inference_for_concentration_and_pressure(self):
        concentration_yaml = """
        REFERENCES:
          R1:
            NAME: r1
            REACTION: CH3OH(l) => CH3OH(l)
            EXPRESSION:
              - r = C["CH3OH-l"] ** 2
        """
        pressure_yaml = """
        REFERENCES:
          R1:
            NAME: r1
            REACTION: CO(g) + 2H2(g) => CH3OH(g)
            EXPRESSION:
              - r = P["CO-g"] * P["H2-g"] ** 2
        """

        c_rate = RateAdapter.from_yaml_string(
            textwrap.dedent(concentration_yaml),
            self.components_l,
        ).to_rate_expressions()[0]
        p_rate = RateAdapter.from_yaml_string(
            textwrap.dedent(pressure_yaml),
            self.components_g,
        ).to_rate_expressions()[0]

        self.assertEqual(c_rate.basis, "concentration")
        self.assertEqual(c_rate.state["CH3OH-l"].unit, "mol/m3")
        self.assertEqual(p_rate.basis, "pressure")
        self.assertEqual(p_rate.state["H2-g"].unit, "bar")

    def test_order_inference_and_explicit_override(self):
        yaml_text = """
        REFERENCES:
          R1:
            NAME: r1
            REACTION: CO(g) + 2H2(g) => CH3OH(g)
            STATE:
              H2-g:
                order: 3
                unit: atm
            EXPRESSION:
              - rate_piece = P["CO-g"] * P["H2-g"] ** 2
              - r = 4.0 * rate_piece
        """

        rate = RateAdapter.from_yaml_string(
            textwrap.dedent(yaml_text),
            self.components_g,
        ).to_rate_expressions()[0]

        self.assertEqual(rate.state["CO-g"].order, 1)
        self.assertEqual(rate.state["H2-g"].order, 3)
        self.assertEqual(rate.state["H2-g"].unit, "atm")

    def test_restricted_evaluator_rejects_unsafe_or_unsupported_syntax(self):
        unsafe_yaml = """
        REFERENCES:
          R1:
            NAME: r1
            REACTION: CH3OH(l) => CH3OH(l)
            EXPRESSION:
              - r = __import__("os").system("echo unsafe")
        """
        unsupported_yaml = """
        REFERENCES:
          R1:
            NAME: r1
            REACTION: CH3OH(l) => CH3OH(l)
            EXPRESSION:
              - r = [C["CH3OH-l"]]
        """

        with self.assertRaises(RateExpressionError):
            RateAdapter.from_yaml_string(
                textwrap.dedent(unsafe_yaml),
                self.components_l,
            ).to_rate_expressions()
        with self.assertRaises(RateExpressionError):
            RateAdapter.from_yaml_string(
                textwrap.dedent(unsupported_yaml),
                self.components_l,
            ).to_rate_expressions()


if __name__ == "__main__":
    unittest.main()
