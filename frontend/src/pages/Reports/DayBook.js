import React, { useState, useEffect } from 'react';
import api, { formatCurrency, formatDate, getTodayDate } from '../../services/api';

const DayBook = ({ currentBranch }) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [startDate, setStartDate] = useState(getTodayDate());
  const [endDate, setEndDate] = useState(getTodayDate());

  const fetchReport = async () => {
    setLoading(true);
    try {
      const branchParam = currentBranch?.id ? `&branch_id=${currentBranch.id}` : '';
      const res = await api.get(`/accounting/reports/day-book?start_date=${startDate}&end_date=${endDate}${branchParam}`);
      setReport(res.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchReport(); }, [currentBranch]);

  const voucherLabels = { journal: 'Journal', payment: 'Payment', receipt: 'Receipt', contra: 'Contra', sales: 'Sales', purchase: 'Purchase', debit_note: 'DN', credit_note: 'CN' };

  return (
    <div data-testid="day-book">
      <div className="page-header">
        <div><h1>Day Book</h1><p className="page-subtitle">All vouchers for selected period</p></div>
        <div className="btn-group">
          <input type="date" className="form-control" value={startDate} onChange={e => setStartDate(e.target.value)} style={{width: '140px'}} />
          <span style={{padding: '6px'}}>to</span>
          <input type="date" className="form-control" value={endDate} onChange={e => setEndDate(e.target.value)} style={{width: '140px'}} />
          <button className="btn btn-primary" onClick={fetchReport} disabled={loading}>{loading ? 'Loading...' : 'View'}</button>
        </div>
      </div>

      {report && (
        <div className="card">
          <div className="card-header">{report.total_vouchers} vouchers | Total Dr: {formatCurrency(report.total_debit)} | Total Cr: {formatCurrency(report.total_credit)}</div>
          <div className="card-content" style={{overflowX: 'auto'}}>
            <table className="data-grid">
              <thead><tr><th>Date</th><th>Voucher No.</th><th>Type</th><th>Account</th><th className="text-right">Debit</th><th className="text-right">Credit</th><th>Narration</th></tr></thead>
              <tbody>
                {report.vouchers.map(v => (
                  v.entries?.map((e, i) => (
                    <tr key={`${v.id}-${i}`}>
                      {i === 0 && <td rowSpan={v.entries.length}>{formatDate(v.voucher_date)}</td>}
                      {i === 0 && <td rowSpan={v.entries.length}><strong>{v.voucher_number}</strong></td>}
                      {i === 0 && <td rowSpan={v.entries.length}><span className="badge badge-info">{voucherLabels[v.voucher_type] || v.voucher_type}</span></td>}
                      <td>{e.ledger_name}</td>
                      <td className="numeric">{e.debit > 0 ? formatCurrency(e.debit) : '-'}</td>
                      <td className="numeric">{e.credit > 0 ? formatCurrency(e.credit) : '-'}</td>
                      {i === 0 && <td rowSpan={v.entries.length} style={{maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis'}}>{v.narration}</td>}
                    </tr>
                  ))
                ))}
              </tbody>
            </table>
            {report.vouchers.length === 0 && <div className="empty-state"><p>No vouchers found</p></div>}
          </div>
        </div>
      )}
    </div>
  );
};

export default DayBook;
