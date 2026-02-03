import React, { useRef, useState, useCallback, useEffect } from 'react';
import {
    ZoomIn,
    ZoomOut,
    RotateCw,
    Maximize2,
    Move,
    Download,
    RefreshCcw
} from 'lucide-react';
import { Button } from './ui/button';
import { BoundingBox, BillItem } from '../types';

interface ImageViewerProps {
    imageUrl: string;
    items: BillItem[];
    selectedItemIndex?: number | null;
    onItemClick?: (index: number) => void;
    className?: string;
}

const ImageViewer: React.FC<ImageViewerProps> = ({
    imageUrl,
    items,
    selectedItemIndex,
    onItemClick,
    className = '',
}) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const imageRef = useRef<HTMLImageElement>(null);

    const [scale, setScale] = useState(1);
    const [rotation, setRotation] = useState(0);
    const [position, setPosition] = useState({ x: 0, y: 0 });
    const [isDragging, setIsDragging] = useState(false);
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
    const [imageLoaded, setImageLoaded] = useState(false);
    const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });

    // Reset view
    const resetView = useCallback(() => {
        setScale(1);
        setRotation(0);
        setPosition({ x: 0, y: 0 });
    }, []);

    // Zoom controls
    const zoomIn = useCallback(() => {
        setScale(prev => Math.min(prev + 0.25, 4));
    }, []);

    const zoomOut = useCallback(() => {
        setScale(prev => Math.max(prev - 0.25, 0.5));
    }, []);

    // Rotate control
    const rotate = useCallback(() => {
        setRotation(prev => (prev + 90) % 360);
    }, []);

    // Handle mouse wheel zoom
    const handleWheel = useCallback((e: React.WheelEvent) => {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        setScale(prev => Math.min(Math.max(prev + delta, 0.5), 4));
    }, []);

    // Pan handling
    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        if (e.button === 0) {
            setIsDragging(true);
            setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
        }
    }, [position]);

    const handleMouseMove = useCallback((e: React.MouseEvent) => {
        if (isDragging) {
            setPosition({
                x: e.clientX - dragStart.x,
                y: e.clientY - dragStart.y,
            });
        }
    }, [isDragging, dragStart]);

    const handleMouseUp = useCallback(() => {
        setIsDragging(false);
    }, []);

    // Zoom to bounding box
    const zoomToBoundingBox = useCallback((box: BoundingBox) => {
        if (!containerRef.current || !imageRef.current) return;

        const container = containerRef.current.getBoundingClientRect();
        const imgWidth = imageDimensions.width;
        const imgHeight = imageDimensions.height;

        // Calculate the center of the bounding box in image coordinates
        const boxCenterX = box.x + box.width / 2;
        const boxCenterY = box.y + box.height / 2;

        // Calculate scale to fit the bounding box with padding
        const padding = 50;
        const scaleX = (container.width - padding * 2) / box.width;
        const scaleY = (container.height - padding * 2) / box.height;
        const newScale = Math.min(Math.max(Math.min(scaleX, scaleY), 1), 3);

        // Calculate position to center the bounding box
        const newX = (container.width / 2) - (boxCenterX * newScale);
        const newY = (container.height / 2) - (boxCenterY * newScale);

        setScale(newScale);
        setPosition({ x: newX, y: newY });
    }, [imageDimensions]);

    // Effect to zoom to selected item
    useEffect(() => {
        if (selectedItemIndex !== null && selectedItemIndex !== undefined) {
            const item = items[selectedItemIndex];
            if (item?.boundingBox) {
                zoomToBoundingBox(item.boundingBox);
            }
        }
    }, [selectedItemIndex, items, zoomToBoundingBox]);

    // Handle image load
    const handleImageLoad = useCallback(() => {
        if (imageRef.current) {
            setImageDimensions({
                width: imageRef.current.naturalWidth,
                height: imageRef.current.naturalHeight,
            });
            setImageLoaded(true);
        }
    }, []);

    // Get confidence color for bounding box
    const getConfidenceColor = (confidence: number): string => {
        if (confidence >= 85) return 'rgba(34, 197, 94, 0.6)'; // green
        if (confidence >= 70) return 'rgba(234, 179, 8, 0.6)'; // yellow
        return 'rgba(239, 68, 68, 0.6)'; // red
    };

    // Download image
    const downloadImage = useCallback(() => {
        const link = document.createElement('a');
        link.href = imageUrl;
        link.download = 'bill-image.png';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }, [imageUrl]);

    return (
        <div className={`flex flex-col h-full ${className}`}>
            {/* Toolbar */}
            <div className="flex items-center justify-between p-3 bg-white/5 border-b border-white/10">
                <div className="flex items-center gap-2">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={zoomOut}
                        title="Zoom Out"
                    >
                        <ZoomOut size={18} />
                    </Button>
                    <span className="text-sm font-medium text-white/70 w-14 text-center">
                        {Math.round(scale * 100)}%
                    </span>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={zoomIn}
                        title="Zoom In"
                    >
                        <ZoomIn size={18} />
                    </Button>
                    <div className="w-px h-6 bg-white/10 mx-2" />
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={rotate}
                        title="Rotate"
                    >
                        <RotateCw size={18} />
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={resetView}
                        title="Reset View"
                    >
                        <RefreshCcw size={18} />
                    </Button>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={downloadImage}
                        title="Download"
                    >
                        <Download size={18} />
                    </Button>
                </div>
            </div>

            {/* Image Container */}
            <div
                ref={containerRef}
                className="flex-1 relative overflow-hidden bg-black/20 cursor-move"
                onWheel={handleWheel}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
            >
                <div
                    className="absolute transition-transform duration-200 ease-out"
                    style={{
                        transform: `translate(${position.x}px, ${position.y}px) scale(${scale}) rotate(${rotation}deg)`,
                        transformOrigin: 'top left',
                    }}
                >
                    {/* Bill Image */}
                    <img
                        ref={imageRef}
                        src={imageUrl}
                        alt="Bill"
                        className="max-w-none select-none"
                        draggable={false}
                        onLoad={handleImageLoad}
                    />

                    {/* Bounding Box Overlays */}
                    {imageLoaded && items.map((item, index) => {
                        if (!item.boundingBox) return null;
                        const box = item.boundingBox;
                        const isSelected = selectedItemIndex === index;
                        const isLowConfidence = item.confidence < 85;

                        return (
                            <div
                                key={index}
                                className={`
                  absolute border-2 cursor-pointer
                  transition-all duration-200
                  ${isSelected
                                        ? 'border-blue-400 shadow-lg shadow-blue-500/50 z-10'
                                        : isLowConfidence
                                            ? 'border-rose-400/70 hover:border-rose-400'
                                            : 'border-emerald-400/50 hover:border-emerald-400'
                                    }
                `}
                                style={{
                                    left: box.x,
                                    top: box.y,
                                    width: box.width,
                                    height: box.height,
                                    backgroundColor: isSelected
                                        ? 'rgba(59, 130, 246, 0.15)'
                                        : 'transparent',
                                }}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onItemClick?.(index);
                                }}
                                title={`${item.name} - ${item.confidence}% confidence`}
                            >
                                {/* Confidence indicator */}
                                <div
                                    className={`
                    absolute -top-6 left-0 text-[10px] font-bold px-1.5 py-0.5 rounded
                    ${item.confidence >= 85
                                            ? 'bg-emerald-500/80 text-white'
                                            : item.confidence >= 70
                                                ? 'bg-amber-500/80 text-white'
                                                : 'bg-rose-500/80 text-white'
                                        }
                  `}
                                >
                                    {item.confidence}%
                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* Drag hint */}
                {!isDragging && (
                    <div className="absolute bottom-3 right-3 flex items-center gap-2 px-3 py-1.5 bg-black/50 rounded-lg text-xs text-white/50">
                        <Move size={14} />
                        Drag to pan • Scroll to zoom
                    </div>
                )}
            </div>

            {/* Legend */}
            <div className="flex items-center gap-4 p-3 bg-white/5 border-t border-white/10 text-xs">
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded bg-emerald-500/50 border border-emerald-400" />
                    <span className="text-white/50">High confidence (≥85%)</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded bg-amber-500/50 border border-amber-400" />
                    <span className="text-white/50">Medium (70-84%)</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded bg-rose-500/50 border border-rose-400" />
                    <span className="text-white/50">Low (&lt;70%)</span>
                </div>
            </div>
        </div>
    );
};

export default ImageViewer;
