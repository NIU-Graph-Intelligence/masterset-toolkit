"""
Context extraction utilities — cite key extraction, body parsing, sentence extraction.
"""

import re
import json
import sys

# ============================================================
# Import from our internal ref_utils module
from .ref_utils import (
    extract_references,
    extract_reference_section,
    split_references,
)


# ============================================================
# STEP 1: EXTRACT CITE KEY FROM RAW REFERENCE
# ============================================================

def extract_cite_key(raw_ref: str) -> list:
    """
    Extract the in-text citation key(s) from a raw reference entry.
    The cite key is what appears in the paper body when citing this work.
    
    Returns a list of possible cite strings.
    """
    r = raw_ref.strip().replace('\n', ' ')
    # Remove leading bullet
    r = re.sub(r'^\*\s*', '', r)
    
    cites = []
    
    # --- P1: "Name [year]" or "Name et al. [year]" or "Name and Name [year]" ---
    m = re.match(
        r'^([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)?'
        r'(?:\s+et\s+al\.?)?)'
        r'\s*\[(\d{4}[a-z]?)\]',
        r
    )
    if m:
        cites.append(f'{m.group(1)} [{m.group(2)}]')
        return cites
    
    # --- P2: Leading "Name et al. (year)" or "Name-Name et al. (year)" ---
    # Also handles multi-word names: "Sohl-Dickstein et al. (2015)"
    # Also handles multi-word first-names: "Thi Phan et al. (2022)"
    # Also handles "Name and Name and Name (year)"
    # Also handles "Van der Maaten and Hinton (2008)"
    m = re.match(
        r'^((?:(?:Van|De|Von)\s+(?:der|de|den)\s+)?'  # multi-word prefix
        r'[A-Z][a-z]+(?:-[A-Z][a-z]+)?'                # first name part
        r'(?:\s+[A-Z][a-z]+)*'                          # additional name words (Thi Phan)
        r'(?:\s+(?:and|&)\s+(?:(?:Van|De|Von)\s+(?:der|de|den)\s+)?[A-Z][a-z]+(?:-[A-Z][a-z]+)?)*'  # and Name
        r'(?:\s+et\s+al\.?)?'                           # et al.
        r')\s*\((\d{4}[a-z]?)\)',
        r
    )
    if m:
        full_cite = f'{m.group(1)} ({m.group(2)})'
        cites.append(full_cite)
        # If the name part contains multiple "and" (3+ authors), 
        # the body likely uses "FirstAuthor et al. (year)" instead
        name_part = m.group(1)
        and_count = len(re.findall(r'\s+and\s+', name_part))
        if and_count >= 2:
            first_name = name_part.split()[0]
            cites.append(f'{first_name} et al. ({m.group(2)})')
        return cites
    
    # --- P3: "[Tag]" bracket tags ---
    m = re.match(r'^(\[[^\]]+\])', r)
    if m:
        cites.append(m.group(1))
        return cites
    
    # --- P4: "(number)" prefix ---
    m = re.match(r'^\((\d+)\)', r)
    if m:
        cites.append(f'({m.group(1)})')
        return cites
    
    # --- P5: "I. LastName and I. LastName (year)" two-author format ---
    # e.g. "N. Anand and T. Achim (2022)Title..."
    # e.g. "V. Liu and L. B. Chilton (2022)Title..."
    m = re.match(
        r'^(?:[A-Z]\.\s*)+([A-Z][a-z]+(?:-[A-Z][a-z]+)?)'
        r'\s+and\s+'
        r'(?:[A-Z]\.\s*)*(?:[A-Z]\.\s+)?([A-Z][a-z]+(?:-[A-Z][a-z]+)?)'
        r'\s*\((\d{4}[a-z]?)\)',
        r
    )
    if m:
        cites.append(f'{m.group(1)} and {m.group(2)} ({m.group(3)})')
        return cites
    
    # --- P6: "I. LastName, I. LastName, ... (year)" multi-author format ---
    # e.g. "G. Papandreou, T. Zhu, ... (2018)Personlab:..."
    # Also handles multi-word lastnames after initials:
    # e.g. "S. Mehran Kazemi, ..." or "D. Singh Sachan, ..."
    # Capture all words after initial(s) up to first comma, take LAST word as lastname.
    m = re.match(r'^(?:[A-Z]\.\s*)+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:-[A-Z][a-z]+)?)\s*[,\s]', r)
    if m:
        name_part = m.group(1)
        lastname = name_part.split()[-1]  # last word is the lastname
        ym = re.search(r'\((\d{4}[a-z]?)\)', r)
        if ym:
            before_year = r[:ym.start()]
            comma_count = before_year.count(',')
            if comma_count == 0:
                cites.append(f'{lastname} ({ym.group(1)})')
            else:
                cites.append(f'{lastname} et al. ({ym.group(1)})')
        else:
            cites.append(f'{lastname} et al.')
        return cites
    
    # --- P7: "LastName, I.; LastName, I.; ..." AAAI/semicolon format ---
    m = re.match(r'^([A-Z][a-z]+(?:-[A-Z][a-z]+)?)\s*,\s*[A-Z]', r)
    if m:
        lastname = m.group(1)
        ym = re.search(r'(\d{4}[a-z]?)\.', r)
        if not ym:
            ym = re.search(r'\((\d{4}[a-z]?)\)', r)
        if ym:
            year = ym.group(1)
            before = r[:ym.start()]
            semicolons = before.count(';')
            if semicolons == 0:
                cites.append(f'{lastname} ({year})')
            elif semicolons == 1 and 'and' in before:
                m2 = re.search(r';\s*(?:and\s+)?([A-Z][a-z]+(?:-[A-Z][a-z]+)?)\s*,', before)
                if m2:
                    cites.append(f'{lastname} and {m2.group(1)} ({year})')
                else:
                    cites.append(f'{lastname} et al. ({year})')
            else:
                cites.append(f'{lastname} et al. ({year})')
        else:
            cites.append(f'{lastname} et al.')
        return cites
    
    # --- P8: "Initial(s) LastName, ..." no-period initials ---
    # e.g. "E Michael Nussbaum, Ian J Dove, Nathan Slife, ... 2018. Title..."
    # The initial(s) are single uppercase letters NOT followed by a period.
    # Capture all words after the initial(s) up to the first comma, then
    # take the LAST word as the lastname.
    m = re.match(
        r'^(?:[A-Z]\s+)+((?:[A-Z][a-z]+\s+)*[A-Z][a-z]+(?:-[A-Z][a-z]+)?)\s*,',
        r
    )
    if m:
        name_part = m.group(1)
        lastname = name_part.split()[-1]  # last word is the lastname
        ym = re.search(r'(\d{4}[a-z]?)\.', r)
        if not ym:
            ym = re.search(r'\((\d{4}[a-z]?)\)', r)
        if ym:
            year = ym.group(1)
            before = r[:ym.start()]
            comma_count = before.count(',')
            if comma_count == 0:
                cites.append(f'{lastname} ({year})')
            elif comma_count == 1:
                # Could be single author with "Lastname, Firstname"
                cites.append(f'{lastname} ({year})')
            else:
                cites.append(f'{lastname} et al. ({year})')
        else:
            cites.append(f'{lastname} et al.')
        return cites
    
    # --- P9: "Firstname Lastname, Firstname Lastname, ..." full-name format ---
    # e.g. "Jason Wei, Xuezhi Wang, Dale Schuurmans, ... 2022. Title..."
    # e.g. "Yi Tay, M. Dehghani, ... (2022)Unifying language..."
    # e.g. "Luyu Gao, Zhuyun Dai, and Jamie Callan. 2021. Re-think..."
    # Capture "Firstname(s) Lastname" before the first comma; lastname is the last word.
    m = re.match(
        r'^([A-Z][a-z]+(?:\s+[A-Z]\.?)*\s+[A-Z][a-z]+(?:-[A-Z][a-z]+)?)\s*,',
        r
    )
    if m:
        name_part = m.group(1)
        lastname = name_part.split()[-1]  # last word is the lastname
        # Search for (year) first to avoid matching arXiv IDs like "2205.05131"
        ym = re.search(r'\((\d{4}[a-z]?)\)', r)
        if not ym:
            ym = re.search(r'(?:^|[\s,;])((?:19|20)\d{2}[a-z]?)\.', r)
        if ym:
            year = ym.group(1)
            before = r[:ym.start()]
            comma_count = before.count(',')
            and_count = len(re.findall(r'\band\b', before))
            if comma_count <= 1 and and_count == 0:
                cites.append(f'{lastname} ({year})')
            elif comma_count == 1 and and_count == 1:
                # Two-author: "First Last and First Last (year)"
                m2 = re.search(r'and\s+(?:[A-Z]\.?\s+)*([A-Z][a-z]+(?:-[A-Z][a-z]+)?)\s*[\.(]', before + r[ym.start():])
                if m2:
                    cites.append(f'{lastname} and {m2.group(1)} ({year})')
                else:
                    cites.append(f'{lastname} et al. ({year})')
            else:
                cites.append(f'{lastname} et al. ({year})')
        else:
            cites.append(f'{lastname} et al.')
        return cites
    
    return cites


