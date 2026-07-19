"""
Marker PDF Output — Citation Context Extractor

Extracts references and their in-text citation contexts from Marker-produced
markdown files. Handles two citation formats:

  Format A (page-anchor): Used by ACL/EMNLP/ICML-style papers
    - In-text: [\\(Author et al.,](#page-5-6) [2023\\)](#page-5-6)
    - Refs:    <span id="page-5-6"></span>Author. Year. [Title](URL). Venue.

  Format B (numbered): Used by CVPR/IEEE/NeurIPS-style papers
    - In-text: [23] or [43, 50, 47, 44]
    - Refs:    - [1] Author. Title. In *Venue*, Year.

Output format matches the existing Nougat/GROBID extractors.
"""

import re
import collections
from pathlib import Path

try:
    from .sentence_utils import split_sentences
except ImportError:
    from sentence_utils import split_sentences


# ============================================================
# STEP 1: DETECT CITATION FORMAT
# ============================================================

def _detect_format(text, ref_section):
    """Detect whether the paper uses page-anchor or numbered citations.

    Returns 'page_anchor', 'numbered', or None if references can't be parsed.
    """
    # Check for page-anchor span IDs in the references section
    page_spans = re.findall(r'<span id="(page-\d+-\d+)"></span>', ref_section)
    # Check for numbered reference entries
    numbered_entries = re.findall(r'^\s*-\s*\[(\d+)\]', ref_section, re.MULTILINE)

    if len(page_spans) >= 3:
        return 'page_anchor'
    elif len(numbered_entries) >= 3:
        return 'numbered'
    elif len(page_spans) > 0:
        return 'page_anchor'
    elif len(numbered_entries) > 0:
        return 'numbered'
    return None


# ============================================================
# STEP 2: PARSE REFERENCES
# ============================================================

def _extract_year(text):
    """Extract a 4-digit year from text."""
    m = re.search(r'(?:19|20)\d{2}', text)
    return int(m.group()) if m else None


def _parse_refs_page_anchor(ref_section):
    """Parse references from page-anchor format.

    Returns list of dicts:
        [{'id': 'page-5-6', 'title': '...', 'year': 2023, 'raw': '...'}, ...]
    """
    # Split on <span id="page-X-Y"></span> markers
    # Each entry: span ID followed by text until next span or end
    entries = re.findall(
        r'<span id="(page-\d+-\d+)"></span>(.*?)(?=<span id="page-\d+-\d+">|\Z)',
        ref_section, re.DOTALL
    )

    results = []
    for ref_id, raw_text in entries:
        clean = re.sub(r'\s+', ' ', raw_text).strip()
        if not clean or len(clean) < 10:
            continue

        # Extract year: look for 4-digit year followed by optional letter and period
        year = _extract_year(clean)

        # Extract title from various formats:
        # Format 1: Year. [Title](URL)               (ACL/EMNLP style)
        # Format 2: Author, Init. Title. *Venue*      (ICML/NeurIPS style)
        # Format 3: Year. Title. In *Venue*            (plain text after year)
        title = ''

        # Try Format 1: [Title](URL) after year
        title_match = re.search(
            r'(?:19|20)\d{2}[a-z]?\.\s*\[([^\]]+)\]',
            clean
        )
        if title_match:
            title = title_match.group(1).strip()
            # Sometimes title is split across two markdown links
            after_first = clean[title_match.end():]
            cont_match = re.match(r'\([^)]*\)\[([^\]]+)\]', after_first)
            if cont_match:
                title += cont_match.group(1).strip()
        else:
            # Try Format 2: "Author, I., Author, I. Title. *Venue*"
            # Find text between end-of-author-block and venue marker.
            title_match2 = re.search(
                r'(?:et al\.|[A-Z]\.)\s+'            # End of author block
                r'([A-Z][^.]*(?:\.[^.]*)*?)'          # Title (may contain periods)
                r'\.\s+'                               # End of title
                r'(?:\*|In\s+\*|arXiv|Proceedings|http|pp\.\s)',  # Venue marker
                clean
            )
            if title_match2:
                candidate = title_match2.group(1).strip()
                # Verify: title shouldn't look like "M., Baker, B." (author list)
                if not re.search(r',\s+[A-Z]\.\s*,', candidate):
                    title = candidate

            if not title:
                # Fallback Format 3: "Year. Title. In *Venue*"
                title_match3 = re.search(
                    r'(?:19|20)\d{2}[a-z]?\.\s+([A-Z].*?)'
                    r'(?:\.\s+(?:In\s|Proceedings|Journal|arXiv|http|\*))',
                    clean
                )
                if title_match3:
                    title = title_match3.group(1).strip()

        # Clean up title
        title = re.sub(r'\s+', ' ', title).strip().rstrip('.')

        if title or year:
            results.append({
                'id': ref_id,
                'title': title,
                'year': year,
                'raw': clean[:200],
            })

    return results


