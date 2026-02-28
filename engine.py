import random
import numpy as np
from agents import ConsumptionFirm, CapitalFirm, Bank, Worker, Capitalist
from accounting import Ledger, Entry
import math


class SimulationEngine:
    def __init__(self, config):
        self.config = config
        self.current_step = 0
        self.ze = self.config['households']['search_intensity']['labor']
        self.ledger = Ledger()

        # Containers for all agents
        self.workers = []
        self.capitalists = []
        self.c_firms = []
        self.k_firms = []
        self.bank = None
        self.deposits = {}

        # Setup the world
        self._setup_agents()

    def _setup_agents(self):
        """Creates agents using parameters from the YAML config."""

        self.wage_rate = self.config['firms']['wage_rate']
        self.tau = self.config['firms']['dividend_payout_ratio']

        # 1. Setup Bank
        self.bank = Bank(
            initial_equity=self.config['bank']['initial_equity'],
            r_policy=self.config['bank']['risk_free_rate'],
            markup=self.config['bank']['markup'],
            zeta=self.config['bank']['loss_parameter'],
            theta=self.config['bank']['debt_installment_rate']
        )

        # 2. Setup Households
        for i in range(self.config['simulation']['num_workers']):
            w = Worker(
                worker_id=f"W_{i}",
                initial_wealth=self.config['households']['initial_assets'],
                memory_param=self.config['households']['income_memory_weight'],
                cons_propensity=self.config['households']['wealth_consumption_ratio'],
                search_count=self.config['households']['search_intensity']['consumer']
            )
            self.workers.append(w)

        # 3. Setup C-Firms
        for i in range(self.config['simulation']['num_c_firms']):
            cf = ConsumptionFirm(
                firm_id=f"C_{i}",
                initial_capital=self.config['firms']['c_sector']['initial_capital'],
                initial_price=self.config['firms']['c_sector']['initial_price'],
                initial_liquidity=self.config['firms']['initial_liquidity'],
                dividend_ratio=self.config['firms']['dividend_payout_ratio'],
                theta=self.config['bank']['debt_installment_rate'],
                quantity_adj_param=self.config['firms']['quantity_adjustment'],
                price_adj_max=self.config['firms']['price_adjustment_max'],
                capital_productivity=self.config['firms']['c_sector']['capital_productivity'],
                capital_depreciation=self.config['firms']['c_sector']['capital_depreciation'],
                investment_prob=self.config['firms']['c_sector']['investment_probability'],
                investment_memory=self.config['firms']['c_sector']['investment_memory'],
                desired_utilization=self.config['firms']['c_sector']['desired_utilization'],
                labour_prod=self.config['firms']['k_sector']['labor_productivity'],  # same l productivity for both k and c firms
                search_count=self.config['firms']['c_sector']['search_k_firms']
            )
            # Inject behavioral parameters
            cf.rho = self.config['firms']['quantity_adjustment']
            cf.eta_max = self.config['firms']['price_adjustment_max']
            cf.omega = self.config['firms']['c_sector']['desired_utilization']
            cf.gamma = self.config['firms']['c_sector']['investment_probability']
            cf.delta = self.config['firms']['c_sector']['capital_depreciation']
            cf.kappa = self.config['firms']['c_sector']['capital_productivity']
            cf.initial_production = self.config['firms']['c_sector']['initial_production']
            cf.expected_demand = cf.initial_production
            cf.wage=self.wage_rate
            self.c_firms.append(cf)

        # 4. Setup K-Firms
        for i in range(self.config['simulation']['num_k_firms']):
            kf = CapitalFirm(
                firm_id=f"K_{i}",
                initial_price=self.config['firms']['k_sector']['initial_price'],
                initial_liquidity=self.config['firms']['initial_liquidity'],
                wage_rate=self.config['firms']['wage_rate'],
                dividend_ratio=self.config['firms']['dividend_payout_ratio'],
                theta=self.config['bank']['debt_installment_rate'],
                delta=self.config['firms']['c_sector']['capital_depreciation'],
                quantity_adj_param=self.config['firms']['quantity_adjustment'],
                price_adj_max=self.config['firms']['price_adjustment_max'],
                labor_productivity=self.config['firms']['k_sector']['labor_productivity']
            )
            kf.rho = self.config['firms']['quantity_adjustment']
            kf.eta_max = self.config['firms']['price_adjustment_max']
            kf.alpha = self.config['firms']['k_sector']['labor_productivity']
            kf.initial_production = self.config['firms']['k_sector']['initial_production']
            kf.expected_demand = kf.initial_production

            kf.wage=self.wage_rate
            self.k_firms.append(kf)

        cn=0
        for f in self.c_firms + self.k_firms:
            capitalist=Capitalist(
                capitalist_id=f"B_{cn}",
                initial_wealth=self.config["households"]["initial_assets"],
                owned_firm=f,
                search_count=self.config['households']['search_intensity']['consumer']
            )
            cn+=1
            f.owner=capitalist
            self.capitalists.append(capitalist)


    def run_step(self):
        data=[]
        """
        The recursive loop of the model (Section 2.1 of the paper).
        The order of events is mandatory.
        """
        self.current_step += 1

        # 1. FIRMS' PLANNING: Decide production and investment
        # Use average prices from previous period for adaptive heuristics
        self.avg_p_c = np.mean([f.price for f in self.c_firms])
        self.avg_p_k = np.mean([f.price for f in self.k_firms])

        for cf in self.c_firms:
            cf.update_equity(self.avg_p_c)
            if cf.id=="C_0":
                pass
            cf.adjust_price_and_output(self.avg_p_c)
            cf.plan_invest()

        for kf in self.k_firms:
            kf.update_equity(self.avg_p_k)
            kf.adjust_price_and_output(self.avg_p_k)

        # Banks estimate bankruptcy predictions for leverage levels and prices
        self.bank.estimate_logistic_failure_prob(self.config["simulation"]["save_model"], self.config["simulation"]["use_saved_model"])

        # 1. FIRMS' PLANNING: Decide production
        for f in self.c_firms + self.k_firms:
            f.calculate_labor_demand()

        # 2. CREDIT MARKET: Firms calculate financing gaps and request loans
        self._resolve_credit_market(self.avg_p_k)

        # 3. LABOR MARKET: Firms hire workers (matching Ze)
        self._resolve_labor_market()

        # 4. PRODUCTION: Firms convert L and K into goods
        for f in self.c_firms + self.k_firms:
            f.produce()

        # 5. CAPITAL MARKET: C-firms shop (matching Zk)
        self._resolve_capital_market()

        # 6. GOODS MARKET: Households shop (matching Zc)
        self._resolve_goods_market()

        # 7. ACCOUNTING: Update bank equity, firm dividends, etc.
        data.append(0)
        self._perform_accounting(data)

        return data

    def _resolve_credit_market(self, avg_p_k):
        """Firms ask for loans, Bank calculates risk and rations if necessary."""
        for firm in self.c_firms + self.k_firms:
            if firm.id=="C_0":
                pass
            gap = firm.get_financing_gap(k_goods_price=avg_p_k)
            if gap > 0:
                # Bank sets rate and determines loan amount
                leverage= firm.calculate_leverage(gap)
                rate, phi = self.bank.set_interest_rate(leverage)
                loan_granted = self.bank.get_credit_limit(firm.debt, phi )
                firm.receive_loan(min(gap, loan_granted), rate)

    def _resolve_labor_market(self):
        """Matching unemployed workers to firms (Ze parameter)."""

        # Simplified: all workers supply 1 unit of labor inelastically
        unemployed = [h for h in self.workers if not(h.employed)]
        random.shuffle(unemployed)

        for h in unemployed:
            # Each worker visits Ze firms
            potential_employers = random.sample(self.c_firms + self.k_firms, k=self.ze)
            # Pick firm with highest labor demand
            best_employer = max(potential_employers, key=lambda f: f.labour_demand)
            if best_employer.labour_demand > 0:
                best_employer.hire(h)

    def _resolve_goods_market(self):
        """Households visit Zc firms to consume."""
        for h in self.workers + self.capitalists:
            h.shop(self.c_firms)

    def _resolve_capital_market(self):
        """C-firms visit Zk K-firms to buy Capital goods"""
        for cf in self.c_firms:
            if cf.id=="C_0":
                pass
            cf.shop(self.k_firms)

    def _perform_accounting(self, data):
        """Handle accounting"""

        total_wage=0
        total_spent=0
        for h in self.workers :
            #get wage and spend money on consumption
            if h.employed:
                h.wealth += self.wage_rate - h.spent_amount
                total_wage += self.wage_rate
                total_spent += h.spent_amount
            else:
                h.wealth -= h.spent_amount
                total_spent += h.spent_amount

        #self.ledger.add_entry(Entry("Wages_workers", total_wage, "","w"))
        #self.ledger.add_entry(Entry("Consum_worker", total_spent, "w", "cf"))

        self.bank.intresses=0
        total_wages = 0
        total_sales=0
        for f in self.c_firms:
            if f.id=="C_0":
                pass
            f.pay_intress(self.bank)
            f.repay_loan()
            total_wages += len(f.staff) * self.wage_rate
            total_sales += f.sales * f.price
            f.sales=0
            f.liquidity -= len(f.staff) * self.wage_rate

        data[0]+=total_wages

        #self.ledger.add_entry(Entry("Wages_cf", total_wages, "cf", ""))
        #self.ledger.add_entry(Entry("Sales_cf", total_sales, "", "cf"))

        total_wages = 0
        total_sales = 0
        for f in self.k_firms:
            f.pay_intress(self.bank)
            f.repay_loan()
            total_wages += len(f.staff) * self.wage_rate
            total_sales += f.sales * f.price
            f.sales=0
            f.liquidity -= len(f.staff) * self.wage_rate

        #self.ledger.add_entry(Entry("Wages_kf", total_wages, "kf", ""))
        #self.ledger.add_entry(Entry("Sales_kf", total_sales, "", "kf"))


        bankrupt=[]
        history_for_bank=[]
        # Dividends tau
        total_divs=0
        for f in self.c_firms:
            if f.id=="C_0":
                pass
            f.depreciate_capital()
            f.recalculate_book_capital(self.avg_p_k)

            if f.check_bankruptcy():
                bankrupt.append(f)
                history_for_bank.append((f.lmbda, 1))
            else:
                dividents=f.dividends()
                total_divs += dividents
                f.payout_dividents()
                history_for_bank.append((f.lmbda, 0))

        cleaned = [tup for tup in history_for_bank if not any(math.isnan(val) for val in tup)]
        self.bank.c_history.append(cleaned)

        #self.ledger.add_entry(Entry("Dividents_cf", total_divs, "cf", "c"))

        history_for_bank = []
        total_divs = 0
        for f in self.k_firms:
            f.depreciate_capital()

            if f.check_bankruptcy():
                bankrupt.append(f)
                history_for_bank.append((f.lmbda, 1))
            else:
                dividents = f.dividends()
                total_divs += dividents
                f.payout_dividents()
                history_for_bank.append((f.lmbda, 0))

        cleaned = [tup for tup in history_for_bank if not any(math.isnan(val) for val in tup)]
        self.bank.k_history.append(cleaned)

        for f in bankrupt:
            f.process_bankruptcy()

        #self.ledger.add_entry(Entry("Dividents_kf", total_divs, "kf", "c"))

if __name__=="__main__":
    pass