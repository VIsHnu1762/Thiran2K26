import React, { useState, useCallback, useEffect } from 'react';
import {
    ArrowLeft,
    Loader2,
    AlertCircle,
    CheckCircle,
    RefreshCw,
    Columns,
    Maximize2,
    Minimize2,
} from 'lucide-react';
import { Button } from './ui/button';
import { Badge, StatusBadge } from './ui/badge';
import ImageViewer from './ImageViewer';
import BillForm from './BillForm';
import { Bill, Page } from '../types';
import { api } from '../services/api';

interface BillReviewProps {
    billId?: string;
    bill?: Bill;
    onNavigate: (page: Page) => void;
    onBillUpdate?: (bill: Bill) => void;
}

const BillReview: React.FC<BillReviewProps> = ({
    billId,
    bill: initialBill,
    onNavigate,
    onBillUpdate,
}) => {
    const [bill, setBill] = useState<Bill | null>(initialBill || null);
    const [isLoading, setIsLoading] = useState(!initialBill && !!billId);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedItemIndex, setSelectedItemIndex] = useState<number | null>(null);
    const [splitRatio, setSplitRatio] = useState(50); // Image panel percentage
    const [isFullscreenImage, setIsFullscreenImage] = useState(false);

    // Fetch bill data if not provided
    useEffect(() => {
        if (!initialBill && billId) {
            loadBill();
        }
    }, [billId, initialBill]);

    const loadBill = async () => {
        if (!billId) return;

        setIsLoading(true);
        setError(null);

        try {
            const response = await api.getBill(billId);
            if (response.success && response.data) {
                setBill(response.data);
            } else {
                setError(response.error || 'Failed to load bill');
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load bill');
        } finally {
            setIsLoading(false);
        }
    };

    // Handle bill update
    const handleBillUpdate = useCallback(async (updatedBill: Bill) => {
        setIsSaving(true);
        try {
            const response = await api.updateBill(updatedBill.id, updatedBill);
            if (response.success && response.data) {
                setBill(response.data);
                onBillUpdate?.(response.data);
            } else {
                setError(response.error || 'Failed to save changes');
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to save changes');
        } finally {
            setIsSaving(false);
        }
    }, [onBillUpdate]);

    // Handle approval
    const handleApprove = useCallback(async () => {
        if (!bill) return;

        setIsSaving(true);
        try {
            const approvedBill: Bill = {
                ...bill,
                status: 'APPROVED',
            };
            const response = await api.updateBill(bill.id, approvedBill);
            if (response.success && response.data) {
                setBill(response.data);
                onBillUpdate?.(response.data);
                // Navigate back after approval
                setTimeout(() => onNavigate(Page.History), 1000);
            } else {
                setError(response.error || 'Failed to approve bill');
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to approve bill');
        } finally {
            setIsSaving(false);
        }
    }, [bill, onBillUpdate, onNavigate]);

    // Handle rejection
    const handleReject = useCallback(async () => {
        if (!bill) return;

        setIsSaving(true);
        try {
            const rejectedBill: Bill = {
                ...bill,
                status: 'FAILED',
            };
            const response = await api.updateBill(bill.id, rejectedBill);
            if (response.success && response.data) {
                setBill(response.data);
                onBillUpdate?.(response.data);
                setTimeout(() => onNavigate(Page.History), 1000);
            } else {
                setError(response.error || 'Failed to reject bill');
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to reject bill');
        } finally {
            setIsSaving(false);
        }
    }, [bill, onBillUpdate, onNavigate]);

    // Handle item selection
    const handleItemSelect = useCallback((index: number | null) => {
        setSelectedItemIndex(index);
    }, []);

    // Toggle fullscreen image view
    const toggleFullscreenImage = useCallback(() => {
        setIsFullscreenImage(prev => !prev);
    }, []);

    // Loading state
    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center h-[calc(100vh-200px)]">
                <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
                <p className="text-white/70">Loading bill details...</p>
            </div>
        );
    }

    // Error state
    if (error && !bill) {
        return (
            <div className="flex flex-col items-center justify-center h-[calc(100vh-200px)]">
                <AlertCircle className="w-12 h-12 text-rose-500 mb-4" />
                <p className="text-white/70 mb-4">{error}</p>
                <div className="flex gap-3">
                    <Button variant="outline" onClick={() => onNavigate(Page.History)}>
                        <ArrowLeft size={16} className="mr-2" />
                        Go Back
                    </Button>
                    <Button variant="primary" onClick={loadBill}>
                        <RefreshCw size={16} className="mr-2" />
                        Retry
                    </Button>
                </div>
            </div>
        );
    }

    // No bill state
    if (!bill) {
        return (
            <div className="flex flex-col items-center justify-center h-[calc(100vh-200px)]">
                <AlertCircle className="w-12 h-12 text-amber-500 mb-4" />
                <p className="text-white/70 mb-4">No bill data available</p>
                <Button variant="outline" onClick={() => onNavigate(Page.History)}>
                    <ArrowLeft size={16} className="mr-2" />
                    Go Back
                </Button>
            </div>
        );
    }

    // Count items needing review
    const reviewCount = bill.items.filter(item => item.confidence < 85).length;

    return (
        <div className="h-[calc(100vh-120px)] flex flex-col animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 bg-white/5 border-b border-white/10">
                <div className="flex items-center gap-4">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => onNavigate(Page.History)}
                    >
                        <ArrowLeft size={20} />
                    </Button>
                    <div>
                        <h1 className="text-xl font-bold text-white/90 flex items-center gap-3">
                            Bill Review
                            <StatusBadge status={bill.status} />
                        </h1>
                        <p className="text-sm text-white/50">
                            {bill.vendorName || bill.vendor?.name || 'Unknown Vendor'} • {bill.invoiceNumber || bill.id}
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    {reviewCount > 0 && (
                        <Badge variant="warning">
                            <AlertCircle size={14} className="mr-1" />
                            {reviewCount} items need review
                        </Badge>
                    )}
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={toggleFullscreenImage}
                        title={isFullscreenImage ? 'Exit Fullscreen' : 'Fullscreen Image'}
                    >
                        {isFullscreenImage ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={loadBill}
                        title="Refresh"
                        disabled={isLoading}
                    >
                        <RefreshCw size={18} className={isLoading ? 'animate-spin' : ''} />
                    </Button>
                </div>
            </div>

            {/* Error banner */}
            {error && (
                <div className="mx-6 mt-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-center gap-2 text-rose-400 text-sm">
                    <AlertCircle size={16} />
                    {error}
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setError(null)}
                        className="ml-auto"
                    >
                        Dismiss
                    </Button>
                </div>
            )}

            {/* Split View */}
            <div className="flex-1 flex overflow-hidden">
                {/* Left Panel - Image Viewer */}
                <div
                    className={`
            border-r border-white/10 transition-all duration-300
            ${isFullscreenImage ? 'w-full' : ''}
          `}
                    style={{ width: isFullscreenImage ? '100%' : `${splitRatio}%` }}
                >
                    <ImageViewer
                        imageUrl={bill.imageUrl}
                        items={bill.items}
                        selectedItemIndex={selectedItemIndex}
                        onItemClick={handleItemSelect}
                        className="h-full"
                    />
                </div>

                {/* Resize Handle */}
                {!isFullscreenImage && (
                    <div
                        className="w-1 bg-white/10 hover:bg-blue-500/50 cursor-col-resize transition-colors"
                        onMouseDown={(e) => {
                            e.preventDefault();
                            const startX = e.clientX;
                            const startRatio = splitRatio;

                            const handleMouseMove = (moveEvent: MouseEvent) => {
                                const container = (e.target as HTMLElement).parentElement;
                                if (!container) return;

                                const containerWidth = container.offsetWidth;
                                const deltaX = moveEvent.clientX - startX;
                                const deltaRatio = (deltaX / containerWidth) * 100;
                                const newRatio = Math.min(Math.max(startRatio + deltaRatio, 30), 70);
                                setSplitRatio(newRatio);
                            };

                            const handleMouseUp = () => {
                                document.removeEventListener('mousemove', handleMouseMove);
                                document.removeEventListener('mouseup', handleMouseUp);
                            };

                            document.addEventListener('mousemove', handleMouseMove);
                            document.addEventListener('mouseup', handleMouseUp);
                        }}
                    />
                )}

                {/* Right Panel - Bill Form */}
                {!isFullscreenImage && (
                    <div
                        className="overflow-hidden"
                        style={{ width: `${100 - splitRatio}%` }}
                    >
                        <BillForm
                            bill={bill}
                            onUpdate={handleBillUpdate}
                            onApprove={handleApprove}
                            onReject={handleReject}
                            selectedItemIndex={selectedItemIndex}
                            onItemSelect={handleItemSelect}
                            isLoading={isSaving}
                            className="h-full"
                        />
                    </div>
                )}
            </div>

            {/* Quick Actions Footer (for fullscreen mode) */}
            {isFullscreenImage && (
                <div className="flex items-center justify-center gap-3 p-4 bg-white/5 border-t border-white/10">
                    <Button
                        variant="outline"
                        onClick={toggleFullscreenImage}
                    >
                        <Columns size={16} className="mr-2" />
                        Show Form
                    </Button>
                    <Button
                        variant="success"
                        onClick={handleApprove}
                        isLoading={isSaving}
                    >
                        <CheckCircle size={16} className="mr-2" />
                        Approve Bill
                    </Button>
                </div>
            )}
        </div>
    );
};

export default BillReview;
