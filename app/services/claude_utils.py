"""
Claude API utilities - shared helpers for Claude integration

JSON repair strategy for Claude responses:
1. Try strict JSON parse first
2. If fails, attempt repair: trailing commas, unclosed brackets, truncated strings
3. If repair fails, try progressive truncation to find valid JSON prefix
"""
import json
import re
import logging
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)


def _repair_json(text: str) -> Optional[str]:
    """
    Attempt to repair common JSON issues from Claude responses.

    Common problems:
    - Trailing commas before } or ]
    - Truncated JSON (response cut off by max_tokens)
    - Unclosed strings, arrays, objects
    - Comments or markdown mixed in

    Returns:
        Repaired JSON string, or None if unfixable
    """
    if not text:
        return None

    # Step 1: Remove trailing commas before ] or }
    # e.g., [1, 2, 3,] → [1, 2, 3]
    repaired = re.sub(r',\s*([}\]])', r'\1', text)

    # Step 2: Try parsing as-is after trailing comma fix
    try:
        json.loads(repaired)
        logger.info("JSON repaired: removed trailing commas")
        return repaired
    except json.JSONDecodeError:
        pass

    # Step 3: Fix truncated JSON by closing unclosed brackets/braces
    # Count open vs close brackets
    open_braces = repaired.count('{') - repaired.count('}')
    open_brackets = repaired.count('[') - repaired.count(']')

    if open_braces > 0 or open_brackets > 0:
        # Truncated response — try to close it
        # First, remove any trailing partial value (incomplete string, number, etc.)
        # Find last complete JSON element (ends with }, ], number, "string", true, false, null)
        truncated = repaired.rstrip()

        # Remove trailing partial string (unterminated "...")
        if truncated.count('"') % 2 != 0:
            # Odd number of quotes = unclosed string
            last_quote = truncated.rfind('"')
            # Find the opening quote of this string
            # Walk back to find the key-value separator
            search_pos = last_quote - 1
            while search_pos >= 0 and truncated[search_pos] != '"':
                search_pos -= 1
            if search_pos >= 0:
                # Remove the entire incomplete key-value pair
                # Go back further to find the comma or brace
                trim_pos = search_pos
                while trim_pos > 0 and truncated[trim_pos - 1] in ' \t\n\r,':
                    trim_pos -= 1
                truncated = truncated[:trim_pos]

        # Remove trailing comma
        truncated = truncated.rstrip().rstrip(',')

        # Close brackets in reverse order of opening
        closers = ']' * max(0, open_brackets) + '}' * max(0, open_braces)

        # But we need correct nesting order — scan from end
        # to determine what needs closing
        stack = []
        in_string = False
        escape = False
        for ch in truncated:
            if escape:
                escape = False
                continue
            if ch == '\\' and in_string:
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch in '{[':
                stack.append(ch)
            elif ch in '}]':
                if stack:
                    stack.pop()

        # Close remaining open brackets/braces in LIFO order
        closers = ''
        for opener in reversed(stack):
            closers += ']' if opener == '[' else '}'

        candidate = truncated + closers

        # Remove trailing commas again after truncation repair
        candidate = re.sub(r',\s*([}\]])', r'\1', candidate)

        try:
            json.loads(candidate)
            logger.info(
                f"JSON repaired: closed {len(stack)} unclosed brackets/braces "
                f"(truncated response)"
            )
            return candidate
        except json.JSONDecodeError as e:
            logger.debug(f"Bracket-closing repair failed: {e}")

    # Step 4: Progressive truncation — find the longest valid JSON prefix
    # This handles cases where Claude appended comments after JSON
    # or the JSON is partially corrupt near the end
    for end_pos in range(len(repaired), max(len(repaired) // 2, 100), -1):
        chunk = repaired[:end_pos].rstrip()
        if not chunk.endswith('}') and not chunk.endswith(']'):
            continue
        try:
            json.loads(chunk)
            logger.info(
                f"JSON repaired: found valid JSON prefix "
                f"({end_pos}/{len(repaired)} chars)"
            )
            return chunk
        except json.JSONDecodeError:
            continue

    return None


def _extract_json_text(text: str) -> str:
    """
    Extract JSON from Claude response text.

    Claude often returns markdown commentary before/after JSON.
    This function isolates the JSON portion.
    """
    # Try markdown-wrapped JSON first (```json ... ```)
    json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if json_match:
        return json_match.group(1)

    # Try to find JSON object/array boundaries
    first_brace = text.find('{')
    first_bracket = text.find('[')

    if first_brace >= 0 and (first_bracket < 0 or first_brace < first_bracket):
        last_brace = text.rfind('}')
        if last_brace > first_brace:
            return text[first_brace:last_brace + 1]
    elif first_bracket >= 0:
        last_bracket = text.rfind(']')
        if last_bracket > first_bracket:
            return text[first_bracket:last_bracket + 1]

    # If no closing bracket found but opening exists (truncated response)
    if first_brace >= 0:
        return text[first_brace:]
    if first_bracket >= 0:
        return text[first_bracket:]

    return text


def parse_claude_json_response(
    content: Any,
    extract_key: Optional[str] = None
) -> Union[Dict, List]:
    """
    Parse Claude API response and extract JSON.

    Handles:
    - Markdown-wrapped JSON (```json ... ```)
    - Direct JSON in text with commentary
    - Truncated JSON (max_tokens cutoff)
    - Trailing commas and other common Claude JSON issues
    - List-wrapped content (content[0].text)

    Strategy:
    1. Extract text from response
    2. Isolate JSON portion (skip markdown commentary)
    3. Try strict parse
    4. On failure: repair JSON and retry
    5. On repair failure: return empty with error log

    Args:
        content: Claude response.content (list or text)
        extract_key: If set, return data[extract_key] instead of full JSON

    Returns:
        Parsed JSON dict/list, or empty dict/list on failure

    Example:
        >>> content = [MessageContent(text='```json\\n{"ops": []}\\n```')]
        >>> parse_claude_json_response(content, extract_key='ops')
        []
    """
    text = ""
    try:
        # Extract text from Claude response
        if isinstance(content, list) and len(content) > 0:
            text = content[0].text if hasattr(content[0], 'text') else str(content[0])
        else:
            text = str(content)

        # Isolate JSON portion from surrounding text/markdown
        json_text = _extract_json_text(text)

        # Try strict parse first
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as first_error:
            # Attempt repair
            logger.warning(
                f"Strict JSON parse failed: {first_error}. "
                f"Attempting repair on {len(json_text)} chars..."
            )
            repaired = _repair_json(json_text)
            if repaired:
                data = json.loads(repaired)
                logger.info("JSON repair successful — data recovered")
            else:
                # Re-raise original error for logging below
                raise first_error

        # Extract specific key if requested
        if extract_key:
            if isinstance(data, dict):
                return data.get(extract_key, [] if extract_key.endswith('s') else {})
            else:
                logger.warning(f"Expected dict for extract_key, got {type(data)}")
                return data

        return data

    except (json.JSONDecodeError, AttributeError, TypeError, IndexError) as e:
        # Log raw text for debugging (truncated)
        raw_preview = text[:500] if text else 'N/A'
        logger.error(
            f"Failed to parse Claude JSON response (even after repair): {e}\n"
            f"Raw text preview (first 500 chars): {raw_preview}"
        )
        # Return appropriate empty type
        if extract_key and extract_key.endswith('s'):  # Assume list if plural
            return []
        return {}


def build_few_shot_examples(similar_cases: List[Dict], max_examples: int = 3) -> str:
    """
    Build few-shot learning examples from similar verified cases.

    Args:
        similar_cases: List of similar recognized cases from DB
        max_examples: Max number of examples to include

    Returns:
        Formatted string for Claude prompt
    """
    if not similar_cases:
        return ""

    examples = []
    for i, case in enumerate(similar_cases[:max_examples], 1):
        similarity = case.get('similarity', 0)
        examples.append(f"""
Example {i} ({similarity}% similar):
  AI originally found: {case.get('ai_features', [])}
  Expert corrected to: {case.get('verified_features', [])}
  Mistake was: "{case.get('corrections', 'N/A')}"
  Accuracy score: {case.get('accuracy', 'N/A')}
""")

    return "\n".join(examples)
