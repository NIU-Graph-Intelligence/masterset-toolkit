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

def get_section_header(element):
    """Walk up from element to find the nearest ancestor div's <head> text."""
    # Check immediate parent div, then ancestors
    heads = element.xpath('ancestor::tei:div[1]/tei:head', namespaces=NS)
    if heads:
        # Combine head number and text
        head = heads[0]
        n = head.get('n', '')
        text = head.text if head.text else ''
        return f"{n} {text}".strip() if n else text.strip()
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


def build_body_sections(root, valid_bibl_ids, exclude_appendix=False):
    """
    Build a list of (section_header, paragraph_text, original_p_element) tuples
    from the body of the paper.

    If exclude_appendix is True, skip sections whose header starts with
    'Appendix' or 'A.' etc.
    """
    body = root.find('.//tei:body', namespaces=NS)
    if body is None:
        return []

    results = []
    all_paragraphs = body.xpath('.//tei:p', namespaces=NS)

    for p in all_paragraphs:
        header = get_section_header(p)

        if exclude_appendix:
            h_lower = header.lower()
            if any(h_lower.startswith(x) for x in ['appendix', 'a.', 'b.', 'c.', 'supplementary']):
                continue

        text = process_paragraph_to_text(p, valid_bibl_ids)
        if text:
            results.append((header, text, p))

    return results


# ============================================================
# STEP 3: SENTENCE SPLITTING
# ============================================================

# Common abbreviations that end with periods but are NOT sentence endings
_ABBREV_PATTERN = re.compile(
    r'(?:et al|i\.e|e\.g|cf|vs|Fig|Eq|Sec|Ref|Tab|App|Prop|Thm|Lem|Cor|Def|'
    r'Prof|Dr|Mr|Mrs|Ms|Jr|Sr|Inc|Ltd|Corp|Vol|No|pp|Chap|Dept|Univ|approx|'
    r'resp|w\.r\.t|s\.t|viz|ca|[A-Z])$'
)


def split_sentences(text):
    """
    Split text into sentences, being careful about abbreviations, decimal
    numbers, and citation markers.

    Returns a list of sentence strings.
    """
    if not text:
        return []

    sentences = []
    current_start = 0
    i = 0

    while i < len(text):
        ch = text[i]

        if ch in '.!?':
            # Check if this is a real sentence boundary
            before = text[max(0, i - 20):i + 1]
            after = text[i + 1:min(len(text), i + 10)].lstrip()

            # Not a boundary if: abbreviation
            if _ABBREV_PATTERN.search(before.rstrip('.!?')):
                i += 1
                continue

            # Not a boundary if: decimal number (e.g., "3.14")
            if i > 0 and text[i - 1].isdigit() and after and after[0].isdigit():
                i += 1
                continue

            # Not a boundary if: inside parentheses that look like a citation
            # e.g., "(Author et al., 2022)"
            depth = 0
            for j in range(i, max(i - 200, -1), -1):
                if text[j] == ')':
                    depth += 1
                elif text[j] == '(':
                    depth -= 1
                    if depth < 0:
                        break
            if depth < 0:
                # We're inside parens - not a boundary
                i += 1
                continue

            # It's a boundary if followed by space + uppercase or end of text
            if not after or (after[0].isupper() or after[0] in '("\'['):
                sent = text[current_start:i + 1].strip()
                if sent:
                    sentences.append(sent)
                current_start = i + 1
        i += 1

    # Last piece
    remainder = text[current_start:].strip()
    if remainder:
        sentences.append(remainder)

    return sentences


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
