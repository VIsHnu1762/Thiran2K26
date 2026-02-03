/**
 * BillAgent Pro - Authentication Service
 * =======================================
 * Handles JWT token management, storage, and refresh logic.
 */

// Types
export interface User {
    id: string;
    email: string;
    full_name: string | null;
    role: UserRole;
    is_active: boolean;
    is_superuser: boolean;
    created_at: string;
    updated_at: string;
    last_login: string | null;
}

export enum UserRole {
    VIEWER = 'viewer',
    ACCOUNTANT = 'accountant',
    APPROVER = 'approver',
    ADMIN = 'admin'
}

export interface LoginCredentials {
    email: string;
    password: string;
}

export interface LoginResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
    user: User;
}

export interface TokenResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
}

export interface AuthState {
    isAuthenticated: boolean;
    user: User | null;
    accessToken: string | null;
    refreshToken: string | null;
    tokenExpiry: number | null;
}

// Constants
const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';
const AUTH_STORAGE_KEY = 'billagent_auth';
const TOKEN_REFRESH_THRESHOLD = 5 * 60 * 1000; // Refresh 5 minutes before expiry

// =============================================================================
// Token Storage
// =============================================================================

interface StoredAuth {
    accessToken: string;
    refreshToken: string;
    tokenExpiry: number;
    user: User;
}

/**
 * Store authentication data in localStorage
 */
function storeAuth(data: StoredAuth): void {
    try {
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(data));
    } catch (error) {
        console.error('Failed to store auth data:', error);
    }
}

/**
 * Retrieve authentication data from localStorage
 */
function getStoredAuth(): StoredAuth | null {
    try {
        const stored = localStorage.getItem(AUTH_STORAGE_KEY);
        if (stored) {
            return JSON.parse(stored);
        }
    } catch (error) {
        console.error('Failed to retrieve auth data:', error);
        localStorage.removeItem(AUTH_STORAGE_KEY);
    }
    return null;
}

/**
 * Clear authentication data from localStorage
 */
function clearAuth(): void {
    localStorage.removeItem(AUTH_STORAGE_KEY);
}

// =============================================================================
// Token Validation
// =============================================================================

/**
 * Check if the access token is expired or about to expire
 */
function isTokenExpired(expiry: number): boolean {
    return Date.now() >= expiry - TOKEN_REFRESH_THRESHOLD;
}

/**
 * Parse JWT token to extract payload (without verification)
 */
function parseJwtPayload(token: string): Record<string, any> | null {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(
            atob(base64)
                .split('')
                .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                .join('')
        );
        return JSON.parse(jsonPayload);
    } catch {
        return null;
    }
}

// =============================================================================
// Auth Service Class
// =============================================================================

class AuthService {
    private state: AuthState;
    private refreshPromise: Promise<TokenResponse | null> | null = null;
    private listeners: Set<(state: AuthState) => void> = new Set();

    constructor() {
        this.state = this.loadInitialState();
    }

    /**
     * Load initial state from localStorage
     */
    private loadInitialState(): AuthState {
        const stored = getStoredAuth();

        if (stored && !isTokenExpired(stored.tokenExpiry)) {
            return {
                isAuthenticated: true,
                user: stored.user,
                accessToken: stored.accessToken,
                refreshToken: stored.refreshToken,
                tokenExpiry: stored.tokenExpiry
            };
        }

        // Clear invalid stored auth
        if (stored) {
            clearAuth();
        }

        return {
            isAuthenticated: false,
            user: null,
            accessToken: null,
            refreshToken: null,
            tokenExpiry: null
        };
    }

    /**
     * Get current auth state
     */
    getState(): AuthState {
        return { ...this.state };
    }

    /**
     * Subscribe to auth state changes
     */
    subscribe(listener: (state: AuthState) => void): () => void {
        this.listeners.add(listener);
        return () => this.listeners.delete(listener);
    }

    /**
     * Notify all listeners of state change
     */
    private notifyListeners(): void {
        this.listeners.forEach(listener => listener(this.getState()));
    }

    /**
     * Update state and persist to storage
     */
    private setState(newState: Partial<AuthState>): void {
        this.state = { ...this.state, ...newState };

        if (this.state.isAuthenticated && this.state.accessToken && this.state.refreshToken && this.state.user && this.state.tokenExpiry) {
            storeAuth({
                accessToken: this.state.accessToken,
                refreshToken: this.state.refreshToken,
                tokenExpiry: this.state.tokenExpiry,
                user: this.state.user
            });
        }

        this.notifyListeners();
    }

