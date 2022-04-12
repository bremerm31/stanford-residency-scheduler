import argparse
import os.path

from src.inputs import Config

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Compute Optimal residency schedule')
    parser.add_argument('CONFIG_FILE', type=str,
                        help='input yaml config file')
    args = parser.parse_args()

    assert os.path.exists(args.CONFIG_FILE)

    model_config = Config(args.CONFIG_FILE)
    print("Input Configuration summary")
    model_config.print_summary()
    