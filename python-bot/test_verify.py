#!/usr/bin/env python3
"""
Test script to verify links and review copy without Slack integration.

Usage:
    python test_verify.py                      # Uses sample marketing copy
    python test_verify.py "Your copy here"    # Verify your own copy
    python test_verify.py --file copy.txt     # Verify from a file
    python test_verify.py --url https://...   # Verify a single URL directly
    python test_verify.py --direct            # Use direct HTTP mode (no Browserbase needed!)
    python test_verify.py --review            # Also review copy for spelling/wording
    python test_verify.py --review-only       # Only review copy (skip link verification)
    python test_verify.py --direct --review --file copy.txt  # Combine flags

Modes:
    Default: Uses Browserbase for full browser rendering (requires API keys)
    --direct: Fetches pages directly via HTTP (no API keys needed, simpler analysis)
    --review: Also check spelling and wording suggestions (requires OpenAI API key)
    --review-only: Skip link verification, only review copy text
"""

import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from bot.analyzer import extract_links_and_claims
from bot.stagehand_client import StagehandClient
from bot.formatter import format_slack_reply
from bot.models import LinkClaim, ClaimType, AlignmentStatus
from bot.copy_reviewer import CopyReviewer, format_review_result

# Sample marketing copy for testing
SAMPLE_COPY = """
Check out our company: https://www.anthropic.com

Apply to join our team: https://www.anthropic.com/careers

Meet our research lead:
- Dario Amodei: https://www.linkedin.com/in/dario-amodei/
"""


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


async def verify_single_url(url: str, claim_type: str = "generic", use_direct: bool = False):
    """Verify a single URL directly."""
    client = StagehandClient(use_direct_mode=use_direct)
    
    # Create a simple claim for the URL
    type_map = {
        "application": ClaimType.APPLICATION,
        "speaker": ClaimType.SPEAKER_PROFILE,
        "generic": ClaimType.GENERIC,
    }
    
    claim = LinkClaim(
        url=url,
        claim_context=f"Testing URL: {url}",
        claim_type=type_map.get(claim_type, ClaimType.GENERIC),
    )
    
    print(f"\n🔍 Verifying: {url}")
    print(f"   Type: {claim_type}")
    print(f"   Mode: {'Direct HTTP' if use_direct else 'Browserbase'}")
    print("   Please wait...")
    
    results = await client.analyze_links([claim])
    return results


async def verify_marketing_copy(copy: str, use_direct: bool = False):
    """Verify all links in marketing copy."""
    # Extract links and claims
    print_header("EXTRACTING LINKS")
    claims = extract_links_and_claims(copy)
    
    if not claims:
        print("\n⚠️  No links found in the provided text.")
        return []
    
    print(f"\n📊 Found {len(claims)} link(s) to verify:")
    for i, claim in enumerate(claims, 1):
        print(f"   {i}. [{claim.claim_type.value}] {claim.url}")
    
    # Verify each link
    print_header("VERIFYING LINKS")
    
    if use_direct:
        print("\n🔍 Analyzing pages with direct HTTP requests...")
        print("   (Faster but simpler analysis - no JavaScript rendering)\n")
    else:
        print("\n🔍 Analyzing pages with Browserbase...")
        print("   (This may take 10-30 seconds per link)\n")
    
    client = StagehandClient(use_direct_mode=use_direct)
    results = await client.analyze_links(claims)
    
    return results


def print_results(results):
    """Print verification results in a readable format."""
    print_header("VERIFICATION RESULTS")
    
    if not results:
        print("\n⚠️  No results to display.")
        return
    
    # Summary
    aligned = sum(1 for r in results if r.status == AlignmentStatus.ALIGNED)
    questionable = sum(1 for r in results if r.status == AlignmentStatus.QUESTIONABLE)
    misaligned = sum(1 for r in results if r.status == AlignmentStatus.MISALIGNED)
    errors = sum(1 for r in results if r.status == AlignmentStatus.ERROR)
    
    print(f"\n📊 Summary: {len(results)} link(s) verified")
    if aligned:
        print(f"   ✅ {aligned} aligned")
    if questionable:
        print(f"   ⚠️  {questionable} need review")
    if misaligned:
        print(f"   ❌ {misaligned} misaligned")
    if errors:
        print(f"   🚫 {errors} error(s)")
    
    # Individual results
    for i, result in enumerate(results, 1):
        emoji = result.status_emoji
        status_text = {
            AlignmentStatus.ALIGNED: "ALIGNED",
            AlignmentStatus.QUESTIONABLE: "NEEDS REVIEW",
            AlignmentStatus.MISALIGNED: "MISALIGNED",
            AlignmentStatus.ERROR: "ERROR",
        }.get(result.status, "UNKNOWN")
        
        print(f"\n[Link {i}] {emoji} {status_text}")
        print(f"  URL: {result.url}")
        print(f"  Type: {result.claim_type.value}")
        print(f"  Reason: {result.short_reason}")
        
        if result.page_title:
            print(f"  Page Title: \"{result.page_title}\"")
        
        print(f"  Confidence: {int(result.confidence * 100)}%")
        
        if result.details:
            print(f"  Details: {result.details}")
        
        if result.error_message:
            print(f"  Error: {result.error_message}")
    
    # Also show Slack-formatted output
    print_header("SLACK-FORMATTED OUTPUT (LINKS)")
    print("\nThis is what the bot would post in Slack:\n")
    print(format_slack_reply(results))


