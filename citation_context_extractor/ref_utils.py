"""
Reference extraction utilities (from extract_titles.py)

Standalone reference extraction logic — no external dependencies outside stdlib.
"""

import re
import json


def extract_reference_section(text: str) -> str:
    """Extract the reference/bibliography section from a paper."""
    patterns = [
        r'\n##\s*References?\s*\n',
        r'\n##\s*Bibliography\s*\n',
        r'\n##\s*REFERENCES?\s*\n',
        r'\n\*\*References?\*\*\s*\n',
        r'\nReferences?\s*\n\s*\n',
        r'\n#\s*References?\s*\n',
    ]

    for pat in patterns:
        match = re.search(pat, text)
        if match:
            ref_text = text[match.end():]
            end_patterns = [
                r'\n##\s+Appendix',
                r'\n##\s+[A-Z]',
                r'\n#\s+[A-Z]',
            ]
            for end_pat in end_patterns:
                end_match = re.search(end_pat, ref_text)
                if end_match:
                    ref_text = ref_text[:end_match.start()]
            return ref_text

    return text


def split_references(ref_section: str) -> list:
    """Split the reference section into individual references."""
    # Strategy 1: Lines starting with "* " (Nougat bullet-style)
    bullet_refs = re.split(r'\n\* ', ref_section)
    if len(bullet_refs) > 3:
        # Post-process: some refs may lack a leading * and get merged with
        # the previous ref. Split each chunk on double-newlines to recover them.
        final_refs = []
        for r in bullet_refs:
            r = r.strip()
            if not r:
                continue
            sub_parts = re.split(r'\n\s*\n', r)
            if len(sub_parts) > 1:
                for sp in sub_parts:
                    sp = sp.strip()
                    if sp and len(sp) > 20:
                        final_refs.append(sp)
            else:
                final_refs.append(r)
        # Second post-process: split any remaining large chunks that contain
        # inline [number] references (no newlines between them)
        final_refs2 = []
        for r in final_refs:
            inline_parts = re.split(r'\s*\[(\d+)\]\s*', r)
            if len(inline_parts) > 5:  # at least 3 inline refs
                for i in range(1, len(inline_parts), 2):
                    if i + 1 < len(inline_parts):
                        final_refs2.append(f"[{inline_parts[i]}] {inline_parts[i+1].strip()}")
                # Also keep the preamble if it looks like a ref
                if inline_parts[0].strip() and len(inline_parts[0].strip()) > 20:
                    final_refs2.append(inline_parts[0].strip())
            else:
                final_refs2.append(r)
        return final_refs2

    # Strategy 2: Lines starting with [number]
    numbered = re.split(r'\n\s*\[(\d+)\]\s*', ref_section)
    if len(numbered) > 3:
        refs = []
        for i in range(1, len(numbered), 2):
            if i + 1 < len(numbered):
                refs.append(f"[{numbered[i]}] {numbered[i+1].strip()}")
        if refs:
            return refs

    # Strategy 2b: Inline [number] references (no newlines between them)
    # e.g. "[8] Ref text (2023) [9] Ref text (2022) [10] Ref text..."
    inline_numbered = re.split(r'\s*\[(\d+)\]\s*', ref_section)
    if len(inline_numbered) > 5:  # at least 3 refs (each produces 2 parts)
        refs = []
        for i in range(1, len(inline_numbered), 2):
            if i + 1 < len(inline_numbered):
                refs.append(f"[{inline_numbered[i]}] {inline_numbered[i+1].strip()}")
        if refs:
            return refs

    # Strategy 3: Double newline separated
    double_nl = ref_section.split('\n\n')
    if len(double_nl) > 3:
        return [r.strip().replace('\n', ' ') for r in double_nl if r.strip()]

    # Strategy 4: Each line is a reference
    lines = ref_section.strip().split('\n')
    return [l.strip() for l in lines if l.strip() and len(l.strip()) > 20]


