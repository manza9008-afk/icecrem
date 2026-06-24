import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Plus, X, Download } from 'lucide-react';
import { toast } from 'sonner';
import { useSearchParams } from 'react-router-dom';

const SalesInvoice = () => {
  const [searchParams] = useSearchParams();
  const [items, setItems] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [invoiceType, setInvoiceType] = useState(searchParams.get('type') === 'kacha' ? 'kacha' : 'gst');
  const [formData, setFormData] = useState({
    customer_name: '',
    customer_gstin: '',
    customer_address: '',
    invoice_date: new Date().toISOString().split('T')[0],
    discount: 0,
    notes: '',
  });
  const [invoiceItems, setInvoiceItems] = useState([]);
  const [newItem, setNewItem] = useState({
    item_id: '',
    quantity: 1,
  });

  useEffect(() => {
    fetchItems();
    fetchCustomers();
  }, []);

  const fetchItems = async () => {
    try {
      const response = await api.get('/items');
      setItems(response.data);
    } catch (error) {
      toast.error('Failed to fetch items');
    }
  };

  const fetchCustomers = async () => {
    try {
      const response = await api.get('/customers');
      setCustomers(response.data);
    } catch (error) {
      toast.error('Failed to fetch customers');
    }
  };

  const handleCustomerChange = (e) => {
    const customerId = e.target.value;
    const customer = customers.find(c => c.id === customerId);
    if (customer) {
      setFormData({
        ...formData,
        customer_name: customer.name,
        customer_gstin: customer.gstin || '',
        customer_address: customer.address,
      });
    }
  };

  const handleAddItem = () => {
    const item = items.find(i => i.id === newItem.item_id);
    if (!item) return;

    const amount = item.selling_price * newItem.quantity;
    setInvoiceItems([...invoiceItems, {
      item_id: item.id,
      item_name: item.name,
      hsn: item.hsn,
      quantity: newItem.quantity,
      rate: item.selling_price,
      amount: amount,
      gst_rate: item.gst_rate,
    }]);
    setNewItem({ item_id: '', quantity: 1 });
  };

  const handleRemoveItem = (index) => {
    setInvoiceItems(invoiceItems.filter((_, i) => i !== index));
  };

  const calculateTotals = () => {
    const subtotal = invoiceItems.reduce((sum, item) => sum + item.amount, 0);
    let tax = 0;
    if (invoiceType === 'gst') {
      tax = invoiceItems.reduce((sum, item) => sum + (item.amount * item.gst_rate / 100), 0);
    }
    const discount = parseFloat(formData.discount) || 0;
    const grandTotal = subtotal + tax - discount;
    return { subtotal, tax, grandTotal };
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (invoiceItems.length === 0) {
      toast.error('Please add at least one item');
      return;
    }

    try {
      const payload = {
        ...formData,
        invoice_type: invoiceType,
        items: invoiceItems,
      };
      const response = await api.post('/sales', payload);
      toast.success('Invoice created successfully');
      
      // Reset form
      setFormData({
        customer_name: '',
        customer_gstin: '',
        customer_address: '',
        invoice_date: new Date().toISOString().split('T')[0],
        discount: 0,
        notes: '',
      });
      setInvoiceItems([]);
      
      // Optionally download PDF
      if (window.confirm('Invoice created! Download PDF?')) {
        window.open(`${process.env.REACT_APP_BACKEND_URL}/api/sales/${response.data.id}/pdf`, '_blank');
      }
    } catch (error) {
      toast.error('Failed to create invoice');
    }
  };

  const totals = calculateTotals();

  return (
    <div data-testid="sales-invoice-page">
      <div className="page-header">
        <div>
          <h1>Create Sales Invoice</h1>
          <p className="page-subtitle">Generate GST or Kacha bill</p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="card" style={{ marginBottom: '16px' }}>
          <div className="card-header">
            <h3>Invoice Type</h3>
          </div>
          <div className="card-content">
            <div style={{ display: 'flex', gap: '16px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input 
                  type="radio" 
                  value="gst" 
                  checked={invoiceType === 'gst'} 
                  onChange={(e) => setInvoiceType(e.target.value)}
                  data-testid="invoice-type-gst"
                />
                GST Invoice (Tax Invoice)
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input 
                  type="radio" 
                  value="kacha" 
                  checked={invoiceType === 'kacha'} 
                  onChange={(e) => setInvoiceType(e.target.value)}
                  data-testid="invoice-type-kacha"
                />
                Kacha Bill (Non-Tax Invoice)
              </label>
            </div>
          </div>
        </div>

        <div className="card" style={{ marginBottom: '16px' }}>
          <div className="card-header">
            <h3>Customer Details</h3>
          </div>
          <div className="card-content">
            <div className="grid grid-2">
              <div className="form-group">
                <label>Select Customer</label>
                <select onChange={handleCustomerChange} data-testid="customer-select">
                  <option value="">-- Select Customer --</option>
                  {customers.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Customer Name *</label>
                <input 
                  value={formData.customer_name} 
                  onChange={(e) => setFormData({...formData, customer_name: e.target.value})} 
                  required
                  data-testid="customer-name-input"
                />
              </div>
              <div className="form-group">
                <label>GSTIN</label>
                <input 
                  value={formData.customer_gstin} 
                  onChange={(e) => setFormData({...formData, customer_gstin: e.target.value})}
                  data-testid="customer-gstin-input"
                />
              </div>
              <div className="form-group">
                <label>Invoice Date *</label>
                <input 
                  type="date" 
                  value={formData.invoice_date} 
                  onChange={(e) => setFormData({...formData, invoice_date: e.target.value})} 
                  required
                  data-testid="invoice-date-input"
                />
              </div>
              <div className="form-group" style={{ gridColumn: 'span 2' }}>
                <label>Address *</label>
                <textarea 
                  value={formData.customer_address} 
                  onChange={(e) => setFormData({...formData, customer_address: e.target.value})} 
                  required
                  rows="2"
                  data-testid="customer-address-input"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="card" style={{ marginBottom: '16px' }}>
          <div className="card-header">
            <h3>Add Items</h3>
          </div>
          <div className="card-content">
            <div className="grid grid-3" style={{ marginBottom: '16px' }}>
              <div className="form-group" style={{ gridColumn: 'span 2' }}>
                <label>Select Item</label>
                <select 
                  value={newItem.item_id} 
                  onChange={(e) => setNewItem({...newItem, item_id: e.target.value})}
                  data-testid="item-select"
                >
                  <option value="">-- Select Item --</option>
                  {items.map(item => (
                    <option key={item.id} value={item.id}>
                      {item.name} - ₹{item.selling_price} ({item.sku})
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Quantity</label>
                <input 
                  type="number" 
                  min="1" 
                  step="0.01"
                  value={newItem.quantity} 
                  onChange={(e) => setNewItem({...newItem, quantity: parseFloat(e.target.value)})}
                  data-testid="item-quantity-input"
                />
              </div>
            </div>
            <button 
              type="button" 
              className="btn btn-secondary" 
              onClick={handleAddItem}
              disabled={!newItem.item_id}
              data-testid="add-item-to-invoice-btn"
            >
              <Plus size={18} />
              Add to Invoice
            </button>

            <div className="table-container" style={{ marginTop: '16px' }}>
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Item</th>
                    <th>HSN</th>
                    <th>Qty</th>
                    <th>Rate</th>
                    {invoiceType === 'gst' && <th>GST %</th>}
                    <th>Amount</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {invoiceItems.map((item, idx) => (
                    <tr key={idx}>
                      <td>{idx + 1}</td>
                      <td>{item.item_name}</td>
                      <td className="data-value">{item.hsn}</td>
                      <td className="data-value">{item.quantity}</td>
                      <td className="data-value">₹{item.rate.toFixed(2)}</td>
                      {invoiceType === 'gst' && <td className="data-value">{item.gst_rate}%</td>}
                      <td className="data-value">₹{item.amount.toFixed(2)}</td>
                      <td>
                        <button type="button" className="btn btn-ghost" onClick={() => handleRemoveItem(idx)}>
                          <X size={16} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="grid grid-2">
          <div className="card">
            <div className="card-header">
              <h3>Additional Details</h3>
            </div>
            <div className="card-content">
              <div className="form-group">
                <label>Discount</label>
                <input 
                  type="number" 
                  step="0.01"
                  value={formData.discount} 
                  onChange={(e) => setFormData({...formData, discount: e.target.value})}
                />
              </div>
              <div className="form-group">
                <label>Notes</label>
                <textarea 
                  value={formData.notes} 
                  onChange={(e) => setFormData({...formData, notes: e.target.value})}
                  rows="3"
                />
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h3>Invoice Summary</h3>
            </div>
            <div className="card-content">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Subtotal:</span>
                  <span className="data-value">₹{totals.subtotal.toFixed(2)}</span>
                </div>
                {invoiceType === 'gst' && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Tax:</span>
                    <span className="data-value">₹{totals.tax.toFixed(2)}</span>
                  </div>
                )}
                {formData.discount > 0 && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Discount:</span>
                    <span className="data-value">- ₹{parseFloat(formData.discount).toFixed(2)}</span>
                  </div>
                )}
                <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '2px solid #e2e8f0', paddingTop: '12px', fontWeight: 'bold' }}>
                  <span>Grand Total:</span>
                  <span className="data-value" style={{ fontSize: '1.25rem' }}>₹{totals.grandTotal.toFixed(2)}</span>
                </div>
              </div>
              <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '16px' }} data-testid="create-invoice-btn">
                Create Invoice
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};

export default SalesInvoice;
