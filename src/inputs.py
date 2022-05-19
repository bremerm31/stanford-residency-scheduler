import csv
import yaml

import os.path

class ConfigException(Exception):
    """Raise for exceptions encountered during input file parsing"""

n_services = 21

class Resident:
    allowable_years={'AP1','AP2'}

    def __init__(self, name, year, headers, data):
        assert len(headers) == len(data)
        self.name = str(name)
        self.year = year
        self.service_lbs = {}
        for service_name, req in zip(headers[:n_services], data[:n_services]):
            req = req.split('-')[0]
            if service_name == "Conference":
                if req == "Yes" or req == "USCAP":
                    self.service_lbs[service_name] = 1
                else:
                    self.service_lbs[service_name] = 0
            else:
                self.service_lbs[service_name] = int(req) if req else None

        assert headers[n_services] == "Vacation weeks"
        print(self.name, data[n_services])
        self.vacation_weeks = [ int(w.strip()[5:]) - 2
                                for w in data[n_services].split(",") ]

        if self.year not in Resident.allowable_years:
            raise ConfigException("Year "+self.year+" is an unknown type")

class ClinicalService:
    def __init__(self, name, lb, ub, hardness, ok_after_vacation):
        self.name     = str(name)
        self.lb = int(lb) if lb else None
        self.ub = int(ub) if ub else None
        self.hardness = float(hardness)
        self.ok_after_vacation = bool(ok_after_vacation=='y')

class Config:
    def __init__(self, config_file):
        with open(config_file, 'r') as f:
            config_inputs = yaml.safe_load(f)

        self.parse_gurobi_config(
            config_inputs['gurobi'] if 'gurobi' in config_inputs
            else dict())

        self.rules= \
            config_inputs['rules'] if 'rules' in config_inputs \
            else []

        sched = config_inputs['scheduling']
        service_csv = sched['service_requirements']

        assert os.path.exists(service_csv)
        assert os.path.exists(sched['ap1_residents'])
        assert os.path.exists(sched['ap2_residents'])

        with open(service_csv) as f:
            next(f)
            reader = csv.reader(f)
            self.services = []
            for s in reader:
                self.services.append(
                    ClinicalService(s[0], s[1], s[2], s[3], s[4]))

        service_set = { s.name for s in self.services }

        self.residents = []
        with open(sched['ap1_residents']) as f:
            reader = csv.reader(f)
            header = next(reader)

            for s in header[1:(n_services)]:
                if s not in service_set:
                    raise ConfigException("Unknown service "+
                                          s+" not found in "+service_csv)

            for r in reader:
                self.residents.append(
                    Resident(r[0], 'AP1', header[1:], r[1:]))

        with open(sched['ap2_residents']) as f:
            reader = csv.reader(f)
            header = next(reader)

            for s in header[1:(n_services)]:
                if s not in service_set:
                    raise ConfigException("Unknown service "+
                                          s+" not found in "+service_csv)

            for r in reader:
                self.residents.append(
                    Resident(r[0], 'AP2', header[1:], r[1:]))

        self.output_filename = config_inputs['output']['file']

    def parse_gurobi_config(self, gurobi_node):
        self.gurobi = {}
        if 'BestObjStop' in gurobi_node:
            self.addVar(gurobi_node, 'BestObjStop', float)
        else:
            self.gurobi['BestObjStop'] = 0.05
        if 'MIPFocus' in gurobi_node:
            self.addVar(gurobi_node, 'MIPFocus')
        else:
            self.gurobi['MIPFocus'] = 1
        if 'Threads' in gurobi_node:
            self.addVar(gurobi_node, 'Threads')
        else:
            self.gurobi['Threads'] = 2
        if 'Presolve' in gurobi_node:
            self.addVar(gurobi_node, 'Presolve')
        else:
            self.gurobi['Presolve'] = 2

    def addVar(self, node, key, dtype=int):
        self.gurobi[key] = dtype(node[key])
        
    def print_summary(self):
        print("{:d} services".format(len(self.services)))
        print("{:d} residents".format(len(self.residents)))
        count_AP1 = 0
        count_AP2 = 0
        for r in self.residents:
            if r.year == "AP1":
                count_AP1 += 1
            if r.year == "AP2":
                count_AP2 += 1
        print("{:d} AP1 residents".format(count_AP1))
        print("{:d} AP2 residents".format(count_AP2))
        print("{:d} Rules found".format(len(self.rules)))
        print("Writing results to {:}".format(self.output_filename))