# ============================================================
# STEP 2: DETECT CITATION FORMAT IN BODY
# ============================================================

def detect_citation_format(body: str) -> str:
    """
    Detect the dominant citation format in the paper body.
    Returns: 'author_year', 'numeric', or 'alpha_tag'
    """
    # Count author-year cites: "Name et al. (year)" or "Name (year)" with () or []
    ay_count = len(re.findall(
        r'[A-Z][a-z]+(?:\s+(?:and|et)\s+[A-Za-z. ]+?)?\s*[\(\[]\d{4}[a-z]?[\)\]]',
        body
    ))
    # Count numeric cites: [1], [2, 3], [1, 2, 3]
    num_count = len(re.findall(r'\[\d+(?:,\s*\d+)*\]', body))
    # Count alpha tag cites: [DKS19], [GDDM14]
    tag_count = len(re.findall(r'\[[A-Z][A-Za-z+\\(){}^]+\d{2,4}[a-z]?\]', body))
    
    if ay_count > num_count and ay_count > tag_count:
        return 'author_year'
    elif num_count >= tag_count:
        return 'numeric'
    else:
        return 'alpha_tag'


def has_alpha_tag_numeric_mismatch(raw_refs: list, body: str) -> bool:
    """
    Detect when references use alpha tags (e.g. [DKS17], [GDDM14], [KPR+17])
    but Nougat converted the in-body citations to numeric [number] format.
    
    This mismatch means we cannot reliably map references to their in-body
    citations, so the entire file should be skipped.
    
    Returns True if mismatch is detected (file should be skipped).
    """
    # Count how many raw references start with an alpha tag like [DKS17], [BB20], etc.
    # Alpha tags: bracket content has letters and ends with digits, but is NOT purely numeric.
    # Examples: [DKS17], [GDDM14], [KPR+17], [HBV+20], [Hus18], [vdVT18]
    # Also handles LaTeX escapes: [DJV\({}^{+}\)13], [KPR\({}^{+}\)17]
    alpha_tag_count = 0
    for r in raw_refs:
        r_clean = re.sub(r'^\*\s*', '', r.strip())
        # Match references starting with [AlphaTag] where the tag contains letters
        # and is not purely numeric
        m = re.match(r'^\[([^\]]+)\]', r_clean)
        if m:
            tag = m.group(1).strip()
            # Remove LaTeX escapes for +/- superscripts
            tag_clean = re.sub(r'\\[({}\s^)+]+', '', tag)
            # Alpha tag: contains at least one letter AND at least one digit,
            # but is NOT purely numeric
            has_letter = bool(re.search(r'[A-Za-z]', tag_clean))
            has_digit = bool(re.search(r'\d', tag_clean))
            is_purely_numeric = bool(re.match(r'^\d+$', tag_clean))
            if has_letter and has_digit and not is_purely_numeric:
                alpha_tag_count += 1
    
    # If a significant portion of references use alpha tags...
    if len(raw_refs) < 3:
        return False
    alpha_ratio = alpha_tag_count / len(raw_refs)
    if alpha_ratio < 0.3:
        return False
    
    # ...and the body uses numeric citations [N], it's a mismatch
    num_count = len(re.findall(r'\[\d+(?:,\s*\d+)*\]', body))
    # Also count alpha tags in body — if they exist, it's NOT a mismatch
    tag_count = len(re.findall(r'\[[A-Z][A-Za-z+\\(){}^]+\d{2,4}[a-z]?\]', body))
    
    if num_count > 3 and tag_count < num_count * 0.1:
        return True
    
    return False


