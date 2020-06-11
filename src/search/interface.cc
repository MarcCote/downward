#include "command_line.h"
#include "option_parser.h"
#include "search_engine.h"

#include "options/registries.h"
#include "tasks/root_task.h"
#include "task_utils/task_properties.h"
#include "utils/system.h"
#include "utils/timer.h"
#include "task_utils/successor_generator.h"

#include <iostream>
#include <cstring>

using namespace std;
using utils::ExitCode;

bool DEBUG = false;

// Global variables for the stateful library.
StateID state_id = StateID::no_state;
StateRegistry* state_registry = nullptr;


typedef struct Operator_t {
    int id;
    char name[1024];
    int nb_effect_atoms;
} Operator_t;


typedef struct Atom_t {
    char name[1024];
} Atom_t;


extern "C" void cleanup() {
    if(DEBUG) {
        utils::register_event_handlers();
        cout << "cleaning " << state_registry << "... ";
    }

    delete state_registry;
    state_registry = nullptr;
    tasks::g_root_task = nullptr;

    if(DEBUG) {
        utils::register_event_handlers();
        cout << "done" << endl;
    }
}


extern "C" int load_sas(char* input) {
    if (state_registry)
        cleanup();  // Delete existing state_registry.

    istringstream str(input);
    if(DEBUG) {
        utils::register_event_handlers();
        cout << "Loading SAS... [t=" << utils::g_timer << "]" << endl;
    }
    tasks::read_root_task(str);

    if (DEBUG) {
        cout << "Loading SAS... Done [t=" << utils::g_timer << "]" << endl;
    }

    TaskProxy global_task_proxy(*tasks::g_root_task);
    state_registry = new StateRegistry(global_task_proxy);
    GlobalState current_state = state_registry->get_initial_state();
    state_id = current_state.get_id();
    return true;
}


extern "C" int get_applicable_operators_count() {
    vector<OperatorID> applicable_ops;
    successor_generator::SuccessorGenerator successor_generator(state_registry->get_task_proxy());
    GlobalState current_state = state_registry->lookup_state(state_id);
    successor_generator.generate_applicable_ops(current_state, applicable_ops);

    if (DEBUG) {
        printf("===> Found %d operators! <===\n", (int) applicable_ops.size());
    }

    return (int) applicable_ops.size();
}


extern "C" void get_applicable_operators(Operator_t* operators) {
    OperatorsProxy global_operators = state_registry->get_task_proxy().get_operators();
    vector<OperatorID> applicable_ops;
    successor_generator::SuccessorGenerator successor_generator(state_registry->get_task_proxy());

    GlobalState current_state = state_registry->lookup_state(state_id);
    successor_generator.generate_applicable_ops(current_state, applicable_ops);

    for (size_t i=0; i != applicable_ops.size(); ++i) {
        OperatorID op_id = applicable_ops[i];
        OperatorProxy op = global_operators[op_id];
        operators[i].id = op_id.hash();
        operators[i].nb_effect_atoms = op.get_effects().size();
        strcpy(operators[i].name, op.get_name().c_str());
    }
}


extern "C" size_t apply_operator(size_t operator_idx, Atom_t* effects=NULL) {
    OperatorsProxy global_operators = state_registry->get_task_proxy().get_operators();
    OperatorProxy op = global_operators[operator_idx];
    if (DEBUG) {
        cout << "idx:" << operator_idx << " Op:" << op.get_id()
            << op.get_name() << endl;
    }

    EffectsProxy op_effects = op.get_effects();
    if (effects) {
        for (size_t i=0; i != op_effects.size(); ++i) {
            EffectProxy effect = op_effects[i];
            strcpy(effects[i].name, effect.get_fact().get_name().c_str());

            if (DEBUG) {
                cout << effects[i].name << endl;
            }
        }
    }

    GlobalState current_state = state_registry->lookup_state(state_id);
    GlobalState new_state = state_registry->get_successor_state(current_state, op);
    state_id = new_state.get_id();

    return op_effects.size();
}


extern "C" int get_state_size() {
    GlobalState current_state = state_registry->lookup_state(state_id);
    return (int) current_state.unpack().size();
}


extern "C" void get_state(Atom_t* atoms) {
    GlobalState current_state = state_registry->lookup_state(state_id);

    for (size_t i=0; i != current_state.unpack().size(); ++i) {
        FactProxy fact = current_state.unpack()[i];
        string fact_name = fact.get_name();
        if (fact_name != "<none of those>")
            strcpy(atoms[i].name, fact_name.c_str());
    }
}
