import { createWorker } from 'tesseract.js';
import { Bill, BusinessInsight } from "../types";
import { processWithGemini } from './geminiOCR';

/**
 * OCR CONFIDENCE AGENT
 * Analyzes Tesseract confidence scores and character clarity
 */
const analyzeOCRConfidence = (confidence: number, text: string): { score: number; reasoning: string } => {
    let score = confidence;
    let issues: string[] = [];

    // Check for suspicious characters or patterns
    if (text.includes('�') || text.includes('�')) {
        score -= 20;
        issues.push('garbled characters detected');
    }

    // Check text length (very short = suspicious)
    if (text.length < 3 && text.trim() !== '') {
        score -= 10;
        issues.push('unusually short text');
    }

    const reasoning = score > 75
        ? 'High OCR confidence with clear character recognition'
        : issues.length > 0
            ? `Reduced confidence: ${issues.join(', ')}`
            : 'Moderate OCR confidence';

    return { score: Math.max(0, Math.min(100, score)), reasoning };
};

/**
 * VALIDATION AGENT
 * Checks field completeness and data validity
 */
const validateFields = (data: any): { verdict: 'OK' | 'WARNING' | 'CRITICAL'; reasoning: string } => {
    const issues: string[] = [];

    if (!data.items || data.items.length === 0) {
        return { verdict: 'CRITICAL', reasoning: 'No line items detected in bill' };
    }

    if (!data.grandTotal || data.grandTotal === 0) {
        issues.push('missing grand total');
    }

    if (!data.date) {
        issues.push('date not found');
    }

    data.items.forEach((item: any, idx: number) => {
        if (!item.name || item.name.trim() === '') issues.push(`item ${idx + 1} missing name`);
        if (item.quantity <= 0) issues.push(`item ${idx + 1} invalid quantity`);
        if (item.price < 0) issues.push(`item ${idx + 1} negative price`);
    });

    if (issues.length === 0) {
        return { verdict: 'OK', reasoning: 'All required fields present and valid' };
    } else if (issues.length <= 2) {
        return { verdict: 'WARNING', reasoning: `Minor issues: ${issues.join(', ')}` };
    } else {
        return { verdict: 'CRITICAL', reasoning: `Multiple validation failures: ${issues.slice(0, 3).join(', ')}` };
    }
};

/**
 * ERROR DETECTION AGENT
 * Mathematical validation: sum of line items vs grand total
 */
const detectMathErrors = (items: any[], grandTotal: number): { verdict: 'OK' | 'WARNING' | 'CRITICAL'; reasoning: string } => {
    const calculatedTotal = items.reduce((sum, item) => sum + (item.total || 0), 0);
    const difference = Math.abs(calculatedTotal - grandTotal);
    const errorPercent = grandTotal > 0 ? (difference / grandTotal) * 100 : 0;

    if (errorPercent < 1) {
        return {
            verdict: 'OK',
            reasoning: `Math verified: Σ items (₹${calculatedTotal.toFixed(2)}) matches total (₹${grandTotal.toFixed(2)})`
        };
    } else if (errorPercent < 5) {
        return {
            verdict: 'WARNING',
            reasoning: `Minor discrepancy: ₹${difference.toFixed(2)} variance (${errorPercent.toFixed(1)}%)`
        };
    } else {
        return {
            verdict: 'CRITICAL',
            reasoning: `Math error detected: ₹${difference.toFixed(2)} mismatch between sum and total`
        };
    }
};

/**
 * WORKFLOW DECISION AGENT
 * Determines review status based on confidence and errors
 */
const decideWorkflow = (overallConfidence: number, agents: any[]): 'PENDING' | 'VERIFIED' | 'FLAGGED' => {
    const hasCritical = agents.some(a => a.verdict === 'CRITICAL');
    const hasWarning = agents.some(a => a.verdict === 'WARNING');

    if (hasCritical) return 'FLAGGED';
    if (overallConfidence < 60 || hasWarning) return 'PENDING';
    return 'VERIFIED';
};

