import { GoogleGenerativeAI } from '@google/generative-ai';
import { Bill } from '../types';

// Initialize Gemini AI (free tier: 15 requests/min, 1500/day)
// Best for handwritten text recognition
const GEMINI_API_KEY = 'AIzaSyDLSLfiKQRBxvZGNBPdABjfbQRKrQxfRHo';
const genAI = new GoogleGenerativeAI(GEMINI_API_KEY);

/**
 * Process bill image using Gemini AI
 * Excellent for handwritten bills (90%+ accuracy)
 */
export const processWithGemini = async (base64Image: string): Promise<any> => {
    try {
        console.log('🔑 Gemini API Key:', GEMINI_API_KEY ? 'Present' : 'MISSING');

        const model = genAI.getGenerativeModel({ model: 'gemini-2.0-flash-exp' });

        // Remove data URL prefix if present
        const imageData = base64Image.includes(',') ? base64Image.split(',')[1] : base64Image;

        console.log('📸 Sending image to Gemini AI...');

        const result = await model.generateContent([
            {
                inlineData: {
                    mimeType: 'image/jpeg',
                    data: imageData
                }
            },
            {
                text: `Analyze this bill/receipt image and extract ALL data in JSON format. For handwritten bills, carefully read each number and item.

Return ONLY valid JSON (no markdown, no code blocks):
{
  "vendorName": "store name or 'Handwritten Bill'",
  "date": "YYYY-MM-DD or extracted date",
  "items": [
    {
      "name": "item name or 'Item 1', 'Item 2', etc for unnamed items",
      "quantity": number,
      "price": number (per unit),
      "total": number (quantity * price)
    }
  ],
  "grandTotal": number (sum of all item totals),
  "extractedText": "all text you can see in the image"
}

IMPORTANT RULES:
1. Extract ALL items you can see, even if handwritten
2. For tables with columns of numbers, treat each row as an item
3. If you see quantity, price, total columns - extract them accurately
4. Calculate grandTotal as sum of all item totals
5. Use "Item 1", "Item 2" etc if item names are unclear`
            }
        ]);

        const response = await result.response;
        let text = response.text();

        console.log('📥 Gemini Response received (length:', text.length, ')');
        console.log('First 200 chars:', text.substring(0, 200));

        // Clean response (remove markdown code blocks if present)
        text = text.trim();
        if (text.startsWith('```json')) {
            text = text.replace(/```json\n?/g, '').replace(/```\n?$/g, '');
        } else if (text.startsWith('```')) {
            text = text.replace(/```\n?/g, '');
        }

        const data = JSON.parse(text);

        console.log('✅ Items extracted:', data.items ? data.items.length : 0);
        console.log('💰 Grand Total:', data.grandTotal);

        // Validate response
        if (!data.items || !Array.isArray(data.items)) {
            throw new Error('Invalid response from Gemini: missing items array');
        }

        if (data.items.length === 0) {
            console.warn('⚠️ No items found in image');
        }

        return data;

    } catch (error) {
        console.error('❌ Gemini OCR Failed:', error);
        throw error;
    }
};
