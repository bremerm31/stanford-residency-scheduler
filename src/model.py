import gurobipy as gb
from gurobipy import GRB

from .inputs import Resident, ClinicalService

class schedulingModel:
    def __init__(self, residents, services):
        hardness_interval = 6
        hardness_weight_ratio = 0.5
        
        n_weeks = 52
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
            self.model.setParam('BestObjStop', 0.05)
            self.model.setParam('MIPFocus', 1)
            self.model.setParam('Threads', 2)
            self.model.setParam('Presolve', 2)
            self.model.optimize()

        except gb.GurobiError as e:
            print('Error code '+str(e.errno) + ": "+str(e))

    def performIISAnalysis(self):
        self.model.computeIIS()

        for c in self.model.getConstrs():
            if c.IISConstr:
                print('%s' % c.ConstrName)
