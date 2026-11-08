from collections import defaultdict

from structure import SPN, Place, Transition

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def get_transition(spn, label):
    """
    Find transition by label.
    """

    for transition in spn.transitions:

        if transition.label == label:
            return transition

    return None


def get_place(spn, label):
    """
    Find place by label.
    """

    for place in spn.places:

        if place.label == label:
            return place

    return None


# ---------------------------------------------------------------------
# Failure extraction
# ---------------------------------------------------------------------


def extract_component_failures(state_log):
    """
    Extracts failed components.
    """

    failures = defaultdict(list)

    if state_log is None:
        return failures

    for _, row in state_log.iterrows():

        if "lifecycle:state" not in row:
            continue

        if str(row["lifecycle:state"]).lower() != "failure":
            continue

        component = None

        #
        # Try common DDRA columns
        #

        for col in ["component", "concept:name", "org:resource"]:

            if col in row:

                component = str(row[col])

                break

        if component is None:
            continue

        failures[component].append(row["time:timestamp"])

    return failures


# ---------------------------------------------------------------------
# Create reliability structure
# ---------------------------------------------------------------------


def create_failure_structure(
    spn, component, failure_distribution=None, repair_distribution=None
):
    """
    Creates DDRA reliability subnet:
    """

    fail_label = f"FAIL_{component}"

    repair_label = f"RESTORE_{component}"

    failed_place_label = f"FAILED_{component}"

    available_place_label = f"AVAILABLE_{component}"

    if get_transition(spn, fail_label):
        return

    #
    # Timed failure transition
    #

    fail_transition = Transition(fail_label, "T")

    fail_transition.distribution = failure_distribution

    fail_transition.color = "darkgoldenrod"

    #
    # Timed repair transition
    #

    repair_transition = Transition(repair_label, "T")

    repair_transition.distribution = repair_distribution

    repair_transition.color = "darkgoldenrod"

    #
    # Places
    #

    failed_place = Place(failed_place_label, 0)

    failed_place.color = "darkgoldenrod"

    available_place = Place(available_place_label, 1)

    available_place.color = "darkgoldenrod"

    spn.add_transition(fail_transition)

    spn.add_transition(repair_transition)

    spn.add_place(failed_place)

    spn.add_place(available_place)

    #
    # AVAILABLE -> FAIL
    #

    spn.add_input_arc(available_place, fail_transition)

    #
    # FAIL -> FAILED
    #

    spn.add_output_arc(fail_transition, failed_place)

    #
    # FAILED -> REPAIR
    #

    spn.add_input_arc(failed_place, repair_transition)

    #
    # REPAIR -> AVAILABLE
    #

    spn.add_output_arc(repair_transition, available_place)

    if not hasattr(spn, "failed_components"):

        spn.failed_components = set()

    spn.failed_components.add(component)


# ---------------------------------------------------------------------
# Add inhibitor relations
# ---------------------------------------------------------------------


def add_failure_inhibitors(spn, component):
    """
    Failed component blocks
    """

    failed_place = get_place(spn, f"FAILED_{component}")

    if failed_place is None:
        return

    #
    # Find transitions belonging
    # to this component
    #

    for transition in spn.transitions:

        if component.lower() in transition.label.lower():

            #
            # Avoid failure/repair transitions
            #

            if transition.label.startswith("FAIL_") or transition.label.startswith(
                "RESTORE_"
            ):
                continue

            #
            # Add inhibitor
            #
            if "choice" not in transition.label.lower() and "loop" not in transition.label.lower():

                spn.add_inhibitor_arc(transition, failed_place, color="darkgoldenrod")


# ---------------------------------------------------------------------
# Repair connection
# ---------------------------------------------------------------------


def connect_repair_to_component(spn, component):
    """
    After repair the component
    becomes available again.
    """

    repair = get_transition(spn, f"RESTORE_{component}")

    if repair is None:
        return

    for transition in spn.transitions:

        if component.lower() in transition.label.lower():

            if transition == repair:
                continue

            #
            # Find incoming places
            #

            for arc in transition.input_arcs:

                place = arc.from_place

                #
                # Restore token availability
                #

                spn.add_output_arc(repair, place)

                return


# ---------------------------------------------------------------------
# Main reliability extraction
# ---------------------------------------------------------------------


def extract_reliability_components(
    spn: SPN, state_log, failure_distributions=None, repair_distributions=None
):
    """
    Complete reliability extraction.
    Adds:
    - timed failure transitions
    - timed repair transitions
    - failure distributions
    - repair distributions
    - failed state places
    - inhibitor arcs
    """

    print("Extracting reliability components...")

    failures = extract_component_failures(state_log)

    print(f"Components with failures: {len(failures)}")

    for component in failures:

        failure_distribution = None

        repair_distribution = None

        if failure_distributions:

            failure_distribution = failure_distributions.get(component)

        if repair_distributions:

            repair_distribution = repair_distributions.get(component)

        create_failure_structure(
            spn, component, failure_distribution, repair_distribution
        )

        add_failure_inhibitors(spn, component)

    print("Reliability extraction completed.")

    return spn
