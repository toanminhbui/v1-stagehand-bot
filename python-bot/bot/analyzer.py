"""
Message parsing and link claim extraction for marketing materials.
"""

import re
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from .models import LinkClaim, ClaimType


# Patterns for detecting claim types
APPLICATION_PATTERNS = [
    r'\bapply\s+now\b',
    r'\bapply\s+here\b',
    r'\bapply\s+today\b',
    r'\bapplication[s]?\s+(?:are\s+)?(?:open|due|close)',  # "Applications are open", "Applications due"
    r'\bsubmit\s+(?:your\s+)?application\b',
    r'\bjoin\s+(?:our\s+)?team\b',
    r'\bwe\'?re\s+hiring\b',
    r'\bcareer(?:s)?\s+(?:page|opportunity|opening)\b',
    r'\bjob\s+(?:posting|opening|listing)\b',
]

SPEAKER_PATTERNS = [
    r'\bspeaker[s]?\b',
    r'\bpresenter[s]?\b',
    r'\bpanelist[s]?\b',
    r'\bfeatured\s+(?:guest|speaker)\b',
    r'\bmeet\s+(?:the\s+)?(?:speaker|team|presenter)\b',
    r'\babout\s+(?:the\s+)?(?:speaker|author|presenter)\b',
]

# URL regex pattern
URL_PATTERN = re.compile(
    r'https?://[^\s<>\[\]()]+(?:\([^\s<>\[\]()]*\)|[^\s<>\[\](),.])*',
    re.IGNORECASE
)

# Pattern for Slack-formatted links: <url|text> or <url>
SLACK_LINK_PATTERN = re.compile(r'<(https?://[^|>]+)(?:\|[^>]*)?>') 


def extract_urls(text: str) -> List[Tuple[str, int, int]]:
    """
    Extract all URLs from text, returning (url, start_pos, end_pos) tuples.
    Handles both plain URLs and Slack-formatted links.
    """
    urls = []
    
    # First, extract Slack-formatted links
    for match in SLACK_LINK_PATTERN.finditer(text):
        url = match.group(1)
        urls.append((url, match.start(), match.end()))
    
    # Then extract plain URLs (avoiding duplicates from Slack links)
    slack_ranges = [(u[1], u[2]) for u in urls]
    for match in URL_PATTERN.finditer(text):
        start, end = match.start(), match.end()
        # Check if this URL is already captured as a Slack link
        is_in_slack_link = any(
            s <= start and end <= e for s, e in slack_ranges
        )
        if not is_in_slack_link:
            urls.append((match.group(0), start, end))
    
    # Sort by position
    urls.sort(key=lambda x: x[1])
    return urls


def get_context_around_url(text: str, url_start: int, url_end: int, context_chars: int = 150) -> str:
    """
    Extract the text context around a URL.
    Returns the surrounding sentence or paragraph snippet, focusing on the same line.
    """
    # First, try to get the line containing the URL
    line_start = text.rfind('\n', 0, url_start) + 1
    line_end = text.find('\n', url_end)
    if line_end == -1:
        line_end = len(text)
    
    # Get the line text
    line_text = text[line_start:line_end].strip()
    
    # If line is too short, expand context but prefer text before the URL
    if len(line_text) < 30:
        context_start = max(0, url_start - context_chars)
        context_end = min(len(text), url_end + 50)  # Less context after
        context = text[context_start:context_end]
    else:
        context = line_text
    
    # Clean up: remove the URL itself from context for cleaner analysis
    url_in_context = text[url_start:url_end]
    context = context.replace(url_in_context, "[LINK]")
    
    # Clean up Slack formatting artifacts
    context = re.sub(r'<@[A-Z0-9]+>', '', context)  # Remove user mentions
    context = context.strip()
    
    return context


