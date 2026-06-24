import React, { useState, useEffect } from 'react';
import { Search, FileText, Printer } from 'lucide-react';
import api, { formatCurrency, getTodayDate } from '../../services/api';

const LedgerStatement = ({ currentBranch }) => {
  const [ledgers, setLedgers] = useState([]);
  const [selectedLedger, setSelectedLedger] = useState('');
  const [statement, setStatement] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const [filters, setFilters] = useState({
    start_date: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().slice(0, 10),
    end_date: getTodayDate()
  });

  useEffect(() => {
    fetchLedgers();
  }, []);

  const fetchLedgers = async () => {
    try {
      const response = await api.get('/accounting/ledgers');
      setLedgers(response.data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const fetchStatement = async () => {
    if (!selectedLedger) {
      alert('Select a ledger');
      return;
    }
    
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      
      const response = await api.get(`/reports/ledger-account/${selectedLedger}?${params.toString()}`);
      setStatement(response.data);
    } catch (error) {
      alert(error.response?.data?.detail || 'Error fetching statement');
    } finally {
      setLoading(false);
    }
  };

  const printStatement = () => {
    window.print();
  };

  return (
    <div data-testid="ledger-statement">
      <div className="page-header">
        <div>
          <h1>Ledger Account Statement</h1>
          <p className="page-subtitle">Detailed ledger transactions with running balance</p>
        </div>
        {statement && (
          <button className="btn btn-secondary" onClick={printStatement}>
            <Printer size={16} /> Print
          </button>
        )}
      </div>

      <div className="card" style={{ marginBottom: '16px' }}>
        <div className="card-content">
          <div className="form-row">
            <div className="form-group" style={{ flex: 2 }}>
              <label className="form-label">Select Ledger *</label>
              <select className="form-control" value={selectedLedger}
                onChange={e => setSelectedLedger(e.target.value)}>
                <option value="">-- Select Ledger --</option>
                {ledgers.map(ledger => (
                  <option key={ledger.id} value={ledger.id}>
                    {ledger.name} ({ledger.group_name})
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group" style={{ maxWidth: '150px' }}>
              <label className="form-label">From Date</label>
              <input type="date" className="form-control" value={filters.start_date}
                onChange={e => setFilters({...filters, start_date: e.target.value})} />
            </div>
            <div className="form-group" style={{ maxWidth: '150px' }}>
              <label className="form-label">To Date</label>
              <input type="date" className="form-control" value={filters.end_date}
                onChange={e => setFilters({...filters, end_date: e.target.value})} />
            </div>
            <div className="form-group" style={{ alignSelf: 'flex-end' }}>
              <button className="btn btn-primary" onClick={fetchStatement} disabled={loading}>
                <Search size={16} /> {loading ? 'Loading...' : 'View Statement'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {statement && (
        <div className="card print-area">
          <div className="card-header">
            <div>
              <strong>{statement.ledger?.name}</strong>
              <span style={{ marginLeft: '16px', color: 'var(--text-muted)' }}>
                {statement.ledger?.group_name} | {statement.ledger?.account_type}
              </span>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              {statement.period?.start_date} to {statement.period?.end_date}
            </div>
          </div>
          <div className="card-content">
            <div className="grid-3" style={{ marginBottom: '16px' }}>
              <div className="mini-stat">
                <span className="label">Opening Balance</span>
                <span className="value">{formatCurrency(statement.opening_balance)}</span>
              </div>
              <div className="mini-stat">
                <span className="label">Total Transactions</span>
                <span className="value">{statement.total_transactions}</span>
              </div>
              <div className="mini-stat">
                <span className="label">Closing Balance</span>
                <span className="value">{formatCurrency(statement.closing_balance)}</span>
              </div>
            </div>

            <table className="data-grid">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Voucher No.</th>
                  <th>Type</th>
                  <th>Narration</th>
                  <th className="text-right">Debit</th>
                  <th className="text-right">Credit</th>
                  <th className="text-right">Balance</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ background: 'var(--bg-secondary)', fontWeight: 'bold' }}>
                  <td colSpan={4}>Opening Balance</td>
                  <td className="numeric">{statement.opening_balance >= 0 ? formatCurrency(statement.opening_balance) : ''}</td>
                  <td className="numeric">{statement.opening_balance < 0 ? formatCurrency(Math.abs(statement.opening_balance)) : ''}</td>
                  <td className="numeric">{formatCurrency(statement.opening_balance)}</td>
                </tr>
                {statement.transactions?.map((trans, idx) => (
                  <tr key={trans.id || idx}>
                    <td>{trans.voucher_date}</td>
                    <td><strong>{trans.voucher_number}</strong></td>
                    <td><span className="badge badge-secondary">{trans.voucher_type?.toUpperCase()}</span></td>
                    <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>{trans.narration || '-'}</td>
                    <td className="numeric">{trans.debit > 0 ? formatCurrency(trans.debit) : ''}</td>
                    <td className="numeric">{trans.credit > 0 ? formatCurrency(trans.credit) : ''}</td>
                    <td className="numeric" style={{ fontWeight: 'bold' }}>{formatCurrency(trans.running_balance)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr style={{ background: 'var(--bg-secondary)', fontWeight: 'bold' }}>
                  <td colSpan={4}>Closing Balance</td>
                  <td className="numeric">{formatCurrency(statement.total_debit)}</td>
                  <td className="numeric">{formatCurrency(statement.total_credit)}</td>
                  <td className="numeric">{formatCurrency(statement.closing_balance)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default LedgerStatement;
