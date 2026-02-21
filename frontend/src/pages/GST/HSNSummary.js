import React, { useState } from 'react';
import { RefreshCw } from 'lucide-react';
import api, { formatCurrency, formatNumber } from '../../services/api';

const HSNSummary = ({ currentBranch }) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [year, setYear] = useState(new Date().getFullYear());
  const [reportType, setReportType] = useState('sales');

  const fetchReport = async () => {
    setLoading(true);
    try {
      const branchParam = currentBranch?.id ? `&branch_id=${currentBranch.id}` : '';
      const res = await api.get(`/gst/hsn-summary?month=${month}&year=${year}&report_type=${reportType}${branchParam}`);
      setReport(res.data);
    } catch (e) { alert(e.response?.data?.detail || 'Error'); }
    finally { setLoading(false); }
  };

  return (
    <div data-testid="hsn-summary">
      <div className="page-header">
        <div><h1>HSN Summary</h1><p className="page-subtitle">HSN-wise summary for GST filing</p></div>
        <div className="btn-group">
          <select className="form-control" value={reportType} onChange={e => setReportType(e.target.value)} style={{width: '120px'}}>
            <option value="sales">Sales</option>
            <option value="purchase">Purchase</option>
          </select>
          <select className="form-control" value={month} onChange={e => setMonth(parseInt(e.target.value))} style={{width: '120px'}}>
            {[1,2,3,4,5,6,7,8,9,10,11,12].map(m => <option key={m} value={m}>{new Date(2000, m-1).toLocaleString('default', {month: 'long'})}</option>)}
          </select>
          <select className="form-control" value={year} onChange={e => setYear(parseInt(e.target.value))} style={{width: '100px'}}>
            {[2024, 2025, 2026].map(y => <option key={y} value={y}>{y}</option>)}
          </select>
          <button className="btn btn-primary" onClick={fetchReport} disabled={loading}><RefreshCw size={14} /> {loading ? 'Loading...' : 'Generate'}</button>
        </div>
      </div>

      {report && (
        <div className="card">
          <div className="card-header">HSN Summary - {report.report_type.toUpperCase()} ({report.month}/{report.year})</div>
          <div className="card-content">
            <table className="data-grid">
              <thead><tr><th>HSN Code</th><th>Description</th><th className="text-right">Qty</th><th className="text-right">Taxable Value</th><th className="text-right">CGST</th><th className="text-right">SGST</th><th className="text-right">IGST</th><th className="text-right">Total Tax</th></tr></thead>
              <tbody>
                {report.items?.map((h, i) => (
                  <tr key={i}><td><code>{h.hsn_code}</code></td><td>{h.description}</td><td className="numeric">{formatNumber(h.quantity)}</td><td className="numeric">{formatCurrency(h.taxable_value)}</td><td className="numeric">{formatCurrency(h.cgst_amount)}</td><td className="numeric">{formatCurrency(h.sgst_amount)}</td><td className="numeric">{formatCurrency(h.igst_amount)}</td><td className="numeric">{formatCurrency(h.total_tax)}</td></tr>
                ))}
              </tbody>
              <tfoot>
                <tr style={{fontWeight: 'bold', background: 'var(--bg-grid-header)', color: 'white'}}>
                  <td colSpan={3}>TOTAL</td>
                  <td className="numeric">{formatCurrency(report.totals?.taxable_value || 0)}</td>
                  <td colSpan={3}></td>
                  <td className="numeric">{formatCurrency(report.totals?.total_tax || 0)}</td>
                </tr>
              </tfoot>
            </table>
            {(!report.items || report.items.length === 0) && <div className="empty-state"><p>No HSN data found</p></div>}
          </div>
        </div>
      )}
    </div>
  );
};

export default HSNSummary;
