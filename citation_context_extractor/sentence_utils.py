"""
Shared sentence boundary detection for citation context extraction.

Used by both the Nougat (ctx_utils.py) and GROBID (grobid_utils.py)
extraction paths to ensure consistent sentence splitting.
"""

import re


# ============================================================
# NON-BOUNDARY DETECTION
# ============================================================

# --- Rule 1: Known abbreviations ---
# Single-word abbreviations commonly found in academic papers.
# These end with a period but are NOT sentence endings.
_KNOWN_ABBREVS = {
    # Academic / citation
    'al', 'et',
    # Titles
    'Dr', 'Prof', 'Mr', 'Mrs', 'Ms', 'Jr', 'Sr', 'St',
    # Latin
    'ibid', 'viz', 'ca', 'approx', 'resp',
    # Units / references
    'Fig', 'Figs', 'Eq', 'Eqs', 'Sec', 'Secs', 'Ref', 'Refs',
    'Tab', 'App', 'Vol', 'No', 'Nos', 'pp', 'Chap', 'Dept', 'Univ',
    'Prop', 'Thm', 'Lem', 'Cor', 'Def', 'Ex',
    # Corporate
    'Inc', 'Ltd', 'Corp', 'Co',
    # Other
    'ed', 'eds', 'trans', 'rev', 'pt',
}

# --- Rule 2: Multi-dot abbreviations ---
# Patterns like: i.e., e.g., w.r.t., s.t., Ph.D., M.S., U.S., M.I.T.
# Match: letter(s) DOT letter(s) DOT [letter(s) DOT]... at the end
_MULTI_DOT_ABBREV = re.compile(
    r'(?:[A-Za-z]{1,4}\.){2,}$'  # e.g. "i.e." "Ph.D." "U.S." "M.I.T." "w.r.t."
)

# --- Rule 3: Dotted identifiers (no space around the dot) ---
# Patterns like: model.train, script.sh, example.com, ref.bib, df.dropna
# The dot has a word character on BOTH sides with no whitespace.
# Also covers file extensions and domain names.

# --- Rule 4: Numeric contexts ---
# Decimal numbers: 3.14, 0.05
# IP addresses: 192.168.1.1
# Version numbers: v2.1.3
# Already partially handled, but we make it more robust.

# --- Rule 5: Path-like patterns ---
# ./ ../ which appear in academic text when discussing file paths


def _is_not_sentence_boundary(text, dot_pos):
    """
    Given the full text and the position of a period/dot, return True if
    this dot is NOT a sentence boundary.

    This function checks all non-boundary rules. If any rule matches,
    the dot should NOT cause a sentence split.
    """
    before_char = text[dot_pos - 1] if dot_pos > 0 else ''
    after_raw = text[dot_pos + 1:] if dot_pos + 1 < len(text) else ''
    after_char = after_raw[0] if after_raw else ''

    # ----- Rule 3: Dotted identifier (word.word with no space) -----
    # model.train, script.sh, example.com, ref.bib, df.dropna
    if before_char.isalnum() and after_char.isalnum():
        # Dot is between two word characters with no space — not a boundary
        return True

    # ----- Rule 4a: Decimal / IP / version (digit.digit) -----
    if before_char.isdigit() and after_char.isdigit():
        return True

    # ----- Rule 5: Path patterns ./ or ../ -----
    if after_char == '/' or after_char == '.':
        return True

    # ----- Rule 1: Known abbreviation -----
    # Look backward from dot_pos to find the word before the dot
    word_end = dot_pos
    word_start = dot_pos - 1
    while word_start >= 0 and text[word_start].isalpha():
        word_start -= 1
    word_start += 1  # first alpha char
    word_before = text[word_start:word_end]

    if word_before in _KNOWN_ABBREVS:
        return True

    # "et al." — check for "et al" as two words
    if word_before == 'al' and word_start >= 4:
        pre = text[max(0, word_start - 4):word_start].rstrip()
        if pre.endswith('et'):
            return True

    # ----- Rule 2: Multi-dot abbreviation (internal dots only) -----
    # Patterns like "Ph.D." "i.e." "U.S." "M.I.T." "w.r.t."
    # Only suppress the split for INTERNAL dots (followed by a letter).
    # The terminal dot (followed by space) should still allow a sentence split.
    lookback = text[max(0, dot_pos - 15):dot_pos + 1]
    if _MULTI_DOT_ABBREV.search(lookback):
        # Check if this is an internal dot (next char is a letter = more abbrev)
        if after_char.isalpha():
            return True
        # Terminal dot: don't suppress — let the boundary check decide

    # ----- Rule 4b: Version-like patterns (v2.1, 2.1.3) -----
    # Already covered by digit.digit rule above, but also handle
    # cases like v2.1 where before_char is digit and we already caught it.
    # Check if we're inside a version string: look for preceding digit-dot pattern
    if before_char.isdigit():
        # Walk backward to see if there's a version-like pattern
        j = dot_pos - 1
        while j >= 0 and (text[j].isdigit() or text[j] == '.'):
            j -= 1
        # If we hit a 'v' or another digit-dot sequence, it's a version
        if j >= 0 and text[j] in 'vV':
            return True

    # ----- Rule: Single uppercase letter before dot -----
    # Catches initials like "J." "A." in names, and leftover single-letter abbrevs.
    # BUT: don't suppress if this is the terminal dot of a multi-dot abbreviation
    # like "M.I.T." — the internal dots are already handled by Rule 2 above,
    # and the terminal dot should allow a sentence split.
    if len(word_before) == 1 and word_before.isupper():
        # Check if this is part of a multi-dot abbreviation
        lookback = text[max(0, dot_pos - 15):dot_pos + 1]
        if _MULTI_DOT_ABBREV.search(lookback):
            # Terminal dot of multi-dot abbrev — let the boundary check decide
            return False
        return True

    return False


