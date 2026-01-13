#!/usr/bin/env python3
"""
Quick test script to parse marketing copy and extract links with their claims.
Run this to see what the analyzer detects without needing Slack or Browserbase.

Usage:
    python test_analyzer.py                    # Uses sample marketing copy
    python test_analyzer.py "Your copy here"   # Parse your own copy
    python test_analyzer.py --file copy.txt    # Parse from a file
"""

import sys
from bot.analyzer import extract_links_and_claims, summarize_claims
from bot.models import ClaimType

# Sample marketing copy for testing
SAMPLE_COPY = """
🚀 Join Our Team at TechCorp!

We're hiring talented engineers to build the future of AI.
Apply now: https://techcorp.com/careers/apply

---

📅 Upcoming Conference: AI Summit 2026

Meet our amazing speakers:
- Dr. Jane Smith (Keynote): https://linkedin.com/in/janesmith
- John Doe, CTO of DataFlow: https://dataflow.io/team/john
- Sarah Johnson: https://twitter.com/sarahjtech

Learn more about the event: https://aisummit2026.com/about

Register here: https://aisummit2026.com/register
"""


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_claim(index: int, claim):
    """Print a single claim in a readable format."""
    claim_type_labels = {
        ClaimType.APPLICATION: "📝 APPLICATION",
        ClaimType.SPEAKER_PROFILE: "👤 SPEAKER PROFILE", 
        ClaimType.GENERIC: "🔗 GENERIC LINK",
    }
    
    label = claim_type_labels.get(claim.claim_type, "❓ UNKNOWN")
    
    print(f"\n[Link {index}] {label}")
    print(f"  URL: {claim.url}")
    
    if claim.extracted_name:
        print(f"  Expected Person: {claim.extracted_name}")
    
    print(f"  Context: \"{claim.claim_context[:100]}{'...' if len(claim.claim_context) > 100 else ''}\"")


def main():
    # Determine input source
    if len(sys.argv) > 1:
        if sys.argv[1] == "--file" and len(sys.argv) > 2:
            # Read from file
            try:
                with open(sys.argv[2], 'r') as f:
                    copy = f.read()
                print(f"📄 Reading from file: {sys.argv[2]}")
            except FileNotFoundError:
                print(f"❌ File not found: {sys.argv[2]}")
                sys.exit(1)
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print(__doc__)
            sys.exit(0)
        else:
            # Use command line argument as the copy
            copy = " ".join(sys.argv[1:])
            print("📝 Parsing provided text...")
    else:
        # Use sample copy
        copy = SAMPLE_COPY
        print("📝 Using sample marketing copy (pass your own text as an argument)")
    
    print_header("INPUT MARKETING COPY")
    print(copy)
    
    # Extract links and claims
    print_header("EXTRACTED LINKS & CLAIMS")
    
    claims = extract_links_and_claims(copy)
    
    if not claims:
        print("\n⚠️  No links found in the provided text.")
        print("    Make sure your text contains valid URLs (https://...)")
        return
    
    # Print summary
    print(f"\n📊 Found {len(claims)} link(s):")
    
    app_count = sum(1 for c in claims if c.claim_type == ClaimType.APPLICATION)
    speaker_count = sum(1 for c in claims if c.claim_type == ClaimType.SPEAKER_PROFILE)
    generic_count = sum(1 for c in claims if c.claim_type == ClaimType.GENERIC)
    
    if app_count:
        print(f"   • {app_count} application link(s)")
    if speaker_count:
        print(f"   • {speaker_count} speaker profile link(s)")
    if generic_count:
        print(f"   • {generic_count} generic link(s)")
    
    # Print each claim
    for i, claim in enumerate(claims, 1):
        print_claim(i, claim)
    
    print_header("WHAT THE BOT WOULD CHECK")
    
    for i, claim in enumerate(claims, 1):
        print(f"\n[Link {i}] {claim.url}")
        
        if claim.claim_type == ClaimType.APPLICATION:
            print("  ➡️  Bot will verify: Is this page an application/job form?")
            print("      Looking for: form fields, 'apply', 'submit', job titles")
        
        elif claim.claim_type == ClaimType.SPEAKER_PROFILE:
            name = claim.extracted_name or "the mentioned person"
            print(f"  ➡️  Bot will verify: Is this page about {name}?")
            print("      Looking for: name match, bio, title, company, photo")
        
        else:
            print("  ➡️  Bot will verify: Is page content relevant to surrounding text?")
            print(f"      Context: \"{claim.claim_context[:50]}...\"")
    
    print("\n" + "=" * 60)
    print("✅ Analysis complete! Run with Slack integration to verify links.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

