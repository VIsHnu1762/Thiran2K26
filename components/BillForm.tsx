import React, { useState, useCallback } from 'react';
import {
    Save,
    CheckCircle,
    AlertTriangle,
    Edit2,
    X,
    Plus,
    Trash2,
    RefreshCw,
    ChevronDown,
    ChevronUp,
} from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge, ConfidenceBadge, StatusBadge } from './ui/badge';
import { Bill, BillItem, ValidationError, Vendor } from '../types';

interface BillFormProps {
    bill: Bill;
    onUpdate: (bill: Bill) => void;
    onApprove: () => void;
    onReject?: () => void;
    selectedItemIndex?: number | null;
    onItemSelect?: (index: number | null) => void;
    isLoading?: boolean;
    className?: string;
}

const BillForm: React.FC<BillFormProps> = ({
    bill,
    onUpdate,
    onApprove,
    onReject,
    selectedItemIndex,
    onItemSelect,
    isLoading = false,
    className = '',
}) => {
    const [isEditing, setIsEditing] = useState(false);
    const [editedBill, setEditedBill] = useState<Bill>(bill);
    const [expandedSections, setExpandedSections] = useState({
        vendor: true,
        items: true,
        summary: true,
        validation: true,
    });

    // Toggle section expansion
    const toggleSection = (section: keyof typeof expandedSections) => {
        setExpandedSections(prev => ({
            ...prev,
            [section]: !prev[section],
        }));
    };

    // Calculate if any fields need review
    const needsReview = bill.items.some(item => item.confidence < 85);
    const criticalIssues = bill.validationErrors?.filter(e => e.severity === 'error').length || 0;

    // Handle field updates
    const handleFieldChange = useCallback((field: keyof Bill, value: any) => {
        setEditedBill(prev => ({
            ...prev,
            [field]: value,
        }));
    }, []);

    // Handle vendor updates
    const handleVendorChange = useCallback((field: keyof Vendor, value: string) => {
        setEditedBill(prev => ({
            ...prev,
            vendor: {
                ...prev.vendor,
                id: prev.vendor?.id || 'new',
                name: prev.vendor?.name || '',
                [field]: value,
            } as Vendor,
        }));
    }, []);

    // Handle item updates
    const handleItemChange = useCallback((index: number, field: keyof BillItem, value: any) => {
        setEditedBill(prev => {
            const newItems = [...prev.items];
            newItems[index] = {
                ...newItems[index],
                [field]: value,
                isVerified: true,
            };

            // Recalculate total if quantity or price changed
            if (field === 'quantity' || field === 'price' || field === 'unitPrice') {
                const item = newItems[index];
                item.total = (item.quantity || 1) * (item.price || item.unitPrice || 0);
            }

            // Recalculate grand total
            const grandTotal = newItems.reduce((sum, item) => sum + (item.total || 0), 0);

            return {
                ...prev,
                items: newItems,
                grandTotal,
            };
        });
    }, []);

    // Mark item as verified
    const verifyItem = useCallback((index: number) => {
        handleItemChange(index, 'isVerified', true);
        handleItemChange(index, 'confidence', 100);
    }, [handleItemChange]);

    // Add new item
    const addItem = useCallback(() => {
        setEditedBill(prev => ({
            ...prev,
            items: [
                ...prev.items,
                {
                    id: `new-${Date.now()}`,
                    name: '',
                    quantity: 1,
                    price: 0,
                    total: 0,
                    confidence: 100,
                    isVerified: true,
                },
            ],
        }));
    }, []);

    // Remove item
    const removeItem = useCallback((index: number) => {
        setEditedBill(prev => {
            const newItems = prev.items.filter((_, i) => i !== index);
            const grandTotal = newItems.reduce((sum, item) => sum + (item.total || 0), 0);
            return {
                ...prev,
                items: newItems,
                grandTotal,
            };
        });
    }, []);

    // Save changes
    const saveChanges = useCallback(() => {
        onUpdate(editedBill);
        setIsEditing(false);
    }, [editedBill, onUpdate]);

    // Cancel editing
    const cancelEditing = useCallback(() => {
        setEditedBill(bill);
        setIsEditing(false);
    }, [bill]);

    // Section Header Component
    const SectionHeader: React.FC<{
        title: string;
        section: keyof typeof expandedSections;
        badge?: React.ReactNode;
    }> = ({ title, section, badge }) => (
        <div
            className="flex items-center justify-between cursor-pointer py-2"
            onClick={() => toggleSection(section)}
        >
            <div className="flex items-center gap-2">
                <span className="font-semibold text-white/90">{title}</span>
                {badge}
            </div>
            {expandedSections[section] ? (
                <ChevronUp size={18} className="text-white/50" />
            ) : (
                <ChevronDown size={18} className="text-white/50" />
            )}
        </div>
    );

    return (
        <div className={`flex flex-col h-full ${className}`}>
            {/* Header */}
            <div className="flex items-center justify-between p-4 bg-white/5 border-b border-white/10">
                <div>
                    <h2 className="text-lg font-bold text-white/90">Bill Details</h2>
                    <p className="text-sm text-white/50">
                        Invoice #{bill.invoiceNumber || bill.id}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <StatusBadge status={bill.status} />
                    {needsReview && (
                        <Badge variant="warning" size="sm">
                            <AlertTriangle size={12} className="mr-1" />
                            Review Required
                        </Badge>
                    )}
                </div>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {/* Validation Errors */}
                {bill.validationErrors && bill.validationErrors.length > 0 && (
                    <Card variant="default" padding="sm" className="border-rose-500/30 bg-rose-500/5">
                        <SectionHeader
                            title="Validation Issues"
                            section="validation"
                            badge={<Badge variant="danger" size="sm">{bill.validationErrors.length}</Badge>}
                        />
                        {expandedSections.validation && (
                            <div className="space-y-2 mt-2">
                                {bill.validationErrors.map((error, index) => (
                                    <div
                                        key={index}
                                        className={`
                      flex items-start gap-2 p-2 rounded-lg text-sm
                      ${error.severity === 'error'
                                                ? 'bg-rose-500/10 text-rose-400'
                                                : 'bg-amber-500/10 text-amber-400'
                                            }
                    `}
                                    >
                                        <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" />
                                        <div>
                                            <span className="font-medium">{error.field}:</span> {error.message}
                                            {error.suggestedValue && (
                                                <span className="block text-xs mt-1 opacity-70">
                                                    Suggested: {error.suggestedValue}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </Card>
                )}

                {/* Vendor Information */}
                <Card variant="default" padding="sm">
                    <SectionHeader title="Vendor Information" section="vendor" />
                    {expandedSections.vendor && (
                        <div className="grid grid-cols-2 gap-3 mt-2">
                            <Input
                                label="Vendor Name"
                                value={isEditing ? editedBill.vendor?.name || editedBill.vendorName : bill.vendor?.name || bill.vendorName}
                                onChange={(e) => isEditing && handleVendorChange('name', e.target.value)}
                                disabled={!isEditing}
                            />
                            <Input
                                label="Invoice Number"
                                value={isEditing ? editedBill.invoiceNumber : bill.invoiceNumber}
                                onChange={(e) => isEditing && handleFieldChange('invoiceNumber', e.target.value)}
                                disabled={!isEditing}
                            />
                            <Input
                                label="Invoice Date"
                                type="date"
                                value={isEditing ? editedBill.invoiceDate || editedBill.date : bill.invoiceDate || bill.date}
                                onChange={(e) => isEditing && handleFieldChange('invoiceDate', e.target.value)}
                                disabled={!isEditing}
                            />
                            <Input
                                label="Due Date"
                                type="date"
                                value={isEditing ? editedBill.dueDate : bill.dueDate}
                                onChange={(e) => isEditing && handleFieldChange('dueDate', e.target.value)}
                                disabled={!isEditing}
                            />
                        </div>
                    )}
                </Card>

                {/* Line Items */}
                <Card variant="default" padding="sm">
                    <SectionHeader
                        title="Line Items"
                        section="items"
                        badge={
                            <span className="text-xs text-white/50">
                                {bill.items.length} items
                            </span>
                        }
                    />
                    {expandedSections.items && (
                        <div className="space-y-3 mt-2">
                            {(isEditing ? editedBill.items : bill.items).map((item, index) => {
                                const isSelected = selectedItemIndex === index;
                                const isLowConfidence = item.confidence < 85;

                                return (
                                    <div
                                        key={item.id || index}
                                        className={`
                      p-3 rounded-xl border transition-all cursor-pointer
                      ${isSelected
                                                ? 'border-blue-500/50 bg-blue-500/10'
                                                : isLowConfidence
                                                    ? 'border-rose-500/30 bg-rose-500/5'
                                                    : 'border-white/10 bg-white/5 hover:border-white/20'
                                            }
                    `}
                                        onClick={() => onItemSelect?.(isSelected ? null : index)}
                                    >
                                        <div className="flex items-start justify-between mb-2">
                                            <div className="flex items-center gap-2">
                                                <span className="text-xs text-white/40">#{index + 1}</span>
                                                <ConfidenceBadge value={item.confidence} size="sm" showIcon />
                                                {item.isVerified && (
                                                    <Badge variant="success" size="sm">
                                                        <CheckCircle size={10} className="mr-1" />
                                                        Verified
                                                    </Badge>
                                                )}
                                            </div>
                                            {isEditing && (
                                                <div className="flex items-center gap-1">
                                                    <Button
                                                        variant="ghost"
                                                        size="icon"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            verifyItem(index);
                                                        }}
                                                        title="Mark as Verified"
                                                    >
                                                        <CheckCircle size={14} />
                                                    </Button>
                                                    <Button
                                                        variant="ghost"
                                                        size="icon"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            removeItem(index);
                                                        }}
                                                        title="Remove Item"
                                                    >
                                                        <Trash2 size={14} />
                                                    </Button>
                                                </div>
                                            )}
                                        </div>

                                        <div className="grid grid-cols-12 gap-2">
                                            <div className="col-span-5">
                                                <Input
                                                    label="Description"
                                                    value={item.name}
                                                    onChange={(e) => isEditing && handleItemChange(index, 'name', e.target.value)}
                                                    disabled={!isEditing}
                                                    confidence={item.confidence}
                                                />
                                            </div>
                                            <div className="col-span-2">
                                                <Input
                                                    label="Qty"
                                                    type="number"
                                                    value={item.quantity}
                                                    onChange={(e) => isEditing && handleItemChange(index, 'quantity', parseFloat(e.target.value) || 0)}
                                                    disabled={!isEditing}
                                                />
                                            </div>
                                            <div className="col-span-2">
                                                <Input
                                                    label="Price"
                                                    type="number"
                                                    step="0.01"
                                                    value={item.price}
                                                    onChange={(e) => isEditing && handleItemChange(index, 'price', parseFloat(e.target.value) || 0)}
                                                    disabled={!isEditing}
                                                />
                                            </div>
                                            <div className="col-span-3">
                                                <Input
                                                    label="Total"
                                                    type="number"
                                                    step="0.01"
                                                    value={item.total.toFixed(2)}
                                                    disabled
                                                />
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}

                            {isEditing && (
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={addItem}
                                    className="w-full"
                                >
                                    <Plus size={16} className="mr-2" />
                                    Add Line Item
                                </Button>
                            )}
                        </div>
                    )}
                </Card>

                {/* Summary */}
                <Card variant="default" padding="sm">
                    <SectionHeader title="Summary" section="summary" />
                    {expandedSections.summary && (
                        <div className="space-y-3 mt-2">
                            <div className="flex justify-between items-center py-2 border-b border-white/10">
                                <span className="text-white/70">Subtotal</span>
                                <span className="font-medium text-white/90">
                                    ₹{(isEditing ? editedBill.grandTotal : bill.grandTotal).toFixed(2)}
                                </span>
                            </div>
                            <div className="flex justify-between items-center py-2 border-b border-white/10">
                                <span className="text-white/70">Tax (if applicable)</span>
                                <span className="font-medium text-white/50">—</span>
                            </div>
                            <div className="flex justify-between items-center py-2">
                                <span className="text-lg font-bold text-white/90">Grand Total</span>
                                <span className="text-lg font-bold text-white">
                                    ₹{(isEditing ? editedBill.grandTotal : bill.grandTotal).toFixed(2)}
                                </span>
                            </div>
                            <div className="flex justify-between items-center py-2 border-t border-white/10">
                                <span className="text-white/70">Overall Confidence</span>
                                <ConfidenceBadge value={bill.overallConfidence} showIcon />
                            </div>
                        </div>
                    )}
                </Card>

                {/* Notes */}
                <Card variant="default" padding="sm">
                    <Input
                        label="Notes"
                        value={isEditing ? editedBill.notes : bill.notes}
                        onChange={(e) => isEditing && handleFieldChange('notes', e.target.value)}
                        disabled={!isEditing}
                        hint="Add any additional notes about this bill"
                    />
                </Card>
            </div>

            {/* Footer Actions */}
            <div className="flex items-center justify-between p-4 bg-white/5 border-t border-white/10">
                {isEditing ? (
                    <>
                        <Button variant="ghost" onClick={cancelEditing}>
                            <X size={16} className="mr-2" />
                            Cancel
                        </Button>
                        <div className="flex items-center gap-2">
                            <Button variant="primary" onClick={saveChanges} isLoading={isLoading}>
                                <Save size={16} className="mr-2" />
                                Save Changes
                            </Button>
                        </div>
                    </>
                ) : (
                    <>
                        <Button variant="outline" onClick={() => setIsEditing(true)}>
                            <Edit2 size={16} className="mr-2" />
                            Edit
                        </Button>
                        <div className="flex items-center gap-2">
                            {onReject && (
                                <Button variant="danger" onClick={onReject} isLoading={isLoading}>
                                    <X size={16} className="mr-2" />
                                    Reject
                                </Button>
                            )}
                            <Button
                                variant="success"
                                onClick={onApprove}
                                isLoading={isLoading}
                                disabled={criticalIssues > 0}
                            >
                                <CheckCircle size={16} className="mr-2" />
                                Approve
                            </Button>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default BillForm;
