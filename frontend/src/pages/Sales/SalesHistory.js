import React, { useState, useEffect } from 'react';
import { Eye, FileText } from 'lucide-react';
import api, { formatCurrency, formatDate } from '../../services/api';

const SalesHistory = ({ currentBranch }) => {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [invoiceType, setInvoiceType] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  useEffect(() => { fetchInvoices(); }, [currentBranch, invoiceType, startDate, endDate]);

  const fetchInvoices = async () => {
    try {
      let url = '/sales/invoices?';
      if (currentBranch?.id) url += `branch_id=${currentBranch.id}&`;
      if (invoiceType) url += `invoice_type=${invoiceType}&`;
      if (startDate) url += `start_date=${startDate}&`;
      if (endDate) url += `end_date=${endDate}&`;
      const response = await api.get(url);
      setInvoices(response.data);
    } catch (error) { console.error('Error:', error); }
    finally { setLoading(false); }
  };

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="sales-history">
      <div className="page-header"><div><h1>Sales History</h1><p className="page-subtitle">{currentBranch?.name || 'All Branches'}</p></div></div>
      <div className="filter-bar">
        <div className="filter-group"><label>Type:</label><select value={invoiceType} onChange={e => setInvoiceType(e.target.value)}><option value="">All</option><option value="gst">GST</option><option value="kacha">Kacha Bill</option></select></div>
        <div className="filter-group"><label>From:</label><input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} /></div>
        <div className="filter-group"><label>To:</label><input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} /></div>
      </div>
      <div className="card">
        <table className="data-grid">
          <thead><tr><th>Date</th><th>Invoice No.</th><th>Type</th><th>Customer</th><th className="text-right">Amount</th><th>Status</th></tr></thead>
          <tbody>
            {invoices.map(inv => (
              <tr key={inv.id}>
                <td>{formatDate(inv.invoice_date)}</td>
                <td><strong>{inv.invoice_number}</strong></td>
                <td><span className={`badge badge-${inv.invoice_type === 'gst' ? 'success' : 'warning'}`}>{inv.invoice_type.toUpperCase()}</span></td>
                <td>{inv.customer_name}</td>
                <td className="numeric">{formatCurrency(inv.grand_total)}</td>
                <td><span className="badge badge-success">{inv.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
        {invoices.length === 0 && <div className="empty-state"><p>No invoices found</p></div>}
      </div>
    </div>
  );
};

export default SalesHistory;
