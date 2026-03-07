import pymysql
from pymysql.converters import escape_string
import json, uuid, time
from decimal import Decimal


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
            print(f"Executing Query: {query}")  # Debug
            cursor.execute(query)
            result = cursor.fetchall()
            print(f"Query Result: {result}")  # Debug
            return result

    except pymysql.MySQLError as e:
        print(f"Error while connecting to MySQL: {e}")  # Debug
        raise
    finally:
        if connection:
            connection.close()
            print("MySQL connection closed")


def send_config_data(db_config, config_data):

    try:
        connection = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            charset='utf8mb4'
        )

        columns = [
            "periods", "num_workers", "num_c_firms", "num_k_firms", "income_memory_weight",
            "wealth_consumption_ratio", "initial_assets", "si_labor", "si_consumer",
            "dividend_payout_ratio", "qty_adjustment", "p_adjustment_max", "wage_rate",
            "init_m", "init_capital", "c_init_production", "c_productivity", "invest_prob",
            "c_depreciation", "invest_memory", "desired_util", "search_k", "c_init_p",
            "k_initial_production", "l_productivity", "k_init_p", "b_init_e",
            "risk_free_rate", "markup", "loss_param", "debt_installment_rate"
        ]

        placeholders = ", ".join(["%s"] * len(columns))
        column_names = ", ".join(columns)

        values = [config_data.get(col) for col in columns]

        with connection.cursor() as cursor:
            query = f"INSERT INTO configs ({column_names}) VALUES ({placeholders})"
            cursor.execute(query, values)
            new_config_id = cursor.lastrowid
            connection.commit()
            #print("Config data sent to MySQL")
            return new_config_id

    except pymysql.MySQLError as e:
        print(f"Error while connecting to MySQL: {e}")  # Debug
        raise

def fetch_config_data(db_config, config_id):
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
            query = f"SELECT * FROM configs WHERE config_id = %s"
            cursor.execute(query, (config_id,))
            result = cursor.fetchone()
            if result:
                columns = [desc[0] for desc in cursor.description]
                config_data = dict(zip(columns, result))
                return config_data
            else:
                print(f"No config found with ID: {config_id}")
                return None

    except pymysql.MySQLError as e:
        print(f"Error while connecting to MySQL: {e}")  # Debug
        raise

def send_run_data(db_config, run_data):
    try:
        connection = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            charset='utf8mb4'
        )

        columns = ["config", "run_id", "start_seed", "name", "version"]
        #start_seed is bigint(20) in mysql
        placeholders = ", ".join(["%s"] * len(columns))
        column_names = ", ".join(columns)

        values = [run_data.get(col) for col in columns]

        with connection.cursor() as cursor:
            query = f"INSERT INTO runs ({column_names}) VALUES ({placeholders})"
            cursor.execute(query, values)
            connection.commit()

    except pymysql.MySQLError as e:
        print(f"Error while connecting to MySQL: {e}")
        raise