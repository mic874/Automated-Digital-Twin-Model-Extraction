from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict

from typing import Dict
from typing import List
from typing import Tuple

import numpy as np

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pyspn.components.spn import SPN, Place, Transition

# --------------------------------------------------------------------
# Helper class
# --------------------------------------------------------------------


@dataclass
class TransitionTiming:
    """
    Stores timing information for one transition.
    """

    name: str

    durations: List[float] = field(default_factory=list)

    corrected_durations: List[float] = field(default_factory=list)

    enabled_times: List = field(default_factory=list)

    firing_times: List = field(default_factory=list)

    expected_times: List = field(default_factory=list)

    median_delay: float = 0.0


# --------------------------------------------------------------------
# Estimate enabling times
# --------------------------------------------------------------------


def compute_enabled_times(traces: Dict):
    """
    Estimate the enabling timestamp of every event.
    """

    enabled = defaultdict(list)

    for trace in traces.values():

        previous_time = None

        for event in trace:

            timestamp = event["timestamp"]
            activity = event["activity"]

            if previous_time is None:
                enable_time = timestamp
            else:
                enable_time = previous_time

            enabled[activity].append(enable_time)

            previous_time = timestamp

    return enabled


# --------------------------------------------------------------------
# Compute durations Δ
# --------------------------------------------------------------------


def compute_transition_durations(traces: Dict):
    """
    Returns transition -> durations
    """

    durations = defaultdict(list)

    firing_times = defaultdict(list)

    for trace in traces.values():

        previous_time = None

        for event in trace:

            timestamp = event["timestamp"]
            activity = event["activity"]

            firing_times[activity].append(timestamp)

            if previous_time is None:

                delta = 0.0

            else:

                delta = (timestamp - previous_time).total_seconds()

            durations[activity].append(delta)

            previous_time = timestamp

    return durations, firing_times


# --------------------------------------------------------------------
# Remove outliers
# --------------------------------------------------------------------


def trim_outliers(values: List[float]):
    """
    Remove outliers 
    """

    if len(values) < 5:
        return values.copy()

    values = np.asarray(values)

    lower = np.percentile(values, 15)

    upper = np.percentile(values, 85)

    mask = np.logical_and(values >= lower, values <= upper)

    return values[mask].tolist()


# --------------------------------------------------------------------
# Compute median delay
# --------------------------------------------------------------------


def compute_median_delay(durations: List[float]):

    trimmed = trim_outliers(durations)

    if len(trimmed) == 0:
        return 0.0

    return float(np.median(trimmed))


# --------------------------------------------------------------------
# Expected firing timestamps
# --------------------------------------------------------------------


def compute_expected_times(enabled_times, median_delay):

    expected = []

    for t in enabled_times:

        expected.append(t + np.timedelta64(int(median_delay * 1000), "ms"))

    return expected


# --------------------------------------------------------------------
# Build timing objects
# --------------------------------------------------------------------


def build_transition_timings(traces):
    """
    Creates a timing object for every transition.
    """

    enabled = compute_enabled_times(traces)

    durations, firing = compute_transition_durations(traces)

    timing = {}

    transitions = sorted(durations.keys())

    for transition in transitions:

        info = TransitionTiming(transition)

        info.enabled_times = enabled[transition]

        info.firing_times = firing[transition]

        info.durations = durations[transition]

        info.median_delay = compute_median_delay(durations[transition])

        info.expected_times = compute_expected_times(
            info.enabled_times, info.median_delay
        )

        timing[transition] = info

    return timing


# --------------------------------------------------------------------
# Helper
# --------------------------------------------------------------------


def transition_has_zero_duration(timing: TransitionTiming):
    """
    Determines whether a transition
    should initially be considered
    an immediate transition.
    """

    if len(timing.durations) == 0:
        return True

    return np.allclose(timing.durations, 0.0)


# --------------------------------------------------------------------
# Utility
# --------------------------------------------------------------------


def get_outgoing_place(spn: SPN, transition_label: str):
    """
    Returns the first outgoing place
    of a transition using PySPN objects.
    """

    transition = spn.get_transition_by_label(transition_label)

    if transition is None:
        return None

    if len(transition.output_arcs) == 0:
        return None

    return transition.output_arcs[0].to_place



# --------------------------------------------------------------------
# Detect whether successor transition is enabled
# --------------------------------------------------------------------


def successor_enabled(trace, index):

    return index + 1 < len(trace)


# --------------------------------------------------------------------
# Find next transition
# --------------------------------------------------------------------


def next_transition(trace, index):
    """
    Returns Ei+1.
    """

    if index + 1 >= len(trace):
        return None

    return trace[index + 1]["activity"]


# --------------------------------------------------------------------
# Detect inhibitor conditions
# --------------------------------------------------------------------


