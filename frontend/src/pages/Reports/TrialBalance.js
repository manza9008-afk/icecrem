import React, { useState, useEffect } from 'react';
import { RefreshCw, Printer } from 'lucide-react';
import api, { formatCurrency, getTodayDate } from '../../services/api';

const TrialBalance = ({ currentBranch }) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [asOnDate, setAsOnDate] = useState(getTodayDate());

  const fetchReport = async () => {
    setLoading(true);
    try {
      const branchParam = currentBranch?.id ? `&branch_id=${currentBranch.id}` : '';
      const res = await api.get(`/accounting/reports/trial-balance?as_on_date=${asOnDate}${branchParam}`);
      setReport(res.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchReport(); }, [currentBranch]);

  const groupByType = (items) => {
    const grouped = {};
    items.forEach(item => {
      if (!grouped[item.account_type]) grouped[item.account_type] = [];
      grouped[item.account_type].push(item);
    });
    return grouped;
  };

  const typeOrder = ['Asset', 'Liability', 'Capital', 'Income', 'Expense'];

  return (
    <div data-testid="trial-balance">
      <div className="page-header">
        <div><h1>Trial Balance</h1><p className="page-subtitle">{currentBranch?.name || 'All Branches'}</p></div>
        <div className="btn-group">
          <input type="date" className="form-control" value={asOnDate} onChange={e => setAsOnDate(e.target.value)} style={{width: '150px'}} />
          <button className="btn btn-primary" onClick={fetchReport} disabled={loading}><RefreshCw size={14} /> {loading ? 'Loading...' : 'Refresh'}</button>
          <button className="btn btn-secondary" onClick={() => window.print()}><Printer size={14} /> Print</button>
        </div>
      </div>

      {report && (
        <div className="card">
          <div className="card-header">
            Trial Balance as on {report.as_on_date}
            {report.is_balanced ? <span className="badge badge-success" style={{marginLeft: '12px'}}>BALANCED</span> : <span className="badge badge-danger" style={{marginLeft: '12px'}}>NOT BALANCED (Diff: {formatCurrency(report.difference)})</span>}
          </div>
          <div className="card-content" style={{overflowX: 'auto'}}>
            <table className="data-grid">
              <thead><tr><th>Particulars</th><th className="text-right">Debit (Dr)</th><th className="text-right">Credit (Cr)</th></tr></thead>
              <tbody>
                {typeOrder.map(type => {
                  const items = report.items.filter(i => i.account_type === type && (i.closing_debit > 0 || i.closing_credit > 0));
                  if (items.length === 0) return null;
                  return (
                    <React.Fragment key={type}>
                      <tr style={{background: 'var(--bg-secondary)', fontWeight: 'bold'}}><td colSpan={3}>{type}s</td></tr>
                      {items.map((item, i) => (
                        <tr key={i}>
                          <td style={{paddingLeft: '24px'}}>{item.ledger_name} <span style={{color: 'var(--text-muted)', fontSize: '10px'}}>({item.group_name})</span></td>
                          <td className="numeric">{item.closing_debit > 0 ? formatCurrency(item.closing_debit) : '-'}</td>
                          <td className="numeric">{item.closing_credit > 0 ? formatCurrency(item.closing_credit) : '-'}</td>
                        </tr>
                      ))}
                    </React.Fragment>
                  );
                })}
              </tbody>
              <tfoot>
                <tr style={{fontWeight: 'bold', background: 'var(--bg-grid-header)', color: 'white'}}>
                  <td>TOTAL</td>
                  <td className="numeric">{formatCurrency(report.total_closing_debit)}</td>
                  <td className="numeric">{formatCurrency(report.total_closing_credit)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default TrialBalance;
