import re
from pyspn.components.spn import SPN, Place, Transition
import pandas as pd
import json


def integrate_temporal_and_probabilistic(spn, knowledge, id):
    """
    Integrate temporal and probabilistic knowledge.
    Behaviour:
    - If transition exists:
          update its distribution/weight
    - If transition does not exist:
          create transition
    - Distribution:
          creates timed transition (T)
    - Weight:
          creates immediate transition (I)
    """

    print("inside integrate temporal/probabilistic --------", knowledge)

    if knowledge is None:
        return spn

    knowledge = str(knowledge).strip()

    #
    # Extract IF event
    #

    match = re.search(r"IF\s+(.*?)\s+THEN", knowledge, flags=re.IGNORECASE | re.DOTALL)

    if not match:

        print(f"Cannot extract temporal event: {knowledge}")

        return spn

    event = match.group(1).strip()

    #
    # Extract THEN information
    #

    match = re.search(r"THEN\s+(.*)$", knowledge, flags=re.IGNORECASE | re.DOTALL)

    if not match:

        print(f"Cannot extract temporal information: {knowledge}")

        return spn

    temporal_information = match.group(1).strip()

    #
    # Find transition
    #

    transition = None

    for t in spn.transitions:

        if t.label.lower() == event.lower():

            transition = t
            break

    #
    # Create transition if missing
    #

    if transition is None:

        print(f"No transition found for {event}. Creating.")

        transition = Transition(event, "I")

        transition.color = "darkorange"

        transition.source = id

        spn.add_transition(transition)

    #
    # Distribution handling
    #

    distribution_match = re.search(
        r"distribution\s*=\s*([a-zA-Z_]+)", temporal_information, flags=re.IGNORECASE
    )

    if distribution_match:

        distribution_name = distribution_match.group(1).strip()

        parameters = {}

        #
        # Extract parameters
        #

        parameter_matches = re.findall(
            r"([a-zA-Z_]+)\s*=\s*([^,]+)", temporal_information
        )

        for key, value in parameter_matches:

            if key.lower() != "distribution":

                parameters[key.strip()] = value.strip()

        #
        # Timed transition
        #

        transition.t_type = "T"

        transition.distribution = {distribution_name: parameters}

        transition.color = "darkorange"

        transition.source = id

        print(f"Added distribution {distribution_name} " f"to {transition.label}")

        return spn

    #
    # Weight / probability handling
    #

    weight_match = re.search(
        r"(weight|probability)\s*=\s*([0-9.]+)\s*%?",
        temporal_information,
        flags=re.IGNORECASE,
    )

    if weight_match:

        value_type = weight_match.group(1).lower()

        weight = float(weight_match.group(2))

        #
        # Convert percentage probability
        # to decimal firing weight
        #

        if value_type == "probability":

            if "%" in temporal_information:

                weight = weight / 100.0

        #
        # Immediate transition
        #

        transition.t_type = "I"

        transition.weight = "w = " + str(weight)

        transition.color = "darkorange"

        transition.source = id

        transition.probability = weight

        print(f"Added probability/weight {weight} " f"to {transition.label}")

        return spn

    #
    # Unsupported format
    #

    print(f"Unknown temporal/probabilistic format: " f"{temporal_information}")

    return spn