def detect_claim_type(context: str, url: str = "") -> Tuple[ClaimType, Optional[str]]:
    """
    Detect the type of claim being made about a link based on surrounding context.
    Returns (claim_type, extracted_name) where extracted_name is for speaker profiles.
    """
    context_lower = context.lower()
    url_lower = url.lower()
    
    # Check URL for profile indicators first (more reliable)
    if 'linkedin.com/in/' in url_lower or 'twitter.com/' in url_lower:
        name = extract_person_name(context)
        return ClaimType.SPEAKER_PROFILE, name
    
    # Check URL path for application indicators
    if '/apply' in url_lower or '/application' in url_lower or '/careers' in url_lower:
        return ClaimType.APPLICATION, None
    
    # Check for speaker/profile patterns in context (before application patterns)
    # This prevents "Apply now" from overshadowing speaker context
    for pattern in SPEAKER_PATTERNS:
        if re.search(pattern, context_lower):
            name = extract_person_name(context)
            return ClaimType.SPEAKER_PROFILE, name
    
    # Check if context looks like a list item with a person's name
    # Pattern: "- Name:" or "• Name:" or "- Name, Title:" at start of context
    list_item_match = re.match(r'^[\-•\*]\s*(?:Dr\.\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', context.strip())
    if list_item_match:
        name = list_item_match.group(1)
        # Filter out false positives
        if name not in ['Learn More', 'Read More', 'Click Here', 'Sign Up', 'Apply Now']:
            return ClaimType.SPEAKER_PROFILE, name
    
    # Check for application-related patterns
    for pattern in APPLICATION_PATTERNS:
        if re.search(pattern, context_lower):
            return ClaimType.APPLICATION, None
    
    # Check for common profile indicators in URL or context
    if any(indicator in context_lower for indicator in ['bio', 'profile', 'about me']):
        name = extract_person_name(context)
        if name:
            return ClaimType.SPEAKER_PROFILE, name
    
    return ClaimType.GENERIC, None


def extract_person_name(context: str) -> Optional[str]:
    """
    Try to extract a person's name from the context.
    Uses simple heuristics to find capitalized name patterns.
    """
    # Pattern for names like "Jane Doe", "Dr. John Smith", etc.
    name_patterns = [
        # Name followed by colon or dash (common in speaker lists)
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*[:\-–—]',
        # Name after "by" or "from"
        r'(?:by|from|with|featuring)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        # Name in quotes
        r'["\']([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)["\']',
        # Name with title
        r'(?:Dr\.|Mr\.|Ms\.|Mrs\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        # Simple capitalized name pattern near [LINK]
        r'([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s*[:\-–—]?\s*\[LINK\])',
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, context)
        if match:
            name = match.group(1).strip()
            # Filter out common false positives
            false_positives = ['Apply Now', 'Learn More', 'Read More', 'Click Here', 'Sign Up']
            if name not in false_positives:
                return name
    
    return None


def extract_links_and_claims(message_text: str) -> List[LinkClaim]:
    """
    Extract all links from a message and determine the claims being made about each.
    
    Args:
        message_text: The raw message text containing marketing copy with links
        
    Returns:
        List of LinkClaim objects, each containing a URL and its associated claim
    """
    claims = []
    urls = extract_urls(message_text)
    
    for url, start, end in urls:
        # Validate URL
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                continue
        except Exception:
            continue
        
        # Get surrounding context
        context = get_context_around_url(message_text, start, end)
        
        # Detect claim type
        claim_type, extracted_name = detect_claim_type(context, url)
        
        claims.append(LinkClaim(
            url=url,
            claim_context=context,
            claim_type=claim_type,
            extracted_name=extracted_name,
        ))
    
    return claims


def summarize_claims(claims: List[LinkClaim]) -> str:
    """
    Create a summary of the extracted claims for debugging/logging.
    """
    if not claims:
        return "No links found in the message."
    
    lines = [f"Found {len(claims)} link(s):"]
    for i, claim in enumerate(claims, 1):
        name_info = f" (expecting: {claim.extracted_name})" if claim.extracted_name else ""
        lines.append(f"  {i}. [{claim.claim_type.value}]{name_info}: {claim.url}")
    
    return "\n".join(lines)