def _parse_refs_numbered(ref_section):
    """Parse references from numbered format.

    Returns list of dicts:
        [{'id': '1', 'title': '...', 'year': 2023, 'raw': '...'}, ...]
    """
    # Pattern: - [N] Author text...
    entries = re.findall(
        r'-\s*\[(\d+)\]\s*(.*?)(?=\n\s*-\s*\[\d+\]|\Z)',
        ref_section, re.DOTALL
    )

    results = []
    for num, raw_text in entries:
        clean = re.sub(r'\s+', ' ', raw_text).strip()
        if not clean or len(clean) < 10:
            continue

        year = _extract_year(clean)

        # Extract title: after "Author(s). " find the title sentence
        # Pattern: Author. Title. In *Venue* or Author. Title. *Journal*
        title = ''
        # First try: Author. Title. In *Venue
        title_match = re.search(
            r'(?:^[^.]+\.)\s+([A-Z*].*?)(?:\.\s+(?:In\s+\*|arXiv|Proceedings|\*[A-Z]))',
            clean
        )
        if title_match:
            title = title_match.group(1).strip()
        else:
            # Fallback: just grab text between first and second period
            parts = clean.split('. ', 2)
            if len(parts) >= 2:
                candidate = parts[1].strip()
                # If it starts with uppercase and is reasonably long, it's the title
                if candidate and candidate[0].isupper() and len(candidate) > 5:
                    title = candidate

        # Clean title
        title = re.sub(r'^\*+|\*+$', '', title)  # strip markdown emphasis
        title = re.sub(r'\s+', ' ', title).strip().rstrip('.')

        if title or year:
            results.append({
                'id': num,
                'title': title,
                'year': year,
                'raw': clean[:200],
            })

    return results


# ============================================================
# STEP 3: PARSE SECTIONS FROM MARKDOWN HEADERS
# ============================================================

_SECTION_NUM_RE = re.compile(r'^(\d+)\.?\s')
_APPENDIX_HEAD_RE = re.compile(
    r'^(?:Appendix|A\.|B\.|C\.|D\.|E\.|F\.)\s',
    re.IGNORECASE,
)


