"""GESTIMA - Article Number Fuzzy Matching

Generic normalization — no hardcoded prefix list.
Detects any alphabetic prefix before a numeric article number.

Examples:
- "byn-10101251" → prefix="byn-", base="10101251"
- "kod-0561716" → prefix="kod-", base="0561716"
- "[kod-0561716]" → clean brackets, prefix="kod-", base="0561716"
- "ART-12345" → prefix="ART-", base="12345"
- "90057637-00" → base="90057637", revision="00"
- "D00253480-001" → base="D00253480", revision="001" (drawing number)

Match strategies:
1. Exact match (highest priority)
2. Match without detected prefix
3. Match without revision suffix
4. Match with different prefix (warning)
"""

import re
import logging
from typing import Optional, Tuple, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Generic prefix pattern: alphabetic chars followed by separator before digits
# Matches: "byn-", "kod-", "ART-", "trgcz-", "GELSO_", "XYZ." etc.
# Does NOT match: "D00" (letter + digits = drawing number, not prefix)
_PREFIX_PATTERN = re.compile(
    r"^([a-zA-Z]{2,})"   # 2+ letters (avoids stripping "D" from D00253480)
    r"([-_./\s])"         # separator
)

# Brackets / tags around the whole value: [kod-0561716], (ART-123), #12345
_BRACKETS_PATTERN = re.compile(r"^[\[\](){}#]+|[\[\](){}]+$")

# Revision pattern: -00, -001, -01, -A, -B, etc. at END of string
REVISION_PATTERN = re.compile(r"-([0-9]{2,3}|[A-Z])$")


@dataclass
class NormalizedArticleNumber:
    """Normalized article number with metadata."""
    original: str           # Raw input (e.g., "[kod-0561716]")
    cleaned: str            # After bracket removal (e.g., "kod-0561716")
    normalized: str         # Without detected prefix (e.g., "0561716")
    base: str              # Without prefix AND revision (e.g., "0561716")
    prefix: Optional[str]  # Detected prefix (e.g., "kod-")
    revision: Optional[str] # Detected revision (e.g., "00")


class ArticleNumberMatcher:
    """Generic fuzzy matcher for article numbers — no hardcoded prefixes."""

    @staticmethod
    def normalize(article_number: str) -> NormalizedArticleNumber:
        """Normalize article number — strip brackets, detect prefix, extract revision.

        Works with ANY customer prefix format (no known-prefix list needed).

        Examples:
            "[kod-0561716]" → cleaned="kod-0561716", normalized="0561716", prefix="kod-"
            "byn-10101251" → normalized="10101251", prefix="byn-"
            "90057637-00"  → base="90057637", revision="00"
            "D00253480-001" → base="D00253480", revision="001" (no prefix stripped)
            "0561716"      → no prefix, no revision
        """
        original = article_number.strip()

        # 1. Strip brackets / tags
        cleaned = _BRACKETS_PATTERN.sub("", original).strip()

        prefix = None
        revision = None
        normalized = cleaned

        # 2. Detect generic alphabetic prefix (2+ letters + separator)
        prefix_match = _PREFIX_PATTERN.match(cleaned)
        if prefix_match:
            # Only strip if what follows the prefix starts with a digit
            after_prefix = cleaned[prefix_match.end():]
            if after_prefix and after_prefix[0].isdigit():
                prefix = cleaned[:prefix_match.end()]
                normalized = after_prefix

        # 3. Extract revision suffix (from normalized version)
        rev_match = REVISION_PATTERN.search(normalized)
        if rev_match:
            revision = rev_match.group(1)
            base = normalized[:rev_match.start()]
        else:
            base = normalized

        logger.debug(
            "Normalized '%s' -> cleaned='%s', normalized='%s', "
            "base='%s', prefix='%s', revision='%s'",
            original, cleaned, normalized, base, prefix, revision,
        )

        return NormalizedArticleNumber(
            original=original,
            cleaned=cleaned,
            normalized=normalized,
            base=base,
            prefix=prefix,
            revision=revision,
        )

    @staticmethod
    def generate_variants(article_number: str) -> List[str]:
        """Generate matching variants for fuzzy search.

        Examples:
            "[kod-0561716]"  → ["[kod-0561716]", "kod-0561716", "0561716"]
            "byn-10101251"   → ["byn-10101251", "10101251"]
            "90057637-00"    → ["90057637-00", "90057637"]
            "D00253480-001"  → ["D00253480-001", "D00253480"]

        Returns:
            List of variants ordered by priority (exact first).
        """
        norm = ArticleNumberMatcher.normalize(article_number)
        variants = [
            norm.original,     # Exact match (highest priority)
            norm.cleaned,      # Without brackets
            norm.normalized,   # Without detected prefix
            norm.base,         # Without prefix AND revision
        ]

        # Deduplicate preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for v in variants:
            if v and v not in seen:
                seen.add(v)
                unique.append(v)

        logger.debug("Generated variants for '%s': %s", article_number, unique)
        return unique

    @staticmethod
    def match_type(
        input_article: str,
        db_article: str,
    ) -> Tuple[str, str]:
        """Determine match type and generate warning.

        Returns:
            (match_type, warning_message)

        Match types:
            "exact" - exact match, no warning
            "prefix_stripped" - matched after removing customer prefix
            "revision_ignored" - matched ignoring revision difference
            "fuzzy" - other fuzzy match
        """
        input_norm = ArticleNumberMatcher.normalize(input_article)
        db_norm = ArticleNumberMatcher.normalize(db_article)

        # Exact match
        if input_article == db_article:
            return ("exact", "")

        # Match without customer prefix
        if input_norm.normalized == db_norm.normalized:
            if input_norm.prefix != db_norm.prefix:
                warning = (
                    f"[POZOR] Prefix mismatch: '{input_article}' matched to '{db_article}' "
                    f"(customer prefix differs)"
                )
                return ("prefix_stripped", warning)

        # Match with different revisions
        if input_norm.base == db_norm.base:
            if input_norm.revision != db_norm.revision:
                warning = (
                    f"[POZOR] Revision mismatch: '{input_article}' "
                    f"(rev {input_norm.revision or 'none'}) "
                    f"matched to '{db_article}' (rev {db_norm.revision or 'none'})"
                )
                return ("revision_ignored", warning)

        # Fuzzy match (base numbers match)
        warning = (
            f"[POZOR] Fuzzy match: '{input_article}' matched to '{db_article}' "
            f"(normalized: {input_norm.base} ~ {db_norm.base})"
        )
        return ("fuzzy", warning)


# Convenience functions
def normalize_article_number(article_number: str) -> str:
    """Get normalized article number (without prefix/revision)."""
    return ArticleNumberMatcher.normalize(article_number).base


def get_search_variants(article_number: str) -> List[str]:
    """Get list of search variants for fuzzy matching."""
    return ArticleNumberMatcher.generate_variants(article_number)
