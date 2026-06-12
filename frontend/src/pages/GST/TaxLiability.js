import React, { useState } from 'react';
import { RefreshCw } from 'lucide-react';
import api, { formatCurrency } from '../../services/api';

const TaxLiability = ({ currentBranch }) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [year, setYear] = useState(new Date().getFullYear());

  const fetchReport = async () => {
    setLoading(true);
    try {
      const branchParam = currentBranch?.id ? `&branch_id=${currentBranch.id}` : '';
      const res = await api.get(`/gst/tax-liability?month=${month}&year=${year}${branchParam}`);
      setReport(res.data);
    } catch (e) { alert(e.response?.data?.detail || 'Error'); }
    finally { setLoading(false); }
  };

  return (
    <div data-testid="tax-liability">
      <div className="page-header">
        <div><h1>Tax Liability</h1><p className="page-subtitle">Monthly GST liability calculation</p></div>
        <div className="btn-group">
          <select className="form-control" value={month} onChange={e => setMonth(parseInt(e.target.value))} style={{width: '120px'}}>
            {[1,2,3,4,5,6,7,8,9,10,11,12].map(m => <option key={m} value={m}>{new Date(2000, m-1).toLocaleString('default', {month: 'long'})}</option>)}
          </select>
          <select className="form-control" value={year} onChange={e => setYear(parseInt(e.target.value))} style={{width: '100px'}}>
            {[2024, 2025, 2026].map(y => <option key={y} value={y}>{y}</option>)}
          </select>
          <button className="btn btn-primary" onClick={fetchReport} disabled={loading}><RefreshCw size={14} /> {loading ? 'Loading...' : 'Calculate'}</button>
        </div>
      </div>

      {report && (
        <div className="grid-2">
          <div className="card">
            <div className="card-header">Output Tax (on Sales)</div>
            <div className="card-content">
              <table className="data-grid">
                <tbody>
                  <tr><td>CGST</td><td className="numeric">{formatCurrency(report.output_tax?.cgst)}</td></tr>
                  <tr><td>SGST</td><td className="numeric">{formatCurrency(report.output_tax?.sgst)}</td></tr>
                  <tr><td>IGST</td><td className="numeric">{formatCurrency(report.output_tax?.igst)}</td></tr>
                  <tr><td>CESS</td><td className="numeric">{formatCurrency(report.output_tax?.cess)}</td></tr>
                </tbody>
                <tfoot><tr style={{fontWeight: 'bold', background: 'var(--bg-secondary)'}}><td>Total Output Tax</td><td className="numeric">{formatCurrency(report.output_tax?.total)}</td></tr></tfoot>
              </table>
            </div>
          </div>

          <div className="card">
            <div className="card-header">Input Tax Credit (on Purchases)</div>
            <div className="card-content">
              <table className="data-grid">
                <tbody>
                  <tr><td>CGST</td><td className="numeric">{formatCurrency(report.input_tax_credit?.cgst)}</td></tr>
                  <tr><td>SGST</td><td className="numeric">{formatCurrency(report.input_tax_credit?.sgst)}</td></tr>
                  <tr><td>IGST</td><td className="numeric">{formatCurrency(report.input_tax_credit?.igst)}</td></tr>
                  <tr><td>CESS</td><td className="numeric">{formatCurrency(report.input_tax_credit?.cess)}</td></tr>
                </tbody>
                <tfoot><tr style={{fontWeight: 'bold', background: 'var(--bg-secondary)'}}><td>Total ITC</td><td className="numeric">{formatCurrency(report.input_tax_credit?.total)}</td></tr></tfoot>
              </table>
            </div>
          </div>

          <div className="card" style={{gridColumn: '1 / -1'}}>
            <div className="card-header">Net Tax Liability</div>
            <div className="card-content">
              <table className="data-grid">
                <thead><tr><th>Tax Type</th><th className="text-right">Output Tax</th><th className="text-right">Less: ITC</th><th className="text-right">Net Payable</th><th className="text-right">Carry Forward</th></tr></thead>
                <tbody>
                  <tr><td>CGST</td><td className="numeric">{formatCurrency(report.output_tax?.cgst)}</td><td className="numeric">{formatCurrency(report.input_tax_credit?.cgst)}</td><td className="numeric" style={{fontWeight: 'bold', color: 'var(--danger)'}}>{formatCurrency(report.net_liability?.cgst)}</td><td className="numeric" style={{color: 'var(--success)'}}>{formatCurrency(report.itc_carry_forward?.cgst)}</td></tr>
                  <tr><td>SGST</td><td className="numeric">{formatCurrency(report.output_tax?.sgst)}</td><td className="numeric">{formatCurrency(report.input_tax_credit?.sgst)}</td><td className="numeric" style={{fontWeight: 'bold', color: 'var(--danger)'}}>{formatCurrency(report.net_liability?.sgst)}</td><td className="numeric" style={{color: 'var(--success)'}}>{formatCurrency(report.itc_carry_forward?.sgst)}</td></tr>
                  <tr><td>IGST</td><td className="numeric">{formatCurrency(report.output_tax?.igst)}</td><td className="numeric">{formatCurrency(report.input_tax_credit?.igst)}</td><td className="numeric" style={{fontWeight: 'bold', color: 'var(--danger)'}}>{formatCurrency(report.net_liability?.igst)}</td><td className="numeric" style={{color: 'var(--success)'}}>{formatCurrency(report.itc_carry_forward?.igst)}</td></tr>
                  <tr><td>CESS</td><td className="numeric">{formatCurrency(report.output_tax?.cess)}</td><td className="numeric">{formatCurrency(report.input_tax_credit?.cess)}</td><td className="numeric" style={{fontWeight: 'bold', color: 'var(--danger)'}}>{formatCurrency(report.net_liability?.cess)}</td><td className="numeric">-</td></tr>
                </tbody>
                <tfoot>
                  <tr style={{fontWeight: 'bold', background: 'var(--bg-grid-header)', color: 'white'}}>
                    <td>TOTAL</td>
                    <td className="numeric">{formatCurrency(report.output_tax?.total)}</td>
                    <td className="numeric">{formatCurrency(report.input_tax_credit?.total)}</td>
                    <td className="numeric">{formatCurrency(report.net_liability?.total)}</td>
                    <td className="numeric"></td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TaxLiability;
