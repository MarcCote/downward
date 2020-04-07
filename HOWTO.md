
# Installation

## TextWorld
You need a custom branch of TextWorld for now.

    pip install https://github.com/MarcCote/TextWorld/archive/1.5.pddl_interface.zip

## Fast-downward
    git clone https://github.com/MarcCote/fast-downward.git -b api
    pip install fast-downward/

# Testing the interface
Within the root folder of this project, run

    python tests/test_interface.py --domain tests/domain.pddl --problem tests/problem.pddl
