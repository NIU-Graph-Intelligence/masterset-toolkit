"""
GROBID citation context extraction utilities.

Extracts references with their in-text citation contexts from GROBID-processed
academic papers in TEI XML format. Produces the same output format as the
Nougat-based extractor:

[
    {
        "target": "b0",
        "title": "Paper title",
        "year": 2022,
        "cite": "(Author et al., 2022)",
        "contexts": [
            {"section": "Introduction", "context": "...3-sentence window..."},
            ...
        ]
    },
    ...
]


"""

import re
import json
import sys
import copy
from pathlib import Path
from lxml import etree

# ============================================================
# CONFIGURATION

NS = {
    'tei': 'http://www.tei-c.org/ns/1.0',
    'xml': 'http://www.w3.org/XML/1998/namespace',
}
XML_ID = '{http://www.w3.org/XML/1998/namespace}id'


# ============================================================
# STEP 1: PARSE BIBLIOGRAPHY
# ============================================================

def parse_bibl_structs(root):
    """
    Parse all <biblStruct> entries from the bibliography.

    Returns a list of dicts:
        [{'id': 'b0', 'title': '...', 'year': 2021, 'authors': ['Smith', 'Jones']}, ...]
    """
    bibls = root.xpath('//tei:listBibl/tei:biblStruct', namespaces=NS)
    results = []
    for b in bibls:
        bib_id = b.get(XML_ID)
        if not bib_id:
            continue

        # Title
        title_el = b.find('.//tei:title[@type="main"]', namespaces=NS)
        if title_el is None:
            title_el = b.find('.//tei:title', namespaces=NS)
        title = title_el.text.strip() if (title_el is not None and title_el.text) else ""

        # Year
        year = None
        date_el = b.find('.//tei:date', namespaces=NS)
        if date_el is not None:
            when = date_el.get('when', '')
            # Extract 4-digit year from 'when' attribute (e.g. "2021", "2021-05", "2021-05-01")
            ym = re.search(r'((?:19|20)\d{2})', when)
            if ym:
                year = int(ym.group(1))
            elif date_el.text:
                ym = re.search(r'((?:19|20)\d{2})', date_el.text)
                if ym:
                    year = int(ym.group(1))

        # Authors (surnames)
        authors = b.xpath('.//tei:author/tei:persName/tei:surname/text()', namespaces=NS)

        results.append({
            'id': bib_id,
            'title': title,
            'year': year,
            'authors': authors,
        })

    return results


def get_valid_bibl_ids(bibl_list):
    """
    Return set of bibl IDs that have a meaningful title (>3 chars) OR at least
    one author surname. This is intentionally lenient because GROBID sometimes
    fails to extract titles from certain reference formats while still correctly
    linking in-text refs via target IDs.
    """
    valid = set()
    for b in bibl_list:
        has_title = b['title'] and len(b['title'].strip()) > 3
        has_authors = len(b['authors']) > 0
        if has_title or has_authors:
            valid.add(b['id'])
    return valid


# ============================================================
# STEP 2: BUILD STRUCTURED BODY TEXT WITH CITATION MARKERS
# ============================================================

def _is_main_section_n(n_val):
    """Check if an n attribute value represents a main section (e.g. '1', '6', '1.')
    vs a subsection (e.g. '2.1', '5.3', '3.1.') or unnumbered (empty string).

    Main sections have a single integer, optionally followed by a trailing dot:
    '1', '2', '10', '1.', '6.'
    Subsections have internal dots: '2.1', '3.4.2', '3.1.'
    Unnumbered heads have no n or empty n.
    """
    if not n_val:
        return False
    # Strip trailing dot then check for pure integer
    cleaned = n_val.strip().rstrip('.')
    return re.fullmatch(r'\d+', cleaned) is not None


_APPENDIX_HEAD_RE = re.compile(
    r'^(?:Appendix|A\.|B\.|C\.|D\.|E\.|F\.)',
    re.IGNORECASE,
)


def _is_appendix_head(text):
    """Check if a head's text indicates an appendix section."""
    return bool(_APPENDIX_HEAD_RE.match(text.strip()))


