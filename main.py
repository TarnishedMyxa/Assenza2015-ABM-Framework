import yaml
from engine import *
import time
from dotenv import load_dotenv
import os

CONFIG="DB"  # Could be "YAML" or "DB",
yaml_config_path = "config.yaml"  # Path to YAML config file if using YAML
db_config_id = 2  # ID of the config in the database if using DB




def main(db_creds):

    if CONFIG == "DB":
        config = fetch_config_from_db(db_creds, db_config_id)
        cnf_id = config["config_id"]
    else:
        with open(yaml_config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            cnf_id=send_config_to_db(db_creds, config)
            config['config_id']=cnf_id

    return

    # 2. Initialize the Engine (which creates all agents)
    economy = SimulationEngine(config)

    # 3. Run Simulation Loop
    for t in range(config['simulation']['periods']):
        data=economy.run_step()

    return data


if __name__ == "__main__":
    if CONFIG == "DB":
        load_dotenv()
        db_creds = {
            'host': os.getenv("host"),
            'port': int(os.getenv("port")),
            'user': os.getenv("user"),
            'password': os.getenv("password"),
            'database': os.getenv("database")
        }
    else:
        db_creds=None
    N=1
    for i in range(N):
        data=main(db_creds)
