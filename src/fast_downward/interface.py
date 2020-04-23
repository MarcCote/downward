# Copyright (C) 2018 Microsoft Corporation

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import os
import shutil
import textwrap
import tempfile
import warnings
import numpy as np
from os.path import join as pjoin

from ctypes import *
from numpy.ctypeslib import as_ctypes
from pkg_resources import Requirement, resource_filename

from pprint import pprint

import textworld
import textworld.logic
from textworld.logic import Proposition, Variable
from textworld.generator.data import KnowledgeBase


DOWNWARD_PATH = resource_filename(Requirement.parse('fast_downward'), 'fast_downward')
DOWNWARD_LIB_PATH = os.path.join(DOWNWARD_PATH, 'libdownward.so')

# Function to unload a shared library.
dlclose_func = CDLL(None).dlclose  # This WON'T work on Win
dlclose_func.argtypes = [c_void_p]


def get_var_name(value):
    if value.lower() in ("i", "p"):
        return value.upper()

    return value

def get_var_type(value):
    if value.lower() in ("i", "p"):
        return value.upper()

    return value[0]


class Operator(Structure):
    """
    An Operator object contains the following fields:

    :param num: Operator ID
    :type num: int
    :param name: Operator name
    :type name: string

    ..warning this class must reflect the C struct in interface.cc.

    """
    _fields_ = [
        ("id", c_int),
        ("_name", c_char*1024),  # Fixed-length name.
        ("nb_effect_atoms", c_int),
    ]

    def __init__(self):
        self.id = -1
        self.nb_effect_atoms = 0
        self._name = ""

    def __str__(self):
        return "Id {}:\t{}".format(self.id, self.name)

    def __repr__(self):
        return str(self)

    @property
    def name(self):
        return self._name.decode('cp1252')


class Atom(Structure):
    """
    An Atom object contains the following fields:

    :param num: Operator ID
    :type num: int
    :param name: Operator name
    :type name: string

    ..warning this class must reflect the C struct in interface.cc.

    """
    _fields_ = [
        ("_name", c_char*1024),  # Fixed-length name.
    ]

    def __init__(self):
        self._name = ""

    def __str__(self):
        return "{}".format(self.name)

    def __repr__(self):
        return str(self)

    @property
    def name(self):
        return self._name.decode('cp1252')

    @property
    def as_fact(self) -> Proposition:
        atom_type, rest = self.name.split(" ", 1)
        name, args = rest.split("(", 1)
        args = args[:-1].split(", ")
        arguments = [Variable(get_var_name(arg), get_var_type(arg)) for arg in args if arg]
        if atom_type == "NegatedAtom":
            name = "not_" + name

        return Proposition(name, arguments)


def load_downward_lib():
    """ Loads a copy of fast-downward's shared library. """

    # Make a copy of libdownward.so before loading it to avoid concurrency issues.
    with tempfile.TemporaryDirectory() as tmpdir:
        downward_lib_path = os.path.join(tmpdir, 'libdownward.so')
        shutil.copyfile(DOWNWARD_LIB_PATH, downward_lib_path)
        print(DOWNWARD_LIB_PATH)
        downward_lib = cdll.LoadLibrary(DOWNWARD_LIB_PATH)

        downward_lib.load_sas.argtypes = [c_char_p]
        downward_lib.load_sas.restype = None

        downward_lib.cleanup.argtypes = []
        downward_lib.cleanup.restype = None

        downward_lib.get_applicable_operators_count.argtypes = []
        downward_lib.get_applicable_operators_count.restype = int
        downward_lib.get_applicable_operators.argtypes = [POINTER(Operator)]
        downward_lib.get_applicable_operators.restype = None

        downward_lib.get_state_size.argtypes = []
        downward_lib.get_state_size.restype = int
        downward_lib.get_state.argtypes = [POINTER(Atom)]
        downward_lib.get_state.restype = None

        downward_lib.apply_operator.argtypes = [c_int, POINTER(Atom)]
        downward_lib.apply_operator.restype = int

    return downward_lib


