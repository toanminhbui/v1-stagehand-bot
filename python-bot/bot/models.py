"""
Data models for the Marketing Link Verifier bot.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional, Dict, Any
from enum import Enum


class ClaimType(str, Enum):
    """Types of claims that can be made about a link."""
    APPLICATION = "application"
    SPEAKER_PROFILE = "speaker_profile"
    GENERIC = "generic"


class AlignmentStatus(str, Enum):
    """Status of link alignment with its claim."""
    ALIGNED = "aligned"
    QUESTIONABLE = "questionable"
    MISALIGNED = "misaligned"
    ERROR = "error"


@dataclass
class LinkClaim:
    """Represents a link extracted from marketing copy with its contextual claim."""
    url: str
    claim_context: str  # The surrounding text that describes the link
    claim_type: ClaimType
    extracted_name: Optional[str] = None  # For speaker profiles, the expected person's name


@dataclass
class VerificationResult:
    """Result of verifying a link against its claim."""
    url: str
    claim_type: ClaimType
    status: AlignmentStatus
    confidence: float  # 0.0 to 1.0
    short_reason: str
    page_title: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    @property
    def is_aligned(self) -> bool:
        """Check if the link is aligned with its claim."""
        return self.status == AlignmentStatus.ALIGNED
    
    @property
    def status_emoji(self) -> str:
        """Get the emoji representing the alignment status."""
        return {
            AlignmentStatus.ALIGNED: "✅",
            AlignmentStatus.QUESTIONABLE: "⚠️",
            AlignmentStatus.MISALIGNED: "❌",
            AlignmentStatus.ERROR: "🚫",
        }.get(self.status, "❓")

