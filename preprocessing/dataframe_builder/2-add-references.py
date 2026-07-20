import json
import os
import re
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from collections import defaultdict, Counter
from rapidfuzz import process, fuzz
from dotenv import load_dotenv

#set your own root path in .env file and make sure to use a fallback path as well
ROOT_DIR = Path(os.getenv("ROOT_DIR", "/home/ratul/mustcite/")) 
DATAFRAME_INPUT_DIR = ROOT_DIR / "data/train_eval_set/v1.0"
DATAFRAME_OUTPUT_DIR = ROOT_DIR / "data/train_eval_set/v1.0"
CITATION_CONTEXTS_ROOT = ROOT_DIR / "data/citation_contexts"

STOP_WORDS = {'a', 'an', 'the', 'and', 'or', 'in', 'on', 'of', 'for', 'with', 'to', 'is', 'at'}

CONFERENCE_LIST = [
    "aaai", "acl", "aistats", "colt", "cvpr", "eccv", "emnlp",
    "iccv", "iclr", "icml", "ijcai", "jmlr", "naacl", "neurips", "uai"
]


def normalize(title):
    """Lowercase, remove non-alphanumeric chars, collapse whitespace."""
    title = title.lower()
    title = re.sub(r'[^\w\s]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def get_citation_context_path(paper_path):
    """Convert any tool output path (grobid/marker/nougat) to citation context JSON path."""
    reduced_path = paper_path
    for tool_dir in ("data/grobid_output/", "data/marker_output/", "data/nougat_output/"):
        if tool_dir in reduced_path:
            reduced_path = reduced_path.split(tool_dir, 1)[1]
            break

    for ext in (".grobid.tei.xml", ".xml", ".md"):
        if reduced_path.endswith(ext):
            reduced_path = reduced_path[:-len(ext)] + ".json"
            break

    return f"{CITATION_CONTEXTS_ROOT}/{reduced_path}"


def build_lookup_structures(df):
    """
    Pre-build:
      - exact_lookup: normalized title -> list of (paper_id, original_title, venue)
      - normalized_titles: list of normalized titles (indexed by position)
      - paper_ids: list of paper_ids (indexed by position)
      - original_titles: list of original titles (indexed by position)
      - venues: list of venues (indexed by position)
      - year_map: position index -> year
      - inverted_index: word -> set of position indices
    """
    exact_lookup = {}
    normalized_titles = []
    paper_ids = []
    original_titles = []
    venues = []
    year_map = {}
    inverted_index = defaultdict(set)

    for i, (_, r) in enumerate(df.iterrows()):
        orig_title = r["title"]
        norm_title = normalize(orig_title)
        pid = r["paper_id"]
        yr = int(r["year"])
        venue = r["venue"]

        # Exact lookup
        if norm_title not in exact_lookup:
            exact_lookup[norm_title] = []
        exact_lookup[norm_title].append((pid, orig_title, venue))

        # Indexed lists
        normalized_titles.append(norm_title)
        paper_ids.append(pid)
        original_titles.append(orig_title)
        venues.append(venue)
        year_map[i] = yr

        # Inverted index: map each non-stop word to its position index
        for word in norm_title.split():
            if word not in STOP_WORDS:
                inverted_index[word].add(i)

    return exact_lookup, normalized_titles, paper_ids, original_titles, venues, year_map, inverted_index


def find_match(ref_title, ref_year, exact_lookup, normalized_titles, paper_ids, original_titles, venues, year_map, inverted_index):
    """
    Try exact match first, then fuzzy match using inverted index to narrow candidates.
    Returns (matched_paper_id, matched_title, matched_venue, match_type).
    """
    norm_ref = normalize(ref_title)

    # --- Step 1: Exact match ---
    if norm_ref in exact_lookup:
        pid, orig, venue = exact_lookup[norm_ref][0]
        return pid, orig, venue, "exact"

    # --- Step 2: Fuzzy match with inverted index narrowing ---
    query_words = set(w for w in norm_ref.split() if w not in STOP_WORDS)
    if not query_words:
        return "", "", "", "no_match"

    # Count how many query words appear in each candidate, filter by year ±1
    candidate_counts = Counter()
    for word in query_words:
        for idx in inverted_index.get(word, set()):
            candidate_year = year_map.get(idx)
            if candidate_year is not None and (ref_year is None or abs(candidate_year - ref_year) <= 1):
                candidate_counts[idx] += 1

    # Take top 25 candidates by word overlap
    top_indices = [idx for idx, _ in candidate_counts.most_common(25)]
    if not top_indices:
        return "", "", "", "no_match"

    candidate_choices = {idx: normalized_titles[idx] for idx in top_indices}

    match = process.extractOne(norm_ref, candidate_choices, score_cutoff=90)
    if match:
        matched_idx = match[2]
        return paper_ids[matched_idx], original_titles[matched_idx], venues[matched_idx], "fuzzy"

    return "", "", "", "no_match"


def update_citation_context_jsons(df, exact_lookup, normalized_titles, paper_ids, original_titles, venues, year_map, inverted_index):
    """
    Walk through each paper's citation context JSON file.
    For each reference entry, add two fields:
      - in_dataset: true if the reference title matched a paper in our dataframe
      - in_conference_list: true if the matched paper's venue is in CONFERENCE_LIST
    Save the updated JSON back to the same path.
    """
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Updating JSON files", unit="paper"):
        citation_contexts_path = get_citation_context_path(row["path"])

        if not os.path.exists(citation_contexts_path):
            continue

        with open(citation_contexts_path, "r", encoding="utf-8") as f:
            paper_contexts = json.load(f)

        modified = False
        for ref_paper in paper_contexts:
            ref_paper_title = ref_paper["title"]
            ref_paper_year = ref_paper["year"]

            matched_paper_id, matched_title, matched_venue, match_type = find_match(
                ref_paper_title, ref_paper_year,
                exact_lookup, normalized_titles, paper_ids, original_titles, venues, year_map, inverted_index
            )

            in_dataset = match_type != "no_match"
            in_conference_list = matched_venue.lower() in CONFERENCE_LIST if matched_venue else False

            ref_paper["in_dataset"] = in_dataset
            ref_paper["in_conference_list"] = in_conference_list
            modified = True

        if modified:
            with open(citation_contexts_path, "w", encoding="utf-8") as f:
                json.dump(paper_contexts, f, ensure_ascii=False, indent=2)


def main():
    # Open the dataframe
    dataframe_path = DATAFRAME_INPUT_DIR / "all_papers.parquet"
    df = pd.read_parquet(dataframe_path)

    # Build lookup structures
    print("Building lookup structures...")
    exact_lookup, normalized_titles, paper_ids, original_titles, venues, year_map, inverted_index = build_lookup_structures(df)
    print(f"Built index over {len(normalized_titles)} papers, {len(inverted_index)} unique words.")

    # Parse the references column (stored as JSON strings) into actual lists
    df["references"] = df["references"].apply(lambda x: json.loads(x) if isinstance(x, str) else x)

    stats = {"exact": 0, "fuzzy": 0, "no_match": 0, "total_refs": 0}

    # --- Pass 1: Build references in the dataframe ---
    for index, row in tqdm(df.iterrows(), total=len(df), desc="Adding references", unit="paper"):
        main_paper_references = row["references"]

        citation_contexts_path = get_citation_context_path(row["path"])

        if not os.path.exists(citation_contexts_path):
            continue

        with open(citation_contexts_path, "r", encoding="utf-8") as f:
            paper_contexts = json.load(f)

        for ref_paper in paper_contexts:
            ref_paper_target = ref_paper["target"]
            ref_paper_title = ref_paper["title"]
            ref_paper_year = ref_paper["year"]

            stats["total_refs"] += 1

            matched_paper_id, matched_title, matched_venue, match_type = find_match(
                ref_paper_title, ref_paper_year,
                exact_lookup, normalized_titles, paper_ids, original_titles, venues, year_map, inverted_index
            )
            stats[match_type] += 1

            if match_type != "no_match":
                matched_reference = {
                    "target": ref_paper_target,
                    "matched_paper_id": matched_paper_id,
                    "title": matched_title,
                    "title_from_ref": ref_paper_title,
                    "venue": matched_venue,
                    "year": ref_paper_year,
                }
                main_paper_references.append(matched_reference)

        df.at[index, "references"] = main_paper_references

    # Print stats
    print(f"\n--- Matching Stats ---")
    print(f"Total references processed: {stats['total_refs']}")
    print(f"Exact matches:              {stats['exact']}")
    print(f"Fuzzy matches:              {stats['fuzzy']}")
    print(f"No match found:             {stats['no_match']}")

    # Serialize references back to JSON strings for storage
    df["references"] = df["references"].apply(lambda x: json.dumps(x, ensure_ascii=False))

    # Save dataframe
    os.makedirs(DATAFRAME_OUTPUT_DIR, exist_ok=True)

    parquet_path = DATAFRAME_OUTPUT_DIR / "all_papers_with_refs.parquet"
    df.to_parquet(parquet_path, engine="pyarrow")
    print(f"\nSaved {len(df)} papers to {parquet_path}")

    csv_path = DATAFRAME_OUTPUT_DIR / "all_papers_with_refs.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved CSV copy to {csv_path}")

    # --- Pass 2: Update citation context JSON files with in_dataset and in_conference_list ---
    print("\nUpdating citation context JSON files...")
    update_citation_context_jsons(df, exact_lookup, normalized_titles, paper_ids, original_titles, venues, year_map, inverted_index)
    print("Done updating JSON files.")


if __name__ == "__main__":
    main()