# Code Review Feedback — March 17, 2026

**Reviewer:** Nicolas Reigl
**Author:** Igor Mohhov
**Repo state:** commit `2fee81a` ("something is brewing but is it any good?")

---

## 1. Overall Assessment

Significant progress since the Feb 25 review. You have fixed several critical bugs (employment status, leverage ratio, underproduction), added MySQL persistence infrastructure, and restructured bankruptcy handling into a deferred queue. The codebase is substantially more mature. That said, a number of issues remain before the model can replicate the Assenza et al. (2015) dynamics. Below I prioritize them from most to least critical.

---

## 2. Bugs Fixed Since Last Review (acknowledged)

| Issue | Status |
|-------|--------|
| Worker employment status not toggled | Fixed (`f04a2ea`) |
| Leverage ratio `lambda` miscalculated | Fixed (`17cb4ac`) |
| Underproduction bug (capital capacity constraint) | Fixed (`c0b19ff`) |
| Human wealth now recalculated each period | Fixed — `recalculate_human_wealth()` called in accounting |
| Dividend formula now includes wage bill, depreciation, capital appreciation | Fixed — `firms.py:59` |
| Bankruptcy queue (deferred processing) | Good architectural choice — `to_process_bankruptcies` in `engine.py:350-351` |
| MySQL data persistence | Professional-grade infrastructure — enables systematic debugging |
| `requirements.txt` added | Fixed (`eb4b20f`) |

Well done on all of these.

---

## 3. Remaining Critical Issues

### 3.1 Bank Insolvency — No Safety Net (Priority 1)

**The problem:** When bank equity goes negative, the bank continues to operate — issuing credit, calculating interest rates, paying dividends. There is no check, no recapitalization, and no bailout mechanism.

**Where in the code:**

- `engine.py:353` — `bank.equity += -bank.losses` can push equity negative
- `engine.py:520` — `bank.equity += bank.intresses - divs` does not check for solvency
- `bank.py:131` — `get_credit_limit()` uses `self.equity` in the numerator, so negative equity means *negative* credit limits (which `max(0, ...)` catches), effectively freezing the credit market

**Why it matters:** Once the bank is insolvent, no new loans are issued, firms cannot finance production, employment collapses, and the model enters a death spiral. This is likely the core of the problem you identified.

**What the paper says:** Assenza et al. (2015) are somewhat vague on this. Section 8.3 discusses the bank's balance sheet but assumes solvency is maintained through the interest rate mechanism. In practice, ABM implementations typically add one of:

1. **Government bailout** — if `bank.equity < 0`, inject public funds (effectively a helicopter drop)
2. **Minimum equity floor** — `bank.equity = max(bank.equity, E_min)` with `E_min` calibrated
3. **Lender of last resort** — central bank provides emergency liquidity at a penalty rate

**Recommendation:** Implement option (1) as a simple `if bank.equity <= 0: bank.equity = initial_equity * 0.5` at `engine.py:353`. This is a modelling assumption you should document and discuss in the thesis. It keeps the simulation running while you debug the *reason* the bank goes insolvent (which is likely issues 3.2–3.5 below).

### 3.2 Default Bankruptcy Probability = 0.5 Is Too Conservative (Priority 2)

**Where:** `bank.py:34-38` — initial coefficients `c_model_coefficient = 12`, `c_model_intercept = -2.5`

**The problem:** Before the logistic model has enough data (< 50 observations), the bank uses hardcoded coefficients. With `coefficient = 12` and `intercept = -2.5`:

- At leverage λ = 0.3: φ = 1/(1+exp(-(12×0.3 - 2.5))) = 1/(1+exp(-1.1)) ≈ 0.75
- At leverage λ = 0.2: φ ≈ 0.62

These are *extremely* high bankruptcy probabilities. For comparison, real-world annual corporate default rates are 1–5%. Even in a stressed ABM, 10–20% would be aggressive.

**Effect:** High φ → short expected survival T → high interest rates → tight credit limits → firms cannot borrow → no production → no income → more bankruptcies. This is a self-fulfilling credit crunch.

**Recommendation:** Start with `coefficient = 3`, `intercept = -4`. This gives φ ≈ 0.12 at λ = 0.3 and φ ≈ 0.05 at λ = 0.2 — much more reasonable starting values. Let the logistic regression update these as data accumulates.

### 3.3 Interest Rate Formula — Verify Against Paper Eq. 8.9–8.10 (Priority 2)

**Where:** `bank.py:120-122`

```python
xi_T = (1 - (1 - self.theta) ** (expected_T + 1)) / self.theta
r = self.mu * ((1 + self.r / self.theta) / xi_T) - self.theta
```

**Concern:** The formula structure looks approximately right, but I want to verify the parentheses against the paper's equation 8.9:

$$r_{i,t} = \mu \cdot \frac{1 + r}{\Xi(T)} - \theta$$

where $\Xi(T) = \sum_{s=0}^{T} (1-\theta)^s = \frac{1 - (1-\theta)^{T+1}}{\theta}$

In your code: `(1 + self.r / self.theta)` — is the division by `theta` correct? The paper has $(1+r)$, not $(1 + r/\theta)$. **Check this carefully.** If this is wrong, the interest rate will be systematically too high (since $r/\theta = 0.01/0.05 = 0.2$ vs. $r = 0.01$), which compounds the credit crunch from issue 3.2.

### 3.4 Credit Limit Cap at 10% of Bank Equity — Not in Paper (Priority 3)

**Where:** `bank.py:131`

