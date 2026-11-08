import re
from pyspn.components.spn import SPN, Place, Transition
import pandas as pd
import json


def integrate_process_flow(spn, knowledge, id):
    """
    Integrate a structural rule into an existing SPN.
    Existing transitions and places are reused whenever possible.
    Duplicate arcs are avoided.
    """

    # --------------------------------------------------------
    # Parse sentence
    # --------------------------------------------------------
  
    
    left_expr, right_expr = parse_if_then_complex(knowledge)

    if left_expr is None or right_expr is None:
        return spn

    # --------------------------------------------------------
    # Parse expressions
    # --------------------------------------------------------

    left_type, left_labels = parse_expression(left_expr)
    right_type, right_labels = parse_expression(right_expr)

    # --------------------------------------------------------
    # Reuse / create transitions
    # --------------------------------------------------------

    left = [
        get_or_create_transition(spn, label, id, color="forestgreen")
        for label in left_labels
    ]

    right = [
        get_or_create_transition(spn, label, id, color="forestgreen")
        for label in right_labels
    ]

    # ========================================================
    # SINGLE -> SINGLE
    # ========================================================

    if left_type == "SINGLE" and right_type == "SINGLE":

         # A -> XOR_A (split place) -> choice_A_to_B -> place before B
        connect_via_places(spn, left[0], right[0], id, color="forestgreen")

        return spn

        source = left[0]
        target = right[0]

        # 1. First: reuse an existing input place of target
        existing_places = [
            arc.from_place
            for arc in target.input_arcs
            if getattr(arc, "from_place", None) is not None
        ]

        if existing_places:

            # Prefer an existing XOR place
            xor_places = [
                p for p in existing_places
                if (p.label or "").upper().startswith("XOR")
            ]

            place = xor_places[0] if xor_places else existing_places[0]

            # Connect source to the existing place
            if not any(
                arc.to_place == place
                for arc in source.output_arcs
            ):
                spn.add_output_arc(
                    source, place, color="forestgreen"
                )

        else:

            # 2. No input place before target:
            # check for an existing XOR split after source
            existing_xor = find_existing_xor_split(spn, source)

            if existing_xor is not None:

                extend_xor_split(
                    spn, source, target, id,
                    color="forestgreen"
                )

            else:

                # 3. Neither exists: use original connection logic
                connect_transition_to_transition(
                    spn, source, target, id,
                    color="forestgreen"
                )

        return spn

    # ========================================================
    # SINGLE -> AND
    # ========================================================

    if left_type == "SINGLE" and right_type == "AND":

        if connect_and_split_via_places(spn, left[0], right, id) is not None:
            return spn

        # Fallback (source has ambiguous output places): old logic
        and_transition = get_or_create_transition(
            spn, f"{left[0].label}_AND_SPLIT", id, color="forestgreen"
        )
        connect_transition_to_transition(spn, left[0], and_transition, id)
        for transition in right:
            connect_transition_to_transition(spn, and_transition, transition, id)

        return spn

    # ========================================================
    # SINGLE -> OR
    # ========================================================

    if left_type == "SINGLE" and right_type == "OR":

        for target in right:

            connect_via_places(spn, left[0], target, id, color="forestgreen")

        return spn

    # ========================================================
    # AND -> SINGLE
    # ========================================================

    if left_type == "AND" and right_type == "SINGLE":

        if connect_and_join_via_places(spn, left, right[0], id) is not None:
            return spn

        # Fallback: old logic
        and_transition = get_or_create_transition(
            spn, f"{right[0].label}_AND_Join", id, color="forestgreen"
        )
        for transition in left:
            place = get_or_create_place(
                spn, f"{transition.label}_TO_{and_transition.label}"
            )
            place.color = "forestgreen"
            place.source = id
            if not any(arc.to_place == place for arc in transition.output_arcs):
                spn.add_output_arc(transition, place, color="forestgreen")
            if not any(arc.from_place == place for arc in and_transition.input_arcs):
                spn.add_input_arc(place, and_transition, color="forestgreen")
        connect_transition_to_transition(spn, and_transition, right[0], id)

        return spn

    # ========================================================
    # OR -> SINGLE
    # ========================================================

    if left_type == "OR" and right_type == "SINGLE":

        for source in left:

            connect_via_places(spn, source, right[0], id, color="forestgreen")

        return spn

    # ========================================================
    # AND -> AND
    # ========================================================

    if left_type == "AND" and right_type == "AND":
        if connect_and_join_to_targets_via_places(
            spn, left, right, id, as_and=True
        ) is not None:
            return spn
        else:

            and_transition_label = "_AND_".join(left_labels)

            and_transition = get_or_create_transition(
                spn, and_transition_label, id, color="forestgreen"
            )

            for transition in left:

                connect_transition_to_transition(
                    spn, transition, and_transition, id, color="forestgreen"
                )

            connect_and_split(spn, and_transition, right, id, color="forestgreen")

            return spn

    # ========================================================
    # AND -> OR
    # ========================================================

    if left_type == "AND" and right_type == "OR":
        if connect_and_join_to_targets_via_places(
            spn, left, right, id, as_and=False
        ) is not None:
            return spn
        else:

            and_transition_label = "_AND_".join(left_labels)

            and_transition = get_or_create_transition(
                spn, and_transition_label, id, color="forestgreen"
            )

            for transition in left:

                connect_transition_to_transition(
                    spn, transition, and_transition, id, color="forestgreen"
                )

            connect_xor_split(spn, and_transition, right, id, color="forestgreen")

            return spn

    # ========================================================
    # OR -> AND
    # ========================================================


    if left_type == "OR" and right_type == "AND":
        connect_or_join_and_split(spn, left, right, id)

        return spn
        #for source in left:
        #    connect_and_split_via_places(spn, source, right, id)
        #return spn

        # A OR B -> common XOR place / gateway
        xor_gateway = connect_xor_join(
            spn, left, None, id, return_transition=True, color="forestgreen"
        )

        # AND transition -> C and D

        connect_and_split_xor_and(spn, xor_gateway, right)

        return spn

    # ========================================================
    # OR -> OR
    # ========================================================

    if left_type == "OR" and right_type == "OR":
        for source in left:
            for target in right:
                connect_via_places(spn, source, target, id)
        return spn

        gateway = connect_xor_join(spn, left, None, id, return_transition=True)

        connect_xor_split(spn, gateway, right, id)

        return spn

    return spn


