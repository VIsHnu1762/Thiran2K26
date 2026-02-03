"""
BillAgent Pro - Auditor Agent
==============================
Agent 2: Validates bill data with strict mathematical checks.
Implements all validation rules from SPEC with Decimal precision.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Severity level for validation issues."""
    ERROR = "error"
    WARNING = "warning"


@dataclass
class ValidationError:
    """A single validation error or warning."""
    field: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    rule: Optional[str] = None  # Which rule triggered this error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "field": self.field,
            "message": self.message,
            "severity": self.severity.value,
            "expected_value": str(self.expected_value) if self.expected_value is not None else None,
            "actual_value": str(self.actual_value) if self.actual_value is not None else None,
            "rule": self.rule,
        }


@dataclass
class ValidationResult:
    """Result of bill validation."""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    suggested_status: str = "APPROVED"
    validation_summary: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_valid": self.is_valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "suggested_status": self.suggested_status,
            "validation_summary": self.validation_summary,
        }
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


class AuditorAgent:
    """
    Agent 2: Auditor Agent
    
    Validates bill data with strict mathematical checks:
    - Rule 1: Line items sum check (sum of line totals = subtotal)
    - Rule 2: Grand total check (subtotal + tax = total)
    - Rule 3: Date validation (reasonable dates, due date >= invoice date)
    - Rule 4: Line item math (qty × unit_price = line_total)
    
    All monetary calculations use Decimal for precision.
    """
    
    # Tolerance for monetary comparisons (1 cent)
    TOLERANCE = Decimal("0.01")
    
    # Maximum days in the past for invoice date
    MAX_PAST_DAYS = 365 * 2  # 2 years
    
    # Maximum days in the future for invoice date
    MAX_FUTURE_DAYS = 7
    
    # Maximum days for due date after invoice date
    MAX_DUE_DATE_DAYS = 180  # 6 months
    
    def __init__(self, tolerance: Decimal = Decimal("0.01")):
        """
        Initialize the Auditor Agent.
        
        Args:
            tolerance: Tolerance for monetary comparisons (default: 0.01)
        """
        self.TOLERANCE = tolerance
        logger.info(f"AuditorAgent initialized with tolerance: {self.TOLERANCE}")
    
    def validate(
        self,
        bill_data: Dict[str, Any],
        line_items: Optional[List[Dict[str, Any]]] = None
    ) -> ValidationResult:
        """
        Validate a bill's data.
        
        Args:
            bill_data: Dictionary containing bill fields:
                - subtotal: Decimal or str
                - tax_amount: Decimal or str
                - total_amount: Decimal or str
                - invoice_date: date or str
                - due_date: date or str (optional)
            line_items: List of line item dictionaries:
                - quantity: Decimal or str
                - unit_price: Decimal or str
                - total_price: Decimal or str
                - description: str
        
        Returns:
            ValidationResult with errors, warnings, and suggested status
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        
        logger.info("Starting bill validation...")
        
        # Extract and convert bill data to Decimal
        subtotal = self._to_decimal(bill_data.get("subtotal"))
        tax_amount = self._to_decimal(bill_data.get("tax_amount")) or Decimal("0.00")
        total_amount = self._to_decimal(bill_data.get("total_amount"))
        invoice_date = self._to_date(bill_data.get("invoice_date"))
        due_date = self._to_date(bill_data.get("due_date"))
        
        # Use line_items from bill_data if not provided separately
        if line_items is None:
            line_items = bill_data.get("line_items", [])
        
        # =====================================================================
        # Rule 1: Line Items Sum Check
        # Sum of all line item totals should equal subtotal
        # =====================================================================
        if line_items and subtotal is not None:
            rule1_result = self._validate_line_items_sum(line_items, subtotal)
            errors.extend(rule1_result.get("errors", []))
            warnings.extend(rule1_result.get("warnings", []))
        elif subtotal is not None and not line_items:
            # No line items but subtotal exists - just a warning
            warnings.append(ValidationError(
                field="line_items",
                message="No line items found to validate against subtotal",
                severity=ValidationSeverity.WARNING,
                rule="RULE_1_LINE_ITEMS_SUM"
            ))
        
        # =====================================================================
        # Rule 2: Subtotal + Tax = Total
        # Grand total should equal subtotal + tax_amount
        # =====================================================================
        if subtotal is not None and total_amount is not None:
            rule2_result = self._validate_grand_total(subtotal, tax_amount, total_amount)
            errors.extend(rule2_result.get("errors", []))
            warnings.extend(rule2_result.get("warnings", []))
        elif total_amount is None:
            errors.append(ValidationError(
                field="total_amount",
                message="Total amount is missing",
                severity=ValidationSeverity.ERROR,
                rule="RULE_2_GRAND_TOTAL"
            ))
        
        # =====================================================================
        # Rule 3: Date Validation
        # - Invoice date should be reasonable (not too far in past/future)
        # - Due date should be >= invoice date
        # =====================================================================
        rule3_result = self._validate_dates(invoice_date, due_date)
        errors.extend(rule3_result.get("errors", []))
        warnings.extend(rule3_result.get("warnings", []))
        
        # =====================================================================
        # Rule 4: Line Item Math
        # For each line item: quantity × unit_price = total_price
        # =====================================================================
        if line_items:
            rule4_result = self._validate_line_item_math(line_items)
            errors.extend(rule4_result.get("errors", []))
            warnings.extend(rule4_result.get("warnings", []))
        
        # =====================================================================
        # Determine suggested status
        # =====================================================================
        is_valid = len(errors) == 0
        
        if is_valid and len(warnings) == 0:
            suggested_status = "APPROVED"
        elif is_valid and len(warnings) > 0:
            suggested_status = "APPROVED"  # Warnings don't block approval
        else:
            suggested_status = "NEEDS_REVIEW"
        
        # Build validation summary
        validation_summary = {
            "total_errors": len(errors),
            "total_warnings": len(warnings),
            "rules_checked": ["RULE_1_LINE_ITEMS_SUM", "RULE_2_GRAND_TOTAL", 
                             "RULE_3_DATE_VALIDATION", "RULE_4_LINE_ITEM_MATH"],
            "rules_failed": list(set(e.rule for e in errors if e.rule)),
        }
        
        logger.info(
            f"Validation complete: valid={is_valid}, "
            f"errors={len(errors)}, warnings={len(warnings)}, "
            f"suggested_status={suggested_status}"
        )
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggested_status=suggested_status,
            validation_summary=validation_summary,
        )
    
    def _validate_line_items_sum(
        self,
        line_items: List[Dict[str, Any]],
        subtotal: Decimal
    ) -> Dict[str, List[ValidationError]]:
        """
        Rule 1: Validate that sum of line item totals equals subtotal.
        
        Returns:
            Dictionary with 'errors' and 'warnings' lists
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        
        calculated_sum = Decimal("0.00")
        
        for idx, item in enumerate(line_items):
            line_total = self._to_decimal(item.get("total_price"))
            if line_total is not None:
                calculated_sum += line_total
            else:
                warnings.append(ValidationError(
                    field=f"line_items[{idx}].total_price",
                    message=f"Line item {idx + 1} is missing total_price",
                    severity=ValidationSeverity.WARNING,
                    rule="RULE_1_LINE_ITEMS_SUM"
                ))
        
        # Compare with tolerance
        difference = abs(calculated_sum - subtotal)
        
        if difference > self.TOLERANCE:
            errors.append(ValidationError(
                field="subtotal",
                message=f"Sum of line items ({calculated_sum:.2f}) does not match subtotal ({subtotal:.2f}). Difference: {difference:.2f}",
                severity=ValidationSeverity.ERROR,
                expected_value=subtotal,
                actual_value=calculated_sum,
                rule="RULE_1_LINE_ITEMS_SUM"
            ))
        
        logger.debug(f"Rule 1: Line items sum = {calculated_sum}, Subtotal = {subtotal}, Diff = {difference}")
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_grand_total(
        self,
        subtotal: Decimal,
        tax_amount: Decimal,
        total_amount: Decimal
    ) -> Dict[str, List[ValidationError]]:
        """
        Rule 2: Validate that subtotal + tax = total.
        
        Returns:
            Dictionary with 'errors' and 'warnings' lists
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        
        calculated_total = subtotal + tax_amount
        difference = abs(calculated_total - total_amount)
        
        if difference > self.TOLERANCE:
            errors.append(ValidationError(
                field="total_amount",
                message=f"Subtotal ({subtotal:.2f}) + Tax ({tax_amount:.2f}) = {calculated_total:.2f}, but total is {total_amount:.2f}. Difference: {difference:.2f}",
                severity=ValidationSeverity.ERROR,
                expected_value=calculated_total,
                actual_value=total_amount,
                rule="RULE_2_GRAND_TOTAL"
            ))
        
        logger.debug(f"Rule 2: {subtotal} + {tax_amount} = {calculated_total}, Total = {total_amount}, Diff = {difference}")
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_dates(
        self,
        invoice_date: Optional[date],
        due_date: Optional[date]
    ) -> Dict[str, List[ValidationError]]:
        """
        Rule 3: Validate invoice and due dates.
        
        Returns:
            Dictionary with 'errors' and 'warnings' lists
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        today = date.today()
        
        # Check invoice date
        if invoice_date is None:
            warnings.append(ValidationError(
                field="invoice_date",
                message="Invoice date is missing",
                severity=ValidationSeverity.WARNING,
                rule="RULE_3_DATE_VALIDATION"
            ))
        else:
            # Check if invoice date is too far in the past
            days_ago = (today - invoice_date).days
            if days_ago > self.MAX_PAST_DAYS:
                errors.append(ValidationError(
                    field="invoice_date",
                    message=f"Invoice date ({invoice_date}) is more than {self.MAX_PAST_DAYS} days in the past",
                    severity=ValidationSeverity.ERROR,
                    expected_value=f"Within last {self.MAX_PAST_DAYS} days",
                    actual_value=str(invoice_date),
                    rule="RULE_3_DATE_VALIDATION"
                ))
            
            # Check if invoice date is in the future
            days_ahead = (invoice_date - today).days
            if days_ahead > self.MAX_FUTURE_DAYS:
                errors.append(ValidationError(
                    field="invoice_date",
                    message=f"Invoice date ({invoice_date}) is more than {self.MAX_FUTURE_DAYS} days in the future",
                    severity=ValidationSeverity.ERROR,
                    expected_value=f"Within next {self.MAX_FUTURE_DAYS} days",
                    actual_value=str(invoice_date),
                    rule="RULE_3_DATE_VALIDATION"
                ))
        
        # Check due date
        if due_date is not None and invoice_date is not None:
            # Due date should be >= invoice date
            if due_date < invoice_date:
                errors.append(ValidationError(
                    field="due_date",
                    message=f"Due date ({due_date}) is before invoice date ({invoice_date})",
                    severity=ValidationSeverity.ERROR,
                    expected_value=f">= {invoice_date}",
                    actual_value=str(due_date),
                    rule="RULE_3_DATE_VALIDATION"
                ))
            
            # Due date shouldn't be too far in the future
            days_until_due = (due_date - invoice_date).days
            if days_until_due > self.MAX_DUE_DATE_DAYS:
                warnings.append(ValidationError(
                    field="due_date",
                    message=f"Due date ({due_date}) is {days_until_due} days after invoice date",
                    severity=ValidationSeverity.WARNING,
                    expected_value=f"Within {self.MAX_DUE_DATE_DAYS} days of invoice",
                    actual_value=str(due_date),
                    rule="RULE_3_DATE_VALIDATION"
                ))
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_line_item_math(
        self,
        line_items: List[Dict[str, Any]]
    ) -> Dict[str, List[ValidationError]]:
        """
        Rule 4: Validate line item math (qty × unit_price = total).
        
        Returns:
            Dictionary with 'errors' and 'warnings' lists
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        
        for idx, item in enumerate(line_items):
            description = item.get("description", f"Item {idx + 1}")[:50]
            quantity = self._to_decimal(item.get("quantity"))
            unit_price = self._to_decimal(item.get("unit_price"))
            total_price = self._to_decimal(item.get("total_price"))
            
            # Skip if we don't have all three values
            if quantity is None or unit_price is None or total_price is None:
                if total_price is None:
                    warnings.append(ValidationError(
                        field=f"line_items[{idx}].total_price",
                        message=f"Line item '{description}' is missing total_price",
                        severity=ValidationSeverity.WARNING,
                        rule="RULE_4_LINE_ITEM_MATH"
                    ))
                continue
            
            # Calculate expected total
            calculated_total = quantity * unit_price
            difference = abs(calculated_total - total_price)
            
            if difference > self.TOLERANCE:
                errors.append(ValidationError(
                    field=f"line_items[{idx}].total_price",
                    message=f"Line item '{description}': {quantity} × {unit_price:.2f} = {calculated_total:.2f}, but total is {total_price:.2f}",
                    severity=ValidationSeverity.ERROR,
                    expected_value=calculated_total,
                    actual_value=total_price,
                    rule="RULE_4_LINE_ITEM_MATH"
                ))
        
        return {"errors": errors, "warnings": warnings}
    
    def _to_decimal(self, value: Any) -> Optional[Decimal]:
        """
        Safely convert a value to Decimal.
        
        Args:
            value: Value to convert (str, int, float, Decimal, or None)
        
        Returns:
            Decimal value or None if conversion fails
        """
        if value is None:
            return None
        
        if isinstance(value, Decimal):
            return value
        
        try:
            if isinstance(value, float):
                # Convert float to string first to avoid precision issues
                return Decimal(str(value))
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as e:
            logger.warning(f"Could not convert {value} to Decimal: {e}")
            return None
    
    def _to_date(self, value: Any) -> Optional[date]:
        """
        Safely convert a value to date.
        
        Args:
            value: Value to convert (date, datetime, str, or None)
        
        Returns:
            date value or None if conversion fails
        """
        if value is None:
            return None
        
        if isinstance(value, date):
            return value
        
        try:
            from datetime import datetime
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, str):
                # Try ISO format first
                return date.fromisoformat(value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not convert {value} to date: {e}")
            return None


# Alias for backward compatibility
ErrorDetectionAgent = AuditorAgent
