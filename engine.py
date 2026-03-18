import random
import numpy as np
from agents import ConsumptionFirm, CapitalFirm, Bank, Worker, Capitalist
from accounting import Ledger, Entry
from mysql_connector.mnemosyne import *
import math
import yaml
import os
from dotenv import load_dotenv
import pickle


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
            start_seed = random.randint(0, int(1e10))


        runid = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890', k=15))

        if "config_id" in self.config:
            run_data = {
                "config": self.config["config_id"],
                "run_id": runid,
                "name": name,
                "version": "1.0",
                "start_seed": start_seed
            }
            send_run_data(self.db_creds, run_data)

        run=SimulationEngine(self.config, name=name, start_seed=start_seed, runid=runid)
        if "config_id" in self.config:
            populate_run_data(self.db_creds, run)

        return run

    def run_steps(self, run, steps=1):
        self.runs_to_send={
            "step_data": [],
            "bank_data": [],
            "workers": [],
            "c_firms": [],
            "k_firms": [],
            "capitalists": []
        }
        for _ in range(steps):
            time_processing=run.run_step()
            if self.db_creds is not None:
                self.save_run_data(run)


    def save_run_data(self, run):
        # logic here is to try to run X steps and then try to send data to db for speed, instead of sending data after every step
        step_data={
            "step_id": run.current_step_id,
            "run_id": run.runid,
            "start_state": pickle.dumps(run.current_step_start_state),
            "end_state": pickle.dumps(run.current_step_end_state),
            "step_no": run.current_step
        }

        bank_data={
            "step_id": run.current_step_id,
            "equity": run.bank.equity,
            "r": run.bank.r,
            "c_history": str(run.bank.c_history),   # proper serialization for later
            "k_history": str(run.bank.k_history),
            "c_coef": run.bank.c_model_coefficient if run.bank.c_model_coefficient is not None else -1,
            "c_intercept": run.bank.c_model_intercept if run.bank.c_model_intercept is not None else -1,
            "k_coef": run.bank.k_model_coefficient if run.bank.k_model_coefficient is not None else -1,
            "k_intercept": run.bank.k_model_intercept if run.bank.k_model_intercept is not None else -1,
            "intresses":run.bank.intresses,
            "losses":run.bank.losses
        }

        workers=[]
        for w in run.workers:
            workers.append({
                "step_id": run.current_step_id,
                "worker_id": w.id,
                "wealth": w.wealth,
                "human_wealth": w.human_wealth,
                "budget": w.budget,
                "spent_amount": w.spent_amount,
                "employed": w.employed,
                "employer": w.employer.id if w.employer else None
            })

        c_firms=[]
        for f in run.c_firms:
            c_firms.append({
                "step_id": run.current_step_id,
                "cf_id": f.id,
                "liquidity": f.liquidity,
                "price": f.price,
                "equity": f.equity,
                "debt": f.debt,
                "profit": f.profit,
                "production": f.production,
                "sales": f.sales,
                "queue": f.queue,
                "expected_demand": f.expected_demand,
                "intresses": f.intresses,
                "labour_demand": f.labour_demand,
                "lmbda": f.lmbda,
                "loans": json.dumps(f.get_all_loans()),  # proper serialization for later
                "staff": json.dumps([w.id for w in f.staff]),
                "first_step": f.first_step,
                "capital": f.capital,
                "capital_avg": f.capital_avg,
                "invested": f.invested,
                "planned_production": f.planned_production,
                "planned_investment": f.planned_investment,
                "wage_bill": f.wage_bill,
                "investment_cost": f.investment_cost,
                "capital_book": f.capital_book,
                "desired_capital": f.desired_capital,
                "omega": f.omega
            })

        k_firms = []
        for f in run.k_firms:
            k_firms.append({
                "step_id": run.current_step_id,
                "kf_id": f.id,
                "liquidity": f.liquidity,
                "price": f.price,
                "equity": f.equity,
                "debt": f.debt,
                "profit": f.profit,
                "production": f.production,
                "sales": f.sales,
                "inventory": f.inventory,
                "queue": f.queue,
                "expected_demand": f.expected_demand,
                "intresses": f.intresses,
                "loans": json.dumps(f.get_all_loans()),  # proper serialization for later
                "staff": json.dumps([w.id for w in f.staff]),
                "labour_demand": f.labour_demand,
                "lmbda": f.lmbda,
                "wage_bill": f.wage_bill,
                "planned_production": f.planned_production,
                "first_step": f.first_step
            })

        capitalists=[]
        for c in run.capitalists:
            capitalists.append({
                "step_id": run.current_step_id,
                "capitalist_id": c.id,
                "budget": c.budget,
                "wealth": c.wealth,
                "human_wealth": c.human_wealth,
                "spent_amount": c.spent_amount
            })

        self.runs_to_send["step_data"].append(step_data)
        self.runs_to_send["bank_data"].append(bank_data)
        self.runs_to_send["workers"].extend(workers)
        self.runs_to_send["c_firms"].extend(c_firms)
        self.runs_to_send["k_firms"].extend(k_firms)
        self.runs_to_send["capitalists"].extend(capitalists)
        if len(self.runs_to_send["step_data"])>=10:  # batch size of 10 steps before sending to DB
            send_run_steps_data(self.db_creds, self.runs_to_send)
            self.runs_to_send={
                "step_data": [],
                "bank_data": [],
                "workers": [],
                "c_firms": [],
                "k_firms": [],
                "capitalists": []
            }
        return 1

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
        self.to_process_bankruptcies=[]

        # Setup the world
        self._setup_agents()

        self.current_step_start_state = None
        self.current_step_end_state = None


    def _setup_agents(self):
        """Creates agents using parameters from the YAML config."""

        total_money=0

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
            total_money+=self.config['households']['initial_assets']

        self.zc=self.config['households']['search_intensity']['consumer']
        self.ze = self.config['households']['search_intensity']['labor']

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
                labour_prod=self.config['firms']['k_sector']['labor_productivity'],
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
            cf.production = cf.initial_production  # So plan_invest() has valid production in period 1
            cf.expected_demand = cf.initial_production
            cf.wage=self.wage_rate
            self.c_firms.append(cf)
            total_money+=self.config['firms']['initial_liquidity']

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
            kf.initial_production = self.config['firms']['k_sector']['initial_production']
            kf.production = kf.initial_production  # So first-period adjust has valid production
            kf.expected_demand = kf.initial_production

            kf.wage=self.wage_rate
            self.k_firms.append(kf)
            total_money+=self.config['firms']['initial_liquidity']

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
            total_money+=self.config["households"]["initial_assets"]

        self.bank.reserves=total_money


    def run_step(self):
        """
        The recursive loop of the model (Section 2.1 of the paper).
        The order of events is mandatory.
        """

        self.current_step_start_state = random.getstate()

        self.current_step_id=random.randint(0, int(1e9))
        self.current_step += 1

        # 1. FIRMS' PLANNING: Decide production and investment
        # Use average prices from previous period for adaptive heuristics
        self.avg_p_c = np.mean([f.price for f in self.c_firms])
        self.avg_p_k = np.mean([f.price for f in self.k_firms])

        self.bank.losses = 0
        for f in self.to_process_bankruptcies:
            f.process_bankruptcy(self.bank, self.avg_p_k)

        self.bank.equity += - self.bank.losses
        # Bank bailout: recapitalize if equity goes negative
        if self.bank.equity <= 0:
            self.bank.equity = self.config['bank']['initial_equity'] * 0.5
        self.bank.divs=0

        for cf in self.c_firms:
            cf.sales=0
            cf.update_equity(self.avg_p_c)
            cf.adjust_price_and_output(self.avg_p_c)
            cf.queue=0
            cf.plan_invest()

        for kf in self.k_firms:
            kf.sales=0
            kf.update_equity(self.avg_p_k)
            kf.adjust_price_and_output(self.avg_p_k)
            kf.queue=0

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

        # 5.5. PAY WAGES + UPDATE HUMAN WEALTH (before goods market so workers have income for budgeting)
        self._pay_wages_and_update_income()

        # 6. GOODS MARKET: Households shop (matching Zc)
        self._resolve_goods_market()

        # 7. ACCOUNTING: Interest, dividends, depreciation, bankruptcy
        self._perform_accounting([])

        self.current_step_end_state = random.getstate()

        return self.time_processing

    def _resolve_credit_market(self, avg_p_k):
        """Firms ask for loans, Bank calculates risk and rations if necessary."""
        for firm in self.c_firms + self.k_firms:
            gap = firm.get_financing_gap(k_goods_price=avg_p_k)
            if gap > 0:
                # Bank sets rate and determines loan amount
                leverage= firm.calculate_leverage(gap)
                firm_type = 'K' if isinstance(firm, CapitalFirm) else 'C'
                rate, phi = self.bank.set_interest_rate(leverage, firm_type)
                loan_granted = self.bank.get_credit_limit(firm.debt, phi )
                if loan_granted > 0:
                    firm.receive_loan(min(gap, loan_granted), rate)
            firm.calculate_leverage(0)

    def _resolve_labor_market(self):
        """Matching unemployed workers to firms (Ze parameter)."""

        unemployed = [h for h in self.workers if not h.employed]
        if not unemployed:
            return

        np.random.shuffle(unemployed)

        all_firms = self.c_firms + self.k_firms
        num_firms = len(all_firms)

        if num_firms == 0:
            return

        sample_size = min(self.ze, num_firms)
        demands_cache = np.array(
            [math.ceil(max(f.labour_demand, 0)) for f in all_firms],
            dtype=np.int32
        )

        for worker in unemployed:
            firm_indices = np.random.choice(num_firms, size=sample_size, replace=False)
            for firm_idx in firm_indices:
                if demands_cache[firm_idx] <= 0:
                    continue

                employer = all_firms[firm_idx]
                demands_cache[firm_idx] -= 1
                employer.labour_demand = max(employer.labour_demand - 1, 0)
                employer.staff.append(worker)
                worker.employed = True
                worker.employer = employer
                break

    def _resolve_goods_market(self):
        """Households visit Zc firms to consume."""
        sorted_c_firms = sorted(self.c_firms, key=lambda f: f.price)

        shoppers = self.workers + self.capitalists
        np.random.shuffle(shoppers)

        num_firms = len(sorted_c_firms)
        if num_firms == 0:
            return

        sample_size = min(self.zc, num_firms)

        for h in shoppers:
            visited_indices = np.random.choice(num_firms, size=sample_size, replace=False)
            visited_firms = [sorted_c_firms[idx] for idx in visited_indices]
            visited_firms.sort(key=lambda f: f.price)

            h.determine_budget()
            remaining_budget = h.budget
            h.spent_amount = 0.0

            for firm in visited_firms:
                if remaining_budget <= 0:
                    break

                if firm.inventory <= 0:
                    continue

                price = firm.price
                desired_qty = remaining_budget / price

                actual_qty = min(desired_qty, firm.inventory)
                firm.inventory -= actual_qty
                firm.sales += actual_qty
                if actual_qty < desired_qty:
                    firm.queue += desired_qty - actual_qty

                cost = actual_qty * price
                remaining_budget -= cost
                h.spent_amount += cost

                firm.liquidity += cost


    def _resolve_capital_market(self):
        """C-firms visit Zk K-firms to buy Capital goods"""
        for cf in self.c_firms:
            cf.shop(self.k_firms)

    def _pay_wages_and_update_income(self):
        """Pay wages and update human_wealth BEFORE goods market."""
        for h in self.workers:
            if h.employed:
                h.wealth += self.wage_rate
                h.employer.liquidity -= self.wage_rate
                h.recalculate_human_wealth(self.wage_rate)
            else:
                h.recalculate_human_wealth(0.0)

    def _perform_accounting(self, data):
        """Handle post-market accounting: spending deduction, interest, dividends, bankruptcy."""

        # Deduct spending from wealth
        for h in self.workers:
            h.wealth -= h.spent_amount

        for c in self.capitalists:
            c.wealth -= c.spent_amount

        self.bank.intresses=0
        for f in self.c_firms:
            f.pay_intress(self.bank)
            f.repay_loan()

        for f in self.k_firms:
            f.pay_intress(self.bank)
            f.repay_loan()


        divs=self.bank.dividends()
        self.bank.equity += self.bank.intresses - divs
        caps=len(self.capitalists)
        for c in self.capitalists:
            c.wealth+= divs/caps
            c.income=divs/caps

        bankrupt=[]
        history_for_bank=[]
        # Dividends tau
        for f in self.c_firms:
            f.wage_bill= len(f.staff) * self.wage_rate
            f.depreciate_capital(self.avg_p_k)
            f.recalculate_book_capital(self.avg_p_k)

            if f.check_bankruptcy():
                bankrupt.append(f)
                history_for_bank.append((f.lmbda, 1))
            else:
                f.dividends()
                if f.debt > 0:
                    history_for_bank.append((f.lmbda, 0))
            f.owner.recalulate_human_wealth()

        cleaned = [tup for tup in history_for_bank if not math.isnan(tup[0])]
        self.bank.c_history.extend(cleaned)

        history_for_bank = []
        for f in self.k_firms:
            f.wage_bill = len(f.staff) * self.wage_rate
            f.depreciate_capital()

            if f.check_bankruptcy():
                bankrupt.append(f)
                history_for_bank.append((f.lmbda, 1))
            else:
                f.dividends()
                if f.debt > 0:
                    history_for_bank.append((f.lmbda, 0))

            f.owner.recalulate_human_wealth()

        cleaned = [tup for tup in history_for_bank if not math.isnan(tup[0])]
        self.bank.k_history.extend(cleaned)

        self.to_process_bankruptcies = bankrupt


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
