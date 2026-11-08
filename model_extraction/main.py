"""
main.py

Main entry point for the Data-Knolwedge-Fused Digital Twin Stochastic Petri Net model extraction algorithm.

"""

# --------------------------------------------------------------------------
# Imports
# --------------------------------------------------------------------------

from pathlib import Path
import pandas as pd

from pathlib import Path

from preprocess import (
    load_event_log,
    load_state_log,
    preprocess_log,
)

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pyspn.components.spn import (
    SPN,
    Place,
    Transition
)

from process_discovery import (
    discover_process_model,
)

from structure import (
    build_spn_structure,
)

from inhibitor_detection import (
    detect_inhibitor_arcs,
)

from multiplicity import (
    detect_arc_multiplicities,
)

from controlflow import (
    implement_control_flow_patterns,
)

from distributions import (
    fit_transition_distributions,
)

from weights import (
    compute_immediate_transition_weights,
)

from reliability_ddra import (
    extract_reliability_components,
)

from reliability_distributions import (
    assign_reliability_distributions,
)

from expert_knowledge_load import (
    load_raw_expert_knowledge, 
    load_formalized_knowledge,
)

from expert_knowledge_classification import (
    classify_statement
)

from expert_knowledge_formalization import (
    formalize_statement
)

from integrate_state_deviation_knowledge import (
    integrate_state_deviation
)

from integrate_process_flow_knowledge import (
    integrate_process_flow
)

from integrate_maintenance_knowledge import (
    integrate_maintenance
)

from integrate_operational_knowledge import (
    integrate_operational
)

from integrate_structural_knowledge import (
    integrate_structural
)

from integrate_temporal_and_probabilistic_knowledge import (
    integrate_temporal_and_probabilistic
)

from pyspn_visualization import (
    visualize_pyspn_model
)

from pyspn.components.spn_visualization import (
    draw_spn
)

# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------