def _is_author_segment(text: str) -> bool:
    """Check if a text segment looks like author names rather than a title."""
    text = text.strip()
    if not text:
        return True
    if len(text) < 5:
        return True

    initial_count = len(re.findall(r'\b[A-Z]\.', text))
    word_count = len(text.split())

    if word_count > 0 and initial_count / word_count > 0.25:
        return True

    if re.match(
        r'^[A-Z][a-z]+(?:\s+[A-Z]\.?)+'
        r'(?:\s*(?:,|and|&)\s*[A-Z][a-z]+(?:\s+[A-Z]\.?)+)*$',
        text
    ):
        return True

    if re.match(
        r'^(?:[A-Z][a-z]+\s+)+(?:[A-Z]\.\s+)*[A-Z][a-z]+'
        r'(?:\s+(?:and|&)\s+(?:[A-Z][a-z]+\s+)+(?:[A-Z]\.\s+)*[A-Z][a-z]+)*$',
        text
    ):
        return True

    filler_words = {
        'and', '&', 'de', 'du', 'van', 'von', 'dos', 'del',
        'di', 'da', 'der', 'den', 'le', 'la', 'el',
    }
    words = text.split()
    if word_count >= 3:
        cap_or_filler = sum(
            1 for w in words
            if (w[0].isupper() if w else False) or w.lower().rstrip(',') in filler_words
        )
        ratio = cap_or_filler / word_count
        has_connector = ('and' in [w.lower().rstrip(',') for w in words]) or ',' in text
        if ratio > 0.85 and has_connector:
            # Extra check: author lists have short comma-separated segments (names)
            # while titles have longer segments. Split on comma and check avg length.
            if ',' in text:
                segments = [s.strip() for s in text.split(',') if s.strip()]
                avg_seg_words = sum(len(s.split()) for s in segments) / max(len(segments), 1)
                # Author name segments are typically 1-4 words (e.g. "Hideko Kawakubo")
                # Title segments tend to be longer (e.g. "A Modularized Multimodal Foundation Model Across Text")
                if avg_seg_words <= 4:
                    return True
            else:
                # No commas but has 'and' — shorter text is more likely author names
                if word_count <= 6:
                    return True

    return False


def _extract_title_after_authors(text: str) -> str:
    """
    For references where full author names precede the title separated by periods,
    extract the title by skipping author-looking segments.
    """
    # Pre-check: colon-separated format "LastName, X.: Title. In: Venue"
    # e.g. "Ahn, M., ..., Zeng, A.: Do as i can and not as i say: Grounding language..."
    # e.g. "..., et al.: Flamingo: a visual language model..."
    # The author block ends with "Initial.:" or "al.:" and the title follows
    colon_m = re.search(r'(?:[A-Z]|et al)\.?:\s+(.+)', text)
    if colon_m:
        after_colon = colon_m.group(1).strip()
        # Extract title: everything up to ". In:" or ". In " or ". arXiv" or ". Venue"
        # where venue starts with a capital and looks like a journal/conference name
        title_m = re.match(r'(.+?)(?:\.\s+In[:\s]|\.\s+arXiv|\.\s+[A-Z][a-z])', after_colon)
        if title_m:
            candidate = title_m.group(1).strip()
            if len(candidate) > 5 and not _is_author_segment(candidate):
                return candidate
        # If no venue separator found, try up to first period
        title_m = re.match(r'(.+?)\.', after_colon)
        if title_m:
            candidate = title_m.group(1).strip()
            if len(candidate) > 5 and not _is_author_segment(candidate):
                return candidate
        # Fallback: no period at all — title ends at trailing (year)
        # e.g. "Video pretraining (ypt): Learning to act by watching unlabeled online videos (2022)"
        title_m = re.match(r'(.+?)\s*\(\d{4}\)\s*$', after_colon)
        if title_m:
            candidate = title_m.group(1).strip()
            if len(candidate) > 5 and not _is_author_segment(candidate):
                return candidate
        # Last resort: no period, no (year), no venue — title is the entire text after colon
        # e.g. "Less is more: Clipbert for video-and-language learning via sparse sampling"
        if len(after_colon) > 10 and not _is_author_segment(after_colon):
            return after_colon.rstrip('.')

    parts = re.split(r'(?<![A-Z])\.\s+', text, maxsplit=10)

    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        if _is_author_segment(part):
            continue
        # Skip venue/publication parts that aren't titles
        if re.match(r'^_(?:arXiv|Proceedings|Journal|IEEE|ACM|AAAI|International|Conference|Transactions)', part):
            continue
        if re.match(r'^(?:In\s+|arXiv|Proceedings|Journal|Conference|Transactions|Springer|MIT Press|ACM|IEEE|PMLR|External Links|Cited by|URL\s)', part):
            continue

        title_text = part.rstrip('.')

        for j in range(i + 1, min(i + 3, len(parts))):
            next_part = parts[j].strip()
            if re.match(r'^In\s+[_A-Z]', next_part):
                break
            if re.match(r'^In\s+Proc', next_part):
                break
            if next_part.startswith('_'):
                break
            if re.match(r'^pages?\s+\d', next_part, re.I):
                break
            if re.match(r'^\d{4}', next_part):
                break
            if re.match(r'^(?:Springer|MIT Press|ACM|IEEE|Cambridge|Oxford|Elsevier)', next_part):
                break
            if re.match(r'^(?:Master|PhD|Doctoral)', next_part):
                break
            if re.match(r'^(?:Proceedings|Journal|Conference|Trans)', next_part):
                break
            if re.match(r'^arXiv', next_part):
                break
            if re.match(r'^(?:External Links|Cited by)', next_part):
                break
            title_text += '. ' + next_part

        return title_text

    # Fallback: when period-based splitting fails (e.g. due to multi-letter initials
    # like "O. D." preventing splits), find the last sentence before an italic venue _Venue_
    # The title starts after the last ". CapitalWord(3+ letters)" boundary
    venue_m = re.search(r'\.?\s+(?:In\s+)?_', text)
    if venue_m:
        before_venue = text[:venue_m.start()]
        matches = list(re.finditer(r'\.\s+([A-Z][a-z]{2,})', before_venue))
        if matches:
            last = matches[-1]
            candidate = before_venue[last.start() + 2:].strip()
            if len(candidate) > 5 and not _is_author_segment(candidate):
                return candidate

    # Fallback: italic title _Title_
    m = re.search(r'_([^_]{10,})_', text)
    if m:
        return m.group(1).strip()

    return ""