/**
 * Parse OCR text to extract bill data
 * Enhanced for handwritten bills and tabular data
 */
const parseBillText = (text: string): Partial<Bill> => {
    const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0);

    // Extract vendor name (usually first significant line)
    let vendorName = '';
    for (const line of lines) {
        if (line.length > 3 && !line.match(/^\d+/) && !line.includes('₹') && !line.includes('$')) {
            vendorName = line;
            break;
        }
    }

    // Extract date using multiple regex patterns
    const datePatterns = [
        /(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})/,
        /(\d{4}[-/]\d{1,2}[-/]\d{1,2})/,
        /(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})/i
    ];

    let date = new Date().toISOString().split('T')[0];
    for (const pattern of datePatterns) {
        const dateMatch = text.match(pattern);
        if (dateMatch) {
            date = dateMatch[0];
            break;
        }
    }

    // Extract all numbers from the text (more aggressive)
    const numberPattern = /\b\d+\.?\d*\b/g;
    const allNumbers: number[] = [];
    let match;
    while ((match = numberPattern.exec(text)) !== null) {
        const num = parseFloat(match[0]);
        if (num > 0 && num < 1000000) { // Reasonable range for bill amounts
            allNumbers.push(num);
        }
    }

    // Try multiple item extraction strategies
    const items: any[] = [];

    // Strategy 1: Pattern matching for structured items (name qty price total)
    const itemPattern1 = /([a-zA-Z\s]{2,})\s+(\d+)\s+[\₹\$]?\s*(\d+\.?\d*)\s+[\₹\$]?\s*(\d+\.?\d*)/;

    // Strategy 2: Just numbers in sequence (for handwritten bills)
    const itemPattern2 = /(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)/;

    for (const line of lines) {
        // Try structured pattern first
        const itemMatch1 = line.match(itemPattern1);
        if (itemMatch1) {
            const [, name, qty, price, total] = itemMatch1;
            items.push({
                name: name.trim(),
                quantity: parseInt(qty),
                price: parseFloat(price),
                total: parseFloat(total),
                confidence: 70
            });
            continue;
        }

        // Try number sequence pattern
        const itemMatch2 = line.match(itemPattern2);
        if (itemMatch2 && items.length < 20) { // Limit to 20 items
            const [, qty, price, total] = itemMatch2;
            const qtyNum = parseFloat(qty);
            const priceNum = parseFloat(price);
            const totalNum = parseFloat(total);

            // Validate: total should be close to qty * price
            const expectedTotal = qtyNum * priceNum;
            const variance = Math.abs(expectedTotal - totalNum) / totalNum;

            if (variance < 0.5 || totalNum > priceNum) { // Allow 50% variance or total > price
                items.push({
                    name: `Item ${items.length + 1}`,
                    quantity: Math.round(qtyNum),
                    price: priceNum,
                    total: totalNum,
                    confidence: 65
                });
            }
        }
    }

    // If no items found via patterns, create from number sequences
    if (items.length === 0 && allNumbers.length >= 3) {
        // Group numbers in sets of 3 (qty, price, total)
        for (let i = 0; i < Math.min(allNumbers.length - 2, 30); i += 3) {
            const qty = allNumbers[i];
            const price = allNumbers[i + 1];
            const total = allNumbers[i + 2];

            // Basic validation
            if (qty <= 100 && price > 0 && total >= price) {
                items.push({
                    name: `Item ${items.length + 1}`,
                    quantity: Math.round(qty),
                    price: price,
                    total: total,
                    confidence: 55
                });
            }
        }
    }

    // Determine grand total
    let grandTotal = 0;

    // Strategy 1: Look for "total" keyword
    const totalPattern = /total[:\s]+[\₹\$]?\s*(\d+\.?\d*)/i;
    const totalMatch = text.match(totalPattern);
    if (totalMatch) {
        grandTotal = parseFloat(totalMatch[1]);
    }

    // Strategy 2: Largest number in the text
    if (grandTotal === 0 && allNumbers.length > 0) {
        grandTotal = Math.max(...allNumbers);
    }

    // Strategy 3: Sum of all item totals
    if (grandTotal === 0 && items.length > 0) {
        grandTotal = items.reduce((sum, item) => sum + item.total, 0);
    }

    // If we have items but grand total seems wrong, recalculate
    if (items.length > 0) {
        const calculatedTotal = items.reduce((sum, item) => sum + item.total, 0);

        // If grand total is way off, use calculated
        if (Math.abs(grandTotal - calculatedTotal) / calculatedTotal > 0.3) {
            grandTotal = calculatedTotal;
        }
    }

    return {
        vendorName: vendorName || 'Handwritten Bill',
        date,
        items,
        grandTotal: Math.round(grandTotal * 100) / 100 // Round to 2 decimals
    };
};

