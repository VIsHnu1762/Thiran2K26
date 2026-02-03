import { Bill, TaskStatus, ApiResponse, PaginatedResponse, BillFilters } from '../types';
import { authService } from './auth';

// API Configuration
const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';
const API_TIMEOUT = 30000; // 30 seconds

// Create axios-like fetch wrapper with timeout and retry
class ApiClient {
    private baseUrl: string;
    private timeout: number;
    private maxRetries: number;
    private retryDelay: number;

    constructor(baseUrl: string, timeout = API_TIMEOUT) {
        this.baseUrl = baseUrl;
        this.timeout = timeout;
        this.maxRetries = 3;
        this.retryDelay = 1000;
    }

    private async getAuthHeaders(): Promise<Record<string, string>> {
        return await authService.getAuthHeader();
    }

    private async fetchWithTimeout(
        url: string,
        options: RequestInit = {}
    ): Promise<Response> {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        // Get auth headers
        const authHeaders = await this.getAuthHeaders();

        // Determine if this is a file upload (FormData)
        const isFileUpload = options.body instanceof FormData;

        try {
            const headers: Record<string, string> = {
                ...authHeaders,
                ...options.headers,
            };
            
            // Only set Content-Type for JSON requests, not file uploads
            if (!isFileUpload && !options.headers?.['Content-Type']) {
                headers['Content-Type'] = 'application/json';
            }

            const response = await fetch(url, {
                ...options,
                signal: controller.signal,
                headers,
            });

            // Handle 401 - try to refresh token
            if (response.status === 401) {
                const refreshed = await authService.refreshAccessToken();
                if (refreshed) {
                    // Retry with new token
                    const newAuthHeaders = await this.getAuthHeaders();
                    return await fetch(url, {
                        ...options,
                        signal: controller.signal,
                        headers: {
                            'Content-Type': 'application/json',
                            ...newAuthHeaders,
                            ...options.headers,
                        },
                    });
                }
            }

            return response;
        } finally {
            clearTimeout(timeoutId);
        }
    }

    private async retryFetch(
        url: string,
        options: RequestInit = {},
        retries = this.maxRetries
    ): Promise<Response> {
        for (let attempt = 0; attempt <= retries; attempt++) {
            try {
                const response = await this.fetchWithTimeout(url, options);

                // Don't retry on client errors (4xx)
                if (response.status >= 400 && response.status < 500) {
                    return response;
                }

                // Retry on server errors (5xx)
                if (!response.ok && attempt < retries) {
                    await new Promise(resolve =>
                        setTimeout(resolve, this.retryDelay * Math.pow(2, attempt))
                    );
                    continue;
                }

                return response;
            } catch (error) {
                if (attempt === retries) {
                    throw error;
                }
                await new Promise(resolve =>
                    setTimeout(resolve, this.retryDelay * Math.pow(2, attempt))
                );
            }
        }
        throw new Error('Max retries exceeded');
    }

    async get<T>(endpoint: string): Promise<ApiResponse<T>> {
        try {
            const response = await this.retryFetch(`${this.baseUrl}${endpoint}`);
            const data = await response.json();

            if (!response.ok) {
                return {
                    success: false,
                    error: data.detail || data.message || 'Request failed',
                };
            }

            return {
                success: true,
                data,
            };
        } catch (error) {
            return {
                success: false,
                error: error instanceof Error ? error.message : 'Network error',
            };
        }
    }

    async post<T>(endpoint: string, body: unknown): Promise<ApiResponse<T>> {
        try {
            const response = await this.retryFetch(`${this.baseUrl}${endpoint}`, {
                method: 'POST',
                body: JSON.stringify(body),
            });
            const data = await response.json();

            if (!response.ok) {
                return {
                    success: false,
                    error: data.detail || data.message || 'Request failed',
                };
            }

            return {
                success: true,
                data,
            };
        } catch (error) {
            return {
                success: false,
                error: error instanceof Error ? error.message : 'Network error',
            };
        }
    }

    async put<T>(endpoint: string, body: unknown): Promise<ApiResponse<T>> {
        try {
            const response = await this.retryFetch(`${this.baseUrl}${endpoint}`, {
                method: 'PUT',
                body: JSON.stringify(body),
            });
            const data = await response.json();

            if (!response.ok) {
                return {
                    success: false,
                    error: data.detail || data.message || 'Request failed',
                };
            }

            return {
                success: true,
                data,
            };
        } catch (error) {
            return {
                success: false,
                error: error instanceof Error ? error.message : 'Network error',
            };
        }
    }

    async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
        try {
            const response = await this.retryFetch(`${this.baseUrl}${endpoint}`, {
                method: 'DELETE',
            });

            if (response.status === 204) {
                return { success: true };
            }

            const data = await response.json();

            if (!response.ok) {
                return {
                    success: false,
                    error: data.detail || data.message || 'Request failed',
                };
            }

            return {
                success: true,
                data,
            };
        } catch (error) {
            return {
                success: false,
                error: error instanceof Error ? error.message : 'Network error',
            };
        }
    }

    async uploadFile<T>(
        endpoint: string,
        file: File,
        additionalData?: Record<string, string>
    ): Promise<ApiResponse<T>> {
        try {
            const formData = new FormData();
            formData.append('file', file);

            if (additionalData) {
                Object.entries(additionalData).forEach(([key, value]) => {
                    formData.append(key, value);
                });
            }

            // Get auth headers but don't include Content-Type (browser will set it for FormData)
            const authHeaders = await this.getAuthHeaders();
            
            const response = await this.fetchWithTimeout(`${this.baseUrl}${endpoint}`, {
                method: 'POST',
                body: formData,
                headers: {
                    ...authHeaders,
                    // Don't set Content-Type - let browser handle it for multipart/form-data
                },
            });

            const data = await response.json();

            if (!response.ok) {
                return {
                    success: false,
                    error: data.detail || data.message || 'Upload failed',
                };
            }

            return {
                success: true,
                data,
            };
        } catch (error) {
            return {
                success: false,
                error: error instanceof Error ? error.message : 'Network error',
            };
        }
    }
}

