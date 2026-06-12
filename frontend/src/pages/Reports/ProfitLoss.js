import React, { useState, useEffect } from 'react';
import { RefreshCw, Printer } from 'lucide-react';
import api, { formatCurrency, getTodayDate } from '../../services/api';

const ProfitLoss = ({ currentBranch }) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [startDate, setStartDate] = useState('2025-04-01');
  const [endDate, setEndDate] = useState(getTodayDate());

  const fetchReport = async () => {
    setLoading(true);
    try {
      const branchParam = currentBranch?.id ? `&branch_id=${currentBranch.id}` : '';
      const res = await api.get(`/accounting/reports/profit-loss?start_date=${startDate}&end_date=${endDate}${branchParam}`);
      setReport(res.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchReport(); }, [currentBranch]);

  return (
    <div data-testid="profit-loss">
      <div className="page-header">
        <div><h1>Profit & Loss Statement</h1><p className="page-subtitle">{currentBranch?.name || 'All Branches'}</p></div>
        <div className="btn-group">
          <input type="date" className="form-control" value={startDate} onChange={e => setStartDate(e.target.value)} style={{width: '140px'}} />
          <span style={{padding: '6px'}}>to</span>
          <input type="date" className="form-control" value={endDate} onChange={e => setEndDate(e.target.value)} style={{width: '140px'}} />
          <button className="btn btn-primary" onClick={fetchReport} disabled={loading}><RefreshCw size={14} /> {loading ? 'Loading...' : 'Refresh'}</button>
          <button className="btn btn-secondary" onClick={() => window.print()}><Printer size={14} /> Print</button>
        </div>
      </div>

      {report && (
        <div className="grid-2">
          <div className="card">
            <div className="card-header">Income</div>
            <div className="card-content">
              <table className="data-grid">
                <tbody>
                  {report.income_items.map((group, i) => (
                    <React.Fragment key={i}>
                      <tr style={{background: 'var(--bg-secondary)', fontWeight: 'bold'}}><td>{group.group_name}</td><td className="numeric"></td></tr>
                      {group.ledgers.map((l, j) => (<tr key={j}><td style={{paddingLeft: '24px'}}>{l.name}</td><td className="numeric">{formatCurrency(l.amount)}</td></tr>))}
                      <tr style={{fontWeight: 600, borderTop: '1px solid var(--border-color)'}}><td style={{paddingLeft: '24px'}}>Subtotal</td><td className="numeric">{formatCurrency(group.total)}</td></tr>
                    </React.Fragment>
                  ))}
                </tbody>
                <tfoot><tr style={{fontWeight: 'bold', background: 'var(--bg-grid-header)', color: 'white'}}><td>Total Income</td><td className="numeric">{formatCurrency(report.total_income)}</td></tr></tfoot>
              </table>
            </div>
          </div>

          <div className="card">
            <div className="card-header">Expenses</div>
            <div className="card-content">
              <table className="data-grid">
                <tbody>
                  {report.expense_items.map((group, i) => (
                    <React.Fragment key={i}>
                      <tr style={{background: 'var(--bg-secondary)', fontWeight: 'bold'}}><td>{group.group_name}</td><td className="numeric"></td></tr>
                      {group.ledgers.map((l, j) => (<tr key={j}><td style={{paddingLeft: '24px'}}>{l.name}</td><td className="numeric">{formatCurrency(l.amount)}</td></tr>))}
                      <tr style={{fontWeight: 600, borderTop: '1px solid var(--border-color)'}}><td style={{paddingLeft: '24px'}}>Subtotal</td><td className="numeric">{formatCurrency(group.total)}</td></tr>
                    </React.Fragment>
                  ))}
                </tbody>
                <tfoot><tr style={{fontWeight: 'bold', background: 'var(--bg-grid-header)', color: 'white'}}><td>Total Expenses</td><td className="numeric">{formatCurrency(report.total_expense)}</td></tr></tfoot>
              </table>
            </div>
          </div>

          <div className="card" style={{gridColumn: '1 / -1'}}>
            <div className="card-content">
              <div className="totals-panel" style={{maxWidth: '400px', margin: '0 auto'}}>
                <div className="totals-row highlight" style={{fontSize: '16px'}}>
                  <span className="label">{report.net_profit >= 0 ? 'Net Profit' : 'Net Loss'}</span>
                  <span className="value" style={{color: report.net_profit >= 0 ? 'var(--success)' : 'var(--danger)'}}>{formatCurrency(Math.abs(report.net_profit))}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProfitLoss;
