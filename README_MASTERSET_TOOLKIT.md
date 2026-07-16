# Preprocessing Pipeline

## Overview

This document outlines the complete preprocessing pipeline for data preparation of MasterSet.

---

## Step 1: Nougat and Grobid Processing

Starts with Nougat and Grobid processing.

- **nougat_processor**
- **grobid_processor**

We get .tei.xml files of extracted texts by Grobid and .md files of parsed texts by Marker. Read READMEs from the following two packages:
1. grobid_processor
2. nougat_processor

---

## Step 2: Citation Context Extraction

We run the citation_context_extractor package after that.

- First using `--grobid` argument. Because Grobid is our primarily tools for citation extraction. For fallback, we use Nougat (using `--nougat`).
- Those skipped ones will be covered by the `--nougat` argument. What it will do is: for the missing citation contexts, it will extract those contexts from the Nougat generated .md files.

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

Now we know, which prompts to build for LLM processing i.e. IF (`'in_dataset'` = true || `'in_conference_list'` = true). Now we run the `'generate_prompts'` package. It will automatically only generate those prompts needed for LLM processing inside `'generated_prompts_filtered'` directory.

---

## Step 5: LLM Processing

Now we can run the LLM processing package `'run_on_prompts'` to generate the Type-1 and Type-2 ground truths. This package has 3 backends:

1. Qwen
2. Gemini 2.5 Flash
3. Gemini 2.5 Batch API

---

## Step 6: Label Addition

After we have the labels ready by the LLM, we run `/preprocessing/dataframe_builder/3-add-three-labels.py`. We will have the labels inside the reference obejcts in the reference list for each paper.

---

## Step 7: Core Set and Train/Eval Split

Now we run the `/preprocessing/dataframe_builder/4-build-core-set-and-train-eval.py` to get the core (Main 3 or 4 conferences) paper set, train and eval sets.