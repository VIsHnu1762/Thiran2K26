"""
BillAgent Pro - Accountant Agent
==================================
Agent 4: GL code assignment and expense categorization.
Uses vendor history, keyword matching, and LLM fallback.
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)


class GLCodeSource(str, Enum):
    """Source of GL code assignment."""
    VENDOR_DEFAULT = "vendor_default"
    VENDOR_HISTORY = "vendor_history"
    KEYWORD_MATCH = "keyword"
    LLM_CLASSIFICATION = "llm"
    MANUAL = "manual"
    DEFAULT = "default"


@dataclass
class GLCodeAssignment:
    """Result of GL code assignment for a line item."""
    line_item_index: int
    gl_code: str
    gl_code_name: Optional[str]
    source: GLCodeSource
    confidence: float  # 0.0 to 1.0
    description: str  # Item description for reference
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "line_item_index": self.line_item_index,
            "gl_code": self.gl_code,
            "gl_code_name": self.gl_code_name,
            "source": self.source.value,
            "confidence": self.confidence,
            "description": self.description,
        }


@dataclass
class AccountantResult:
    """Result of the Accountant Agent processing."""
    assignments: List[GLCodeAssignment] = field(default_factory=list)
    total_items: int = 0
    assigned_count: int = 0
    default_count: int = 0
    llm_used: bool = False
    vendor_default_used: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "assignments": [a.to_dict() for a in self.assignments],
            "total_items": self.total_items,
            "assigned_count": self.assigned_count,
            "default_count": self.default_count,
            "llm_used": self.llm_used,
            "vendor_default_used": self.vendor_default_used,
            "assignment_rate": self.assigned_count / self.total_items if self.total_items > 0 else 0,
        }


# =============================================================================
# Default GL Code Keyword Mappings
# =============================================================================
GL_CODE_MAPPINGS: Dict[str, List[str]] = {
    "5001": [  # Office Supplies
        "office", "supplies", "paper", "pen", "pencil", "stapler", "folder",
        "stationery", "printer", "ink", "toner", "envelope", "notebook",
        "marker", "clipboard", "binder", "tape", "glue", "scissors"
    ],
    "5002": [  # Travel & Transportation
        "travel", "transport", "fuel", "gas", "petrol", "diesel", "taxi",
        "uber", "ola", "flight", "train", "bus", "parking", "toll",
        "mileage", "airfare", "cab", "auto", "rickshaw"
    ],
    "5003": [  # Utilities
        "utility", "utilities", "electric", "electricity", "water", "gas",
        "internet", "phone", "telecom", "broadband", "wifi", "mobile",
        "telephone", "power", "energy", "sewage"
    ],
    "5004": [  # Professional Services
        "professional", "consulting", "legal", "accounting", "audit",
        "advisory", "service", "lawyer", "attorney", "consultant",
        "chartered", "ca ", "advocate"
    ],
    "5005": [  # Maintenance & Repairs
        "maintenance", "repair", "fix", "service", "cleaning", "janitorial",
        "plumbing", "electrical", "hvac", "ac ", "air conditioning",
        "painting", "renovation", "restoration"
    ],
    "5006": [  # Raw Materials
        "raw", "material", "ingredient", "component", "supply",
        "manufacturing", "production", "chemical", "metal", "plastic",
        "fabric", "leather", "wood", "lumber"
    ],
    "5007": [  # Inventory Purchases
        "inventory", "stock", "goods", "merchandise", "product", "purchase",
        "wholesale", "retail", "resale", "trading"
    ],
    "5008": [  # Marketing & Advertising
        "marketing", "advertising", "ad ", "promotion", "campaign", "media",
        "print", "digital", "social", "branding", "banner", "hoarding",
        "pamphlet", "brochure", "flyer"
    ],
    "5009": [  # Insurance
        "insurance", "premium", "coverage", "policy", "health", "life",
        "vehicle", "property", "liability"
    ],
    "5010": [  # Rent & Lease
        "rent", "lease", "rental", "property", "office", "warehouse",
        "godown", "storage", "space", "premises"
    ],
    "5011": [  # Equipment
        "equipment", "machine", "machinery", "tool", "hardware", "computer",
        "laptop", "desktop", "server", "printer", "scanner", "ups",
        "furniture", "chair", "desk", "table"
    ],
    "5012": [  # Software & Subscriptions
        "software", "subscription", "license", "saas", "cloud", "app",
        "microsoft", "google", "adobe", "zoom", "slack", "github",
        "aws", "azure", "hosting", "domain"
    ],
    "5099": [  # Miscellaneous (fallback)
        "misc", "miscellaneous", "other", "general", "sundry"
    ],
}

# GL Code names for reference
GL_CODE_NAMES: Dict[str, str] = {
    "5001": "Office Supplies",
    "5002": "Travel & Transportation",
    "5003": "Utilities",
    "5004": "Professional Services",
    "5005": "Maintenance & Repairs",
    "5006": "Raw Materials",
    "5007": "Inventory Purchases",
    "5008": "Marketing & Advertising",
    "5009": "Insurance",
    "5010": "Rent & Lease",
    "5011": "Equipment",
    "5012": "Software & Subscriptions",
    "5099": "Miscellaneous Expenses",
}


class AccountantAgent:
    """
    Agent 4: Accountant Agent
    
    Responsible for assigning GL codes to line items using:
    1. Vendor default GL code (highest priority)
    2. Vendor history lookup (learn from past assignments)
    3. Keyword-based matching
    4. LLM classification (fallback for unknown items)
    
    Also learns from manual corrections to improve future assignments.
    """
    
    DEFAULT_GL_CODE = "5099"  # Miscellaneous Expenses
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        use_llm_fallback: bool = True,
        default_gl_code: str = "5099",
        keyword_confidence_threshold: float = 0.7,
    ):
        """
        Initialize the Accountant Agent.
        
        Args:
            openai_api_key: OpenAI API key for LLM fallback (optional)
            use_llm_fallback: Whether to use LLM for unknown items
            default_gl_code: Default GL code when no match found
            keyword_confidence_threshold: Minimum confidence for keyword matches
        """
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.use_llm_fallback = use_llm_fallback
        self.DEFAULT_GL_CODE = default_gl_code
        self.keyword_confidence_threshold = keyword_confidence_threshold
        
        # Pre-compile regex patterns for faster matching
        self._compile_patterns()
        
        logger.info(
            f"AccountantAgent initialized with LLM fallback={use_llm_fallback}, "
            f"default_gl_code={default_gl_code}"
        )
    
    def _compile_patterns(self):
        """Compile regex patterns for keyword matching."""
        self.keyword_patterns: Dict[str, re.Pattern] = {}
        for gl_code, keywords in GL_CODE_MAPPINGS.items():
            pattern = "|".join(re.escape(kw) for kw in keywords)
            self.keyword_patterns[gl_code] = re.compile(pattern, re.IGNORECASE)
    
    async def assign_gl_codes(
        self,
        line_items: List[Dict[str, Any]],
        vendor_id: Optional[UUID],
        db: AsyncSession,
    ) -> AccountantResult:
        """
        Assign GL codes to line items.
        
        Args:
            line_items: List of line item dictionaries with at least:
                - description: str (item description)
                - gl_code: str (optional, existing GL code)
            vendor_id: Vendor UUID for lookup (optional)
            db: AsyncSession for database queries
        
        Returns:
            AccountantResult with assignments for each line item
        """
        from app.models import Vendor, LineItem as LineItemModel, Bill
        from app.models.bill import BillStatus
        
        logger.info(f"Assigning GL codes to {len(line_items)} line items, vendor_id={vendor_id}")
        
        assignments: List[GLCodeAssignment] = []
        llm_used = False
        vendor_default_used = False
        
        # Get vendor info if available
        vendor = None
        vendor_default_gl = None
        vendor_history: Dict[str, str] = {}  # description pattern -> gl_code
        
        if vendor_id:
            vendor = await self._get_vendor(db, vendor_id, Vendor)
            if vendor:
                vendor_default_gl = vendor.default_gl_code
                vendor_history = await self._get_vendor_history(
                    db, vendor_id, LineItemModel, Bill, BillStatus
                )
                logger.debug(f"Vendor: {vendor.name}, default_gl={vendor_default_gl}, history_items={len(vendor_history)}")
        
        # Process each line item
        for idx, item in enumerate(line_items):
            description = item.get("description", "")
            existing_gl = item.get("gl_code")
            
            # Skip if already has a GL code
            if existing_gl:
                assignments.append(GLCodeAssignment(
                    line_item_index=idx,
                    gl_code=existing_gl,
                    gl_code_name=GL_CODE_NAMES.get(existing_gl),
                    source=GLCodeSource.MANUAL,
                    confidence=1.0,
                    description=description[:100],
                ))
                continue
            
            # Priority 1: Vendor default GL code
            if vendor_default_gl:
                assignments.append(GLCodeAssignment(
                    line_item_index=idx,
                    gl_code=vendor_default_gl,
                    gl_code_name=GL_CODE_NAMES.get(vendor_default_gl),
                    source=GLCodeSource.VENDOR_DEFAULT,
                    confidence=0.95,
                    description=description[:100],
                ))
                vendor_default_used = True
                continue
            
            # Priority 2: Vendor history lookup
            history_gl = self._check_vendor_history(description, vendor_history)
            if history_gl:
                assignments.append(GLCodeAssignment(
                    line_item_index=idx,
                    gl_code=history_gl,
                    gl_code_name=GL_CODE_NAMES.get(history_gl),
                    source=GLCodeSource.VENDOR_HISTORY,
                    confidence=0.9,
                    description=description[:100],
                ))
                continue
            
            # Priority 3: Keyword matching
            keyword_result = self._match_by_keywords(description)
            if keyword_result and keyword_result[1] >= self.keyword_confidence_threshold:
                gl_code, confidence = keyword_result
                assignments.append(GLCodeAssignment(
                    line_item_index=idx,
                    gl_code=gl_code,
                    gl_code_name=GL_CODE_NAMES.get(gl_code),
                    source=GLCodeSource.KEYWORD_MATCH,
                    confidence=confidence,
                    description=description[:100],
                ))
                continue
            
            # Priority 4: LLM classification (if enabled)
            if self.use_llm_fallback and self.openai_api_key:
                llm_result = await self._classify_with_llm(description)
                if llm_result:
                    gl_code, confidence = llm_result
                    assignments.append(GLCodeAssignment(
                        line_item_index=idx,
                        gl_code=gl_code,
                        gl_code_name=GL_CODE_NAMES.get(gl_code),
                        source=GLCodeSource.LLM_CLASSIFICATION,
                        confidence=confidence,
                        description=description[:100],
                    ))
                    llm_used = True
                    continue
            
            # Fallback: Use default GL code
            assignments.append(GLCodeAssignment(
                line_item_index=idx,
                gl_code=self.DEFAULT_GL_CODE,
                gl_code_name=GL_CODE_NAMES.get(self.DEFAULT_GL_CODE),
                source=GLCodeSource.DEFAULT,
                confidence=0.3,
                description=description[:100],
            ))
        
        # Count statistics
        assigned_count = sum(1 for a in assignments if a.source != GLCodeSource.DEFAULT)
        default_count = sum(1 for a in assignments if a.source == GLCodeSource.DEFAULT)
        
        logger.info(
            f"GL code assignment complete: {assigned_count}/{len(line_items)} assigned, "
            f"{default_count} defaults, llm_used={llm_used}"
        )
        
        return AccountantResult(
            assignments=assignments,
            total_items=len(line_items),
            assigned_count=assigned_count,
            default_count=default_count,
            llm_used=llm_used,
            vendor_default_used=vendor_default_used,
        )
    
    async def _get_vendor(self, db: AsyncSession, vendor_id: UUID, Vendor) -> Optional[Any]:
        """Get vendor by ID."""
        result = await db.execute(
            select(Vendor).where(Vendor.id == vendor_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_vendor_history(
        self,
        db: AsyncSession,
        vendor_id: UUID,
        LineItemModel,
        Bill,
        BillStatus,
    ) -> Dict[str, str]:
        """
        Get GL code history for a vendor from past approved bills.
        Returns a mapping of description patterns to GL codes.
        """
        history: Dict[str, str] = {}
        
        try:
            # Get line items from approved bills for this vendor
            result = await db.execute(
                select(LineItemModel.description, LineItemModel.gl_code)
                .join(Bill, LineItemModel.bill_id == Bill.id)
                .where(
                    Bill.vendor_id == vendor_id,
                    Bill.status == BillStatus.APPROVED,
                    LineItemModel.gl_code.isnot(None),
                )
                .limit(100)  # Limit to recent history
            )
            
            for description, gl_code in result.all():
                if description and gl_code:
                    # Normalize description for matching
                    normalized = self._normalize_description(description)
                    if normalized and len(normalized) >= 3:
                        history[normalized] = gl_code
        except Exception as e:
            logger.warning(f"Error getting vendor history: {e}")
        
        return history
    
    def _normalize_description(self, description: str) -> str:
        """Normalize description for matching."""
        # Convert to lowercase and remove special characters
        normalized = re.sub(r'[^a-z0-9\s]', '', description.lower())
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        return normalized
    
    def _check_vendor_history(
        self,
        description: str,
        history: Dict[str, str]
    ) -> Optional[str]:
        """Check if description matches vendor history."""
        if not history:
            return None
        
        normalized = self._normalize_description(description)
        
        # Exact match
        if normalized in history:
            return history[normalized]
        
        # Partial match (description contains a known pattern)
        for pattern, gl_code in history.items():
            if pattern in normalized or normalized in pattern:
                return gl_code
        
        return None
    
    def _match_by_keywords(self, description: str) -> Optional[Tuple[str, float]]:
        """
        Match description against keyword patterns.
        Returns (gl_code, confidence) or None.
        """
        if not description:
            return None
        
        description_lower = description.lower()
        best_match: Optional[Tuple[str, float]] = None
        best_score = 0
        
        for gl_code, pattern in self.keyword_patterns.items():
            matches = pattern.findall(description_lower)
            if matches:
                # Calculate score based on number of matches and specificity
                score = len(matches) / max(len(description_lower.split()), 1)
                # Boost score for more specific matches
                score = min(score + 0.5, 0.9)
                
                if score > best_score:
                    best_score = score
                    best_match = (gl_code, score)
        
        return best_match
    
    async def _classify_with_llm(self, description: str) -> Optional[Tuple[str, float]]:
        """
        Use LLM to classify item description.
        Returns (gl_code, confidence) or None.
        """
        if not self.openai_api_key or not description:
            return None
        
        try:
            import openai
            
            client = openai.AsyncOpenAI(api_key=self.openai_api_key)
            
            # Build prompt with available GL codes
            gl_codes_info = "\n".join([
                f"- {code}: {name}" 
                for code, name in GL_CODE_NAMES.items()
            ])
            
            prompt = f"""Classify this expense item into one of the following GL codes.
