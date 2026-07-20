# Preprocessing Pipeline

## Overview

This document outlines the complete preprocessing pipeline for data preparation of MasterSet.

---

## Step 0: Create an environment variable

Inside this repository, create a `'.env'` file and put one variable named `'ROOT_DIR'`. It is path to the parent directory where the sub-modules/sub-repositories (`'OpenPapers'`, `'masterset-toolkit'`, and `'masterset-benchmark'`) stay. 
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

The value of the `'ROOT_DIR'` would be `'/Desktop/mustcite/'`.


## Step 1: Grobid and Nougat Processing

Starts with Grobid and Nougat processing.

- **grobid_processor**
- **nougat_processor**

We get .md files of extracted texts by Nougat and .xml files of parsed texts by Grobid.

One clarification: In the paper, our primary extractor was Nougat, and as a fallback we used Grobid. Now, we are using Grobid as our primary PDF processor and Nougat as a fallback. In this version, we made the three-sentence extraction from raw paper texts more accurate, and robust.

---

## Step 2: Citation Context Extraction

We run the citation_context_extractor package after that.

- First using `--grobid` argument. Nougat will automatically skip the alpha-tag citation number mismatch patterns.
- Those skipped ones will be covered by the `--nougat` argument. What it will do is: for the missing citation contexts, it will extract those contexts from the Nougat generated .md files because Grobid couldn't process them from its .md files (because of number mismatches of alpha-tag).

---

## Step 3: Dataset Building and Filtering

Now that, We have the contexts ready, we could easily generate two prompts for each paper-reference pair. But wait, we do not need all of them. Because processing all the prompts has time and cost contraints. So:

We will first build our dataset from `/preprocessing/dataframe-builder` (script 1 and 2):

- **Script-1** (`1-dataframe-builder.py`): Generates the whole paper corpus without the 'references' column.
- **Script-2** (`2-add-references.py`): Has two purposes:
  1. It will take the dataframe built by Script-1 and add (only the matched papers inside this dataframe) the reference papers inside references [].
  2. It will change the citation contexts JSON files. It will add two fields inside each JSON objects:
     - `'in_dataset'` = true if found inside the dataset, false otherwise
     - `'in_conference_list'` = true if in ALL_CONF, false otherwise

---

## Step 4: Prompt Generation

Now we know, which prompts to build for LLM processing i.e. IF (`'in_dataset'` = true || `'in_conference_list'` = true). Now we run the `'generate_prompts'` package. It will automatically only generate those prompts needed for LLM processing inside `'generated_prompts'` directory.

---

## Step 5: LLM Processing

We created a package named `'run_on_prompts'` to generate the Type-1 and Type-2 ground truths. This package has our own Google Cloud Platform setup and `'gemini-2.5-flash'` model backend (API) along with some other models. For our `'MasterSet-CoreML-v1'` version, we used `'gemini-2.5-flash'` for generating the ground truths. On purpose, we are exluding the `'run_on_prompts'` package. However, users may run the prompts using their own setup, whether it be from GCP account or using open-weights models, only if they want to recreate the labels. Otherwise, we already shared the labels and train and evaluation set as well which users may use.



---

## Step 6: Label Addition

After we have the labels ready by the LLM, we run `/preprocessing/dataframe_builder/3-add-three-labels.py`. We will have the labels inside the reference obejcts in the reference list for each paper.

---

## Step 7: Core Set and Train/Eval Split

Now we run the `/preprocessing/dataframe_builder/4-build-core-set-and-train-eval.py` to get the core (Main 3 or 4 conferences) paper set, train and eval sets.