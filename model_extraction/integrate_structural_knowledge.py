import re
from pyspn.components.spn import SPN, Place, Transition
import pandas as pd
import json


def integrate_structural(spn, knowledge, id):
    """
    Integrate structural knowledge into SPN.
    Behaviour:
    - Creates structural event group.
    - Connects group to represented transitions.
    - Stores structural metadata.
    """

    print("inside integrate structural --------", knowledge)

    if knowledge is None:
        return spn

    knowledge = str(knowledge).strip()

    #
    # Extract IF part
    #

    match = re.search(r"IF\s+(.*?)\s+THEN", knowledge, flags=re.IGNORECASE | re.DOTALL)

    if not match:

        print("No IF THEN structural pattern detected. " "Using process flow fallback.")

        return process_flow_execution(spn, knowledge)

    event_group = match.group(1).strip()

    #
    # Extract THEN part
    #

    match = re.search(r"THEN\s+(.*)$", knowledge, flags=re.IGNORECASE | re.DOTALL)

    if not match:

        return process_flow_execution(spn, knowledge)

    represented_events = match.group(1).strip()

    #
    # Split represented events
    #

    components = [x.strip() for x in represented_events.split(",") if x.strip()]

    #
    # Structural fallback:
    # only one target -> probably process flow
    #

    if len(components) <= 1:

        print("Structural relation not detected. " "Executing process flow.")

        return process_flow_execution(spn, knowledge)

    #
    # Verify that targets exist
    #

    target_transitions = []

    for component in components:

        found = None

        for transition in spn.transitions:

            if transition.label.lower() == component.lower():

                found = transition
                break

        if found is None:

            for transition in spn.transitions:

                if component.lower() in transition.label.lower():

                    found = transition
                    break

        if found:

            target_transitions.append(found)

    if len(target_transitions) == 0:

        print("No structural target transitions found. " "Using process flow fallback.")

        return process_flow_execution(spn, knowledge)

    #
    # Create structural event group
    #

    structural_place_label = f"STRUCTURAL_{event_group}"

    existing_place = None

    for place in spn.places:

        if place.label.lower() == structural_place_label.lower():

            existing_place = place
            break

    if existing_place is None:

        structural_place = Place(structural_place_label, 1)

        structural_place.color = "darkcyan"

        structural_place.source = id

        structural_place.event_group = event_group

        spn.add_place(structural_place)

    else:

        structural_place = existing_place

    #
    # Connect structural group
    #

    for transition in target_transitions:

        spn.add_output_arc(structural_place, transition, color="darkcyan")

        transition.color = "darkcyan"

        transition.source = id

        transition.structural_group = event_group

    #
    # Metadata
    #

    structural_place.members = [t.label for t in target_transitions]

    print(
        f"Integrated structural knowledge: "
        f"{event_group} -> "
        f"{[t.label for t in target_transitions]}"
    )

    return spn

def process_flow_execution(spn, knowledge):
    """
    Integrates process flow relations into an SPN.
    """

    print("Executing process flow integration:", knowledge)

    if knowledge is None:
        return spn

    knowledge = str(knowledge).strip()

    #
    # Parse flow
    #

    if "->" in knowledge:
        flow = [x.strip() for x in knowledge.split("->") if x.strip()]

    else:
        match = re.search(
            r"IF\s+(.*?)\s+THEN\s+(.*)",
            knowledge,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if match:
            flow = [match.group(1).strip(), match.group(2).strip()]
        else:
            print("No process flow detected.")
            return spn

    if len(flow) < 2:
        return spn

    #
    # Resolve transitions
    #

    resolved = []

    for activity in flow:

        transition = None

        # exact match
        for t in spn.transitions:
            if t.label.lower() == activity.lower():
                transition = t
                break

        # partial match
        if transition is None:
            for t in spn.transitions:
                if activity.lower() in t.label.lower():
                    transition = t
                    break

        if transition is None:
            print(f"Transition not found: {activity}")
            continue

        resolved.append(transition)

    if len(resolved) < 2:
        print("Not enough transitions found.")
        return spn

    #
    # Connect transitions sequentially
    #

    for i in range(len(resolved) - 1):

        source = resolved[i]
        target = resolved[i + 1]

        #
        # Avoid duplicate connection
        #

        already_connected = False

        for place in spn.places:
            outputs = getattr(place, "output_arcs", [])

            if source in outputs and target in outputs:
                already_connected = True
                break

        if already_connected:
            continue

        #
        # Create intermediate place
        #

        place = Place(
            f"PF_{source.label}_TO_{target.label}",
            0,
        )

        place.color = "orange"

        spn.add_place(place)

        #
        # source -> place
        #

        spn.add_input_arc(source, place, color="orange")

        #
        # place -> target
        #

        spn.add_output_arc(place, target, color="orange")

        print(f"Connected {source.label} -> {target.label}")

    return spn