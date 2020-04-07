#ifndef TASKS_ROOT_TASK_H
#define TASKS_ROOT_TASK_H

#include "../state_registry.h"
#include "../abstract_task.h"

namespace tasks {
extern std::shared_ptr<AbstractTask> g_root_task;
extern void read_root_task(std::istream &in);
extern void read_root_task(std::istream &in, const GlobalState &state);
}
#endif
