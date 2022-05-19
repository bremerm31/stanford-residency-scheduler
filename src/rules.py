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

class inBlocks(Rule):
    def __init__(self, block_size, service_name, who):
        super().__init__("in"+str(block_size)+"WeekBlocks_"+service_name)
        self.block_size = block_size
        self.service_name = service_name
        self.who = who
    def addRuleToModel(self, scheduler, residents, services):
        s_idx = super().getServiceIndex(self.service_name, services)
        r_indices = super().getResidentIndices(self.who, residents)

        s = scheduler.schedule
        m = scheduler.model

        for r_idx in r_indices:
            r = residents[r_idx]
            service_lb = r.service_lbs[self.service_name]
            
            if service_lb == 0:
                continue
            
            start = m.addVars(
                schedulingModel.n_weeks-self.block_size,
                vtype = GRB.BINARY,
                name = r.name+'_'+self.service_name+'_start')

            n_starts = service_lb // self.block_size
            assert n_starts * self.block_size == service_lb

            m.addConstr(start.sum('*') == n_starts, name="n_starts_"+self.name+"_"+r.name)

            # require contiguous blocks of block_size 
            m.addConstrs((gb.quicksum(s[r_idx,s_idx,tt] for tt in range(t,t+self.block_size))
                          >= self.block_size * start[t] for t in range(schedulingModel.n_weeks-self.block_size)),
                         name=self.name)
            #starts can't double count an interval (i.e. one start per "block_size")
            m.addConstrs((gb.quicksum(start[tt] for tt in range(t,t+self.block_size))
                          <= 1 for t in range(schedulingModel.n_weeks-2*self.block_size)),
                         name=self.name+"_no_block_overlap")

class upperBound(Rule):
    def __init__(self, service_name, count):
        super().__init__("upperBound")
        self.service_name = service_name
        self.count   = count
    def addRuleToModel(self, scheduler, residents, services):
        s_idx = super().getServiceIndex(self.service_name, services)

        if self.count:
            scheduler.model.addConstrs(
                (scheduler.schedule.sum(r,s_idx,'*') <= self.count
                 for r in range(len(residents))),
                name=self.name)
        else:
            scheduler.model.addConstrs(
                (scheduler.schedule.sum(r,s_idx,'*')
                 <= residents[r].service_lbs[self.service_name]
                 for r in range(len(residents))),
                name=self.name)

class singleBlock(Rule):
    def __init__(self, service_name, who):
        super().__init__(service_name+"singleBlock")
        self.service_name = service_name
        self.who = who
    def addRuleToModel(self, scheduler, residents, services):
        s_idx = super().getServiceIndex(self.service_name, services)
        r_indices = super().getResidentIndices(self.who, residents)

        m  = scheduler.model
        s  = scheduler.schedule

        for r_idx in r_indices:
            r = residents[r_idx]
            service_lb = r.service_lbs[self.service_name]
            
            if service_lb == 0:
                continue
            
            start = m.addVar(
                vtype = GRB.INTEGER,
                lb=0, ub=schedulingModel.n_weeks-service_lb,
                name = r.name+'_'+self.service_name+'_start')

            stop = m.addVar(
                vtype=GRB.INTEGER,
                lb=service_lb, ub=schedulingModel.n_weeks,
                name = r.name+'_'+self.service_name+'_stop')

            m.addConstr(stop - start == s.sum(r_idx, s_idx,'*'),
                         name=self.name)

class sequence(Rule):
    def __init__(self, first_service, second_service, who):
        super().__init__("sequence")
        self.first_service = first_service
        self.second_service = second_service
        self.who = who
    def addRuleToModel(self, scheduler, residents, services):
        s_first_idx = super().getServiceIndex(self.first_service, services)
        s_second_idx = super().getServiceIndex(self.second_service, services)
        r_indices = super().getResidentIndices(self.who, residents)

        m  = scheduler.model
        s  = scheduler.schedule

        m.addConstrs((s[r_idx,s_first_idx,t] == s[r_idx,s_second_idx,t+1]
                      for r_idx in r_indices
                      for t in range(schedulingModel.n_weeks-1)),
                      name=self.name)
        
class specify(Rule):
    def __init__(self, service, weeks, who):
        super().__init__("specify")
        self.service = service
        if type(weeks) == int:
            weeks = [weeks]
        self.weeks = weeks
        self.who = who
    def addRuleToModel(self, scheduler, residents, services):
        s_idx = super().getServiceIndex(self.service, services)
        r_indices = super().getResidentIndices(self.who, residents)

        m  = scheduler.model
        s  = scheduler.schedule

        for r_idx in r_indices:
            m.addConstrs((s[r_idx,s_idx,w-2] == 1
                          for r_idx in r_indices
                          for w in self.weeks),
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
        return inBlocks(arg_dict["block_size"],
                        arg_dict["service"],
                        arg_dict["who"])
    elif name == "upper_bound":
        assert "service" in arg_dict
        if "count" not in arg_dict:
            arg_dict["count"] = None
        return upperBound(arg_dict["service"],
                          arg_dict["count"])
    elif name == "single_block":
        assert "service" in arg_dict
        return singleBlock(arg_dict["service"],
                           arg_dict["who"])
    elif name == "sequence":
        assert "first" in arg_dict
        assert "second" in arg_dict
        return sequence(arg_dict["first"],
                        arg_dict["second"],
                        arg_dict["who"])
    elif name == "specify":
        assert "service" in arg_dict
        assert "week"    in arg_dict
        assert "who"     in arg_dict
        return specify(arg_dict["service"],
                       arg_dict["week"],
                       arg_dict["who"])

def addVacation(rules_list, residents):
    for r in residents:
        week_input = [ w+2 for w in r.vacation_weeks ]
        rules_list.append(specify("Vacation",
                                  week_input,
                                  r.name))

def addConferenceWeek(rules_list, residents, conference_week):
    for r in residents:
        if r.service_lbs["Conference"] > 0:
            rules_list.append(specify("Conference",
                                      conference_week,
                                      r.name))