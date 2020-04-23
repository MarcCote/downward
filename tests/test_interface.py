import argparse

import textworld
from textworld.generator import KnowledgeBase

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


def run_custom_pddl(args):
    #state = State(KnowledgeBase.default().logic, game.world.facts)
    state = State.from_pddl(args.domain, args.problem)
    print(state)
    if args.render:
        textworld.render.visualize(state, True)

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
            textworld.render.visualize(state, True)

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