def extract_spn(
    DATA_INPUT_FILE: str,
    EXPERT_KNOWLEDGE_INPUT_FILE: str,
    miner: str = "alpha",
):

    print("=" * 70)
    print(" DKDT Stochastic Petri Net Model Extraction")
    print("=" * 70)

    # ----------------------------------------------------------
    # IoT Data Processing
    # ----------------------------------------------------------

    print("\nLoading and preprocessing of the event and state log...")

    event_log = load_event_log(DATA_INPUT_FILE)

    state_log = load_state_log(DATA_INPUT_FILE)

    cleaned_event_log, traces = preprocess_log(event_log)

    print(f"Cases: {len(traces)}")

    # ----------------------------------------------------------
    # Step 2: Automated Expert Knowledge Procesing
    # ----------------------------------------------------------

    print("\n[1] Automated expert knowledge processing... ")

    print("\nLoad expert knowledge ... ")

    id, expert_knowledge = load_raw_expert_knowledge(
        EXPERT_KNOWLEDGE_INPUT_FILE,
    )

    knowledge_df = pd.DataFrame(
        columns=["knowledge_type", "formalized_knowledge", "original", "id"]
    )

    print("\n[1.1] Classify expert knowledge statements... ")

    for index, knowledge_item in enumerate(expert_knowledge):

        knowledge_types = classify_statement(
            knowledge_item,
        )

        print(
            "\n[1.2 and 1.3] Orchestrate and formalize expert knowledge statements... "
        )

        for knowledge_type in knowledge_types:

            formalized_knowledge = formalize_statement(knowledge_type, knowledge_item)
            
            print("\n[1.4] Save processed knowledge... ")

            knowledge_df.loc[len(knowledge_df)] = {
                "knowledge_type": knowledge_type,
                "formalized_knowledge": formalized_knowledge,
                "original": knowledge_item,
                "id": id[index],
            }

    spn = SPN()

    
    # ----------------------------------------------------------
    # Step 2: Data-driven Stochastic Petri Net Model Extraction
    # ----------------------------------------------------------

    print("\n[2] Data-driven model extraction...")

    print("\n[2.1] Discovering process model...")

    discovered_net = discover_process_model(cleaned_event_log, algorithm=miner)

    print("\n[2.2] Building the stochastic Petri net structure...")

    spn = build_spn_structure(
        traces=traces,
        process_model=discovered_net,
    )

    print("\n[2.3] Detecting inhibitor arcs...")

    spn = detect_inhibitor_arcs(
        spn=spn,
        traces=traces,
    )

    print("\n[2.4] Detecting multiplicities...")

    spn = detect_arc_multiplicities(
        spn=spn,
        traces=traces,
    )

    print("\n[2.5] Detecting control-flow patterns...")

    spn = implement_control_flow_patterns(
        spn=spn,
        traces=traces,
    )

    print("\n[2.6] Fitting duration distributions...")

    spn = fit_transition_distributions(spn)

    print("\n[2.7] Computing immediate transition weights...")

    spn = compute_immediate_transition_weights(
        spn=spn,
        traces=traces,
    )

    # ----------------------------------------------------------
    # Extraction of reliability related components
    # ----------------------------------------------------------

    print("\n[2.8] Extracting reliability components...")

    spn = extract_reliability_components(
        spn=spn,
        state_log=state_log,
    )

    print(state_log.columns.tolist())

    print("\n[2.9] Extracting reliability distributions...")

    spn = assign_reliability_distributions(spn=spn, state_log=state_log)

    # ----------------------------------------------------------
    # Helper for visualized comparison
    # ----------------------------------------------------------

    visualize_pyspn_model(spn, "data-driven-model")

    

    # ----------------------------------------------------------
    # Step 3: Expert Knowledge Integration into the Data-Driven Digital Twin Model to extract a Data-Knowledge-Fused Digital Twin Model
    # ----------------------------------------------------------
    
    print("\n[3] Integrate expert knowledge into the data-driven model ... ")

    for _, row in knowledge_df.iterrows():

        knowledge_type = str(row["knowledge_type"]).strip()
        knowledge = str(row["formalized_knowledge"])
        id = str(row["id"]).strip()

        for part_knowledge in knowledge.split(";"):

            if knowledge_type == "state_deviation":
                print("\n[3.1] Integrate state deviation knowledge ... ")
                integrate_state_deviation(spn, part_knowledge, id)

            elif knowledge_type == "process_flow":
                print("\n[3.2] Integrate process flow knowledge ... ")
                integrate_process_flow(spn, part_knowledge, id)

            elif knowledge_type == "maintenance":
                print("\n[3.3] Integrate maintenance knowledge ... ")
                integrate_maintenance(spn, part_knowledge, id)

            elif knowledge_type == "operational":
                print("\n[3.4] Integrate operational knowledge ... ")
                integrate_operational(spn, part_knowledge, id)

            elif knowledge_type == "structural":
                print("\n[3.5] Integrate structural knowledge ... ")
                integrate_structural(spn, part_knowledge, id)

            elif knowledge_type == "temporal_and_probabilistic":
                print("\n[3.6] Integrate temporal_and_probabilistic knowledge ... ")
                integrate_temporal_and_probabilistic(spn, part_knowledge, id)

  
    # ----------------------------------------------------------
    # Step 4: Visualization of the extracted Data-Knowledge-Fused Stochastic Petri Net model
    # ----------------------------------------------------------
    
    print("\n[4] Visualize model...")

    visualize_pyspn_model(spn, "data-knowledge-fused-model")

    return spn


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

# Input files
DATA_INPUT = "../input_data/event_and_state_log.csv"
EXPERT_KNOWLEDGE_INPUT = "../input_data/expert_knowledge.csv"

# Process discovery algorithm
MINER = "alpha"

# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def main():

    DATA_INPUT_FILE = Path(DATA_INPUT)

    # Check input file exists
    if not DATA_INPUT_FILE.exists():
        raise FileNotFoundError(f"Event log not found: {DATA_INPUT_FILE}")

    print("Input event log:", DATA_INPUT_FILE)

    EXPERT_KNOWLEDGE_INPUT_FILE = Path(EXPERT_KNOWLEDGE_INPUT)

    # Check input file exists
    if not DATA_INPUT_FILE.exists():
        raise FileNotFoundError(f"Event log not found: {DATA_INPUT_FILE}")

    print("Miner:", MINER)

    # Start Data-Knowledge-Fused Digital Twin Stochastic Petri Net model extraction pipeline
    extract_spn(
        DATA_INPUT_FILE=str(DATA_INPUT_FILE),
        EXPERT_KNOWLEDGE_INPUT_FILE=str(EXPERT_KNOWLEDGE_INPUT_FILE),
        miner=MINER,
    )


# --------------------------------------------------------------------------
# Execute
# --------------------------------------------------------------------------

if __name__ == "__main__":

    main()