class State(textworld.logic.State):
    """
    The current state of a world.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.downward_lib = load_downward_lib()
        if list(self.facts):
            self._init_planner()

    def _init_planner(self, domain_filename=None, problem_filename=None):
        with textworld.utils.make_temp_directory() as tmpdir:
            output_filename = pjoin(tmpdir, "output.sas")

            if domain_filename is None:
                domain_filename = pjoin(tmpdir, "domain.sas")
                with open(domain_filename, "w") as f:
                    f.write(self.domain_as_pddl())

            if problem_filename is None:
                problem_filename = pjoin(tmpdir, "problem.pddl")
                with open(problem_filename, "w") as f:
                    f.write(self.as_pddl())

            # TODO: make translate return the string instead of writing to a temp file.
            translate(domain_filename, problem_filename, output_filename)
            with open(output_filename) as f:
                sas = f.read()

            self.downward_lib.load_sas(sas.encode('utf-8'))

    @classmethod
    def from_pddl(cls, domain_filename: str, problem_filename: str) -> "State":
        state = cls(KnowledgeBase.default().logic, [])
        state._init_planner(domain_filename, problem_filename)

        state_size = state.downward_lib.get_state_size()
        atoms = (Atom * state_size)()
        state.downward_lib.get_state(atoms)
        facts = [atom.as_fact for atom in atoms]
        facts = [fact for fact in facts if not fact.is_negation]
        state.add_facts(facts)
        return state

    def as_pddl(self):
        predicate = "({name} {params})"
        problem = textwrap.dedent("""\
        (define (problem textworld-game-1)
            (:domain textworld)
            (:objects {objects})
            (:init {init})
            (:goal
                (and {goal}))
        )
        """)

        def _format_proposition(fact):
            return predicate.format(
                name=fact.name,
                params=" ".join(fact.names)
            )

        problem_pddl = problem.format(
            objects=" ".join(sorted(set("{} - {}".format(arg.name, arg.type) for fact in self.facts for arg in fact.arguments))),
            init=textwrap.indent("\n" + "\n".join(_format_proposition(fact) for fact in self.facts), "        "),
            #goal=textwrap.indent("\n" + "\n".join(_format_proposition(fact) for fact in game.quests[0].win_events[0].condition.preconditions), "            "),
            goal="",
        )

        problem_pddl = problem_pddl.replace("'", "2")  # hack
        problem_pddl = problem_pddl.replace("/", "-")  # hack
        print(problem_pddl)
        return problem_pddl
        # with open("/tmp/textworld/problem.pddl", "w") as f:
        #     f.write(problem_pddl)

    def domain_as_pddl(self):
        domain = textwrap.dedent("""\
        (define (domain textworld)
            (:requirements
            :typing)
            (:types {types})
            (:predicates {predicates})

        {actions}
        )
        """)
        predicate = "({name} {params})"
        action = textwrap.dedent("""\
        (:action {name}
            :parameters ({parameters})
            :precondition
                (and {preconditions})
            :effect
                (and {effects})
        )
        """)

        def _differentiate_type(types):
            seen = []
            for t in types:
                if t in seen:
                    t = t + "2"
                seen.append(t)
            return seen

        def _format_predicate(pred):
            if isinstance(pred, textworld.logic.Signature):
                return predicate.format(
                    name=pred.name,
                    params=" ".join("?{p} - {t}".format(p=p, t=t) for t, p in zip(pred.types, _differentiate_type(pred.types)))
                )

            return predicate.format(
                name=pred.name,
                params=" ".join("?{p}".format(p=n) for n in pred.names)
            )

        def _format_effects(rule):
            text = ""
            text += textwrap.indent("\n" + "\n".join(_format_predicate(p) for p in rule.added), "            ")
            text += textwrap.indent("\n" + "\n".join("(not {})".format(_format_predicate(p)) for p in rule.removed), "            ")
            return text


        predicates = []
        for pred in sorted(self._logic.predicates):
            predicates.append(_format_predicate(pred))

        actions = []
        for k in sorted(self._logic.rules):
            rule = self._logic.rules[k]
            actions.append(
                action.format(
                    name=rule.name,
                    parameters=" ".join("?{p} - {t}".format(p=p.name, t=p.type) for p in rule.placeholders),
                    preconditions=textwrap.indent("\n" + "\n".join(_format_predicate(p) for p in rule.preconditions), "            "),
                    effects=_format_effects(rule),
                )
            )

        domain_pddl = domain.format(
            types=textwrap.indent("\n" + "\n".join(self._logic.types._types), "        "),
            predicates=textwrap.indent("\n" + "\n".join(predicates), "        "),
            actions=textwrap.indent("\n".join(actions), "    "),
        )
        domain_pddl = domain_pddl.replace("'", "2")  # hack
        domain_pddl = domain_pddl.replace("/", "-")  # hack
        print(domain_pddl)
        return domain_pddl
        # with open("/tmp/textworld/domain.pddl", "w") as f:
        #     f.write(domain_pddl)

    def all_applicable_actions(self):
        print("# Count operators")
        operator_count = self.downward_lib.get_applicable_operators_count()
        print("# Count operators - done")

        operators = (Operator * operator_count)()
        print("# Getting operators")
        self.downward_lib.get_applicable_operators(operators)
        print("# Getting operators - done")
        self._operators = {op.id: op for op in operators}
        pprint(self._operators)

    def apply(self, action):
        # TODO: convert textworld.logic.Action into operator id.
        op = self._operators[action]  # HACK: assume action is operator id for now.

        effects = (Atom * op.nb_effect_atoms)()
        self.downward_lib.apply_operator(op.id, effects)
        pprint(list(str(atom.as_fact) for atom in effects))

        # Update facts
        for effect in effects:
            prop = effect.as_fact
            if prop.is_negation:
                self.remove_fact(prop.negate())
            else:
                self.add_fact(prop)

    def print_state(self):
        print("-= STATE =-")
        state_size = self.downward_lib.get_state_size()
        atoms = (Atom * state_size)()
        self.downward_lib.get_state(atoms)
        pprint(list(str(atom.as_fact) for atom in atoms))

    def __del__(self):
        if hasattr(self, "downward_lib"):
            self.downward_lib.cleanup()
            dlclose_func(self.downward_lib._handle)


def translate(domain_filename="domain.pddl", task_filename="problem.pddl", sas_filename="output.sas"):
    # TODO: change translate.py so it's not relying on command line arguments.
    import sys
    sys.argv = ["translate.py", "domain", "task"]

    from fast_downward.translate import pddl_parser
    from fast_downward.translate import normalize
    from fast_downward.translate import options
    from fast_downward.translate import translate

    options.domain = domain_filename
    options.task = task_filename
    options.sas_file = sas_filename
    options.filter_unimportant_vars = False
    # options.skip_variable_reordering = True
    options.filter_unreachable_facts = False
    options.use_partial_encoding = True
    # options.add_implied_preconditions = True

    task = pddl_parser.open(domain_filename=options.domain, task_filename=options.task)
    normalize.normalize(task)
    sas_task = translate.pddl_to_sas(task)

    with open(options.sas_file, "w") as output_file:
        sas_task.output(output_file)

    return None
