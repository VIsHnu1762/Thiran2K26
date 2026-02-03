
import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  FileUp,
  Loader2,
  CheckCircle,
  RotateCcw,
  ZoomIn,
  Camera,
  X,
  Scan,
  ShieldCheck,
  Zap,
  ArrowRight,
  Edit2,
  Save,
  AlertCircle,
  RefreshCw
} from 'lucide-react';
import { processBillImage } from '../services/ocrService';
import { api, usePolling } from '../services/api';
import { Bill, BillItem, AgentReport, TaskStatus } from '../types';
import { correctionService } from '../services/correctionService';
import { Button } from './ui/button';
import { Badge } from './ui/badge';

interface BillUploadProps {
  onComplete: (bill: Bill) => void;
  useBackendProcessing?: boolean; // Toggle between local and backend processing
}

const BillUpload: React.FC<BillUploadProps> = ({ onComplete, useBackendProcessing = false }) => {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [step, setStep] = useState<'upload' | 'analyzing' | 'review'>('upload');
  const [extractedData, setExtractedData] = useState<Partial<Bill> | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editingItemIndex, setEditingItemIndex] = useState<number | null>(null);
  const [originalData, setOriginalData] = useState<Partial<Bill> | null>(null);

  // Backend processing state
  const [taskId, setTaskId] = useState<string | null>(null);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [processingMessage, setProcessingMessage] = useState('');
  const [processingError, setProcessingError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Handle polling completion
  const handlePollingComplete = useCallback((bill: Bill) => {
    setExtractedData(bill);
    setOriginalData(JSON.parse(JSON.stringify(bill)));
    setStep('review');
    setIsProcessing(false);
    setTaskId(null);
  }, []);

  // Handle polling error
  const handlePollingError = useCallback((error: string) => {
    setProcessingError(error);
    setStep('upload');
    setIsProcessing(false);
    setTaskId(null);
  }, []);

  // Setup polling hook
  const { status, isPolling, progress, message, startPolling, stopPolling } = usePolling(
    taskId,
    handlePollingComplete,
    handlePollingError,
    { interval: 2000, maxAttempts: 90 } // 3 minutes max
  );

  // Update progress from polling
  useEffect(() => {
    if (isPolling && status) {
      setProcessingProgress(progress);
      setProcessingMessage(message);
    }
  }, [isPolling, status, progress, message]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      // Validate file type
      const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
      if (!validTypes.includes(selected.type)) {
        alert('❌ Invalid file type! Please upload a valid image (JPEG, PNG, or WebP).');
        return;
      }

      // Validate file size (max 10MB)
      const maxSize = 10 * 1024 * 1024; // 10MB
      if (selected.size > maxSize) {
        alert('❌ File too large! Please upload an image smaller than 10MB.');
        return;
      }

      setFile(selected);
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result as string);
        setStep('upload');
      };
      reader.onerror = () => {
        alert('❌ Failed to read file! Please try again with a valid image.');
      };
      reader.readAsDataURL(selected);
    }
  };

  const startProcessing = async () => {
    if (!preview) return;
    setIsProcessing(true);
    setStep('analyzing');
    setProcessingError(null);
    setProcessingProgress(0);
    setProcessingMessage('Initializing...');

    // Use backend processing if enabled and file is available
    if (useBackendProcessing && file) {
      try {
        const response = await api.uploadBill(file);

        if (response.success && response.data?.taskId) {
          setTaskId(response.data.taskId);
          startPolling();
        } else {
          throw new Error(response.error || 'Failed to upload bill');
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
        setProcessingError(errorMessage);
        setStep('upload');
        setIsProcessing(false);
      }
      return;
    }

    // Local processing (original implementation)
    try {
      const result = await processBillImage(preview);

      // Validate that we got meaningful data
      if (!result.items || result.items.length === 0) {
        throw new Error('No bill data detected in the image. Please ensure the image contains a clear bill or receipt.');
      }

      setExtractedData(result);
      setOriginalData(JSON.parse(JSON.stringify(result))); // Deep copy for comparison
      setStep('review');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';

      // User-friendly error messages
      if (errorMessage.includes('No bill data') || errorMessage.includes('No line items')) {
        alert('❌ Could not detect bill information!\n\nPlease upload a valid bill or receipt image with:\n• Clear text\n• Item names and prices\n• Total amount');
      } else if (errorMessage.includes('Failed to process')) {
        alert('❌ Image processing failed!\n\nPlease ensure:\n• Image is clear and well-lit\n• Text is readable\n• Image format is valid (JPEG/PNG)');
      } else {
        alert(`❌ Error: ${errorMessage}\n\nPlease try again with a valid bill image.`);
      }

      setStep('upload');
      setPreview(null);
      setFile(null);
    } finally {
      setIsProcessing(false);
    }
  };

  // Cancel backend processing
  const cancelProcessing = useCallback(() => {
    stopPolling();
    setTaskId(null);
    setIsProcessing(false);
    setStep('upload');
    setProcessingProgress(0);
    setProcessingMessage('');
  }, [stopPolling]);

  // Handle item field editing
  const handleItemEdit = (index: number, field: keyof BillItem, value: string | number) => {
    if (!extractedData || !extractedData.items) return;

    const updatedItems = [...extractedData.items];
    const item = { ...updatedItems[index] };

    // Track correction if value changed
    if (originalData && originalData.items && originalData.items[index]) {
      const originalValue = originalData.items[index][field];
      if (originalValue !== value) {
        correctionService.saveCorrection({
          id: Math.random().toString(36).substr(2, 9),
          billId: 'temp-' + Date.now(),
          fieldType: field === 'name' ? 'itemName' : field as any,
          originalValue,
          correctedValue: value,
          timestamp: new Date().toISOString(),
          itemIndex: index
        });
      }
    }

    // Update the field
    if (field === 'name') {
      item.name = String(value);
    } else if (field === 'quantity') {
      item.quantity = Number(value);
      item.total = item.quantity * item.price;
    } else if (field === 'price') {
      item.price = Number(value);
      item.total = item.quantity * item.price;
    } else if (field === 'total') {
      item.total = Number(value);
    }

    updatedItems[index] = item;

    // Recalculate grand total
    const newGrandTotal = updatedItems.reduce((sum, item) => sum + item.total, 0);

    setExtractedData({
      ...extractedData,
      items: updatedItems,
      grandTotal: newGrandTotal
    });
  };

  // Handle vendor name edit
  const handleVendorEdit = (value: string) => {
    if (!extractedData) return;

    if (originalData && originalData.vendorName !== value) {
      correctionService.saveCorrection({
        id: Math.random().toString(36).substr(2, 9),
        billId: 'temp-' + Date.now(),
        fieldType: 'vendorName',
        originalValue: originalData.vendorName || '',
        correctedValue: value,
        timestamp: new Date().toISOString()
      });
    }

    setExtractedData({ ...extractedData, vendorName: value });
  };

  // Handle date edit
  const handleDateEdit = (value: string) => {
    if (!extractedData) return;

    if (originalData && originalData.date !== value) {
      correctionService.saveCorrection({
        id: Math.random().toString(36).substr(2, 9),
        billId: 'temp-' + Date.now(),
        fieldType: 'date',
        originalValue: originalData.date || '',
        correctedValue: value,
        timestamp: new Date().toISOString()
      });
    }

    setExtractedData({ ...extractedData, date: value });
  };

  const confirmBill = () => {
    if (!extractedData || !preview) return;

    // Track items for learning
    if (extractedData.items) {
      extractedData.items.forEach(item => {
        correctionService.trackItem(item.name, item.price);
      });
    }

    const finalBill: Bill = {
      id: Math.random().toString(36).substr(2, 9),
      date: extractedData.date || new Date().toISOString().split('T')[0],
      imageUrl: preview,
      items: extractedData.items as BillItem[],
      grandTotal: extractedData.grandTotal || 0,
      status: 'VERIFIED',
      overallConfidence: extractedData.overallConfidence || 100,
      agents: extractedData.agents as AgentReport[],
      vendorName: extractedData.vendorName
    };

    console.log('✅ Bill confirmed with', extractedData.items?.length, 'items');
    console.log('📊 Learning stats:', correctionService.getStats());

    onComplete(finalBill);
    setStep('upload');
    setFile(null);
    setPreview(null);
    setIsEditing(false);
    setEditingItemIndex(null);
  };

  return (
    <div className="max-w-6xl mx-auto animate-in fade-in zoom-in-95 duration-700">
      <div className="flex items-center justify-between mb-10">
        <div>
          <h1 className="text-4xl font-bold text-white/90 tracking-tight">Digitize Bill</h1>
          <p className="text-white/50 text-lg">Agentic neural extraction engine</p>
        </div>
        <div className="flex gap-4">
          {['Source', 'Logic', 'Finalize'].map((s, i) => (
            <div key={s} className="flex items-center gap-3">
              <div className={`tap-effect w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold transition-all duration-500 ${(i === 0 && step === 'upload') || (i === 1 && step === 'analyzing') || (i === 2 && step === 'review')
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30 ring-4 ring-blue-500/10' : 'bg-white/10 text-white/40'
                }`}>
                {i + 1}
              </div>
              <span className={`text-sm font-bold tracking-tight ${(i === 0 && step === 'upload') || (i === 1 && step === 'analyzing') || (i === 2 && step === 'review')
                ? 'text-white' : 'text-white/30'
                }`}>{s}</span>
              {i < 2 && <ArrowRight size={16} className="text-white/10" />}
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
        {/* Main Interface Area */}
        <div className="lg:col-span-7 space-y-8">
          <div className="glass-card overflow-hidden">
            {preview ? (
              <div className="relative aspect-video lg:aspect-[3/4] flex items-center justify-center bg-black/20">
                <img src={preview} alt="Capture" className="max-h-full w-full object-contain" />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/40 pointer-events-none" />

                <div className="absolute bottom-10 left-1/2 -translate-x-1/2 flex items-center gap-5">
                  <button onClick={() => setPreview(null)} className="tap-effect p-4 bg-rose-500/20 text-rose-400 backdrop-blur-xl rounded-[20px] border border-rose-500/30 hover:bg-rose-500/40 transition-all active:scale-95">
                    <X size={24} />
                  </button>
                  <button className="tap-effect p-4 bg-white/10 text-white backdrop-blur-xl rounded-[20px] border border-white/20 hover:bg-white/20 transition-all active:scale-95">
                    <RotateCcw size={24} />
                  </button>
                  <button className="tap-effect p-4 bg-white/10 text-white backdrop-blur-xl rounded-[20px] border border-white/20 hover:bg-white/20 transition-all active:scale-95">
                    <ZoomIn size={24} />
                  </button>
                </div>

                {step === 'analyzing' && (
                  <div className="absolute inset-0 bg-indigo-900/40 backdrop-blur-2xl flex flex-col items-center justify-center text-center p-10 animate-in fade-in duration-500">
                    <div className="relative w-32 h-32 mb-8">
                      <div className="absolute inset-0 border-4 border-blue-500/10 rounded-full" />
                      <div className="absolute inset-0 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
                      <div className="absolute inset-0 flex items-center justify-center">
                        <Scan className="text-blue-400 animate-pulse" size={48} />
                      </div>
                    </div>

                    {/* Progress bar for backend processing */}
                    {useBackendProcessing && taskId && (
                      <div className="w-full max-w-xs mb-6">
                        <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 transition-all duration-500"
                            style={{ width: `${processingProgress}%` }}
                          />
                        </div>
                        <p className="text-blue-200/60 text-sm mt-2">{processingProgress}% complete</p>
                      </div>
                    )}

                    <h3 className="text-3xl font-bold text-white mb-3 tracking-tight">
                      {useBackendProcessing ? 'Processing...' : 'Agent reasoning...'}
                    </h3>
                    <p className="text-blue-200/60 text-lg max-w-sm font-medium">
                      {processingMessage || 'Extracting neural patterns and verifying ledger consistency.'}
                    </p>

                    {/* Error display */}
                    {processingError && (
                      <div className="mt-6 p-4 bg-rose-500/20 border border-rose-500/30 rounded-xl max-w-sm">
                        <div className="flex items-center gap-2 text-rose-400 mb-2">
                          <AlertCircle size={18} />
                          <span className="font-bold">Processing Error</span>
                        </div>
                        <p className="text-rose-300/80 text-sm">{processingError}</p>
                      </div>
                    )}

                    {/* Cancel button for backend processing */}
                    {useBackendProcessing && taskId && (
                      <Button
                        variant="ghost"
                        onClick={cancelProcessing}
                        className="mt-6"
                      >
                        <X size={16} className="mr-2" />
                        Cancel
                      </Button>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div
                onClick={() => fileInputRef.current?.click()}
                className="tap-effect aspect-video lg:aspect-[3/4] flex flex-col items-center justify-center p-16 border-4 border-dashed border-white/5 hover:border-blue-500/40 hover:bg-blue-600/5 cursor-pointer transition-all duration-500 group"
              >
                <div className="w-24 h-24 bg-blue-600/10 rounded-[32px] flex items-center justify-center mb-8 text-blue-500 group-hover:scale-110 group-hover:bg-blue-600/20 transition-all duration-500">
                  <FileUp size={48} />
                </div>
                <h3 className="text-3xl font-bold text-white/90 mb-3 tracking-tight">Digitize Document</h3>
                <p className="text-white/40 text-center max-w-md text-lg mb-10 font-medium leading-relaxed">
                  Upload high-resolution capture. Multi-agent logic will handle handwriting, pricing, and tax validation.
                </p>
                <div className="flex gap-6">
                  <button className="tap-effect px-8 py-4 bg-white/5 border border-white/10 text-white rounded-[24px] font-bold hover:bg-white/10 transition-all flex items-center gap-3 active:scale-95">
                    <Camera size={22} /> Live Scan
                  </button>
                  <button className="gem-button px-10 py-4 text-lg">
                    Browse Assets
                  </button>
                </div>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept="image/*"
              onChange={handleFileChange}
            />
          </div>

          {preview && step === 'upload' && (
            <button
              onClick={startProcessing}
              disabled={isProcessing}
              className="gem-button w-full py-6 text-2xl flex items-center justify-center gap-4 active:scale-95"
            >
              {isProcessing ? <Loader2 className="animate-spin" /> : <Zap className="fill-white" size={32} />}
              {isProcessing ? 'Thinking...' : 'Start Agentic Workflow'}
            </button>
          )}
        </div>

        {/* Intelligence Sidebar */}
        <div className="lg:col-span-5">
          <div className="sticky top-28 space-y-8">
            <div className="glass-card p-8">
              <h2 className="text-2xl font-bold text-white/90 mb-8 flex items-center gap-3">
                <ShieldCheck className="text-blue-400" size={30} />
                Neural Verdict
              </h2>

              {!extractedData ? (
                <div className="py-24 flex flex-col items-center justify-center text-center space-y-6 opacity-30">
                  <div className="w-20 h-20 bg-white/5 rounded-[24px] flex items-center justify-center">
                    <Scan size={40} />
                  </div>
                  <p className="text-white/80 font-medium max-w-[240px] text-lg">Agent justifications will appear after scanning</p>
                </div>
              ) : (
                <div className="space-y-8 animate-in fade-in slide-in-from-right-4 duration-700">
                  {extractedData.agents?.map((agent, i) => (
                    <div key={i} className="tap-effect p-5 rounded-[24px] bg-white/5 border border-white/10 space-y-3 cursor-default">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold text-white/40 uppercase tracking-widest">{agent.agentName}</span>
                        <span className={`px-3 py-1 rounded-lg text-[10px] font-bold tracking-tight border ${agent.verdict === 'OK' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-400/20' :
                          agent.verdict === 'WARNING' ? 'bg-amber-500/10 text-amber-400 border-amber-400/20' : 'bg-rose-500/10 text-rose-400 border-rose-400/20'
                          }`}>
                          {agent.verdict}
                        </span>
                      </div>
                      <p className="text-base text-white/70 italic leading-relaxed font-medium">"{agent.reasoning}"</p>
                    </div>
                  ))}

                  <div className="pt-8 border-t border-white/10">
                    <div className="flex justify-between items-center mb-6">
                      <span className="text-white/40 font-bold uppercase tracking-widest text-xs">Extraction Map</span>
                      <span className="text-blue-400 text-sm font-bold bg-blue-400/10 px-3 py-1 rounded-full">{extractedData.items?.length || 0} Assets</span>
                    </div>
                    <div className="space-y-4 max-h-[340px] overflow-y-auto pr-3 scroll-thin">
                      {extractedData.items?.map((item: any, i: number) => (
                        <div key={i} className="tap-effect p-4 rounded-[20px] bg-white/5 border border-white/10 hover:bg-white/8 transition-colors">
                          {editingItemIndex === i ? (
                            // EDIT MODE
                            <div className="space-y-3">
                              <div className="flex items-center gap-2">
                                <input
                                  type="text"
                                  value={item.name}
                                  onChange={(e) => handleItemEdit(i, 'name', e.target.value)}
                                  className="flex-1 px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white font-bold focus:outline-none focus:border-blue-400"
                                  placeholder="Item name"
                                />
                                <button
                                  onClick={() => setEditingItemIndex(null)}
                                  className="p-2 bg-emerald-500/20 text-emerald-400 rounded-lg hover:bg-emerald-500/30 transition-colors"
                                >
                                  <Save size={18} />
                                </button>
                              </div>
                              <div className="grid grid-cols-3 gap-2">
                                <div>
                                  <label className="text-[10px] text-white/40 uppercase font-bold">Qty</label>
                                  <input
                                    type="number"
                                    value={item.quantity}
                                    onChange={(e) => handleItemEdit(i, 'quantity', e.target.value)}
                                    className="w-full px-2 py-1 bg-white/10 border border-white/20 rounded text-white text-sm focus:outline-none focus:border-blue-400"
                                  />
                                </div>
                                <div>
                                  <label className="text-[10px] text-white/40 uppercase font-bold">Price</label>
                                  <input
                                    type="number"
                                    value={item.price}
                                    onChange={(e) => handleItemEdit(i, 'price', e.target.value)}
                                    className="w-full px-2 py-1 bg-white/10 border border-white/20 rounded text-white text-sm focus:outline-none focus:border-blue-400"
                                  />
                                </div>
                                <div>
                                  <label className="text-[10px] text-white/40 uppercase font-bold">Total</label>
                                  <input
                                    type="number"
                                    value={item.total}
                                    onChange={(e) => handleItemEdit(i, 'total', e.target.value)}
                                    className="w-full px-2 py-1 bg-white/10 border border-white/20 rounded text-blue-400 text-sm font-bold focus:outline-none focus:border-blue-400"
                                  />
                                </div>
                              </div>
                            </div>
                          ) : (
                            // VIEW MODE
                            <div className="flex items-center justify-between">
                              <div className="space-y-1 flex-1">
                                <p className="text-base font-bold text-white/90">{item.name}</p>
                                <p className="text-sm text-white/40 font-medium">{item.quantity} units @ ₹{item.price.toFixed(2)}</p>
                              </div>
                              <div className="flex items-center gap-3">
                                <div className="text-right space-y-1">
                                  <p className="text-lg font-bold text-blue-400 tracking-tight">₹{item.total.toFixed(2)}</p>
                                  <div className="flex items-center gap-1.5 justify-end">
                                    <div className={`w-2 h-2 rounded-full ${item.confidence > 70 ? 'bg-emerald-500' : item.confidence > 50 ? 'bg-amber-500' : 'bg-rose-500'}`} />
                                    <span className={`text-[11px] font-bold ${item.confidence > 70 ? 'text-emerald-400' : item.confidence > 50 ? 'text-amber-400' : 'text-rose-400'}`}>{item.confidence}% Match</span>
                                  </div>
                                </div>
                                <button
                                  onClick={() => setEditingItemIndex(i)}
                                  className="p-2 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 transition-colors"
                                  title="Edit this item"
                                >
                                  <Edit2 size={16} />
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="p-7 rounded-[28px] bg-blue-600/10 border border-blue-500/20 flex justify-between items-center shadow-inner">
                    <div className="space-y-1">
                      <p className="text-xs text-blue-300 uppercase font-bold tracking-widest">Aggregated Total</p>
                      <p className="text-3xl font-bold text-white tracking-tighter">₹{extractedData.grandTotal?.toFixed(2)}</p>
                    </div>
                    <button
                      onClick={confirmBill}
                      className="gem-button px-8 py-4 flex items-center gap-2.5"
                    >
                      Commit <CheckCircle size={20} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BillUpload;
