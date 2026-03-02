import random
import uuid

class Household:
    """
    Base class representing a consumer (Worker or Capitalist).
    Shared behavior: Permanent Income calculation and consumption shopping.
    """

    def __init__(self, agent_id, initial_wealth, memory_param=0.96,
                 cons_propensity=0.05):
        self.id = agent_id
        self.wealth = initial_wealth  # D_c (Financial Wealth/Deposits)
        self.human_wealth = 0.0  # Y*_c (Permanent Income proxy)
        self.spent_amount = 0.0

        # Parameters
        self.xi = memory_param  # ξ (Memory parameter)
        self.chi = cons_propensity  # χ (Consumption propensity)


    def determine_budget(self):
        """
        Calculates consumption budget based on permanent income and financial wealth.
        Budget = Y*_c,t + χ * D_c,t
        """
        budget = self.human_wealth + (self.chi * self.wealth)
        return max(0, budget)

    def shop(self, c_firms):
        """
        Visits Zc randomly selected C-firms to purchase consumption goods.

        """
        budget = self.determine_budget()

        # 1. Search: Select Zc random firms
        # "visits Zc randomly selected firms"
        potential_sellers = random.sample(c_firms, k=self.search_count)

        # 2. Rank: Sort by price ascending
        # "ranks them in ascending order of posted price"
        potential_sellers.sort(key=lambda f: f.price)

        remaining_budget = budget
        self.spent_amount = 0.0

        # 3. Buy: Try to fulfill demand starting from cheapest
        for firm in potential_sellers:
            if remaining_budget <= 0:
                break

            # Demand is constrained by budget
            desired_qty = remaining_budget / firm.price

            # Firm checks inventory and sells what it can
            actual_qty = firm.sell(desired_qty)
            cost = actual_qty * firm.price

            remaining_budget -= cost
            self.spent_amount += cost

        if remaining_budget > 0:
            queue_qty=remaining_budget / firm.price
            firm.queue+=queue_qty

        # 4. Update Wealth
        # D_c,t = D_c,t-1 + Y_c,t - C_c,t
        # Any unspent budget becomes involuntary savings
        #self.wealth += remaining_budget


class Worker(Household):
    """
    Supplies labor inelastically. Receives wage w if employed.

    """

    def __init__(self, worker_id, initial_wealth, search_count, **kwargs):
        super().__init__(worker_id, initial_wealth, **kwargs)
        self.uuid = uuid.uuid4()
        self.employed = False
        self.employer = None
        self.search_count = search_count
        self.wage = 1.0

class Capitalist(Household):
    """
    Owns a firm. Receives dividends if the firm is profitable.
    Must recapitalize the firm if it goes bankrupt.

    """

    def __init__(self, capitalist_id, initial_wealth, search_count, owned_firm, **kwargs):
        super().__init__(capitalist_id, initial_wealth, **kwargs)
        self.owned_firm = owned_firm
        self.uuid = uuid.uuid4()
        self.search_count=search_count

    def recapitalize_firm(self):
        """
        If firm equity < 0, the capitalist uses personal wealth to provide equity.

        """
        if self.owned_firm.equity < 0:
            # The paper implies the firm is "replaced", effectively reset.
            # The cost is deducted from the capitalist's wealth.
            # Assuming recapitalization restores equity to a baseline (e.g., initial liquidity)
            recap_cost = abs(self.owned_firm.equity) + 1.0  # Ensure positive equity

            # Deduct from personal wealth
            self.wealth -= recap_cost

            # Reset firm financials handled in Firm class, but triggered here or by engine
            self.owned_firm.reset_bankruptcy(new_equity=1.0)

if __name__=="__main__":
    pass