def _build_div_to_main_section_map(root):
    """Walk all divs in both <body> and <back> in document order and build a
    mapping from each div element to its parent main section header string.

    GROBID typically outputs flat divs (all siblings under <body>), so
    subsection divs with n='2.1' are siblings of n='2', not children.
    Unnumbered divs (n='') also appear as flat siblings.

    For <back> matter (appendix, acknowledgements, etc.), all divs are
    mapped to "Appendix" since they have no numbered main sections.
    Body divs whose head looks like an appendix (e.g. "A. Theoretical Proofs")
    are also mapped to "Appendix".

    Returns:
        dict mapping sourceline of div element → main section header string
        (sourceline is stable across XPath queries unlike id())
    """
    div_to_main = {}

    # --- Body divs ---
    body = root.find('.//tei:body', namespaces=NS)
    if body is not None:
        current_main = ''
        found_any_numbered = False
        body_divs = body.xpath('tei:div', namespaces=NS)

        for div in body_divs:
            head = div.find('tei:head', namespaces=NS)
            if head is not None:
                n = (head.get('n', '') or '').strip()
                text = (head.text or '').strip()
                full_header = f'{n} {text}'.strip() if n else text

                if _is_main_section_n(n):
                    current_main = full_header
                    found_any_numbered = True
                elif _is_appendix_head(text):
                    # Appendix section in body (some papers have appendix in body)
                    current_main = 'Appendix'

            div_to_main[div.sourceline] = current_main

        # --- Fallback for fully unnumbered papers (e.g. AAAI) ---
        # If GROBID didn't extract ANY numbered sections, every body div
        # maps to "". Fall back to using each div's own head text as the
        # section label, since there's no main/sub distinction to make.
        if not found_any_numbered:
            for div in body_divs:
                head = div.find('tei:head', namespaces=NS)
                if head is not None:
                    text = (head.text or '').strip()
                    if _is_appendix_head(text):
                        div_to_main[div.sourceline] = 'Appendix'
                    elif text:
                        div_to_main[div.sourceline] = text
                    else:
                        div_to_main[div.sourceline] = ''
                else:
                    div_to_main[div.sourceline] = ''

        # --- Cleanup pass for mixed papers ---
        # Some papers have partial numbering: subsections like n="2.1"
        # exist but their parent main section n="2" is missing from GROBID
        # output. Those subsections map to "" because current_main was
        # never set before the first real main section.
        # Fix: any div still mapped to "" that has a head with text gets
        # its own head text as the section label.
        # Also handles headless first divs (Introduction) where GROBID
        # failed to extract the section header entirely.
        for i, div in enumerate(body_divs):
            if div_to_main.get(div.sourceline) == '':
                head = div.find('tei:head', namespaces=NS)
                if head is not None:
                    n = (head.get('n', '') or '').strip()
                    text = (head.text or '').strip()
                    full_header = f'{n} {text}'.strip() if n else text
                    if _is_appendix_head(text):
                        div_to_main[div.sourceline] = 'Appendix'
                    elif full_header:
                        div_to_main[div.sourceline] = full_header
                elif i == 0:
                    # First div in body with no <head> at all.
                    # GROBID failed to extract the section header.
                    # The first body div with content is virtually always
                    # the Introduction (GROBID puts abstracts in <front>).
                    ps = div.findall('tei:p', namespaces=NS)
                    if ps:
                        div_to_main[div.sourceline] = 'Introduction'

    # --- Back matter divs (appendix, acknowledgements, etc.) ---
    back = root.find('.//tei:back', namespaces=NS)
    if back is not None:
        for div in back.xpath('.//tei:div', namespaces=NS):
            div_to_main[div.sourceline] = 'Appendix'

    return div_to_main


def get_section_header(element, div_to_main):
    """Look up the main section header for a paragraph element using the
    pre-built div-to-main-section map.

    Falls back to the div's own head text if the div isn't in the map
    (shouldn't happen, but defensive).
    """
    anc_divs = element.xpath('ancestor::tei:div[1]', namespaces=NS)
    if anc_divs:
        div = anc_divs[0]
        main_section = div_to_main.get(div.sourceline)
        if main_section is not None:
            return main_section
        # Fallback: use the div's own head
        head = div.find('tei:head', namespaces=NS)
        if head is not None:
            n = (head.get('n', '') or '').strip()
            text = (head.text or '').strip()
            return f'{n} {text}'.strip() if n else text
    return ""


