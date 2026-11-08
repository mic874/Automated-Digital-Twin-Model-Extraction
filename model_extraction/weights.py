from collections import defaultdict

from pyspn.components.spn import SPN

# ---------------------------------------------------------------------
# Count transition occurrences
# ---------------------------------------------------------------------


def count_transition_occurrences(traces):
    """
    Counts how often every event occurs.
    """

    counts = defaultdict(int)

    for trace in traces.values():

        for event in trace:

            activity = event["activity"]

            counts[activity] += 1

    return counts


# ---------------------------------------------------------------------
# Detect XOR choices
# ---------------------------------------------------------------------


def get_xor_branch_transitions(spn: SPN):
    """
    Finds transitions connected after XOR places.
    """

    branches = set()

    xor_places = getattr(spn, "xor_places", set())

    for place in spn.places:

        if place.label not in xor_places:
            continue

        #
        # Place -> Transition arcs
        #
        # These are InputArcs
        #

        for arc in place.input_arcs:

            transition = arc.to_transition

            branches.add(transition.label)

    return branches


# ---------------------------------------------------------------------
# Compute immediate weights
# ---------------------------------------------------------------------


def compute_immediate_weights(spn: SPN, traces):
    """
    Only immediate transitions
    participating in XOR splits
    receive weights.
    """

    occurrences = count_transition_occurrences(traces)

    xor_branches = get_xor_branch_transitions(spn)

    immediate = getattr(spn, "immediate_transitions", set())

    candidates = immediate & xor_branches

    weights = {}

    #
    # Raw frequencies
    #

    total = 0

    for transition in candidates:

        value = occurrences.get(transition, 0)

        weights[transition] = value

        total += value

    #
    # Normalize
    #

    if total > 0:

        for transition in weights:

            weights[transition] = weights[transition] / total

    return weights


# ---------------------------------------------------------------------
# Store weights in SPN
# ---------------------------------------------------------------------


def assign_transition_weights(spn: SPN, weights):
    """
    Adds weights to PySPN transition objects.
    """

    for transition_label, weight in weights.items():

        for transition in spn.transitions:

            if transition.label == transition_label:

                if transition.t_type == "I":

                    transition.weight = weight

                break

    return spn


# ---------------------------------------------------------------------
# Main interface
# ---------------------------------------------------------------------


def compute_immediate_transition_weights(spn: SPN, traces):
    """
    Complete implementation of Step 7.
    """

    print("Computing immediate transition weights...")

    weights = compute_immediate_weights(spn, traces)

    spn = assign_transition_weights(spn, weights)

    spn.immediate_weights = weights

    print(f"Immediate transition weights assigned: " f"{len(weights)}")

    return spn
