# Preprocessing Pipeline

## Overview

This document outlines the complete preprocessing pipeline for the data preparation of MasterSet.

---

## Step 0: Create an environment variable

Inside this repository, create a `.env` file and put one variable named `ROOT_DIR` in it. It is the path to the parent directory where the sub-modules/sub-repositories (`OpenPapers`, `masterset-toolkit`, and `masterset-benchmark`) stay.
For example, if your directory structure is like this:

├── ~/Desktop/mustcite/
    ├── data/
          ├── papers
          ├── metadata
          ├── grobid_output
          ├── nougat_output
          ├── citation_contexts
          ├── generated_prompts
          ├── prompt_scores
          ├── train_eval_set
              ├── v1.0
                  ├── all_papers_with_refs_and_labels.parquet
                  ├── train.parquet
                  ├── eval.parquet
    ├── masters-toolkit
          ├── grobid_processor
          ├── nougat_processor
          ├── citation_context_extractor
          ├── etc. packages ---------
    ├── masterset-benchmark # for experiments

The value of `ROOT_DIR` would be `/Desktop/mustcite/`.


## Step 1: Grobid and Nougat Processing

The pipeline starts with Grobid and Nougat processing.

- **grobid_processor**
- **nougat_processor**

We get .md files of texts extracted by Nougat and .xml files of texts parsed by Grobid.

One clarification: in the paper, our primary extractor was Nougat and Grobid was the fallback. Now we are using Grobid as our primary PDF processor and Nougat as the fallback. In this version, we made the three-sentence extraction from raw paper texts more accurate and robust.

---

## Step 2: Citation Context Extraction

After that, we run the citation_context_extractor package.

- First with the `--grobid` argument. It will automatically skip the alpha-tag citation number mismatch patterns.
- Those skipped ones will be covered by the `--nougat` argument. What it does is: for the missing citation contexts, it extracts those contexts from the Nougat-generated .md files, because Grobid couldn't process them from its .xml files (due to alpha-tag number mismatches).

---

## Step 3: Dataset Building and Filtering

Now that we have the contexts ready, we could easily generate two prompts for each paper-reference pair. But we do not need all of them, because processing all the prompts has time and cost constraints. So:

We first build our dataset from `/preprocessing/dataframe-builder` (scripts 1 and 2):

- **Script-1** (`1-dataframe-builder.py`): Generates the whole paper corpus without the `references` column.
- **Script-2** (`2-add-references.py`): Has two purposes:
  1. It takes the dataframe built by Script-1 and adds the reference papers (only the matched papers inside this dataframe) into `references []`.
  2. It modifies the citation context JSON files by adding two fields to each JSON object:
     - `in_dataset` = true if found inside the dataset, false otherwise
     - `in_conference_list` = true if in ALL_CONF, false otherwise

---

## Step 4: Prompt Generation

Now we know which prompts to build for LLM processing, i.e. IF (`in_dataset` = true || `in_conference_list` = true). Next we run the `generate_prompts` package. It automatically generates only those prompts needed for LLM processing inside the `generated_prompts` directory.

---

## Step 5: LLM Processing

We created a package named `run_on_prompts` to generate the Type-1 and Type-2 ground truths. This package uses our own Google Cloud Platform setup with the `gemini-2.5-flash` model backend (API), along with some other models. For our `MasterSet-CoreML-v1` version, we used `gemini-2.5-flash` to generate the ground truths. We are intentionally excluding the `run_on_prompts` package. However, users may run the prompts using their own setup, whether from a GCP account or with open-weights models, if they want to recreate the labels. Otherwise, we have already shared the labels as well as the train and evaluation sets, which users may use directly.

---

## Step 6: Label Addition

Once the labels are ready from the LLM, we run `/preprocessing/dataframe_builder/3-add-three-labels.py`. This puts the labels inside the reference objects in the reference list of each paper.

---

## Step 7: Core Set and Train/Eval Split

Finally, we run `/preprocessing/dataframe_builder/4-build-core-set-and-train-eval.py` to get the core paper set (main 3 or 4 conferences) and the train and eval sets.