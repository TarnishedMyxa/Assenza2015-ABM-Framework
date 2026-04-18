import pymysql
import pandas as pd
import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.tsa.filters.hp_filter import hpfilter
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

def get_run_ids(db_config):
    query = "SELECT DISTINCT run_id FROM steps"
    # Assuming execute_query returns a DataFrame
    res = execute_query(db_config, query)
    return [row[0] for row in res]


def get_data_for_run(db_config, run_id):
    query = f"""
        SELECT 
            s.step_no, 
            COALESCE(k.total_k, 0) as consum
        FROM steps s
        LEFT JOIN (
            SELECT step_id, SUM(sales) as total_k 
            FROM c_firms_data 
            GROUP BY step_id
        ) k ON s.step_id = k.step_id
        WHERE s.run_id = '{run_id}'
        AND s.step_no > 200
        ORDER BY s.step_no
        """
    res = execute_query(db_config, query)
    # Convert tuple of tuples to DataFrame
    return pd.DataFrame(res, columns=['step_no', 'consum'])


def process_all_runs(db_config, lamb=100000):
    run_ids = get_run_ids(db_config)
    autocorrelations = []
    std_dev_list = []

    print(f"Starting processing for {len(run_ids)} runs...")

    for rid in run_ids:
        try:
            df_run = get_data_for_run(db_config, rid)

            if len(df_run) < 200:  # Skip empty or too short runs
                continue

            gdp_log = np.log(df_run['consum'].replace(0, np.nan).interpolate())
            #gdp_log = df_run['consum'].replace(0, np.nan).interpolate()
            cycle, trend = hpfilter(gdp_log, lamb=lamb)

            ac = cycle.autocorr(lag=1)
            sd = cycle.std()
            autocorrelations.append(ac)
            std_dev_list.append(sd)

        except Exception as e:
            print(f"Error on run {rid}: {e}")


    if autocorrelations:
        final_avg = np.mean(autocorrelations)
        final_std = np.mean(std_dev_list)
        print(f"Average Cyclical Autocorrelation: {final_avg:.4f}")
        print(f"Average Std Dev Cyclical : {final_std:.4f}")
        return final_avg, final_std
    return None


avg_persistence = process_all_runs(db_creds)