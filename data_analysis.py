from analytics.stats import *
import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt

load_dotenv()
db_creds = {
    'host': os.getenv("host"),
    'port': int(os.getenv("port")),
    'user': os.getenv("user"),
    'password': os.getenv("password"),
    'database': os.getenv("database")
}


"""
    SELECT s.run_id, s.step_no, cf.price
    FROM steps s LEFT JOIN c_firms_data cf on s.step_id = cf.step_id
    WHERE s.run_id = "zgx30YZd3ECh7iZ"
"""
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