def extend_existing_xor_join(
    spn, sources, target, id, color="forestgreen"
):
    """
    Reuses an existing XOR place immediately before target.

    Adds missing source transitions to the existing place.
    Creates a new XOR join only if no existing input place exists.
    """

    existing_places = []

    for arc in target.input_arcs:

        place = getattr(arc, "from_place", None)

        if place is not None and place not in existing_places:
            existing_places.append(place)

    # Prefer an existing XOR place
    xor_places = [
        p for p in existing_places
        if (p.label or "").upper().startswith("XOR")
    ]

    if xor_places:

        xor_place = xor_places[0]

    elif existing_places:

        # Reuse an existing input place if no XOR place exists
        xor_place = existing_places[0]

    else:

        # No existing input place: create XOR join
        return connect_xor_join(
            spn, sources, target, id,
            color=color
        )

    # Add missing incoming source connections
    for source in sources:

        already_connected = any(
            arc.to_place == xor_place
            for arc in source.output_arcs
        )

        if not already_connected:

            spn.add_output_arc(
                source,
                xor_place,
                color=color
            )

    xor_place.color = color
    xor_place.source = id

    return xor_place


def extend_existing_xor_split(
    spn, source, targets, id, color="forestgreen"
):
    """
    Reuses ANY existing output place of source.

    Adds all missing target transitions to that place.
    Creates a new XOR place only if source has no output place.
    """

    existing_places = []

    # Find all existing output places of source
    for arc in source.output_arcs:

        place = getattr(arc, "to_place", None)

        if place is not None and place not in existing_places:
            existing_places.append(place)

    if existing_places:

        # Prefer an existing place already connected to
        # one or more of the requested targets.
        matching_places = [
            place
            for place in existing_places
            if any(
                input_arc.from_place == place
                for target in targets
                for input_arc in target.input_arcs
            )
        ]

        if matching_places:
            xor_place = matching_places[0]
        else:
            xor_place = existing_places[0]

    else:

        # No existing output place: create XOR split
        return connect_xor_split(
            spn, source, targets, id, color
        )

    # Add missing target connections
    for target in targets:

        already_connected = any(
            input_arc.from_place == xor_place
            for input_arc in target.input_arcs
        )

        if not already_connected:

            spn.add_input_arc(
                xor_place,
                target,
                color=color
            )

    xor_place.color = color
    xor_place.source = id

    return xor_place


