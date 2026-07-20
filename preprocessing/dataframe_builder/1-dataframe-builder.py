import json
import os
import glob
import uuid
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

#set your own root path in .env file and make sure to use a fallback path as well
ROOT_DIR = Path(os.getenv("ROOT_DIR", "/home/ratul/mustcite/")) 
METADATA_ROOT = ROOT_DIR / "data/metadata"
DATAFRAME_OUTPUT_DIR = ROOT_DIR / "data/train_eval_set/v1.0"

# Namespace UUID for deterministic paper ID generation (fixed, never change this)
_FALLBACK_NAMESPACE = "f47ac10b-58cc-4372-a567-0d02b2c3d479"
PAPER_UUID_NAMESPACE = uuid.UUID(os.getenv("PAPER_UUID_NAMESPACE", _FALLBACK_NAMESPACE))

# Conference → (start_year, end_year, only_even, only_odd)
CONFERENCES = {
    "aaai":     (2010, 2025, False, False),
    "acl":      (2017, 2025, False, False),
    "aistats":  (2009, 2025, False, False),
    "colt":     (2011, 2025, False, False),
    "cvpr":     (2013, 2025, False, False),
    "eccv":     (2018, 2024, True,  False),  # only even years
    "emnlp":    (2017, 2025, False, False),
    "iccv":     (2013, 2025, False, True),   # only odd years
    "iclr":     (2013, 2026, False, False),
    "icml":     (2013, 2025, False, False),
    "ijcai":    (2017, 2025, False, False),
    "jmlr":     (2000, 2025, False, False),
    "naacl":    (2013, 2025, False, False),
    "neurips":  (2000, 2025, False, False),
    "uai":      (2015, 2025, False, False),
}

# Generate the list of valid years for a conference

def get_years(start, end, only_even, only_odd):
    """Generate the list of valid years for a conference."""
    years = list(range(start, end + 1))
    if only_even:
        years = [y for y in years if y % 2 == 0]
    if only_odd:
        years = [y for y in years if y % 2 == 1]
    return years


def generate_paper_id(title, venue, year, original_id):
    
    # Uses UUID5 (SHA-1 based) with a fixed namespace so that:
    #  - The same paper always gets the same ID (deterministic)
    #  - Different papers get different IDs (collision-resistant)
    #  - IDs are stable across runs, additions, and deletions
    
    key = f"{title.strip().lower()}|{venue.strip().lower()}|{int(year)}|{original_id.strip().lower()}"
    return str(uuid.uuid5(PAPER_UUID_NAMESPACE, key))


STOP = 10
counter = 0

def main():
    global counter
    rows = []
    skipped_from_json = []
    total_metadat = []

    for conf, (start, end, only_even, only_odd) in sorted(CONFERENCES.items()):
        # remove this later
        # if(counter > STOP):
        #     break

        years = get_years(start, end, only_even, only_odd)
        for year in years:
            # remove this later
            # if(counter > STOP):
            #     break

            metadata_file = os.path.join(METADATA_ROOT, conf, f"{conf}_{year}.json")
            if not os.path.isfile(metadata_file):
                print(f"[SKIP] Metadata not found: {metadata_file}")
                continue

            with open(metadata_file, "r", encoding="utf-8") as f:
                papers = json.load(f)
            for paper in papers:

                # remove this later
                # counter += 1
                # if(counter > STOP):
                #     break


                pdf_path = paper.get("pdf_path", "")
                if not pdf_path:
                    # that paper was not downloaded
                    continue
                absolute_pdf_path = ROOT_DIR / pdf_path
                citation_contexts_path = str(absolute_pdf_path).replace("/data/papers", "/data/citation_contexts").replace(".pdf", ".json")
                if not os.path.exists(citation_contexts_path):
                    # that paper has no citation contexts due to possible reasons:
                    # - Extractor found the citation number mismatch in Nougat texts
                    # - Then even Grobid couldn't extract XML files because the PDF was made with images, not texts
                    continue
                # Now that we have "pdf_path" and citation contexts json both
                id = str(paper.get("id", ""))
                title = paper.get("title", "")
                abstract = paper.get("abstract", "")
                authors = paper.get("authors", [])
                year = paper.get("year", year)
                venue = paper.get("conference", conf)
                path = ""

                grobid_path = pdf_path.replace("data/papers", "data/grobid_output").replace(".pdf", ".grobid.tei.xml")
                if not os.path.exists(ROOT_DIR / grobid_path):
                    marker_path = pdf_path.replace("data/papers", "data/marker_output").replace(".pdf", ".md")
                    if not os.path.exists(ROOT_DIR / marker_path):
                        nougat_path = pdf_path.replace("data/papers", "data/nougat_output").replace(".pdf", ".md")
                        if not os.path.exists(ROOT_DIR / nougat_path):
                            print("Warning: No valid path found for paper (Grobid or Marker or Nougat):", pdf_path)
                        else:
                            path = nougat_path
                    else:
                        path = marker_path
                else:
                    path = grobid_path

                # Generate a deterministic unique paper ID
                paper_id = generate_paper_id(title, venue, year, id)

                rows.append({
                    "paper_id": paper_id,
                    "path": path,
                    "title": title,
                    "abstract": abstract,
                    "year": int(year),
                    "venue": venue,
                    "authors": authors,
                    "references": [],
                })

    print(f"Papers collected: {len(rows)}")
    # Sort: primary by year (asc), secondary by venue (lexicographic asc)
    rows.sort(key=lambda r: (r["year"], r["venue"]))

    # Building the dataframe now
    df = pd.DataFrame(rows)

    # Sanity check: ensure no duplicate paper_ids
    duplicates = df[df.duplicated(subset="paper_id", keep=False)]
    if len(duplicates) > 0:
        print(f"[WARNING] {len(duplicates)} duplicate paper_ids found!")
        print(duplicates[["paper_id", "title", "venue", "year"]].to_string())

    # Set paper_id as the index
    # df = df.set_index("paper_id")

    # authors and references are lists — store as JSON strings
    df["authors"] = df["authors"].apply(lambda x: json.dumps(x, ensure_ascii=False))
    df["references"] = df["references"].apply(lambda x: json.dumps(x, ensure_ascii=False))

    # Saving the dataframe
    os.makedirs(DATAFRAME_OUTPUT_DIR, exist_ok=True)

    parquet_path = DATAFRAME_OUTPUT_DIR / "all_papers.parquet"
    df.to_parquet(parquet_path, engine="pyarrow")
    print(f"Saved {len(df)} papers to {parquet_path}")

    # Also save a CSV for easy inspection
    csv_path = DATAFRAME_OUTPUT_DIR / "all_papers.csv"
    df.to_csv(csv_path)
    print(f"Saved CSV copy to {csv_path}")


if __name__ == "__main__":
    main()