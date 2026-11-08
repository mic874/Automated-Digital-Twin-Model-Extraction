from pathlib import Path
import sys
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pyspn.components.spn import (
    SPN,
    Place,
    Transition
)

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def get_transition(spn: SPN, label: str):
    """
    Retrieve transition by label.
    """

    for transition in spn.transitions:

        if transition.label == label:
            return transition

    return None


def get_place(spn: SPN, label: str):
    """
    Retrieve place by label.
    """

    for place in spn.places:

        if place.label == label:
            return place

    return None


# ----------------------------------------------------------------------
# Directly-follows graph + loop detection
# ----------------------------------------------------------------------


def get_directly_follows(traces):
    """
    Returns {activity: sorted list of direct successors}
    and the sorted list of start activities.
    """

    successors = defaultdict(set)
    start_activities = set()

    for trace in traces.values():

        activities = [event["activity"] for event in trace]

        if not activities:
            continue

        start_activities.add(activities[0])

        for source, target in zip(activities, activities[1:]):

            successors[source].add(target)

    return (
        {a: sorted(t) for a, t in successors.items()},
        sorted(start_activities),
    )


def find_loop_edges(successors, start_activities, all_activities):
    """
    DFS over the directly-follows graph. An edge pointing to an activity
    that is currently on the DFS stack is a back edge (= loop edge).
    Self-loops (A -> A) are back edges as well.
    """

    visited = set()
    on_stack = set()
    loop_edges = set()

    def dfs(node):

        visited.add(node)
        on_stack.add(node)

        for succ in successors.get(node, []):

            if succ in on_stack:

                loop_edges.add((node, succ))

            elif succ not in visited:

                dfs(succ)

        on_stack.remove(node)

    for activity in list(start_activities) + sorted(all_activities):

        if activity not in visited:

            dfs(activity)

    return loop_edges


# ----------------------------------------------------------------------
# Create transitions + individual input places
# ----------------------------------------------------------------------


def create_transitions(traces, spn: SPN):
    """
    Every activity becomes a timed transition.
    """

    activities = set()

    for trace in traces.values():

        for event in trace:

            activities.add(event["activity"])

    for activity in sorted(activities):

        transition = Transition(activity, "T")

        spn.add_transition(transition)

    return activities


def create_input_places(activities, start_activities, spn: SPN):
    """
    Every timed transition gets its own input place (never shared).

    Single start activity    : its input place holds the initial token.
    Several start activities : a XOR_start place holds the token and
                               immediate transitions choose the start.
    """

    input_places = {}

    single_start = len(start_activities) == 1

    for activity in sorted(activities):

        marking = 0 #1 if (single_start and activity in start_activities) else 0

        place = Place(f"{activity}_in", marking)

        spn.add_place(place)

        spn.add_input_arc(place, get_transition(spn, activity))

        input_places[activity] = place

    if len(start_activities) > 1:

        start_place = Place("XOR_start", 1)

        spn.add_place(start_place)

        for activity in start_activities:

            immediate = Transition(f"start_{activity}", "I")

            spn.add_transition(immediate)

            spn.add_input_arc(start_place, immediate)

            spn.add_output_arc(immediate, input_places[activity])

    return input_places


# ----------------------------------------------------------------------
# Connect activities
# ----------------------------------------------------------------------


def create_arcs(successors, loop_edges, input_places, spn: SPN):
    """
    One successor, forward : source -> target_in
    One successor, loop    : source -> place -> immediate -> target_in
    Several successors     : source -> XOR_source -> immediate (per
                             successor) -> target_in

    Loops always return to the INPUT place of the target transition.
    """

    if not hasattr(spn, "xor_places"):

        spn.xor_places = set()

    for source in sorted(successors):

        targets = successors[source]

        if not targets:
            continue

        source_transition = get_transition(spn, source)

        #
        # Exactly one successor
        #

        if len(targets) == 1:

            target = targets[0]

            if (source, target) not in loop_edges:

                spn.add_output_arc(source_transition, input_places[target])

                continue

            place = Place(f"{source}_to_{target}", 0)

            spn.add_place(place)

            spn.add_output_arc(source_transition, place)

            immediate = Transition(f"loop_{source}_to_{target}", "I")

            spn.add_transition(immediate)

            spn.add_input_arc(place, immediate)

            spn.add_output_arc(immediate, input_places[target])

            continue

        #
        # Several successors: XOR place + one immediate transition each
        #

        xor_place = Place(f"XOR_{source}", 0)

        spn.add_place(xor_place)

        spn.xor_places.add(xor_place.label)

        spn.add_output_arc(source_transition, xor_place)

        for target in targets:

            prefix = "loop" if (source, target) in loop_edges else "choice"

            immediate = Transition(f"{prefix}_{source}_to_{target}", "I")

            spn.add_transition(immediate)

            spn.add_input_arc(xor_place, immediate)

            spn.add_output_arc(immediate, input_places[target])


# ----------------------------------------------------------------------
# Build complete structure
# ----------------------------------------------------------------------
def create_start_transition(spn: SPN):

    start_transition = Transition("START", "I")
    spn.add_transition(start_transition)

    start_place = get_place(spn, "XOR_start")

    if start_place is None:
        start_place = get_place(spn, "START_place")

    if start_place is not None:
        spn.add_output_arc(start_transition, start_place)

    return spn

def build_spn_structure(traces, process_model=None):

    spn = SPN()

    activities = create_transitions(traces, spn)

    successors, start_activities = get_directly_follows(traces)

    loop_edges = find_loop_edges(successors, start_activities, activities)

    input_places = create_input_places(activities, start_activities, spn)

    #create_start_transition(
    #    spn
    #)

    create_arcs(successors, loop_edges, input_places, spn)

    return spn