def _clean_title(title: str) -> str:
    """Clean and normalize an extracted title."""
    title = title.rstrip('.')
    title = title.strip()
    title = title.replace('_', '')
    title = title.replace('**', '')
    title = re.sub(r',?\s*Cited by:.*$', '', title)
    title = re.sub(r'\\\(.*?\\\)', '', title)
    title = re.sub(r'\{\\text\{([^}]*)\}\}', r'\1', title)
    title = re.sub(r'\$[^$]*\$', '', title)
    title = re.sub(r'\s+', ' ', title)
    title = re.sub(r'^\d+\.\s*', '', title)
    return title.strip()


def extract_year(ref: str) -> int:
    """Extract the publication year from a reference string."""
    ref_clean = re.sub(r'^[\*\-•]\s*', '', ref.strip())

    # 1) Year in brackets: [2013] or [2022a]
    m = re.search(r'\[(\d{4})[a-z]?\]', ref_clean)
    if m:
        return int(m.group(1))

    # 2) Year in parentheses: (2017) or (2022a)
    m = re.search(r'\((\d{4})[a-z]?\)', ref_clean)
    if m:
        return int(m.group(1))

    # 3) Standalone year followed by period: 2001.
    m = re.search(r'(?:^|\s)(\d{4})[a-z]?\.', ref_clean)
    if m:
        return int(m.group(1))

    # 4) Year at end of reference: , 2013. or , 2013
    m = re.search(r',\s*(\d{4})[a-z]?\s*\.?\s*$', ref_clean)
    if m:
        return int(m.group(1))

    # 5) Any 4-digit year (last one found, usually the publication year)
    years = re.findall(r'\b((?:19|20)\d{2})\b', ref_clean)
    if years:
        return int(years[-1])

    return None


