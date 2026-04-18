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
            charset='utf8mb4'

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


def get_bank_data(db_config):
    query = """
    SELECT s.run_id, s.step_no, c.equity, c.intresses, c.losses
        FROM steps s LEFT JOIN bank_data c on s.step_id = c.step_id
    """
    return execute_query(db_config, query)

data=get_bank_data(db_creds)

column_names = ['run_id', 'step_no', 'equity', 'intresses', 'losses']
df = pd.DataFrame(data, columns=column_names)

stats = df.groupby('step_no')['equity'].agg([
    'mean',
    'std',
    lambda x: np.percentile(x, 2.5),
    lambda x: np.percentile(x, 97.5)
]).rename(columns={'<lambda_0>': 'p2_5', '<lambda_1>': 'p97_5'})


stats['sigma_up'] = stats['mean'] + stats['std']
stats['sigma_down'] = stats['mean'] - stats['std']

# 3. Create the plot
plt.figure(figsize=(10, 6))

# Plot the Average (Mean)
plt.plot(stats.index, stats['mean'], color='blue', label='Average Equity', linewidth=2)

# Fill the 1-sigma area (approx 68% of data)
plt.fill_between(stats.index, stats['sigma_down'], stats['sigma_up'],
                 color='blue', alpha=0.2, label=r'$1\sigma$ (68% Range)')

# Plot the 95% lines (Percentile based)
plt.plot(stats.index, stats['p2_5'], color='red', linestyle='--', alpha=0.7, label='95% Bounds (2.5/97.5th)')
plt.plot(stats.index, stats['p97_5'], color='red', linestyle='--', alpha=0.7)

# Formatting
#plt.title('Equity Evolution per Step with Confidence Intervals')
plt.xlabel('Step Number')
plt.ylabel('Bank Equity')
plt.legend(loc='upper left')
plt.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout()

plt.show()



