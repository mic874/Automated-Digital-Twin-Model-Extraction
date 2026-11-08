import re


def transition_has_distribution(transition):
    """
    Returns True if the transition already models a
    reliability distribution.
    """
    return getattr(transition, "distribution", None) is not None


def get_transition_output_places(spn, transition):
    """
    Returns places connected from a transition.
    """

    places = []

    for arc in transition.output_arcs:

        if arc.to_place is not None:
            places.append(arc.to_place)

    return places


def transition_has_condition(transition):
    """
    Checks if a transition already has a guard.
    """

    return (
        hasattr(transition, "condition_label")
        and transition.condition_label is not None
        and transition.condition_label != ""
    )


def get_transition_by_label(self, label: str):

    target = normalize_identifier(label)

    for transition in self.transitions:

        if normalize_identifier(transition.label) == target:
            return transition

    return None


def normalize_identifier(text):
    """
    Robust identifier normalization.
    """

    if text is None:
        return ""

    tokens = re.findall(r"[a-z0-9]+", str(text).lower())

    if not tokens:
        return ""

    # Remove repeated prefixes/groups
    changed = True

    while changed:

        changed = False

        n = len(tokens)

        # Try every possible repeated block
        for size in range(1, n // 2 + 1):

            first = tokens[:size]
            second = tokens[size : 2 * size]

            if first == second:

                tokens = tokens[size:]
                changed = True
                break

    return "".join(tokens)


def get_component_transitions(spn, component):
    """
    Return all operational transitions belonging to a component.
    """

    component_norm = normalize_identifier(component)

    matches = []

    for transition in spn.transitions:

        label = getattr(transition, "label", "")

        if not label:
            continue

        upper = label.upper()

        # Ignore reliability transitions
        if upper.startswith("FAIL_") or upper.startswith("RESTORE_"):
            continue

        label_norm = normalize_identifier(label)

        # Match either direction to allow labels containing
        # repeated state names, prefixes, etc.
        if component_norm in label_norm or label_norm in component_norm:
            matches.append(transition)

    return matches


def get_transition(spn, label):
    """
    Returns transition by label.
    """

    for transition in spn.transitions:
        if transition.label == label:
            return transition

    return None


def get_place(spn, label):
    """
    Returns place by label.
    """

    for place in spn.places:
        if place.label == label:
            return place

    return None


def get_transition_input_places(spn, transition):
    """
    Returns places connected into a transition.

    Structure:
        Place -> Transition
    """

    places = []

    for arc in transition.input_arcs:

        if arc.from_place is not None:
            places.append(arc.from_place)

    return places
