from itertools import product
import heapq


# Domain

class Predicate:
    def __init__(self, name, parameters):
        self.name = name.lower()
        self.parameters = parameters


# class Object:
#    def __init__(self, name, typeName):
#        self.name = name.lower()
#        self.typeName = typeName

class Action:
    def __init__(self, name, param, unique=False):
        self.name = name.lower()
        params = dict()
        for i, j in param["parameters"].items():
            for k in j:
                params[k] = i
        self.parameters = params
        self.precondition = param["precondition"]
        self.effect = param["effect"]
        self.unique = unique

    def ground(self, *args):
        return _GroundedAction(self, *args)


class Domain:
    def __init__(self, name, requirements=None, types=None, predicates=None, actions=None):
        self.name = name.lower()
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

    def ground(self, objects):
        """
        Ground all action schemas given a dictionary of objects keyed by type
        """
        grounded_actions = list()
        for action in self.actions:
            param_lists = [list(objects.keys()) for i in range(len(action.parameters.values()))]
            param_combos = set()
            for params in product(*param_lists):
                param_combos.add(params)
                grounded_actions.append(action.ground(*params))
        return grounded_actions


def parse_domain_def(dom_dict):
    name = dom_dict["domain"]
    domain = Domain(name)

    for key, attr in dom_dict.items():
        if key == "types":
            domain.types = attr
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

class Problem:
    def __init__(self, name, objects=None, init=None, goal=None):
        self.name = name
        if objects == None:
            self.objects = dict()
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
    for key, attr in prob_dict.items():
        if key == "objects":
            for type_, obj in attr.items():
                for ob in obj:
                    # o = Object(ob, type_)
                    problem.objects[ob] = type_
        elif key == "init":
            p = []
            for pred, d in attr.items():
                pr = Predicate(pred, d)
                p.append(pr)
            problem.initial_state = p
        elif key == "goal":
            p = []
            for pred, d in attr.items():
                pr = Predicate(pred, d)
                p.append(pr)
            problem.goal = p
            break
    return problem


def _grounder(arg_names, args):
    """
    Function for grounding predicates and function symbols
    """
    namemap = dict()
    for arg_name, arg in zip(arg_names, args):
        namemap[arg_name] = arg

    def _ground_by_names(predicate):
        return (predicate,) + tuple(namemap.get(arg, arg) for arg in predicate)

    return _ground_by_names


class _GroundedAction(object):
    """
    An action schema that has been grounded with objects
    """

    def __init__(self, action, *args):
        self.name = action.name
        ground = _grounder(tuple(list(action.parameters.keys())), args)  # arg names = xyz

        # Ground Action Signature
        self.sig = ground((self.name,) + tuple(action.parameters))

        # Ground Preconditions
        self.precondition = list()
        self.num_precondition = list()

        for pre in action.precondition.items():
            gr_precon = ground((pre[0],) + tuple(pre[1]))
            self.precondition.append((gr_precon[1], gr_precon[2], gr_precon[3]) if len(pre[1]) == 2
                                     else (gr_precon[1], gr_precon[2]))

        # Ground Effects
        self.effects = list()
        flag1 = False
        flag2 = False
        for effect in action.effect.items():
            gr_action = ground((effect[0],) + tuple(effect[1]))
            self.effects.append((gr_action[1], gr_action[2], gr_action[3]) if len(effect[1]) == 2
                                else (gr_action[1], gr_action[2]))

    def __str__(self):
        arglist = ', '.join(map(str, self.sig[1:]))
        return '(%s)' % (arglist)


# Parser
class Parser:
    def __init__(self, domFile, probFile):
        self.domFile = domFile
        self.probFile = probFile
        self.domInput = {}
        self.probInput = {}
        self.domain = None
        self.problem = None

    def get_state(self, cur_state, action):
        new_preds = set(cur_state)
        new_preds -= set(action.precondition)
        new_preds |= set(action.effects) - set(action.precondition)
        return frozenset(new_preds)

    def gettable(self, cur_state, action):
        act = set(action.precondition)
        preds = set(cur_state)
        for a in act:
            if a not in preds:
                return False
        return True

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
        self.grounded_actions = self.domain.ground(self.problem.objects)

    def bfs_planner(self, state=None, visited=None, queue=None):
        if state == None:
            state = self.problem.initial_state
        if visited == None:
            visited = list()
        if queue == None:
            queue = list()

        if not isinstance(state, frozenset):
            state = frozenset((st.name, param[0], param[1]) if isinstance(st.parameters[0], list) else (st.name, param)
                              for st in state for param in st.parameters)
        if not isinstance(self.problem.goal, frozenset):
            goal_state = set((st.name, param[0], param[1]) if isinstance(st.parameters[0], list) else (st.name, param)
                             for st in self.problem.goal for param in st.parameters)
        print("init state: ", state)
        print("goal state: ", goal_state)

        queue.append(state)
        """
        create a plan by dict (new_state: cur state), go back to create a list
        """
        while queue:
            cur_state = queue.pop(0)

            if equal(cur_state, goal_state):
                # print plan
                return print("solution found")

            if cur_state not in visited:
                visited.append(cur_state)
                actions = set(self.get_state(cur_state, action) for action in self.grounded_actions
                              if self.gettable(cur_state, action))
                for act in actions:
                    if act not in visited:
                        queue.append(act)
        return print("no solution")


def equal(st1, st2):
    if len(st1) != len(st2):
        return False
    for pred in st1:
        if pred not in st2:
            return False
    return True


if __name__ == "__main__":
    import json

    json_dom = 'domain.json'
    json_prob = 'task01.json'

    parse_dom = Parser(json_dom, json_prob)
    parse_dom.parse_domain()
    parse_dom.parse_problem()
    parse_dom.bfs_planner()

# [i.__str__() for i in parse_dom.grounded_actions]