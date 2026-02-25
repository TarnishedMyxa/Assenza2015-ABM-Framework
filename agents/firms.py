import random
import uuid
import math


class BaseFirm:
    """
    Parent class containing shared logic for accounting, bankruptcy, and state management.
    """

    def __init__(self, firm_id, initial_liquidity, initial_price,
                 labour_prod, dividend_ratio, theta, quantity_adj_param, price_adj_max):
        self.id = firm_id
        self.liquidity = initial_liquidity  # D_f
        self.price = initial_price  # P_t
        self.equity = 0.0  # E_t
        self.debt = 0.0  # L_t
        self.owner=None
        self.profit=0
        self.theta=theta

        # Market State
        self.production = 0.0  # Y_t
        self.sales = 0.0  # Q_t
        self.inventory = 0.0  # Delta (Unsold goods)
        self.expected_demand = 0.0  # Y_e
        self.intresses=0

        # Injected Parameters (from YAML)
        self.labour_prod = labour_prod  # w
        self.tau = dividend_ratio  # tau
        self.rho = quantity_adj_param  # rho
        self.eta_max = price_adj_max  # eta (upper bound)
        self.loans=[]
        self.labour_demand = 0.0
        self.staff = []
        self.first_step=True

    def dividends(self):

        self.profit = self.sales * self.price - self.intresses

        if self.profit > 0:
            return self.profit * self.tau
        else:
            return 0

    def payout_dividents(self):
        divs=self.dividends()
        self.liquidity -= divs
        self.owner.wealth += divs


    def hire(self, worker):
        """Hires a worker and updates labor demand."""
        self.labour_demand -= 1
        self.staff.append(worker)
        worker.employed = True
        worker.employer = self


    def get_adjustment_shock(self):
        """Returns a random price adjustment factor U(0, 0.1)."""
        return random.uniform(0, 0.1)

    def receive_loan(self, amount, rate):
        """Updates debt and liquidity upon receiving a loan."""
        self.loans.append(loan(amount, rate))
        self.debt += amount
        self.liquidity += amount

    def pay_intress(self, bank):
        for l in self.loans:
            amount=l.rate * l.amount
            bank.intresses=amount
            self.liquidity -= amount

    def repay_loan(self):
        self.intresses=0
        for l in self.loans:
            amount=self.theta * l.amount
            l.amount -= amount
            self.liquidity -= amount
            #self.intresses+=amount  # those are not intresses CHANGE THIS LATER
            self.debt -= amount

    def fire_workers(self, amount):

        amount=min(amount, len(self.staff))  # just in case
        #choose amount out of staff
        to_fire= set(random.sample(self.staff, amount))
        for w in to_fire:
            w.employed=False
            w.employer=None

        self.staff = [obj for obj in self.staff if obj not in to_fire]

    def get_loans(self):
        total_loans = 0
        for l in self.loans:
            total_loans += l.amount
        return total_loans

    def calculate_leverage(self, gap):
        """Calculates leverage ratio lambda = L + F / (E + L + F)
            L - Debt
            E - Equity
            F - New Financing Needed
        """
        denominator = self.equity + self.debt + gap
        if denominator <= 0:
            return 0.9999  # in theory this should not happen since equity negative triggers bankruptcy before

        leverage =  (self.debt + self.debt) / denominator
        return min(leverage, 0.9999)

    def process_bankruptcy(self):
        self.loans=[]
        self.owner.wealth -= self.equity
        self.liquidity -= self.equity
        self.equity = 0

