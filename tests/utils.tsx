/**
 * BillAgent Pro - Test Utilities
 * ==============================
 * Shared test utilities and custom render functions
 */

import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Mock AuthContext provider for testing
const mockAuthContext = {
    user: null,
    isAuthenticated: false,
    isLoading: false,
    login: async () => { },
    logout: async () => { },
    updateUser: () => { },
};

// Create a mock provider wrapper
const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
    return <>{children}</>;
};

// Custom render function with providers
const customRender = (
    ui: ReactElement,
    options?: Omit<RenderOptions, 'wrapper'>
) => {
    return {
        user: userEvent.setup(),
        ...render(ui, { wrapper: AllTheProviders, ...options }),
    };
};

// Re-export everything from testing-library
export * from '@testing-library/react';
export { customRender as render };

// Test data factories
export const createMockBill = (overrides = {}) => ({
    id: 1,
    invoice_number: 'INV-2024-001',
    vendor_name: 'Test Vendor',
    invoice_date: '2024-01-15',
    due_date: '2024-02-15',
    subtotal: 100.0,
    tax_amount: 8.25,
    total_amount: 108.25,
    status: 'pending_review',
    ocr_confidence: 0.95,
    line_items: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
});

export const createMockVendor = (overrides = {}) => ({
    id: 1,
    name: 'Test Vendor Corp',
    address: '123 Test Street',
    city: 'Test City',
    state: 'CA',
    zip_code: '90210',
    phone: '555-0100',
    email: 'vendor@test.com',
    is_active: true,
    ...overrides,
});

export const createMockUser = (overrides = {}) => ({
    id: 1,
    email: 'test@billagent.com',
    username: 'testuser',
    full_name: 'Test User',
    role: 'user',
    is_active: true,
    created_at: new Date().toISOString(),
    ...overrides,
});

export const createMockLineItem = (overrides = {}) => ({
    id: 1,
    description: 'Office Supplies',
    quantity: 10,
    unit_price: 10.0,
    total_price: 100.0,
    gl_code: '5000-100',
    ...overrides,
});

// API mock helpers
export const mockApiResponse = <T>(data: T, status = 200) => {
  return Promise.resolve({
        ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  });
};

export const mockApiError = (message: string, status = 400) => {
  return Promise.resolve({
        ok: false,
    status,
    json: () => Promise.resolve({error: message }),
    text: () => Promise.resolve(JSON.stringify({error: message })),
  });
};
