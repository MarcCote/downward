import argparse

import textworld
from textworld.generator import KnowledgeBase
from textworld.logic import Proposition, Variable

from fast_downward.interface import State


def build_game():
    options = textworld.GameOptions()
    M = textworld.GameMaker(options)

    # The goal
    commands = ["go east", "insert ball into chest"]

    # Create a 'bedroom' room.
    R1 = M.new_room("bedroom")
    R2 = M.new_room("kitchen")
    M.set_player(R1)

    path = M.connect(R1.east, R2.west)
    path.door = M.new(type='d', name='wooden door')
    path.door.add_property("closed")
    path.door.add_property("openable")
    path.door.add_property("closeable")

    ball = M.new(type='t', name='ball')
    ball.add_property("portable")
    M.inventory.add(ball)

    # Add a closed chest in R2.
    chest = M.new(type='t', name='chest')
    chest.add_property("closed")
    chest.add_property("closeable")
    chest.add_property("openable")
    chest.add_property("container")
    R2.add(chest)

    # M.set_quest_from_commands(commands)
    game = M.build()

    # M.render(interactive=True)
    return game

def run_textworld_example(args):
    game = build_game()
    state = State(KnowledgeBase.default().logic, game.world.facts)
    print(state)
    if args.render:
        textworld.render.visualize(state, True)

    defaults = []
    while True:
        state.print_state()
        state.all_applicable_actions()

        default = None
        if defaults:
            default = defaults.pop()

        value = input("Operation Id [{}]: > ".format(default or ""))
        if not value:
            value = default

        if int(value) == -1:
            break

        state.apply(int(value))

        if args.render:
            textworld.render.visualize(state, True)

    del state




import hashlib


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


def clean_alfred_facts(facts):
    def _clean_fact(fact: textworld.logic.Proposition):
        args = [Variable(_demangle_alfred_name(arg.name), arg.type) for arg in fact.arguments]
        return Proposition(fact.name, args)

    facts = [_clean_fact(fact) for fact in facts if not fact.name.startswith("new-axiom@")]
    return facts


def run_custom_pddl(args):
    state = State.from_pddl(args.domain, args.problem)
    print(state)
    if args.render:
        # textworld.render.show_graph(clean_alfred_facts(state.facts), renderer="browser", save_html="/tmp/plot.html")
        textworld.render.show_graph(clean_alfred_facts(state.facts), renderer="browser")
        # textworld.render.visualize(state, True)

    defaults = [7]
    while True:
        state.print_state()
        state.all_applicable_actions()

        default = None
        if defaults:
            default = defaults.pop()

        value = input("Operation Id [{}]: > ".format(default or ""))
        if not value:
            value = default

        if int(value) == -1:
            break

        state.apply(int(value))

        if args.render:
            # textworld.render.show_graph(clean_alfred_facts(state.facts), renderer="browser", save_html="/tmp/plot.html")
            textworld.render.show_graph(clean_alfred_facts(state.facts), renderer="browser")
            # textworld.render.visualize(state, True)

    del state


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--domain")
    parser.add_argument("--problem")
    args = parser.parse_args()

    if args.domain is None and args.problem is None:
        run_textworld_example(args)
    else:
        run_custom_pddl(args)
