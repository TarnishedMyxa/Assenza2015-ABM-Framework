import os
import sys
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from agents.bank import Bank
from agents.firms import CapitalFirm, ConsumptionFirm
from engine import SimulationEngine
from experiment_utils import load_config


class CapitalFirmAdjustmentTests(unittest.TestCase):
    def make_firm(self):
        firm = CapitalFirm(
            firm_id="K_test",
            initial_price=2.0,
            initial_liquidity=10.0,
            wage_rate=1.0,
            dividend_ratio=0.2,
            theta=0.05,
            delta=0.02,
            quantity_adj_param=0.5,
            price_adj_max=0.1,
            labor_productivity=0.5,
        )
        firm.wage = 1.0
        firm.initial_production = 4.0
        firm.production = 4.0
        firm.expected_demand = 4.0
        firm.first_step = False
        firm.get_adjustment_shock = lambda: 0.1
        return firm

    def test_stockout_and_underpriced_raises_price(self):
        firm = self.make_firm()
        firm.price = 2.0
        firm.inventory = 0.0
        firm.queue = 1.0

        firm.adjust_price_and_output(market_avg_price=3.0)

        self.assertAlmostEqual(firm.price, 2.2)
        self.assertAlmostEqual(firm.planned_production, 4.0)

    def test_excess_inventory_and_overpriced_cuts_price(self):
        firm = self.make_firm()
        firm.price = 3.0
        firm.inventory = 6.0
        firm.queue = 0.0

        firm.adjust_price_and_output(market_avg_price=2.5)

        self.assertAlmostEqual(firm.price, 2.7)
        self.assertAlmostEqual(firm.planned_production, 4.0)

    def test_stockout_without_price_disadvantage_raises_quantity(self):
        firm = self.make_firm()
        firm.price = 3.0
        firm.inventory = 0.0
        firm.queue = 2.0

        firm.adjust_price_and_output(market_avg_price=2.5)

        self.assertAlmostEqual(firm.expected_demand, 5.0)
        self.assertAlmostEqual(firm.planned_production, 5.0)

    def test_excess_inventory_without_price_premium_cuts_quantity(self):
        firm = self.make_firm()
        firm.price = 2.0
        firm.inventory = 6.0
        firm.queue = 0.0

        firm.adjust_price_and_output(market_avg_price=2.5)

        self.assertAlmostEqual(firm.expected_demand, 1.0)
        self.assertAlmostEqual(firm.planned_production, 1.0)

    def test_journal_switches_use_forecast_error_and_inventory_offset(self):
        firm = self.make_firm()
        firm.use_cost_price_floor = True
        firm.use_min_output_rule = True
        firm.use_forecast_error_delta = True
        firm.subtract_carried_inventory = True
        firm.price = 1.5
        firm.inventory = 4.0
        firm.queue = 0.0
        firm.forecast_error = -2.0

        firm.adjust_price_and_output(market_avg_price=1.0)

        self.assertAlmostEqual(firm.expected_demand, 5.0)
        self.assertAlmostEqual(firm.planned_production, 1.0)
        self.assertAlmostEqual(firm.price, 2.0)