# ============================================================
# STEP 3: FIND BODY TEXT AND SECTIONS
# ============================================================

def find_reference_section_bounds(text: str) -> tuple:
    """Find (ref_start, ref_end) in text."""
    for pat in [r'\n##\s*References?\s*\n', r'\n##\s*Bibliography\s*\n',
                r'\n##\s*REFERENCES?\s*\n', r'\n\*\*References?\*\*\s*\n',
                r'\n#\s*References?\s*\n', r'\nReferences?\s*\n\s*\n']:
        m = re.search(pat, text)
        if m:
            post = text[m.end():]
            ns = re.search(r'\n#{1,2}\s+\S', post)
            return (m.start(), m.end() + ns.start() if ns else len(text))
    return (len(text), len(text))


def get_body_text(text: str, ref_start: int, ref_end: int, exclude_appendix: bool) -> str:
    """Get body text excluding the reference list itself."""
    before = text[:ref_start]
    if exclude_appendix or ref_end >= len(text):
        return before
    return before + "\n\n" + text[ref_end:]


def parse_main_sections(body: str) -> list:
    """Parse body into MAIN sections only (## headers). Returns [(header, start, end)]."""
    headers = list(re.finditer(r'^##\s+(.+)$', body, re.MULTILINE))
    sections = []
    for i, m in enumerate(headers):
        title = m.group(1).strip()
        title = re.sub(r'\*\*(.+?)\*\*', r'\1', title).strip('#').strip()
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(body)
        sections.append((title, start, end))
    if not sections:
        sections = [("", 0, len(body))]
    return sections


