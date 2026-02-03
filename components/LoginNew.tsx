/**
 * BillAgent Pro - Login Component
 * =================================
 * Authentication form with JWT login support.
 */

import React, { useState, useCallback, useEffect } from 'react';
import { authService, LoginCredentials } from '../services/auth';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';

interface LoginProps {
    onLoginSuccess?: () => void;
    redirectTo?: string;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess, redirectTo = '/dashboard' }) => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showPassword, setShowPassword] = useState(false);

    // Check if already authenticated
    useEffect(() => {
        if (authService.isAuthenticated()) {
            onLoginSuccess?.();
        }
    }, [onLoginSuccess]);

    const handleSubmit = useCallback(async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);

        try {
            const credentials: LoginCredentials = { email, password };
            await authService.login(credentials);
            onLoginSuccess?.();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Login failed. Please try again.');
        } finally {
            setIsLoading(false);
        }
    }, [email, password, onLoginSuccess]);

    const handleDemoLogin = useCallback(async (role: 'admin' | 'accountant' | 'viewer') => {
        setError(null);
        setIsLoading(true);

        const demoCredentials: Record<string, LoginCredentials> = {
            admin: { email: 'admin@billagent.pro', password: 'admin123456' },
            accountant: { email: 'accountant@billagent.pro', password: 'account123456' },
            viewer: { email: 'viewer@billagent.pro', password: 'viewer123456' }
        };

        try {
            await authService.login(demoCredentials[role]);
            onLoginSuccess?.();
        } catch (err) {
            setError(`Demo login failed. Please ensure the backend is running and demo users are seeded.`);
        } finally {
            setIsLoading(false);
        }
    }, [onLoginSuccess]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-4">
            <Card className="w-full max-w-md bg-gray-800 border-gray-700">
                <CardHeader className="space-y-1 text-center">
                    <div className="flex justify-center mb-4">
                        <div className="p-3 bg-green-600/20 rounded-full">
                            <svg
                                className="w-8 h-8 text-green-500"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                                />
                            </svg>
                        </div>
                    </div>
                    <CardTitle className="text-2xl font-bold text-white">
                        BillAgent Pro
                    </CardTitle>
                    <CardDescription className="text-gray-400">
                        Sign in to your account to continue
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit} className="space-y-4">
                        {/* Error Alert */}
                        {error && (
                            <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg">
                                <p className="text-sm text-red-400">{error}</p>
                            </div>
                        )}

                        {/* Email Input */}
                        <div className="space-y-2">
                            <label htmlFor="email" className="text-sm font-medium text-gray-300">
                                Email
                            </label>
                            <Input
                                id="email"
                                type="email"
                                placeholder="you@example.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                disabled={isLoading}
                                className="bg-gray-700 border-gray-600 text-white placeholder:text-gray-400"
                            />
                        </div>

                        {/* Password Input */}
                        <div className="space-y-2">
                            <label htmlFor="password" className="text-sm font-medium text-gray-300">
                                Password
                            </label>
                            <div className="relative">
                                <Input
                                    id="password"
                                    type={showPassword ? 'text' : 'password'}
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                    disabled={isLoading}
                                    className="bg-gray-700 border-gray-600 text-white placeholder:text-gray-400 pr-10"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-300"
                                >
                                    {showPassword ? (
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                                        </svg>
                                    ) : (
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                        </svg>
                                    )}
                                </button>
                            </div>
                        </div>

                        {/* Submit Button */}
                        <Button
                            type="submit"
                            disabled={isLoading || !email || !password}
                            className="w-full bg-green-600 hover:bg-green-700 text-white"
                        >
                            {isLoading ? (
                                <div className="flex items-center justify-center">
                                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                    Signing in...
                                </div>
                            ) : (
                                'Sign In'
                            )}
                        </Button>
                    </form>

                    {/* Demo Login Options */}
                    <div className="mt-6 pt-6 border-t border-gray-700">
                        <p className="text-sm text-gray-400 text-center mb-3">
                            Or try a demo account
                        </p>
                        <div className="grid grid-cols-3 gap-2">
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={() => handleDemoLogin('admin')}
                                disabled={isLoading}
                                className="text-xs border-gray-600 text-gray-300 hover:bg-gray-700"
                            >
                                Admin
                            </Button>
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={() => handleDemoLogin('accountant')}
                                disabled={isLoading}
                                className="text-xs border-gray-600 text-gray-300 hover:bg-gray-700"
                            >
                                Accountant
                            </Button>
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={() => handleDemoLogin('viewer')}
                                disabled={isLoading}
                                className="text-xs border-gray-600 text-gray-300 hover:bg-gray-700"
                            >
                                Viewer
                            </Button>
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="mt-6 text-center">
                        <p className="text-xs text-gray-500">
                            Secure authentication powered by JWT
                        </p>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

export default Login;
