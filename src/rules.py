import gurobipy as gb
from gurobipy import GRB
from .model import schedulingModel

class RuleException(Exception):
    """Raise for exceptions encountered when applying a rule"""

class Rule:
    count = 0
    def __init__(self, name):
        self.name = "R"+str(Rule.count)+"_"+name
        ++Rule.count
    def addRuleToModel(self, scheduler, residents, services):
        pass
    def getServiceIndex(self, service_name, services):
        service_idx = -1
        for i, s in enumerate(services):
            if s.name == service_name:
                service_idx = i
                break

        if service_idx == -1:
            raise RuleException("Service: "+self.service_name+
                                " not found in list of services")
        
        return service_idx
    def getResidentIndices(self, who, residents):
        if who == "everyone":
            return range(len(residents))
        elif who == "AP1" or who == "AP2":
            return [ pair[0] for pair in enumerate(residents) if pair[1].year == who ]
        else:
            resident_idx = -1
            for i, r, in enumerate(residents):
                if r.name == who:
                    resident_idx = i
                    break

            if resident_idx == -1:
                raise RuleException("Resident: "+self.who+
                                    " not found in list of residents")

            return [resident_idx]


class doBefore(Rule):
    def __init__(self,week_id,service_name, who):
        super().__init__("do_before")
        self.week_id = week_id
        self.service_name = service_name
        self.who          = who

    def addRuleToModel(self, scheduler, residents, services):
        s_idx = super().getServiceIndex(self.service_name, services)
        r_indices = super().getResidentIndices(self.who, residents)

        s = scheduler.schedule
        m = scheduler.model
        
        m.addConstrs((gb.quicksum(s[r,s_idx,t]
                                  for t in range(self.week_id, schedulingModel.n_weeks))
                      == 0 for r in r_indices),
                     self.name)

class doAfter(Rule):
    def __init__(self,week_id,service_name,who):
        super().__init__("do_after")
        self.week_id      = week_id
        self.service_name = service_name
        self.who          = who

    def addRuleToModel(self, scheduler, residents, services):
        s_idx = super().getServiceIndex(self.service_name, services)
        r_indices = super().getResidentIndices(self.who, residents)

        s = scheduler.schedule
        m = scheduler.model
        
        m.addConstrs((gb.quicksum(s[r,s_idx,t]
                                  for t in range(self.week_id))
                      == 0 for r in r_indices),
                     self.name)

'''
class inBlocks(Rule):
    def __init__(self,name, block_size, service_name):
        super(Rule, self).__init__(name)
        self.block_size = block_size
        self.service_name = service_name
    def addRuleToModel(self, model, schedule, residents, services):
        service_idx = -1
        for i, s in enumerate(services):
            if s.name == self.service_name:
                service_idx = i
                break

        if service_idx == -1:
            raise RuleException("Service: "+self.service_name+
                                " not found in list of services")

        #need to add rule here
'''
class upperBound(Rule):
    def __init__(self, service_name, count):
        super().__init__("upperBound")
        self.service_name = service_name
        self.count   = int(count)
    def addRuleToModel(self, scheduler, residents, services):
        s_idx = super().getServiceIndex(self.service_name, services)

        scheduler.model.addConstrs(
            (scheduler.schedule.sum(r,s_idx,'*') <= self.count
             for r in range(len(residents))),
             name=self.name)

class singleBlock(Rule):
    def __init__(self, service_name):
        super().__init__(service_name+"singleBlock")
        self.service_name = service_name
    def addRuleToModel(self, scheduler, residents, services):
        s_idx = super().getServiceIndex(self.service_name, services)

        m  = scheduler.model
        s  = scheduler.schedule

        for r_idx in range(len(residents)):
            r = residents[r_idx]
            service_lb = r.service_lbs[self.service_name]
            
            if service_lb == 0:
                continue
            
            start = m.addVars(
                schedulingModel.n_weeks-service_lb,
                vtype = GRB.BINARY,
                name = r.name+'_'+self.service_name+'_start')


            m.addConstr(start.sum('*') == 1, name="start_once_"+self.name+"_"+r.name)

            m.addConstrs((gb.quicksum(s[r_idx,s_idx,tt] for tt in range(t,t+service_lb))
                          >= service_lb * start[t] for t in range(schedulingModel.n_weeks-service_lb)),
                         name=self.name)
            

            

def RuleFactory(rule_type):
    assert len(rule_type.keys())==1
    name = next(iter(rule_type.keys()))
    arg_dict = rule_type[name]

    if "who" not in arg_dict:
        arg_dict["who"] = "everyone"
        
    if name == "do_before":
        assert "week" in arg_dict
        assert "service" in arg_dict
        return doBefore(arg_dict["week"],
                        arg_dict["service"],
                        arg_dict["who"])
    elif name == "do_after":
        assert "week" in arg_dict
        assert "service" in arg_dict
        return doAfter(arg_dict["week"],
                       arg_dict["service"],
                       arg_dict["who"])
    elif name == "in_blocks":
        assert "block_size" in arg_dict
        assert "service" in arg_dict
        return inBlocks(arg_dict["name"],
                        arg_dict["block_size"],
                        arg_dict["service"])
    elif name == "upper_bound":
        assert "service" in arg_dict
        assert "count"   in arg_dict
        return upperBound(arg_dict["service"],
                          arg_dict["count"])
    elif name == "single_block":
        assert "service" in arg_dict
        return singleBlock(arg_dict["service"])           