# ============================================================
# STEP 4: FIND CITATION OCCURRENCES IN BODY
# ============================================================

def find_cite_occurrences(body: str, cite_key: str, cite_format: str) -> list:
    """
    Find all positions where cite_key appears in body.
    Returns [(start, end), ...].
    """
    # For author_year: cite_key is like "Author et al. (2023)" or "Author and Name (2020)"
    # Need to match both (year) and [year] forms in body
    # Also match parenthetical form: "(Author et al., year)"
    
    m = re.match(r'^(.+?)\s*[\(\[]([\d]{4}[a-z]?)[\)\]]$', cite_key)
    if m:
        author_part = m.group(1).strip()
        year_part = m.group(2)
        ae = re.escape(author_part)
        
        # When year has a letter suffix (e.g. 2016a), also try the base year
        # since the body often cites as just (2016) without the a/b suffix
        year_variants = [year_part]
        base_year = re.match(r'^(\d{4})[a-z]$', year_part)
        if base_year:
            year_variants.append(base_year.group(1))
        
        occurrences = []
        seen = set()
        
        for yv in year_variants:
            yve = re.escape(yv)
            
            # Inline with (): Author et al. (year)
            for match in re.finditer(ae + r'\s*\(' + yve + r'\)', body):
                pos = (match.start(), match.end())
                if pos not in seen:
                    seen.add(pos); occurrences.append(pos)
            
            # Inline with []: Author et al. [year]
            for match in re.finditer(ae + r'\s*\[' + yve + r'\]', body):
                pos = (match.start(), match.end())
                if pos not in seen:
                    seen.add(pos); occurrences.append(pos)
            
            # Multi-year inline with (): Author et al. (2013, 2014) or (2014, 2013)
            # The year we're looking for appears among a comma-separated list of years
            for match in re.finditer(ae + r'\s*\((\d{4}[a-z]?(?:,\s*\d{4}[a-z]?)+)\)', body):
                years_str = match.group(1)
                years_in_cite = [y.strip() for y in years_str.split(',')]
                if yv in years_in_cite:
                    pos = (match.start(), match.end())
                    if pos not in seen:
                        seen.add(pos); occurrences.append(pos)
            
            # Multi-year inline with []: Author et al. [2013, 2014]
            for match in re.finditer(ae + r'\s*\[(\d{4}[a-z]?(?:,\s*\d{4}[a-z]?)+)\]', body):
                years_str = match.group(1)
                years_in_cite = [y.strip() for y in years_str.split(',')]
                if yv in years_in_cite:
                    pos = (match.start(), match.end())
                    if pos not in seen:
                        seen.add(pos); occurrences.append(pos)
            
            # Parenthetical: (Author et al., year) inside parens
            pat = re.compile(re.escape(author_part) + r',?\s*' + yve)
            for match in pat.finditer(body):
                pos = (match.start(), match.end())
                if pos in seen:
                    continue
                # Walk back to check if inside parens
                for j in range(match.start() - 1, max(match.start() - 200, -1), -1):
                    if j < 0:
                        break
                    if body[j] == '(':
                        seen.add(pos); occurrences.append(pos); break
                    if body[j] == ')':
                        break
        
        return occurrences
    
    # For numeric [N]: match [N] or [N, M, ...] or [N; M; ...]
    m = re.match(r'^\[(\d+)\]$', cite_key)
    if m:
        num = m.group(1)
        pat = re.compile(r'\[(?:\d+[,;]\s*)*\b' + re.escape(num) + r'\b(?:[,;]\s*\d+)*\]')
        return [(match.start(), match.end()) for match in pat.finditer(body)]
    
    # For (number): match (N) — but be careful not to match equation refs
    m = re.match(r'^\((\d+)\)$', cite_key)
    if m:
        num = m.group(1)
        # Only match if preceded by text that looks like a citation context
        pat = re.compile(r'\((?:\d+,\s*)*\b' + re.escape(num) + r'\b(?:,\s*\d+)*\)')
        return [(match.start(), match.end()) for match in pat.finditer(body)]
    
    # For alpha tags [TAG]: match exact tag
    m = re.match(r'^\[.+\]$', cite_key)
    if m:
        pat = re.compile(re.escape(cite_key))
        return [(match.start(), match.end()) for match in pat.finditer(body)]
    
    return []