def _parse_sections(body):
    """Parse the body into a list of (section_name, section_text) tuples.

    Only tracks MAIN sections (single-number headers like "1 Introduction",
    "2. Related Work") and maps subsections to their parent main section.
    Appendix sections are labelled "Appendix".

    Returns list of (main_section_name, text_block) tuples.
    """
    # Split body into lines and identify section headers
    lines = body.split('\n')
    sections = []  # list of (line_idx, header_level, header_text)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith('#'):
            continue

        # Count header level
        level = 0
        for ch in stripped:
            if ch == '#':
                level += 1
            else:
                break

        header_text = stripped[level:].strip()
        # Remove span IDs from header text
        header_text = re.sub(r'<span[^>]*></span>\s*', '', header_text).strip()

        if header_text:
            sections.append((i, level, header_text))

    if not sections:
        return [('', body)]

    # Build main section mapping
    # Walk through sections, track current main section
    current_main = ''
    section_to_main = {}

    for idx, (line_idx, level, header_text) in enumerate(sections):
        # Check if this is a main section (number-only prefix)
        num_match = _SECTION_NUM_RE.match(header_text)
        if num_match:
            # It's numbered — check if main (single digit) or sub (has dot in number)
            full_num = header_text[:header_text.index(' ')] if ' ' in header_text else header_text
            full_num = full_num.rstrip('.')
            if '.' not in full_num:
                # Main section
                current_main = header_text
            # else: subsection — keep current_main
        elif _APPENDIX_HEAD_RE.match(header_text):
            current_main = 'Appendix'
        elif header_text.lower() in ('abstract', 'references', 'acknowledgements',
                                      'acknowledgments', 'acknowledgement'):
            current_main = header_text
        # else: unnumbered sub-heading, keep current_main

        section_to_main[idx] = current_main

    # Now build (main_section, text) pairs
    result = []
    for idx, (line_idx, level, header_text) in enumerate(sections):
        # Text runs from this header's next line to the next header's line
        start = line_idx + 1
        if idx + 1 < len(sections):
            end = sections[idx + 1][0]
        else:
            end = len(lines)

        text_block = '\n'.join(lines[start:end]).strip()
        main_section = section_to_main.get(idx, '')
        result.append((main_section, text_block))

    return result


# ============================================================
# STEP 4: REPLACE CITATIONS WITH MARKERS
# ============================================================

def _replace_citations_page_anchor(text, ref_ids):
    """Replace page-anchor citations with (citation #page-X-Y) markers.

    Handles patterns like:
        [\\(Author et al.,](#page-5-6) [2023\\)](#page-5-6)
        [Author et al.](#page-5-6) [\\(2023\\)](#page-5-6)

    Each [text](#page-X-Y) link is replaced with (citation #page-X-Y) if the
    anchor points to a known reference. Non-reference links (figures, tables,
    sections) are replaced with their display text.
    """
    def replace_link(match):
        display = match.group(1)
        anchor = match.group(2)
        if anchor in ref_ids:
            return f'(citation #{anchor})'
        else:
            # Non-reference link: inline the display text
            # Clean up escaped parens
            clean = display.replace('\\(', '(').replace('\\)', ')')
            return clean

    # Replace all [text](#anchor) links
    result = re.sub(r'\[([^\]]*)\]\(#(page-\d+-\d+)\)', replace_link, text)
    return result


def _replace_citations_numbered(text, ref_nums):
    """Replace numbered citations with (citation #N) markers.

    Handles patterns like:
        [23]         → (citation #23)
        [43, 50, 47] → (citation #43)(citation #50)(citation #47)

    Only replaces if the number corresponds to a known reference.
    """
    def replace_bracket(match):
        full = match.group(0)
        inner = match.group(1)

        # Don't replace if followed by '(' — it's a markdown link [text](url)
        after = text[match.end():match.end() + 1] if match.end() < len(text) else ''
        if after == '(':
            return full

        # Split by commas
        nums = re.findall(r'\d+', inner)
        if not nums:
            return full

        # Check if at least one is a valid reference number
        valid = [n for n in nums if n in ref_nums]
        if not valid:
            return full

        # Replace each number with a citation marker
        parts = []
        for n in nums:
            if n in ref_nums:
                parts.append(f'(citation #{n})')
            else:
                parts.append(f'[{n}]')
        return ''.join(parts)

    # Match [N] or [N, M, K] but not [text](url)
    result = re.sub(r'\[(\d+(?:\s*,\s*\d+)*)\](?!\()', replace_bracket, text)
    return result


# ============================================================
# STEP 5: EXTRACT CITATION CONTEXTS
# ============================================================

def _find_citation_ids_in_text(text):
    """Find all (citation #id) markers in text. Returns set of IDs."""
    return set(re.findall(r'\(citation #([^)]+)\)', text))


def _extract_3_sentence_context(sentences, cite_sent_idx):
    """Extract a 3-sentence context window around the citation sentence."""
    n = len(sentences)
    idx = cite_sent_idx

    has_prev = idx > 0
    has_next = idx < n - 1

    if has_prev and has_next:
        parts = [sentences[idx - 1], sentences[idx], sentences[idx + 1]]
    elif not has_prev:
        parts = sentences[idx:idx + 3]
    elif not has_next:
        start = max(0, idx - 2)
        parts = sentences[start:idx + 1]
    else:
        parts = [sentences[idx]]

    return ' '.join(parts)


