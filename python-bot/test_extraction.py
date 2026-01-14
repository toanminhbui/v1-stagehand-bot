#!/usr/bin/env python3
"""
Test script to see raw extraction results from Browserbase/Stagehand.
Usage:
    python test_extraction.py <url>
    python test_extraction.py https://lu.ma/some-event
    python test_extraction.py http://v1michigan.com/ship-it
"""

import sys
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Event extraction schema
EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "is_event_page": {"type": "boolean", "description": "Whether this is an event page (Luma, Eventbrite, etc.)"},
        "page_title": {"type": "string", "description": "The title/name of the event"},
        "event_date": {"type": "string", "description": "The date of the event (e.g., 'January 20, 2026' or 'Jan 20')"},
        "event_time": {"type": "string", "description": "The time of the event (e.g., '6:00 PM EST' or '18:00')"},
        "event_location": {"type": "string", "description": "The location or 'Online' if virtual"},
        "topic_match": {"type": "boolean", "description": "Does the event name match the expected topic?"},
        "confidence": {"type": "number", "description": "Confidence score between 0 and 1"},
        "reason": {"type": "string", "description": "Brief conclusion"},
    },
    "required": ["is_event_page", "page_title", "confidence", "reason"],
}


def test_extraction(url: str):
    """Test extraction for a single URL."""
    from stagehand import Stagehand
    
    api_key = os.getenv("BROWSERBASE_API_KEY")
    project_id = os.getenv("BROWSERBASE_PROJECT_ID")
    model_api_key = os.getenv("MODEL_API_KEY") or os.getenv("OPENAI_API_KEY")
    
    if not api_key or not project_id:
        print("❌ Missing BROWSERBASE_API_KEY or BROWSERBASE_PROJECT_ID")
        return
    
    print(f"\n{'='*60}")
    print(f"Testing URL: {url}")
    print(f"{'='*60}\n")
    
    try:
        # Initialize Stagehand (synchronous API like in stagehand_client.py)
        client = Stagehand(
            browserbase_api_key=api_key,
            browserbase_project_id=project_id,
            model_api_key=model_api_key,
        )
        
        print("🤘 Creating Stagehand session...")
        session = client.sessions.create(model_name="gpt-4o")
        session_id = session.id
        print(f"✅ Session created: {session_id[:12]}...")
        print(f"👀 Watch live: https://www.browserbase.com/sessions/{session_id}")
        
        # Navigate to URL
        print(f"\n📍 Navigating to {url}...")
        client.sessions.navigate(session_id, url=url)
        print("✅ Page loaded")
        
        # Extract event data
        print("\n🔍 Extracting event data...")
        response = client.sessions.extract(
            session_id,
            instruction=(
                "Extract the event details EXACTLY as shown on this page.\n\n"
                "IMPORTANT: Read the date and time EXACTLY as displayed on the page. "
                "Do NOT guess or infer dates. Copy the exact text shown for the event date and time.\n\n"
                "Extract: the event name, the EXACT date shown, the EXACT time shown, and location."
            ),
            schema=EVENT_SCHEMA,
        )
        
        print("\n" + "="*60)
        print("RAW EXTRACTION RESULT:")
        print("="*60)
        
        # Print the raw response
        print(f"\nResponse type: {type(response)}")
        print(f"\nResponse: {response}")
        
        # Try to extract data from different formats
        if hasattr(response, 'data'):
            print(f"\nresponse.data: {response.data}")
            if hasattr(response.data, 'result'):
                print(f"\nresponse.data.result: {response.data.result}")
        
        if hasattr(response, '__dict__'):
            print(f"\nResponse __dict__: {response.__dict__}")
        
        # Try to get the actual extracted values
        data = None
        if hasattr(response, 'data') and hasattr(response.data, 'result'):
            data = response.data.result
        elif isinstance(response, dict):
            data = response
        
        if data:
            print("\n" + "="*60)
            print("EXTRACTED EVENT DATA:")
            print("="*60)
            print(json.dumps(data, indent=2, default=str))
            
            print("\n📋 Summary:")
            print(f"  • Is Event Page: {data.get('is_event_page', 'N/A')}")
            print(f"  • Page Title: {data.get('page_title', 'N/A')}")
            print(f"  • Event Date: {data.get('event_date', 'N/A')}")
            print(f"  • Event Time: {data.get('event_time', 'N/A')}")
            print(f"  • Location: {data.get('event_location', 'N/A')}")
            print(f"  • Confidence: {data.get('confidence', 'N/A')}")
        
        # End session
        print("\n🔚 Ending session...")
        client.sessions.end(session_id)
        print("✅ Done!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    if len(sys.argv) < 2:
        # Default test URLs
        urls = [
            "http://v1michigan.com/ship-it",
        ]
        print("No URL provided. Testing default URLs...")
    else:
        urls = sys.argv[1:]
    
    for url in urls:
        test_extraction(url)


if __name__ == "__main__":
    main()