# ============================================================
# STEP 5: EXTRACT SENTENCE AROUND CITATION
# ============================================================

def _is_sentence_boundary(body: str, pos: int, direction: str) -> bool:
    """
    Check if position `pos` is a real sentence boundary.
    `direction` is 'backward' (looking left for sentence start) or
    'forward' (looking right for sentence end).

    Delegates to the shared sentence_utils module for comprehensive
    non-boundary detection (abbreviations, dotted identifiers, etc.).
    """
    try:
        from .sentence_utils import is_sentence_boundary
    except ImportError:
        from sentence_utils import is_sentence_boundary
    return is_sentence_boundary(body, pos, direction)


def _find_sentence_start(body: str, pos: int, boundary: int) -> int:
    """Find the start of the sentence containing `pos`, not going before `boundary`."""
    ss = pos
    while ss > boundary:
        if _is_sentence_boundary(body, ss, 'backward'):
            break
        ss -= 1
    return ss


def _find_sentence_end(body: str, pos: int, boundary: int) -> int:
    """Find the end of the sentence containing `pos`, not going past `boundary`."""
    se = pos
    while se < boundary:
        if _is_sentence_boundary(body, se, 'forward'):
            se += 1  # include the punctuation
            break
        se += 1
    return se


def _find_section_bounds(body: str, pos: int) -> tuple:
    """
    Find the (start, end) character offsets of the section/subsection/subsubsection
    that contains `pos`. Sections are delimited by any markdown header (#{1,6}).
    """
    # Find all headers (any level: #, ##, ###, ####, etc.)
    headers = list(re.finditer(r'^#{1,6}\s+.+$', body, re.MULTILINE))
    
    sec_start = 0
    sec_end = len(body)
    
    for i, h in enumerate(headers):
        h_end = h.end()
        next_start = headers[i + 1].start() if i + 1 < len(headers) else len(body)
        if h_end <= pos < next_start:
            sec_start = h_end
            sec_end = next_start
            break
    else:
        # pos is before the first header
        if headers:
            if pos < headers[0].start():
                sec_start = 0
                sec_end = headers[0].start()
    
    return (sec_start, sec_end)


