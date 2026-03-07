import yaml
from engine import *
import time
from dotenv import load_dotenv
import os


#SETTINGS
CONFIG="DB"  # Could be "YAML" or "DB",
yaml_config_path = "config.yaml"  # Path to YAML config file if using YAML
create_new_config_in_db = True  # Whether to create a new config in the database or fetch an existing one
db_config_id = 2  # ID of the config in the database if using DB


def main(settings):

    rm = runManager(settings) # manager sets up config and database connection, and manages runs

    run=rm.create_new_run()


    return 0

    # 2. Initialize the Engine (which creates all agents)
    economy = SimulationEngine(config)

    # 3. Run Simulation Loop
    for t in range(config['simulation']['periods']):
        data=economy.run_step()

    return data


if __name__ == "__main__":

    settings={
        "CONFIG": CONFIG,
        "yaml_config_path": yaml_config_path,
        "db_config_id": db_config_id,
        "create_new_config_in_db": create_new_config_in_db
    }
    N=1
    for i in range(N):
        data=main(settings)