```python
available_credit = min(available_credit, self.equity * 0.1)
```

**Problem:** This is not in Assenza et al. (2015). The paper's credit rationing (Eq. 8.12) is purely based on the `zeta * E_b - phi * L_i` formula. Adding a hard 10% cap creates an additional binding constraint that is not part of the theoretical model.

**Effect:** With 250 firms potentially needing credit each period, the bank can only extend 10% of equity per firm. If equity = 3000, that's max 300 per firm — which may be fine initially but becomes binding as the bank's equity erodes.

**Recommendation:** Remove this cap unless you have a specific justification. If you need it for stability, document why and consider making the percentage a config parameter.

### 3.5 Capital Stock Not Included in Equity (Priority 3)

**Where:** `firms.py:316` and `firms.py:424`

```python
# Commented out: self.equity = k_price * self.capital + self.liquidity - self.get_loans()
self.equity = self.liquidity - self.get_loans()
```

**Problem:** Both C-firms and K-firms calculate equity as `liquidity - debt`, ignoring the value of capital stock (machines for C-firms, inventory for K-firms). This means equity is systematically understated, which:

1. Triggers premature bankruptcies (equity < 0 when the firm actually has positive net worth)
2. Inflates leverage ratios (denominator is too small)
3. Makes the bank overestimate default risk

**In the paper:** Firm equity includes the book value of capital. Equation 8.2 defines net worth as A = K + D - L (capital + deposits - liabilities).

**Recommendation:** Uncomment the capital-inclusive equity formula. If this was commented out to fix a different bug, we should discuss what went wrong.

---

## 4. The Bank Insolvency Problem — Economic Analysis

You mentioned suspecting this is a "design flaw in the original paper." Let me offer my analysis:

**It is not a flaw in the paper — it is an adverse selection spiral caused by the current calibration.** Here is the causal chain:

1. Default coefficients are too aggressive (3.2) → bankruptcy probabilities too high
2. Interest rates are too high (possibly compounded by 3.3) → firms pay more in interest
3. Credit limits too tight (3.4 makes it worse) → firms cannot finance production
4. Equity understated (3.5) → premature bankruptcies
5. Bankruptcies → bank absorbs losses → bank equity falls
6. Lower bank equity → even tighter credit limits → goto 3

**The fix is not one thing — it is addressing 3.2–3.5 together.** Start with the initial bankruptcy probability (3.2) and the interest rate formula (3.3). These have the largest impact.

**Re: the Assenza et al. paper:** The authors themselves note (Section 8.4) that the model can produce credit crunches and financial fragility. But in their calibration, these are *cyclical* — the economy recovers because:

- Surviving firms eventually repay loans → bank equity rebuilds
- Lower leverage after defaults → lower bankruptcy probabilities → looser credit
- This creates the endogenous business cycle that is the paper's main contribution

Your model is not reaching the "recovery" phase because the initial conditions are too tight. Fix the starting calibration and the cycle should emerge.

---

## 5. Minor Issues

### 5.1 Typos

- `intresses` → `interests` (throughout `bank.py`, `engine.py`, `firms.py`)
- `conenction` → `connection` (in commit message, but also check code)
- `recalulate_human_wealth` → `recalculate_human_wealth` (`household.py:70`)
- `capital_apreciation` → `capital_appreciation` (`firms.py:32`)

### 5.2 Dead Code

- `household.py:76-77` and `80-81` — `if self.human_wealth <= 0.0000001: pass` — these do nothing, remove them
- `household.py:84-100` — `recapitalize_firm()` is never called from the engine; the bankruptcy queue system superseded this
- `firms.py:324-331` — `check_bankruptcy()` computes `K_book` and `debt` as local variables but never uses them (only uses `self.equity`)

### 5.3 Magic Numbers

- `bank.py:131` — `0.1` (10% credit cap) — should be in config.yaml
- `bank.py:137` — `0.2` (bank dividend ratio) — should be in config.yaml (currently only firm tau = 0.2 is there)
- `firms.py:209` — `0.03` minimum utilization — should be in config.yaml
- `bank.py:117` — `0.01` minimum phi — should be in config.yaml

### 5.4 Model runs only 600 periods

- `main.py:23` — `rm.run_steps(run, 600)`. The paper uses 3500 periods with 500 transient. Consider extending once the model stabilizes.

### 5.5 K-firm history only added on bankruptcy

- `engine.py:555-556` — for K-firms, non-bankrupt firms are *always* added to `history_for_bank` (no `if f.debt > 0` check like C-firms at line 539). This means K-firm history includes firms with zero debt, which dilutes the logistic regression signal. Add the `if f.debt > 0` guard to match C-firms.

---

## 6. Suggested Next Steps (in priority order)

1. **Fix interest rate formula** (3.3) — verify against paper equation 8.9, especially the `r/theta` term
2. **Adjust initial logistic coefficients** (3.2) — use `coefficient=3, intercept=-4` as starting point
3. **Uncomment capital in equity** (3.5) — this will reduce premature bankruptcies
4. **Remove 10% credit cap** (3.4) — or justify it
5. **Add bank bailout mechanism** (3.1) — simple equity floor for now
6. **Run for 1000+ periods** and check if endogenous cycles emerge
7. **Compare moments** to Table 3 targets (GDP std dev ≈ 1.66%, autocorrelation ≈ 0.85)

Once steps 1–5 are in place, the adverse selection spiral should break and you should start seeing the cyclical dynamics the paper describes.

---

*Next meeting: discuss bank solvency mechanism and interest rate formula derivation.*