def extract_sentence_at(body: str, occ_start: int, occ_end: int) -> str:
    """Extract the sentence containing the citation at occ_start..occ_end."""
    ss = occ_start
    while ss > 0:
        if _is_sentence_boundary(body, ss, 'backward'):
            break
        ss -= 1

    se = occ_end
    while se < len(body):
        if _is_sentence_boundary(body, se, 'forward'):
            se += 1; break
        se += 1

    sent = body[ss:se].strip()
    return re.sub(r'\s+', ' ', sent).strip()


def extract_3_sentence_context(body: str, occ_start: int, occ_end: int) -> str:
    """
    Extract a 3-sentence context around the citation at occ_start..occ_end.
    
    Normal case: previous_sentence + citation_sentence + next_sentence
    
    If citation sentence is the first sentence of a section/subsection/subsubsection:
        citation_sentence + next_sentence_1 + next_sentence_2
    
    If citation sentence is the last sentence of a section/subsection/subsubsection
    or end of document:
        prev_sentence_2 + prev_sentence_1 + citation_sentence
    """
    # Determine section boundaries (any header level)
    sec_start, sec_end = _find_section_bounds(body, occ_start)
    
    # --- Find citation sentence boundaries ---
    cite_sent_start = _find_sentence_start(body, occ_start, sec_start)
    cite_sent_end = _find_sentence_end(body, occ_end, sec_end)
    
    # --- Try to find previous sentence(s) within same section ---
    prev_sentences = []  # list of (start, end) going backwards
    cursor = cite_sent_start
    for _ in range(2):
        # Skip whitespace backwards
        p = cursor
        while p > sec_start and body[p - 1] in ' \t\n\r':
            p -= 1
        if p <= sec_start:
            break
        ps_end = p
        ps_start = _find_sentence_start(body, p - 1, sec_start)
        text = body[ps_start:ps_end].strip()
        if not text:
            break
        prev_sentences.insert(0, (ps_start, ps_end))
        cursor = ps_start
    
    # --- Try to find next sentence(s) within same section ---
    next_sentences = []  # list of (start, end) going forward
    cursor = cite_sent_end
    for _ in range(2):
        # Skip whitespace forwards
        p = cursor
        while p < sec_end and body[p] in ' \t\n\r':
            p += 1
        if p >= sec_end:
            break
        ns_start = p
        ns_end = _find_sentence_end(body, p, sec_end)
        text = body[ns_start:ns_end].strip()
        if not text:
            break
        next_sentences.append((ns_start, ns_end))
        cursor = ns_end
    
    has_prev = len(prev_sentences) >= 1
    has_next = len(next_sentences) >= 1
    
    # --- Assemble the 3-sentence window ---
    if has_prev and has_next:
        # Normal: 1 prev + citation + 1 next
        parts_ranges = [prev_sentences[-1], (cite_sent_start, cite_sent_end), next_sentences[0]]
    elif not has_prev:
        # First sentence of section: citation + up to 2 next
        parts_ranges = [(cite_sent_start, cite_sent_end)] + next_sentences[:2]
    elif not has_next:
        # Last sentence of section: up to 2 prev + citation
        parts_ranges = prev_sentences[-2:] + [(cite_sent_start, cite_sent_end)]
    else:
        parts_ranges = [(cite_sent_start, cite_sent_end)]
    
    # Build final text from the ranges
    parts = []
    for s, e in parts_ranges:
        t = body[s:e].strip()
        t = re.sub(r'\s+', ' ', t).strip()
        if t:
            parts.append(t)
    
    return ' '.join(parts)


