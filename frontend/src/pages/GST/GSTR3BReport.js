import React, { useState } from 'react';
import { RefreshCw } from 'lucide-react';
import api, { formatCurrency } from '../../services/api';

const GSTR3BReport = ({ currentBranch }) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [year, setYear] = useState(new Date().getFullYear());

  const fetchReport = async () => {
    setLoading(true);
    try {
      const branchParam = currentBranch?.id ? `&branch_id=${currentBranch.id}` : '';
      const res = await api.get(`/gst/gstr3b?month=${month}&year=${year}${branchParam}`);
      setReport(res.data);
    } catch (e) { alert(e.response?.data?.detail || 'Error'); }
    finally { setLoading(false); }
  };

  const TaxRow = ({ label, data }) => (
    <tr><td>{label}</td><td className="numeric">{formatCurrency(data?.txval || 0)}</td><td className="numeric">{formatCurrency(data?.iamt || 0)}</td><td className="numeric">{formatCurrency(data?.camt || 0)}</td><td className="numeric">{formatCurrency(data?.samt || 0)}</td><td className="numeric">{formatCurrency(data?.csamt || 0)}</td></tr>
  );

  return (
    <div data-testid="gstr3b-report">
      <div className="page-header">
        <div><h1>GSTR-3B</h1><p className="page-subtitle">Monthly Summary Return</p></div>
        <div className="btn-group">
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
        <>
          <div className="card">
            <div className="card-header">3.1 - Outward Supplies</div>
            <div className="card-content">
              <table className="data-grid">
                <thead><tr><th>Nature of Supplies</th><th className="text-right">Taxable Value</th><th className="text-right">IGST</th><th className="text-right">CGST</th><th className="text-right">SGST</th><th className="text-right">CESS</th></tr></thead>
                <tbody>
                  <TaxRow label="(a) Outward taxable supplies" data={report.outward_taxable_supplies} />
                  <TaxRow label="(b) Outward taxable supplies (zero rated)" data={report.outward_zero_rated} />
                  <TaxRow label="(c) Other outward supplies (Nil rated, exempted)" data={report.outward_nil_rated} />
                  <TaxRow label="(d) Inward supplies (liable to reverse charge)" data={report.inward_reverse_charge} />
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <div className="card-header">4 - Eligible ITC</div>
            <div className="card-content">
              <table className="data-grid">
                <thead><tr><th>Details</th><th className="text-right">IGST</th><th className="text-right">CGST</th><th className="text-right">SGST</th></tr></thead>
                <tbody>
                  <tr><td>ITC Available</td><td className="numeric">{formatCurrency(report.eligible_itc?.iamt || 0)}</td><td className="numeric">{formatCurrency(report.eligible_itc?.camt || 0)}</td><td className="numeric">{formatCurrency(report.eligible_itc?.samt || 0)}</td></tr>
                  <tr><td>ITC Reversed</td><td className="numeric">{formatCurrency(report.ineligible_itc?.iamt || 0)}</td><td className="numeric">{formatCurrency(report.ineligible_itc?.camt || 0)}</td><td className="numeric">{formatCurrency(report.ineligible_itc?.samt || 0)}</td></tr>
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <div className="card-header">6 - Payment of Tax</div>
            <div className="card-content">
              <table className="data-grid">
                <thead><tr><th>Description</th><th className="text-right">IGST</th><th className="text-right">CGST</th><th className="text-right">SGST</th></tr></thead>
                <tbody>
                  <tr style={{fontWeight: 'bold', background: 'var(--bg-secondary)'}}>
                    <td>Tax Payable</td>
                    <td className="numeric">{formatCurrency(report.net_tax_liability?.iamt || 0)}</td>
                    <td className="numeric">{formatCurrency(report.net_tax_liability?.camt || 0)}</td>
                    <td className="numeric">{formatCurrency(report.net_tax_liability?.samt || 0)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default GSTR3BReport;
