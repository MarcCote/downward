import argparse
import hashlib

from pprint import pprint

import fast_downward
from fast_downward import Atom, Operator


def _demangle_alfred_name(text):
    text = text.replace("_bar_", "|")
    text = text.replace("_minus_", "-")
    text = text.replace("_dot_", ".")
    text = text.replace("_comma_", ",")

    splits = text.split("_", 1)
    if len(splits) == 1:
        return text

    name, rest = splits
    m = hashlib.md5()
    m.update(rest.encode("utf-8"))
    return "{}_{}".format(name, m.hexdigest()[:6])


def clean_alfred_facts(atoms):

    def _clean(atom: Atom):
        atom_type, rest = atom.name.split(" ", 1)
        name, rest = rest.split("(", 1)
        if name.startswith("new-axiom@"):
            return None

        arguments = rest[:-1].split(", ")
        fact = "" if atom_type == "Atom" else "!"
        fact += "{}({})".format(name, ", ".join(map(_demangle_alfred_name, arguments)))
        return fact

    facts = [_clean(atom) for atom in atoms]
    facts = sorted(filter(None, facts))
    return facts


def run_custom_pddl(args):
    downward_lib = fast_downward.load_lib()

    domain = open(args.domain).read()
    problem = open(args.problem).read()
    _, sas = fast_downward.pddl2sas(domain, problem)

    downward_lib.load_sas(sas.encode('utf-8'))

    while True:
        print("\n-= STATE =-")
        state_size = downward_lib.get_state_size()
        atoms = (Atom * state_size)()
        downward_lib.get_state(atoms)
        print("\n".join(sorted(map(str, clean_alfred_facts(atoms)))))

        print("\n-= Operators =-")
        operator_count = downward_lib.get_applicable_operators_count()
        operators = (Operator * operator_count)()
        downward_lib.get_applicable_operators(operators)
        operators = {int(op.id): op for op in operators}
        pprint(operators)

        idx = int(input("> "))

        print("\n-= Effects =-")
        op = operators[idx]
        effects = (Atom * op.nb_effect_atoms)()
        downward_lib.apply_operator(op.id, effects)
        pprint(list(sorted(map(str, clean_alfred_facts(effects)))))

        input("...")

    fast_downward.close_lib(downward_lib)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("domain")
    parser.add_argument("problem")
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()

    run_custom_pddl(args)