def find_existing_xor_join(spn, target):
    """
    Finds an existing XOR place immediately before target.
    """

    for arc in target.input_arcs:

        place = arc.from_place

        if place is None:
            continue

        if (
            place.label.startswith("XOR_JOIN_")
            or place.label.startswith("XOR_SPLIT_")
            or place.label.startswith("XOR_")
        ):
            return place

    return None

def extend_xor_join(spn, source, target, id, color="forestgreen"):
    """
    Adds source as another incoming alternative to an existing
    XOR place immediately before target.

    Reuses the existing XOR place and avoids duplicate arcs.
    """

    xor_place = find_existing_xor_join(spn, target)

    if xor_place is None:
        return None

    # Check whether source is already connected to the XOR place
    already_connected = any(
        arc.to_place == xor_place
        for arc in source.output_arcs
    )

    if not already_connected:

        spn.add_output_arc(
            source,
            xor_place,
            color=color
        )

    xor_place.color = color
    xor_place.source = id

    return xor_place

def connect_to_existing_input_places(
    spn, source, targets, id, color="forestgreen"
):
    """
    Connects source directly to the existing individual input places
    of the target transitions.

    Does not create XOR places or intermediate places.
    """

    for target in targets:

        input_place = get_place(
            spn,
            f"{target.label}_in"
        )

        if input_place is None:
            print(
                f"WARNING: No existing input place for {target.label}"
            )
            continue

        # Avoid duplicate source -> input place arcs
        already_connected = any(
            arc.to_place == input_place
            for arc in source.output_arcs
        )

        if not already_connected:
            spn.add_output_arc(
                source,
                input_place,
                color=color
            )

        input_place.color = color
        input_place.source = id

    return spn
    

def get_or_create_connection_place(
    spn,
    source,
    target,
    id=None,
    color="forestgreen"
):
    """
    Reuses existing places according to the initial SPN naming convention.

    Priority:
    1. Target input place: {target.label}_in
    2. Existing source-target place: {source.label}_TO_{target.label}
    3. Existing source-target loop place: {source.label}_to_{target.label}
    4. Create a new connection place.
    """

    # ------------------------------------------------
    # 1. Reuse the target's individual input place
    # ------------------------------------------------

    input_place = spn.get_place_by_label(
        f"{target.label}_in"
    )

    if input_place is not None:
        return input_place

    # ------------------------------------------------
    # 2. Reuse existing connection place
    # ------------------------------------------------

    possible_labels = [
        f"{source.label}_TO_{target.label}",
        f"{source.label}_to_{target.label}"
    ]

    for label in possible_labels:

        place = spn.get_place_by_label(label)

        if place is not None:
            return place

    # ------------------------------------------------
    # 3. Create a new place only if necessary
    # ------------------------------------------------

    label = f"{source.label}_TO_{target.label}"

    place = get_or_create_place(spn, label)

    place.color = color
    place.source = id

    return place


def find_existing_xor_split(spn, source):
    """
    Finds an existing XOR split place belonging to source.
    """

    for arc in source.output_arcs:

        place = arc.to_place

        if place is None:
            continue

        if place.label.startswith("XOR_SPLIT_"):

            return place

        # Also support XOR places created by the initial SPN builder
        if place.label == f"XOR_{source.label}":

            return place

    return None


def extend_xor_split(spn, source, target, id, color="forestgreen"):
    """
    Adds target as another alternative to an existing XOR split.

    Does not create a new XOR place.
    """

    xor_place = find_existing_xor_split(spn, source)

    if xor_place is None:
        return None

    # Check whether target is already connected
    for arc in target.input_arcs:

        if arc.from_place == xor_place:
            return xor_place

    # Add target as another XOR alternative
    spn.add_input_arc(
        xor_place,
        target,
        color=color
    )

    xor_place.color = color
    xor_place.source = id

    return xor_place

def get_or_create_transition(spn, label, id, t_type="I", color="forestgreen"):
    """
    Returns an existing transition (exact, then case-insensitive match)
    or creates a new one. color / source are only set if given.
    """

    label = label.strip()

    transition = spn.get_transition_by_label(label)

    if transition is None:

        for candidate in spn.transitions:

            if (candidate.label or "").strip().lower() == label.lower():
                transition = candidate
                break

    if transition is not None:
        return transition

    transition = Transition(label, t_type)

    if color is not None:
        transition.color = color

    if id is not None:
        transition.source = id

    spn.add_transition(transition)

    return transition


# ============================================================
# CONNECTIONS VIA PLACES (never directly into a timed transition)
# ============================================================

