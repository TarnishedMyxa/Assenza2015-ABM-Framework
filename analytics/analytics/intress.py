import pymysql
import pandas as pd
from functools import reduce
import os
from dotenv import load_dotenv
import csv
import matplotlib.pyplot as plt
import numpy as np

load_dotenv()
db_creds = {
    'host': os.getenv("host"),
    'port': int(os.getenv("port")),
    'user': os.getenv("user"),
    'password': os.getenv("password"),
    'database': os.getenv("database")
}

def execute_query(db_config, query):
    try:
        connection = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            charset='utf8mb4',
            connect_timeout=600,  # Wait longer to connect
            read_timeout=600,  # Wait up to 10 minutes for data

        )

        with connection.cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchall()
            return result

    except pymysql.MySQLError as e:
        print(f"Error while connecting to MySQL: {e}")  # Debug
        raise
    finally:
        if connection:
            connection.close()
            print("MySQL connection closed")

def get_debts(db_config):
    # 1. Get a map of step_id -> (run_id, step_no)
    # This is a much smaller query
    mapping_query = "SELECT step_id, run_id, step_no FROM steps"
    mapping = pd.DataFrame(execute_query(db_config, mapping_query),
                          columns=['step_id', 'run_id', 'step_no'])

    # 2. Get sums directly from the firm tables
    # No JOIN here = Much faster query
    cf_query = "SELECT step_id, SUM(debt) as cf_d FROM c_firms_data GROUP BY step_id"
    cf_m = pd.DataFrame(execute_query(db_config, cf_query), columns=['step_id', 'cf_d'])

    kf_query = "SELECT step_id, SUM(debt) as kf_d FROM kf_firms_data GROUP BY step_id"
    kf_m = pd.DataFrame(execute_query(db_config, kf_query), columns=['step_id', 'kf_d'])

    # 3. Merge in Pandas (which is very fast)
    final_cf = pd.merge(mapping, cf_m, on='step_id', how='left')
    final_kf = pd.merge(mapping, kf_m, on='step_id', how='left')

    return final_cf, final_kf

def get_bank_data(db_config):
    query = """
    SELECT s.run_id, s.step_no, c.intresses, c.losses
        FROM steps s LEFT JOIN bank_data c on s.step_id = c.step_id
    """
    return execute_query(db_config, query)

# 1. Retrieve the data
bank_raw = get_bank_data(db_creds)


cf_debt_raw, kf_debt_raw = get_debts(db_creds) # Assuming get_debts returns both

# 2. Convert to DataFrames
df_bank = pd.DataFrame(bank_raw, columns=['run_id', 'step_no', 'intresses', 'losses'])
df_cf = pd.DataFrame(cf_debt_raw, columns=['run_id', 'step_no', 'cf_d'])
df_kf = pd.DataFrame(kf_debt_raw, columns=['run_id', 'step_no', 'kf_d'])

# 3. Merge data on run_id and step_no
df = pd.merge(df_bank, df_cf, on=['run_id', 'step_no'], how='left')
df = pd.merge(df, df_kf, on=['run_id', 'step_no'], how='left')

# Fill NaN values with 0 in case some steps have no debt data
df[['cf_d', 'kf_d']] = df[['cf_d', 'kf_d']].fillna(0)

# 4. Calculate the average interest rate per run/step
# Note: total_interest / (debt_c + debt_k)
df['total_debt'] = df['cf_d'] + df['kf_d']

# Use np.where to avoid division by zero errors
df['interest_rate'] = np.where(df['total_debt'] > 0,
                               df['intresses'] / df['total_debt'],
                               0)

# 5. Aggregate stats by step_no
stats = df.groupby('step_no')['interest_rate'].agg([
    'mean',
    'std',
    lambda x: np.percentile(x, 2.5),
    lambda x: np.percentile(x, 97.5)
]).rename(columns={'<lambda_0>': 'p2_5', '<lambda_1>': 'p97_5'})

stats['sigma_up'] = stats['mean'] + stats['std']
stats['sigma_down'] = stats['mean'] - stats['std']

# 6. Plotting
plt.figure(figsize=(10, 6))

# Mean line
plt.plot(stats.index, stats['mean'], color='green', label='Mean Interest Rate', linewidth=2)

# 1-sigma area (68%)
plt.fill_between(stats.index, stats['sigma_down'], stats['sigma_up'],
                 color='green', alpha=0.2, label=r'$1\sigma$ (68% Range)')

# 95% lines (2.5th and 97.5th percentiles)
plt.plot(stats.index, stats['p2_5'], color='darkorange', linestyle='--', alpha=0.8, label='95% Bounds')
plt.plot(stats.index, stats['p97_5'], color='darkorange', linestyle='--', alpha=0.8)

# Formatting
#plt.title('Average Interest Rate Evolution per Step')
plt.xlabel('Step Number')
plt.ylabel('Interest Rate (Total Interest / Total Debt)')
plt.legend(loc='upper right')
plt.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout()

plt.show()