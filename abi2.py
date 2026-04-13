from analytics.stats import *
import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import csv

load_dotenv()
db_creds = {
    'host': os.getenv("host"),
    'port': int(os.getenv("port")),
    'user': os.getenv("user"),
    'password': os.getenv("password"),
    'database': os.getenv("database")
}
runid="6CMzaM96lJhziPZ"


query="""
SELECT  s.step_no, b.intresses as intr, b.debt as debt, b.intresses/b.debt as rate, b.loans
FROM steps s LEFT JOIN c_firms_data b on s.step_id = b.step_id
WHERE s.run_id = '""" + str(runid) +"""'
AND b.intresses/b.debt < 0.01
AND b.debt > 0.1
"""
#
result=execute_query(db_creds, query)
#print(result)
#to csv
loans = pd.DataFrame(result, columns=['step_no', 'intr', 'debt', 'rate', 'loans'])
loans.to_csv('laonsdata.csv', index=False)