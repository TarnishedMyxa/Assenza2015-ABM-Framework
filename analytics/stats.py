import pymysql
import pandas as pd
from functools import reduce
import numpy as np



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


def get_simply_prices(db_config):
    query = """
        SELECT s.run_id, s.step_no, cf.price
        FROM steps s LEFT JOIN c_firms_data cf on s.step_id = cf.step_id
        WHERE s.run_id = "zgx30YZd3ECh7iZ"
    """
    return execute_query(db_config, query)


def get_firm_data(db_config, firmid, runid):
    query = """
        SELECT s.step_no, cf.*
        FROM steps s LEFT JOIN c_firms_data cf on s.step_id = cf.step_id
        WHERE s.run_id = '""" + str(runid) + """'
        and cf.cf_id = '""" + str(firmid) + """'
    """
    return execute_query(db_config, query)


def get_k_firm_data(db_config, firmid, runid):
    query = """
        SELECT s.step_no, cf.*
        FROM steps s LEFT JOIN kf_firms_data cf on s.step_id = cf.step_id
        WHERE s.run_id = '""" + str(runid) + """'
        and cf.kf_id = '""" + str(firmid) + """'
    """
    return execute_query(db_config, query)


def get_worker_data(db_config, workerid, runid):
    query = """
        SELECT s.step_no, w.*
        FROM steps s LEFT JOIN workers_data w on s.step_id = w.step_id
        WHERE s.run_id = '""" + str(runid) + """'
        and w.worker_id = '""" + str(workerid) + """'
    """
    return execute_query(db_config, query)


def get_capitalist_data(db_config, capitalistid, runid):
    query = """
        SELECT s.step_no, c.*
        FROM steps s LEFT JOIN capitalists_data c on s.step_id = c.steps_id
        WHERE s.run_id = '""" + str(runid) + """'
        and c.capitalist_id = '""" + str(capitalistid) + """'
    """
    return execute_query(db_config, query)


def get_c_price_over_time(db_config):
    query = """
        SELECT s.run_id, s.step_no, SUM(cf.sales) AS total_qty, SUM(cf.sales * cf.price) AS total_sales
        FROM steps s LEFT JOIN c_firms_data cf on s.step_id = cf.step_id
        WHERE s.run_id = "zgx30YZd3ECh7iZ"
        GROUP BY s.run_id, s.step_no
    """
    return execute_query(db_config, query)


def get_unemployment_rate_over_time(db_config, runid):
    query = """
        SELECT s.step_no, SUM(w.employed)/3000 AS employment_rate
        FROM steps s LEFT JOIN workers_data w on s.step_id = w.step_id
        WHERE s.run_id = '""" + str(runid) + """'
        GROUP BY s.step_no

    """
    return execute_query(db_config, query)


def get_bank_data(db_config, runid):
    query = """
    SELECT s.step_no, c.equity, c.k_coef, c.k_intercept, c.c_coef, c.c_intercept, c.intresses, c.losses
        FROM steps s LEFT JOIN bank_data c on s.step_id = c.step_id
        WHERE s.run_id = '""" + str(runid) + """'
    """
    return execute_query(db_config, query)