class BankCreditLimitTests(unittest.TestCase):
    def test_credit_limit_monotonicity(self):
        for mode in ("current", "journal_candidate"):
            with self.subTest(mode=mode):
                low_equity_bank = Bank(initial_equity=100.0, credit_limit_mode=mode)
                high_equity_bank = Bank(initial_equity=200.0, credit_limit_mode=mode)
                self.assertLessEqual(
                    low_equity_bank.get_credit_limit(current_debt=10.0, phi=0.2),
                    high_equity_bank.get_credit_limit(current_debt=10.0, phi=0.2),
                )

                bank = Bank(initial_equity=200.0, credit_limit_mode=mode)
                self.assertLessEqual(
                    bank.get_credit_limit(current_debt=20.0, phi=0.2),
                    bank.get_credit_limit(current_debt=10.0, phi=0.2),
                )
                self.assertLessEqual(
                    bank.get_credit_limit(current_debt=10.0, phi=0.4),
                    bank.get_credit_limit(current_debt=10.0, phi=0.2),
                )

    def test_sector_specific_phi_caps_and_fallbacks(self):
        bank = Bank(
            initial_equity=200.0,
            c_phi_cap=0.1,
            k_phi_cap=0.5,
        )
        bank.c_model = object()
        bank.k_model = object()
        bank.c_model_coefficient = 10.0
        bank.c_model_intercept = 10.0
        bank.k_model_coefficient = 10.0
        bank.k_model_intercept = 10.0

        self.assertLessEqual(bank.get_bankruptcy_prob(0.9, "C"), 0.1)
        self.assertLessEqual(bank.get_bankruptcy_prob(0.9, "K"), 0.5)

        bank.c_model = None
        bank.k_model = None
        bank.c_model_coefficient = 0.0
        bank.c_model_intercept = 0.0
        bank.k_model_coefficient = 0.0
        bank.k_model_intercept = 10.0

        self.assertLessEqual(bank.get_bankruptcy_prob(0.9, "C"), 0.1)
        self.assertLessEqual(bank.get_bankruptcy_prob(0.9, "K"), 0.5)
        self.assertGreater(bank.get_bankruptcy_prob(0.9, "K"), bank.get_bankruptcy_prob(0.9, "C"))

    def test_fit_toggle_keeps_overridden_coefficients(self):
        bank = Bank(
            initial_equity=200.0,
            c_fit_enabled=False,
            k_fit_enabled=False,
            c_logit_coefficient=2.0,
            c_logit_intercept=-5.0,
            k_logit_coefficient=4.0,
            k_logit_intercept=-4.0,
        )
        bank.c_history.extend([(0.2, 0), (0.8, 1), (0.7, 1), (0.1, 0)])
        bank.k_history.extend([(0.2, 0), (0.8, 1), (0.7, 1), (0.1, 0)])

        bank.estimate_logistic_failure_prob()

        self.assertAlmostEqual(bank.c_model_coefficient, 2.0)
        self.assertAlmostEqual(bank.c_model_intercept, -5.0)
        self.assertAlmostEqual(bank.k_model_coefficient, 4.0)
        self.assertAlmostEqual(bank.k_model_intercept, -4.0)

    def test_min_fit_observations_blocks_early_reestimation(self):
        bank = Bank(
            initial_equity=200.0,
            c_min_fit_observations=10,
            k_min_fit_observations=10,
            c_logit_coefficient=3.0,
            c_logit_intercept=-4.0,
            k_logit_coefficient=3.0,
            k_logit_intercept=-4.0,
        )
        bank.c_history.extend([(0.2, 0), (0.8, 1), (0.7, 1), (0.1, 0)])
        bank.k_history.extend([(0.2, 0), (0.8, 1), (0.7, 1), (0.1, 0)])

        bank.estimate_logistic_failure_prob()

        self.assertAlmostEqual(bank.c_model_coefficient, 3.0)
        self.assertAlmostEqual(bank.c_model_intercept, -4.0)
        self.assertAlmostEqual(bank.k_model_coefficient, 3.0)
        self.assertAlmostEqual(bank.k_model_intercept, -4.0)


