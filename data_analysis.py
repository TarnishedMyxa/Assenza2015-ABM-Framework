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
runid="PvVpgXTKXpLEWqn"


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
    'step_no', 'steps_id', 'capitalist_id', 'wealth', 'human_wealth',
    'spent_amount',  'budget'
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


liquidity= get_total_money_amount(db_creds)
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


"""
    SELECT s.run_id, s.step_no, cf.price
    FROM steps s LEFT JOIN c_firms_data cf on s.step_id = cf.step_id
    WHERE s.run_id = "zgx30YZd3ECh7iZ"

simply_prices= get_simply_prices(db_creds)

# plot price distribution over time
steps = [step_no for run_id, step_no, price in simply_prices]
prices = [price for run_id, step_no, price in simply_prices]
plt.figure(figsize=(10, 5))
plt.scatter(steps, prices, alpha=0.5)
plt.title('Price Distribution of C Firms Over Time')
plt.xlabel('Step No')
plt.ylabel('Price')
plt.grid()
plt.show()
"""


"""
prices=get_c_price_over_time(db_creds)

# avg price= total_sales/total_qty
avg_prices = []
for run_id, step_no, total_qty, total_sales in prices:
    avg_price = total_sales / total_qty if total_qty > 0 else 0
    avg_prices.append((step_no, avg_price))

# Plotting the average price over time
steps = [step_no for step_no, avg_price in avg_prices]
avg_price_values = [avg_price for step_no, avg_price in avg_prices]
plt.figure(figsize=(10, 5))
plt.plot(steps, avg_price_values, marker='o')
plt.title('Average Price of C Firms Over Time')
plt.xlabel('Step No')
plt.ylabel('Average Price')
plt.grid()
plt.show()
"""








#unemployment= get_unemployment_rate_over_time(db_creds)
