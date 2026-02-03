import React from 'react';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
    variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'confidence';
    size?: 'sm' | 'md' | 'lg';
    confidence?: number;
}

const variantStyles: Record<string, string> = {
    default: 'bg-white/10 text-white/70 border-white/10',
    success: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    warning: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    danger: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
    info: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    confidence: '', // Dynamic based on confidence value
};

const sizeStyles: Record<string, string> = {
    sm: 'px-2 py-0.5 text-[10px]',
    md: 'px-2.5 py-1 text-xs',
    lg: 'px-3 py-1.5 text-sm',
};

// Get variant based on confidence level
const getConfidenceVariant = (confidence: number): string => {
    if (confidence >= 85) return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
    if (confidence >= 70) return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
    return 'bg-rose-500/20 text-rose-400 border-rose-500/30';
};

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
    ({
        className = '',
        variant = 'default',
        size = 'md',
        confidence,
        children,
        ...props
    }, ref) => {
        const computedVariant = variant === 'confidence' && confidence !== undefined
            ? getConfidenceVariant(confidence)
            : variantStyles[variant];

        return (
            <span
                ref={ref}
                className={`
          inline-flex items-center justify-center
          font-bold uppercase tracking-wider
          rounded-full border
          ${computedVariant}
          ${sizeStyles[size]}
          ${className}
        `}
                {...props}
            >
                {children}
            </span>
        );
    }
);

Badge.displayName = 'Badge';

// Confidence Badge - specialized for displaying confidence scores
export interface ConfidenceBadgeProps extends Omit<BadgeProps, 'variant' | 'children'> {
    value: number;
    showIcon?: boolean;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
    value,
    showIcon = false,
    size = 'md',
    ...props
}) => {
    const getIcon = () => {
        if (!showIcon) return null;
        if (value >= 85) return '✓';
        if (value >= 70) return '!';
        return '✗';
    };

    return (
        <Badge
            variant="confidence"
            confidence={value}
            size={size}
            {...props}
        >
            {showIcon && <span className="mr-1">{getIcon()}</span>}
            {value}%
        </Badge>
    );
};

// Status Badge - specialized for bill status
export interface StatusBadgeProps extends Omit<BadgeProps, 'variant' | 'children'> {
    status: 'PROCESSING' | 'NEEDS_REVIEW' | 'APPROVED' | 'POSTED' | 'FAILED' | 'PENDING' | 'VERIFIED' | 'FLAGGED';
}

const statusConfig: Record<string, { variant: BadgeProps['variant']; label: string }> = {
    PROCESSING: { variant: 'info', label: 'Processing' },
    NEEDS_REVIEW: { variant: 'warning', label: 'Needs Review' },
    APPROVED: { variant: 'success', label: 'Approved' },
    POSTED: { variant: 'success', label: 'Posted' },
    FAILED: { variant: 'danger', label: 'Failed' },
    PENDING: { variant: 'warning', label: 'Pending' },
    VERIFIED: { variant: 'success', label: 'Verified' },
    FLAGGED: { variant: 'danger', label: 'Flagged' },
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({
    status,
    size = 'md',
    ...props
}) => {
    const config = statusConfig[status] || { variant: 'default', label: status };

    return (
        <Badge variant={config.variant} size={size} {...props}>
            {config.label}
        </Badge>
    );
};

export default Badge;
