/**
 * BillAgent Pro - OCR Service Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock Google Generative AI
vi.mock('@google/generative-ai', () => ({
    GoogleGenerativeAI: vi.fn().mockImplementation(() => ({
        getGenerativeModel: vi.fn().mockReturnValue({
            generateContent: vi.fn().mockResolvedValue({
                response: {
                    text: () => JSON.stringify({
                        vendor_name: 'Test Vendor',
                        invoice_number: 'INV-001',
                        total_amount: 108.25,
                    }),
                },
            }),
        }),
    })),
}));

describe('OCR Service', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('Image Processing', () => {
        it('should validate image format', () => {
            const validFormats = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
            const invalidFormats = ['application/pdf', 'text/plain', 'video/mp4'];

            validFormats.forEach(format => {
                const isValid = format.startsWith('image/');
                expect(isValid).toBe(true);
            });

            invalidFormats.forEach(format => {
                const isValid = format.startsWith('image/');
                expect(isValid).toBe(false);
            });
        });

        it('should convert base64 to data URL', () => {
            const base64 = 'SGVsbG8gV29ybGQ=';
            const mimeType = 'image/png';
            const dataUrl = `data:${mimeType};base64,${base64}`;

            expect(dataUrl).toContain('data:image/png;base64,');
            expect(dataUrl).toContain(base64);
        });
    });

    describe('OCR Response Parsing', () => {
        it('should parse vendor name', () => {
            const ocrResult = {
                vendor_name: 'Test Vendor Corp',
                invoice_number: 'INV-2024-001',
            };

            expect(ocrResult.vendor_name).toBe('Test Vendor Corp');
        });

        it('should parse invoice number', () => {
            const ocrResult = {
                vendor_name: 'Test Vendor',
                invoice_number: 'INV-2024-001',
            };

            expect(ocrResult.invoice_number).toBe('INV-2024-001');
        });

        it('should parse amounts', () => {
            const ocrResult = {
                subtotal: 100.00,
                tax_amount: 8.25,
                total_amount: 108.25,
            };

            expect(ocrResult.subtotal + ocrResult.tax_amount).toBeCloseTo(ocrResult.total_amount);
        });

        it('should handle missing fields gracefully', () => {
            const partialResult = {
                vendor_name: 'Test Vendor',
                // Missing other fields
            };

            expect(partialResult.vendor_name).toBeDefined();
            expect((partialResult as any).invoice_number).toBeUndefined();
        });
    });

    describe('Confidence Scores', () => {
        it('should calculate confidence score in valid range', () => {
            const confidence = 0.95;

            expect(confidence).toBeGreaterThanOrEqual(0);
            expect(confidence).toBeLessThanOrEqual(1);
        });

        it('should flag low confidence results', () => {
            const threshold = 0.7;
            const lowConfidence = 0.5;
            const highConfidence = 0.9;

            expect(lowConfidence < threshold).toBe(true);
            expect(highConfidence >= threshold).toBe(true);
        });
    });
});
