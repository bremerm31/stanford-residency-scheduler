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

'''
class doBefore(Rule):
    def __init__(self,week_id,service_name):
        super(Rule,self).__init__("do_before")
        self.week = week
        self.service_name = service_name

    def addRuleToModel(self, model, schedule, residents, services):
        service_idx = -1
        for i, s in enumerate(services):
            if s.name == self.service_name:
                service_idx = i
                break

        model.addConstrs((gb.quicksum(schedule[r,service_idx,t]
                                      for t in range(week, n_weeks))
                          == 0) for r in range(len(residents)),
                         self.name)

class doAfter(Rule):
    def __init__(self,week_id,service_name):
        super(Rule,self).__init__("do_after")
        self.week = week
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

        model.addConstrs((gb.quicksum(schedule[r,service_idx,t]
                                      for t in range(week))
                          == 0) for r in range(len(residents)),
                         name=self.name)

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
        
    if name == "do_before":
        assert "week" in arg_dict
        assert "service" in arg_dict
        return doBefore(name,
                        arg_dict["week"],
                        arg_dict["service"])
    elif name == "do_after":
        assert "week" in arg_dict
        assert "service" in arg_dict
        return doAfter(arg_dict["name"],
                       arg_dict["week"],
                       arg_dict["service"])
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