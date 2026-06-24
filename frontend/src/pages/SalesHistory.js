import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Download, Eye } from 'lucide-react';
import { toast } from 'sonner';

const SalesHistory = () => {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchInvoices();
  }, []);

  const fetchInvoices = async () => {
    try {
      const response = await api.get('/sales');
      setInvoices(response.data);
    } catch (error) {
      toast.error('Failed to fetch invoices');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPDF = (invoiceId) => {
    window.open(`${process.env.REACT_APP_BACKEND_URL}/api/sales/${invoiceId}/pdf`, '_blank');
  };

  if (loading) {
    return <div className="loading-container"><div className="spinner" /></div>;
  }

  return (
    <div data-testid="sales-history-page">
      <div className="page-header">
        <div>
          <h1>Sales History</h1>
          <p className="page-subtitle">View all sales invoices</p>
        </div>
      </div>

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Invoice No</th>
                <th>Date</th>
                <th>Type</th>
                <th>Customer</th>
                <th>Subtotal</th>
                <th>Tax</th>
                <th>Grand Total</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((invoice) => (
                <tr key={invoice.id} data-testid={`invoice-row-${invoice.invoice_number}`}>
                  <td className="data-value">{invoice.invoice_number}</td>
                  <td>{invoice.invoice_date?.split('T')[0]}</td>
                  <td>
                    <span className={`badge ${invoice.invoice_type === 'gst' ? 'badge-success' : 'badge-secondary'}`}>
                      {invoice.invoice_type === 'gst' ? 'GST' : 'Kacha'}
                    </span>
                  </td>
                  <td>{invoice.customer_name}</td>
                  <td className="data-value">₹{invoice.subtotal.toFixed(2)}</td>
                  <td className="data-value">₹{invoice.tax_amount.toFixed(2)}</td>
                  <td className="data-value">₹{invoice.grand_total.toFixed(2)}</td>
                  <td>
                    <button 
                      className="btn btn-ghost" 
                      onClick={() => handleDownloadPDF(invoice.id)}
                      data-testid="download-invoice-btn"
                    >
                      <Download size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default SalesHistory;
