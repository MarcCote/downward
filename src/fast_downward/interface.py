import io
import os
import sys
import shutil
import tempfile

from ctypes import cdll, CDLL
from ctypes import Structure
from ctypes import POINTER, c_void_p, c_char, c_int, c_char_p

from pkg_resources import Requirement, resource_filename

DOWNWARD_PATH = resource_filename(Requirement.parse('fast_downward'), 'fast_downward')
DOWNWARD_LIB_PATH = os.path.join(DOWNWARD_PATH, 'libdownward.so')

# Function to unload a shared library.
dlclose_func = CDLL(None).dlclose  # This WON'T work on Win
dlclose_func.argtypes = [c_void_p]


class CapturingStdout(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = io.StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio    # free up some memory
        sys.stdout = self._stdout


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


def load_lib():
    """ Loads a copy of fast-downward's shared library. """

    # Make a copy of libdownward.so before loading it to avoid concurrency issues.
    with tempfile.TemporaryDirectory() as tmpdir:
        downward_lib_path = os.path.join(tmpdir, 'libdownward.so')
        if not os.path.isfile(DOWNWARD_LIB_PATH):
            raise RuntimeError("Can't find: {}".format(DOWNWARD_LIB_PATH))

        shutil.copyfile(DOWNWARD_LIB_PATH, downward_lib_path)
        downward_lib = cdll.LoadLibrary(downward_lib_path)

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

        downward_lib.check_goal.argtypes = []
        downward_lib.check_goal.restype = bool

    return downward_lib


def close_lib(downward_lib):
    downward_lib.cleanup()
    dlclose_func(downward_lib._handle)


def pddl2sas(domain: str, problem: str) -> str:
    """ Converts a PDDL domain-problem to fast-downward planning task format (SAS).

    Arguments:
        domain: text content of the PDDL file describing the domain.
        problem: text content of the PDDL file describing the problem.

    Returns:
        planning task described in the SAS format understood by fast-downward.
    """
    # HACK: modify sys.argv according to what module `options` expects.
    import sys
    sys.argv = ["translate.py", "domain", "task"]
    from fast_downward.translate import options
    from fast_downward.translate import normalize
    from fast_downward.translate import translate
    from fast_downward.translate.pddl_parser import lisp_parser, parsing_functions

    options.filter_unimportant_vars = False
    options.filter_unreachable_facts = False
    options.use_partial_encoding = False
    options.skip_variable_reordering = True
    options.add_implied_preconditions = False
    options.invariant_generation_max_candidates = 0
    # options.generate_relaxed_task = True

    with CapturingStdout():
        # Load task.
        domain_pddl = lisp_parser.parse_nested_list(domain.split("\n"))
        problem_pddl = lisp_parser.parse_nested_list(problem.split("\n"))
        task = parsing_functions.parse_task(domain_pddl, problem_pddl)

        normalize.normalize(task)
        sas_task = translate.pddl_to_sas(task)

        # Write SAS file to a string to avoid I/O.
        sas_io = io.StringIO()
        sas_task.output(sas_io)
        sas_io.seek(0)
        sas = sas_io.read()

    return task, sas
