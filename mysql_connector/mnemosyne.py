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

def populate_run_data(db_config, run):

    #send bank const
    bank_const = {
        "run_id": run.runid,
        "mu": run.bank.mu,
        "theta": run.bank.theta,
        "zeta": run.bank.zeta
    }
    send_bank_const(db_config, bank_const)


    #send workers const
    workers=[]
    for w in run.workers:
        worker_const = {
            "run_id": run.runid,
            "worker_id": w.id,
            "xi": w.xi,
            "chi": w.chi,
            "si": w.search_count
        }
        workers.append(worker_const)

    send_worker_const(db_config, workers)

    #send c_firms const
    cfs=[]
    for c in run.c_firms:
        c_firm_const = {
            "run_id": run.runid,
            "cf_id": c.id,
            "delta": c.delta,
            "eta_max": c.eta_max,
            "kappa": c.kappa,
            "gamma": c.gamma,
            "labour_prod": c.labour_prod,
            "nu": c.nu,
            "omega": c.omega,
            "owner_id": c.owner.id,
            "rho": c.rho,
            "search_count": c.search_count,
            "tau": c.tau,
            "theta": c.theta
        }
        cfs.append(c_firm_const)
    send_c_firm_const(db_config, cfs)

    #send k_firms const
    kfs=[]
    for k in run.k_firms:
        k_firm_const = {
            "run_id": run.runid,
            "kf_id": k.id,
            "delta": k.delta,
            "eta_max": k.eta_max,
            "labour_prod": k.labour_prod,
            "owner_id": k.owner.id,
            "rho": k.rho,
            "tau": k.tau,
            "theta": k.theta
        }
        kfs.append(k_firm_const)
    send_k_firm_const(db_config, kfs)

    #send capitalists const
    caps=[]
    for cap in run.capitalists:
        capitalist_const = {
            "run_id": run.runid,
            "capitalist_id": cap.id,
            "xi": cap.xi,
            "chi": cap.chi,
            "si": cap.search_count,
            "owned_firm_id": cap.owned_firm.id
        }
        caps.append(capitalist_const)
    send_capitalists_const(db_config, caps)


    return 0

def send_bank_const(db_config, bank_const):
    try:
        connection = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            charset='utf8mb4'
        )

        columns = ["run_id", "mu", "theta", "zeta"]
        placeholders = ", ".join(["%s"] * len(columns))
        column_names = ", ".join(columns)

        values = [bank_const.get(col) for col in columns]

        with connection.cursor() as cursor:
            query = f"INSERT INTO bank_const ({column_names}) VALUES ({placeholders})"
            cursor.execute(query, values)
            connection.commit()

    except pymysql.MySQLError as e:
        print(f"Error while connecting to MySQL: {e}")
        raise

def send_worker_const(db_config, worker_const):
    try:
        connection = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            charset='utf8mb4'
        )

        columns = ["run_id", "worker_id", "xi", "chi", "si"]
        placeholders = ", ".join(["%s"] * len(columns))
        column_names = ", ".join(columns)

        values_to_insert = [
            [worker.get(col) for col in columns]
            for worker in worker_const
        ]

        with connection.cursor() as cursor:
            query = f"INSERT INTO workers_const ({column_names}) VALUES ({placeholders})"

            # executemany handles the looping and optimization internally
            cursor.executemany(query, values_to_insert)
            connection.commit()

    except pymysql.MySQLError as e:
        if connection:
            connection.rollback()
        print(f"Error while connecting to MySQL: {e}")
        raise


def send_c_firm_const(db_config, c_firm_const):
    try:
        connection = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            charset='utf8mb4'
        )

        columns = ["run_id", "cf_id", "delta", "eta_max", "kappa", "gamma", "labour_prod",
                   "nu", "omega", "owner_id", "rho", "search_count", "tau", "theta"]
        placeholders = ", ".join(["%s"] * len(columns))
        column_names = ", ".join(columns)

        values_to_insert = [
            [c_firm.get(col) for col in columns]
            for c_firm in c_firm_const
        ]

        with connection.cursor() as cursor:
            query = f"INSERT INTO cf_firms_const ({column_names}) VALUES ({placeholders})"

            # executemany handles the looping and optimization internally
            cursor.executemany(query, values_to_insert)
            connection.commit()

    except pymysql.MySQLError as e:
        print(f"Error while connecting to MySQL: {e}")
        raise

def send_k_firm_const(db_config, k_firm_const):
    try:
        connection = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            charset='utf8mb4'
        )

        columns = ["run_id", "kf_id", "delta", "eta_max", "labour_prod",
                   "owner_id", "rho", "tau", "theta"]
        placeholders = ", ".join(["%s"] * len(columns))
        column_names = ", ".join(columns)

        values_to_insert = [
            [k_firm.get(col) for col in columns]
            for k_firm in k_firm_const
        ]
        with connection.cursor() as cursor:
            query = f"INSERT INTO kf_firms_const ({column_names}) VALUES ({placeholders})"

            # executemany handles the looping and optimization internally
            cursor.executemany(query, values_to_insert)
            connection.commit()

    except pymysql.MySQLError as e:
        print(f"Error while connecting to MySQL: {e}")
        raise

def send_capitalists_const(db_config, capitalist_const):
    try:
        connection = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            charset='utf8mb4'
        )

        columns = ["run_id", "capitalist_id", "xi", "chi", "si", "owned_firm_id"]
        placeholders = ", ".join(["%s"] * len(columns))
        column_names = ", ".join(columns)

        values_to_insert = [
            [capitalist.get(col) for col in columns]
            for capitalist in capitalist_const
        ]
        with connection.cursor() as cursor:
            query = f"INSERT INTO capitalist_const ({column_names}) VALUES ({placeholders})"

            # executemany handles the looping and optimization internally
            cursor.executemany(query, values_to_insert)
            connection.commit()

    except pymysql.MySQLError as e:
        print(f"Error while connecting to MySQL: {e}")
        raise

def get_all_runs(db_config):
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
            query = f"SELECT run_id FROM runs"
            cursor.execute(query)
            result = cursor.fetchall()
            return result

    except pymysql.MySQLError as e:
        print(f"Error while connecting to MySQL: {e}")
        raise

def drop_whole_run_data(db_config, run_id):
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
            query = f"DELETE FROM runs WHERE run_id = %s"
            cursor.execute(query, (run_id,))
            connection.commit()



    except pymysql.MySQLError as e:
        print(f"Error while connecting to MySQL: {e}")
        raise

def drop_all_runs(db_config):
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
            query = f"DELETE FROM runs"
            cursor.execute(query)
            connection.commit()

    except pymysql.MySQLError as e:
        print(f"Error while connecting to MySQL: {e}")
        raise

