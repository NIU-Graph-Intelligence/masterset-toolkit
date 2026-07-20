import json
import os
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv


load_dotenv()

#set your own root path in .env file and make sure to use a fallback path as well
ROOT_DIR = Path(os.getenv("ROOT_DIR", "/home/ratul/mustcite/")) 
PROMPT_SCORES_ROOT = ROOT_DIR / "data/prompt_scores"
DATAFRAME_INPUT_DIR = ROOT_DIR / "data/train_eval_set/v1.0"
DATAFRAME_OUTPUT_DIR = ROOT_DIR / "data/train_eval_set/v1.0"


def load_prompt_scores(prompt_scores_path):
    """Load prompt scores CSV and build a lookup dict: ref_target -> (type_1, type_2, type_3)."""
    prompt_df = pd.read_csv(prompt_scores_path)
    lookup = {}
    for _, r in prompt_df.iterrows():
        lookup[r["ref_target"]] = (
            str(r.get("type_1_output", "")),
            str(r.get("type_2_output", "")),
            str(r.get("type_3_output", "")),
        )
    return lookup


def add_labels_to_references(df):
    """
    For each paper, open its prompt scores CSV.
    For each reference, match by ref_target and add type_1/2/3_output fields.
    Returns the modified df and a list of missing ref records.
    """
    missing_refs = []
    STOP = None
    processed = 0
    for index, row in tqdm(df.iterrows(), total=len(df), desc="Adding labels", unit="paper"):
        # remove this later
        if STOP is not None and processed >= STOP:
            break
        processed += 1

        main_paper_path = row["path"]
        main_paper_references = json.loads(row["references"]) if isinstance(row["references"], str) else row["references"]

        # Build the prompt scores CSV path
        reduced_path = (
            main_paper_path
            .replace("data/grobid_output/", "")
            .replace("data/nougat_output/", "")
        )
        valid_csv_path = (
            reduced_path
            .replace(".grobid.tei.xml", ".csv")
            .replace(".md", ".csv")
        )
        prompt_scores_path = f"{PROMPT_SCORES_ROOT}/{valid_csv_path}"

        if not os.path.exists(prompt_scores_path):
            # No prompt scores for this paper — set all refs to empty strings
            for single_ref in main_paper_references:
                single_ref["type_1_output"] = ""
                single_ref["type_2_output"] = ""
                single_ref["type_3_output"] = ""
            df.at[index, "references"] = json.dumps(main_paper_references, ensure_ascii=False)
            continue

        scores_lookup = load_prompt_scores(prompt_scores_path)

        for single_ref in main_paper_references:
            ref_target = single_ref["target"]
            if ref_target in scores_lookup:
                t1, t2, t3 = scores_lookup[ref_target]
                single_ref["type_1_output"] = t1
                single_ref["type_2_output"] = ""
                single_ref["type_3_output"] = t3
            else:
                single_ref["type_1_output"] = ""
                single_ref["type_2_output"] = ""
                single_ref["type_3_output"] = ""
                missing_refs.append({
                    "paper_id": row["paper_id"],
                    "paper_title": row["title"],
                    "prompt_scores_path": str(prompt_scores_path),
                    "missing_ref_target": ref_target,
                    "ref_title_from_ref": single_ref.get("title_from_ref", ""),
                })

        df.at[index, "references"] = json.dumps(main_paper_references, ensure_ascii=False)

    return df, missing_refs, processed


def main():
    # Open the dataframe
    dataframe_path = DATAFRAME_INPUT_DIR / "all_papers_with_refs.parquet"
    df = pd.read_parquet(dataframe_path)

    print(f"Loaded {len(df)} papers from {dataframe_path}")

    STOP = None # set to None for a full run

    # Add labels
    df, missing_refs, processed = add_labels_to_references(df)
    if STOP is not None:
        df = df.iloc[:processed].copy()   # keep only the rows we actually labeled

    suffix = f"_first{STOP}" if STOP is not None else ""

    # Save the updated dataframe
    os.makedirs(DATAFRAME_OUTPUT_DIR, exist_ok=True)

    parquet_path = DATAFRAME_OUTPUT_DIR / f"all_papers_with_refs_and_labels{suffix}.parquet"
    df.to_parquet(parquet_path, engine="pyarrow")
    print(f"\nSaved {len(df)} papers to {parquet_path}")

    csv_path = DATAFRAME_OUTPUT_DIR / f"all_papers_with_refs_and_labels{suffix}.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved CSV copy to {csv_path}")

    # Save missing refs report
    missing_report_path = DATAFRAME_OUTPUT_DIR / f"missing_ref_targets{suffix}.json"
    with open(missing_report_path, "w", encoding="utf-8") as f:
        json.dump(missing_refs, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(missing_refs)} missing ref target records to {missing_report_path}")


if __name__ == "__main__":
    main()