def _is_immediate(transition):

    return getattr(transition, "t_type", None) == "I"


def _consumers_of(spn, place):
    """
    All (arc, transition) pairs for arcs leaving the place.
    """

    return [
        (arc, t)
        for t in spn.transitions
        for arc in t.input_arcs
        if getattr(arc, "from_place", None) is place
    ]


def _is_split_place(spn, place):
    """
    A place that only feeds immediate transitions (XOR split place).
    """

    consumers = _consumers_of(spn, place)

    return bool(consumers) and all(_is_immediate(t) for _, t in consumers)


def _remove_arc(spn, arc):
    """
    Removes an arc. Uses spn.remove_arc if pyspn has it, otherwise
    removes the arc object from every arc list it can be found in.
    """

    remove = getattr(spn, "remove_arc", None)

    if callable(remove):

        try:
            remove(arc)
            return
        except Exception:
            pass

    holders = list(spn.transitions) + list(spn.places) + [spn]

    for holder in holders:

        for attr in ("input_arcs", "output_arcs", "arcs"):

            container = getattr(holder, attr, None)

            if isinstance(container, list):
                container[:] = [a for a in container if a is not arc]

            elif isinstance(container, set):
                container.discard(arc)

def find_input_place(spn, target, id, color="forestgreen"):
    """
    The existing place directly before target:
    1. an existing XOR place (not a split place)
    2. <target>_in
    3. any other existing input place
    4. a new <target>_in (only if target has no input place at all)
    """
    existing = []

    for arc in target.input_arcs:
        place = getattr(arc, "from_place", None)
        if place is not None and not any(place is p for p in existing):
            existing.append(place)

    xor_places = [
        p for p in existing
        if (p.label or "").upper().startswith("XOR")
        and not _is_split_place(spn, p)
    ]

    if xor_places:
        return xor_places[0]

    place = spn.get_place_by_label(f"{target.label}_in")

    if place is not None:
        return place

    if existing:
        return existing[0]

    place = get_or_create_place(spn, f"{target.label}_in")
    spn.add_input_arc(place, target, color=color)

    return place

def _is_connected(spn, source, target_in):
    """
    True if the source already reaches target_in, directly or via an
    immediate transition behind its split place.
    """

    for arc in source.output_arcs:

        place = getattr(arc, "to_place", None)

        if place is None:
            continue

        if place is target_in:
            return True

        for _, consumer in _consumers_of(spn, place):

            if _is_immediate(consumer) and any(
                getattr(a, "to_place", None) is target_in
                for a in consumer.output_arcs
            ):
                return True

    return False


def convert_to_xor_split(spn, source, direct_place, id):
    """
    source -> direct_place -> X   becomes
    source -> XOR_source -> choice_source_to_X -> direct_place -> X

    direct_place stays the input place of X. The rewired parts are
    left uncolored (they are not new knowledge).
    """

    consumers = [t for _, t in _consumers_of(spn, direct_place)]

    for arc in [
        a for a in source.output_arcs
        if getattr(a, "to_place", None) is direct_place
    ]:
        _remove_arc(spn, arc)

    xor_place = get_or_create_place(spn, f"XOR_{source.label}")

    spn.add_output_arc(source, xor_place)

    labels = [t.label for t in consumers] or [direct_place.label]

    for label in labels:

        immediate = get_or_create_transition(
            spn, f"choice_{source.label}_to_{label}",
            None, t_type="I", color=None
        )

        spn.add_input_arc(xor_place, immediate)

        spn.add_output_arc(immediate, direct_place)

    return xor_place


def find_or_make_split_place(spn, source, id):
    """
    The split place after source. Converts a single direct output place
    into a XOR split. Returns None if source has no output place (or an
    ambiguous parallel one).
    """

    out_places = []

    for arc in source.output_arcs:

        place = getattr(arc, "to_place", None)

        if place is not None and not any(place is p for p in out_places):
            out_places.append(place)

    for place in out_places:

        if _is_split_place(spn, place):
            return place

    if len(out_places) == 1:
        return convert_to_xor_split(spn, source, out_places[0], id)

    return None

