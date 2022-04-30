import csv
import gurobipy as gb
from gurobipy import GRB

class schedulingModel:
    n_weeks = 52

    def __init__(self, gurobi_params):
        print(gurobi_params)
        self.BestObjStop = gurobi_params['BestObjStop']
        self.MIPFocus    = gurobi_params['MIPFocus']
        self.Threads     = gurobi_params['Threads']
        self.Presolve    = gurobi_params['Presolve']


    def build_model(self, residents, services):
        hardness_interval = 6
        hardness_weight_ratio = 0.5

        n_weeks = schedulingModel.n_weeks
        n_residents = len(residents)
        n_services = len(services)

        try:
            self.model = gb.Model('Residency Scheduler')

            self.schedule = self.model.addVars(
                n_residents, n_services, n_weeks,
                vtype = GRB.BINARY,
                name = 'X')

            #Add basic model constraints

            #Residents can be on one service at a time
            self.model.addConstrs((self.schedule.sum(r,'*',t) == 1
                                   for r in range(n_residents)
                                   for t in range(n_weeks)),
                                  name="One service per resident")

            #Each resident must meet their requirements
            for s_idx, s in enumerate(services):
                self.model.addConstrs((self.schedule.sum(r,s_idx,'*') >= residents[r].service_lbs[s.name]
                                       for r in range(n_residents) if residents[r].service_lbs[s.name]),
                                      name="Residents requirements for "+s.name)

            #Each service must meet its coverage bounds
            for s_idx, s in enumerate(services):
                self.model.addConstrs((self.schedule.sum('*',s_idx,t) >= s.lb
                                       for t in range(n_weeks) if s.lb),
                                      name="Service coverage lower bounds")
                self.model.addConstrs((self.schedule.sum('*',s_idx,t) <= s.ub
                                       for t in range(n_weeks) if s.ub),
                                      name="Service coverage upper bounds")

            #Compute hardess over hardness_interval
            hrs_per_interval = self.model.addVars(n_residents, n_weeks-hardness_interval,
                                                  vtype=GRB.CONTINUOUS,
                                                  name=str(hardness_interval)+"-week avg hrs")

            self.model.addConstrs((gb.quicksum(self.schedule[r,s,tt] * services[s].hardness
                                               for s in range(n_services)
                                               for tt in range(t, t+hardness_interval))
                                   == hrs_per_interval[r,t] * hardness_interval
                                   for r in range(n_residents)
                                   for t in range(n_weeks -hardness_interval)),
                                  name="Interval definition")

            max_hrs_per_interval = self.model.addVars(n_residents, vtype=GRB.CONTINUOUS,
                                                      name="max "+str(hardness_interval)+"-week avg hrs")

            self.model.addConstrs((max_hrs_per_interval[r] == gb.max_([hrs_per_interval[r,t] for t in range(n_weeks-hardness_interval)])
                                   for r in range(n_residents)),
                                  name="defn max hardness")

            avg_hrs_per_year = self.model.addVars(n_residents,
                                                  vtype=GRB.CONTINUOUS,
                                                  name="Avg hours per year")

            self.model.addConstrs((gb.quicksum(self.schedule[r,s,t] * services[s].hardness
                                               for s in range(n_services)
                                               for t in range(n_weeks)) == avg_hrs_per_year[r] * n_weeks
                                   for r in range(n_residents)),
                                  name="Avg hours definition")
            
            resident_hardness = self.model.addVars(n_residents,
                                                   vtype=GRB.CONTINUOUS,
                                                   name="Hardness")

            if hardness_weight_ratio > 0:
                self.model.addConstrs((max_hrs_per_interval[r] == resident_hardness[r]
                                   for r in range(n_residents)),
                                  name="Hardness definition")
            else:
                self.model.addConstrs((resident_hardness[r] == avg_hrs_per_year[r]
                                   for r in range(n_residents)),
                                  name="Hardness definition")

            max_hardness = self.model.addVar(vtype=GRB.CONTINUOUS,
                                             name="max_work")
            self.model.addConstr(max_hardness == gb.max_(resident_hardness), name="max_hardness definition")

            self.model.setObjective(max_hardness)
            self.model.setParam('BestObjStop', self.BestObjStop)
            self.model.setParam('MIPFocus', self.MIPFocus)
            self.model.setParam('Threads', self.Threads)
            self.model.setParam('Presolve', self.Presolve)
            self.optimize()

        except gb.GurobiError as e:
            print('Error code '+str(e.errno) + ": "+str(e))

    def performIISAnalysis(self):
        try:
            self.model.computeIIS()

            for c in self.model.getConstrs():
                if c.IISConstr:
                    print('%s' % c.ConstrName)
        except gb.GurobiError as e:
            print('Error code '+str(e.errno) + ": "+str(e))

    def optimize(self):
        try:
            self.model.optimize()
        except gb.GurobiError as e:
            print('Error code '+str(e.errno) + ": "+str(e))

    def write_csv(self, filename, residents, services):
        attr_schedule = self.model.getAttr('X', self.schedule)
        with open(filename, 'w') as csvfile:
            writer = csv.writer(csvfile)

            writer.writerow(['Name'] +
                            ['Week '+str(w) for w in range(schedulingModel.n_weeks)])

            for r_idx,r in enumerate(residents):
                line = [r.name]
                for t in range(schedulingModel.n_weeks):
                    service_idxs = []
                    for s_idx in range(len(services)):
                        if attr_schedule[(r_idx, s_idx,t)] > 0.5:
                            service_idxs.append(s_idx)
                    assert len(service_idxs)==1

                    line.append(services[service_idxs[0]].name)

                writer.writerow(line)