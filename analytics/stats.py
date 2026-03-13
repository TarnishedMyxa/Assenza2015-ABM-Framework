import pymysql


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