# ============================================================
# GROBID SENTENCE SPLITTER
# ============================================================

def split_sentences(text):
    """
    Split text into sentences for GROBID-extracted paragraphs.

    Uses comprehensive non-boundary detection to avoid splitting on
    abbreviations, decimal numbers, dotted identifiers, file paths, etc.

    A period is a sentence boundary only if:
    1. It passes all non-boundary checks (not an abbreviation, etc.)
    2. It's not inside parentheses
    3. It's followed by whitespace then an uppercase letter, opening bracket,
       or end of text

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
            after = text[i + 1:min(len(text), i + 10)].lstrip()

            # Check all non-boundary rules
            if ch == '.' and _is_not_sentence_boundary(text, i):
                i += 1
                continue

            # Not a boundary if inside parentheses (citation context)
            depth = 0
            for j in range(i, max(i - 200, -1), -1):
                if text[j] == ')':
                    depth += 1
                elif text[j] == '(':
                    depth -= 1
                    if depth < 0:
                        break
            if depth < 0:
                i += 1
                continue

            # It's a boundary if followed by uppercase, opening bracket, or end of text
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
# NOUGAT SENTENCE BOUNDARY CHECKER
# ============================================================

def is_sentence_boundary(body, pos, direction):
    """
    Check if position `pos` in `body` is a real sentence boundary.

    `direction` is 'backward' (looking left for sentence start) or
    'forward' (looking right for sentence end).

    This replaces the original _is_sentence_boundary in ctx_utils.py
    with comprehensive non-boundary detection.
    """
    if direction == 'backward':
        ch = body[pos - 1] if pos > 0 else ''
        if ch in '.!?':
            # Check non-boundary rules for the dot at pos-1
            if ch == '.' and _is_not_sentence_boundary(body, pos - 1):
                return False
            after = body[pos:min(len(body), pos + 3)]
            aft = after.lstrip()
            if aft and (aft[0].isupper() or aft[0] in '(['):
                return True
            return False
        if ch == '\n' and pos >= 2 and body[pos - 2] == '\n':
            return True
        return False
    else:  # forward
        ch = body[pos] if pos < len(body) else ''
        if ch in '.!?':
            # Check non-boundary rules for the dot at pos
            if ch == '.' and _is_not_sentence_boundary(body, pos):
                return False
            return True
        if ch == '\n' and pos + 1 < len(body) and body[pos + 1] == '\n':
            return True
        return False