class ConsumptionFirmCapitalTimingTests(unittest.TestCase):
    def make_c_firm(self):
        firm = ConsumptionFirm(
            firm_id="C_test",
            initial_capital=100.0,
            initial_price=1.0,
            initial_liquidity=50.0,
            labour_prod=1.0,
            dividend_ratio=0.2,
            theta=0.05,
            quantity_adj_param=0.5,
            price_adj_max=0.1,
            capital_productivity=1.0,
            capital_depreciation=0.1,
            investment_prob=1.0,
            investment_memory=0.9,
            desired_utilization=0.8,
            search_count=1,
        )
        firm.production = 50.0
        return firm

    def test_shop_records_realized_investment_before_capital_update(self):
        buyer = self.make_c_firm()
        buyer.planned_investment = 10.0
        buyer.liquidity = 50.0

        seller = CapitalFirm(
            firm_id="K_test",
            initial_price=2.0,
            initial_liquidity=10.0,
            wage_rate=1.0,
            dividend_ratio=0.2,
            theta=0.05,
            delta=0.02,
            quantity_adj_param=0.5,
            price_adj_max=0.1,
            labor_productivity=1.0,
        )
        seller.inventory = 10.0

        buyer.shop([seller])

        self.assertAlmostEqual(buyer.capital, 100.0)
        self.assertAlmostEqual(buyer.realized_investment, 10.0)
        self.assertAlmostEqual(buyer.invested, 20.0)

    def test_depreciation_applies_to_installed_capital_then_adds_investment(self):
        firm = self.make_c_firm()
        firm.realized_investment = 10.0

        firm.depreciate_capital(k_price=2.0)

        self.assertAlmostEqual(firm.wear_and_tear, 10.0)
        self.assertAlmostEqual(firm.capital, 105.0)
        self.assertAlmostEqual(firm.realized_investment, 0.0)


class CapitalFirmAccountingTests(unittest.TestCase):
    def test_inventory_depreciation_reduces_stock_not_profit_term(self):
        firm = CapitalFirm(
            firm_id="K_test",
            initial_price=2.0,
            initial_liquidity=10.0,
            wage_rate=1.0,
            dividend_ratio=0.2,
            theta=0.05,
            delta=0.1,
            quantity_adj_param=0.5,
            price_adj_max=0.1,
            labor_productivity=1.0,
        )
        firm.inventory = 20.0

        firm.depreciate_capital()

        self.assertAlmostEqual(firm.inventory, 18.0)
        self.assertAlmostEqual(firm.capital_apreciation, 0.0)

    def test_equity_uses_liquidity_minus_debt_only(self):
        firm = CapitalFirm(
            firm_id="K_test",
            initial_price=2.0,
            initial_liquidity=10.0,
            wage_rate=1.0,
            dividend_ratio=0.2,
            theta=0.05,
            delta=0.1,
            quantity_adj_param=0.5,
            price_adj_max=0.1,
            labor_productivity=1.0,
        )
        firm.inventory = 50.0
        firm.liquidity = 12.0
        firm.receive_loan(5.0, 0.02)
        firm.receive_loan(3.0, 0.03)

        self.assertAlmostEqual(firm.update_equity(k_price=2.4), 12.0)
        self.assertFalse(firm.check_bankruptcy())

        firm.liquidity = 7.9
        self.assertTrue(firm.check_bankruptcy())


class EngineDiagnosticsTests(unittest.TestCase):
    def test_engine_emits_step_diagnostics(self):
        config = load_config(os.path.join(REPO_ROOT, "config.yaml"))
        config["simulation"]["num_workers"] = 30
        config["simulation"]["num_c_firms"] = 4
        config["simulation"]["num_k_firms"] = 2
        config["experiments"]["diagnostics"] = True

        engine = SimulationEngine(config, start_seed=123)
        engine.run_step()

        self.assertEqual(len(engine.step_diagnostics_history), 1)
        diagnostics = engine.last_step_diagnostics
        for key in (
            "opening_bank_equity",
            "closing_bank_equity",
            "new_loans_granted",
            "interest_received",
            "principal_repaid",
            "bad_debt_losses",
            "bank_dividends",
            "mean_c_leverage",
            "mean_k_leverage",
            "planned_investment_total",
            "realized_investment_total",
            "investment_fulfillment",
            "k_queue_total",
        ):
            self.assertIn(key, diagnostics)


if __name__ == "__main__":
    unittest.main()
