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
runid="J76zZkrfd5U3OHK"


k_firm_data=get_k_firm_data(db_creds, "K_12", runid)
headers=[
    'step_no', 'step_id', 'kf_id', 'liquidity', 'price', 'equity', 'debt',
    'profit', 'production', 'sales',"inventory", 'queue', 'expected_demand',
    'intresses', "loans", 'labour_demand', 'staff',
    'first_step', 'lmbda', 'wage_bill'
]

with open('k_firm_data.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)

    # Write the header row
    writer.writerow(headers)

    # Write all data rows
    if k_firm_data:
        writer.writerows(k_firm_data)
    else:
        print("No data found for the specified Run ID and Firm ID.")

capitalist_data= get_capitalist_data(db_creds, "B_116", runid)
headers = [
    'step_no', 'steps_id', 'capitalist_id', 'budget', 'wealth',
    'human_wealth',  'spent_amount'
]
with open('capitalist_data.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)

    # Write the header row
    writer.writerow(headers)

    # Write all data rows
    if capitalist_data:
        writer.writerows(capitalist_data)
    else:
        print("No data found for the specified Run ID and Capitalist ID.")


firm_data= get_firm_data(db_creds, "C_116", runid)
headers = [
    'step_no', 'step_id', 'cf_id', 'liquidity', 'price', 'equity', 'debt',
    'profit', 'production', 'sales', 'queue', 'expected_demand',
    'intresses', 'labour_demand', 'lmbda', 'loans', 'staff',
    'first_step', 'capital', 'capital_avg', 'invested',
    'planned_production', 'planned_investment', 'wage_bill',
    'investment_cost', 'capital_book', 'desired_capital'
]


with open('firm_data.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)

    # Write the header row
    writer.writerow(headers)

    # Write all data rows
    if firm_data:
        writer.writerows(firm_data)
    else:
        print("No data found for the specified Run ID and Firm ID.")