def connect_or_join_and_split(spn, sources, targets, id, color="forestgreen"):
    """
    IF s1 OR s2 THEN t1 AND t2

    s_i -> split place of s_i -> choice_s_i_to_<join> -> OR-join place
        -> AND-split transition -> place before t1 / place before t2
    """
    # Resolve all split places first, so nothing is half-built on failure
    split_places = []

    for source in sources:
        place = get_split_place(spn, source, id, color)
        if place is None:
            return None
        split_places.append(place)

    # --- OR-join place (shared by all sources) ---
    join_label = "XOR_JOIN_" + "_".join(s.label for s in sources)

    join_place = get_or_create_place(spn, join_label)
    join_place.color = color
    join_place.source = id

    # --- sources -> split place -> choice -> OR-join place ---
    for source, split_place in zip(sources, split_places):

        choice = get_or_create_transition(
            spn, f"choice_{source.label}_to_{join_label}",
            id, t_type="I", color=color
        )

        if not any(a.from_place is split_place for a in choice.input_arcs):
            spn.add_input_arc(split_place, choice, color=color)

        if not any(a.to_place is join_place for a in choice.output_arcs):
            spn.add_output_arc(choice, join_place, color=color)

        split_place.color = color
        split_place.source = id

    # --- one AND-split transition after the OR-join place ---
    and_split = get_or_create_transition(
        spn,
        f"AND_SPLIT_{'_OR_'.join(s.label for s in sources)}"
        f"_TO_{'_AND_'.join(t.label for t in targets)}",
        id, t_type="I", color=color
    )

    if not any(a.from_place is join_place for a in and_split.input_arcs):
        spn.add_input_arc(join_place, and_split, color=color)

    # --- AND-split transition -> existing place before each target ---
    for target in targets:

        target_in = find_input_place(spn, target, id, color)

        if not any(a.to_place is target_in for a in and_split.output_arcs):
            spn.add_output_arc(and_split, target_in, color=color)

        target_in.color = color
        target_in.source = id

    return and_split

def connect_via_places(spn, source, target, id, color="forestgreen"):
    """
    source -> (split place) -> immediate transition -> target_in -> target

    Never connects a place directly to the target transition. The
    resulting connection is colored, whether it is new or existing.
    """

    target_in = find_input_place(spn, target, id, color)

    if _is_connected(spn, source, target_in):

        _mark_connection(spn, source, target_in, id, color)

        return target_in

    #split_place = find_or_make_split_place(spn, source, id)
    split_place = get_split_place(spn, source, id, color)

    if split_place is not None:

        immediate = get_or_create_transition(
            spn, f"choice_{source.label}_to_{target.label}",
            id, t_type="I", color=color
        )

        if not any(a.from_place is split_place for a in immediate.input_arcs):
            spn.add_input_arc(split_place, immediate, color=color)

        if not any(a.to_place is target_in for a in immediate.output_arcs):
            spn.add_output_arc(immediate, target_in, color=color)

    elif source is target:

        loop_place = get_or_create_place(
            spn, f"{source.label}_to_{target.label}"
        )

        spn.add_output_arc(source, loop_place, color=color)

        immediate = get_or_create_transition(
            spn, f"loop_{source.label}_to_{target.label}",
            id, t_type="I", color=color
        )

        spn.add_input_arc(loop_place, immediate, color=color)
        spn.add_output_arc(immediate, target_in, color=color)

        loop_place.color = color
        loop_place.source = id

    else:

        spn.add_output_arc(source, target_in, color=color)

    target_in.color = color
    target_in.source = id

    _mark_connection(spn, source, target_in, id, color)

    return target_in


def _mark_connection(spn, source, target_in, id, color="forestgreen"):
    """
    Colors the existing connection source -> (split place) ->
    immediate transition -> target_in (or the direct arc) and sets
    source on the transition and the places.
    """

    def mark(obj):

        obj.color = color

        if not hasattr(obj, "from_place") and not hasattr(obj, "to_place"):
            obj.source = id

    for out_arc in source.output_arcs:

        place = getattr(out_arc, "to_place", None)

        if place is None:
            continue

        if place is target_in:

            mark(out_arc)
            mark(place)

            continue

        for in_arc, consumer in _consumers_of(spn, place):

            if not _is_immediate(consumer):
                continue

            for imm_out in consumer.output_arcs:

                if getattr(imm_out, "to_place", None) is target_in:

                    mark(out_arc)
                    mark(place)
                    mark(in_arc)
                    mark(consumer)
                    mark(imm_out)
                    mark(target_in)

def get_or_create_place(spn, label, tokens=0):
    """
    Returns an existing place if it already exists.
    Otherwise creates and adds a new place to the SPN.
    """

    label = label.strip()

    place = spn.get_place_by_label(label)

    if place is not None:
        return place

    place = Place(label, tokens)

    spn.add_place(place)

    return place