# ============================================================
# STEP 6: MAIN ENTRY POINT
# ============================================================

def extract_citation_contexts(file_path: str, exclude_appendix: bool = False) -> list:
    """
    Main function: extract references with citation contexts.
    
    Returns list of dicts:
    [
        {
            "target": "b0",
            "title": "Paper title",
            "year": 2022,
            "cite": "Author et al. (2022)",
            "contexts": [
                {"section": "Introduction", "context": "...sentence..."},
                ...
            ]
        },
        ...
    ]
    """
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        text = f.read()
    
    # 1. Extract references using the proven extract_titles.py
    refs = extract_references(file_path)
    
    # 2. Get raw reference entries for cite key extraction
    ref_section_text = extract_reference_section(text)
    raw_refs = split_references(ref_section_text)
    
    # 3. Get body text
    ref_start, ref_end = find_reference_section_bounds(text)
    body = get_body_text(text, ref_start, ref_end, exclude_appendix)
    
    # 3b. Check for alpha-tag / numeric mismatch (Nougat conversion issue)
    # When references use [DKS17]-style tags but body has [5]-style numeric cites,
    # the mapping is lost — skip the entire file.
    if has_alpha_tag_numeric_mismatch(raw_refs, body):
        return []
    
    # 4. Detect citation format
    cite_format = detect_citation_format(body)
    
    # 5. Parse main sections
    sections = parse_main_sections(body)
    
    # 6. For each reference: extract cite key, find contexts
    results = []
    for i, ref in enumerate(refs):
        raw = raw_refs[i] if i < len(raw_refs) else ""
        
        # Extract cite key from raw reference
        cite_keys = extract_cite_key(raw)
        cite_display = cite_keys[0] if cite_keys else ""
        
        # Find all occurrences of any cite key in body
        all_occurrences = []
        for ck in cite_keys:
            occs = find_cite_occurrences(body, ck, cite_format)
            all_occurrences.extend(occs)
        
        # Extract sentence contexts
        contexts = []
        seen = set()
        for occ_start, occ_end in all_occurrences:
            # Find section
            section_name = ""
            for header, sec_start, sec_end in sections:
                if sec_start <= occ_start < sec_end:
                    section_name = header
                    break
            
            sentence = extract_3_sentence_context(body, occ_start, occ_end)
            
            # Filter junk
            if not sentence or len(sentence) <= 10:
                continue
            if sentence in seen:
                continue
            if '\\begin{table}' in sentence or '\\begin{tabular}' in sentence:
                continue
            if sentence.count('\\') / max(len(sentence), 1) > 0.15 and len(sentence) > 50:
                continue
            
            seen.add(sentence)
            contexts.append({"section": section_name, "context": sentence})
        
        results.append({
            "target": ref['target'],
            "title": ref['title'],
            "year": ref['year'],
            "cite": cite_display,
            "contexts": contexts,
        })
    
    return results
