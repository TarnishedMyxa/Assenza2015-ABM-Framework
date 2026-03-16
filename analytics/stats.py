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

def get_total_money_amount(db_config):
    #get all money workers
    query = """ 
    SELECT s.run_id, s.step_no, SUM(w.wealth) as w_m
    FROM steps s LEFT JOIN workers_data w on s.step_id = w.step_id
    GROUP BY s.run_id, s.step_no
    """
    w_m = execute_query(db_config, query)

    #get all capitalist money
    query = """
    SELECT s.run_id, s.step_no, SUM(c.wealth) as c_m
    FROM steps s LEFT JOIN capitalists_data c on s.step_id = c.steps_id
    GROUP BY s.run_id, s.step_no
    """
    c_m = execute_query(db_config, query)

    #get all money from c firms
    query = """
    SELECT s.run_id, s.step_no, SUM(cf.liquidity) as cf_m, SUM(cf.debt) as cf_d
    FROM steps s LEFT JOIN c_firms_data cf on s.step_id = cf.step_id
    GROUP BY s.run_id, s.step_no
    """
    cf_m = execute_query(db_config, query)

    # get all money from k firms
    query = """
        SELECT s.run_id, s.step_no, SUM(kf.liquidity) as kf_m, SUM(kf.debt) as kf_d
        FROM steps s LEFT JOIN kf_firms_data kf on s.step_id = kf.step_id
        GROUP BY s.run_id, s.step_no
        """
    kf_m = execute_query(db_config, query)

    #bank
    query = """
            SELECT s.run_id, s.step_no, b.equity
            FROM steps s LEFT JOIN bank_data b on s.step_id = b.step_id
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