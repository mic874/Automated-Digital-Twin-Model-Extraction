import re

from pyspn.components.spn import Transition

from expert_knowledge_integration_helper import (
    transition_has_condition,
    get_transition_input_places,
    get_transition_output_places,
)


def integrate_operational(spn, knowledge, id):
    """
    Integrate operational knowledge into SPN.
    Behaviour:
    - Extracts IF condition.
    - Extracts operational effect/action.
    - Finds target transition.
    - Adds operational condition as guard.
    - Creates transition if missing.
    - Supports multiple operational conditions
      using cloned transitions.
    """

    print("inside integrate operational -----------", knowledge)

    if knowledge is None:
        return spn

    knowledge = str(knowledge).strip()

    #
    # Extract IF condition
    #

    match = re.search(r"IF\s+(.*?)\s+THEN", knowledge, flags=re.IGNORECASE | re.DOTALL)

    if not match:

        print(f"Cannot extract operational IF condition: {knowledge}")

        return spn

    condition = match.group(1).strip()

    #
    # Extract THEN part
    #

    match = re.search(
        r"THEN\s+(.*?)(?:\s+IN\s+(.+))?$", knowledge, flags=re.IGNORECASE | re.DOTALL
    )

    if not match:

        print(f"Cannot extract operational THEN part: {knowledge}")

        return spn

    then_part = match.group(1).strip()

    component = match.group(2)

    if component:

        component = component.strip().rstrip(".,; ")

    #
    # Determine target transition
    #

    target_transition = None

    #
    # Case 1:
    # Explicit IN component
    #

    if component:

        for transition in spn.transitions:

            if component.lower() == transition.label.lower():

                target_transition = transition
                break

        #
        # fallback matching
        #

        if target_transition is None:

            for transition in spn.transitions:

                if component.lower() in transition.label.lower():

                    target_transition = transition
                    break

    #
    # Case 2:
    # Process flow style
    #
    # THEN contains transition name
    #

    else:

        for transition in spn.transitions:

            if then_part.lower() == transition.label.lower():

                target_transition = transition
                break

        if target_transition is None:

            for transition in spn.transitions:

                if then_part.lower() in transition.label.lower():

                    target_transition = transition
                    break

    #
    # Create transition if missing
    #

    if target_transition is None:

        print(f"No transition found. Creating operational transition: {then_part}")

        target_transition = Transition(then_part, "I")

        target_transition.color = "royalblue"

        target_transition.source = id

        spn.add_transition(target_transition)

    #
    # Add operational guard
    #

    if transition_has_condition(target_transition):

        print(
            "Existing operational condition found. "
            "Creating cloned operational transition."
        )

        target_transition = clone_operational_transition(
            spn, target_transition, condition
        )

    else:

        target_transition.condition_label = (
            "operational: " + condition + " -> " + then_part
        )

        target_transition.t_type = "I"

    #
    # Metadata
    #

    target_transition.operational_condition = condition

    target_transition.operational_action = then_part

    target_transition.color = "royalblue"

    target_transition.source = id

    print(
        f"Integrated operational knowledge: "
        f"IF {condition} "
        f"THEN {then_part} "
        f"TARGET {target_transition.label}"
    )

    return spn


def clone_operational_transition(spn, original_transition, condition):
    """
    Clone an operational transition and reuse
    the same input/output places.
    Used when multiple operational conditions
    affect the same transition.
    """

    #
    # Generate unique label
    #

    base_label = original_transition.label

    counter = 2

    new_label = f"{base_label}_{counter}"

    while spn.get_transition_by_label(new_label):

        counter += 1

        new_label = f"{base_label}_{counter}"

    #
    # Create cloned transition
    #

    new_transition = Transition(new_label, "I")

    #
    # Add operational condition
    #

    new_transition.condition_label = "*" + condition

    new_transition.t_type = "I"

    new_transition.color = "royalblue"

    new_transition.source = id

    #
    # Copy distribution if present
    #

    if hasattr(original_transition, "distribution"):

        new_transition.distribution = original_transition.distribution

    #
    # Copy firing weight if present
    #

    if hasattr(original_transition, "weight"):

        new_transition.weight = original_transition.weight

    #
    # Copy metadata
    #

    new_transition.operational_condition = condition

    if hasattr(original_transition, "operational_action"):

        new_transition.operational_action = original_transition.operational_action

    #
    # Add transition
    #

    spn.add_transition(new_transition)

    #
    # Copy input places
    #

    for place in get_transition_input_places(spn, original_transition):

        spn.add_input_arc(place, new_transition, color="royalblue")

    #
    # Copy output places
    #

    for place in get_transition_output_places(spn, original_transition):

        spn.add_output_arc(new_transition, place, color="royalblue")

    print(
        "Created cloned operational transition:",
        new_transition.label,
        new_transition.condition_label,
    )

    return new_transition