def get_total_money_amount(db_config, runid):
    # 1. Get the step mapping for this run
    map_query = f"SELECT step_id, step_no, run_id FROM steps WHERE run_id = '{runid}' ORDER BY step_no"
    df_steps = pd.DataFrame(execute_query(db_config, map_query),
                            columns=['step_id', 'step_no', 'run_id'])

    step_ids = df_steps['step_id'].tolist()

    # 2. Define a function to fetch data in small batches
    def fetch_in_chunks(table, sum_cols, step_col='step_id', chunk_size=50):
        all_results = []
        # Split step_ids into small batches of 50
        for i in range(0, len(step_ids), chunk_size):
            batch = tuple(step_ids[i:i + chunk_size])
            print(f"  - Table {table}: Processing steps {i} to {i + chunk_size}...")

            # Format SUM columns
            sum_str = ", ".join([f"SUM({c})" for c in sum_cols])

            query = f"""
                SELECT {step_col}, {sum_str}
                FROM {table}
                WHERE {step_col} IN {batch}
                GROUP BY {step_col}
            """
            batch_data = execute_query(db_config, query)
            all_results.extend(batch_data)

        # Flatten column names for DataFrame
        cols = ['step_id'] + [f"{table}_{c}" for c in sum_cols]
        return pd.DataFrame(all_results, columns=cols)

    # 3. Execute for each table
    print(f"Starting Fail-Safe data retrieval for Run {runid}...")

    df_w = fetch_in_chunks('workers_data', ['wealth'])
    df_c = fetch_in_chunks('capitalists_data', ['wealth'], step_col='steps_id')
    df_cf = fetch_in_chunks('c_firms_data', ['liquidity', 'debt'])
    df_kf = fetch_in_chunks('kf_firms_data', ['liquidity', 'debt'])

    # Bank data is usually small enough to fetch in one go
    bank_query = f"SELECT step_id, equity FROM bank_data WHERE step_id IN {tuple(step_ids)}"
    df_bank = pd.DataFrame(execute_query(db_config, bank_query), columns=['step_id', 'equity'])

    # 4. Merge everything in Pandas
    # We rename columns to match your original expected names
    dfs = [df_steps, df_w, df_c, df_cf, df_kf, df_bank]
    df_final = reduce(lambda left, right: pd.merge(left, right, on='step_id', how='left'), dfs)

    # 5. Final Cleaning
    df_final = df_final.fillna(0)

    # Map back to your original naming convention
    rename_map = {
        'workers_data_wealth': 'w_m',
        'capitalists_data_wealth': 'c_m',
        'c_firms_data_liquidity': 'cf_m',
        'c_firms_data_debt': 'cf_d',
        'kf_firms_data_liquidity': 'kf_m',
        'kf_firms_data_debt': 'kf_d'
    }
    df_final = df_final.rename(columns=rename_map).drop(columns=['step_id'])

    # Force numeric conversion (Fixes the Decimal vs Float issue)
    numeric_cols = ['w_m', 'c_m', 'cf_m', 'cf_d', 'kf_m', 'kf_d', 'equity']
    for col in numeric_cols:
        df_final[col] = pd.to_numeric(df_final[col], errors='coerce').astype(float)

    return df_final


def get_c_sales(db_config, runid):
    query = """
    SELECT s.run_id, s.step_no, SUM(b.sales) as qty, SUM(b.sales*b.price) as amount
    FROM steps s LEFT JOIN c_firms_data b on s.step_id = b.step_id
    WHERE s.run_id = '""" + str(runid) + """'
    GROUP BY s.run_id, s.step_no
    """
    sales = execute_query(db_config, query)
    query = """
    SELECT s.run_id, s.step_no, SUM(b.spent_amount) as bought_amount_w
    FROM steps s LEFT JOIN workers_data b on s.step_id = b.step_id
    WHERE s.run_id = '""" + str(runid) + """'
    GROUP BY s.run_id, s.step_no
    """
    w_buy = execute_query(db_config, query)
    query = """
    SELECT s.run_id, s.step_no, SUM(b.spent_amount) as bought_amount_c
    FROM steps s LEFT JOIN capitalists_data b on s.step_id = b.steps_id
    WHERE s.run_id = '""" + str(runid) + """'
    GROUP BY s.run_id, s.step_no
    """
    c_buy = execute_query(db_config, query)

    d_sales = pd.DataFrame(sales, columns=['run_id', 'step_no', 'qty', 'amount'])
    dw_buy = pd.DataFrame(w_buy, columns=['run_id', 'step_no', 'bought_amount_w'])
    dc_buy = pd.DataFrame(c_buy, columns=['run_id', 'step_no', 'bought_amount_c'])

    dataframes = [d_sales, dw_buy, dc_buy]

    df_final = reduce(lambda left, right: pd.merge(left, right, on=['run_id', 'step_no'], how='outer'), dataframes)

    df_final = df_final.fillna(0)

    return df_final


