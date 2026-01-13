"""
Stagehand client for analyzing web pages using the official Python SDK.
https://github.com/browserbase/stagehand-python
"""

import asyncio
import os
import re
from typing import Optional, List, Dict, Any

from .models import LinkClaim, VerificationResult, ClaimType, AlignmentStatus


# JSON schemas for structured extraction
APPLICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "is_application_page": {"type": "boolean", "description": "Whether this is an application/signup form page"},
        "page_title": {"type": "string", "description": "The title of the page"},
        "page_purpose": {"type": "string", "description": "Brief description of what the page is for"},
        "has_form_fields": {"type": "boolean", "description": "Whether the page has input fields or forms"},
        "role_or_position": {"type": "string", "description": "The job/role being applied for if applicable"},
        "confidence": {"type": "number", "description": "Confidence score between 0 and 1"},
        "reason": {"type": "string", "description": "Brief explanation of the conclusion"},
    },
    "required": ["is_application_page", "page_title", "confidence", "reason"],
}

SPEAKER_SCHEMA = {
    "type": "object",
    "properties": {
        "is_about_person": {"type": "boolean", "description": "Whether this page is about the expected person"},
        "person_name_found": {"type": "string", "description": "The person's name found on the page"},
        "page_title": {"type": "string", "description": "The title of the page"},
        "profile_type": {"type": "string", "description": "Type: linkedin, company_bio, personal_website, other"},
        "person_title": {"type": "string", "description": "The person's job title if found"},
        "confidence": {"type": "number", "description": "Confidence score between 0 and 1"},
        "reason": {"type": "string", "description": "Brief explanation of the conclusion"},
    },
    "required": ["is_about_person", "page_title", "confidence", "reason"],
}

GENERIC_SCHEMA = {
    "type": "object",
    "properties": {
        "is_relevant": {"type": "boolean", "description": "Whether the page is about the expected topic based on title and content"},
        "page_title": {"type": "string", "description": "The title of the page"},
        "page_type": {"type": "string", "description": "Type of page: event, article, product, registration, etc."},
        "topic_match": {"type": "boolean", "description": "Does the page title or main heading match the expected topic?"},
        "confidence": {"type": "number", "description": "Confidence score between 0 and 1"},
        "reason": {"type": "string", "description": "Brief conclusion"},
    },
    "required": ["is_relevant", "page_title", "topic_match", "confidence", "reason"],
}

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


