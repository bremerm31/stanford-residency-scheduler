import argparse
import os.path

from src.inputs import Config
from src.model import schedulingModel
from src.rules import RuleFactory
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

    rules = [ RuleFactory(rule_input)
              for rule_input in model_config.rules]

    m.build_model(model_config.residents,
                  model_config.services)

    for r in rules:
        r.addRuleToModel(m,
                         model_config.residents,
                         model_config.services)

    m.optimize(model_config.residents,
               model_config.services)

    print("Optimization Complete")
    print("Max hours per 6 week interval: {:.1f}".format(m.max_avg_hours_per_interval))
    print("Max avg hours per year: {:.1f}".format(m.max_avg_hours_per_year))

    m.write_csv(model_config.output_filename,
                model_config.residents,
                model_config.services)