class ConsumptionFirm(BaseFirm):
    """
    C-Firm: Produces consumption goods using Labor and Capital.
    """

    def __init__(self, firm_id, initial_capital, initial_price, initial_liquidity,
                 # Base Params
                 labour_prod, dividend_ratio, theta, quantity_adj_param, price_adj_max,
                 # C-Firm Specific Params
                 capital_productivity, capital_depreciation, investment_prob,
                 investment_memory, desired_utilization, search_count):

        super().__init__(firm_id, initial_liquidity, initial_price,
                         labour_prod, dividend_ratio, theta, quantity_adj_param, price_adj_max)

        self.capital = initial_capital  # K_t
        self.capital_avg = initial_capital  # Moving average of K
        self.invested=0

        self.uuid = str(uuid.uuid4())
        self.theta=theta

        self.labour_prod=labour_prod
        self.search_count = search_count

        # Injected Parameters (from YAML)
        self.kappa = capital_productivity
        self.delta = capital_depreciation
        self.gamma = investment_prob
        self.nu = investment_memory
        self.omega = desired_utilization
        self.old_loans=0

        # Temporary State for the Step
        self.planned_production = 0.0
        self.planned_investment = 0.0
        self.wage_bill = 0.0
        self.investment_cost = 0.0
        self.capital_book=self.capital * 1.2

    def adjust_price_and_output(self, market_avg_price):
        """
        Adaptive rule for Price (P) and Desired Output (Y*).
        """
        eta = self.get_adjustment_shock()

        # 1. Price Decision
        if self.inventory > 0 and self.price > market_avg_price:
            self.price *= (1 - eta)
        elif self.inventory <= 0 and self.price <= market_avg_price:
            self.price *= (1 + eta)

        # 2. Quantity Decision (Desired Production)
        # Y*_t+1 = Y_t + rho * (Demand - Y_t)
        if self.inventory > 0 and self.price < market_avg_price:
            # Excess Supply: Cut production
            self.planned_production = self.production - self.rho * self.inventory
        elif self.inventory <= 0 and self.price > market_avg_price:
            # Excess Demand: Increase production
            self.planned_production = self.production

        if self.first_step:
            self.planned_production= self.initial_production
            self.first_step = False
        self.expected_demand = self.planned_production

    def calculate_labor_demand(self):
        """Calculates labor demand based on planned production and capital."""
        # Assuming a Leontief production function: Y = min(alfa * N, k * K)

        if self.kappa * self.capital >= self.planned_production:
            self.omega=self.planned_production / (self.kappa * self.desired_capital)
            self.omega = min(self.omega, 1.0)

            desired_laboour = self.omega * self.desired_capital *  self.kappa/self.labour_prod
            current_labour = len(self.staff)
            self.labour_demand = desired_laboour - current_labour

        else:
            desired_laboour = min(self.planned_production/self.labour_prod, self.desired_capital * self.kappa/self.labour_prod)
            current_labour = len(self.staff)
            self.labour_demand = desired_laboour - current_labour

        # fire if too many workers.
        # The paper does not specify whether the fired worker can seek employment in the same period...
        if self.labour_demand  < 0 :
            to_fire=int(abs(self.labour_demand))
            self.labour_demand = 0
            self.fire_workers(to_fire)

    def plan_invest(self):
        """
        Calculates Desired Capital and Investment.
        """
        # 1. Update memory of utilized capital (K_avg)
        required_k_last = self.production / self.kappa
        self.capital_avg = self.nu * self.capital_avg + (1 - self.nu) * required_k_last

        """
        # 2. Check if firm is allowed to invest this period CURRENTLY THE ENGINE DECIDES WHICH FIRMS INVEST WHEN
        if random.random() > self.gamma:
            self.planned_investment = 0
            return
        """

        # 3. Calculate Investment
        replacement = (self.delta * self.capital_avg) / self.gamma
        self.desired_capital = self.capital_avg / self.omega
        total_inv = self.desired_capital + replacement - self.capital

        # self.planned_investment = total_inv    # if disinvestment is allowed
        self.planned_investment = max(0, total_inv)

    def get_financing_gap(self, k_goods_price):
        """
        Calculates need for external funds.
        """
        max_possible_prod = self.capital * self.kappa
        target_prod = min(self.planned_production, max_possible_prod)

        # Approximating labor required (assuming alpha normalized or handled externally)
        labor_required = math.ceil(target_prod)

        self.wage_bill = labor_required * self.wage
        self.investment_cost = self.planned_investment * k_goods_price

        total_needs = self.wage_bill + self.investment_cost
        return max(0, total_needs - self.liquidity)

    def shop(self, k_firms):

        """
            Visits Zk randomly selected K-firms to purchase capital goods.
        """

        # 1. Search: Select Zk random firms
        # "visits Zk randomly selected firms"
        potential_sellers = random.sample(k_firms, k=self.search_count)

        # 2. Rank: Sort by price ascending
        # "ranks them in ascending order of posted price"
        potential_sellers.sort(key=lambda f: f.price)

        costs=0
        to_buy = self.planned_investment

        # 3. Buy: Try to fulfill demand starting from cheapest
        for firm in potential_sellers:
            if to_buy <= 0:
                break

            # Firm checks inventory and sells what it can
            actual_qty = firm.sell(to_buy)
            cost = actual_qty * firm.price

            to_buy -= actual_qty
            costs += cost    # in theory here can be implemented FIFO, LIFO, avg cost methods but i will just recalc the book value somewhere else with avg price on the market

        self.capital += self.planned_investment - to_buy
        self.liquidity -= costs
        self.invested=costs


    def produce(self):
        """Executes production limited by capital capacity."""
        self.production = min(self.capital * self.kappa, self.labour_prod * len(self.staff) )
        self.inventory = self.production   # Notice that if there was any inventory before it is gone now

    def sell(self, amount):
        """Handles sales to households and updates inventory."""
        actual_sold = min(amount, self.inventory)
        if actual_sold < 0:
            pass
        self.sales += actual_sold
        self.inventory -= actual_sold
        self.liquidity += actual_sold * self.price
        return actual_sold

    def depreciated_capital_update(self):
        """Updates capital stock: K_t+1 = (1 - delta*util)K + I """
        utilization = self.production / (self.capital * self.kappa) if self.capital > 0 else 0
        self.capital = (1 - self.delta * utilization) * self.capital + self.planned_investment

    def update_equity(self, k_price):
        self.equity = k_price * self.capital + self.liquidity - self.get_loans()

        return self.equity

    def depreciate_capital(self):
        # for some reason in consumptions firms only utiliized capital is depreciated but in K firms inventory is depreciated fully
        utilized_cap= self.production / (self.capital * self.kappa ) * self.capital
        self.capital -= utilized_cap * self.delta

    def recalculate_book_capital(self, c_price):
        self.capital_book = c_price * self.capital

    def check_bankruptcy(self):
        #revenue=self.sales * self.price
        #new_loans= self.get_loans()-self.old_loans  - old stuff
        #costs=self.intresses

        K_book = self.capital_book
        debt = self.get_loans()
        self.equity = K_book + self.liquidity - debt
        return self.equity <= 0


