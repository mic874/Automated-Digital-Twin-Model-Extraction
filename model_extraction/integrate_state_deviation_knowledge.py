import re
from pyspn.components.spn import SPN, Place, Transition
import pandas as pd
import json

from expert_knowledge_integration_helper import (
    transition_has_condition,
    transition_has_distribution,
    get_transition,
    get_component_transitions,
    get_transition_input_places,
    get_transition_output_places,
)


def integrate_state_deviation(spn, knowledge, id):
    """
    Integrate state deviation knowledge as a guard
    on a failure transition.
    Behaviour:
    - If FAIL_component exists:
          add guard to it
    - If no reliability model exists:
          create FAIL_component,
          FAILED_component place,
          REPAIR_component transition,
          then attach guard.
    """
  
    if knowledge is None:
        return spn

    knowledge = str(knowledge).strip()

    # --------------------------------------------------
    # Extract IF condition
    # --------------------------------------------------

    match = re.search(r"IF\s+(.*?)\s+THEN", knowledge, flags=re.IGNORECASE | re.DOTALL)

    if not match:

        print(f"Cannot extract condition from: {knowledge}")

        return spn

    condition = match.group(1).strip()

    # --------------------------------------------------
    # Extract component
    # --------------------------------------------------

    match = re.search(r"\bIN\b\s+(.+)$", knowledge, flags=re.IGNORECASE)

    if not match:

        print(f"Cannot extract component from: {knowledge}")

        return spn

    component = match.group(1).strip()

    component = component.rstrip(".,; ")

    # --------------------------------------------------
    # Find existing failure transition
    # --------------------------------------------------

    failure_transition = None

    failure_label = f"FAIL_{component}"

    for transition in spn.transitions:

        if transition.label.lower() == failure_label.lower():

            failure_transition = transition
            break

    # --------------------------------------------------
    # Reliability model missing
    # --------------------------------------------------

    if failure_transition is None:

        print(
            f"No reliability model found for {component}. "
            f"Creating failure/repair structure."
        )

        create_failure_structure(spn, component, id)

        # search again

        for transition in spn.transitions:

            if transition.label.lower() == failure_label.lower():

                failure_transition = transition
                break

    # --------------------------------------------------
    # Fallback matching
    # --------------------------------------------------

    if failure_transition is None:

        for transition in spn.transitions:

            if not transition.label.startswith("FAIL_"):
                continue

            if component.lower() in transition.label.lower():

                failure_transition = transition
                break

    if failure_transition is None:

        print(f"Could not create/find failure transition " f"for {component}")

        return spn

    # --------------------------------------------------
    # Add guard condition
    # --------------------------------------------------

    if transition_has_condition(failure_transition):

        #
        # Existing guarded transition:
        # clone it and attach another condition.
        #

        print("Existing condition found. " "Creating additional failure transition.")

        failure_transition = clone_failure_transition(
            spn, failure_transition, condition, id
        )

    elif transition_has_distribution(failure_transition):

        #
        # Existing reliability transition:
        #

        print("Existing reliability transition found. " "Creating guarded clone.")

        failure_transition = clone_failure_transition(
            spn, failure_transition, condition, id
        )

    else:

        failure_transition.condition_label = "*" + condition
        failure_transition.t_type = "I"

    failure_transition.color = "firebrick"
    failure_transition.source = id
    

    if hasattr(spn, "transitions"):

        for transition in spn.transitions:

            if transition.label in [f"FAIL_{component}", f"RESTORE_{component}"]:

                transition.color = "firebrick"
               
    print(
        f"Integrated state deviation: "
        f"IF {condition} "
        f"-> {failure_transition.label}"
    )

    return spn


def create_failure_structure(
    spn,
    component,
    id,
    failure_distribution=None,
    repair_distribution=None,
):
    """
    Creates reliability loop model
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

    fail_transition = Transition(
        fail_label,
        "I",
    )

    fail_transition.color = "firebrick"
    fail_transition.source = id

    fail_transition.distribution = failure_distribution

    #
    # Timed repair transition
    #

    repair_transition = Transition(
        repair_label,
        "T",
    )

    repair_transition.color = "firebrick"
    repair_transition.source = id

    repair_transition.distribution = repair_distribution

    #
    # Places
    #

    failed_place = Place(
        failed_place_label,
        0,
    )

    failed_place.color = "firebrick"
    failed_place.source = id

    available_place = Place(
        available_place_label,
        1,
    )

    available_place.color = "firebrick"
    available_place.source = id

    spn.add_transition(fail_transition)

    spn.add_transition(repair_transition)

    spn.add_place(failed_place)

    spn.add_place(available_place)

    #
    # AVAILABLE -> FAIL
    #

    spn.add_input_arc(available_place, fail_transition, color="firebrick")

    #
    # FAIL -> FAILED
    #

    spn.add_output_arc(fail_transition, failed_place, color="firebrick")

    #
    # FAILED -> REPAIR
    #

    spn.add_input_arc(failed_place, repair_transition, color="firebrick")

    #
    # REPAIR -> AVAILABLE
    #

    spn.add_output_arc(repair_transition, available_place, color="firebrick")

    for transition in get_component_transitions(spn, component):
        if "choice" not in transition.label.lower() and "loop" not in transition.label.lower():
            spn.add_inhibitor_arc(transition, failed_place, color="firebrick")

    if not hasattr(spn, "failed_components"):

        spn.failed_components = set()

    spn.failed_components.add(component)


def clone_failure_transition(spn, original_transition, condition, id):
    """
    Clone a failure transition and reuse
    the same input/output places.
    """

    base_label = original_transition.label

    counter = 2

    new_label = f"{base_label}_{counter}"

    while spn.get_transition_by_label(new_label):

        counter += 1
        new_label = f"{base_label}_{counter}"

    new_transition = Transition(new_label, "I")

    new_transition.condition_label = "*" + condition

    new_transition.t_type = "I"
    new_transition.color = "firebrick"
    new_transition.source = id

    if hasattr(original_transition, "distribution"):

        new_transition.distribution = original_transition.distribution
    #
    # Add transition to SPN
    #

    spn.add_transition(new_transition)

    #
    # Copy input places
    #

    for place in get_transition_input_places(spn, original_transition):

        spn.add_input_arc(place, new_transition, color="firebrick")

    #
    # Copy output places
    #

    for place in get_transition_output_places(spn, original_transition):

        spn.add_output_arc(new_transition, place, color="firebrick")

    print(
        "Created cloned failure transition:",
        new_transition.label,
        new_transition.condition_label,
    )

    return new_transition