def get_k_sales(db_config, runid):
    query = """
    SELECT s.run_id, s.step_no, SUM(b.sales) as qty, SUM(b.sales*b.price) as amount
    FROM steps s LEFT JOIN kf_firms_data b on s.step_id = b.step_id
    WHERE s.run_id = '""" + str(runid) + """'
    GROUP BY s.run_id, s.step_no
    """

    k_sales = execute_query(db_config, query)

    query = """
    SELECT s.run_id, s.step_no, SUM(b.invested) as buy_amount
    FROM steps s LEFT JOIN c_firms_data b on s.step_id = b.step_id
    WHERE s.run_id = '""" + str(runid) + """'
    GROUP BY s.run_id, s.step_no
    """

    k_buy = execute_query(db_config, query)
    dk_sales = pd.DataFrame(k_sales, columns=['run_id', 'step_no', 'qty', 'amount'])
    dk_buy = pd.DataFrame(k_buy, columns=['run_id', 'step_no', 'buy_amount'])

    dataframes = [dk_sales, dk_buy]

    df_final = reduce(lambda left, right: pd.merge(left, right, on=['run_id', 'step_no'], how='outer'), dataframes)

    df_final = df_final.fillna(0)

    return df_final


def get_bankrupts(db_config, runid):
    query = """
    SELECT s.run_id, s.step_no, b.cf_id as idnum, b.equity, b.debt, b.liquidity
    FROM steps s LEFT JOIN c_firms_data b on s.step_id = b.step_id
    WHERE s.run_id = '""" + str(runid) + """'
    AND b.equity < 0
    """
    c = execute_query(db_config, query)
    query = """
    SELECT s.run_id, s.step_no, b.kf_id as idnum, b.equity, b.debt, b.liquidity
    FROM steps s LEFT JOIN kf_firms_data b on s.step_id = b.step_id
    WHERE s.run_id = '""" + str(runid) + """'
    AND b.equity < 0

    """
    w = execute_query(db_config, query)
    dw = pd.DataFrame(w, columns=['run_id', 'step_no', 'idnum', 'equity', 'debt', 'liquidity'])
    dc = pd.DataFrame(c, columns=['run_id', 'step_no', 'idnum', 'equity', 'debt', 'liquidity'])

    dataframes = [dw, dc]

    df_final = pd.concat(dataframes, ignore_index=True)

    df_final = df_final.fillna(0)

    return df_final


def total_capital(db_config, runid):
    query = """
    SELECT s.run_id, s.step_no, SUM(b.capital) as capital
    FROM steps s LEFT JOIN c_firms_data b on s.step_id = b.step_id
    WHERE s.run_id = '""" + str(runid) + """'
    GROUP BY s.run_id, s.step_no
    """
    return execute_query(db_config, query)


def cap_production(db_config, runid):
    query = """
    SELECT s.step_no, SUM(b.production) as K_prod, SUM(b.inventory) as K_inventory
    FROM steps s LEFT JOIN kf_firms_data b on s.step_id = b.step_id
    WHERE s.run_id = '""" + str(runid) + """'
    GROUP BY s.step_no
    """
    return execute_query(db_config, query)


def demand(db_config, runid):
    query = """
    SELECT s.run_id, s.step_no, SUM(w.budget) as w_budget, SUM(w.spent_amount) as w_spent
    FROM steps s LEFT JOIN workers_data w on s.step_id = w.step_id
    WHERE s.run_id = '""" + str(runid) + """'
    GROUP BY s.run_id, s.step_no
    """
    w = execute_query(db_config, query)

    query = """
    SELECT s.run_id, s.step_no, SUM(c.budget) as c_budget, SUM(c.spent_amount) as c_spent
    FROM steps s LEFT JOIN capitalists_data c on s.step_id = c.steps_id
    WHERE s.run_id = '""" + str(runid) + """'
    GROUP BY s.run_id, s.step_no
    """
    c = execute_query(db_config, query)

    dw = pd.DataFrame(w, columns=['run_id', 'step_no', 'w_budget', 'w_spent'])
    dc = pd.DataFrame(c, columns=['run_id', 'step_no', 'c_budget', 'c_spent'])

    dataframes = [dw, dc]

    df_final = reduce(lambda left, right: pd.merge(left, right, on=['run_id', 'step_no'], how='outer'), dataframes)

    df_final = df_final.fillna(0)

    return df_final


def supply(db_config, runid):
    query = """
    SELECT s.step_no, SUM(b.production) as qty, SUM(b.expected_demand) as e_demand
    FROM steps s LEFT JOIN c_firms_data b on s.step_id = b.step_id
    WHERE s.run_id = '""" + str(runid) + """'
    GROUP BY s.step_no
    """
    return execute_query(db_config, query)