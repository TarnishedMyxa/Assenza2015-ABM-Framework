import random
import numpy as np
from agents import ConsumptionFirm, CapitalFirm, Bank, Worker, Capitalist
from accounting import Ledger, Entry
from mysql_connector.mnemosyne import *
import math
import yaml
import os
from dotenv import load_dotenv


class runManager:
    def __init__(self, settings):
        self.settings = settings
        if self.settings["CONFIG"] == "DB":
            load_dotenv()
            self.db_creds = {
                'host': os.getenv("host"),
                'port': int(os.getenv("port")),
                'user': os.getenv("user"),
                'password': os.getenv("password"),
                'database': os.getenv("database")
            }
            self.config = fetch_config_from_db(self.db_creds, self.settings["db_config_id"])
            self.config['config_id'] = self.settings["db_config_id"]
            print(f"Config fetched from DB with ID: {self.settings['db_config_id']}")
        else:
            self.db_creds=None
            with open(self.settings["yaml_config_path"], "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
                print("YAML CONFIG LOADED")
                if self.settings["create_new_config_in_db"]:
                    cnf_id = send_config_to_db(self.db_creds, self.config)
                    self.config['config_id'] = cnf_id
                    print(f"Config sent to DB with ID: {cnf_id}")

    def create_new_run(self, name=None, start_seed=None ):
        if start_seed is None:
            start_seed = random.randint(0, 1e10)


        runid = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890', k=15))

        if self.config["config_id"] is not None:
            run_data = {
                "config": self.config["config_id"],
                "run_id": runid,
                "name": name,
                "version": "1.0",
                "start_seed": start_seed
            }
            send_run_data(self.db_creds, run_data)

        run=SimulationEngine(self.config, name=name, start_seed=start_seed, runid=runid)

        populate_run_data(self.db_creds, run)

        return run

    def run_steps(self, run, steps=1):
        for _ in range(steps):
            time_processing=run.run_step()
            #update_run_data(self.db_creds, run, time_processing)

    def _drop_all_runs_from_db(self):
        drop_all_runs(self.db_creds)

class SimulationEngine:
    def __init__(self, config, name=None, start_seed=None, runid=None):
        self.runid = runid
        self.name = name
        self.start_seed = start_seed
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
        self.time_processing={}

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

        self.zc=self.config['households']['search_intensity']['consumer']

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
        self.bank.estimate_logistic_failure_prob()


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
        #data.append(0)
        self._perform_accounting([])

        return self.time_processing

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

        unemployed = [h for h in self.workers if not h.employed]
        if not unemployed:
            return

        np.random.shuffle(unemployed)

        all_firms = self.c_firms + self.k_firms
        num_firms = len(all_firms)

        demands_cache = np.array([f.labour_demand for f in all_firms], dtype=np.int32)

        samples = np.random.randint(0, num_firms, size=(len(unemployed), self.ze))

        for i, worker in enumerate(unemployed):
            firm_indices = samples[i]
            sampled_demands = demands_cache[firm_indices]
            local_idx = np.argmax(sampled_demands)
            best_f_idx = firm_indices[local_idx]
            if demands_cache[best_f_idx] > 0:
                best_employer = all_firms[best_f_idx]
                demands_cache[best_f_idx] -= 1
                best_employer.labour_demand -= 1
                best_employer.staff.append(worker)
                worker.employed = True
                worker.employer = best_employer

    def _resolve_goods_market(self):
        """Households visit Zc firms to consume."""
        sorted_c_firms = sorted(self.c_firms, key=lambda f: f.price)

        shoppers = self.workers + self.capitalists
        np.random.shuffle(shoppers)

        num_firms = len(sorted_c_firms)

        all_indices = np.random.randint(0, num_firms, size=(len(shoppers), self.zc))

        for i, h in enumerate(shoppers):
            visited_indices = all_indices[i]

            visited_indices.sort()

            remaining_budget = h.budget
            h.spent_amount = 0.0

            for idx in visited_indices:
                if remaining_budget <= 0:
                    break

                firm = sorted_c_firms[idx]

                if firm.inventory <= 0:
                    continue

                price = firm.price
                desired_qty = remaining_budget / price

                actual_qty = min(desired_qty, firm.inventory)
                firm.inventory -= actual_qty
                firm.sales += actual_qty

                cost = actual_qty * price
                remaining_budget -= cost
                h.spent_amount += cost

                firm.liquidity += cost

            if remaining_budget > 0:
                q_price = firm.price
                firm.queue += remaining_budget / q_price

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

        cleaned = [tup for tup in history_for_bank if not math.isnan(tup[0])]
        self.bank.c_history.extend(cleaned)

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

        cleaned = [tup for tup in history_for_bank if not math.isnan(tup[0])]
        self.bank.k_history.extend(cleaned)

        for f in bankrupt:
            f.process_bankruptcy()

        #self.ledger.add_entry(Entry("Dividents_kf", total_divs, "kf", "c"))

def send_config_to_db(db_creds, config):
    cnf={
        "periods": config['simulation']['periods'],
        "num_workers": config['simulation']['num_workers'],
        "num_c_firms": config['simulation']['num_c_firms'],
        "num_k_firms": config['simulation']['num_k_firms'],
        "income_memory_weight": config['households']['income_memory_weight'],
        "wealth_consumption_ratio": config['households']['wealth_consumption_ratio'],
        "initial_assets": config['households']['initial_assets'],
        "si_labor": config['households']['search_intensity']['labor'],
        "si_consumer": config['households']['search_intensity']['consumer'],
        "dividend_payout_ratio": config['firms']['dividend_payout_ratio'],
        "qty_adjustment": config['firms']['quantity_adjustment'],
        "p_adjustment_max": config['firms']['price_adjustment_max'],
        "wage_rate": config['firms']['wage_rate'],
        "init_m": config['firms']['c_sector']['initial_capital'],
        "init_capital": config['firms']['c_sector']['initial_capital'],
        "c_init_production": config['firms']['c_sector']['initial_production'],
        "c_productivity": config['firms']['c_sector']['capital_productivity'],
        "invest_prob": config['firms']['c_sector']['investment_probability'],
        "c_depreciation": config['firms']['c_sector']['capital_depreciation'],
        "invest_memory": config['firms']['c_sector']['investment_memory'],
        "desired_util": config['firms']['c_sector']['desired_utilization'],
        "search_k": config['firms']['c_sector']['search_k_firms'],
        "c_init_p": config['firms']['c_sector']['initial_price'],
        "k_initial_production": config['firms']['k_sector']['initial_production'],
        "l_productivity": config['firms']['k_sector']['labor_productivity'],
        "k_init_p": config['firms']['k_sector']['initial_price'],
        "b_init_e": config['bank']['initial_equity'],
        "risk_free_rate": config['bank']['risk_free_rate'],
        "markup": config['bank']['markup'],
        "loss_param": config['bank']['loss_parameter'],
        "debt_installment_rate": config['bank']['debt_installment_rate']
    }
    cnf_id=send_config_data(db_creds, cnf)
    return cnf_id

def fetch_config_from_db(db_creds, config_id):
    data=fetch_config_data(db_creds, config_id)

    config={
        'simulation': {
            'periods': data['periods'],
            'num_workers': data['num_workers'],
            'num_c_firms': data['num_c_firms'],
            'num_k_firms': data['num_k_firms']
        },
        'households': {
            'income_memory_weight': data['income_memory_weight'],
            'wealth_consumption_ratio': data['wealth_consumption_ratio'],
            'initial_assets': data['initial_assets'],
            'search_intensity': {
                'labor': data['si_labor'],
                'consumer': data['si_consumer']
            }
        },
        'firms': {
            'dividend_payout_ratio': data['dividend_payout_ratio'],
            'quantity_adjustment': data['qty_adjustment'],
            'price_adjustment_max': data['p_adjustment_max'],
            'wage_rate': data['wage_rate'],
            "initial_liquidity": data['init_m'],
            'c_sector': {
                "initial_price": data['c_init_p'],
                'initial_capital': data['init_capital'],
                'initial_production': data['c_init_production'],
                'capital_productivity': data['c_productivity'],
                'investment_probability': data['invest_prob'],
                'capital_depreciation': data['c_depreciation'],
                'investment_memory': data['invest_memory'],
                'desired_utilization': data['desired_util'],
                'search_k_firms': data['search_k']
            },
            'k_sector': {
                'initial_production': data['k_initial_production'],
                'labor_productivity': data['l_productivity'],
                'initial_price': data['k_init_p'],
            }
        },
        'bank': {
            'initial_equity': data['b_init_e'],
            'risk_free_rate': data['risk_free_rate'],
            'markup': data['markup'],
            'loss_parameter': data['loss_param'],
            'debt_installment_rate': data['debt_installment_rate']
        }
    }
    return config

if __name__=="__main__":
    pass