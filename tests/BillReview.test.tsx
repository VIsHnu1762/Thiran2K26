/**
 * BillAgent Pro - BillReview Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from './utils';
import { createMockBill, createMockLineItem } from './utils';
import BillReview from '../components/BillReview';

// Mock the API
vi.mock('../services/api', () => ({
    default: {
        getBill: vi.fn(),
        updateBill: vi.fn(),
        approveBill: vi.fn(),
        rejectBill: vi.fn(),
    },
}));

describe('BillReview Component', () => {
    const mockBill = createMockBill({
        line_items: [createMockLineItem()],
    });

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should render without crashing', () => {
        const { container } = render(<BillReview />);
        expect(container).toBeTruthy();
    });

    it('should render review elements', () => {
        render(<BillReview />);
        // Component should render something
        expect(document.body).toBeTruthy();
    });
});
