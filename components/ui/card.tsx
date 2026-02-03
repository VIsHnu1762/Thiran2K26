import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
    variant?: 'default' | 'glass' | 'matte' | 'elevated';
    padding?: 'none' | 'sm' | 'md' | 'lg';
    hoverable?: boolean;
}

const variantStyles: Record<string, string> = {
    default: 'bg-white/5 border border-white/10',
    glass: 'glass-card',
    matte: 'matte-card',
    elevated: 'bg-white/5 border border-white/10 shadow-xl shadow-black/20',
};

const paddingStyles: Record<string, string> = {
    none: 'p-0',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
};

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
    ({
        className = '',
        variant = 'default',
        padding = 'md',
        hoverable = false,
        children,
        ...props
    }, ref) => {
        return (
            <div
                ref={ref}
                className={`
          rounded-2xl transition-all duration-300
          ${variantStyles[variant]}
          ${paddingStyles[padding]}
          ${hoverable ? 'hover:scale-[1.02] hover:shadow-lg cursor-pointer' : ''}
          ${className}
        `}
                {...props}
            >
                {children}
            </div>
        );
    }
);

Card.displayName = 'Card';

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> { }

export const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
    ({ className = '', children, ...props }, ref) => (
        <div
            ref={ref}
            className={`flex flex-col space-y-1.5 ${className}`}
            {...props}
        >
            {children}
        </div>
    )
);

CardHeader.displayName = 'CardHeader';

export interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> { }

export const CardTitle = React.forwardRef<HTMLHeadingElement, CardTitleProps>(
    ({ className = '', children, ...props }, ref) => (
        <h3
            ref={ref}
            className={`text-lg font-bold text-white/90 tracking-tight ${className}`}
            {...props}
        >
            {children}
        </h3>
    )
);

CardTitle.displayName = 'CardTitle';

export interface CardDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> { }

export const CardDescription = React.forwardRef<HTMLParagraphElement, CardDescriptionProps>(
    ({ className = '', children, ...props }, ref) => (
        <p
            ref={ref}
            className={`text-sm text-white/50 ${className}`}
            {...props}
        >
            {children}
        </p>
    )
);

CardDescription.displayName = 'CardDescription';

export interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> { }

export const CardContent = React.forwardRef<HTMLDivElement, CardContentProps>(
    ({ className = '', children, ...props }, ref) => (
        <div
            ref={ref}
            className={`${className}`}
            {...props}
        >
            {children}
        </div>
    )
);

CardContent.displayName = 'CardContent';

export interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> { }

export const CardFooter = React.forwardRef<HTMLDivElement, CardFooterProps>(
    ({ className = '', children, ...props }, ref) => (
        <div
            ref={ref}
            className={`flex items-center ${className}`}
            {...props}
        >
            {children}
        </div>
    )
);

CardFooter.displayName = 'CardFooter';

export default Card;
