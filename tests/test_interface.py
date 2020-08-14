import os
import unittest
from os.path import join as pjoin
from pprint import pprint
import hashlib

import numpy as np

import fast_downward
from fast_downward import Atom, Operator


DATA_PATH = os.path.abspath(pjoin(__file__, '..', "data"))


class TestInterface(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.lib = fast_downward.load_lib()

        cls.domain = open(pjoin(DATA_PATH, "domain.pddl")).read()
        cls.problem = open(pjoin(DATA_PATH, "problem.pddl")).read()
        cls.task, cls.sas = fast_downward.pddl2sas(cls.domain, cls.problem)

    @classmethod
    def tearDownClass(cls):
        fast_downward.close_lib(cls.lib)

    def setUp(self):
        self.lib.load_sas(self.sas.encode('utf-8'))

    def test_pddl2sas(self):
        EXPECTED = [
            "look",
            "inventory",
            "examine",
            "close",
            "open",
            "insert",
            "put",
            "drop",
            "take",
            "eat",
            "go-east",
            "go-north",
            "go-south",
            "go-west",
            "lock",
            "unlock"
        ]
        actions = [a.name for a in self.task.actions]
        assert set(actions) == set(EXPECTED)

        EXPECTED = [
            "is_door",
            "is_room",
            "is_container",
            "is_supporter",
            "is_player",
            "open",
            "closed",
            "locked",
            "unlocked",
            "eaten",
            "examined",
            "openable",
            "closable",
            "lockable",
            "unlockable",
            "portable",
            "moveable",
            "edible",
            "visible",
            "reachable",
            "at",
            "in",
            "on",
            "free",
            "link",
            "match",
            "north_of",
            "north_of-d",
            "west_of",
            "east_of",
            "west_of-d"
        ]
        predicates = [a.name for a in self.task.predicates]
        assert set(predicates).issuperset(set(EXPECTED))

    def test_get_state(self):
        state_size = self.lib.get_state_size()
        atoms = (Atom * state_size)()
        self.lib.get_state(atoms)

        EXPECTED = [
            "Atom at(c_0, r_1)",
            "Atom at(p, r_0)",
            "Atom at(s_0, r_0)",
            "Atom closed(c_0)",
            "Atom closed(d_0)",
            "Atom in(t_0, p)",
            "Atom reachable(p, d_0)",
            "Atom reachable(p, s_0)",
            "Atom reachable(p, t_0)",
            "Atom visible(p, d_0)",
            "Atom visible(p, p)",
            "Atom visible(p, s_0)",
            "Atom visible(p, t_0)"
        ]
        assert set(map(str, atoms)).issuperset(set(EXPECTED))

    def test_get_applicable_operators(self):
        operator_count = self.lib.get_applicable_operators_count()
        operators = (Operator * operator_count)()
        self.lib.get_applicable_operators(operators)
        operators = {int(op.id): op.name for op in operators}
        #pprint(operators)
        EXPECTED = [
            "drop p r_0 t_0",
            "examine p d_0",
            "examine p p",
            "examine p s_0",
            "examine p t_0",
            "inventory p",
            "look p r_0",
            "open p d_0",
            "put p s_0 t_0"
        ]
        assert set(map(str, operators.values())) == set(EXPECTED)

    def test_apply_operator(self):
        operator_count = self.lib.get_applicable_operators_count()
        operators = (Operator * operator_count)()
        self.lib.get_applicable_operators(operators)
        operators = {int(op.id): op for op in operators}
        # pprint(operators)
        op = operators[2]
        assert op.name == "drop p r_0 t_0"

        effects = (Atom * op.nb_effect_atoms)()
        self.lib.apply_operator(op.id, effects)
        # pprint(list(sorted(map(str, effects))))
        EXPECTED = ['Atom at(t_0, r_0)', 'NegatedAtom in(t_0, p)']
        assert set(map(str, effects)) == set(EXPECTED)

    def test_check_goal(self):
        WALKTHROUGH = [16, 9, 15, 4, 6]
        for op_id in WALKTHROUGH:
            assert not self.lib.check_goal()

            operator_count = self.lib.get_applicable_operators_count()
            operators = (Operator * operator_count)()
            self.lib.get_applicable_operators(operators)
            operators = {int(op.id): op for op in operators}
            op = operators[op_id]

            effects = (Atom * op.nb_effect_atoms)()
            self.lib.apply_operator(op.id, effects)

        assert self.lib.check_goal()

    def test_solve(self):
        WALKTHROUGH = ['open p d_0', 'go-east p r_0 r_1', 'inventory p', 'examine p c_0']
        for cmd in WALKTHROUGH:
            assert self.lib.solve(False)
            operators = (Operator * self.lib.get_last_plan_length())()
            self.lib.get_last_plan(operators)
            operators = [op.name for op in operators]

            operator_count = self.lib.get_applicable_operators_count()
            operators = (Operator * operator_count)()
            self.lib.get_applicable_operators(operators)
            operators = {op.name: op for op in operators}
            op = operators[cmd]

            effects = (Atom * op.nb_effect_atoms)()
            self.lib.apply_operator(op.id, effects)

            state_size = self.lib.get_state_size()
            atoms = (Atom * state_size)()
            self.lib.get_state(atoms)

        assert self.lib.solve(False)

    def test_replan(self):
        _, sas = fast_downward.pddl2sas(self.domain, self.problem, optimize=True)


        # state_size = self.lib.get_state_size()
        # atoms = (Atom * state_size)()
        # self.lib.get_state(atoms)

        # self.lib.load_sas(sas.encode("utf-8"))
        # state_size = self.lib.get_state_size()
        # atoms2 = (Atom * state_size)()
        # self.lib.get_state(atoms2)

        # from ipdb import set_trace; set_trace()


        self.lib.load_sas_replan(sas.encode("utf-8"))


        WALKTHROUGH = ['open p d_0', 'go-east p r_0 r_1', 'inventory p', 'examine p c_0']
        for cmd in WALKTHROUGH:
            assert self.lib.replan(False)
            operators = (Operator * self.lib.get_last_plan_length())()
            self.lib.get_last_plan(operators)
            operators = [op.name for op in operators]
            # pprint(operators)

            operator_count = self.lib.get_applicable_operators_count()
            operators = (Operator * operator_count)()
            self.lib.get_applicable_operators(operators)
            operators = {op.name: op for op in operators}
            # pprint(sorted(operators))
            op = operators[cmd]

            effects = (Atom * op.nb_effect_atoms)()
            self.lib.apply_operator(op.id, effects)

        assert self.lib.replan(False)


def test_solve_pddl():
    domain = open(pjoin(DATA_PATH, "domain.pddl")).read()
    problem = open(pjoin(DATA_PATH, "problem.pddl")).read()
    EXPECTED = ['inventory p', 'open p d_0', 'go-east p r_0 r_1', 'examine p c_0']
    operators = fast_downward.solve_pddl(domain, problem, verbose=False)
    assert operators == EXPECTED

    # Test calling a second to make sure global variables have been taken care of.
    operators = fast_downward.solve_pddl(domain, problem, verbose=False)
    assert operators == EXPECTED


def _demangle_alfred_name(text):
    def _demangle(text):
        text = text.replace("_bar_", "|")
        text = text.replace("_minus_", "-")
        text = text.replace("_plus_", "+")
        text = text.replace("_dot_", ".")
        text = text.replace("_comma_", ",")

        splits = text.split("|", 1)
        if len(splits) == 1:
            return text

        # splits = text.split("_", 1)
        # if len(splits) == 1:
        #     return text

        name, rest = splits
        m = hashlib.md5()
        m.update(rest.encode("utf-8"))
        res = "{}_{}".format(name, m.hexdigest()[:6])
        return res

    return " ".join(map(_demangle, text.split(" ")))


def test_replanning_in_alfred():
    domain = open(pjoin(DATA_PATH, "alfred_domain.pddl")).read()
    problem = open(pjoin(DATA_PATH, "alfred_problem.pddl")).read()

    _, sas = fast_downward.pddl2sas(domain, problem, optimize=False)
    _, sas_replan = fast_downward.pddl2sas(domain, problem, optimize=True)

    def _get_plan():
        operators = (Operator * lib.get_last_plan_length())()
        lib.get_last_plan(operators)
        return [op.name for op in operators], operators

    lib = fast_downward.load_lib()

    # Following the walkthrough.
    lib.load_sas(sas.encode('utf-8'))
    lib.load_sas_replan(sas_replan.encode('utf-8'))

    assert lib.solve(False)
    plan, plan_operators = _get_plan()
    # print("\n".join(map(_demangle_alfred_name, plan)))

    for cmd in plan:
        assert lib.solve(False)
        slow_replan, plan_operators = _get_plan()
        assert lib.replan(False)
        fast_replan, _ = _get_plan()
        assert slow_replan == fast_replan, (slow_replan, fast_replan)
        # print(_demangle_alfred_name(cmd))
        # print("\t","\n\t".join(map(_demangle_alfred_name, fast_replan)))
        assert lib.check_solution(len(plan_operators), plan_operators)

        operator_count = lib.get_applicable_operators_count()
        operators = (Operator * operator_count)()
        lib.get_applicable_operators(operators)
        operators = {op.name: op for op in operators}
        # pprint(sorted(operators))
        op = operators[cmd]

        effects = (Atom * op.nb_effect_atoms)()
        lib.apply_operator(op.id, effects)

    assert lib.check_goal()

    # Taking random commands.
    lib.load_sas(sas.encode('utf-8'))
    lib.load_sas_replan(sas_replan.encode('utf-8'))

    assert lib.solve(False)
    _, solution = _get_plan()
    # print("Solution:\n -> " +"\n -> ".join(_demangle_alfred_name(op.name) for op in solution))

    solution = fast_downward.compress_plan(lib, solution)
    # print("\n\nSolution:\n -> " +"\n -> ".join(_demangle_alfred_name(op.name) for op in solution))

    history = []
    rng = np.random.RandomState(123)
    for _ in range(10):
        operator_count = lib.get_applicable_operators_count()
        operators = (Operator * operator_count)()
        lib.get_applicable_operators(operators)
        operators = {op.name: op for op in operators}
        # print("\n".join(sorted(map(_demangle_alfred_name, operators))))
        cmd = rng.choice(list(operators))
        # print(_demangle_alfred_name(cmd))
        op = operators[cmd]
        history.append(cmd)

        effects = (Atom * op.nb_effect_atoms)()
        lib.apply_operator(op.id, effects)

        # assert lib.solve(False)
        # slow_replan = _get_plan()
        solution = fast_downward.compress_plan(lib, solution)
        # print("\n\nSolution:\n -> " +"\n -> ".join(_demangle_alfred_name(op.name) for op in solution))

        assert lib.replan(False)
        fast_replan, _ = _get_plan()
        # assert slow_replan == fast_replan, (slow_replan, fast_replan)
        check_plan(sas, history + fast_replan)

    #assert lib.check_goal()

def check_plan(sas, plan):
    lib = fast_downward.load_lib()
    lib.load_sas(sas.encode('utf-8'))

    for cmd in plan:
        operator_count = lib.get_applicable_operators_count()
        operators = (Operator * operator_count)()
        lib.get_applicable_operators(operators)
        operators = {op.name: op for op in operators}
        # print("\t" + _demangle_alfred_name(cmd))
        # print("\tOperators:")
        # print("\t\t" + "\n\t\t".join(sorted(map(_demangle_alfred_name, operators))))
        op = operators[cmd]

        effects = (Atom * op.nb_effect_atoms)()
        lib.apply_operator(op.id, effects)

    assert lib.check_goal()


if __name__ == "__main__":
    test_replanning_in_alfred()

    # TestInterface.setUpClass()
    # case = TestInterface()
    # case.setUp()
    # case.test_replan()
