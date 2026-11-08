# --------------------------------------------------------------------------
# Imports
# --------------------------------------------------------------------------

from __future__ import annotations

import pandas as pd

import pm4py

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

CASE_COL = "case"

ACTIVITY_COL = "concept:name"

RESOURCE_COL = "org:resource"

TIMESTAMP_COL = "time:timestamp"

PROCESS_MODEL_COL = "process_model_id"

TARGET_PROCESS_MODEL = "WF_102"

# ---------------------------------------------------------------------
# Timestamp normalization
# ---------------------------------------------------------------------


def normalize_timestamp_column(df: pd.DataFrame):
    """
    Normalize timestamps YYYY-MM-DD HH:MM:SS.microseconds+timezone
    Removes timezone information afterwards.

    """

    df[TIMESTAMP_COL] = pd.to_datetime(
        df[TIMESTAMP_COL], errors="coerce", format="%Y-%m-%d %H:%M:%S.%f%z"
    )

    df = df.dropna(subset=[TIMESTAMP_COL])

    #
    # Remove timezone
    #

    df[TIMESTAMP_COL] = df[TIMESTAMP_COL].dt.tz_localize(None)

    return df


# ---------------------------------------------------------------------
# Activity normalization
# ---------------------------------------------------------------------


def merge_resource_activity(df):
    """
    Merge resource and activity names while avoiding duplicated
    resource prefixes.
    """

    if RESOURCE_COL in df.columns and ACTIVITY_COL in df.columns:

        def normalize_activity(resource, activity):

            resource = str(resource)
            activity = str(activity).strip("/")

            parts = activity.split("/")

            # resource prefix (e.g. "sm" from "sm_2")
            resource_prefix = resource.split("_")[0].lower()

            # remove duplicated first path element
            if len(parts) > 1 and parts[0].lower() == resource_prefix:
                parts = parts[1:]

            return resource + "_" + "_".join(parts)

        df[ACTIVITY_COL] = [
            normalize_activity(resource, activity)
            for resource, activity in zip(df[RESOURCE_COL], df[ACTIVITY_COL])
        ]

    return df


# ---------------------------------------------------------------------
# Load event log
# ---------------------------------------------------------------------


def load_event_log(filename: str):
    """
    Load CSV or XES.
    Returns dataframe.
    """
    filename = filename.lower()

    if filename.endswith(".csv"):

        df = pd.read_csv(filename, sep=";")

        #
        # Filter process model
        #

        if PROCESS_MODEL_COL in df.columns:

            df = df[df[PROCESS_MODEL_COL] == TARGET_PROCESS_MODEL].copy()

        df[CASE_COL] = df[CASE_COL].astype(str)

        df = normalize_timestamp_column(df)

        df = merge_resource_activity(df)

        df = df.sort_values(by=TIMESTAMP_COL)

        return df

    elif filename.endswith(".xes"):

        if pm4py is None:
            raise ImportError("PM4Py required for XES files.")

        log = pm4py.read_xes(filename)

        df = pm4py.convert_to_dataframe(log)

        df[CASE_COL] = df[CASE_COL].astype(str)

        df = normalize_timestamp_column(df)

        df = merge_resource_activity(df)

        return df.sort_values(by=TIMESTAMP_COL)

    else:
        raise ValueError("Supported formats: CSV, XES")


# ---------------------------------------------------------------------
# Load state log
# ---------------------------------------------------------------------


def load_state_log(filename: str):
    """
    Load CSV or XES.
    Returns dataframe.
    """

    filename = filename.lower()

    if filename.endswith(".csv"):

        df = pd.read_csv(filename, sep=";")

        #
        # Filter process model
        #

        if PROCESS_MODEL_COL in df.columns:

            df = df[df[PROCESS_MODEL_COL] == TARGET_PROCESS_MODEL].copy()

        df[CASE_COL] = df[CASE_COL].astype(str)

        df = normalize_timestamp_column(df)

        df = merge_resource_activity(df)

        df = df.sort_values(by=TIMESTAMP_COL)

        return df

    elif filename.endswith(".xes"):

        if pm4py is None:
            raise ImportError("PM4Py required for XES files.")

        log = pm4py.read_xes(filename)

        df = pm4py.convert_to_dataframe(log)

        df[CASE_COL] = df[CASE_COL].astype(str)

        df = normalize_timestamp_column(df)

        df = merge_resource_activity(df)

        return df.sort_values(by=TIMESTAMP_COL)

    else:
        raise ValueError("Supported formats: CSV, XES")


# ---------------------------------------------------------------------
# Sort event log
# ---------------------------------------------------------------------


def sort_log(df):
    """
    Sort by case and timestamp.
    """

    return df.sort_values(by=[CASE_COL, TIMESTAMP_COL]).reset_index(drop=True)


# ---------------------------------------------------------------------
# Extract traces
# ---------------------------------------------------------------------


def extract_traces(df):
    """
    Extract traces
    """

    traces = {}

    grouped = df.groupby(CASE_COL)

    for case_id, trace in grouped:

        trace = trace.sort_values(TIMESTAMP_COL)

        events = []

        for _, row in trace.iterrows():

            events.append(
                {
                    "activity": row[ACTIVITY_COL],
                    "timestamp": row[TIMESTAMP_COL],
                    "lifecycle_state": row.get("lifecycle:state", None),
                    "lifecycle_transition": row.get("lifecycle:transition", None),
                    "resource": row.get(RESOURCE_COL, None),
                    "row": row,
                }
            )

        traces[str(case_id)] = events

    return traces


# ---------------------------------------------------------------------
# Complete preprocessing
# ---------------------------------------------------------------------


def preprocess_log(
    log: pd.DataFrame,
):
    """
    Complete preprocessing pipeline.
    """

    log = log.copy()

    #
    # Event log normalization
    #

    log[CASE_COL] = log[CASE_COL].astype(str)

    log = normalize_timestamp_column(log)

    log = merge_resource_activity(log)

    log = sort_log(log)

    #
    # State log normalization
    #

    if "lifecycle:state" in log.columns:

        log["lifecycle:state"] = log["lifecycle:state"].astype(str).str.lower()

    if "lifecycle:transition" in log.columns:

        log["lifecycle:transition"] = (
            log["lifecycle:transition"].astype(str).str.lower()
        )

    traces = extract_traces(log)

    return log, traces