// Create API client instance
const client = new ApiClient(API_BASE_URL);

// API Methods
export const api = {
    // Bill Operations
    async uploadBill(file: File): Promise<ApiResponse<{ taskId: string }>> {
        return client.uploadFile('/api/v1/bills/upload', file);
    },

    // Synchronous bill analysis (for dev/demo without Celery)
    async analyzeBillSync(file: File): Promise<ApiResponse<any>> {
        return client.uploadFile('/api/v1/bills/analyze-sync', file);
    },

    async getTaskStatus(taskId: string): Promise<ApiResponse<TaskStatus>> {
        return client.get(`/api/v1/tasks/${taskId}`);
    },

    async getBill(billId: string): Promise<ApiResponse<Bill>> {
        return client.get(`/api/v1/bills/${billId}`);
    },

    async getBills(
        filters?: BillFilters,
        page = 1,
        pageSize = 20
    ): Promise<ApiResponse<PaginatedResponse<Bill>>> {
        const params = new URLSearchParams({
            page: page.toString(),
            page_size: pageSize.toString(),
        });

        if (filters) {
            if (filters.status?.length) {
                filters.status.forEach(s => params.append('status', s));
            }
            if (filters.vendorId) params.append('vendor_id', filters.vendorId);
            if (filters.invoiceNumber) params.append('invoice_number', filters.invoiceNumber);
            if (filters.dateFrom) params.append('date_from', filters.dateFrom);
            if (filters.dateTo) params.append('date_to', filters.dateTo);
            if (filters.minAmount) params.append('min_amount', filters.minAmount.toString());
            if (filters.maxAmount) params.append('max_amount', filters.maxAmount.toString());
            if (filters.searchQuery) params.append('search', filters.searchQuery);
        }

        return client.get(`/api/v1/bills?${params.toString()}`);
    },

    async updateBill(billId: string, bill: Partial<Bill>): Promise<ApiResponse<Bill>> {
        return client.put(`/api/v1/bills/${billId}`, bill);
    },

    async deleteBill(billId: string): Promise<ApiResponse<void>> {
        return client.delete(`/api/v1/bills/${billId}`);
    },

    async approveBill(billId: string): Promise<ApiResponse<Bill>> {
        return client.post(`/api/v1/bills/${billId}/approve`, {});
    },

    async rejectBill(billId: string, reason?: string): Promise<ApiResponse<Bill>> {
        return client.post(`/api/v1/bills/${billId}/reject`, { reason });
    },

    // Vendor Operations
    async getVendors(): Promise<ApiResponse<{ id: string; name: string }[]>> {
        return client.get('/api/v1/vendors');
    },

    // Stats
    async getDashboardStats(): Promise<ApiResponse<{
        totalProcessed: number;
        pendingReviewCount: number;
        processingCount: number;
        approvedToday: number;
        errorRate: number;
        accuracyTrend: number;
    }>> {
        return client.get('/api/v1/stats/dashboard');
    },

    // Health check
    async healthCheck(): Promise<ApiResponse<{ status: string }>> {
        return client.get('/health');
    },
};

// Polling Hook - Custom hook for polling task status
export function usePolling(
    taskId: string | null,
    onComplete: (bill: Bill) => void,
    onError: (error: string) => void,
    options: {
        interval?: number;
        maxAttempts?: number;
    } = {}
) {
    const { interval = 2000, maxAttempts = 60 } = options;
    const [status, setStatus] = React.useState<TaskStatus | null>(null);
    const [isPolling, setIsPolling] = React.useState(false);
    const attemptRef = React.useRef(0);
    const intervalRef = React.useRef<ReturnType<typeof setInterval> | null>(null);
    const startPolling = React.useCallback(() => {
        if (!taskId) return;

        setIsPolling(true);
        attemptRef.current = 0;

        const poll = async () => {
            try {
                const response = await api.getTaskStatus(taskId);

                if (!response.success) {
                    throw new Error(response.error || 'Failed to get task status');
                }

                const taskStatus = response.data!;
                setStatus(taskStatus);

                if (taskStatus.status === 'COMPLETED' && taskStatus.result) {
                    stopPolling();
                    onComplete(taskStatus.result);
                } else if (taskStatus.status === 'FAILED') {
                    stopPolling();
                    onError(taskStatus.error || 'Processing failed');
                } else if (attemptRef.current >= maxAttempts) {
                    stopPolling();
                    onError('Processing timeout - please try again');
                } else {
                    attemptRef.current++;
                }
            } catch (error) {
                stopPolling();
                onError(error instanceof Error ? error.message : 'Polling error');
            }
        };

        // Initial poll
        poll();

        // Set up interval
        intervalRef.current = setInterval(poll, interval);
    }, [taskId, interval, maxAttempts, onComplete, onError]);

    const stopPolling = React.useCallback(() => {
        if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
        }
        setIsPolling(false);
    }, []);

    // Clean up on unmount
    React.useEffect(() => {
        return () => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
            }
        };
    }, []);

    return {
        status,
        isPolling,
        progress: status?.progress || 0,
        message: status?.message || '',
        startPolling,
        stopPolling,
    };
}

// Need React for the hook
import React from 'react';

export default api;