def detect_inhibitor_conditions(traces, timing):
    """
    Returns list of detected inhibitor relations
    """

    inhibitors = []

    for case_id, trace in traces.items():

        for i, event in enumerate(trace):

            activity = event["activity"]

            if activity not in timing:
                continue

            info = timing[activity]

            observed_time = event["timestamp"]

            #
            # find corresponding observation
            #

            for k, expected in enumerate(info.expected_times):

                if k < len(info.firing_times) and info.firing_times[k] == observed_time:

                    if observed_time > expected and successor_enabled(trace, i):

                        successor = next_transition(trace, i)

                        inhibitors.append(
                            {
                                "case": case_id,
                                "transition": activity,
                                "successor": successor,
                                "delay": (observed_time - expected).total_seconds(),
                            }
                        )

    return inhibitors


# --------------------------------------------------------------------
# Correct duration values
# --------------------------------------------------------------------


def correct_duration(duration, inhibitor_delay):
    """
    Removes the inhibitor waiting time.
    """

    corrected = duration - inhibitor_delay

    return max(corrected, 0.0)


# --------------------------------------------------------------------
# Compute corrected transition durations
# --------------------------------------------------------------------


def compute_corrected_durations(traces, timing, inhibitors):

    inhibitor_lookup = defaultdict(list)

    for item in inhibitors:

        key = (item["case"], item["transition"])

        inhibitor_lookup[key].append(item["delay"])

    corrected = defaultdict(list)

    for case_id, trace in traces.items():

        previous_time = None

        for event in trace:

            activity = event["activity"]

            timestamp = event["timestamp"]

            if previous_time is None:

                delta = 0.0

            else:

                delta = (timestamp - previous_time).total_seconds()

            delays = inhibitor_lookup.get((case_id, activity), [])

            if delays:

                delta = correct_duration(delta, max(delays))

            corrected[activity].append(delta)

            previous_time = timestamp

    return corrected


# --------------------------------------------------------------------
# Classify transitions
# --------------------------------------------------------------------


def classify_transitions(spn, corrected_durations):
    """
    Updates PySPN Transition objects.
    """

    immediate = set()

    timed = set()

    for name, values in corrected_durations.items():

        if len(values) == 0:
            continue

        if np.allclose(values, 0.0):

            immediate.add(name)

        else:

            timed.add(name)

    #
    # Update PySPN transition objects
    #

    for transition in spn.transitions:

        if transition.label in immediate:

            transition.t_type = "I"

        elif transition.label in timed:

            transition.t_type = "T"

    #
    # Store information for later modules
    #

    spn.immediate_transitions = immediate

    spn.timed_transitions = timed

    return spn


# --------------------------------------------------------------------
# Add inhibitor arcs to SPN
# --------------------------------------------------------------------


def add_inhibitor_arcs(spn: SPN, inhibitors):
    """
    Creates inhibitor arcs
    """

    existing = set()

    for item in inhibitors:

        transition_label = item["transition"]

        successor = item["successor"]

        # No successor means no inhibitor relation
        if successor is None:
            continue

        place_label = f"{transition_label}_to_{successor}"

        key = (place_label, transition_label)

        # Avoid duplicate inhibitor arcs
        if key in existing:
            continue

        existing.add(key)

        #
        # Find PySPN objects
        #

        transition = spn.get_transition_by_label(transition_label)

        place = spn.get_place_by_label(place_label)

        #
        # Ignore relations where the required
        # SPN elements do not exist
        #

        if transition is None:
            continue

        if place is None:
            continue

        #
        # Create inhibitor arc using PySPN
        #

        spn.add_inhibitor_arc(transition, place)

    return spn


# --------------------------------------------------------------------
# Complete Step 3 interface
# --------------------------------------------------------------------


def detect_inhibitor_arcs(spn: SPN, traces):
    """
    Complete implementation of Step 3.

    Returns updated SPN.
    """

    print("Computing transition timing information...")

    timing = build_transition_timings(traces)

    print("Searching for inhibitor conditions...")

    inhibitors = detect_inhibitor_conditions(traces, timing)

    print(f"Detected inhibitor relations: {len(inhibitors)}")

    print("Correcting transition durations...")

    corrected = compute_corrected_durations(traces, timing, inhibitors)

    print("Adding inhibitor arcs...")

    spn = add_inhibitor_arcs(spn, inhibitors)

    print("Classifying transitions...")

    spn = classify_transitions(spn, corrected)

    #
    # Store duration information
    # needed later by distributions.py
    #

    spn.transition_durations = corrected

    return spn

# --------------------------------------------------------------------
# Detect whether successor transition is enabled
# --------------------------------------------------------------------


def successor_enabled(trace, index):

    return index + 1 < len(trace)


# --------------------------------------------------------------------
# Find next transition
# --------------------------------------------------------------------


