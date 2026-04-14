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

    #rm._drop_all_runs_from_db()

    run=rm.create_new_run()

    rm.run_steps(run, 3000)

    return 0


if __name__ == "__main__":

    settings={
        "CONFIG": CONFIG,
        "yaml_config_path": yaml_config_path,
        "db_config_id": db_config_id,
        "create_new_config_in_db": create_new_config_in_db
    }
    RUNS=1
    for i in range(RUNS):
        data=main(settings)
