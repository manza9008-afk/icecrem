import React, { useState, useEffect } from 'react';
import { Download, RefreshCw } from 'lucide-react';
import api, { formatCurrency } from '../../services/api';

const GSTR1Report = ({ currentBranch }) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [year, setYear] = useState(new Date().getFullYear());

  const fetchReport = async () => {
    setLoading(true);
    try {
      const branchParam = currentBranch?.id ? `&branch_id=${currentBranch.id}` : '';
      const res = await api.get(`/gst/gstr1?month=${month}&year=${year}${branchParam}`);
      setReport(res.data);
    } catch (e) { console.error(e); alert(e.response?.data?.detail || 'Error'); }
    finally { setLoading(false); }
  };

  const handleExport = async () => {
    try {
      const branchParam = currentBranch?.id ? `&branch_id=${currentBranch.id}` : '';
      const res = await api.get(`/gst/gstr1/export?month=${month}&year=${year}${branchParam}`);
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = `GSTR1_${month.toString().padStart(2,'0')}${year}.json`; a.click();
    } catch (e) { alert('Export failed'); }
  };

  return (
    <div data-testid="gstr1-report">
      <div className="page-header">
        <div><h1>GSTR-1</h1><p className="page-subtitle">Outward Supplies Return</p></div>
        <div className="btn-group">
          <select className="form-control" value={month} onChange={e => setMonth(parseInt(e.target.value))} style={{width: '120px'}}>
            {[1,2,3,4,5,6,7,8,9,10,11,12].map(m => <option key={m} value={m}>{new Date(2000, m-1).toLocaleString('default', {month: 'long'})}</option>)}
          </select>
          <select className="form-control" value={year} onChange={e => setYear(parseInt(e.target.value))} style={{width: '100px'}}>
            {[2024, 2025, 2026].map(y => <option key={y} value={y}>{y}</option>)}
          </select>
          <button className="btn btn-primary" onClick={fetchReport} disabled={loading}><RefreshCw size={14} /> {loading ? 'Loading...' : 'Generate'}</button>
          {report && <button className="btn btn-success" onClick={handleExport}><Download size={14} /> Export JSON</button>}
        </div>
      </div>

      {report && (
        <>
          <div className="stats-grid">
            <div className="stat-card"><div><div className="stat-label">GSTIN</div><div className="stat-value" style={{fontSize: '14px'}}>{report.gstin}</div></div></div>
            <div className="stat-card"><div><div className="stat-label">Filing Period</div><div className="stat-value" style={{fontSize: '14px'}}>{report.fp}</div></div></div>
            <div className="stat-card"><div><div className="stat-label">B2B Invoices</div><div className="stat-value">{report.b2b?.length || 0}</div></div></div>
            <div className="stat-card"><div><div className="stat-label">B2C Entries</div><div className="stat-value">{report.b2cs?.length || 0}</div></div></div>
          </div>

          <div className="card">
            <div className="card-header">B2B - Supplies to Registered Dealers</div>
            <div className="card-content">
              <table className="data-grid">
                <thead><tr><th>GSTIN</th><th>Invoices</th><th className="text-right">Taxable Value</th><th className="text-right">CGST</th><th className="text-right">SGST</th><th className="text-right">IGST</th></tr></thead>
                <tbody>
                  {report.b2b?.map((b, i) => {
                    const totals = b.inv.reduce((acc, inv) => {
                      inv.itms?.forEach(it => { acc.txval += it.itm_det?.txval || 0; acc.camt += it.itm_det?.camt || 0; acc.samt += it.itm_det?.samt || 0; acc.iamt += it.itm_det?.iamt || 0; });
                      return acc;
                    }, { txval: 0, camt: 0, samt: 0, iamt: 0 });
                    return (
                      <tr key={i}><td><code>{b.ctin}</code></td><td>{b.inv.length}</td><td className="numeric">{formatCurrency(totals.txval)}</td><td className="numeric">{formatCurrency(totals.camt)}</td><td className="numeric">{formatCurrency(totals.samt)}</td><td className="numeric">{formatCurrency(totals.iamt)}</td></tr>
                    );
                  })}
                </tbody>
              </table>
              {(!report.b2b || report.b2b.length === 0) && <div className="empty-state"><p>No B2B transactions</p></div>}
            </div>
          </div>

          <div className="card">
            <div className="card-header">HSN Summary</div>
            <div className="card-content">
              <table className="data-grid">
                <thead><tr><th>HSN</th><th>Description</th><th className="text-right">Qty</th><th className="text-right">Taxable Value</th><th className="text-right">Total Tax</th></tr></thead>
                <tbody>
                  {report.hsn?.data?.map((h, i) => (
                    <tr key={i}><td><code>{h.hsn_sc}</code></td><td>{h.desc}</td><td className="numeric">{h.qty}</td><td className="numeric">{formatCurrency(h.txval)}</td><td className="numeric">{formatCurrency(h.camt + h.samt + h.iamt)}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default GSTR1Report;
