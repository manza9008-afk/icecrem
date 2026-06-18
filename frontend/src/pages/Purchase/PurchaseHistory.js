import React, { useState, useEffect } from 'react';
import api, { formatCurrency, formatDate } from '../../services/api';

const PurchaseHistory = ({ currentBranch }) => {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  useEffect(() => { fetchInvoices(); }, [currentBranch, startDate, endDate]);

  const fetchInvoices = async () => {
    try {
      let url = '/purchase/invoices?';
      if (currentBranch?.id) url += `branch_id=${currentBranch.id}&`;
      if (startDate) url += `start_date=${startDate}&`;
      if (endDate) url += `end_date=${endDate}&`;
      const response = await api.get(url);
      setInvoices(response.data);
    } catch (error) { console.error('Error:', error); }
    finally { setLoading(false); }
  };

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="purchase-history">
      <div className="page-header">
        <div>
          <h1>Inventory In History</h1>
          <p className="page-subtitle">{currentBranch?.name || 'All Branches'}</p>
        </div>
      </div>
      <div className="filter-bar">
        <div className="filter-group"><label>From:</label><input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} /></div>
        <div className="filter-group"><label>To:</label><input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} /></div>
      </div>
      <div className="card">
        <table className="data-grid">
          <thead>
            <tr>
              <th>Date</th>
              <th>Invoice No.</th>
              <th>Ref. No.</th>
              <th className="text-right">Items</th>
              <th className="text-right">Qty In</th>
              <th className="text-right">Amount</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map(inv => (
              <tr key={inv.id}>
                <td>{formatDate(inv.invoice_date)}</td>
                <td><strong>{inv.invoice_number}</strong></td>
                <td>{inv.supplier_invoice_number}</td>
                <td className="numeric">{inv.items?.length || 0}</td>
                <td className="numeric">{(inv.items || []).reduce((sum, item) => sum + (item.quantity || 0), 0)}</td>
                <td className="numeric">{formatCurrency(inv.grand_total)}</td>
                <td><span className="badge badge-success">{inv.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
        {invoices.length === 0 && <div className="empty-state"><p>No purchase invoices found</p></div>}
      </div>
    </div>
  );
};

export default PurchaseHistory;