def get_split_place(spn, source, id, color="forestgreen"):
    """
    Returns the existing OR-split place after source.
    1. an existing split place (feeds only immediate transitions)
    2. a dangling output place without consumers
    3. a single direct output place, converted into a XOR split
    4. no output place at all: creates XOR_<source>
    Returns None only if source has several ambiguous output places.
    """
    out_places = []

    for arc in source.output_arcs:
        place = getattr(arc, "to_place", None)
        if place is not None and not any(place is p for p in out_places):
            out_places.append(place)

    if not out_places:
        place = get_or_create_place(spn, f"XOR_{source.label}")
        spn.add_output_arc(source, place, color=color)
        return place

    for place in out_places:
        if _is_split_place(spn, place):
            return place

    for place in out_places:
        if not _consumers_of(spn, place):
            return place

    return find_or_make_split_place(spn, source, id)


def connect_and_split_via_places(spn, source, targets, id, color="forestgreen"):
    """
    IF source THEN t1 AND t2 ...
    source -> split place -> choice_source_to_t1_AND_t2 -> t1_in, t2_in
    Reuses the existing split place of source.
    """
    split_place = get_split_place(spn, source, id, color)

    if split_place is None:
        return None

    target_ins = [find_input_place(spn, t, id, color) for t in targets]

    immediate = get_or_create_transition(
        spn,
        f"choice_{source.label}_to_{'_AND_'.join(t.label for t in targets)}",
        id, t_type="I", color=color
    )

    if not any(a.from_place is split_place for a in immediate.input_arcs):
        spn.add_input_arc(split_place, immediate, color=color)

    for place in target_ins:
        if not any(a.to_place is place for a in immediate.output_arcs):
            spn.add_output_arc(immediate, place, color=color)
        place.color = color
        place.source = id

    split_place.color = color
    split_place.source = id

    return immediate


def connect_and_join_via_places(spn, sources, target, id, color="forestgreen"):
    """
    IF s1 AND s2 THEN target
    s1 -> split place 1 --\
                           join_s1_AND_s2_to_target -> target_in
    s2 -> split place 2 --/
    Reuses the existing split places of all sources.
    """
    split_places = []

    for source in sources:
        place = get_split_place(spn, source, id, color)
        if place is None:
            return None
        split_places.append(place)

    target_in = find_input_place(spn, target, id, color)

    immediate = get_or_create_transition(
        spn,
        f"join_{'_AND_'.join(s.label for s in sources)}_to_{target.label}",
        id, t_type="I", color=color
    )

    for place in split_places:
        if not any(a.from_place is place for a in immediate.input_arcs):
            spn.add_input_arc(place, immediate, color=color)
        place.color = color
        place.source = id

    if not any(a.to_place is target_in for a in immediate.output_arcs):
        spn.add_output_arc(immediate, target_in, color=color)

    target_in.color = color
    target_in.source = id

    return immediate

def connect_and_join_to_targets_via_places(
    spn, sources, targets, id, as_and, color="forestgreen"
):
    """
    Join over the split places of all sources, output into the existing
    input place(s) of the targets.

    as_and=True : one join transition -> all target places (AND split)
    as_and=False: one join transition per target; they compete for the
                  same tokens, so exactly one fires (OR split)
    """
    split_places = []

    for source in sources:
        place = get_split_place(spn, source, id, color)
        if place is None:
            return None
        split_places.append(place)

    src_label = "_AND_".join(s.label for s in sources)

    groups = [targets] if as_and else [[t] for t in targets]

    for group in groups:

        tgt_label = "_AND_".join(t.label for t in group)

        join = get_or_create_transition(
            spn, f"join_{src_label}_to_{tgt_label}",
            id, t_type="I", color=color
        )

        for place in split_places:
            if not any(a.from_place is place for a in join.input_arcs):
                spn.add_input_arc(place, join, color=color)
            place.color = color
            place.source = id

        for target in group:
            target_in = find_input_place(spn, target, id, color)
            if not any(a.to_place is target_in for a in join.output_arcs):
                spn.add_output_arc(join, target_in, color=color)
            target_in.color = color
            target_in.source = id

    return spn

