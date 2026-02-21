import React, { useState, useEffect } from 'react';
import { RefreshCw, Printer } from 'lucide-react';
import api, { formatCurrency, getTodayDate } from '../../services/api';

const BalanceSheet = ({ currentBranch }) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [asOnDate, setAsOnDate] = useState(getTodayDate());

  const fetchReport = async () => {
    setLoading(true);
    try {
      const branchParam = currentBranch?.id ? `&branch_id=${currentBranch.id}` : '';
      const res = await api.get(`/accounting/reports/balance-sheet?as_on_date=${asOnDate}${branchParam}`);
      setReport(res.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchReport(); }, [currentBranch]);

  const renderGroup = (items, label) => (
    <div className="card">
      <div className="card-header">{label}</div>
      <div className="card-content">
        <table className="data-grid">
          <tbody>
            {items.map((group, i) => (
              <React.Fragment key={i}>
                <tr style={{background: 'var(--bg-secondary)', fontWeight: 'bold'}}><td>{group.group_name}</td><td className="numeric"></td></tr>
                {group.ledgers.map((l, j) => (<tr key={j}><td style={{paddingLeft: '24px'}}>{l.name}</td><td className="numeric">{formatCurrency(l.amount)}</td></tr>))}
                <tr style={{fontWeight: 600}}><td style={{paddingLeft: '24px'}}>Subtotal</td><td className="numeric">{formatCurrency(group.total)}</td></tr>
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  return (
    <div data-testid="balance-sheet">
      <div className="page-header">
        <div><h1>Balance Sheet</h1><p className="page-subtitle">{currentBranch?.name || 'All Branches'}</p></div>
        <div className="btn-group">
          <input type="date" className="form-control" value={asOnDate} onChange={e => setAsOnDate(e.target.value)} style={{width: '150px'}} />
          <button className="btn btn-primary" onClick={fetchReport} disabled={loading}><RefreshCw size={14} /> {loading ? 'Loading...' : 'Refresh'}</button>
          <button className="btn btn-secondary" onClick={() => window.print()}><Printer size={14} /> Print</button>
        </div>
      </div>

      {report && (
        <>
          <div className="grid-2">
            {renderGroup(report.asset_items, 'Assets')}
            <div>
              {renderGroup(report.liability_items, 'Liabilities')}
              {renderGroup(report.capital_items, 'Capital')}
            </div>
          </div>

          <div className="card" style={{marginTop: '16px'}}>
            <div className="card-content">
              <div className="grid-3" style={{textAlign: 'center'}}>
                <div><div className="stat-label">Total Assets</div><div className="stat-value">{formatCurrency(report.total_assets)}</div></div>
                <div><div className="stat-label">Total Liabilities + Capital</div><div className="stat-value">{formatCurrency(report.total_liabilities_and_capital)}</div></div>
                <div><div className="stat-label">Net Profit</div><div className="stat-value" style={{color: report.net_profit >= 0 ? 'var(--success)' : 'var(--danger)'}}>{formatCurrency(report.net_profit)}</div></div>
              </div>
              {report.is_balanced && <div className="badge badge-success" style={{display: 'block', textAlign: 'center', marginTop: '12px'}}>BALANCED</div>}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default BalanceSheet;
