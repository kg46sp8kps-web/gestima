"""GESTIMA - Article Number Fuzzy Matching

Handles customer-specific prefixes and drawing number revisions.

Examples:
- "byn-10101251" → normalize to "10101251" (strip prefix)
- "90057637-00" → base "90057637", revision "00"
- "trgcz-123456" → normalize to "123456"

Match strategies:
1. Exact match (highest priority)
2. Match without customer prefix
3. Match without revision suffix
4. Match with different prefix (warning)
"""

import re
import logging
from typing import Optional, Tuple, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Known customer prefixes (add more as needed)
CUSTOMER_PREFIXES = [
    "byn-",
    "trgcz-",
    "gelso-",
    # Add more customer-specific prefixes here
]

# Revision pattern: -00, -01, -A, -B, etc. at END of string
REVISION_PATTERN = r"-([0-9]{2}|[A-Z])$"


@dataclass
class NormalizedArticleNumber:
    """Normalized article number with metadata"""
    original: str           # Original input (e.g., "byn-10101251")
    normalized: str         # Normalized without prefix/revision (e.g., "10101251")
    base: str              # Base without revision (e.g., "90057637")
    prefix: Optional[str]  # Extracted prefix (e.g., "byn-")
    revision: Optional[str] # Extracted revision (e.g., "00")


class ArticleNumberMatcher:
    """Fuzzy matcher for article numbers"""

    @staticmethod
    def normalize(article_number: str) -> NormalizedArticleNumber:
        """
        Normalize article number - extract prefix and revision.

        Examples:
            "byn-10101251" → normalized="10101251", prefix="byn-"
            "90057637-00" → base="90057637", revision="00"
            "10101251" → no prefix, no revision
        """
        original = article_number.strip()
        prefix = None
        revision = None
        normalized = original
        base = original

        # 1. Extract customer prefix
        for known_prefix in CUSTOMER_PREFIXES:
            if original.lower().startswith(known_prefix.lower()):
                prefix = original[:len(known_prefix)]
                normalized = original[len(known_prefix):]
                break

        # 2. Extract revision suffix (from normalized version)
        revision_match = re.search(REVISION_PATTERN, normalized)
        if revision_match:
            revision = revision_match.group(1)
            base = normalized[:revision_match.start()]
        else:
            base = normalized

        logger.debug(
            f"Normalized '{original}' → "
            f"base='{base}', prefix='{prefix}', revision='{revision}'"
        )

        return NormalizedArticleNumber(
            original=original,
            normalized=normalized,
            base=base,
            prefix=prefix,
            revision=revision
        )

    @staticmethod
    def generate_variants(article_number: str) -> List[str]:
        """
        Generate matching variants for fuzzy search.

        Examples:
            "byn-10101251" → ["byn-10101251", "10101251"]
            "90057637-00" → ["90057637-00", "90057637"]
            "trgcz-123-01" → ["trgcz-123-01", "123-01", "123"]

        Returns:
            List of variants to try (ordered by priority)
        """
        norm = ArticleNumberMatcher.normalize(article_number)
        variants = [
            norm.original,     # Exact match (highest priority)
            norm.normalized,   # Without customer prefix
            norm.base,         # Without prefix AND revision
        ]

        # Deduplicate while preserving order
        seen = set()
        unique_variants = []
        for v in variants:
            if v and v not in seen:
                seen.add(v)
                unique_variants.append(v)

        logger.debug(f"Generated variants for '{article_number}': {unique_variants}")
        return unique_variants

    @staticmethod
    def match_type(
        input_article: str,
        db_article: str
    ) -> Tuple[str, str]:
        """
        Determine match type and generate warning.

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
                    f"⚠️ Prefix mismatch: '{input_article}' matched to '{db_article}' "
                    f"(customer prefix differs)"
                )
                return ("prefix_stripped", warning)

        # Match with different revisions
        if input_norm.base == db_norm.base:
            if input_norm.revision != db_norm.revision:
                warning = (
                    f"⚠️ Revision mismatch: '{input_article}' (rev {input_norm.revision or 'none'}) "
                    f"matched to '{db_article}' (rev {db_norm.revision or 'none'})"
                )
                return ("revision_ignored", warning)

        # Fuzzy match (base numbers match)
        warning = (
            f"⚠️ Fuzzy match: '{input_article}' matched to '{db_article}' "
            f"(normalized: {input_norm.base} ≈ {db_norm.base})"
        )
        return ("fuzzy", warning)


# Convenience functions
def normalize_article_number(article_number: str) -> str:
    """Get normalized article number (without prefix/revision)"""
    return ArticleNumberMatcher.normalize(article_number).base


def get_search_variants(article_number: str) -> List[str]:
    """Get list of search variants for fuzzy matching"""
    return ArticleNumberMatcher.generate_variants(article_number)
