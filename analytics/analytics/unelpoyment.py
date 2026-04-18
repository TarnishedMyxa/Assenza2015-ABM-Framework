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
            connect_timeout=3600,  # Wait longer to connect
            read_timeout=3600,  # Wait up to 10 minutes for data

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


def get_employment_rate_safe(db_config):
    # 1. Get unique runs
    runs_df = pd.DataFrame(execute_query(db_config, "SELECT DISTINCT run_id FROM steps"), columns=['run_id'])
    all_data = []

    for run in runs_df['run_id']:
        print(f"Processing Run: {run}")
        # Only query one run at a time to keep the load low
        query = f"""
            SELECT s.step_no, SUM(w.employed)/3000 as emp_rate
            FROM steps s 
            JOIN workers_data w ON s.step_id = w.step_id
            WHERE s.run_id = '{run}'
            GROUP BY s.step_no
        """
        # Append results for this run
        run_data = pd.DataFrame(execute_query(db_config, query), columns=['step_no', 'emp_rate'])
        run_data['run_id'] = run
        all_data.append(run_data)

    return pd.concat(all_data)

df = get_employment_rate_safe(db_creds)

df['emp_rate'] = df['emp_rate'].astype(float)
df['step_no'] = df['step_no'].astype(int)

# 2. Calculate Unemployment Rate (1 - Employment Rate)
df['unemployment_rate'] = 1 - df['emp_rate']

# 3. Aggregate statistics by step_no
stats = df.groupby('step_no')['unemployment_rate'].agg([
    'mean',
    'std',
    lambda x: np.percentile(x, 2.5),
    lambda x: np.percentile(x, 97.5)
]).rename(columns={'<lambda_0>': 'p2_5', '<lambda_1>': 'p97_5'})

# Calculate 1-sigma bounds
stats['sigma_up'] = stats['mean'] + stats['std']
stats['sigma_down'] = stats['mean'] - stats['std']

# 4. Plotting
plt.figure(figsize=(10, 6))

# Plot the Mean Unemployment
plt.plot(stats.index, stats['mean'], color='crimson', label='Mean Unemployment Rate', linewidth=2)

# Fill the 1-sigma area (68% of runs)
plt.fill_between(stats.index, stats['sigma_down'], stats['sigma_up'],
                 color='crimson', alpha=0.15, label=r'$1\sigma$ (68% Range)')

# Plot the 95% lines (2.5th and 97.5th percentiles)
plt.plot(stats.index, stats['p2_5'], color='black', linestyle=':', alpha=0.5, label='95% Bounds')
plt.plot(stats.index, stats['p97_5'], color='black', linestyle=':', alpha=0.5)

# Formatting for a professional look
#plt.title('Unemployment Rate Evolution Over Time', fontsize=14)
plt.xlabel('Step Number', fontsize=12)
plt.ylabel('Unemployment Rate (%)', fontsize=12)

# If your data is 0.0 to 1.0, you might want to format the Y axis as percentage
# plt.gca().set_yticklabels(['{:.0f}%'.format(x*100) for x in plt.gca().get_yticks()])

plt.legend(loc='upper right')
plt.grid(True, linestyle='--', alpha=0.4)
plt.tight_layout()

plt.show()