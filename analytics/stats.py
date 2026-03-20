import pymysql
import pandas as pd
from functools import reduce


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
        WHERE s.run_id = '""" + str(runid) +"""'
        and cf.cf_id = '""" + str(firmid) +"""'
    """
    return execute_query(db_config, query)

def get_k_firm_data(db_config, firmid, runid):
    query = """
        SELECT s.step_no, cf.*
        FROM steps s LEFT JOIN kf_firms_data cf on s.step_id = cf.step_id
        WHERE s.run_id = '""" + str(runid) +"""'
        and cf.kf_id = '""" + str(firmid) +"""'
    """
    return execute_query(db_config, query)

def get_worker_data(db_config, workerid, runid):
    query = """
        SELECT s.step_no, w.*
        FROM steps s LEFT JOIN workers_data w on s.step_id = w.step_id
        WHERE s.run_id = '""" + str(runid) +"""'
        and w.worker_id = '""" + str(workerid) +"""'
    """
    return execute_query(db_config, query)

def get_capitalist_data(db_config, capitalistid, runid):
    query = """
        SELECT s.step_no, c.*
        FROM steps s LEFT JOIN capitalists_data c on s.step_id = c.steps_id
        WHERE s.run_id = '""" + str(runid) +"""'
        and c.capitalist_id = '""" + str(capitalistid) +"""'
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


def get_unemployment_rate_over_time(db_config):
    query = """
        SELECT s.run_id, s.step_no, SUM(w.employed)/COUNT(w.worker_id) AS unemployment_rate
        FROM steps s LEFT JOIN workers_data w on s.step_id = w.step_id
        GROUP BY s.run_id, s.step_no
        WHERE s.run_id = "zgx30YZd3ECh7iZ"
    """
    return execute_query(db_config, query)

def get_bank_data(db_config, runid):
    query="""
    SELECT s.step_no, c.equity, c.k_coef, c.k_intercept, c.c_coef, c.c_intercept, c.intresses, c.losses
        FROM steps s LEFT JOIN bank_data c on s.step_id = c.step_id
        WHERE s.run_id = '""" + str(runid) +"""'
    """
    return execute_query(db_config, query)

def get_total_money_amount(db_config, runid):
    #get all money workers
    query = """ 
    SELECT s.run_id, s.step_no, SUM(w.wealth) as w_m
    FROM steps s LEFT JOIN workers_data w on s.step_id = w.step_id
    WHERE s.run_id = '""" + str(runid) +"""'
    GROUP BY s.run_id, s.step_no
    """
    w_m = execute_query(db_config, query)

    #get all capitalist money
    query = """
    SELECT s.run_id, s.step_no, SUM(c.wealth) as c_m
    FROM steps s LEFT JOIN capitalists_data c on s.step_id = c.steps_id
    WHERE s.run_id = '""" + str(runid) +"""'
    GROUP BY s.run_id, s.step_no
    """
    c_m = execute_query(db_config, query)

    #get all money from c firms
    query = """
    SELECT s.run_id, s.step_no, SUM(cf.liquidity) as cf_m, SUM(cf.debt) as cf_d
    FROM steps s LEFT JOIN c_firms_data cf on s.step_id = cf.step_id
    WHERE s.run_id = '""" + str(runid) +"""'
    GROUP BY s.run_id, s.step_no
    """
    cf_m = execute_query(db_config, query)

    # get all money from k firms
    query = """
        SELECT s.run_id, s.step_no, SUM(kf.liquidity) as kf_m, SUM(kf.debt) as kf_d
        FROM steps s LEFT JOIN kf_firms_data kf on s.step_id = kf.step_id
        WHERE s.run_id = '""" + str(runid) +"""'
        GROUP BY s.run_id, s.step_no
        """
    kf_m = execute_query(db_config, query)

    #bank
    query = """
            SELECT s.run_id, s.step_no, b.equity
            FROM steps s LEFT JOIN bank_data b on s.step_id = b.step_id
            WHERE s.run_id = '""" + str(runid) +"""'
            """
    bank = execute_query(db_config, query)

    df_w = pd.DataFrame(w_m, columns=['run_id', 'step_no', 'w_m'])
    df_c = pd.DataFrame(c_m, columns=['run_id', 'step_no', 'c_m'])
    df_cf = pd.DataFrame(cf_m, columns=['run_id', 'step_no', 'cf_m', 'cf_d'])
    df_kf = pd.DataFrame(kf_m, columns=['run_id', 'step_no', 'kf_m', 'kf_d'])
    bank = pd.DataFrame(bank, columns=['run_id', 'step_no', 'equity'])

    dataframes = [df_w, df_c, df_cf, df_kf, bank]

    df_final = reduce(lambda left, right: pd.merge(left, right, on=['run_id', 'step_no'], how='outer'), dataframes)

    df_final = df_final.fillna(0)

    return df_final

def get_c_sales(db_config, runid):
    query = """
    SELECT s.run_id, s.step_no, SUM(b.sales) as qty, SUM(b.sales*b.price) as amount
    FROM steps s LEFT JOIN c_firms_data b on s.step_id = b.step_id
    WHERE s.run_id = '""" + str(runid) +"""'
    GROUP BY s.run_id, s.step_no
    """
    sales= execute_query(db_config, query)
    query = """
    SELECT s.run_id, s.step_no, SUM(b.spent_amount) as bought_amount_w
    FROM steps s LEFT JOIN workers_data b on s.step_id = b.step_id
    WHERE s.run_id = '""" + str(runid) +"""'
    GROUP BY s.run_id, s.step_no
    """
    w_buy= execute_query(db_config, query)
    query = """
    SELECT s.run_id, s.step_no, SUM(b.spent_amount) as bought_amount_c
    FROM steps s LEFT JOIN capitalists_data b on s.step_id = b.steps_id
    WHERE s.run_id = '""" + str(runid) +"""'
    GROUP BY s.run_id, s.step_no
    """
    c_buy= execute_query(db_config, query)

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
    WHERE s.run_id = '""" + str(runid) +"""'
    GROUP BY s.run_id, s.step_no
    """

    k_sales= execute_query(db_config, query)

    query = """
    SELECT s.run_id, s.step_no, SUM(b.invested) as buy_amount
    FROM steps s LEFT JOIN c_firms_data b on s.step_id = b.step_id
    WHERE s.run_id = '""" + str(runid) +"""'
    GROUP BY s.run_id, s.step_no
    """

    k_buy= execute_query(db_config, query)
    dk_sales = pd.DataFrame(k_sales, columns=['run_id', 'step_no', 'qty', 'amount'])
    dk_buy = pd.DataFrame(k_buy, columns=['run_id', 'step_no', 'buy_amount'])

    dataframes = [dk_sales, dk_buy]

    df_final = reduce(lambda left, right: pd.merge(left, right, on=['run_id', 'step_no'], how='outer'), dataframes)

    df_final = df_final.fillna(0)

    return df_final