# ============================================================
# STEP 6: MAIN EXTRACTION FUNCTION
# ============================================================

def extract_citation_contexts_from_marker(file_path):
    """Extract citation contexts from a Marker-produced markdown file.

    Args:
        file_path: Path to the .md file

    Returns:
        List of dicts matching the standard output format:
        [
            {
                "target": "page-5-6" or "1",
                "title": "...",
                "year": 2023,
                "cite": "(citation #page-5-6)" or "(citation #1)",
                "contexts": [
                    {"section": "1 Introduction", "context": "..."},
                    ...
                ]
            },
            ...
        ]
    """
    with open(str(file_path), 'r', encoding='utf-8') as f:
        text = f.read()

    # --- 1. Split into body and references ---
    ref_header_match = re.search(r'^#{1,4}\s+References\s*$', text, re.MULTILINE)
    if not ref_header_match:
        # Try alternate patterns
        ref_header_match = re.search(r'^#{1,4}\s+Bibliography\s*$', text, re.MULTILINE)
    if not ref_header_match:
        return []

    body = text[:ref_header_match.start()]
    ref_section = text[ref_header_match.start():]

    # --- 2. Detect format and parse references ---
    fmt = _detect_format(body, ref_section)
    if fmt is None:
        return []

    if fmt == 'page_anchor':
        ref_list = _parse_refs_page_anchor(ref_section)
    else:
        ref_list = _parse_refs_numbered(ref_section)

    if not ref_list:
        return []

    ref_map = {r['id']: r for r in ref_list}
    ref_id_set = set(ref_map.keys())

    # --- 3. Parse sections and replace citations with markers ---
    sections = _parse_sections(body)

    contexts_by_ref = collections.defaultdict(list)
    seen_contexts = collections.defaultdict(set)

    for main_section, section_text in sections:
        # Skip empty or non-content sections
        if not section_text or main_section.lower() in ('abstract', 'references'):
            continue

        # Replace citations with markers
        if fmt == 'page_anchor':
            marked_text = _replace_citations_page_anchor(section_text, ref_id_set)
        else:
            marked_text = _replace_citations_numbered(section_text, ref_id_set)

        # Clean: strip markdown formatting noise, tables, figures
        # Remove markdown images ![alt](url)
        marked_text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', marked_text)
        # Remove HTML tags (except our markers)
        marked_text = re.sub(r'<(?!citation)[^>]+>', '', marked_text)
        # Remove markdown emphasis **bold** and *italic*
        marked_text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', marked_text)
        # Collapse whitespace
        marked_text = re.sub(r'\n{3,}', '\n\n', marked_text)

        # Split into paragraphs (double newline separated)
        paragraphs = re.split(r'\n\s*\n', marked_text)

        for para in paragraphs:
            para = re.sub(r'\s+', ' ', para).strip()
            if not para or len(para) < 20:
                continue

            cite_ids_in_para = _find_citation_ids_in_text(para)
            if not cite_ids_in_para:
                continue

            sentences = split_sentences(para)
            if not sentences:
                continue

            for sent_idx, sent in enumerate(sentences):
                cite_ids_in_sent = _find_citation_ids_in_text(sent)
                for cid in cite_ids_in_sent:
                    if cid in ref_id_set:
                        context = _extract_3_sentence_context(sentences, sent_idx)

                        if context not in seen_contexts[cid]:
                            seen_contexts[cid].add(context)
                            contexts_by_ref[cid].append({
                                'section': main_section,
                                'context': context,
                            })

    # --- 4. Assemble output ---
    results = []
    for ref in ref_list:
        rid = ref['id']
        contexts = contexts_by_ref.get(rid, [])

        results.append({
            'target': rid,
            'title': ref['title'],
            'year': ref['year'],
            'cite': f'(citation #{rid})',
            'contexts': contexts,
        })

    return results