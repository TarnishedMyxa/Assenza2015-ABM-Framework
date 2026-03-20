import numpy as np
from sklearn.linear_model import LogisticRegression
from collections import deque
import math
from itertools import chain


class Bank:
    def __init__(self, initial_equity, r_policy=0.01, markup=1.1,
                 zeta=0.002, theta=0.05, window_c=1000, window_k=1000,
                 dividend_ratio=0.2, credit_limit_mode='current',
                 c_fit_enabled=True, k_fit_enabled=True,
                 c_min_fit_observations=50, k_min_fit_observations=50,
                 c_logit_coefficient=3.0, c_logit_intercept=-4.0,
                 k_logit_coefficient=3.0, k_logit_intercept=-4.0,
                 c_phi_cap=None, k_phi_cap=None):
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
        self.credit_limit_mode = credit_limit_mode
        self.c_fit_enabled = c_fit_enabled
        self.k_fit_enabled = k_fit_enabled
        self.c_min_fit_observations = c_min_fit_observations
        self.k_min_fit_observations = k_min_fit_observations
        self.c_phi_cap = c_phi_cap
        self.k_phi_cap = k_phi_cap
        self.reserves=0

        # Rolling windows for C and K firms (datasets for T-hat periods)
        self.c_history = deque(maxlen=window_c)
        self.k_history = deque(maxlen=window_k)
        self.intresses=0
        self.losses=0
        self.divs=0

        self.c_model = None
        self.k_model = None

        self.c_model_coefficient = c_logit_coefficient
        self.c_model_intercept = c_logit_intercept

        self.k_model_coefficient = k_logit_coefficient
        self.k_model_intercept = k_logit_intercept

    def estimate_logistic_failure_prob(self):
        """
        Estimates the logistic relationship phi = f(lambda).
        Re-estimated each period by discarding the oldest and incorporating the newest.
            History is in shape: [[(lambda, bankruptcy),(lambda, bankruptcy),(lambda, bankruptcy)], [], ...]
            List of last N periods of data as lists of tuple with labda value and bankruptcy boolean.

        """
        if self.k_fit_enabled and self.k_model is None:
            self.k_model = LogisticRegression(solver='lbfgs', warm_start=True, max_iter=100)
        if self.c_fit_enabled and self.c_model is None:
            self.c_model = LogisticRegression(solver='lbfgs', warm_start=True, max_iter=100)

        def update_and_fit(model, history, firm_type):
            fit_enabled = self.k_fit_enabled if firm_type == 'K' else self.c_fit_enabled
            min_fit = self.k_min_fit_observations if firm_type == 'K' else self.c_min_fit_observations
            if not fit_enabled or model is None:
                return
            if not history or len(history) < min_fit:
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
        phi_cap = self.c_phi_cap if firm_type == 'C' else self.k_phi_cap
        coefficient = self.c_model_coefficient if firm_type == 'C' else self.k_model_coefficient
        intercept = self.c_model_intercept if firm_type == 'C' else self.k_model_intercept

        if model is None:
            if coefficient is None or intercept is None:
                return 0.5 if phi_cap is None else min(0.5, phi_cap)  # Default  risk before C model is trained
            z = coefficient * leverage + intercept
            phi = 1 / (1 + np.exp(-z))
            return phi if phi_cap is None else min(phi, phi_cap)

        if firm_type == 'C':
            if self.c_model_coefficient is None or self.c_model_intercept is None:
                return 0.5 if phi_cap is None else min(0.5, phi_cap)  # Default  risk before C model is trained
            # Use C model parameters to calculate probability
            z = self.c_model_coefficient * leverage + self.c_model_intercept
            phi = 1 / (1 + np.exp(-z))
            return phi if phi_cap is None else min(phi, phi_cap)
        else:
            if self.k_model_coefficient is None or self.k_model_intercept is None:
                return 0.5 if phi_cap is None else min(0.5, phi_cap)  # Default risk before K model is trained
            # Use K model parameters to calculate probability
            z = self.k_model_coefficient * leverage + self.k_model_intercept
            phi = 1 / (1 + np.exp(-z))
            return phi if phi_cap is None else min(phi, phi_cap)

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

        r=self.mu *( (1+self.r / self.theta)/xi_T ) - self.theta

        return max(r, self.r), phi

    def get_credit_limit(self, current_debt, phi, requested_gap=None):
        """
        Rationing based on Equations 8.12 and bank exposure.
        """
        phi = max(phi, 1e-8)
        equity = max(self.equity, 0.0)

        if self.credit_limit_mode == 'journal_candidate':
            max_total_debt = (self.zeta * equity) / phi
            available_credit = max_total_debt - current_debt
        else:
            available_credit = (self.zeta * equity - phi * current_debt) / phi

        if requested_gap is not None:
            available_credit = min(available_credit, requested_gap)

        return max(0.0, available_credit)

    def dividends(self):
        net_profit = self.intresses - self.losses
        if net_profit <= 0:
            self.divs = 0.0
            return 0.0

        self.divs = self.tau * net_profit
        return self.divs


if __name__=="__main__":
    pass
