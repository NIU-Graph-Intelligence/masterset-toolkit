"""
This script extracts four three conference papers from the whole dataframe. Those conferences are:

1. NeurIPS
2. ICML
3. ICLR

"""

import json
import os
import pandas as pd
from tqdm import tqdm
from pathlib import Path
from dotenv import load_dotenv


#set your own root path in .env file and make sure to use a fallback path as well
ROOT_DIR = Path(os.getenv("ROOT_DIR", "/home/ratul/mustcite/")) 
TARGET_CONFERENCES = {'neurips', 'icml', 'iclr'}
TRAIN_YEARS = (2018, 2024)
EVAL_YEAR = (2025, 2026) # remove
DATAFRAME_DIR = ROOT_DIR / "data_test/train_eval_set/v1.0"


def build_venue_lookup(papers_df: pd.DataFrame) -> dict:
    """Build a paper_id -> venue dict for fast lookups."""
    return dict(zip(papers_df["paper_id"], papers_df["venue"]))


def filter_papers(papers_df: pd.DataFrame, venue_lookup: dict) -> pd.DataFrame:
    """
    Reduces the graph size by keeping core conference papers and their direct citations.

    The logic is as follows:
    1. Identifies a "core" set of papers from the TARGET_CONFERENCES.
    2. Finds all papers that are cited by this core set.
    3. Creates a final, reduced graph containing only core papers and their direct citations.
    """

    print("\n--- Applying Graph Reduction and Year Split ---")
    print(f"Target conferences: {TARGET_CONFERENCES}")
    print(f"Training years: {TRAIN_YEARS[0]}-{TRAIN_YEARS[1]}, Evaluation year: {EVAL_YEAR}")

    # 1. Identify the "core" papers from the target conferences
    core_papers_df = papers_df[papers_df["venue"].isin(TARGET_CONFERENCES)]
    core_paper_ids = set(core_papers_df["paper_id"].tolist())
    print(f"Found {len(core_paper_ids)} core papers from target conferences.")

    # 2. Identify all papers cited by the core set (excluding core conferences themselves)
    cited_paper_ids = set()

    for reference_list in tqdm(core_papers_df["references"].tolist(), desc="Finding cited papers"):
        if not reference_list:
            continue
        for ref in reference_list:
            matched_id = ref.get("matched_paper_id")
            if not matched_id:
                continue
            ref_venue = venue_lookup.get(matched_id)
            if ref_venue and ref_venue not in TARGET_CONFERENCES:
                cited_paper_ids.add(matched_id)

    print(f"Found {len(cited_paper_ids)} unique papers cited by the core set.")

    # 3. Combine the sets to get all papers to keep
    final_ids_to_keep = core_paper_ids.union(cited_paper_ids)
    print(f"Total papers in the reduced graph: {len(final_ids_to_keep)}")

    core_papers_df = papers_df[papers_df["paper_id"].isin(final_ids_to_keep)].copy()

    return core_papers_df


def split_papers(core_papers_df: pd.DataFrame):
    """
    Splits the reduced graph into a training set (TRAIN_YEARS) and an evaluation set (EVAL_YEAR).

    Returns:
        A tuple containing two DataFrames: (training_papers_df, evaluation_papers_df)
    """
    training_papers_df = core_papers_df[
        core_papers_df["year"].between(TRAIN_YEARS[0], TRAIN_YEARS[1])
    ].copy()
    evaluation_papers_df = core_papers_df[
        core_papers_df["year"].between(EVAL_YEAR[0], EVAL_YEAR[1]) & 
        (core_papers_df["venue"].isin(TARGET_CONFERENCES))
    ].copy()

    print(f"Split into {len(training_papers_df)} training papers and {len(evaluation_papers_df)} evaluation papers.")

    return training_papers_df, evaluation_papers_df


def main():
    print("Loading dataframe...")
    papers_df = pd.read_parquet(DATAFRAME_DIR / "all_papers_with_refs_and_labels.parquet")

    # Parse references from JSON strings to lists
    papers_df["references"] = papers_df["references"].apply(
        lambda x: json.loads(x) if isinstance(x, str) else x
    )

    # Pre-build venue lookup for fast reference checking
    venue_lookup = build_venue_lookup(papers_df)

    core_papers_df = filter_papers(papers_df, venue_lookup)
    training_papers_df, evaluation_papers_df = split_papers(core_papers_df)

    # Serialize references back to JSON strings for storage
    for df in [core_papers_df, training_papers_df, evaluation_papers_df]:
        df["references"] = df["references"].apply(
            lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, list) else x
        )

    # Save
    core_papers_df.to_parquet(DATAFRAME_DIR / "core_papers.parquet", engine="pyarrow", index=False)
    core_papers_df.to_csv(DATAFRAME_DIR / "core_papers.csv", index=False)
    training_papers_df.to_parquet(DATAFRAME_DIR / "train.parquet", engine="pyarrow", index=False)
    training_papers_df.to_csv(DATAFRAME_DIR / "train.csv", index=False)
    evaluation_papers_df.to_parquet(DATAFRAME_DIR / "eval.parquet", engine="pyarrow", index=False)
    evaluation_papers_df.to_csv(DATAFRAME_DIR / "eval.csv", index=False)

    print(f"\nSaved core set: {len(core_papers_df)} papers")
    print(f"Saved training set: {len(training_papers_df)} papers")
    print(f"Saved evaluation set: {len(evaluation_papers_df)} papers")


if __name__ == "__main__":
    main()