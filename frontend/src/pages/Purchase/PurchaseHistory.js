import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import api, { formatCurrency, formatDate, formatNumber, getItemSizeLabel } from '../../services/api';

const PurchaseHistory = ({ currentBranch }) => {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [items, setItems] = useState([]);
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => { fetchInvoices(); }, [currentBranch, startDate, endDate]);

  useEffect(() => {
    api.get('/inventory/items')
      .then(res => setItems(res.data))
      .catch(error => { console.error('Error:', error); setItems([]); });
  }, []);

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
              <th style={{ width: '32px' }}></th>
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
            {invoices.map(inv => {
              const isOpen = expandedId === inv.id;
              return (
              <React.Fragment key={inv.id}>
              <tr onClick={() => setExpandedId(isOpen ? null : inv.id)} style={{ cursor: 'pointer' }} title="Click to see products">
                <td>{isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</td>
                <td>{formatDate(inv.invoice_date)}</td>
                <td><strong>{inv.invoice_number}</strong></td>
                <td>{inv.supplier_invoice_number}</td>
                <td className="numeric">{inv.items?.length || 0}</td>
                <td className="numeric">{(inv.items || []).reduce((sum, item) => sum + (item.quantity || 0), 0)}</td>
                <td className="numeric">{formatCurrency(inv.grand_total)}</td>
                <td><span className="badge badge-success">{inv.status}</span></td>
              </tr>
              {isOpen && (
                <tr>
                  <td></td>
                  <td colSpan={7} style={{ padding: '8px 16px' }}>
                    <table className="data-grid">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th>Product Name</th>
                          <th>Size</th>
                          <th className="text-right">Qty In</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(inv.items || []).map((item, idx) => {
                          const master = items.find(i => i.id === item.item_id);
                          return (
                            <tr key={item.id || idx}>
                              <td>{idx + 1}</td>
                              <td><strong>{item.item_name || master?.name || '-'}</strong></td>
                              <td>{master ? getItemSizeLabel(master) || '-' : '-'}</td>
                              <td className="numeric">{formatNumber(item.quantity || 0, 2)}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                    {(inv.items || []).length === 0 && <div className="empty-state"><p>No products in this entry</p></div>}
                  </td>
                </tr>
              )}
              </React.Fragment>
              );
            })}
          </tbody>
        </table>
        {invoices.length === 0 && <div className="empty-state"><p>No purchase invoices found</p></div>}
      </div>
    </div>
  );
};

export default PurchaseHistory;