def next_transition(trace, index):

    if index + 1 >= len(trace):
        return None

    return trace[index + 1]["activity"]


# --------------------------------------------------------------------
# Detect inhibitor conditions
# --------------------------------------------------------------------


def detect_inhibitor_conditions(traces, timing):
    """
    Returns list of detected inhibitor relations
    """

    inhibitors = []

    for case_id, trace in traces.items():

        for i, event in enumerate(trace):

            activity = event["activity"]

            if activity not in timing:
                continue

            info = timing[activity]

            observed_time = event["timestamp"]

            #
            # find corresponding observation
            #

            for k, expected in enumerate(info.expected_times):

                if k < len(info.firing_times) and info.firing_times[k] == observed_time:

                    if observed_time > expected and successor_enabled(trace, i):

                        successor = next_transition(trace, i)

                        inhibitors.append(
                            {
                                "case": case_id,
                                "transition": activity,
                                "successor": successor,
                                "delay": (observed_time - expected).total_seconds(),
                            }
                        )

    return inhibitors


# --------------------------------------------------------------------
# Correct duration values
# --------------------------------------------------------------------


def correct_duration(duration, inhibitor_delay):
    """
    Removes the inhibitor waiting time.
    """

    corrected = duration - inhibitor_delay

    return max(corrected, 0.0)


# --------------------------------------------------------------------
# Compute corrected transition durations
# --------------------------------------------------------------------


def compute_corrected_durations(traces, timing, inhibitors):

    inhibitor_lookup = defaultdict(list)

    for item in inhibitors:

        key = (item["case"], item["transition"])

        inhibitor_lookup[key].append(item["delay"])

    corrected = defaultdict(list)

    for case_id, trace in traces.items():

        previous_time = None

        for event in trace:

            activity = event["activity"]

            timestamp = event["timestamp"]

            if previous_time is None:

                delta = 0.0

            else:

                delta = (timestamp - previous_time).total_seconds()

            delays = inhibitor_lookup.get((case_id, activity), [])

            if delays:

                delta = correct_duration(delta, max(delays))

            corrected[activity].append(delta)

            previous_time = timestamp

    return corrected


# --------------------------------------------------------------------
# Classify transitions
# --------------------------------------------------------------------


def classify_transitions(spn, corrected_durations):
    """
    immediate transition and timed transition
    """

    immediate = set()

    timed = set()

    for name, values in corrected_durations.items():

        if len(values) == 0:
            continue

        if np.allclose(values, 0.0):

            immediate.add(name)

        else:

            timed.add(name)

    #
    # Update transitions
    #

    for transition in spn.transitions:

        if transition.label in immediate:

            transition.t_type = "I"

            if not hasattr(transition, "weight"):
                transition.weight = 1

        elif transition.label in timed:

            transition.t_type = "T"

            if not hasattr(transition, "distribution"):
                transition.distribution = None

    #
    # Store sets for later modules
    #

    spn.immediate_transitions = immediate

    spn.timed_transitions = timed

    return spn


# --------------------------------------------------------------------
# Add inhibitor arcs to SPN
# --------------------------------------------------------------------


def add_inhibitor_arcs(spn: SPN, inhibitors):
    """
    Creates inhibitor arcs:
    """

    existing = set()

    for item in inhibitors:

        transition_label = item["transition"]

        successor = item["successor"]

        if successor is None:
            continue

        place_label = f"{transition_label}_to_{successor}"

        key = (place_label, transition_label)

        if key in existing:
            continue

        existing.add(key)

        transition = spn.get_transition_by_label(transition_label)

        place = spn.get_place_by_label(place_label)

        if transition is None:
            continue

        if place is None:
            continue

        #
        # Check whether inhibitor already exists
        #

        already_exists = False

        for arc in transition.inhibitor_arcs:

            if arc.from_place == place:

                already_exists = True

                break

        if already_exists:
            continue

        #
        # Add inhibitor arc
        #

        spn.add_inhibitor_arc(transition, place)

    return spn


# --------------------------------------------------------------------
# Complete Step 3 interface
# --------------------------------------------------------------------


def detect_inhibitor_arcs(spn: SPN, traces):
    """
    Returns updated SPN.
    """

    print("Computing transition timing information...")

    timing = build_transition_timings(traces)

    print("Searching for inhibitor conditions...")

    inhibitors = detect_inhibitor_conditions(traces, timing)

    print(f"Detected inhibitor relations: {len(inhibitors)}")

    print("Correcting transition durations...")

    corrected = compute_corrected_durations(traces, timing, inhibitors)

    print("Adding inhibitor arcs...")

    spn = add_inhibitor_arcs(spn, inhibitors)

    print("Classifying transitions...")

    spn = classify_transitions(spn, corrected)

    spn.transition_durations = corrected

    return spn
