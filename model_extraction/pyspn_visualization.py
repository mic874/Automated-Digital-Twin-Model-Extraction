from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pyspn.components import spn_visualization

from copy import deepcopy

from model_extraction.distributions import DistributionFit

import re

from copy import deepcopy


def remove_duplicate_prefix(label):
    """
    Remove duplicated resource prefixes anywhere in a name.
    """

    if not isinstance(label, str):
        return label

    parts = label.split("_")

    cleaned = []

    i = 0

    while i < len(parts):

        # Detect pattern:
        # something_something_something_something
        # where first two tokens repeat next two tokens
        if (
            i + 3 < len(parts)
            and parts[i] != "XOR"
            and parts[i : i + 2] == parts[i + 2 : i + 4]
        ):

            cleaned.extend(parts[i : i + 2])
            i += 4

        else:

            cleaned.append(parts[i])
            i += 1

    return "_".join(cleaned)


def normalize_path_name(label):
    """
    Removes duplicated path prefixes.
    """

    if not isinstance(label, str):
        return label

    label = label.replace("/", "_")

    # remove repeated underscores
    label = re.sub(r"_+", "_", label)

    return label.strip("_")


def clean_pyspn_name(label):
    """
    Complete name cleanup pipeline.
    """

    label = label.lower()

    label = remove_duplicate_prefix(label)

    label = normalize_path_name(label)

    return label


def prepare_for_pyspn_visualization(spn):
    """
    Prepare SPN for PySPN visualization.
    """

    spn = deepcopy(spn)

    # -----------------------------------------
    # Clean transitions
    # -----------------------------------------

    for transition in spn.transitions:

        if hasattr(transition, "label"):

            old_label = transition.label

            transition.label = clean_pyspn_name(transition.label)

            if old_label != transition.label:
                print(f"Transition renamed: " f"{old_label} -> {transition.label}")

        dist = getattr(transition, "distribution", None)

        if dist is not None and hasattr(dist, "name") and hasattr(dist, "parameters"):

            transition.distribution = {dist.name: dist.parameters}

    # -----------------------------------------
    # Clean places
    # -----------------------------------------

    for place in spn.places:

        if hasattr(place, "label"):

            old_label = place.label

            place.label = clean_pyspn_name(place.label)

            if old_label != place.label:
                print(f"Place renamed: " f"{old_label} -> {place.label}")

    return spn


def visualize_pyspn_model(spn, file):

    visualization_spn = prepare_for_pyspn_visualization(spn)

    # from model_extraction.distributions import DistributionFit

    for t in visualization_spn.transitions:
        if isinstance(getattr(t, "distribution", None), DistributionFit):
            print("NOT CONVERTED:", t.label)
    

    for t in visualization_spn.transitions:
        
        if t.t_type == "T" and t.distribution is not None:
            print(t.label, type(t.distribution))
        
    spn_visualization.draw_spn(visualization_spn, file, show=True)

    return spn