def process_paragraph_to_text(p_element, valid_bibl_ids):
    """
    Convert a <p> element to plain text, replacing valid <ref type="bibr">
    with "(citation #id)" markers, and inlining other ref text.

    Returns the cleaned text string.
    """
    p_copy = copy.deepcopy(p_element)

    for ref in p_copy.xpath('.//tei:ref[@type="bibr"]', namespaces=NS):
        target = ref.get('target')

        if target and target.startswith('#'):
            bibl_id = target[1:]
            if bibl_id in valid_bibl_ids:
                replacement = f"(citation #{bibl_id})"
            else:
                replacement = ''.join(ref.itertext()).strip()
        else:
            replacement = ''.join(ref.itertext()).strip()

        # Replace the ref element with its replacement text in the tree
        prev = ref.getprevious()
        parent = ref.getparent()
        if prev is not None:
            prev.tail = (prev.tail or '') + replacement
        else:
            parent.text = (parent.text or '') + replacement

        if ref.tail:
            if prev is not None:
                prev.tail += ref.tail
            else:
                parent.text += ref.tail

        parent.remove(ref)

    text = etree.tostring(p_copy, method='text', encoding='unicode')
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _merge_p_and_formula_runs(div_element, valid_bibl_ids):
    """Walk a div's direct children and merge <p> elements that are split by
    <formula> elements into single logical paragraphs.

    GROBID often breaks a paragraph around inline/display math:
        <p>...text before formula...</p>
        <formula>...math...</formula>
        <p>...text continuing after formula...</p>

    This function detects such runs and produces merged text. A "run" is a
    sequence of consecutive <p> and <formula> children that starts and ends
    with a <p> (formulas between them act as glue). A standalone <p> with no
    adjacent formula is emitted as-is.

    Returns:
        list of (merged_text, first_p_element) tuples.
        first_p_element is needed for section header lookup later.
    """
    TEI_P = '{http://www.tei-c.org/ns/1.0}p'
    TEI_FORMULA = '{http://www.tei-c.org/ns/1.0}formula'

    children = list(div_element)
    results = []
    i = 0

    while i < len(children):
        child = children[i]

        if child.tag != TEI_P:
            i += 1
            continue

        # Start a run: collect this <p> and any following <formula><p> pairs
        run_elements = [child]
        first_p = child
        j = i + 1

        while j < len(children):
            if children[j].tag == TEI_FORMULA:
                # Check if a <p> follows the formula
                if j + 1 < len(children) and children[j + 1].tag == TEI_P:
                    run_elements.append(children[j])      # formula
                    run_elements.append(children[j + 1])   # next <p>
                    j += 2
                else:
                    # Formula at the end with no following <p> — include it
                    run_elements.append(children[j])
                    j += 1
                    break
            else:
                break

        # Build merged text from the run
        text_parts = []
        for el in run_elements:
            if el.tag == TEI_P:
                t = process_paragraph_to_text(el, valid_bibl_ids)
                if t:
                    text_parts.append(t)
            elif el.tag == TEI_FORMULA:
                t = ''.join(el.itertext()).strip()
                t = re.sub(r'\s+', ' ', t).strip()
                if t:
                    text_parts.append(t)

        merged = ' '.join(text_parts)
        if merged:
            results.append((merged, first_p))

        i = j

    return results


def build_body_sections(root, valid_bibl_ids, exclude_appendix=False):
    """
    Build a list of (section_header, paragraph_text, original_p_element) tuples
    from both <body> and <back> of the paper.

    Merges <p> elements that are split by <formula> elements into single
    logical paragraphs, so that 3-sentence context windows are not cut off
    at formula boundaries.

    section_header is always the MAIN section (e.g. '6 Results and Discussion'),
    never a subsection (e.g. '6.2 Codebook Analysis') or unnumbered sub-heading.
    Back-matter divs are labelled "Appendix".

    If exclude_appendix is True, skip sections labelled "Appendix".
    """
    # Pre-build the div → main section mapping (covers body + back)
    div_to_main = _build_div_to_main_section_map(root)

    results = []

    # Collect all divs from body and back
    all_divs = []

    body = root.find('.//tei:body', namespaces=NS)
    if body is not None:
        all_divs.extend(body.xpath('.//tei:div', namespaces=NS))

    back = root.find('.//tei:back', namespaces=NS)
    if back is not None:
        all_divs.extend(back.xpath('.//tei:div', namespaces=NS))

    # Walk each div and merge p/formula runs within it
    for div in all_divs:
        merged_paras = _merge_p_and_formula_runs(div, valid_bibl_ids)

        for text, first_p in merged_paras:
            header = get_section_header(first_p, div_to_main)

            if exclude_appendix and header == 'Appendix':
                continue

            results.append((header, text, first_p))

    return results


