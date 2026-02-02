// Correction tracking and learning system
export interface Correction {
    id: string;
    billId: string;
    fieldType: 'itemName' | 'quantity' | 'price' | 'total' | 'vendorName' | 'date';
    originalValue: string | number;
    correctedValue: string | number;
    timestamp: string;
    itemIndex?: number;
}

export interface LearningPattern {
    pattern: string; // Original OCR text
    correction: string; // User's correction
    frequency: number; // How many times this correction was made
    confidence: number; // Confidence in this pattern (0-100)
    lastUsed: string;
}

export interface FrequentItem {
    name: string;
    frequency: number;
    avgPrice: number;
    lastSeen: string;
}

// Correction storage service
class CorrectionService {
    private corrections: Correction[] = [];
    private patterns: Map<string, LearningPattern> = new Map();
    private frequentItems: Map<string, FrequentItem> = new Map();

    constructor() {
        this.loadFromStorage();
    }

    // Save a user correction
    saveCorrection(correction: Correction) {
        this.corrections.push(correction);
        this.updatePattern(correction);
        this.saveToStorage();
    }

    // Update learning patterns
    private updatePattern(correction: Correction) {
        if (correction.fieldType === 'itemName') {
            const key = String(correction.originalValue).toLowerCase();
            const existing = this.patterns.get(key);

            if (existing && existing.correction === correction.correctedValue) {
                // Increase frequency and confidence
                existing.frequency++;
                existing.confidence = Math.min(100, existing.confidence + 5);
                existing.lastUsed = new Date().toISOString();
            } else {
                // New pattern
                this.patterns.set(key, {
                    pattern: String(correction.originalValue),
                    correction: String(correction.correctedValue),
                    frequency: 1,
                    confidence: 60,
                    lastUsed: new Date().toISOString()
                });
            }
        }
    }

    // Get suggestion for OCR text
    getSuggestion(ocrText: string, fieldType: string): string | null {
        if (fieldType !== 'itemName') return null;

        const key = ocrText.toLowerCase();
        const pattern = this.patterns.get(key);

        // Return suggestion if confidence is high enough
        if (pattern && pattern.confidence >= 70) {
            return pattern.correction;
        }

        // Fuzzy matching for similar patterns
        for (const [patternKey, patternValue] of this.patterns.entries()) {
            if (this.isSimilar(key, patternKey) && patternValue.confidence >= 80) {
                return patternValue.correction;
            }
        }

        return null;
    }

    // Track frequently sold items
    trackItem(name: string, price: number) {
        const key = name.toLowerCase();
        const existing = this.frequentItems.get(key);

        if (existing) {
            existing.frequency++;
            existing.avgPrice = (existing.avgPrice * (existing.frequency - 1) + price) / existing.frequency;
            existing.lastSeen = new Date().toISOString();
        } else {
            this.frequentItems.set(key, {
                name,
                frequency: 1,
                avgPrice: price,
                lastSeen: new Date().toISOString()
            });
        }

        this.saveToStorage();
    }

    // Get frequent items for suggestions
    getFrequentItems(limit: number = 10): FrequentItem[] {
        return Array.from(this.frequentItems.values())
            .sort((a, b) => b.frequency - a.frequency)
            .slice(0, limit);
    }

    // Get price suggestion for an item
    getPriceSuggestion(itemName: string): number | null {
        const key = itemName.toLowerCase();
        const item = this.frequentItems.get(key);
        return item ? item.avgPrice : null;
    }

    // Simple similarity check (Levenshtein distance would be better)
    private isSimilar(str1: string, str2: string): boolean {
        if (str1 === str2) return true;
        if (Math.abs(str1.length - str2.length) > 2) return false;

        let matches = 0;
        const minLen = Math.min(str1.length, str2.length);

        for (let i = 0; i < minLen; i++) {
            if (str1[i] === str2[i]) matches++;
        }

        return matches / minLen >= 0.7; // 70% similarity
    }

    // Get all corrections for a bill
    getCorrectionsForBill(billId: string): Correction[] {
        return this.corrections.filter(c => c.billId === billId);
    }

    // Get correction statistics
    getStats() {
        return {
            totalCorrections: this.corrections.length,
            learnedPatterns: this.patterns.size,
            frequentItems: this.frequentItems.size,
            avgConfidence: Array.from(this.patterns.values())
                .reduce((sum, p) => sum + p.confidence, 0) / this.patterns.size || 0
        };
    }

    // Storage management
    private saveToStorage() {
        localStorage.setItem('corrections', JSON.stringify(this.corrections));
        localStorage.setItem('patterns', JSON.stringify(Array.from(this.patterns.entries())));
        localStorage.setItem('frequentItems', JSON.stringify(Array.from(this.frequentItems.entries())));
    }

    private loadFromStorage() {
        try {
            const corrections = localStorage.getItem('corrections');
            if (corrections) {
                this.corrections = JSON.parse(corrections);
            }

            const patterns = localStorage.getItem('patterns');
            if (patterns) {
                this.patterns = new Map(JSON.parse(patterns));
            }

            const items = localStorage.getItem('frequentItems');
            if (items) {
                this.frequentItems = new Map(JSON.parse(items));
            }
        } catch (error) {
            console.error('Failed to load correction data:', error);
        }
    }

    // Clear all learning data (for testing)
    clearAll() {
        this.corrections = [];
        this.patterns.clear();
        this.frequentItems.clear();
        this.saveToStorage();
    }
}

// Export singleton instance
export const correctionService = new CorrectionService();
