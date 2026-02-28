import numpy as np
from sklearn.linear_model import LogisticRegression
from collections import deque
import pickle


class Bank:
    def __init__(self, initial_equity, r_policy=0.01, markup=1.1,
                 zeta=0.002, theta=0.05, window_c=1000, window_k=1000):
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

        # Rolling windows for C and K firms (datasets for T-hat periods)
        self.c_history = deque(maxlen=window_c)
        self.k_history = deque(maxlen=window_k)
        self.intresses=0

        self.c_model = None
        self.k_model = None

    def estimate_logistic_failure_prob(self, save, use):
        """
        Estimates the logistic relationship phi = f(lambda).
        Re-estimated each period by discarding the oldest and incorporating the newest.
            History is in shape: [[(lambda, bankruptcy),(lambda, bankruptcy),(lambda, bankruptcy)], [], ...]
            List of last N periods of data as lists of tuple with labda value and bankruptcy boolean.

        """

        if not(self.c_model is None and self.k_model is None):
            return

        if use:
            with open("ModelC.pkl", "rb") as f:
                self.c_model = pickle.load(f)
            with open("ModelK.pkl", "rb") as f:
                self.k_model = pickle.load(f)
            return

        # Fit models for K firms first
        flat_history = [item for sublist in self.k_history for item in sublist]

        data = np.array(flat_history)
        if len(data) >= 20:  # Ensure minimum data points for fit
            X = data[:, 0].reshape(-1, 1)  # Leverage (lambda)
            y = data[:, 1]  # Status (1=Bankrupt, 0=Survived)

            # Check if we have both classes to train
            if len(np.unique(y)) > 1:
                model = LogisticRegression(solver='liblinear')
                model.fit(X, y)
                self.k_model = model
                if save:
                    with open("ModelC.pkl", "wb") as f:
                        pickle.dump(model, f)

        # Fit models for C firms next
        flat_history = [item for sublist in self.c_history for item in sublist]
        data = np.array(flat_history)
        if len(data) >= 20:  # Ensure minimum data points for fit
            X = data[:, 0].reshape(-1, 1)  # Leverage (lambda)
            y = data[:, 1]  # Status (1=Bankrupt, 0=Survived)

            # Check if we have both classes to train
            if len(np.unique(y)) > 1:
                model = LogisticRegression(solver='liblinear')
                model.fit(X, y)
                self.c_model = model
                if save:
                    with open("ModelK.pkl", "wb") as f:
                        pickle.dump(model, f)


    def get_bankruptcy_prob(self, leverage, firm_type='C'):
        """Retrieves phi_i,t = f(lambda_i,t)"""
        model = self.c_model if firm_type == 'C' else self.k_model

        if model is None:
            return 0.04  # Default small risk before models are trained

        # Predict probability of class 1 (Bankruptcy)
        return model.predict_proba([[leverage]])[0][1]

    def set_interest_rate(self, leverage, firm_type='C'):
        """
        Implements Equations 8.4, 8.6, and 8.9.
        1. Calculate survival time T
        2. Calculate sum Xi(T)
        3. Solve for r_i,t using no-arbitrage
        """
        phi = self.get_bankruptcy_prob(leverage, firm_type)

        # Avoid division by zero: T = 1 / phi (Eq 8.4)
        phi = max(phi, 0.000001)
        expected_T = 1 / phi

        xi_T = (1 - (1 - self.theta) ** (expected_T + 1)) / self.theta

        r=self.mu *( (1+self.r/self.theta)/xi_T - self.theta  )  # Eq 8.9, 8.10

        # Cost channel: Ensure rate isn't lower than the policy rate
        return max(r, self.r), phi

    def get_credit_limit(self, current_debt, phi):
        """
        Rationing based on Equations 8.12 and bank exposure.
        F_bar = (zeta * Eb) / phi
        """

        available_credit = self.zeta * self.equity / phi -   current_debt

        return max(0, available_credit)

if __name__=="__main__":
    pass