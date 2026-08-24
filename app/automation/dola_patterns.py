"""
Pattern Engine & Scoped Message Deduplicator for Dola Response Detection.
Supports English & Chinese confirmation prompts and quota exhaustion patterns.
"""

import re
from typing import List, Set, Dict, Any, Tuple
from dataclasses import dataclass, field

# Primary Generation Start Signals (MUST contain at least one)
PRIMARY_GENERATION_PATTERNS = [
    re.compile(r"(?i)video\s+will\s+be\s+generated"),
    re.compile(r"(?i)ready\s+in\s+\d+(?:-\d+)?\s+minutes?"),
    re.compile(r"(?i)I'll\s+send\s+it\s+to\s+you\s+when\s+it's\s+done"),
    re.compile(r"(?i)generation\s+started"),
    re.compile(r"(?i)generation\s+in\s+progress"),
    re.compile(r"(?i)generating\s+your\s+video"),
    re.compile(r"(?i)正在生成视频|开始生成视频|视频生成中|视频制作中"),
]

# Supporting Signals (Contextual only, CANNOT trigger GENERATING alone)
SUPPORTING_PATTERNS = [
    re.compile(r"(?i)Seedance\s+2\.0"),
    re.compile(r"(?i)\d+\s+points?\s+left"),
    re.compile(r"(?i)\d+\s+points?\s+will\s+be\s+used"),
    re.compile(r"剩余\s*\d+\s*点|消耗\s*\d+\s*点"),
]

# Duration / Confirmation Warning Patterns (English & Chinese)
WARNING_PATTERNS = [
    re.compile(r"(?i)longer\s+(?:than|then)\s+\d+\s+seconds?\s+is\s+not\s+supported"),
    re.compile(r"(?i)continue\s+generating\s+for\s+you"),
    re.compile(r"(?i)do\s+you\s+want\s+to\s+continue"),
    re.compile(r"(?i)confirm\s+duration"),
    re.compile(r"(?i)please\s+confirm"),
    re.compile(r"(?i)once\s+confirmed"),
    re.compile(r"(?i)inferred\s+parameters\s+for\s+your\s+confirmation"),
    re.compile(r"请确认|确认生成|是否继续|视频生成参数|已推断|超过\s*10\s*秒|不支持超过10秒|10秒视频"),
]

# Dedicated Quota / Limit Exceeded Patterns
QUOTA_PATTERNS = [
    re.compile(r"(?i)currently\s+generating\s+video\s+longer\s+(?:than|then)\s+10\s*seconds?\s+is\s+not\s+supported"),
    re.compile(r"(?i)longer\s+(?:than|then)\s+10\s*seconds?\s+is\s+not\s+supported"),
    re.compile(r"(?i)10\s*seconds?\s+is\s+not\s+supported"),
    re.compile(r"(?i)generating\s+video\s+longer\s+(?:than|then)\s+10"),
    re.compile(r"(?i)daily\s+limit\s+exceeded"),
    re.compile(r"(?i)quota\s+exceeded"),
    re.compile(r"暂不支持超过10秒|不支持超过10秒|超过10秒的视频|每日额度已满|点数不足"),
]

@dataclass
class ChatMessageBaseline:
    initial_message_count: int = 0
    known_message_ids: Set[str] = field(default_factory=set)
    known_video_counts: int = 0
    page_text_snapshot: str = ""   # Full page text at baseline — used to detect NEW Dola responses

class DolaPatternEngine:
    def __init__(self):
        self.processed_message_ids: Set[str] = set()

    def reset(self):
        self.processed_message_ids.clear()

    def is_quota_exceeded(self, text: str) -> bool:
        """Check if message matches daily quota or 10-second limitation exhaustion."""
        if not text:
            return False
        for pattern in QUOTA_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def is_duration_warning(self, text: str) -> bool:
        """Check if a message node matches duration warning/confirmation patterns."""
        if not text:
            return False
        for pattern in WARNING_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def is_generation_start(self, text: str) -> Tuple[bool, bool, bool]:
        """
        Evaluates text for generation start signals.
        Returns Tuple[is_start, has_primary, has_supporting].
        Rule: is_start is True ONLY if has_primary is True.
        """
        if not text:
            return False, False, False

        has_primary = any(p.search(text) for p in PRIMARY_GENERATION_PATTERNS)
        has_supporting = any(p.search(text) for p in SUPPORTING_PATTERNS)

        # Primary signal MUST be present
        is_start = has_primary
        return is_start, has_primary, has_supporting
