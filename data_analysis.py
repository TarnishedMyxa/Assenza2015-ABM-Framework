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
runid="gm7OSjRfMnJoveM"


firm_data= get_firm_data(db_creds, "C_0", runid)
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

k_firm_data=get_k_firm_data(db_creds, "K_0", runid)
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
    if firm_data:
        writer.writerows(k_firm_data)
    else:
        print("No data found for the specified Run ID and Firm ID.")


worker_data= get_worker_data(db_creds, "W_0", runid)
headers = [
    'step_no', 'step_id', 'worker_id', 'wealth', 'human_wealth',
    'spent_amount', 'employed', 'employer_id', 'budget'
]
with open('worker_data.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)

    # Write the header row
    writer.writerow(headers)

    # Write all data rows
    if worker_data:
        writer.writerows(worker_data)
    else:
        print("No data found for the specified Run ID and Worker ID.")

capitalist_data= get_capitalist_data(db_creds, "B_0", runid)
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


liquidity= get_total_money_amount(db_creds, runid)
liquidity.to_csv('liquidity_data.csv', index=False)


bank_data= get_bank_data(db_creds,runid)
headers = [
    'step_no', 'equity', 'k_coef', 'k_intercept',
    'c_coef',  'c_intercept', 'intresses',  'losses'
]
with open('bank_data.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(headers)
    if bank_data:
        writer.writerows(bank_data)
    else:
        print("No data found for the specified Run ID and Bank ID.")

c_sales=get_c_sales(db_creds,runid)
c_sales.to_csv('c_sales_data.csv', index=False)

k_sales=get_k_sales(db_creds,runid)
k_sales.to_csv('k_sales_data.csv', index=False)