class CapitalFirm(BaseFirm):
    """
    K-Firm: Produces capital goods using only Labor.
    """

    def __init__(self, firm_id, initial_price, initial_liquidity,
                 wage_rate, dividend_ratio, theta, delta, quantity_adj_param, price_adj_max, labor_productivity):

        super().__init__(firm_id, initial_liquidity, initial_price,
                         wage_rate, dividend_ratio, theta, delta, quantity_adj_param)

        # Injected Parameter
        self.alpha = labor_productivity  # alpha
        self.uuid = str(uuid.uuid4())
        self.theta=theta
        self.delta=delta

    def adjust_price_and_output(self, market_avg_price):
        """
        Adaptive logic for K-market.
        """
        eta = self.get_adjustment_shock()

        if self.inventory > 0 and self.price > market_avg_price:
            self.price *= (1 - eta)
        elif self.inventory <= 0 and self.price <= market_avg_price:
            self.price *= (1 + eta)

        # Quantity Adjustment
        if self.inventory > 0:
            self.planned_production = max(0, self.production - self.rho * self.inventory)
        else:
            self.planned_production = self.production + self.rho * abs(self.inventory)

        if self.first_step:
            self.planned_production= self.initial_production
            self.first_step = False

        self.planned_production = max(self.planned_production, 1.0)

    def calculate_labor_demand(self):

        desired_labour = self.planned_production/self.labour_prod
        current_labour=len(self.staff)
        self.labour_demand = desired_labour - current_labour

        if self.labour_demand  < 0 :
            to_fire=int(abs(self.labour_demand))
            # Paper does not specify what happens in situations where desired labour is say 0.5 or -0.8...
            self.labour_demand = 0
            self.fire_workers(to_fire)


    def get_financing_gap(self, k_goods_price):
        """K-Firms only borrow for working capital (wages)."""
        labor_required = self.planned_production / self.alpha
        self.wage_bill = math.ceil(labor_required) * self.wage

        return max(0, self.wage_bill - self.liquidity)

    def produce(self):
        """Production function Y = alpha * N."""

        N=len(self.staff)
        self.production = self.alpha * N
        # K-firms accumulate inventory (unsold machines)
        self.inventory += self.production

    def sell(self, amount):
        """Handles sales to C-Firms."""
        actual_sold = min(amount, self.inventory)
        self.sales += actual_sold
        self.inventory -= actual_sold
        self.liquidity += actual_sold * self.price
        return actual_sold

    def depreciate_capital(self):
        # Paper mentions that capital in K firms inventory depreciates faster but doesnt give any specific number of anything at all
        # delta for k firms can be changed in configs if needed
        self.inventory -= self.inventory * self.delta

    def check_bankruptcy(self):

        debt = self.get_loans()
        self.equity =  self.liquidity - debt
        return self.equity <= 0

    def update_equity(self, k_price):
        self.equity = k_price * self.inventory + self.liquidity - self.get_loans()

        return self.equity


class loan:
    def __init__(self, amount, rate):
        self.amount = amount
        self.rate = rate


if __name__=="__main__":
    pass