/**
 * Process bill image using Tesseract OCR + Agentic validation
 */
/**
 * Process bill image using the Python Backend (OpenCV + Tesseract + Agents)
 */
export const processBillImage = async (base64Image: string): Promise<Partial<Bill>> => {
    try {
        // Validation
        if (!base64Image || base64Image.trim() === '') {
            throw new Error('No image data provided.');
        }

        // Convert Base64 to Blob for FormData
        const fetchResponse = await fetch(base64Image);
        const blob = await fetchResponse.blob();

        const formData = new FormData();
        formData.append('file', blob, 'bill.jpg');

        console.log('🚀 Sending image to Python Backend...');

        const response = await fetch('http://localhost:8000/bills/analyze', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Backend Error (${response.status}): ${errorText}`);
        }

        const data = await response.json();
        console.log('✅ Backend Analysis Complete:', data);

        // Map Backend Response to Frontend Interface

        // 1. Map Agents
        const agents: Array<{ agentName: string; verdict: 'OK' | 'WARNING' | 'CRITICAL'; reasoning: string }> = [];

        // Confidence Agent
        agents.push({
            agentName: 'OCR Confidence Agent',
            verdict: data.confidence_scores.overall >= 85 ? 'OK' : data.confidence_scores.overall >= 60 ? 'WARNING' : 'CRITICAL',
            reasoning: `Overall Confidence: ${Math.round(data.confidence_scores.overall)}%`
        });

        // Error Agent (Backend returns list of error strings)
        if (data.errors && data.errors.length > 0) {
            agents.push({
                agentName: 'Error Detection Agent',
                verdict: 'CRITICAL',
                reasoning: `Issues: ${data.errors.join(', ')}`
            });
        } else {
            agents.push({
                agentName: 'Error Detection Agent',
                verdict: 'OK',
                reasoning: 'No math or logic errors detected.'
            });
        }

        // Workflow Agent
        let workflowVerdict: 'OK' | 'WARNING' | 'CRITICAL' = 'OK';
        if (data.workflow_decision === 'PARTIAL_REVIEW') workflowVerdict = 'WARNING';
        if (data.workflow_decision === 'FULL_REVIEW') workflowVerdict = 'CRITICAL';

        agents.push({
            agentName: 'Workflow Agent',
            verdict: workflowVerdict,
            reasoning: `Decision: ${data.workflow_decision}`
        });

        // 2. Map Items
        const items = data.items.map((item: any) => ({
            name: item.name,
            quantity: item.quantity,
            price: item.unit_price,
            total: item.line_total,
            confidence: item.confidence
        }));

        return {
            vendorName: "Analyzed Bill", // Backend doesn't extract vendor yet
            date: new Date().toISOString().split('T')[0], // Backend doesn't extract date yet
            items: items,
            grandTotal: data.total,
            overallConfidence: data.confidence_scores.overall || 0,
            agents: agents
        };

    } catch (error) {
        console.error('Backend processing failed:', error);
        throw new Error('Failed to connect to the analysis server. Make sure the Python backend is running.');
    }
};
/**
 * Generate business insights from bill collection (Rule-based)
 */
export const generateBusinessInsights = async (bills: Bill[]): Promise<BusinessInsight[]> => {
    const insights: BusinessInsight[] = [];

    if (bills.length === 0) return insights;

    // Calculate aggregates
    const totalRevenue = bills.reduce((sum, b) => sum + b.grandTotal, 0);
    const avgBillValue = totalRevenue / bills.length;

    // Item frequency analysis
    const itemFreq: Record<string, { count: number; revenue: number }> = {};
    bills.forEach(bill => {
        bill.items.forEach(item => {
            const key = item.name.toLowerCase().trim();
            if (!itemFreq[key]) itemFreq[key] = { count: 0, revenue: 0 };
            itemFreq[key].count += item.quantity;
            itemFreq[key].revenue += item.total;
        });
    });

    const topItems = Object.entries(itemFreq)
        .sort((a, b) => b[1].revenue - a[1].revenue)
        .slice(0, 3);

    // INSIGHT 1: Revenue Trend
    if (bills.length >= 3) {
        insights.push({
            type: 'TREND',
            title: 'Revenue Performance Trending',
            content: `Your business processed ${bills.length} bills totaling ₹${totalRevenue.toFixed(2)}. Average transaction value is ₹${avgBillValue.toFixed(2)}.`,
            impact: 'POSITIVE',
            actionable: 'Monitor daily patterns'
        });
    }

    // INSIGHT 2: Top Performer
    if (topItems.length > 0) {
        insights.push({
            type: 'TREND',
            title: 'Best-Selling Item',
            content: `"${topItems[0][0]}" leads with ₹${topItems[0][1].revenue.toFixed(2)} in sales across ${topItems[0][1].count} units.`,
            impact: 'POSITIVE',
            actionable: 'Ensure stock availability'
        });
    }

    // INSIGHT 3: Price Variance Detection
    const priceVariance: Record<string, number[]> = {};
    bills.forEach(bill => {
        bill.items.forEach(item => {
            const key = item.name.toLowerCase().trim();
            if (!priceVariance[key]) priceVariance[key] = [];
            priceVariance[key].push(item.price);
        });
    });

    for (const [itemName, prices] of Object.entries(priceVariance)) {
        if (prices.length > 1) {
            const maxPrice = Math.max(...prices);
            const minPrice = Math.min(...prices);
            const variance = ((maxPrice - minPrice) / minPrice) * 100;

            if (variance > 15) {
                insights.push({
                    type: 'ALERT',
                    title: 'Price Inconsistency Detected',
                    content: `"${itemName}" shows ${variance.toFixed(1)}% price variance (₹${minPrice.toFixed(2)} - ₹${maxPrice.toFixed(2)}). Consider standardizing pricing.`,
                    impact: 'NEUTRAL',
                    actionable: 'Review supplier contracts'
                });
                break; // Only add one alert
            }
        }
    }

    // INSIGHT 4: Low Confidence Warning
    const lowConfidenceBills = bills.filter(b => b.overallConfidence < 70);
    if (lowConfidenceBills.length > bills.length * 0.2) {
        insights.push({
            type: 'ALERT',
            title: 'OCR Accuracy Needs Attention',
            content: `${lowConfidenceBills.length} bills have low extraction confidence. Consider using higher quality images or reviewing flagged bills.`,
            impact: 'NEGATIVE',
            actionable: 'Improve image capture quality'
        });
    }

    // INSIGHT 5: Recommendation
    if (bills.length >= 5) {
        insights.push({
            type: 'RECOMMENDATION',
            title: 'Optimize Inventory Management',
            content: `With ${bills.length} bills processed, you have enough data to forecast demand. Consider implementing automated reorder points for top items.`,
            impact: 'POSITIVE',
            actionable: 'Set up inventory alerts'
        });
    }

    return insights.slice(0, 5); // Limit to 5 insights
};

/**
 * Generate storytelling audio (uses Web Speech API only)
 */
export const generateStorytellingAudio = async (text: string): Promise<string> => {
    // This function now relies entirely on the browser's SpeechSynthesis API
    // The calling component (Dashboard.tsx) already handles the Web Speech API
    // This function is kept for compatibility but does nothing
    return '';
};
