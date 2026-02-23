import pandas as pd
import numpy as np
import statsmodels.api as sm
import matplotlib.pyplot as plt


def test_gdp_hpfilter(lmbda=1600, export=False):
    start_date = "1947-01-01"

    end_date = "2013-10-01"

    # Load GDP data
    df = pd.read_csv('GDPC1.csv', index_col='observation_date', parse_dates=True)

    # Select data from 1947 to 2013
    sample=df.loc[start_date:end_date].copy()

    # take log
    sample = np.log(sample['GDPC1']) * 100

    # Apply HP Filter
    cycle, trend = sm.tsa.filters.hpfilter(sample, lamb=lmbda)

    # Calculate statistics
    std_dev = cycle.std()
    autocorr = cycle.autocorr(lag=1)

    if export:
        export_df = pd.DataFrame(index=sample.index)
        export_df['GDP'] = sample
        export_df['Trend'] = trend
        export_df['Cycle'] = cycle
        export_df.to_csv(f'gdp_hpfilter_lambda_{lmbda}.csv')

    return std_dev, autocorr
"""

THE PAPER DOESNT MENTION WHICH LAMBDA THEY USED FOR THE HP FILTER. SO I TEST A RANGE OF LAMBDAS AND PLOT THE STD DEV OF THE CYCLE COMPONENT.
MAYBE ITS THE SOFTWARE BUT LAMBDA=1673.81 GIVES THE TARGET STD DEV OF 1.6613. WHY NOT 1600? IS IT JUST ROUNDING ERROR OR SOMETHING?

SAME PROCEDURE FOR AUTOCORRELATION. LAMBDA=1519.55 GIVES THE TARGET AUTOCORRELATION OF 0.8485. WHY NOT 1600? WHY NOT THE SAME AS FOR STD DEV?

MY CURRENT GUESS IS THAT FRED HAS UPDATED THE DATA SLIGHTLY AND THATS WHY THE RESULTS ARE A BIT OFF.
NOT A LOT OFF THOUGH.


target_std = 1.6613
target_autocorr = 0.8485
testlen=3000
lambdas =[]
std_devs = []
autocorrs=[]

for i in range(10, testlen, 10):
    lambdas.append(i)
    res=test_gdp_hpfilter(lmbda=i)
    std_devs.append(res[0])
    autocorrs.append(res[1])

plt.figure(figsize=(10, 6))

# Plot Lambda vs Std Dev
#plt.plot(lambdas, std_devs, label='Calculated Std Dev', color='blue', linewidth=2)
plt.plot(lambdas, autocorrs, label='Calculated Autocorr', color='blue', linewidth=2)

# Add a horizontal line for the Target (1.6613)
#plt.axhline(y=target_std, color='red', linestyle='--', label=f'Target Std Dev ({target_std})')
plt.axhline(y=target_autocorr, color='red', linestyle='--', label=f'Target Autocorr ({target_std})')

# Mark the standard lambda = 1600
plt.axvline(x=1600, color='green', alpha=0.5, label='Standard Quarterly Lambda (1600)')

#plt.title('HP Filter Sensitivity: Lambda ($\lambda$) vs. Standard Deviation of Cycle')
plt.title('HP Filter Sensitivity: Lambda ($\lambda$) vs. Autocorrelation of Cycle')
plt.xlabel('Lambda ($\lambda$) Value')
plt.ylabel('Autocorrelation')
plt.legend()
plt.grid(True, alpha=0.3)

#plt.savefig('lambda_sensitivity_plot.png')
plt.show()
"""

EXPORT=True
lbda=1519.55   #1673.81 - STD DEV   #1519.55 - AUTOCORR
std_dev, autocorr = test_gdp_hpfilter(lmbda=lbda, export=EXPORT)
print(f"Using lambda = {lbda}:")
print(f"Standard Deviation of Cycle: {std_dev:.4f}%")
print(f"Autocorrelation of Cycle (lag 1): {autocorr:.4f}")


if __name__ == "__main__":
    pass