def extract_title(ref: str) -> str:
    """Extract the title from a single reference string."""
    ref = ref.strip()
    if not ref or len(ref) < 15:
        return ""

    ref = re.sub(r'^[\*\-•]\s*', '', ref)

    title = ""

    # --- STRATEGY A: Year-period-title pattern ---
    # "...2001. Random forests. _Machine Learning_..."
    m = re.search(
        r'(?:^|\s)(\d{4}[a-z]?)\)?\.\s+'
        r'([A-Z][^.]*?\.)',
        ref
    )
    if m:
        candidate = m.group(2).strip()
        if (len(candidate) > 5
                and not re.match(r'^(?:URL|In\s|External|Cited|Springer|MIT Press|ACM|IEEE)', candidate)):
            title = candidate

    # --- STRATEGY B: (year) then title (no author re-list) ---
    # "G. Papandreou, ... (2018)Personlab: person pose..."
    if not title:
        m = re.search(r'\(\d{4}[a-z]?\)\s*([A-Z](?:[^.]|\.(?!\s))+\.)', ref)
        if m:
            candidate = m.group(1).strip().rstrip('.')
            if (len(candidate) > 10
                    and not re.match(r'^[A-Z][a-z]+,\s+[A-Z]\.', candidate)
                    and not _is_author_segment(candidate)):
                title = candidate

    # --- STRATEGY B variant: no space between ) and title ---
    # Handles titles starting with digits too, e.g. "(2023)3D gaussian splatting..."
    # Also handles periods inside titles, e.g. "Vita-1.5: towards..."
    # No space after ) is a strong signal the next text is the title, not author names
    if not title:
        m = re.search(r'\(\d{4}[a-z]?\)([A-Za-z0-9](?:[^.]|\.(?!\s))+\.)', ref)
        if m:
            candidate = m.group(1).strip().rstrip('.')
            if (len(candidate) > 10
                    and not re.match(r'^[A-Z][a-z]+,\s+[A-Z]\.', candidate)
                    and not _is_author_segment(candidate)):
                title = candidate

    # --- STRATEGY B2: (year) then full author names then title ---
    # "Kawakubo et al. (2016) Hideko Kawakubo, ... Computationally efficient..."
    if not title:
        m = re.search(r'\(\d{4}[a-z]?\)\s+', ref)
        if m:
            rest = ref[m.end():]
            candidate = _extract_title_after_authors(rest)
            if candidate and len(candidate) > 5:
                title = candidate

    # --- STRATEGY C: Numbered references [N] ---
    # "[2] A. A. Efros and T. K. Leung. Texture synthesis..."
    if not title:
        m = re.match(r'\[\d+\]\s*', ref)
        if m:
            rest = ref[m.end():]
            title = _extract_title_after_authors(rest)

    # --- STRATEGY C2: Author et al. [year] FullNames. Title. ---
    # "Barranquero et al. [2013] Jose Barranquero, ... On the study of..."
    if not title:
        m = re.search(r'\[\d{4}[a-z]?\]\s*', ref)
        if m:
            rest = ref[m.end():]
            candidate = _extract_title_after_authors(rest)
            if candidate and len(candidate) > 5:
                title = candidate
            if not title:
                m2 = re.search(r'_([^_]{10,})_', rest)
                if m2:
                    title = m2.group(1).strip()

    # --- STRATEGY D: [AuthorYear] format ---
    # "[Baumann2014] Ringo Baumann. Context-free..."
    if not title:
        m = re.match(r'\[[A-Za-z\s]+\d{4}[a-z]?\]\s*', ref)
        if m:
            rest = ref[m.end():]
            title = _extract_title_after_authors(rest)
            if not title:
                m2 = re.search(r'_([^_]{10,})_', rest)
                if m2:
                    title = m2.group(1).strip()

    # --- STRATEGY E: [Author et al.Year] or [Author and AuthorYear] ---
    if not title:
        m = re.match(r'\[[^\]]*\d{4}[a-z]?\]\s*', ref)
        if m:
            rest = ref[m.end():]
            m2 = re.search(r'(?:^|\s)(\d{4}[a-z]?)\)?\.\s+([A-Z].*?\.)', rest)
            if m2:
                candidate = m2.group(2).strip()
                if len(candidate) > 5:
                    title = candidate

    # --- STRATEGY E2: General bracket tags [ShortTag] with 2-digit years ---
    # e.g. "[GDDM14] Ross Girshick, ... Title. _Venue_"
    # e.g. "[Hus18] Ferenc Huszar. Title. _Venue_"
    # e.g. "[DJV\({}^{+}\)13] Jeff Donahue, ... Title. _Venue_"
    # Also handles (number) prefix: "(1) Authors. Title. _Venue_"
    if not title:
        m = re.match(r'\[[^\]]+\]\s*', ref)
        if not m:
            m = re.match(r'\(\d+\)\s*', ref)
        if m:
            rest = ref[m.end():]
            # Try italic title first — more reliable for bracket-tag formats
            # where the title may be in , _Title_, format
            m2 = re.search(r',\s*_([^_]{10,})_', rest)
            if m2:
                title = m2.group(1).strip()
            if not title:
                candidate = _extract_title_after_authors(rest)
                if candidate and len(candidate) > 5:
                    title = candidate
            if not title:
                m2 = re.search(r'_([^_]{10,})_', rest)
                if m2:
                    title = m2.group(1).strip()

    # --- STRATEGY F: Title before italic venue ---
    if not title:
        m = re.search(r'\d{4}[a-z]?\)?\.\s+(.*?)\s*_[A-Z]', ref)
        if m and len(m.group(1).strip()) > 5:
            title = m.group(1).strip()

    # --- STRATEGY G: Title before "In" keyword ---
    if not title:
        m = re.search(r'\d{4}[a-z]?\)?\.\s+(.*?)\.\s+In\s+', ref)
        if m and len(m.group(1).strip()) > 5:
            title = m.group(1).strip()

    # --- STRATEGY H: Italic title _Title_ after bracket tag and authors ---
    # e.g. "[DKS19] Ilias Diakonikolas, ..., _Efficient algorithms and lower bounds_,..."
    # Also handles general cases where title is in italics anywhere in the ref
    if not title:
        m = re.search(r',\s*_([^_]{10,})_', ref)
        if m:
            title = m.group(1).strip()

    # --- STRATEGY I: Title. In _Venue_ or Title. In Proceedings ---
    # For refs where Nougat lost the author/year prefix, leaving just:
    # "Title. In _Venue_, year."
    if not title:
        m = re.match(r'^(.+?)\.\s+In\s+[_A-Z]', ref)
        if m:
            candidate = m.group(1).strip()
            if len(candidate) > 10 and not _is_author_segment(candidate):
                title = candidate

    # Clean up
    if title:
        title = _clean_title(title)
        title = re.sub(r'\s*arXiv preprint.*$', '', title)
        title = re.sub(r'\s*,\s*\d{4}[a-z]?\.?\s*$', '', title)
        title = re.sub(r'\s*\(\d{4}[a-z]?\)\s*$', '', title)
        if title.lower() in ('springer', 'mit press', 'acm', 'ieee', 'elsevier', 'cambridge', 'pmlr'):
            title = ""

    return title


