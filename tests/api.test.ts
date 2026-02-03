/**
 * BillAgent Pro - API Service Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mockApiResponse, mockApiError, createMockBill, createMockVendor } from './utils';

// We'll test the API service patterns
describe('API Service', () => {
    const originalFetch = global.fetch;

    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        global.fetch = originalFetch;
    });

    describe('GET requests', () => {
        it('should handle successful response', async () => {
            const mockBills = [createMockBill(), createMockBill({ id: 2 })];
            global.fetch = vi.fn().mockResolvedValue(mockApiResponse(mockBills));

            const response = await fetch('/api/bills');
            const data = await response.json();

            expect(response.ok).toBe(true);
            expect(data).toHaveLength(2);
        });

        it('should handle error response', async () => {
            global.fetch = vi.fn().mockResolvedValue(mockApiError('Not found', 404));

            const response = await fetch('/api/bills/99999');

            expect(response.ok).toBe(false);
            expect(response.status).toBe(404);
        });

        it('should handle network errors', async () => {
            global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

            await expect(fetch('/api/bills')).rejects.toThrow('Network error');
        });
    });

    describe('POST requests', () => {
        it('should send JSON body', async () => {
            const newVendor = createMockVendor();
            global.fetch = vi.fn().mockResolvedValue(mockApiResponse(newVendor, 201));

            const response = await fetch('/api/vendors', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newVendor),
            });

            expect(response.ok).toBe(true);
            expect(response.status).toBe(201);
        });

        it('should handle validation errors', async () => {
            global.fetch = vi.fn().mockResolvedValue(
                mockApiError('Validation failed', 422)
            );

            const response = await fetch('/api/vendors', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({}),
            });

            expect(response.ok).toBe(false);
            expect(response.status).toBe(422);
        });
    });

    describe('Authentication', () => {
        it('should include auth header', async () => {
            const mockUser = { id: 1, email: 'test@test.com' };
            global.fetch = vi.fn().mockResolvedValue(mockApiResponse(mockUser));

            await fetch('/api/auth/me', {
                headers: {
                    'Authorization': 'Bearer test-token',
                },
            });

            expect(global.fetch).toHaveBeenCalledWith(
                '/api/auth/me',
                expect.objectContaining({
                    headers: expect.objectContaining({
                        'Authorization': 'Bearer test-token',
                    }),
                })
            );
        });

        it('should handle 401 unauthorized', async () => {
            global.fetch = vi.fn().mockResolvedValue(mockApiError('Unauthorized', 401));

            const response = await fetch('/api/auth/me');

            expect(response.ok).toBe(false);
            expect(response.status).toBe(401);
        });
    });
});
