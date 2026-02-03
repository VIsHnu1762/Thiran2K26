"""
BillAgent Pro - GL Code Repository
===================================
Database operations for GL Code entities.
"""

from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import GLCode


class GLCodeRepository:
    """Repository for GL Code database operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_code(self, code: str) -> Optional[GLCode]:
        """Get a GL code by its code."""
        result = await self.db.execute(
            select(GLCode).where(GLCode.code == code)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, active_only: bool = True) -> List[GLCode]:
        """Get all GL codes."""
        query = select(GLCode)
        if active_only:
            query = query.where(GLCode.is_active == True)
        query = query.order_by(GLCode.code)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_category(self, category: str) -> List[GLCode]:
        """Get GL codes by category."""
        result = await self.db.execute(
            select(GLCode)
            .where(GLCode.category == category, GLCode.is_active == True)
            .order_by(GLCode.code)
        )
        return list(result.scalars().all())
    
    async def create(self, gl_code: GLCode) -> GLCode:
        """Create a new GL code."""
        self.db.add(gl_code)
        await self.db.commit()
        await self.db.refresh(gl_code)
        return gl_code
    
    async def update(self, gl_code: GLCode) -> GLCode:
        """Update a GL code."""
        await self.db.commit()
        await self.db.refresh(gl_code)
        return gl_code
    
    async def delete(self, code: str) -> bool:
        """Delete a GL code (soft delete by deactivating)."""
        gl_code = await self.get_by_code(code)
        if not gl_code:
            return False
        
        gl_code.is_active = False
        await self.db.commit()
        return True
    
    async def search_by_keyword(self, keyword: str) -> List[Tuple[GLCode, float]]:
        """Search GL codes by keyword matching.
        
        Returns list of (GLCode, confidence) tuples.
        """
        all_codes = await self.get_all(active_only=True)
        matches = []
        
        keyword_lower = keyword.lower()
        
        for gl_code in all_codes:
            # Check keywords
            if gl_code.keywords:
                for kw in gl_code.keywords:
                    if kw.lower() in keyword_lower or keyword_lower in kw.lower():
                        matches.append((gl_code, 0.9))
                        break
            
            # Check name
            if gl_code.name and keyword_lower in gl_code.name.lower():
                if (gl_code, 0.9) not in matches:
                    matches.append((gl_code, 0.7))
            
            # Check category
            if gl_code.category and keyword_lower in gl_code.category.lower():
                if gl_code not in [m[0] for m in matches]:
                    matches.append((gl_code, 0.5))
        
        # Sort by confidence
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
    
    async def find_best_match(self, description: str) -> Optional[Tuple[GLCode, float]]:
        """Find the best matching GL code for a line item description.
        
        Returns (GLCode, confidence) or None if no match.
        """
        matches = await self.search_by_keyword(description)
        
        if matches:
            return matches[0]
        return None
    
    async def seed_default_codes(self) -> int:
        """Seed the database with default GL codes.
        
        Returns number of codes created.
        """
        from ..models.gl_code import DEFAULT_GL_CODES
        
        created = 0
        for code_data in DEFAULT_GL_CODES:
            existing = await self.get_by_code(code_data["code"])
            if not existing:
                gl_code = GLCode(**code_data)
                self.db.add(gl_code)
                created += 1
        
        if created > 0:
            await self.db.commit()
        
        return created
    
    async def get_categories(self) -> List[str]:
        """Get all unique categories."""
        result = await self.db.execute(
            select(GLCode.category)
            .where(GLCode.is_active == True, GLCode.category.isnot(None))
            .distinct()
            .order_by(GLCode.category)
        )
        return [row[0] for row in result if row[0]]
