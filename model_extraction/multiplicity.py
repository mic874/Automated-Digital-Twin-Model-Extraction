# ---------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------

from collections import defaultdict

from pyspn.components.spn import SPN

# ---------------------------------------------------------------------
# Count multiplicities from traces
# ---------------------------------------------------------------------


def compute_multiplicities(traces):
    """
    Computes multiplicities for every
    consecutive transition pair.
    """

    multiplicity_data = defaultdict(lambda: {"input": [], "output": []})

    # -------------------------------------------------------------
    # Process every trace
    # -------------------------------------------------------------

    for trace in traces.values():

        activities = [event["activity"] for event in trace]

        #
        # examine all transition pairs
        #

        for i in range(len(activities) - 1):

            Ei = activities[i]

            Ei_next = activities[i + 1]

            pair = (Ei, Ei_next)

            # -------------------------------------------------
            # Input multiplicity
            # -------------------------------------------------

            try:

                first_next = activities.index(Ei_next, i)

            except ValueError:

                continue

            input_count = activities[:first_next].count(Ei)

            # -------------------------------------------------
            # Output multiplicity
            # -------------------------------------------------

            first_Ei = activities.index(Ei)

            output_count = activities[first_Ei + 1 :].count(Ei_next)

            multiplicity_data[pair]["input"].append(input_count)

            multiplicity_data[pair]["output"].append(output_count)

    return multiplicity_data


# ---------------------------------------------------------------------
# Aggregate multiplicities
# ---------------------------------------------------------------------


def aggregate_multiplicities(multiplicity_data):
    """
    Converts multiple observations
    into one multiplicity value.
    """

    result = {}

    for pair, values in multiplicity_data.items():

        input_values = values["input"]

        output_values = values["output"]

        input_value = max(input_values) if input_values else 1

        output_value = max(output_values) if output_values else 1

        result[pair] = {"input": max(1, input_value), "output": max(1, output_value)}

    return result


# ---------------------------------------------------------------------
# Update SPN arcs
# ---------------------------------------------------------------------


def update_arc_multiplicities(spn: SPN, multiplicities):
    """
    Updates PySPN arc multiplicities.
    """

    for pair, values in multiplicities.items():

        source = pair[0]

        target = pair[1]

        place_name = f"{source}_to_{target}"

        input_mult = values["input"]

        output_mult = values["output"]

        source_transition = spn.get_transition_by_label(source)

        target_transition = spn.get_transition_by_label(target)

        place = spn.get_place_by_label(place_name)

        #
        # Skip incomplete relations
        #

        if source_transition is None:
            continue

        if target_transition is None:
            continue

        if place is None:
            continue

        for arc in list(source_transition.output_arcs):

            if arc.to_place == place:

                arc.multiplicity = input_mult


        for arc in list(target_transition.input_arcs):

            if arc.from_place == place:

                arc.multiplicity = output_mult

    return spn


# ---------------------------------------------------------------------
# Complete Multiplicity Detection
# ---------------------------------------------------------------------


def detect_arc_multiplicities(spn: SPN, traces):
    """
    Returns updated SPN.
    """

    print("Computing arc multiplicities...")

    raw = compute_multiplicities(traces)

    multiplicities = aggregate_multiplicities(raw)

    spn = update_arc_multiplicities(spn, multiplicities)

    spn.multiplicities = multiplicities

    print(f"Multiplicity relations detected: " f"{len(multiplicities)}")

    return spn