def connect_and_split_xor_and(spn, source, targets, color="forestgreen"):
    """
    Creates an AND split
    """

    for target in targets:

        place_label = f"{source.label}_TO_{target.label}"

        place = spn.get_place_by_label(place_label)

        if place is None:

            place = Place(place_label, 0)

            place.color = color

            place.source = id

            spn.add_place(place)

        # source transition -> place

        if not any(arc.to_place == place for arc in source.output_arcs):

            spn.add_output_arc(source, place, color=color)

        # place -> target transition

        if not any(arc.from_place == place for arc in target.input_arcs):

            spn.add_input_arc(place, target, color=color)

    return spn


def connect_and_split(spn, source, targets, id, color="forestgreen"):
    """
    Creates an AND parallel split.
    """

    place_label = (
        f"AND_SPLIT_{source.label}_TO_" f"{'_'.join(t.label for t in targets)}"
    )

    # ------------------------------------------------
    # Create / reuse split place
    # ------------------------------------------------

    split_place = get_or_create_place(spn, place_label)

    split_place.color = color

    split_place.source = id

    # ------------------------------------------------
    # source -> split place
    # ------------------------------------------------

    if not any(arc.to_place == split_place for arc in source.output_arcs):

        spn.add_output_arc(source, split_place, color=color)

    # ------------------------------------------------
    # split place -> all targets
    # ------------------------------------------------

    for target in targets:

        if not any(arc.from_place == split_place for arc in target.input_arcs):

            spn.add_input_arc(split_place, target, color=color)

    return split_place


def connect_and_join(
    spn, sources, target, id, return_transition=False, color="forestgreen"
):
    """
    Creates an AND synchronization join.
    """

    source_labels = "_".join(t.label for t in sources)

    target_label = target.label if target is not None else "GATEWAY"

    place_label = f"AND_JOIN_{source_labels}_TO_{target_label}"

    # ------------------------------------------------
    # Create / reuse synchronization place
    # ------------------------------------------------

    join_place = get_or_create_place(spn, place_label)

    join_place.color = color

    join_place.source = id

    # ------------------------------------------------
    # All sources -> join place
    # ------------------------------------------------

    for source in sources:

        if not any(arc.to_place == join_place for arc in source.output_arcs):

            spn.add_output_arc(source, join_place, color=color)

    # ------------------------------------------------
    # Join place -> target
    # ------------------------------------------------

    if target is not None:

        if not any(arc.from_place == join_place for arc in target.input_arcs):

            spn.add_input_arc(join_place, target, color=color)

        return join_place

    # ------------------------------------------------
    # For AND -> AND / AND -> OR chains:
    # create an intermediate gateway transition
    # ------------------------------------------------

    gateway_label = f"AND_GATEWAY_{source_labels}"

    gateway = get_or_create_transition(spn, gateway_label, id, color=color)

    if not any(arc.from_place == join_place for arc in gateway.input_arcs):

        spn.add_input_arc(join_place, gateway, color=color)

    return gateway


def connect_xor_split(spn, source, targets, id, color="forestgreen"):
    """
    Creates an XOR split (exclusive choice).
    """

    place_label = (
        f"XOR_SPLIT_{source.label}_TO_" f"{'_'.join(t.label for t in targets)}"
    )

    # ------------------------------------------------
    # Create / reuse XOR place
    # ------------------------------------------------

    xor_place = get_or_create_place(spn, place_label)

    xor_place.color = color

    xor_place.source = id

    # ------------------------------------------------
    # source -> XOR place
    # ------------------------------------------------

    if not any(arc.to_place == xor_place for arc in source.output_arcs):

        spn.add_output_arc(source, xor_place, color=color)

    # ------------------------------------------------
    # XOR place -> alternatives
    # ------------------------------------------------

    for target in targets:

        if not any(arc.from_place == xor_place for arc in target.input_arcs):

            spn.add_input_arc(xor_place, target, color=color)

    return xor_place


def connect_xor_join(
    spn, sources, target, id, return_transition=False, color="forestgreen"
):
    """
    Creates an XOR join (exclusive merge).
    """

    source_labels = "_".join(t.label for t in sources)

    target_label = target.label if target is not None else "GATEWAY"

    place_label = f"XOR_JOIN_{source_labels}_TO_{target_label}"

    # ------------------------------------------------
    # Create / reuse XOR join place
    # ------------------------------------------------

    join_place = get_or_create_place(spn, place_label)

    join_place.color = color

    join_place.source = id

    # ------------------------------------------------
    # Sources -> XOR join place
    # ------------------------------------------------

    for source in sources:

        if not any(arc.to_place == join_place for arc in source.output_arcs):

            spn.add_output_arc(source, join_place, color=color)

    # ------------------------------------------------
    # XOR join place -> target
    # ------------------------------------------------

    if target is not None:

        if not any(arc.from_place == join_place for arc in target.input_arcs):

            spn.add_input_arc(join_place, target, color=color)

        return join_place

    # ------------------------------------------------
    # For OR -> AND / OR -> OR chaining:
    # create gateway transition
    # ------------------------------------------------
    gateway_label_prefix = source_labels.split("_")[0]
    gateway_label = f"{gateway_label_prefix}_GATEWAY"  # "

    gateway = get_or_create_transition(spn, gateway_label, id, color=color)

    if not any(arc.from_place == join_place for arc in gateway.input_arcs):

        spn.add_input_arc(join_place, gateway, color=color)

    return gateway


