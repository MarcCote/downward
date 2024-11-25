#include "command_line.h"
#include "option_parser.h"
#include "search_engine.h"
#include "search_engines/search_common.h"
#include "search_engines/eager_search.h"
#include "search_engines/lazy_search.h"
#include "../evaluators/g_evaluator.h"

#include "options/registries.h"
#include "tasks/root_task.h"
#include "task_utils/task_properties.h"
#include "utils/system.h"
#include "utils/logging.h"
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
vector<OperatorID> applicable_ops;
string sas;
string sas_replan;
vector<tuple<int, string, int>> last_plan;


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
        cout << "cleaning " << state_registry << "... ";
    }

    delete state_registry;
    state_registry = nullptr;
    tasks::g_root_task = nullptr;

    if(DEBUG) {
        cout << "done" << endl;
    }
}


extern "C" int load_sas(char* input) {
    if (state_registry)
        cleanup();  // Delete existing state_registry.

    sas = string(input);
    if(DEBUG) {
        cout << "Loading SAS... [t=" << utils::g_timer << "]" << endl;
    }
    istringstream in(sas);
    tasks::read_root_task(in);

    if (DEBUG) {
        cout << "Loading SAS... Done [t=" << utils::g_timer << "]" << endl;
    }

    TaskProxy global_task_proxy(*tasks::g_root_task);
    state_registry = new StateRegistry(global_task_proxy);
    GlobalState current_state = state_registry->get_initial_state();
    state_id = current_state.get_id();
    return true;
}


extern "C" int load_sas_replan(char* input) {
    sas_replan = string(input);
    return true;
}


extern "C" int get_applicable_operators_count() {
    successor_generator::SuccessorGenerator &successor_generator = successor_generator::g_successor_generators[state_registry->get_task_proxy()];

    GlobalState current_state = state_registry->lookup_state(state_id);
    current_state = state_registry->lookup_state(state_id);
    applicable_ops.clear();
    successor_generator.generate_applicable_ops(current_state, applicable_ops);

    if (DEBUG) {
        printf("===> Found %d operators! <===\n", (int) applicable_ops.size());
    }

    return (int) applicable_ops.size();
}