Return ONLY the GL code number, nothing else.

Available GL Codes:
{gl_codes_info}

Item Description: {description}

GL Code:"""

            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an accountant classifying expenses. Return only the GL code number."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0.0,
            )
            
            gl_code = response.choices[0].message.content.strip()
            
            # Validate response
            if gl_code in GL_CODE_NAMES:
                return (gl_code, 0.75)  # LLM confidence
            
            logger.warning(f"LLM returned invalid GL code: {gl_code}")
            return None
            
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return None
    
    async def learn_from_correction(
        self,
        vendor_id: UUID,
        old_gl_code: str,
        new_gl_code: str,
        db: AsyncSession,
    ) -> bool:
        """
        Learn from a manual GL code correction.
        Updates vendor's default GL code if pattern detected.
        
        Args:
            vendor_id: Vendor UUID
            old_gl_code: Previous GL code
            new_gl_code: Corrected GL code
            db: AsyncSession for database updates
        
        Returns:
            True if vendor was updated, False otherwise
        """
        from app.models import Vendor, LineItem as LineItemModel, Bill
        from app.models.bill import BillStatus
        
        try:
            # Get vendor
            vendor = await self._get_vendor(db, vendor_id, Vendor)
            if not vendor:
                return False
            
            # Count how many times this GL code appears for this vendor
            count_result = await db.execute(
                select(func.count())
                .select_from(LineItemModel)
                .join(Bill, LineItemModel.bill_id == Bill.id)
                .where(
                    Bill.vendor_id == vendor_id,
                    Bill.status == BillStatus.APPROVED,
                    LineItemModel.gl_code == new_gl_code,
                )
            )
            count = count_result.scalar() or 0
            
            # If this GL code is used >= 3 times, set it as default
            if count >= 3:
                vendor.default_gl_code = new_gl_code
                await db.commit()
                logger.info(f"Updated vendor {vendor.name} default_gl_code to {new_gl_code}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error learning from correction: {e}")
            return False
    
    def get_available_gl_codes(self) -> Dict[str, str]:
        """Get all available GL codes and their names."""
        return GL_CODE_NAMES.copy()
