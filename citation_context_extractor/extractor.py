"""
Extractor wrapper — uses the internal ref_utils, ctx_utils, and grobid_utils
modules that are all bundled inside this package.

This package is fully self-contained. No external preprocessing scripts needed.
"""

from .ref_utils import (
    extract_references as _extract_references_raw,
    extract_reference_section,
    split_references,
)
from .ctx_utils import (
    extract_citation_contexts as _extract_citation_contexts_raw,
    find_reference_section_bounds,
    get_body_text,
    has_alpha_tag_numeric_mismatch,
)
from .grobid_utils import (
    extract_citation_contexts_from_grobid as _extract_grobid_raw,
)


# ----------------------------------------------------------------
# Helper: filter out non-reference entries (year=None)
# ----------------------------------------------------------------
def _filter_null_years(results: list) -> list:
    """Remove entries where year could not be determined, then renumber targets.

    These are typically figures, captions, or other non-reference content
    that Nougat misplaced into the reference section.

    After removing invalid entries, the remaining ones are renumbered
    sequentially: b0, b1, b2, ... so there are no gaps.
    """
    filtered = [r for r in results if r.get('year') is not None]
    for i, r in enumerate(filtered):
        r['target'] = f'b{i}'
    return filtered


# ----------------------------------------------------------------
# Public API — thin wrappers around the internal functions
# ----------------------------------------------------------------

def extract_references(file_path: str) -> list:
    """Extract reference titles and years from a .md file.

    Returns list of dicts: [{'target': 'b0', 'title': '...', 'year': 2017}, ...]

    NOTE: References where the year could not be determined (year=None)
    are filtered out, as they are likely figures, captions, or other
    non-reference content that Nougat misplaced into the reference section.
    """
    return _filter_null_years(_extract_references_raw(file_path))


def extract_citation_contexts(file_path: str, exclude_appendix: bool = False) -> list:
    """Extract references with citation contexts from a .md file.

    Returns list of dicts with 'target', 'title', 'year', 'cite', 'contexts' keys.
    Returns an EMPTY list when the file is skipped (alpha-tag mismatch, etc.).

    NOTE: References where the year could not be determined (year=None)
    are filtered out.
    """
    return _filter_null_years(
        _extract_citation_contexts_raw(file_path, exclude_appendix)
    )


def extract_citation_contexts_grobid(file_path: str, exclude_appendix: bool = False) -> list:
    """Extract references with citation contexts from a GROBID TEI XML file.

    Returns list of dicts with 'target', 'title', 'year', 'cite', 'contexts' keys.

    NOTE: References where the year could not be determined (year=None)
    are filtered out.
    """
    return _filter_null_years(
        _extract_grobid_raw(file_path, exclude_appendix)
    )


def is_alpha_tag_mismatch(file_path: str) -> bool:
    """Check if a nougat file has the alpha-tag / numeric citation mismatch.

    When True, the file should be skipped entirely (no reliable context extraction).
    """
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        text = f.read()

    ref_section_text = extract_reference_section(text)
    raw_refs = split_references(ref_section_text)

    ref_start, ref_end = find_reference_section_bounds(text)
    body = get_body_text(text, ref_start, ref_end, False)

    return has_alpha_tag_numeric_mismatch(raw_refs, body)
