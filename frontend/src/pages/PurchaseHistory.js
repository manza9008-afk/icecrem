import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { toast } from 'sonner';

const PurchaseHistory = () => {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchInvoices();
  }, []);

  const fetchInvoices = async () => {
    try {
      const response = await api.get('/purchases');
      setInvoices(response.data);
    } catch (error) {
      toast.error('Failed to fetch purchase history');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading-container"><div className="spinner" /></div>;
  }

  return (
    <div data-testid="purchase-history-page">
      <div className="page-header">
        <div>
          <h1>Purchase History</h1>
          <p className="page-subtitle">View all purchase entries</p>
        </div>
      </div>

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Invoice No</th>
                <th>Date</th>
                <th>Supplier</th>
                <th>Subtotal</th>
                <th>Input Tax</th>
                <th>Grand Total</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((invoice) => (
                <tr key={invoice.id} data-testid={`purchase-row-${invoice.invoice_number}`}>
                  <td className="data-value">{invoice.invoice_number}</td>
                  <td>{invoice.invoice_date?.split('T')[0]}</td>
                  <td>{invoice.supplier_name}</td>
                  <td className="data-value">₹{invoice.subtotal.toFixed(2)}</td>
                  <td className="data-value">₹{invoice.tax_amount.toFixed(2)}</td>
                  <td className="data-value">₹{invoice.grand_total.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default PurchaseHistory;