extern "C" void get_applicable_operators(Operator_t* operators) {
    OperatorsProxy global_operators = state_registry->get_task_proxy().get_operators();

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

extern "C" int get_state_id() {
    return state_id.value;
}

extern "C" void set_state_id(int value) {
    state_id = StateID(value);
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


extern "C" bool check_goal() {
    GlobalState current_state = state_registry->lookup_state(state_id);
    return task_properties::is_goal_state(state_registry->get_task_proxy(), current_state);
}


extern "C" bool check_solution(size_t size, Operator_t* operators) {

    OperatorsProxy global_operators = state_registry->get_task_proxy().get_operators();
    GlobalState current_state = state_registry->lookup_state(state_id);
    GlobalState new_state = state_registry->lookup_state(state_id);
    for (size_t i = 0; i != size; ++i) {
        OperatorProxy op = global_operators[operators[i].id];
        if (DEBUG) {
            cout << "idx:" << op.get_id() << op.get_name() << endl;
        }

        if (!task_properties::is_applicable(op, current_state.unpack()))
            return false;

        current_state = state_registry->get_successor_state(current_state, op);
    }

    return task_properties::is_goal_state(state_registry->get_task_proxy(), current_state);
}


extern "C" int get_operator_id_from_name(char* name) {

    OperatorsProxy global_operators = state_registry->get_task_proxy().get_operators();
    for (OperatorProxy op : global_operators) {
        // cout << op.get_name() << "\n" << name << "\n---\n" << endl;

        if (strcmp(name, op.get_name().c_str()) == 0) {
            return op.get_id();
        }
    }

    return -1;
}




extern "C" bool solve_sas(char* input, bool verbose=false) {
    utils::g_log.set_verbosity(verbose ? utils::Verbosity::NORMAL : utils::Verbosity::SILENT);

    last_plan.clear();

    Options opts;
    vector<shared_ptr<Evaluator>> evals;
    vector<shared_ptr<Evaluator>> preferred;
    evals.push_back(make_shared<g_evaluator::GEvaluator>());
    opts.set<vector<shared_ptr<Evaluator>>>("evals", evals);
    opts.set<vector<shared_ptr<Evaluator>>>("preferred", preferred);
    opts.set<OperatorCost>("cost_type", OperatorCost::NORMAL);
    opts.set<int>("bound", 2147483647);
    opts.set<double>("max_time", INFINITY);
    opts.set<bool>("reopen_closed", false);
    opts.set<bool>("randomize_successors", false);
    opts.set<bool>("preferred_successors_first", false);
    opts.set<int>("random_seed", -1);
    opts.set<int>("boost", 1000);
    opts.set<utils::Verbosity>("verbosity", verbose ? utils::Verbosity::NORMAL : utils::Verbosity::SILENT);
    opts.set<shared_ptr<OpenListFactory>>("open", search_common::create_greedy_open_list_factory(opts));

    // Change root task to start the search from a new state.
    auto root_task_bkp = tasks::g_root_task;
    tasks::g_root_task = nullptr;
    istringstream in(input);
    tasks::read_root_task(in);

    lazy_search::LazySearch engine(opts);

    vector<shared_ptr<Evaluator>> preferred_list = opts.get_list<shared_ptr<Evaluator>>("preferred");
    engine.set_preferred_operator_evaluators(preferred_list);

    utils::Timer search_timer;
    engine.search();
    search_timer.stop();
    utils::g_log << "Search time: " << search_timer << endl;

    if (engine.found_solution()) {
        utils::g_log << "Solution found!" << endl;

        TaskProxy task_proxy(*tasks::g_root_task);
        OperatorsProxy operators = task_proxy.get_operators();
        for (OperatorID op_id : engine.get_plan()) {
            OperatorProxy op = operators[op_id];
            last_plan.push_back(make_tuple(op_id.hash(), op.get_name(), op.get_effects().size()));
        }
    }

    // Restore root task.
    tasks::g_root_task = root_task_bkp;

    return engine.found_solution();
}

extern "C" bool replan(bool verbose=false) {
    utils::g_log.set_verbosity(verbose ? utils::Verbosity::NORMAL : utils::Verbosity::SILENT);

    last_plan.clear();

    Options opts;
    vector<shared_ptr<Evaluator>> evals;
    vector<shared_ptr<Evaluator>> preferred;
    evals.push_back(make_shared<g_evaluator::GEvaluator>());
    opts.set<vector<shared_ptr<Evaluator>>>("evals", evals);
    opts.set<vector<shared_ptr<Evaluator>>>("preferred", preferred);
    opts.set<OperatorCost>("cost_type", OperatorCost::NORMAL);
    opts.set<int>("bound", 2147483647);
    opts.set<double>("max_time", INFINITY);
    opts.set<bool>("reopen_closed", false);
    opts.set<bool>("randomize_successors", false);
    opts.set<bool>("preferred_successors_first", false);
    opts.set<int>("random_seed", -1);
    opts.set<int>("boost", 1000);
    opts.set<utils::Verbosity>("verbosity", verbose ? utils::Verbosity::NORMAL : utils::Verbosity::SILENT);
    opts.set<shared_ptr<OpenListFactory>>("open", search_common::create_greedy_open_list_factory(opts));

    // Change root task to start the search from a new state.
    auto root_task_bkp = tasks::g_root_task;
    tasks::g_root_task = nullptr;
    istringstream in(sas_replan);
    GlobalState current_state = state_registry->lookup_state(state_id);
    tasks::read_root_task(in, current_state);

    lazy_search::LazySearch engine(opts);

    vector<shared_ptr<Evaluator>> preferred_list = opts.get_list<shared_ptr<Evaluator>>("preferred");
    engine.set_preferred_operator_evaluators(preferred_list);

    utils::Timer search_timer;
    engine.search();
    search_timer.stop();
    utils::g_log << "Search time: " << search_timer << endl;

    if (engine.found_solution()) {
        utils::g_log << "Solution found!" << endl;

        TaskProxy task_proxy(*tasks::g_root_task);
        OperatorsProxy operators = task_proxy.get_operators();
        for (OperatorID op_id : engine.get_plan()) {
            OperatorProxy op = operators[op_id];
            last_plan.push_back(make_tuple(op_id.hash(), op.get_name(), op.get_effects().size()));
        }
    }

    // Restore root task.
    tasks::g_root_task = root_task_bkp;

    return engine.found_solution();
}


extern "C" bool solve(bool verbose=false) {
    utils::g_log.set_verbosity(verbose ? utils::Verbosity::NORMAL : utils::Verbosity::SILENT);

    last_plan.clear();

    Options opts;
    vector<shared_ptr<Evaluator>> evals;
    vector<shared_ptr<Evaluator>> preferred;
    evals.push_back(make_shared<g_evaluator::GEvaluator>());
    opts.set<vector<shared_ptr<Evaluator>>>("evals", evals);
    opts.set<vector<shared_ptr<Evaluator>>>("preferred", preferred);
    opts.set<OperatorCost>("cost_type", OperatorCost::NORMAL);
    opts.set<int>("bound", 2147483647);
    opts.set<double>("max_time", INFINITY);
    opts.set<bool>("reopen_closed", false);
    opts.set<bool>("randomize_successors", false);
    opts.set<bool>("preferred_successors_first", false);
    opts.set<int>("random_seed", -1);
    opts.set<int>("boost", 1000);
    opts.set<utils::Verbosity>("verbosity", verbose ? utils::Verbosity::NORMAL : utils::Verbosity::SILENT);
    opts.set<shared_ptr<OpenListFactory>>("open", search_common::create_greedy_open_list_factory(opts));

    // Change root task to start the search from a new state.
    auto root_task_bkp = tasks::g_root_task;
    tasks::g_root_task = nullptr;
    istringstream in(sas);
    GlobalState current_state = state_registry->lookup_state(state_id);
    tasks::read_root_task(in, current_state);
    lazy_search::LazySearch engine(opts);

    vector<shared_ptr<Evaluator>> preferred_list = opts.get_list<shared_ptr<Evaluator>>("preferred");
    engine.set_preferred_operator_evaluators(preferred_list);

    utils::Timer search_timer;
    engine.search();
    search_timer.stop();
    utils::g_log << "Search time: " << search_timer << endl;

    if (engine.found_solution()) {
        utils::g_log << "Solution found!" << endl;

        TaskProxy task_proxy(*tasks::g_root_task);
        OperatorsProxy operators = task_proxy.get_operators();
        for (OperatorID op_id : engine.get_plan()) {
            OperatorProxy op = operators[op_id];
            last_plan.push_back(make_tuple(op_id.hash(), op.get_name(), op.get_effects().size()));
        }
    }

    // Restore root task.
    tasks::g_root_task = root_task_bkp;

    return engine.found_solution();
}

extern "C" int get_last_plan_length() {
    return last_plan.size();
}

extern "C" void get_last_plan(Operator_t* operators) {
    for (size_t i=0; i != last_plan.size(); ++i) {
        operators[i].id = get<0>(last_plan[i]);
        strcpy(operators[i].name, get<1>(last_plan[i]).c_str());
        operators[i].nb_effect_atoms = get<2>(last_plan[i]);
    }
}
