"""
Copy reviewer for spell checking and wording suggestions using OpenAI API.
"""

import os
from typing import List, Optional
from dataclasses import dataclass, field
import json


@dataclass
class SpellingIssue:
    """A spelling or typo issue found in the text."""
    original: str
    suggestion: str
    context: str  # The sentence/phrase containing the issue


@dataclass
class WordingIssue:
    """A wording or style suggestion."""
    original_phrase: str
    suggested_phrase: str
    reason: str
    severity: str  # "minor", "moderate", "important"


@dataclass
class CopyReviewResult:
    """Result of reviewing marketing copy."""
    spelling_issues: List[SpellingIssue] = field(default_factory=list)
    wording_suggestions: List[WordingIssue] = field(default_factory=list)
    overall_score: int = 100  # 0-100 score
    summary: str = ""


class CopyReviewer:
    """Reviews marketing copy for spelling and wording issues using OpenAI."""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        """
        Initialize the copy reviewer.
        
        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            model: OpenAI model to use (default: gpt-4o-mini for cost efficiency)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("MODEL_API_KEY")
        self.model = model
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY or MODEL_API_KEY is required for copy review")
    
    async def review_copy(self, text: str) -> CopyReviewResult:
        """
        Review marketing copy for spelling and wording issues.
        
        Args:
            text: The marketing copy to review
            
        Returns:
            CopyReviewResult with issues and suggestions
        """
        import httpx
        
        prompt = f"""You are an expert copywriter and editor reviewing marketing material.

Analyze the following marketing copy and provide feedback on:
1. **Spelling errors** - typos, misspellings
2. **Grammar issues** - incorrect grammar, punctuation
3. **Wording suggestions** - ways to make the copy clearer, more engaging, or more professional

Marketing copy to review:
---
{text}
---

Respond with a JSON object in this exact format:
{{
    "spelling_issues": [
        {{
            "original": "the misspelled word",
            "suggestion": "the correct spelling",
            "context": "the sentence containing the error"
        }}
    ],
    "wording_suggestions": [
        {{
            "original_phrase": "the original phrase",
            "suggested_phrase": "improved version",
            "reason": "why this is better",
            "severity": "minor|moderate|important"
        }}
    ],
    "overall_score": 85,
    "summary": "Brief overall assessment of the copy quality"
}}

Notes:
- Only include actual issues, not nitpicks
- For emojis and casual tone, don't flag as issues if they fit the marketing context
- Focus on clarity, professionalism, and effectiveness
- Score from 0-100 where 100 is perfect
- If no issues found, return empty arrays
"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are an expert copywriter. Respond only with valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "response_format": {"type": "json_object"},
                    },
                    timeout=30.0,
                )
                
                response.raise_for_status()
                data = response.json()
                
                # Parse the response
                content = data["choices"][0]["message"]["content"]
                result_data = json.loads(content)
                
                return self._parse_result(result_data)
                
        except Exception as e:
            # Return empty result on error
            return CopyReviewResult(
                summary=f"Error reviewing copy: {str(e)[:100]}"
            )
    
    def _parse_result(self, data: dict) -> CopyReviewResult:
        """Parse the OpenAI response into a CopyReviewResult."""
        spelling_issues = []
        for issue in data.get("spelling_issues", []):
            spelling_issues.append(SpellingIssue(
                original=issue.get("original", ""),
                suggestion=issue.get("suggestion", ""),
                context=issue.get("context", ""),
            ))
        
        wording_suggestions = []
        for suggestion in data.get("wording_suggestions", []):
            wording_suggestions.append(WordingIssue(
                original_phrase=suggestion.get("original_phrase", ""),
                suggested_phrase=suggestion.get("suggested_phrase", ""),
                reason=suggestion.get("reason", ""),
                severity=suggestion.get("severity", "minor"),
            ))
        
        return CopyReviewResult(
            spelling_issues=spelling_issues,
            wording_suggestions=wording_suggestions,
            overall_score=data.get("overall_score", 100),
            summary=data.get("summary", ""),
        )


def format_review_result(result: CopyReviewResult) -> str:
    """Format the review result for display."""
    lines = ["*📝 Copy Review Results*\n"]
    
    # Overall score
    score = result.overall_score
    if score >= 90:
        score_emoji = "🌟"
    elif score >= 70:
        score_emoji = "👍"
    elif score >= 50:
        score_emoji = "⚠️"
    else:
        score_emoji = "❌"
    
    lines.append(f"{score_emoji} *Overall Score: {score}/100*")
    
    if result.summary:
        lines.append(f"_{result.summary}_\n")
    
    # Spelling issues
    if result.spelling_issues:
        lines.append(f"\n*🔤 Spelling Issues ({len(result.spelling_issues)}):*")
        for issue in result.spelling_issues:
            lines.append(f"  • `{issue.original}` → `{issue.suggestion}`")
            if issue.context:
                lines.append(f"    _Context: \"{issue.context[:60]}...\"_")
    
    # Wording suggestions
    if result.wording_suggestions:
        lines.append(f"\n*✍️ Wording Suggestions ({len(result.wording_suggestions)}):*")
        for suggestion in result.wording_suggestions:
            severity_emoji = {"minor": "💡", "moderate": "📝", "important": "⚡"}.get(suggestion.severity, "💡")
            lines.append(f"  {severity_emoji} \"{suggestion.original_phrase}\"")
            lines.append(f"     → \"{suggestion.suggested_phrase}\"")
            if suggestion.reason:
                lines.append(f"     _Reason: {suggestion.reason}_")
    
    # No issues
    if not result.spelling_issues and not result.wording_suggestions:
        lines.append("\n✅ No spelling or wording issues found!")
    
    return "\n".join(lines)

