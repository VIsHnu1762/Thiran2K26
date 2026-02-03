/**
 * BillAgent Pro - Test Setup
 * ==========================
 * Global test configuration and mocks
 */

import '@testing-library/jest-dom';
import { vi, beforeAll, afterAll, afterEach } from 'vitest';

// Mock ResizeObserver (not available in jsdom)
global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
}));

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
}));

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
    })),
});

// Mock localStorage
const localStorageMock = {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
    length: 0,
    key: vi.fn(),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock fetch
global.fetch = vi.fn();

// Reset mocks after each test
afterEach(() => {
    vi.clearAllMocks();
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();
    localStorageMock.removeItem.mockClear();
    localStorageMock.clear.mockClear();
});

// Suppress console errors during tests (optional)
beforeAll(() => {
    vi.spyOn(console, 'error').mockImplementation(() => { });
    vi.spyOn(console, 'warn').mockImplementation(() => { });
});

afterAll(() => {
    vi.restoreAllMocks();
});
