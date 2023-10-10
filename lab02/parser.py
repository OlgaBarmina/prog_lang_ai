# Domain
class Type:
    def __init__(self, name):
        self.name = name.lower()

class Predicate:
    def __init__(self, name, parameters):
        self.name = name
        self.parameters = parameters

class Object:
    def __init__(self, name, typeName):
        self.name = name.lower()
        self.typeName = Type(typeName)

class Action:
    def __init__(self, name, param):
        self.name = name
        #self.parameters = param["parameters"]
        params = []
        print(param["parameters"])
        for i,j in param["parameters"].items():
            for k in j:
                params.append(Object(k, i))
        self.parameters = params
        self.precondition = param["precondition"]
        self.effect = param["effect"]

class Domain:
    def __init__(self, name, requirements=None, types=None, predicates=None, actions=None):
        self.name = name
        self.requirements = requirements
        self.types = types
        if predicates == None:
            self.predicates = []
        else:
            self.predicates = predicates      
        if actions == None:
            self.actions = []
        else:
            self.actions = actions

def parse_domain_def(dom_dict):
    name = dom_dict["domain"]
    domain = Domain(name)
    
    for key,attr in dom_dict.items():
        if key == "types":
            domain.types = Type(attr)
        elif key == "predicates":
            for pred, d in attr.items():
                p = Predicate(pred, d)
                domain.predicates.append(p)
        elif key == "action":
            for action, d in attr.items():
                a = Action(action, d)
                domain.actions.append(a)
            break
    return domain

# Problem
class InitStmt:
    def __init__(self, predicates):
        self.predicates = predicates

class GoalStmt:
    def __init__(self, predicates):
        self.predicates = predicates

class Problem:
    def __init__(self, name, objects=None, init=None, goal=None):
        self.name = name
        if objects == None:
            self.objects = []
        else:
            self.objects = predicates
        if init == None:
            self.initial_state = []
        else:
            self.initial_state = init
        if goal == None:
            self.goal = []
        else:
            self.goal = goal

def parse_problem_def(prob_dict):
    """Main method to parse a problem definition."""
    name = prob_dict["name"]
    problem = Problem(name)
    for key,attr in prob_dict.items():
        if key == "objects":
            for type_, obj in attr.items():
                for ob in obj:
                    o = Object(ob, type_)
                    problem.objects.append(o)
        elif key == "init":
            p = []
            for pred, d in attr.items():
                pr = Predicate(pred, d)
                p.append(pr)
            problem.init = InitStmt(p)
        elif key == "goal":
            p = []
            for pred, d in attr.items():
                pr = Predicate(pred, d)
                p.append(pr)
            problem.goal = GoalStmt(p)
            break
    return problem

# Parser
class Parser:
    def __init__(self, domFile, probFile):
        self.domFile = domFile
        self.probFile = probFile
        self.domInput = {}
        self.probInput = {}
        self.domain = None
        self.problem = None

    def parse_domain(self):
        f = open(self.domFile)
        self.domInput = json.load(f)

        domain = parse_domain_def(self.domInput)
        self.domain = domain

    def parse_problem(self):
        f = open(self.probFile)
        self.probInput = json.load(f)
                
        problem = parse_problem_def(self.probInput)
        self.problem = problem
    
if __name__ == "__main__":
    import json
    json_dom = 'domain.json'
    json_prob = 'task01.json'
    
    parse_dom = Parser(json_dom, json_prob)
    parse_dom.parse_domain()
    parse_dom.parse_problem()
    
    print(parse_dom.problem.init.predicates[0].name, parse_dom.problem.init.predicates[0].parameters)
    print(parse_dom.problem.goal.predicates[0].name, parse_dom.problem.goal.predicates[0].parameters)
    print(parse_dom.problem.objects[0].typeName.name)
    print(parse_dom.domain.actions[0].parameters[0].name, parse_dom.domain.actions[0].parameters[0].typeName.name)



