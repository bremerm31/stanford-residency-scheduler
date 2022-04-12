import csv
import yaml

import os.path

class ConfigException(Exception):
    """Raise for exceptions encountered during input file parsing"""


class Resident:
    allowable_years={'AP1','AP2'}

    def __init__(self, name, year, headers, data):
        assert len(headers) == len(data)
        self.name = str(name)
        self.year = year
        self.service_lbs = {}
        for service_name, req in zip(headers, data):
            self.service_lbs[service_name] = int(req) if req else None

        if self.year not in Resident.allowable_years:
            raise ConfigException("Year "+self.year+" is an unknown type")

class ClinicalService:
    def __init__(self, name, lb, ub, hardness):
        self.name     = str(name)
        self.lb = int(lb) if lb else None
        self.ub = int(ub) if ub else None
        self.hardness = float(hardness)

class Config:
    def __init__(self, config_file):
        with open(config_file, 'r') as f:
            config_inputs = yaml.safe_load(f)

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
                    ClinicalService(s[0], s[1], s[2], s[3]))

        service_set = { s.name for s in self.services }

        self.residents = []
        with open(sched['ap1_residents']) as f:
            reader = csv.reader(f)
            header = next(reader)

            for s in header[1:]:
                if s not in service_set:
                    raise ConfigException("Unknown service "+
                                          s+" not found in "+service_csv)

            for r in reader:
                self.residents.append(
                    Resident(r[0], 'AP1', header[1:], r[1:]))

        with open(sched['ap2_residents']) as f:
            reader = csv.reader(f)
            header = next(reader)

            for s in header[1:]:
                if s not in service_set:
                    raise ConfigException("Unknown service "+
                                          s+" not found in "+service_csv)

            for r in reader:
                self.residents.append(
                    Resident(r[0], 'AP2', header[1:], r[1:]))
        
    def print_summary(self):
        print("{:d} services".format(len(self.services)))
        print("{:d} residents".format(len(self.residents)))
        count_AP1 = 0
        for r in self.residents:
            if r.year == "AP1":
                count_AP1 += 1
        print("{:d} AP1 residents".format(count_AP1))
        count_AP2 = 0
        for r in self.residents:
            if r.year == "AP2":
                count_AP2 += 1
        print("{:d} AP2 residents".format(count_AP2))