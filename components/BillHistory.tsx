
import React from 'react';
import {
  Search,
  Filter,
  Download,
  MoreVertical,
  Calendar,
  Eye,
  Trash2,
  FileText
} from 'lucide-react';
import { Bill } from '../types';

const BillHistory: React.FC<{ bills: Bill[] }> = ({ bills }) => {

  // Export to CSV
  const exportToCSV = () => {
    if (bills.length === 0) {
      alert('No bills to export!');
      return;
    }

    // CSV Headers
    const headers = ['Bill ID', 'Vendor', 'Date', 'Items Count', 'Total Amount (₹)', 'Confidence (%)', 'Status'];

    // CSV Rows
    const rows = bills.map(bill => [
      bill.id,
      bill.vendorName || 'Unknown',
      bill.date,
      bill.items.length,
      bill.grandTotal.toFixed(2),
      bill.overallConfidence,
      bill.status
    ]);

    // Combine headers and rows
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    // Create and download file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `bills_export_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Export to Excel (using HTML table method)
  const exportToExcel = () => {
    if (bills.length === 0) {
      alert('No bills to export!');
      return;
    }

    // Create HTML table
    let tableHTML = `
      <table>
        <thead>
          <tr>
            <th>Bill ID</th>
            <th>Vendor</th>
            <th>Date</th>
            <th>Items Count</th>
            <th>Total Amount (₹)</th>
            <th>Confidence (%)</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
    `;

    bills.forEach(bill => {
      tableHTML += `
        <tr>
          <td>${bill.id}</td>
          <td>${bill.vendorName || 'Unknown'}</td>
          <td>${bill.date}</td>
          <td>${bill.items.length}</td>
          <td>${bill.grandTotal.toFixed(2)}</td>
          <td>${bill.overallConfidence}</td>
          <td>${bill.status}</td>
        </tr>
      `;
    });

    tableHTML += `
        </tbody>
      </table>
    `;

    // Create Excel file using data URI
    const excelContent = `
      <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel">
        <head>
          <meta charset="UTF-8">
          <!--[if gte mso 9]>
          <xml>
            <x:ExcelWorkbook>
              <x:ExcelWorksheets>
                <x:ExcelWorksheet>
                  <x:Name>Bills</x:Name>
                  <x:WorksheetOptions>
                    <x:DisplayGridlines/>
                  </x:WorksheetOptions>
                </x:ExcelWorksheet>
              </x:ExcelWorksheets>
            </x:ExcelWorkbook>
          </xml>
          <![endif]-->
        </head>
        <body>
          ${tableHTML}
        </body>
      </html>
    `;

    const blob = new Blob([excelContent], { type: 'application/vnd.ms-excel' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `bills_export_${new Date().toISOString().split('T')[0]}.xls`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Bill History</h1>
          <p className="text-slate-400">View and manage all your digitized records</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-4 py-2 bg-white/5 text-slate-300 rounded-xl hover:bg-white/10 transition-all">
            <Filter size={18} /> Filters
          </button>
          <button
            onClick={exportToCSV}
            className="flex items-center gap-2 px-4 py-2 bg-white/5 text-slate-300 rounded-xl hover:bg-white/10 transition-all hover:text-white"
          >
            <Download size={18} /> Export CSV
          </button>
          <button
            onClick={exportToExcel}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 rounded-xl hover:bg-emerald-600/30 transition-all"
          >
            <Download size={18} /> Export Excel
          </button>
        </div>
      </div>

      <div className="matte-card rounded-3xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-white/5 text-slate-400 text-xs uppercase tracking-wider font-bold">
                <th className="px-8 py-5">Bill / ID</th>
                <th className="px-8 py-5">Vendor</th>
                <th className="px-8 py-5">Date</th>
                <th className="px-8 py-5">Items</th>
                <th className="px-8 py-5">Total</th>
                <th className="px-8 py-5">Confidence</th>
                <th className="px-8 py-5 text-center">Status</th>
                <th className="px-8 py-5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {bills.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-8 py-20 text-center text-slate-500">
                    <div className="flex flex-col items-center">
                      <FileText size={48} className="mb-4 opacity-20" />
                      <p>No bills processed yet.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                bills.map((bill) => (
                  <tr key={bill.id} className="group hover:bg-white/5 transition-all">
                    <td className="px-8 py-5">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-white/5 rounded-xl overflow-hidden border border-white/10 group-hover:scale-110 transition-transform">
                          <img src={bill.imageUrl} className="w-full h-full object-cover" alt="Bill" />
                        </div>
                        <div>
                          <p className="text-sm font-bold text-white uppercase">{bill.id}</p>
                          <p className="text-[10px] text-slate-500 font-medium">IMAGE_ID_{bill.id.substr(0, 4)}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-8 py-5">
                      <span className="text-sm font-medium text-slate-300">{bill.vendorName || 'Generic Store'}</span>
                    </td>
                    <td className="px-8 py-5">
                      <div className="flex items-center gap-2 text-sm text-slate-400">
                        <Calendar size={14} />
                        {bill.date}
                      </div>
                    </td>
                    <td className="px-8 py-5">
                      <span className="text-sm text-slate-400">{bill.items.length} items</span>
                    </td>
                    <td className="px-8 py-5">
                      <span className="text-sm font-bold text-white">₹{bill.grandTotal.toFixed(2)}</span>
                    </td>
                    <td className="px-8 py-5">
                      <div className="w-full max-w-[80px] space-y-1">
                        <div className="flex justify-between text-[10px] font-bold text-emerald-400">
                          <span>{bill.overallConfidence}%</span>
                        </div>
                        <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                          <div className={`h-full bg-emerald-500`} style={{ width: `${bill.overallConfidence}%` }} />
                        </div>
                      </div>
                    </td>
                    <td className="px-8 py-5 text-center">
                      <span className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${bill.status === 'VERIFIED' ? 'bg-emerald-500/20 text-emerald-400' :
                        bill.status === 'PENDING' ? 'bg-amber-500/20 text-amber-400' : 'bg-rose-500/20 text-rose-400'
                        }`}>
                        {bill.status}
                      </span>
                    </td>
                    <td className="px-8 py-5 text-right">
                      <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button className="p-2 bg-white/5 text-slate-400 hover:text-white rounded-lg transition-colors">
                          <Eye size={16} />
                        </button>
                        <button className="p-2 bg-white/5 text-slate-400 hover:text-rose-400 rounded-lg transition-colors">
                          <Trash2 size={16} />
                        </button>
                        <button className="p-2 text-slate-400 hover:text-white transition-colors">
                          <MoreVertical size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default BillHistory;
