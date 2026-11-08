import csv
import os
import pandas as pd
import json


def load_raw_expert_knowledge(CSV_FILE):
    if not os.path.exists(CSV_FILE):
        return []

    with open(CSV_FILE, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file, delimiter=";")
        rows = [(row["id"], row["statements"]) for row in reader if row["statements"]]

    ids, statements = zip(*rows)
    return list(ids), list(statements)


def load_formalized_knowledge(
    filename="../intermediate/intermediate_formalization.jsonl",
    expert_csv="../input_data/expert_knowledge.csv",
):
    
    # ==========================================
    # Load expert knowledge CSV
    # ==========================================

    expert_df = pd.read_csv(expert_csv, delimiter=";")

    allowed_statements = set(
        expert_df["statements"].astype(str).str.strip().str.lower()
    )

    # ==========================================
    # Load JSONL
    # ==========================================

    records = []

    with open(filename, "r", encoding="utf-8") as file:

        for line in file:

            line = line.strip()

            if not line:
                continue

            item = json.loads(line)

            original = str(item.get("original", "")).strip().lower()

            # keep only if original exists in CSV statements
            if original not in allowed_statements:
                continue

            records.append(item)

    knowledge_df = pd.DataFrame(records)

    print("Loaded matching knowledge entries:", len(knowledge_df))

    return knowledge_df
