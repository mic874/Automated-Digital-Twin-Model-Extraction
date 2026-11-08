from collections import defaultdict

from distributions import select_best_distribution

# ---------------------------------------------------------------
# Lifecycle configuration
# ---------------------------------------------------------------

FAILURE_STATE = "failure"

REPAIR_PRIORITY = ["assigned", "start", "complete"]


OPERATIONAL_STATES = ["assigned", "start", "complete"]


# ---------------------------------------------------------------
# Extract reliability durations
# ---------------------------------------------------------------


def extract_reliability_durations(state_log):
    """
    Extracts reliability durations
    """

    durations = defaultdict(lambda: {"failure": [], "repair": []})

    active = {}

    failed = {}

    for _, row in state_log.iterrows():

        component = None

        #
        # component identifier
        #

        for col in ["component", "concept:name", "org:resource"]:

            if col in row:

                component = str(row[col])

                break

        if component is None:
            continue

        state = str(row["lifecycle:state"]).lower()

        timestamp = row["time:timestamp"]

        #
        # Remember last operational timestamp
        #

        if state in OPERATIONAL_STATES:

            active[component] = timestamp

            #
            # Failure -> repair
            #

            if component in failed:

                repair_time = (timestamp - failed[component]).total_seconds()

                if repair_time >= 0:

                    durations[component]["repair"].append(repair_time)

                del failed[component]

        #
        # Failure detected
        #

        elif state == FAILURE_STATE:

            #
            # operational -> failure
            #

            if component in active:

                failure_time = (timestamp - active[component]).total_seconds()

                if failure_time >= 0:

                    durations[component]["failure"].append(failure_time)

            failed[component] = timestamp

    return durations


# ---------------------------------------------------------------
# Fit distributions
# ---------------------------------------------------------------


def fit_reliability_distributions(state_log):
    """
    Returns:
        failure_distribution
        repair_distribution
    """

    durations = extract_reliability_durations(state_log)

    fitted = {}

    for component, values in durations.items():

        fitted[component] = {}

        #
        # Failure distribution
        #

        if len(values["failure"]) >= 2:

            fitted[component]["failure_distribution"] = select_best_distribution(
                values["failure"]
            )

        #
        # Repair distribution
        #

        if len(values["repair"]) >= 2:

            fitted[component]["repair_distribution"] = select_best_distribution(
                values["repair"]
            )

    return fitted


# ---------------------------------------------------------------
# Assign distributions to SPN transitions
# ---------------------------------------------------------------


def assign_reliability_distributions(spn, state_log):

    fitted = fit_reliability_distributions(state_log)

    for component, distributions in fitted.items():

        fail_transition = f"FAIL_{component}"

        repair_transition = f"RESTORE_{component}"

        for transition in spn.transitions:

            if transition.label == fail_transition:

                transition.t_type = "T"

                transition.distribution = distributions.get("failure_distribution")

            elif transition.label == repair_transition:

                transition.t_type = "T"

                transition.distribution = distributions.get("repair_distribution")

    spn.reliability_distributions = fitted

    return spn
