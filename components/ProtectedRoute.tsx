/**
 * BillAgent Pro - Protected Route Component
 * ==========================================
 * Wrapper component for routes that require authentication and/or specific roles.
 */

import React, { useEffect, useState } from 'react';
import { authService, UserRole, AuthState } from '../services/auth';
import Login from './LoginNew';

interface ProtectedRouteProps {
    children: React.ReactNode;
    /** Required roles (user must have at least one) */
    requiredRoles?: UserRole[];
    /** If true, user must have ALL required roles */
    requireAllRoles?: boolean;
    /** Custom fallback component when unauthorized */
    fallback?: React.ReactNode;
    /** Custom component to show while checking auth */
    loadingComponent?: React.ReactNode;
    /** Callback when access is denied */
    onAccessDenied?: () => void;
}

/**
 * Loading Spinner Component
 */
const DefaultLoadingComponent: React.FC = () => (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-green-500 border-t-transparent mb-4" />
            <p className="text-gray-400">Checking authentication...</p>
        </div>
    </div>
);

/**
 * Access Denied Component
 */
interface AccessDeniedProps {
    userRole?: UserRole;
    requiredRoles?: UserRole[];
    onLogout: () => void;
}

const AccessDeniedComponent: React.FC<AccessDeniedProps> = ({
    userRole,
    requiredRoles,
    onLogout
}) => (
    <div className="min-h-screen flex items-center justify-center bg-gray-900 p-4">
        <div className="text-center max-w-md">
            <div className="p-4 bg-red-500/20 rounded-full w-16 h-16 mx-auto mb-6 flex items-center justify-center">
                <svg
                    className="w-8 h-8 text-red-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                </svg>
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Access Denied</h2>
            <p className="text-gray-400 mb-6">
                You don't have permission to access this page.
                {requiredRoles && requiredRoles.length > 0 && (
                    <span className="block mt-2 text-sm">
                        Required role: <span className="text-yellow-500">{requiredRoles.join(' or ')}</span>
                        <br />
                        Your role: <span className="text-green-500">{userRole || 'None'}</span>
                    </span>
                )}
            </p>
            <div className="space-x-4">
                <button
                    onClick={() => window.history.back()}
                    className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
                >
                    Go Back
                </button>
                <button
                    onClick={onLogout}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                >
                    Sign Out
                </button>
            </div>
        </div>
    </div>
);

/**
 * Protected Route Component
 * 
 * Wraps children components and ensures user is authenticated
 * and has the required roles before rendering.
 */
export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
    children,
    requiredRoles = [],
    requireAllRoles = false,
    fallback,
    loadingComponent,
    onAccessDenied
}) => {
    const [authState, setAuthState] = useState<AuthState>(authService.getState());
    const [isChecking, setIsChecking] = useState(true);

    // Subscribe to auth state changes
    useEffect(() => {
        const unsubscribe = authService.subscribe((newState) => {
            setAuthState(newState);
        });

        // Initial check
        const checkAuth = async () => {
            // Try to get a valid token (will refresh if needed)
            await authService.getValidToken();
            setIsChecking(false);
        };

        checkAuth();

        return unsubscribe;
    }, []);

    // Handle successful login
    const handleLoginSuccess = () => {
        setAuthState(authService.getState());
    };

    // Handle logout
    const handleLogout = async () => {
        await authService.logout();
        setAuthState(authService.getState());
    };

    // Show loading while checking auth
    if (isChecking) {
        return <>{loadingComponent || <DefaultLoadingComponent />}</>;
    }

    // Not authenticated - show login
    if (!authState.isAuthenticated || !authState.user) {
        return <Login onLoginSuccess={handleLoginSuccess} />;
    }

    // Check role-based access
    if (requiredRoles.length > 0) {
        const userRole = authState.user.role;
        const isSuperuser = authState.user.is_superuser;

        let hasAccess = false;

        if (isSuperuser) {
            // Superusers always have access
            hasAccess = true;
        } else if (requireAllRoles) {
            // Must have ALL roles
            hasAccess = requiredRoles.every(role => role === userRole);
        } else {
            // Must have at least one role
            hasAccess = requiredRoles.includes(userRole);
        }

        if (!hasAccess) {
            onAccessDenied?.();
            return (
                <>
                    {fallback || (
                        <AccessDeniedComponent
                            userRole={userRole}
                            requiredRoles={requiredRoles}
                            onLogout={handleLogout}
                        />
                    )}
                </>
            );
        }
    }

    // All checks passed - render children
    return <>{children}</>;
};

/**
 * Hook to get current auth state
 */
export const useAuth = () => {
    const [authState, setAuthState] = useState<AuthState>(authService.getState());

    useEffect(() => {
        const unsubscribe = authService.subscribe(setAuthState);
        return unsubscribe;
    }, []);

    return {
        isAuthenticated: authState.isAuthenticated,
        user: authState.user,
        role: authState.user?.role,
        isSuperuser: authState.user?.is_superuser ?? false,
        hasRole: (role: UserRole) => authService.hasRole(role),
        hasAnyRole: (roles: UserRole[]) => authService.hasAnyRole(roles),
        logout: () => authService.logout(),
        getAuthHeader: () => authService.getAuthHeader()
    };
};

/**
 * HOC to protect a component with authentication
 */
export function withAuth<P extends object>(
    WrappedComponent: React.ComponentType<P>,
    requiredRoles?: UserRole[]
) {
    return function AuthenticatedComponent(props: P) {
        return (
            <ProtectedRoute requiredRoles={requiredRoles}>
                <WrappedComponent {...props} />
            </ProtectedRoute>
        );
    };
}

export default ProtectedRoute;
