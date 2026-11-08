from collections import defaultdict


from pyspn.components.spn import SPN, Place, InputArc, OutputArc

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def get_place(spn, label):

    for place in spn.places:

        if place.label == label:
            return place

    return None


def get_transition(spn, label):

    for transition in spn.transitions:

        if transition.label == label:
            return transition

    return None


# ---------------------------------------------------------------------
# Trace utilities
# ---------------------------------------------------------------------


def get_successors(traces):

    successors = defaultdict(set)

    for trace in traces.values():

        activities = [e["activity"] for e in trace]

        for i in range(len(activities) - 1):

            successors[activities[i]].add(activities[i + 1])

    return successors


# ---------------------------------------------------------------------
# XOR detection
# ---------------------------------------------------------------------


def detect_xor_splits(traces):

    successors = get_successors(traces)

    xor = {}

    for transition, targets in successors.items():

        if len(targets) > 1:

            xor[transition] = targets

    return xor


# ---------------------------------------------------------------------
# Remove arc safely
# ---------------------------------------------------------------------


def remove_output_arc(transition, arc):

    if arc in transition.output_arcs:
        transition.output_arcs.remove(arc)

    if arc.to_place is not None:

        if arc in arc.to_place.input_arcs:
            arc.to_place.input_arcs.remove(arc)


def remove_input_arc(transition, arc):

    if arc in transition.input_arcs:
        transition.input_arcs.remove(arc)

    if arc.from_place is not None:

        if arc in arc.from_place.output_arcs:
            arc.from_place.output_arcs.remove(arc)


# ---------------------------------------------------------------------
# Merge XOR places
# ---------------------------------------------------------------------


def merge_xor_places(spn: SPN, xor_splits):

    if not hasattr(spn, "xor_places"):

        spn.xor_places = set()

    for transition_label, successors in xor_splits.items():

        transition = get_transition(spn, transition_label)

        if transition is None:
            continue

        old_places = []

        for successor in successors:

            label = f"{transition_label}_to_{successor}"

            place = get_place(spn, label)

            if place:

                old_places.append(place)

        if len(old_places) <= 1:

            continue

        xor_place = Place(f"XOR_{transition_label}", 0)

        spn.add_place(xor_place)

        #
        # Remove transition -> old places
        #

        for arc in list(transition.output_arcs):

            if arc.to_place in old_places:

                remove_output_arc(transition, arc)

        #
        # Add transition -> XOR place
        #

        spn.add_output_arc(transition, xor_place)

        #
        # Redirect old place -> transition arcs
        #

        for old_place in old_places:

            for arc in list(old_place.output_arcs):

                target = arc.to_transition

                spn.add_input_arc(xor_place, target, arc.multiplicity)

                remove_input_arc(target, arc)

        #
        # Remove obsolete places
        #

        for old_place in old_places:

            if old_place in spn.places:

                spn.places.remove(old_place)

        spn.xor_places.add(xor_place.label)

    return spn


# ---------------------------------------------------------------------
# Detect AND joins
# ---------------------------------------------------------------------


def detect_and_join_candidates(spn: SPN):

    joins = {}

    for transition in spn.transitions:

        places = []

        for arc in transition.input_arcs:

            places.append(arc.from_place.label)

        if len(places) > 1:

            joins[transition.label] = places

    return joins


# ---------------------------------------------------------------------
# Verify AND join
# ---------------------------------------------------------------------


def verify_and_join(transition, input_places, traces):

    required = set()

    for place in input_places:

        if "_to_" in place:

            predecessor = place.split("_to_")[0]

            required.add(predecessor)

    for trace in traces.values():

        activities = [e["activity"] for e in trace]

        if transition not in activities:
            continue

        index = activities.index(transition)

        before = set(activities[:index])

        if required.issubset(before):

            return True

    return False


# ---------------------------------------------------------------------
# Correct false AND joins
# ---------------------------------------------------------------------


def correct_false_and_join(spn, transition_label, input_places):

    transition = get_transition(spn, transition_label)

    if transition is None:
        return spn

    merged_place = Place(f"JOIN_{transition_label}", 0)

    spn.add_place(merged_place)

    for place_label in input_places:

        place = get_place(spn, place_label)

        if place is None:
            continue

        for arc in list(transition.input_arcs):

            if arc.from_place == place:

                remove_input_arc(transition, arc)

        if place in spn.places:

            spn.places.remove(place)

    spn.add_input_arc(merged_place, transition)

    return spn


# ---------------------------------------------------------------------
# Main interface
# ---------------------------------------------------------------------


def implement_control_flow_patterns(spn: SPN, traces):

    print("Detecting XOR splits...")

    xor = detect_xor_splits(traces)

    print(f"XOR splits found: {len(xor)}")

    spn = merge_xor_places(spn, xor)

    print("Checking AND joins...")

    joins = detect_and_join_candidates(spn)

    corrected = 0

    for transition, places in joins.items():

        valid = verify_and_join(transition, places, traces)

        if not valid:

            spn = correct_false_and_join(spn, transition, places)

            corrected += 1

    print(f"False AND joins corrected: {corrected}")

    return spn