def parse_if_then_complex(sentence):
    """
    Parses structural rules of the form IF A THEN B
    """

    if sentence is None:
        return None, None

    sentence = sentence.strip()
    sentence = sentence.replace("\u2010", "_")


    match = re.match(r"^IF\s+(.+?)\s+THEN\s+(.+?)$", sentence, flags=re.IGNORECASE)

    if match is None:
        return None, None

    condition = match.group(1).strip()
    successor = match.group(2).strip()

    return condition, successor

def parse_expression(expression):
    """
    Parses an expression into its logical structure.
    """

    if expression is None:
        return None, []

    expression = expression.strip()

    # AND has priority if both operators appear
    # because parallel synchronization must be explicit
    if re.search(r"\sAND\s", expression, flags=re.IGNORECASE):

        activities = [
            x.strip() for x in re.split(r"\s+AND\s+", expression, flags=re.IGNORECASE)
        ]

        return "AND", activities

    if re.search(r"\sOR\s", expression, flags=re.IGNORECASE):

        activities = [
            x.strip() for x in re.split(r"\s+OR\s+", expression, flags=re.IGNORECASE)
        ]

        return "OR", activities

    return "SINGLE", [expression]

def connect_transition_to_transition(spn, source, target, id, color="forestgreen"):
    """
    Connects transitions.

    Normal connection:
        source -> place -> target

    Self-loop:
        source -> output place -> immediate transition
               -> existing input place -> source
    """

    # --------------------------------------------
    # Check whether this is a self-loop
    # --------------------------------------------

    if source == target:

        input_place = None

        # Find an existing input place of this transition
        for arc in source.input_arcs:

            input_place = arc.from_place
            break

        if input_place is None:
            return None

        # Check whether this loop already exists
        for output_arc in source.output_arcs:

            loop_place = output_arc.to_place

            for input_arc in loop_place.input_arcs:

                immediate = input_arc.to_transition

                if immediate.t_type != "I":
                    continue

                if any(
                    arc.from_place == input_place
                    for arc in immediate.input_arcs
                ):
                    return loop_place

        # ----------------------------------------
        # Create loop output place
        # ----------------------------------------

        place = get_or_create_place(
            spn,
            f"{source.label}_LOOP_OUT"
        )

        place.color = color
        place.source = id

        if not any(
            arc.to_place == place
            for arc in source.output_arcs
        ):
            spn.add_output_arc(source, place, color=color)

        # ----------------------------------------
        # Create immediate loop transition
        # ----------------------------------------

        immediate = get_or_create_transition(
            spn,
            f"loop_{source.label}",
            id,
            t_type="I",
            color=color
        )

        if not any(
            arc.from_place == place
            for arc in immediate.input_arcs
        ):
            spn.add_input_arc(place, immediate, color=color)

        # ----------------------------------------
        # Return to EXISTING input place
        # ----------------------------------------

        if not any(
            arc.to_place == input_place
            for arc in immediate.output_arcs
        ):
            spn.add_output_arc(
                immediate,
                input_place,
                color=color
            )

        return place

    # --------------------------------------------
    # Normal connection (unchanged)
    # --------------------------------------------

    for output_arc in source.output_arcs:

        place = output_arc.to_place

        for input_arc in place.input_arcs:

            if input_arc.to_transition == target:

                place.color = color
                place.source = id

                return place

    place = get_or_create_place(
        spn,
        f"{source.label}_TO_{target.label}"
    )

    place.color = color
    place.source = id

    if not any(
        arc.to_place == place
        for arc in source.output_arcs
    ):
        spn.add_output_arc(source, place, color=color)

    if not any(
        arc.from_place == place
        for arc in target.input_arcs
    ):
        spn.add_input_arc(place, target, color=color)

    return place