import pymysql
import pandas as pd
import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import statsmodels.api as sm


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
    SELECT s.run_id, s.step_no, c.equity
        FROM steps s LEFT JOIN bank_data c on s.step_id = c.step_id
    """
    return execute_query(db_config, query)

data = get_bank_data(db_creds)
column_names = ['run_id', 'step_no', 'equity']
df = pd.DataFrame(data, columns=column_names)

unique_runs = df['run_id'].unique()[:10]
df_subset = df[df['run_id'].isin(unique_runs)].copy()

plt.figure(figsize=(12, 8))

lamb_value = 100000

for run_id in unique_runs:

    group = df_subset[df_subset['run_id'] == run_id].sort_values('step_no')


    cycle, trend = sm.tsa.filters.hpfilter(group['equity'], lamb=lamb_value)


    line, = plt.plot(
        group['step_no'],
        group['equity'],
        alpha=0.2,  # Faint background for noise
        linewidth=1,
        label='_nolegend_'
    )


    plt.plot(
        group['step_no'],
        trend,
        color=line.get_color(),  # Matches the raw line color
        alpha=1.0,
        linewidth=2.5,
        #label=f'Run {run_id} Trend'
    )


#plt.title(f'Equity Trends vs. Raw Volatility (HP Filter, $\lambda={lamb_value}$)')
plt.xlabel('Step Number')
plt.ylabel('Bank Equity')
plt.grid(True, linestyle=':', alpha=0.5)


plt.legend(loc='upper left', fontsize='small', ncol=2)
plt.tight_layout()

plt.show()