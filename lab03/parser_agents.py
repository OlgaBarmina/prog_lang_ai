from itertools import product
from itertools import islice
import heapq
from operator import itemgetter
import pickle


# Domain

class Predicate:
    def __init__(self, name, parameters):
        self.name = name.lower()
        self.parameters = parameters


class Agent:
    def __init__(self, name, weight):
        self.name = name.lower()
        self.weight = weight


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
    def __init__(self, name, requirements=None, types=None, predicates=None, actions=None, agents=None):
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
        if agents == None:
            self.agents = []
        else:
            self.agents = agents

    def ground(self, objects):
        """
        Ground all action schemas given a dictionary of objects keyed by type
        """
        grounded_actions = list()
        for action in self.actions:
            agent_list = [x.name for x in self.agents]
            param_lists = [list(objects.keys()) for i in range(len(action.parameters.values()))]
            param_combos = set()
            for params in product(agent_list, product(*param_lists)):
                param_combos.add(params)
                a = action.ground(*params)
                grounded_actions.append(a)
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
        elif key == "agents":
            for agent, w in attr.items():
                a = Agent(agent, w)
                domain.agents.append(a)
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
                for ob, w in obj.items():
                    # o = Object(ob, type_)
                    problem.objects[ob] = w
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
    args = tuple([args[0]]) + args[1]
    namemap = dict()
    for arg_name, arg in zip(arg_names, args[1:]):
        namemap[arg_name] = arg

    def _ground_by_names(predicate):
        if predicate[1] in namemap.keys():
            out = [namemap.get(arg, arg) for arg in predicate]  # ['ontable', ('a2', ('B',))]
            return (predicate,) + tuple((args[0], out))

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
            if gr_precon is not None:
                precon = (gr_precon[2][0], gr_precon[1], gr_precon[2][1], gr_precon[2][2]) if len(pre[1]) == 2 \
                    else (gr_precon[2][0], gr_precon[1], gr_precon[2][1])
                self.precondition.append(precon)

        # Ground Effects
        self.effects = list()
        for effect in action.effect.items():
            gr_action = ground((effect[0],) + tuple(effect[1]))
            if gr_action is not None:
                eff = (gr_action[2][0], gr_action[1], gr_action[2][1], gr_action[2][2]) if len(effect[1]) == 2 \
                    else (gr_action[2][0], gr_action[1], gr_action[2][1])
                self.effects.append(eff)

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
        act_precon = set(tuple(v for i, v in enumerate(x) if i != 1) for x in action.precondition)
        act_eff = set(tuple(v for i, v in enumerate(x) if i != 1) for x in action.effects)
        cur_state = set(tuple(v for i, v in enumerate(x) if i != 1) for x in cur_state)
        new_preds = set(cur_state)
        new_preds -= set(act_precon)
        new_preds |= set(act_eff) - set(act_precon)
        new_preds = set([x[:1] + (action.precondition[0][1],) + x[1:] for x in new_preds])
        return frozenset(new_preds)

    def gettable(self, cur_state, action):
        act = set(action.precondition)
        tmp_act = set(tuple(v for i, v in enumerate(x) if i != 1) for x in act)
        cur_state = set(tuple(v for i, v in enumerate(x) if i != 1) for x in cur_state)
        preds = set(cur_state)
        agents = dict([tuple((x.name, x.weight[0])) for x in self.domain.agents])  # [('a1', 50), ('a2', 100)]
        objects = dict(
            [tuple((x, y[0])) for x, y in self.problem.objects.items()])  # [('D', 10), ('B', 60), ('A', 30), ('C', 70)]
        for p in act:  # ('ontable', 'a1', 'D')
            if agents.get(p[1]) <= objects.get(p[2]):
                return False
        for a in tmp_act:
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

    def heuristic(self, states, goal):
        h_states = set()
        for state in states:
            st = [tuple(v for i, v in enumerate(x) if i != 1) for x in state]
            c = 0
            for pred in st:
                if pred in goal:
                    c += 1
            h_states.add((state, c))
        return h_states

    def astar_planner(self, save=False, state=None, visited=None, queue=None):
        if state == None:
            state = (self.problem.initial_state, 0)
        if visited == None:
            visited = list()
        if queue == None:
            queue = list()

        if not isinstance(state[0], frozenset):
            state = [set((st.name, param[0], param[1]) if isinstance(st.parameters[0], list) else (st.name, param)
                         for st in state[0] for param in st.parameters), state[1]]
        if not isinstance(self.problem.goal, frozenset):
            goal_state = set((st.name, param[0], param[1]) if isinstance(st.parameters[0], list) else (st.name, param)
                             for st in self.problem.goal for param in st.parameters)

        state = (frozenset(st[:1] + ('Null',) + st[1:] for st in state[0]), 0)
        print("Init state:\n", list(state))
        print("Goal state:\n", list(goal_state))
        print()

        queue.append(state)
        plan = dict()
        plan[state] = None
        agents = dict()

        while queue:
            cur_state = queue.pop(0)
            strip_state = (frozenset(tuple(v for i, v in enumerate(x) if i != 1) for x in cur_state[0]), cur_state[1])

            if equal(cur_state[0], goal_state):
                print("Plan:")
                path = plan[cur_state]
                full_path = list([(goal_state, 0)])
                while path != None:
                    full_path.append(list(path))
                    path = plan[path]
                full_path = list(reversed(full_path))
                for i in full_path:
                    j = i[:1] + i[1:]
                    ag = list(i[0])[0][1]
                    if i[0] == goal_state:
                        ag = 'a1'
                    print("AGENT - ", ag)
                    print("STATE - ", j)
                    print()
                if save:
                    with open('plan.pkl', 'wb') as f:
                        pickle.dump(plan, f)
                return 0

            if strip_state not in visited:
                visited.append(strip_state)
                actions = list(self.get_state(cur_state[0], action) for action in self.grounded_actions
                               if self.gettable(cur_state[0], action))
                actions = self.heuristic(actions, goal_state)
                actions = sorted(actions, key=itemgetter(1), reverse=True)
                # print(actions,'\n')
                for act in actions:
                    strip_act = (frozenset(tuple(v for i, v in enumerate(x) if i != 1) for x in act[0]), act[1])
                    if strip_act not in visited:
                        queue.append(act)
                        plan[act] = cur_state
        return print("no solution")


def equal(st1, st2):
    st1 = set(tuple(v for i, v in enumerate(x) if i != 1) for x in st1)
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
    parse_dom.astar_planner()

# [i.__str__() for i in parse_dom.grounded_actions]