    /**
     * Login with email and password
     */
    async login(credentials: LoginCredentials): Promise<LoginResponse> {
        const response = await fetch(`${API_BASE_URL}/api/v1/auth/login/json`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(credentials)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Login failed');
        }

        const data: LoginResponse = await response.json();

        // Calculate token expiry
        const tokenExpiry = Date.now() + data.expires_in * 1000;

        this.setState({
            isAuthenticated: true,
            user: data.user,
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
            tokenExpiry
        });

        return data;
    }

    /**
     * Logout and clear all auth data
     */
    async logout(): Promise<void> {
        // Optionally call logout endpoint
        try {
            if (this.state.accessToken) {
                await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${this.state.accessToken}`
                    }
                });
            }
        } catch {
            // Ignore logout endpoint errors
        }

        clearAuth();
        this.state = {
            isAuthenticated: false,
            user: null,
            accessToken: null,
            refreshToken: null,
            tokenExpiry: null
        };
        this.notifyListeners();
    }

    /**
     * Refresh the access token
     */
    async refreshAccessToken(): Promise<TokenResponse | null> {
        // If already refreshing, return existing promise
        if (this.refreshPromise) {
            return this.refreshPromise;
        }

        if (!this.state.refreshToken) {
            this.logout();
            return null;
        }

        this.refreshPromise = (async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        refresh_token: this.state.refreshToken
                    })
                });

                if (!response.ok) {
                    throw new Error('Token refresh failed');
                }

                const data: TokenResponse = await response.json();
                const tokenExpiry = Date.now() + data.expires_in * 1000;

                this.setState({
                    accessToken: data.access_token,
                    refreshToken: data.refresh_token,
                    tokenExpiry
                });

                return data;
            } catch (error) {
                console.error('Token refresh failed:', error);
                await this.logout();
                return null;
            } finally {
                this.refreshPromise = null;
            }
        })();

        return this.refreshPromise;
    }

    /**
     * Get a valid access token, refreshing if necessary
     */
    async getValidToken(): Promise<string | null> {
        if (!this.state.isAuthenticated || !this.state.accessToken) {
            return null;
        }

        // Check if token needs refresh
        if (this.state.tokenExpiry && isTokenExpired(this.state.tokenExpiry)) {
            const refreshed = await this.refreshAccessToken();
            if (!refreshed) {
                return null;
            }
        }

        return this.state.accessToken;
    }

    /**
     * Get authorization header for API requests
     */
    async getAuthHeader(): Promise<Record<string, string>> {
        const token = await this.getValidToken();
        if (token) {
            return { 'Authorization': `Bearer ${token}` };
        }
        return {};
    }

    /**
     * Check if user has a specific role
     */
    hasRole(role: UserRole): boolean {
        if (!this.state.user) return false;

        // Superuser has all roles
        if (this.state.user.is_superuser) return true;

        // Check specific role
        return this.state.user.role === role;
    }

    /**
     * Check if user has any of the specified roles
     */
    hasAnyRole(roles: UserRole[]): boolean {
        if (!this.state.user) return false;
        if (this.state.user.is_superuser) return true;
        return roles.includes(this.state.user.role);
    }

    /**
     * Get current user
     */
    getCurrentUser(): User | null {
        return this.state.user;
    }

    /**
     * Check if authenticated
     */
    isAuthenticated(): boolean {
        return this.state.isAuthenticated;
    }
}

// Create singleton instance
export const authService = new AuthService();

// =============================================================================
// API Request Helpers
// =============================================================================

/**
 * Create authenticated fetch wrapper
 */
export async function authenticatedFetch(
    url: string,
    options: RequestInit = {}
): Promise<Response> {
    const authHeader = await authService.getAuthHeader();

    const response = await fetch(url, {
        ...options,
        headers: {
            ...options.headers,
            ...authHeader
        }
    });

    // Handle 401 Unauthorized
    if (response.status === 401) {
        // Try to refresh token
        const refreshed = await authService.refreshAccessToken();
        if (refreshed) {
            // Retry request with new token
            const newAuthHeader = await authService.getAuthHeader();
            return fetch(url, {
                ...options,
                headers: {
                    ...options.headers,
                    ...newAuthHeader
                }
            });
        }

        // Refresh failed, redirect to login
        window.location.href = '/login';
    }

    return response;
}

export default authService;
