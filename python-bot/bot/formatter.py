"""
Slack response formatting for verification results.
"""

from typing import List
from .models import VerificationResult, AlignmentStatus, ClaimType


def format_slack_reply(results: List[VerificationResult]) -> str:
    """
    Format verification results as a Slack-friendly message.
    
    Args:
        results: List of VerificationResult objects
        
    Returns:
        Formatted Slack message string with mrkdwn formatting
    """
    if not results:
        return "No links were found in your message to verify."
    
    # Build summary stats
    aligned = sum(1 for r in results if r.status == AlignmentStatus.ALIGNED)
    questionable = sum(1 for r in results if r.status == AlignmentStatus.QUESTIONABLE)
    misaligned = sum(1 for r in results if r.status == AlignmentStatus.MISALIGNED)
    errors = sum(1 for r in results if r.status == AlignmentStatus.ERROR)
    
    # Header with summary
    lines = ["*📋 Link Verification Results*\n"]
    
    # Summary line
    total = len(results)
    summary_parts = []
    if aligned > 0:
        summary_parts.append(f"{aligned} aligned")
    if questionable > 0:
        summary_parts.append(f"{questionable} need review")
    if misaligned > 0:
        summary_parts.append(f"{misaligned} misaligned")
    if errors > 0:
        summary_parts.append(f"{errors} error(s)")
    
    lines.append(f"_{total} link(s) checked: {', '.join(summary_parts)}_\n")
    
    # Individual results
    for i, result in enumerate(results, 1):
        lines.append(format_single_result(i, result))
    
    return "\n".join(lines)


def format_single_result(index: int, result: VerificationResult) -> str:
    """
    Format a single verification result.
    
    Args:
        index: The link number (1-indexed)
        result: The VerificationResult to format
        
    Returns:
        Formatted string for this result
    """
    # Status display
    status_text = {
        AlignmentStatus.ALIGNED: "*Aligned*",
        AlignmentStatus.QUESTIONABLE: "*Needs Review*",
        AlignmentStatus.MISALIGNED: "*Misaligned*",
        AlignmentStatus.ERROR: "*Error*",
    }.get(result.status, "*Unknown*")
    
    # Claim type context
    claim_type_text = {
        ClaimType.APPLICATION: "Application page check",
        ClaimType.SPEAKER_PROFILE: "Speaker profile check",
        ClaimType.GENERIC: "Content relevance check",
    }.get(result.claim_type, "Link check")
    
    # Build the result line
    emoji = result.status_emoji
    
    # Truncate URL for display if too long
    display_url = result.url
    if len(display_url) > 60:
        display_url = display_url[:57] + "..."
    
    # Main line
    line = f"*Link {index}:* `{display_url}`\n"
    line += f"  {emoji} {status_text} – {result.short_reason}"
    
    # Add page title if available
    if result.page_title and result.status != AlignmentStatus.ERROR:
        line += f"\n  _Page: \"{result.page_title}\"_"
    
    # Add confidence indicator for non-errors
    if result.status != AlignmentStatus.ERROR:
        confidence_pct = int(result.confidence * 100)
        line += f" ({confidence_pct}% confidence)"
    
    # Add error details if applicable
    if result.error_message:
        line += f"\n  _Error: {result.error_message}_"
    
    return line + "\n"


def format_working_message() -> str:
    """Return the initial 'working on it' message."""
    return "🔍 Analyzing links in your message... This may take a moment."


def format_error_message(error: str) -> str:
    """Format an error message when the entire analysis fails."""
    return f"❌ Sorry, I encountered an error while analyzing the links:\n```{error}```"


def format_no_links_message() -> str:
    """Format a message when no links are found."""
    return "🤔 I didn't find any links in your message to verify. Please include URLs in your marketing copy for me to check."


def create_blocks_message(results: List[VerificationResult]) -> list:
    """
    Create a rich Slack blocks message for better formatting.
    This provides a more structured visual display.
    
    Args:
        results: List of VerificationResult objects
        
    Returns:
        List of Slack block elements
    """
    blocks = []
    
    # Header
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": "📋 Link Verification Results",
            "emoji": True
        }
    })
    
    # Summary section
    aligned = sum(1 for r in results if r.status == AlignmentStatus.ALIGNED)
    questionable = sum(1 for r in results if r.status == AlignmentStatus.QUESTIONABLE)
    misaligned = sum(1 for r in results if r.status == AlignmentStatus.MISALIGNED)
    
    summary_text = f"{len(results)} link(s) checked: "
    summary_parts = []
    if aligned > 0:
        summary_parts.append(f"✅ {aligned} aligned")
    if questionable > 0:
        summary_parts.append(f"⚠️ {questionable} need review")
    if misaligned > 0:
        summary_parts.append(f"❌ {misaligned} misaligned")
    summary_text += " | ".join(summary_parts) if summary_parts else "No results"
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": summary_text
        }
    })
    
    blocks.append({"type": "divider"})
    
    # Individual results
    for i, result in enumerate(results, 1):
        emoji = result.status_emoji
        status_text = {
            AlignmentStatus.ALIGNED: "Aligned",
            AlignmentStatus.QUESTIONABLE: "Needs Review",
            AlignmentStatus.MISALIGNED: "Misaligned",
            AlignmentStatus.ERROR: "Error",
        }.get(result.status, "Unknown")
        
        result_text = f"*Link {i}:* <{result.url}|{_truncate_url(result.url)}>\n"
        result_text += f"{emoji} *{status_text}* – {result.short_reason}"
        
        if result.page_title:
            result_text += f"\n_Page: \"{result.page_title}\"_"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": result_text
            }
        })
    
    return blocks


def _truncate_url(url: str, max_length: int = 50) -> str:
    """Truncate a URL for display."""
    if len(url) <= max_length:
        return url
    return url[:max_length - 3] + "..."

