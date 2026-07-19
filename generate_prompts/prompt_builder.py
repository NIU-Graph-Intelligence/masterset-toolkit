"""Prompt generation logic — builds Type 1 and Type 2 prompt text files from citation context JSON."""


# ── System prompts (from run_prompt.py) ───────────────────────────────────────

SYSTEM_TYPE1 = """You are an expert research assistant in AI and machine learning.

Your task is to determine whether a cited work is either:
1. a baseline or direct comparison method in the current paper, OR
2. a must-cite core reference for the current paper's main task, benchmark, dataset, or method.

A citation qualifies (answer 1) IF ANY of the following are true:
- The cited work is directly compared against the proposed method in the CURRENT PAPER
- The cited work is explicitly used as a baseline in experiments or results
- The cited work is the source of a main benchmark, dataset, or evaluation task used in the CURRENT PAPER
- The cited work defines a core task, problem setting, or method that the CURRENT PAPER directly builds on, evaluates on, or centers around

Strong evidence for answer 1 includes:
- Language such as "compared to", "outperforms", "evaluated against", "our method vs.", "surpasses", "baseline" in Experiments or Results
- Statements in Experimental Setup or Experiments showing that the paper evaluates on a benchmark/dataset introduced by the cited work
- Statements showing the cited work defines the main task/problem central to the current paper

A citation does NOT qualify (answer 0) if:
- It is cited only for background, motivation, or general context
- It appears only as loosely related prior work
- It describes a method or resource that is mentioned but not central to the paper’s main experiments, task, or contribution
- The comparison language refers to what OTHER papers did, not the CURRENT PAPER
- It is a peripheral citation rather than a core benchmark, task, dataset, or comparison target

Important:
- The decision must be based on the CURRENT PAPER, not on what the cited paper itself did
- A citation can qualify even if it is not a baseline, as long as it is a must-cite core reference for the paper’s main benchmark, dataset, task, or method
- Citation contexts may be sentence fragments, so use the section label carefully

[EXAMPLE — Answer: 1]
1. Section: "4 Experiments"
   Context: "Our method achieves 84.2 F1, outperforming [CITATION] (79.1) on SciERC."
→ Direct baseline/comparison in results. Answer: 1

[EXAMPLE — Answer: 1]
1. Section: "4 Experimental Setup"
   Context: "We evaluate our model on StrategyQA [CITATION], a benchmark for implicit reasoning."
→ The cited work is the source of a main benchmark used in the paper. This is a must-cite core reference. Answer: 1

[EXAMPLE — Answer: 0]
1. Section: "2 Related Work"
   Context: "Previous work such as [CITATION] explored prompt-based methods for NLP."
→ Background reference only. Answer: 0

Respond with ONLY a single digit: 0 or 1. No explanation. No punctuation."""


SYSTEM_TYPE2 = """You are an expert research assistant in AI and machine learning.
Score the relevance of a citation to the CORE TASK AND METHOD of a paper (1-5 scale).

1 — General background, unrelated to this paper's task or method.
    Example: A general NLP survey cited in a citation classification paper.

2 — Tangentially related; shares a broad area but not this specific task or method.
    Example: A general BERT paper cited in a scientific document retrieval paper
    where BERT is not the proposed method.

3 — Conceptually related but neither the same task nor a directly extended method.
    Example: A text classification paper cited in a citation intent classification paper.

4 — Substantially relevant: same task OR a key method component is derived from it.
    Example: SciBERT cited in a paper that fine-tunes SciBERT for citation classification.

5 — Core relevance: same task AND method is directly extended, OR defines the
    primary dataset/benchmark used.
    Example: The ACL-ARC dataset paper cited in a paper that evaluates on ACL-ARC.

Rules:
- Primary dataset/benchmark citation → at least 4
- Method directly extended → at least 4
- Both task AND method shared → 5

Note: Citation contexts may be sentence fragments due to extraction. Use the section
label and available context to make your best judgment.

Respond with ONLY a single digit: 1, 2, 3, 4, or 5. No explanation. No punctuation."""


# ── Formatters ────────────────────────────────────────────────────────────────

def format_contexts(contexts: list[dict]) -> str:
    """
    Format a list of {"section": ..., "context": ...} dicts into numbered list.
    Returns empty string if contexts list is empty.
    """
    if not contexts:
        return ""
    lines = []
    for i, ctx in enumerate(contexts, start=1):
        lines.append(f'{i}. Section: "{ctx["section"]}"')
        lines.append(f'   Context: "{ctx["context"]}"')
    return "\n".join(lines)


def build_citation_info(ref: dict) -> str:
    """Build the citation info string from a reference dict."""
    return f'"cited_as": "{ref["cite"]}", "title": "{ref["title"]}"'


# ── Prompt builders ───────────────────────────────────────────────────────────

def build_type1_prompt(title: str, citation_info: str, formatted_contexts: str) -> str:
    """Build the full Type 1 prompt (system + user) as a single text block."""
    user_content = f"""Paper Title: {title}

Citation: {citation_info}

Citation Contexts:
{formatted_contexts}

Is this citation used as a baseline or direct comparison in this paper's experiments?
Answer:"""

    return f"""[SYSTEM]
{SYSTEM_TYPE1}

[USER]
{user_content}"""


def build_type2_prompt(title: str, citation_info: str, formatted_contexts: str) -> str:
    """Build the full Type 2 prompt (system + user) as a single text block."""
    user_content = f"""Paper Title: {title}

Citation: {citation_info}

Citation Contexts:
{formatted_contexts}

How relevant is this citation to the paper's core task and method?
Score:"""

    return f"""[SYSTEM]
{SYSTEM_TYPE2}

[USER]
{user_content}"""
