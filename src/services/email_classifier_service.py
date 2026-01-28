"""
Email Classification Service
Uses OpenRouter to classify emails and filter spam/promotions
"""
import json
from typing import Dict, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from .openrouter_service import call_openrouter_structured, call_openrouter
from ..config.settings import OPENROUTER_CLASSIFIER_MODEL


class EmailCategory(Enum):
    """Email classification categories"""
    SUPPORT_REQUEST = "support_request"  # Genuine support request - needs response
    PROMOTION = "promotion"              # Marketing/promotional email - auto-delete
    SPAM = "spam"                        # Spam/junk - auto-delete
    NEWSLETTER = "newsletter"            # Newsletter subscription - auto-archive
    AUTOMATED = "automated"              # Auto-generated (receipts, confirmations) - archive
    INQUIRY = "inquiry"                  # General inquiry - needs response
    COMPLAINT = "complaint"              # Complaint - high priority response
    FEEDBACK = "feedback"                # Feedback - acknowledge and store
    OTHER = "other"                      # Uncategorized - forward for review


@dataclass
class EmailClassification:
    """Result of email classification"""
    category: EmailCategory
    confidence: float  # 0.0 to 1.0
    priority: int      # 1 (high) to 5 (low)
    should_respond: bool
    should_delete: bool
    should_archive: bool
    reason: str
    suggested_action: str


def classify_email(
    from_email: str,
    subject: str,
    body: str
) -> EmailClassification:
    """
    Classify an email using AI to determine how to handle it
    
    Args:
        from_email: Sender email address
        subject: Email subject
        body: Email body (plain text)
        
    Returns:
        EmailClassification with category and recommended actions
    """
    # Truncate body if too long
    max_body_len = 1500
    truncated_body = body[:max_body_len] + "..." if len(body) > max_body_len else body
    
    system_prompt = """You are an email classification assistant. Analyze emails and classify them accurately.
You must respond with valid JSON only, no other text."""

    prompt = f"""Analyze this email and classify it. Respond with a JSON object.

**From:** {from_email}
**Subject:** {subject}
**Body:**
{truncated_body}

Respond with this exact JSON structure:
{{
    "category": "support_request" | "promotion" | "spam" | "newsletter" | "automated" | "inquiry" | "complaint" | "feedback" | "other",
    "confidence": 0.0 to 1.0,
    "priority": 1 to 5 (1=highest, 5=lowest),
    "should_respond": true/false,
    "should_delete": true/false,
    "should_archive": true/false,
    "reason": "Brief explanation of classification",
    "suggested_action": "What to do with this email"
}}

Classification guidelines:
- promotion/spam/newsletter: should_delete=true or should_archive=true, should_respond=false
- support_request/inquiry/complaint: should_respond=true, priority 1-3
- automated: should_archive=true, should_respond=false
- complaint: priority=1, should_respond=true
- feedback: priority=3, should_respond=true (acknowledge)"""

    result = call_openrouter_structured(
        prompt=prompt,
        model=OPENROUTER_CLASSIFIER_MODEL,
        system_prompt=system_prompt,
        max_tokens=512
    )
    
    if result:
        try:
            return EmailClassification(
                category=EmailCategory(result.get("category", "other")),
                confidence=float(result.get("confidence", 0.5)),
                priority=int(result.get("priority", 3)),
                should_respond=bool(result.get("should_respond", True)),
                should_delete=bool(result.get("should_delete", False)),
                should_archive=bool(result.get("should_archive", False)),
                reason=str(result.get("reason", "Classification completed")),
                suggested_action=str(result.get("suggested_action", "Review manually"))
            )
        except (ValueError, KeyError) as e:
            print(f"Error parsing classification result: {e}")
    
    # Default: treat as support request to be safe
    return EmailClassification(
        category=EmailCategory.OTHER,
        confidence=0.3,
        priority=3,
        should_respond=True,
        should_delete=False,
        should_archive=False,
        reason="Classification failed, defaulting to manual review",
        suggested_action="Forward for manual review"
    )


def is_spam_or_promotion(classification: EmailClassification) -> bool:
    """Check if email should be filtered out"""
    spam_categories = {
        EmailCategory.SPAM,
        EmailCategory.PROMOTION,
        EmailCategory.NEWSLETTER
    }
    return (
        classification.category in spam_categories or
        classification.should_delete
    )


def needs_response(classification: EmailClassification) -> bool:
    """Check if email needs a response"""
    return classification.should_respond


def get_priority_emoji(priority: int) -> str:
    """Get emoji for priority level"""
    emojis = {
        1: "🔴",  # Critical
        2: "🟠",  # High
        3: "🟡",  # Medium
        4: "🟢",  # Low
        5: "⚪",  # Very Low
    }
    return emojis.get(priority, "⚪")


def format_classification_summary(classification: EmailClassification) -> str:
    """Format classification for display"""
    priority_emoji = get_priority_emoji(classification.priority)
    
    return (
        f"📊 Classification: {classification.category.value}\n"
        f"{priority_emoji} Priority: {classification.priority}/5\n"
        f"📝 Confidence: {classification.confidence:.0%}\n"
        f"💬 Respond: {'Yes' if classification.should_respond else 'No'}\n"
        f"📌 Reason: {classification.reason}"
    )
