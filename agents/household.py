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
        self.human_wealth = 0.05  # Y*_c (Permanent Income proxy)
        self.spent_amount = 0.0

        # Parameters
        self.xi = memory_param  # ξ (Memory parameter)
        self.chi = cons_propensity  # χ (Consumption propensity)
        self.budget=0

    def determine_budget(self):
        """
        Calculates consumption budget based on permanent income and financial wealth.
        Budget = Y*_c,t + χ * D_c,t
        """
        if self.wealth <=0:
            self.budget=0
            return 0

        self.budget = self.human_wealth + (self.chi * self.wealth)
        self.budget = min(self.budget, self.wealth)
        return max(0, self.budget)


class Worker(Household):
    """
    Supplies labor inelastically. Receives wage w if employed.

    """

    def __init__(self, worker_id, initial_wealth, search_count, **kwargs):
        super().__init__(worker_id, initial_wealth, **kwargs)
        self.employed = False
        self.employer = None
        self.search_count = search_count
        self.wage = 1.0

    def recalculate_human_wealth(self, wage_rate):
        """
        Updates human wealth based on employment status and wage.
        Y*_c,t = ξ * Y*_c,t-1 + (1 - ξ) * w_t * employed
        """
        self.income =wage_rate if self.employed else 0.0
        self.human_wealth = max(0, (self.xi * self.human_wealth) + ((1 - self.xi) * self.income) )

class Capitalist(Household):
    """
    Owns a firm. Receives dividends if the firm is profitable.
    Must recapitalize the firm if it goes bankrupt.

    """

    def __init__(self, capitalist_id, initial_wealth, search_count, owned_firm, **kwargs):
        super().__init__(capitalist_id, initial_wealth, **kwargs)
        self.owned_firm = owned_firm
        self.search_count=search_count
        self.income=0.0

    def recalulate_human_wealth(self):

        """
        Updates human wealth based on dividends from the owned firm.
        Y*_c,t = ξ * Y*_c,t-1 + (1 - ξ) * dividends_t
        """

        self.human_wealth =max(0, (self.xi * self.human_wealth) + ((1 - self.xi) * self.income) )



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