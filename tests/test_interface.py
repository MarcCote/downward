import os
import unittest
from os.path import join as pjoin

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

    def test_load_lib(self):
        # Loading the library a second time should make a copy.
        lib = fast_downward.load_lib()
        lib.load_sas(self.sas.encode('utf-8'))

        assert lib._handle != self.lib._handle
        assert lib.check_goal() is False
        assert self.lib.check_goal() is False

        WALKTHROUGH = ['open p d_0', 'go-east p r_0 r_1', 'inventory p', 'examine p c_0']
        for cmd in WALKTHROUGH:
            operator_count = lib.get_applicable_operators_count()
            operators = (Operator * operator_count)()
            lib.get_applicable_operators(operators)
            operators = {op.name: op for op in operators}
            op = operators[cmd]

            effects = (Atom * op.nb_effect_atoms)()
            lib.apply_operator(op.id, effects)

        assert lib.check_goal() is True
        assert self.lib.check_goal() is False

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

    def test_restoring_state(self):
        operator_count = self.lib.get_applicable_operators_count()
        operators = (Operator * operator_count)()
        self.lib.get_applicable_operators(operators)
        operators = {int(op.id): op for op in operators}
        op = operators[2]
        assert op.name == "drop p r_0 t_0"

        # Get state ID
        state_id = self.lib.get_state_id()

        effects = (Atom * op.nb_effect_atoms)()
        self.lib.apply_operator(op.id, effects)
        EXPECTED = ['Atom at(t_0, r_0)', 'NegatedAtom in(t_0, p)']
        assert set(map(str, effects)) == set(EXPECTED)

        # New state ID should be different.
        new_state_id = self.lib.get_state_id()
        assert state_id != new_state_id

        # Check state has changed.
        state_size = self.lib.get_state_size()
        atoms = (Atom * state_size)()
        self.lib.get_state(atoms)

        EXPECTED = [
            "Atom at(c_0, r_1)",
            "Atom at(p, r_0)",
            "Atom at(s_0, r_0)",
            "Atom closed(c_0)",
            "Atom closed(d_0)",
            "NegatedAtom in(t_0, p)",
            "Atom reachable(p, d_0)",
            "Atom reachable(p, s_0)",
            "Atom reachable(p, t_0)",
            "Atom visible(p, d_0)",
            "Atom visible(p, p)",
            "Atom visible(p, s_0)",
            "Atom visible(p, t_0)"
        ]
        assert set(map(str, atoms)).issuperset(set(EXPECTED))

        # Restore state
        self.lib.set_state_id(state_id)

        # Restored state should have same ID.
        restored_state_id = self.lib.get_state_id()
        assert state_id == restored_state_id

        # Check if state is restored.
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
