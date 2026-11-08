from __future__ import annotations
import re

class SPN(object):

    def __init__(self):
        self.places = []
        self.transitions = []
        
    def add_place(self, place: Place):            
        self.places.append(place)

    def add_transition(self, transition: Transition):
        self.transitions.append(transition)

    def add_input_arc(self, place: Place, transition: Transition, multiplicity = 1, color = "black"):
        arc = InputArc()
        arc.from_place = place
        arc.to_transition = transition
        arc.multiplicity = multiplicity
        transition.input_arcs.append(arc)
        place.input_arcs.append(arc)
        arc.color = color

    def add_inhibitor_arc(self, transition: Transition, place: Place, multiplicity = 1, color = "black"):
        arc = InhibitorArc()
        arc.to_transition = transition
        arc.from_place = place
        arc.multiplicity = multiplicity
        arc.color = color
        transition.inhibitor_arcs.append(arc)
        place.inhibitor_arcs.append(arc)
        

    def add_output_arc(self, transition: Transition, place: Place, multiplicity = 1, color = "black"):
        arc = OutputArc()
        arc.from_transition = transition
        arc.to_place = place
        arc.multiplicity = multiplicity
        transition.output_arcs.append(arc)
        place.output_arcs.append(arc)
        arc.color = color

    '''
    def get_current_marking(self):
        marking = {}
        for place in self.places:
            place:Place
            marking[place]=place.n_tokens
            return marking
    '''
    def get_place_by_label(self, label: str):
        target = normalize_identifier(label)
        for place in self.places:
            if normalize_identifier(place.label) == target:
                return place
        return None

    def get_transition_by_label(self, label: str):
        target = normalize_identifier(label)
        for transition in self.transitions:
            if normalize_identifier(transition.label) == target:
                return transition
        return None

    def get_arrival_transitions(self):
        try:
            transition: Transition
            arrival_transitions = []
            for transition in self.transitions:
                if transition.input_arcs == []:
                    arrival_transitions.append(transition)
            return arrival_transitions
        except: print("Failed to find arrival transitions.")

def normalize_identifier(text):
    """
    Robust identifier normalization.

    Handles:
    - case differences
    - separators
    - repeated component prefixes

    Examples:
        OV_2_BURN
        ov_2_ov_2_burn
        OV-2-OV-2-BURN

    -> ov2burn
    """

    if text is None:
        return ""

    tokens = re.findall(
        r"[a-z0-9]+",
        str(text).lower()
    )

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
            second = tokens[size:2*size]

            if first == second:

                tokens = tokens[size:]
                changed = True
                break


    return "".join(tokens)        

class Place():

    def __init__(self, label: str, n_tokens: int):
        self.label = label
        self.n_tokens = n_tokens
        self.max_tokens = 0
        self.time_changed = 0
        self.total_tokens = 0
        self.time_non_empty = 0
        self.color = "black"
        self.source = ""

        #self.weight_factor = "w = 1.0" ## (single place)
        #self.threshold_factor = "λ = ..."

        self.input_arcs = []
        self.output_arcs = []
        self.inhibitor_arcs = []

    def set_tokens(self, n_tokens: int):
        self.n_tokens = n_tokens

class Transition(object):

    def __init__(self, label: str, t_type: str):
        self.label = label
        self.condition_label = ""
        #self.certainty_factor = "μ = 0.9 (IoT data)"
        self.t_type = t_type
        self.color = "black"
        self.source = ""

        if self.t_type == "T":
            self.distribution = None
            self.time_unit = None
        elif self.t_type == "I":
            self.weight = 1
        else: raise Exception("Not a valid transition type.")

        self.handicap = 1 #Handicap for experiments with new configurations; Handicap will influence firing times of transition; <1 -> transition fill fire faster; >1 -> transition will fire slower
        self.handicap_type = None
        self.allow_reset = False
        self.reset_threshold = 0 #Threshold; can be used e.g., for testing preventive maintenance with equipment failure transitions
        self.reset_time = 0

        self.guard_function = None
        self.memory_policy = "ENABLE"
        self.clock_active = False

        self.enabled = False
        self.enabled_at = 0
        self.disabled_at = 0
        self.disabled_time = 0
        self.firing_delay = 0
        self.firing_time = 0

        self.time_enabled = 0
        self.n_times_fired = 0

        self.input_arcs = []
        self.output_arcs = []
        self.inhibitor_arcs = []

    def set_distribution(self, distribution, a=0.0, b=0.0, c=0.0, d=0.0, time_unit:str = None):
        if self.t_type == "T":
            self.distribution = {distribution:{"a":a,"b":b,"c":c,"d":d}}
            self.time_unit = time_unit
        else: raise Exception("Can not set distribution for immediate transition.")
    
    def set_weight(self, weight: float):
        if self.t_type == "I":
            self.weight = weight
        else: raise Exception("Can not set weight for timed transition.")

    def set_guard_function(self, guard_function):
        self.guard_function = guard_function

    def set_memory_policy(self, type):
        self.memory_policy = type

class InputArc(object):
    def __init__(self):
        self.to_transition = None
        self.from_place = None
        self.multiplicity = 0
        self.color = "black"

class InhibitorArc(object):
    def __init__(self):
        self.to_transition = None
        self.from_place = None
        self.multiplicity = 0
        self.color = "black"

class OutputArc(object):
    def __init__(self):
        self.to_place = None
        self.from_transition = None
        self.multiplicity = 0
        self.color = "black"