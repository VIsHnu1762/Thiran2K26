import React from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    label?: string;
    error?: string;
    hint?: string;
    leftIcon?: React.ReactNode;
    rightIcon?: React.ReactNode;
    confidence?: number;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
    ({
        className = '',
        label,
        error,
        hint,
        leftIcon,
        rightIcon,
        confidence,
        id,
        ...props
    }, ref) => {
        const inputId = id || label?.toLowerCase().replace(/\s/g, '-');
        const hasLowConfidence = confidence !== undefined && confidence < 85;

        return (
            <div className="w-full">
                {label && (
                    <label
                        htmlFor={inputId}
                        className="block text-sm font-medium text-white/70 mb-1.5"
                    >
                        {label}
                        {confidence !== undefined && (
                            <span
                                className={`ml-2 text-xs font-semibold px-2 py-0.5 rounded-full ${confidence >= 85
                                        ? 'bg-emerald-500/20 text-emerald-400'
                                        : confidence >= 70
                                            ? 'bg-amber-500/20 text-amber-400'
                                            : 'bg-rose-500/20 text-rose-400'
                                    }`}
                            >
                                {confidence}%
                            </span>
                        )}
                    </label>
                )}
                <div className="relative">
                    {leftIcon && (
                        <div className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40">
                            {leftIcon}
                        </div>
                    )}
                    <input
                        ref={ref}
                        id={inputId}
                        className={`
              w-full px-4 py-2.5 
              bg-white/5 border rounded-xl
              text-white placeholder-white/30
              transition-all duration-200
              focus:outline-none focus:ring-2 focus:ring-blue-500/50
              ${leftIcon ? 'pl-10' : ''}
              ${rightIcon ? 'pr-10' : ''}
              ${error
                                ? 'border-rose-500/50 focus:border-rose-500'
                                : hasLowConfidence
                                    ? 'border-rose-500/50 bg-rose-500/5'
                                    : 'border-white/10 hover:border-white/20 focus:border-blue-500/50'
                            }
              ${className}
            `}
                        {...props}
                    />
                    {rightIcon && (
                        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40">
                            {rightIcon}
                        </div>
                    )}
                </div>
                {error && (
                    <p className="mt-1 text-xs text-rose-400">{error}</p>
                )}
                {hint && !error && (
                    <p className="mt-1 text-xs text-white/40">{hint}</p>
                )}
            </div>
        );
    }
);

Input.displayName = 'Input';

export default Input;