async def review_copy_text(copy: str):
    """Review marketing copy for spelling and wording issues."""
    print_header("REVIEWING COPY")
    print("\n📝 Analyzing text for spelling and wording...")
    
    reviewer = CopyReviewer()
    result = await reviewer.review_copy(copy)
    
    return result


def print_review_results(result):
    """Print copy review results."""
    print_header("COPY REVIEW RESULTS")
    print()
    print(format_review_result(result))


async def main():
    import os
    
    # Check for flags
    use_direct = "--direct" in sys.argv
    do_review = "--review" in sys.argv
    review_only = "--review-only" in sys.argv
    args = [a for a in sys.argv[1:] if a not in ("--direct", "--review", "--review-only")]
    
    # Check for required environment variables
    if review_only or do_review:
        if not os.getenv("MODEL_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            print("⚠️  Missing OPENAI_API_KEY or MODEL_API_KEY for copy review")
            sys.exit(1)
    
    if not review_only and not use_direct:
        missing = []
        if not os.getenv("BROWSERBASE_API_KEY"):
            missing.append("BROWSERBASE_API_KEY")
        if not os.getenv("BROWSERBASE_PROJECT_ID"):
            missing.append("BROWSERBASE_PROJECT_ID")
        if not os.getenv("MODEL_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            missing.append("MODEL_API_KEY (or OPENAI_API_KEY)")
        
        if missing:
            print(f"⚠️  Missing required credentials: {', '.join(missing)}")
            print("\nOptions:")
            print("  1. Add --direct flag to use direct HTTP mode (no API keys needed)")
            print("     Example: python test_verify.py --direct --file sample_copy.txt")
            print("")
            print("  2. Add --review-only to skip link verification and only review copy")
            print("     Example: python test_verify.py --review-only --file sample_copy.txt")
            print("")
            print("  3. Or set up credentials in your .env file:")
            print("     BROWSERBASE_API_KEY=your-browserbase-key")
            print("     BROWSERBASE_PROJECT_ID=your-project-id")
            print("     MODEL_API_KEY=your-gemini-or-openai-key")
            sys.exit(1)
        
        print("🤘 Using Stagehand with Browserbase")
    elif use_direct:
        print("📡 Using direct HTTP mode (no AI analysis)")
    
    if do_review or review_only:
        print("📝 Copy review enabled")
    
    # Parse arguments and get copy text
    copy = None
    results = []
    
    if len(args) > 0:
        if args[0] == "--help" or args[0] == "-h":
            print(__doc__)
            sys.exit(0)
        
        elif args[0] == "--url" and len(args) > 1:
            # Verify single URL (no copy review for single URL mode)
            url = args[1]
            claim_type = args[2] if len(args) > 2 else "generic"
            results = await verify_single_url(url, claim_type, use_direct)
            print_results(results)
        
        elif args[0] == "--file" and len(args) > 1:
            # Read from file
            try:
                with open(args[1], 'r') as f:
                    copy = f.read()
                print(f"📄 Reading from file: {args[1]}")
            except FileNotFoundError:
                print(f"❌ File not found: {args[1]}")
                sys.exit(1)
        
        else:
            # Use command line argument as the copy
            copy = " ".join(args)
            print("📝 Verifying provided text...")
    
    else:
        # Use sample copy
        print("📝 Using sample marketing copy")
        print("   (Pass your own text as an argument, or use --url for single URLs)")
        print_header("INPUT")
        print(SAMPLE_COPY)
        copy = SAMPLE_COPY
    
    # Process copy if we have it
    if copy:
        # Link verification (unless review-only)
        if not review_only:
            results = await verify_marketing_copy(copy, use_direct)
            print_results(results)
        
        # Copy review (if enabled)
        if do_review or review_only:
            review_result = await review_copy_text(copy)
            print_review_results(review_result)
    
    print("\n" + "=" * 60)
    print("✅ Complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