class StagehandClient:
    """Client for analyzing web pages using Stagehand Python SDK."""
    
    def __init__(
        self,
        api_key: str = None,
        project_id: str = None,
        model_api_key: str = None,
        model_name: str = "gpt-4o",
        use_direct_mode: bool = False,
    ):
        """
        Initialize the Stagehand client.
        
        Args:
            api_key: Browserbase API key (or set BROWSERBASE_API_KEY env var)
            project_id: Browserbase project ID (or set BROWSERBASE_PROJECT_ID env var)
            model_api_key: API key for the AI model (or set MODEL_API_KEY env var)
            model_name: AI model to use for analysis (default: gpt-4o)
            use_direct_mode: If True, use simple HTTP fetching instead of Stagehand
        """
        self.use_direct_mode = use_direct_mode
        self.api_key = api_key or os.getenv("BROWSERBASE_API_KEY")
        self.project_id = project_id or os.getenv("BROWSERBASE_PROJECT_ID")
        self.model_api_key = model_api_key or os.getenv("MODEL_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.model_name = model_name
        
        if not use_direct_mode:
            if not self.api_key:
                raise ValueError("BROWSERBASE_API_KEY is required (or use use_direct_mode=True)")
            if not self.project_id:
                raise ValueError("BROWSERBASE_PROJECT_ID is required (or use use_direct_mode=True)")
            if not self.model_api_key:
                raise ValueError("MODEL_API_KEY or OPENAI_API_KEY is required for Stagehand")
    
    def analyze_links_sync(self, claims: List[LinkClaim]) -> List[VerificationResult]:
        """
        Analyze multiple links (synchronous version).
        
        Args:
            claims: List of LinkClaim objects to analyze
            
        Returns:
            List of VerificationResult objects
        """
        if not claims:
            return []
        
        if self.use_direct_mode:
            # Run async direct mode in event loop
            return asyncio.get_event_loop().run_until_complete(self._analyze_links_direct(claims))
        else:
            return self._analyze_links_stagehand_sync(claims)
    
    async def analyze_links(self, claims: List[LinkClaim]) -> List[VerificationResult]:
        """Async wrapper for analyze_links."""
        if not claims:
            return []
        
        if self.use_direct_mode:
            return await self._analyze_links_direct(claims)
        else:
            # Run sync stagehand in thread pool to not block
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._analyze_links_stagehand_sync, claims)
    
    def _analyze_links_stagehand_sync(self, claims: List[LinkClaim]) -> List[VerificationResult]:
        """Analyze links using the official Stagehand SDK (synchronous)."""
        from stagehand import Stagehand
        
        results = []
        
        # Create Stagehand client
        client = Stagehand(
            browserbase_api_key=self.api_key,
            browserbase_project_id=self.project_id,
            model_api_key=self.model_api_key,
        )
        
        session = None
        
        try:
            print("   🤘 Creating Stagehand session...")
            session = client.sessions.create(model_name=self.model_name)
            session_id = session.id
            
            print(f"   ✅ Session started: {session_id[:12]}...")
            print(f"   👀 Watch live: https://www.browserbase.com/sessions/{session_id}")
            
            for i, claim in enumerate(claims):
                print(f"\n   [{i+1}/{len(claims)}] Navigating to: {claim.url[:60]}...")
                
                try:
                    # Navigate to the URL
                    client.sessions.navigate(session_id, url=claim.url)
                    
                    # Analyze based on claim type
                    if claim.claim_type == ClaimType.APPLICATION:
                        result = self._analyze_application(client, session_id, claim)
                    elif claim.claim_type == ClaimType.SPEAKER_PROFILE:
                        result = self._analyze_speaker(client, session_id, claim)
                    else:
                        result = self._analyze_generic(client, session_id, claim)
                    
                    results.append(result)
                    print(f"       → {result.status_emoji} {result.short_reason[:50]}")
                    
                except Exception as e:
                    print(f"       ❌ Error: {str(e)[:50]}")
                    results.append(VerificationResult(
                        url=claim.url,
                        claim_type=claim.claim_type,
                        status=AlignmentStatus.ERROR,
                        confidence=0.0,
                        short_reason=f"Failed to analyze: {str(e)[:80]}",
                        error_message=str(e),
                    ))
        
        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ Stagehand error: {error_msg[:80]}")
            
            # Mark remaining claims as errors
            for claim in claims[len(results):]:
                results.append(VerificationResult(
                    url=claim.url,
                    claim_type=claim.claim_type,
                    status=AlignmentStatus.ERROR,
                    confidence=0.0,
                    short_reason=f"Stagehand error: {error_msg[:80]}",
                    error_message=error_msg,
                ))
        
        finally:
            if session:
                print("\n   🔒 Closing session...")
                try:
                    client.sessions.end(session.id)
                except Exception:
                    pass
            client.close()
        
        return results
    
    def _analyze_application(self, client, session_id: str, claim: LinkClaim) -> VerificationResult:
        """Analyze if the current page is an application form."""
        try:
            response = client.sessions.extract(
                session_id,
                instruction=(
                    "Analyze this page: Is this an application form or job application page? "
                    "Look for form fields, submit buttons, application instructions. "
                    "Determine if someone could apply for a job, program, or opportunity here."
                ),
                schema=APPLICATION_SCHEMA,
            )
            
            # Extract the result from response.data.result
            data = self._get_extract_data(response)
            
            is_app = data.get("is_application_page", False)
            confidence = data.get("confidence", 0.5)
            
            if is_app:
                status = AlignmentStatus.ALIGNED
            elif confidence > 0.4:
                status = AlignmentStatus.QUESTIONABLE
            else:
                status = AlignmentStatus.MISALIGNED
            
            return VerificationResult(
                url=claim.url,
                claim_type=claim.claim_type,
                status=status,
                confidence=confidence,
                short_reason=data.get("reason", "Analysis complete"),
                page_title=data.get("page_title"),
                details={
                    "page_purpose": data.get("page_purpose"),
                    "has_form_fields": data.get("has_form_fields"),
                    "role_or_position": data.get("role_or_position"),
                },
            )
        except Exception as e:
            return self._fallback_result(claim, str(e))
    
    def _analyze_speaker(self, client, session_id: str, claim: LinkClaim) -> VerificationResult:
        """Analyze if the current page is about the expected speaker."""
        expected_name = claim.extracted_name or "the expected person"
        
        try:
            response = client.sessions.extract(
                session_id,
                instruction=(
                    f"Analyze this page: Is this page about a person named '{expected_name}'? "
                    f"Look for their name, biography, job title, company, photo. "
                    f"This should be a profile page (LinkedIn, company bio, etc.) for {expected_name}."
                ),
                schema=SPEAKER_SCHEMA,
            )
            
            # Extract the result from response.data.result
            data = self._get_extract_data(response)
            
            is_about = data.get("is_about_person", False)
            confidence = data.get("confidence", 0.5)
            
            if is_about:
                status = AlignmentStatus.ALIGNED
            elif confidence > 0.4:
                status = AlignmentStatus.QUESTIONABLE
            else:
                status = AlignmentStatus.MISALIGNED
            
            return VerificationResult(
                url=claim.url,
                claim_type=claim.claim_type,
                status=status,
                confidence=confidence,
                short_reason=data.get("reason", "Analysis complete"),
                page_title=data.get("page_title"),
                details={
                    "person_name_found": data.get("person_name_found"),
                    "profile_type": data.get("profile_type"),
                    "person_title": data.get("person_title"),
                },
            )
        except Exception as e:
            return self._fallback_result(claim, str(e))
    
    def _analyze_generic(self, client, session_id: str, claim: LinkClaim) -> VerificationResult:
        """Analyze if the current page is relevant to the context."""
        context = claim.claim_context[:300]
        
        # Check if this looks like an event link (Luma, Eventbrite, etc.)
        url_lower = claim.url.lower()
        is_event_url = any(x in url_lower for x in ['luma', 'eventbrite', 'meetup', 'lu.ma', 'kickoff', 'open-house', 'event'])
        
        # Extract any dates/times mentioned in the copy
        copy_date_info = self._extract_date_from_text(context)
        
        if is_event_url or copy_date_info:
            return self._analyze_event_page(client, session_id, claim, context, copy_date_info)
        
        try:
            response = client.sessions.extract(
                session_id,
                instruction=(
                    f"Check if this page matches the expected topic from this marketing text: '{context}'\n\n"
                    f"IMPORTANT: Focus on whether the PAGE TITLE or main heading matches the expected topic. "
                    f"Event registration pages (like Luma, Eventbrite, etc.) with matching titles ARE aligned. "
                    f"Don't penalize pages for having minimal text if the title clearly matches the topic."
                ),
                schema=GENERIC_SCHEMA,
            )
            
            # Extract the result from response.data.result
            data = self._get_extract_data(response)
            
            is_relevant = data.get("is_relevant", False)
            topic_match = data.get("topic_match", False)
            confidence = data.get("confidence", 0.5)
            
            # If title/topic matches, it's aligned even if content is sparse
            if is_relevant or topic_match:
                status = AlignmentStatus.ALIGNED
                if confidence < 0.7:
                    confidence = 0.75  # Boost confidence for title matches
            elif confidence > 0.4:
                status = AlignmentStatus.QUESTIONABLE
            else:
                status = AlignmentStatus.MISALIGNED
            
            return VerificationResult(
                url=claim.url,
                claim_type=claim.claim_type,
                status=status,
                confidence=confidence,
                short_reason=data.get("reason", "Analysis complete"),
                page_title=data.get("page_title"),
                details={
                    "page_type": data.get("page_type"),
                    "topic_match": topic_match,
                },
            )
        except Exception as e:
            return self._fallback_result(claim, str(e))
    
    def _extract_date_from_text(self, text: str) -> dict:
        """Extract date/time information from marketing copy."""
        import re
        
        result = {}
        text_lower = text.lower()
        
        # Common date patterns
        # "Jan 18", "January 18", "Jan 18th", "January 18, 2026"
        date_patterns = [
            r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?(?:[,\s]+(\d{4}))?',
            r'(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?',  # 1/18, 01-18-2026
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text_lower)
            if match:
                result['date_mentioned'] = match.group(0)
                break
        
        # Time patterns - require AM/PM or time range format
        # "6 PM", "6:00 PM", "5-7 PM", "5–7 PM" (with en-dash), "9 PM EST"
        time_patterns = [
            r'(\d{1,2})(?::(\d{2}))?\s*[-–]\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)',  # Time range: 5-7 PM, 5–7 PM
            r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)(?:\s*(est|pst|cst|mst|et|pt))?',  # Single time with AM/PM required
        ]
        
        for pattern in time_patterns:
            time_match = re.search(pattern, text_lower)
            if time_match:
                result['time_mentioned'] = time_match.group(0)
                break
        
        return result
    
    def _analyze_event_page(self, client, session_id: str, claim: LinkClaim, context: str, copy_date_info: dict) -> VerificationResult:
        """Analyze an event page and verify date/time matches."""
        try:
            response = client.sessions.extract(
                session_id,
                instruction=(
                    f"Extract the event details EXACTLY as shown on this page.\n\n"
                    f"IMPORTANT: Read the date and time EXACTLY as displayed on the page. "
                    f"Do NOT guess or infer dates. Copy the exact text shown for the event date and time.\n\n"
                    f"Marketing copy context: '{context}'\n\n"
                    f"Extract: the event name, the EXACT date shown, the EXACT time shown, and location."
                ),
                schema=EVENT_SCHEMA,
            )
            
            data = self._get_extract_data(response)
            
            is_event = data.get("is_event_page", False)
            topic_match = data.get("topic_match", False)
            page_date = data.get("event_date", "")
            page_time = data.get("event_time", "")
            confidence = data.get("confidence", 0.5)
            
            # Check for date/time mismatches - only flag if ACTUAL values differ
            date_mismatch = False
            mismatch_details = []
            
            import re
            
            if copy_date_info.get('date_mentioned') and page_date:
                copy_date = copy_date_info['date_mentioned'].lower()
                page_date_lower = page_date.lower()
                
                # Extract day number
                copy_day = re.search(r'\d{1,2}', copy_date)
                page_day = re.search(r'\d{1,2}', page_date_lower)
                
                # Only mismatch if day numbers are DIFFERENT
                if copy_day and page_day and copy_day.group() != page_day.group():
                    date_mismatch = True
                    mismatch_details.append(f"Date: copy mentions day {copy_day.group()}, page shows day {page_day.group()}")
            
            if copy_date_info.get('time_mentioned') and page_time:
                copy_time = copy_date_info['time_mentioned'].lower()
                page_time_lower = page_time.lower()
                
                # Extract start hour from time ranges
                copy_start = re.search(r'^(\d{1,2})', copy_time)
                page_start = re.search(r'^(\d{1,2})', page_time_lower)
                
                # Only mismatch if start times are DIFFERENT
                if copy_start and page_start and copy_start.group() != page_start.group():
                    date_mismatch = True
                    mismatch_details.append(f"Time: copy mentions {copy_time}, page shows {page_time}")
            
            # Determine status
            if date_mismatch:
                status = AlignmentStatus.MISALIGNED
                reason = " | ".join(mismatch_details)
                confidence = 0.9  # High confidence in the mismatch
            elif is_event and topic_match:
                status = AlignmentStatus.ALIGNED
                reason = data.get("reason", "Event page matches")
                if page_date:
                    reason += f" (Event: {page_date}"
                    if page_time:
                        reason += f" at {page_time}"
                    reason += ")"
            elif topic_match:
                status = AlignmentStatus.ALIGNED
                reason = data.get("reason", "Topic matches")
            elif confidence > 0.4:
                status = AlignmentStatus.QUESTIONABLE
                reason = data.get("reason", "Partial match")
            else:
                status = AlignmentStatus.MISALIGNED
                reason = data.get("reason", "Does not match")
            
            return VerificationResult(
                url=claim.url,
                claim_type=claim.claim_type,
                status=status,
                confidence=confidence,
                short_reason=reason,
                page_title=data.get("page_title"),
                details={
                    "is_event_page": is_event,
                    "event_date": page_date,
                    "event_time": page_time,
                    "event_location": data.get("event_location"),
                    "topic_match": topic_match,
                    "copy_date": copy_date_info.get('date_mentioned'),
                    "copy_time": copy_date_info.get('time_mentioned'),
                    "date_mismatch": date_mismatch,
                },
            )
        except Exception as e:
            return self._fallback_result(claim, str(e))
    
    def _get_extract_data(self, response) -> Dict[str, Any]:
        """Extract the data dictionary from a Stagehand extract response."""
        # Response structure: response.data.result contains the extracted data
        if hasattr(response, 'data') and hasattr(response.data, 'result'):
            result = response.data.result
            if isinstance(result, dict):
                return result
            # If result is an object, try to convert to dict
            if hasattr(result, '__dict__'):
                return result.__dict__
            # Try model_dump for Pydantic models
            if hasattr(result, 'model_dump'):
                return result.model_dump()
        return {}
    
    def _fallback_result(self, claim: LinkClaim, error: str) -> VerificationResult:
        """Return a fallback result when extraction fails."""
        return VerificationResult(
            url=claim.url,
            claim_type=claim.claim_type,
            status=AlignmentStatus.QUESTIONABLE,
            confidence=0.3,
            short_reason=f"Extraction issue: {error[:50]}",
            error_message=error,
        )
    
    # =========================================================================
    # Direct HTTP mode (fallback when Stagehand is not available)
    # =========================================================================
    
    async def _analyze_links_direct(self, claims: List[LinkClaim]) -> List[VerificationResult]:
        """Analyze links by fetching them directly (no Stagehand/AI)."""
        import httpx
        
        print("   📡 Using direct HTTP mode (simple heuristic analysis)")
        results = []
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            for i, claim in enumerate(claims):
                print(f"   [{i+1}/{len(claims)}] Fetching: {claim.url[:50]}...")
                
                try:
                    response = await client.get(
                        claim.url,
                        headers={"User-Agent": "Mozilla/5.0 LinkVerifier/1.0"},
                    )
                    
                    html = response.text
                    
                    # Extract title
                    title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
                    title = title_match.group(1).strip() if title_match else ""
                    
                    # Extract text
                    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
                    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
                    text = re.sub(r'<[^>]+>', ' ', text)
                    text = ' '.join(text.split()).lower()
                    
                    result = self._heuristic_analysis(claim, title, text)
                    results.append(result)
                    print(f"       → {result.status_emoji} {result.short_reason[:50]}")
                    
                except Exception as e:
                    results.append(VerificationResult(
                        url=claim.url,
                        claim_type=claim.claim_type,
                        status=AlignmentStatus.ERROR,
                        confidence=0.0,
                        short_reason=f"Could not fetch page: {str(e)[:50]}",
                        error_message=str(e),
                    ))
                
                await asyncio.sleep(0.5)
        
        return results
    
    def _heuristic_analysis(self, claim: LinkClaim, title: str, text: str) -> VerificationResult:
        """Simple heuristic analysis for direct mode."""
        title_lower = title.lower()
        text_lower = text[:5000]
        
        if claim.claim_type == ClaimType.APPLICATION:
            indicators = ["apply", "application", "submit", "form", "career", "job", "position", "hire"]
            matches = sum(1 for w in indicators if w in title_lower or w in text_lower)
            
            if matches >= 3:
                return VerificationResult(
                    url=claim.url, claim_type=claim.claim_type,
                    status=AlignmentStatus.ALIGNED, confidence=0.7,
                    short_reason="Page appears to be an application form",
                    page_title=title,
                )
            elif matches >= 1:
                return VerificationResult(
                    url=claim.url, claim_type=claim.claim_type,
                    status=AlignmentStatus.QUESTIONABLE, confidence=0.5,
                    short_reason="Page may contain application content",
                    page_title=title,
                )
        
        elif claim.claim_type == ClaimType.SPEAKER_PROFILE:
            if claim.extracted_name:
                name_lower = claim.extracted_name.lower()
                if name_lower in title_lower or name_lower in text_lower[:2000]:
                    return VerificationResult(
                        url=claim.url, claim_type=claim.claim_type,
                        status=AlignmentStatus.ALIGNED, confidence=0.75,
                        short_reason=f"Page contains info about {claim.extracted_name}",
                        page_title=title,
                    )
        
        else:  # Generic
            context_words = set(re.findall(r'\b[a-z]{4,}\b', claim.claim_context.lower()))
            context_words -= {"http", "https", "link", "click", "here", "this", "that"}
            if context_words:
                matches = sum(1 for w in context_words if w in title_lower or w in text_lower)
                if matches >= 3:
                    return VerificationResult(
                        url=claim.url, claim_type=claim.claim_type,
                        status=AlignmentStatus.ALIGNED, confidence=0.65,
                        short_reason=f"Page content matches context ({matches} keywords)",
                        page_title=title,
                    )
        
        return VerificationResult(
            url=claim.url,
            claim_type=claim.claim_type,
            status=AlignmentStatus.QUESTIONABLE,
            confidence=0.4,
            short_reason="Could not definitively verify alignment",
            page_title=title,
        )