def extract_references(file_path: str) -> list:
    """
    Main function: extract titles and years from all references in a .md file.

    Returns:
        List of dicts: [{'target': 'b0', 'title': '...', 'year': 2017}, ...]
    """
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        text = f.read()

    ref_section = extract_reference_section(text)
    refs = split_references(ref_section)

    results = []
    idx = 0

    for ref in refs:
        ref_clean = ref.strip().replace('\n', ' ')
        if len(ref_clean) < 20:
            continue

        title = extract_title(ref_clean)
        year = extract_year(ref_clean)

        if not title:
            # Catch-all: no strategy could extract a title, but this is still
            # a reference entry. Use the raw text (stripped of prefix) as title.
            fallback = re.sub(r'^[\*\-•]\s*', '', ref_clean)
            fallback = re.sub(r'^\[\d+\]\s*', '', fallback)       # [number]
            fallback = re.sub(r'^\[[^\]]+\]\s*', '', fallback)    # [tag]
            fallback = re.sub(r'^\(\d+\)\s*', '', fallback)       # (number)
            fallback = _clean_title(fallback)
            # Truncate to something reasonable if very long
            if len(fallback) > 200:
                fallback = fallback[:200].rsplit(' ', 1)[0] + '...'
            title = fallback if fallback else ref_clean[:200]

        results.append({
            'target': f'b{idx}',
            'title': title,
            'year': year,
        })
        idx += 1

    return results
