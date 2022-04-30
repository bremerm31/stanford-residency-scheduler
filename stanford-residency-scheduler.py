import argparse
import os.path

from src.inputs import Config
from src.model import schedulingModel

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Compute Optimal residency schedule')
    parser.add_argument('CONFIG_FILE', type=str,
                        help='input yaml config file')
    args = parser.parse_args()

    assert os.path.exists(args.CONFIG_FILE)

    model_config = Config(args.CONFIG_FILE)
    print("Input Configuration summary")
    model_config.print_summary()

    m = schedulingModel(model_config.gurobi)

    m.build_model(model_config.residents,
                  model_config.services)

    m.write_csv(model_config.output_filename,
                model_config.residents,
                model_config.services)