import numpy as np
from sklearn.linear_model import LogisticRegression
from collections import deque
import math
from itertools import chain


class Bank:
    def __init__(self, initial_equity, r_policy=0.01, markup=1.1,
                 zeta=0.002, theta=0.05, window_c=1000, window_k=1000,
                 dividend_ratio=0.2):
        """
        r_policy: The risk-free rate 'r' (instrument of monetary policy)
        markup: 'mu' (arbitrage multiplier > 1)
        zeta: 'loss_parameter' (used for credit limits)
        theta: 'installment_rate' (loan repayment share)
        """
        self.equity = initial_equity
        self.r = r_policy  # Policy rate
        self.mu = markup  # µ
        self.zeta = zeta  # ζ
        self.theta = theta  # θ
        self.tau = dividend_ratio
        self.reserves=0

        # Rolling windows for C and K firms (datasets for T-hat periods)
        self.c_history = deque(maxlen=window_c)
        self.k_history = deque(maxlen=window_k)
        self.intresses=0
        self.losses=0
        self.divs=0

        self.c_model = None
        self.k_model = None

        self.c_model_coefficient = 3
        self.c_model_intercept = -4

        self.k_model_coefficient = 3
        self.k_model_intercept = -4

    def estimate_logistic_failure_prob(self):
        """
        Estimates the logistic relationship phi = f(lambda).
        Re-estimated each period by discarding the oldest and incorporating the newest.
            History is in shape: [[(lambda, bankruptcy),(lambda, bankruptcy),(lambda, bankruptcy)], [], ...]
            List of last N periods of data as lists of tuple with labda value and bankruptcy boolean.

        """
        if self.k_model is None:
            self.k_model = LogisticRegression(solver='lbfgs', warm_start=True, max_iter=100)
        if self.c_model is None:
            self.c_model = LogisticRegression(solver='lbfgs', warm_start=True, max_iter=100)

        def update_and_fit(model, history, firm_type):
            if not history or len(history) < 50:
                return

            data = np.array(history)

            X = data[:, 0].reshape(-1, 1)
            y = data[:, 1]

            y_min, y_max = y.min(), y.max()
            if y_min != y_max:
                model.fit(X, y)

                coef = model.coef_[0][0]
                intercept = model.intercept_[0]

                if firm_type == 'K':
                    self.k_model_coefficient = coef
                    self.k_model_intercept = intercept
                else:
                    self.c_model_coefficient = coef
                    self.c_model_intercept = intercept

        update_and_fit(self.k_model, self.k_history, 'K')
        update_and_fit(self.c_model, self.c_history, 'C')


    def get_bankruptcy_prob(self, leverage, firm_type='C'):
        """Retrieves phi_i,t = f(lambda_i,t)"""
        model = self.c_model if firm_type == 'C' else self.k_model

        if model is None:
            if self.c_model_coefficient is None or self.c_model_intercept is None:
                return 0.5  # Default  risk before C model is trained
            # Use C model parameters to calculate probability
            z = self.c_model_coefficient * leverage + self.c_model_intercept
            phi = 1 / (1 + np.exp(-z))
            return phi

        if firm_type == 'C':
            if self.c_model_coefficient is None or self.c_model_intercept is None:
                return 0.5  # Default  risk before C model is trained
            # Use C model parameters to calculate probability
            z = self.c_model_coefficient * leverage + self.c_model_intercept
            phi = 1 / (1 + np.exp(-z))
            return phi
        else:
            if self.k_model_coefficient is None or self.k_model_intercept is None:
                return 0.5  # Default risk before K model is trained
            # Use K model parameters to calculate probability
            z = self.k_model_coefficient * leverage + self.k_model_intercept
            phi = 1 / (1 + np.exp(-z))
            return phi

    def set_interest_rate(self, leverage, firm_type='C'):
        """
        Implements Equations 8.4, 8.6, and 8.9.
        1. Calculate survival time T
        2. Calculate sum Xi(T)
        3. Solve for r_i,t using no-arbitrage
        """
        phi = self.get_bankruptcy_prob(leverage, firm_type)

        # Avoid division by zero: T = 1 / phi (Eq 8.4)
        phi = max(phi, 0.01)
        expected_T = 1 / phi

        xi_T = (1 - (1 - self.theta) ** (expected_T + 1)) / self.theta

        r=self.mu *( (1+self.r)/xi_T ) - self.theta

        return max(r, self.r), phi

    def get_credit_limit(self, current_debt, phi):
        """
        Rationing based on Equations 8.12 and bank exposure.
        """
        available_credit = (self.zeta * self.equity - phi * current_debt) / phi
        # Removed 10% cap — not in Assenza et al. (2015)

        return max(0, available_credit)

    def dividends(self):
        net_profit = self.intresses - self.losses
        if net_profit <= 0:
            self.divs = 0.0
            return 0.0

        self.divs = self.tau * net_profit
        return self.divs


if __name__=="__main__":
    pass