# ============================================================
# STEP 3: SENTENCE SPLITTING
# ============================================================

# Import shared sentence splitter (also used by ctx_utils.py for nougat)
try:
    from .sentence_utils import split_sentences
except ImportError:
    from sentence_utils import split_sentences


# ============================================================
# STEP 4: EXTRACT CITATION CONTEXTS
# ============================================================

def find_citation_ids_in_text(text):
    """Find all (citation #id) markers in a text string. Returns set of IDs."""
    return set(re.findall(r'\(citation #([^)]+)\)', text))


def extract_3_sentence_context(sentences, cite_sent_idx):
    """
    Given a list of sentences and the index of the sentence containing the
    citation, return a 3-sentence context window:
        prev_sentence + citation_sentence + next_sentence

    Edge cases:
        - First sentence: citation + next1 + next2
        - Last sentence:  prev2 + prev1 + citation
    """
    n = len(sentences)
    idx = cite_sent_idx

    has_prev = idx > 0
    has_next = idx < n - 1

    if has_prev and has_next:
        # Normal case
        parts = [sentences[idx - 1], sentences[idx], sentences[idx + 1]]
    elif not has_prev:
        # First sentence in this paragraph
        parts = sentences[idx:idx + 3]
    elif not has_next:
        # Last sentence
        start = max(0, idx - 2)
        parts = sentences[start:idx + 1]
    else:
        parts = [sentences[idx]]

    return ' '.join(parts)


def extract_citation_contexts_from_grobid(file_path, exclude_appendix=False):
    """
    Main extraction function.

    Args:
        file_path: Path to GROBID TEI XML file
        exclude_appendix: Whether to exclude appendix sections

    Returns:
        List of dicts with the standard output format:
        [
            {
                "target": "b0",
                "title": "...",
                "year": 2022,
                "cite": "(Author et al., 2022)",
                "contexts": [
                    {"section": "Introduction", "context": "..."},
                    ...
                ]
            },
            ...
        ]
    """
    tree = etree.parse(str(file_path))
    root = tree.getroot()

    # --- 1. Parse bibliography ---
    bibl_list = parse_bibl_structs(root)
    valid_ids = get_valid_bibl_ids(bibl_list)
    bibl_map = {b['id']: b for b in bibl_list}

    # --- 2. Extract body paragraphs with cleaned text ---
    body_paragraphs = build_body_sections(root, valid_ids, exclude_appendix)

    # --- 4. For each paragraph, split into sentences and find citation contexts ---
    # Store: { bibl_id: [ (section, context_text), ... ] }
    import collections
    contexts_by_ref = collections.defaultdict(list)
    seen_contexts = collections.defaultdict(set)  # avoid duplicate contexts

    for header, para_text, p_element in body_paragraphs:
        # Find which citation IDs appear in this paragraph
        cite_ids_in_para = find_citation_ids_in_text(para_text)
        if not cite_ids_in_para:
            continue

        sentences = split_sentences(para_text)
        if not sentences:
            continue

        for sent_idx, sent in enumerate(sentences):
            cite_ids_in_sent = find_citation_ids_in_text(sent)
            for cid in cite_ids_in_sent:
                if cid in valid_ids:
                    context = extract_3_sentence_context(sentences, sent_idx)

                    # Deduplicate
                    if context not in seen_contexts[cid]:
                        seen_contexts[cid].add(context)
                        contexts_by_ref[cid].append({
                            'section': header,
                            'context': context,
                        })

    # --- 5. Assemble output ---
    results = []
    for b in bibl_list:
        bib_id = b['id']
        if bib_id not in valid_ids:
            continue

        contexts = contexts_by_ref.get(bib_id, [])

        results.append({
            'target': bib_id,
            'title': b['title'],
            'year': b['year'],
            'cite': f"(citation #{bib_id})",
            'contexts': contexts,
        })

    return results
