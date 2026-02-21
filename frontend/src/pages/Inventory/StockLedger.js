import React, { useState, useEffect } from 'react';
import api, { formatCurrency, formatNumber, formatDate } from '../../services/api';

const StockLedger = ({ currentBranch }) => {
  const [items, setItems] = useState([]);
  const [selectedItem, setSelectedItem] = useState('');
  const [ledger, setLedger] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { fetchItems(); }, []);

  const fetchItems = async () => {
    try { const res = await api.get('/inventory/items'); setItems(res.data); } 
    catch (e) { console.error(e); }
  };

  const fetchLedger = async () => {
    if (!selectedItem) return;
    setLoading(true);
    try {
      const branchParam = currentBranch?.id ? `&branch_id=${currentBranch.id}` : '';
      const res = await api.get(`/inventory/stock/ledger/${selectedItem}?${branchParam}`);
      setLedger(res.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  return (
    <div data-testid="stock-ledger">
      <div className="page-header"><div><h1>Stock Ledger</h1><p className="page-subtitle">Item-wise stock movements</p></div></div>
      
      <div className="filter-bar">
        <div className="filter-group">
          <label>Select Item:</label>
          <select value={selectedItem} onChange={e => setSelectedItem(e.target.value)} style={{minWidth: '250px'}}>
            <option value="">-- Select Item --</option>
            {items.map(i => <option key={i.id} value={i.id}>{i.code} - {i.name}</option>)}
          </select>
        </div>
        <button className="btn btn-primary" onClick={fetchLedger} disabled={!selectedItem || loading}>
          {loading ? 'Loading...' : 'View Ledger'}
        </button>
      </div>

      {ledger && (
        <div className="card">
          <div className="card-header">{ledger.item_code} - {ledger.item_name}</div>
          <div className="card-content">
            <div className="form-row" style={{marginBottom: '16px'}}>
              <div><strong>Opening:</strong> {formatNumber(ledger.opening_qty)} units ({formatCurrency(ledger.opening_value)})</div>
              <div><strong>Closing:</strong> {formatNumber(ledger.closing_qty)} units ({formatCurrency(ledger.closing_value)})</div>
              <div><strong>Avg Cost:</strong> {formatCurrency(ledger.average_cost)}</div>
            </div>
            <table className="data-grid">
              <thead><tr><th>Date</th><th>Voucher</th><th>Type</th><th>Batch</th><th className="text-right">In Qty</th><th className="text-right">Out Qty</th><th className="text-right">Rate</th><th className="text-right">Balance</th></tr></thead>
              <tbody>
                {ledger.transactions.map((t, i) => (
                  <tr key={i}>
                    <td>{formatDate(t.date)}</td>
                    <td>{t.voucher_number}</td>
                    <td>{t.voucher_type}</td>
                    <td>{t.batch_number}</td>
                    <td className="numeric" style={{color: t.in_qty > 0 ? 'var(--success)' : ''}}>{t.in_qty > 0 ? formatNumber(t.in_qty) : '-'}</td>
                    <td className="numeric" style={{color: t.out_qty > 0 ? 'var(--danger)' : ''}}>{t.out_qty > 0 ? formatNumber(t.out_qty) : '-'}</td>
                    <td className="numeric">{formatCurrency(t.rate)}</td>
                    <td className="numeric">{formatNumber(t.balance_qty)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {ledger.transactions.length === 0 && <div className="empty-state"><p>No transactions found</p></div>}
          </div>
        </div>
      )}
    </div>
  );
};

export default StockLedger;
