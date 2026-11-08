from __future__ import annotations

from dataclasses import dataclass

from typing import Dict

import numpy as np

from scipy import stats

from pyspn.components.spn import SPN

# ---------------------------------------------------------------------
# Distribution result
# ---------------------------------------------------------------------


@dataclass
class DistributionFit:

    name: str

    parameters: tuple

    ks_statistic: float

    ks_pvalue: float


# ---------------------------------------------------------------------
# Candidate distributions
# ---------------------------------------------------------------------


def fit_normal(data):

    params = stats.norm.fit(data)

    statistic, pvalue = stats.kstest(data, "norm", args=params)

    return DistributionFit(
        name="normal", parameters=params, ks_statistic=statistic, ks_pvalue=pvalue
    )


def fit_lognormal(data):

    positive = [x for x in data if x > 0]

    if len(positive) < 2:

        return None

    params = stats.lognorm.fit(positive)

    statistic, pvalue = stats.kstest(positive, "lognorm", args=params)

    return DistributionFit(
        name="lognormal", parameters=params, ks_statistic=statistic, ks_pvalue=pvalue
    )


def fit_exponential(data):

    positive = [x for x in data if x >= 0]

    if len(positive) < 2:

        return None

    params = stats.expon.fit(positive)

    statistic, pvalue = stats.kstest(positive, "expon", args=params)

    return DistributionFit(
        name="exponential", parameters=params, ks_statistic=statistic, ks_pvalue=pvalue
    )


# ---------------------------------------------------------------------
# Fit candidates
# ---------------------------------------------------------------------


def fit_candidate_distributions(durations):

    results = []

    data = np.asarray(durations, dtype=float)

    if len(data) < 2:

        return results

    candidates = [fit_normal(data), fit_lognormal(data), fit_exponential(data)]

    for candidate in candidates:

        if candidate is not None:

            results.append(candidate)

    return results


# ---------------------------------------------------------------------
# Select best distribution
# ---------------------------------------------------------------------


def select_best_distribution(durations):

    candidates = fit_candidate_distributions(durations)

    if not candidates:

        return None

    return max(candidates, key=lambda x: x.ks_pvalue)


# ---------------------------------------------------------------------
# Fit transition distributions
# ---------------------------------------------------------------------


def fit_transition_distributions(spn: SPN):

    print("Fitting transition distributions...")

    fitted = {}

    durations = getattr(spn, "transition_durations", {})

    timed = getattr(spn, "timed_transitions", set())

    for transition_label in timed:

        if transition_label not in durations:

            continue

        values = durations[transition_label]

        best = select_best_distribution(values)

        if best is None:

            continue

        fitted[transition_label] = best

        #
        # Update PySPN transition object
        #

        transition = spn.get_transition_by_label(transition_label)

        if transition is not None:

            transition.distribution = {best.name: best.parameters}

    spn.distributions = fitted

    print(f"Distributions fitted: {len(fitted)}")

    return spn
