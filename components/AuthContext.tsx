/**
 * BillAgent Pro - Auth Context Provider
 * =======================================
 * React context for authentication state management.
 */

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { authService, AuthState, User, UserRole, LoginCredentials } from '../services/auth';

// Context type
interface AuthContextType {
    // State
    isAuthenticated: boolean;
    isLoading: boolean;
    user: User | null;
    role: UserRole | undefined;
    isSuperuser: boolean;

    // Actions
    login: (credentials: LoginCredentials) => Promise<void>;
    logout: () => Promise<void>;
    refreshToken: () => Promise<boolean>;

    // Permission checks
    hasRole: (role: UserRole) => boolean;
    hasAnyRole: (roles: UserRole[]) => boolean;
    canAccess: (requiredRoles: UserRole[]) => boolean;
}

// Create context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Provider props
interface AuthProviderProps {
    children: ReactNode;
}

/**
 * Auth Provider Component
 * 
 * Wraps the application and provides authentication state and methods
 * to all child components.
 */
export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
    const [authState, setAuthState] = useState<AuthState>(authService.getState());
    const [isLoading, setIsLoading] = useState(true);

    // Subscribe to auth state changes
    useEffect(() => {
        const unsubscribe = authService.subscribe((newState) => {
            setAuthState(newState);
        });

        // Initial auth check
        const checkAuth = async () => {
            try {
                await authService.getValidToken();
            } catch (error) {
                console.error('Auth check failed:', error);
            } finally {
                setIsLoading(false);
            }
        };

        checkAuth();

        return unsubscribe;
    }, []);

    // Login handler
    const login = useCallback(async (credentials: LoginCredentials) => {
        setIsLoading(true);
        try {
            await authService.login(credentials);
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Logout handler
    const logout = useCallback(async () => {
        setIsLoading(true);
        try {
            await authService.logout();
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Token refresh handler
    const refreshToken = useCallback(async () => {
        const result = await authService.refreshAccessToken();
        return result !== null;
    }, []);

    // Permission checks
    const hasRole = useCallback((role: UserRole) => {
        return authService.hasRole(role);
    }, []);

    const hasAnyRole = useCallback((roles: UserRole[]) => {
        return authService.hasAnyRole(roles);
    }, []);

    const canAccess = useCallback((requiredRoles: UserRole[]) => {
        if (!authState.user) return false;
        if (authState.user.is_superuser) return true;
        if (requiredRoles.length === 0) return true;
        return requiredRoles.includes(authState.user.role);
    }, [authState.user]);

    // Context value
    const value: AuthContextType = {
        isAuthenticated: authState.isAuthenticated,
        isLoading,
        user: authState.user,
        role: authState.user?.role,
        isSuperuser: authState.user?.is_superuser ?? false,
        login,
        logout,
        refreshToken,
        hasRole,
        hasAnyRole,
        canAccess,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};

/**
 * Hook to access auth context
 * 
 * @throws Error if used outside of AuthProvider
 */
export const useAuthContext = (): AuthContextType => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuthContext must be used within an AuthProvider');
    }
    return context;
};

/**
 * Hook for checking if user can perform an action
 * 
 * @param requiredRoles - Roles that can perform the action
 * @returns Object with canPerform boolean and reason
 */
export const usePermission = (requiredRoles: UserRole[]) => {
    const { isAuthenticated, user, canAccess } = useAuthContext();

    if (!isAuthenticated || !user) {
        return {
            canPerform: false,
            reason: 'Not authenticated'
        };
    }

    const hasAccess = canAccess(requiredRoles);

    return {
        canPerform: hasAccess,
        reason: hasAccess ? null : `Requires ${requiredRoles.join(' or ')} role`
    };
};

export default AuthProvider;
