import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Plus, X } from 'lucide-react';
import { toast } from 'sonner';

const PurchaseInvoice = () => {
  const [items, setItems] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [formData, setFormData] = useState({
    supplier_name: '',
    supplier_gstin: '',
    invoice_date: new Date().toISOString().split('T')[0],
  });
  const [invoiceItems, setInvoiceItems] = useState([]);
  const [newItem, setNewItem] = useState({
    item_id: '',
    quantity: 1,
    batch_no: '',
    expiry_date: '',
  });

  useEffect(() => {
    fetchItems();
    fetchSuppliers();
  }, []);

  const fetchItems = async () => {
    try {
      const response = await api.get('/items');
      setItems(response.data);
    } catch (error) {
      toast.error('Failed to fetch items');
    }
  };

  const fetchSuppliers = async () => {
    try {
      const response = await api.get('/suppliers');
      setSuppliers(response.data);
    } catch (error) {
      toast.error('Failed to fetch suppliers');
    }
  };

  const handleSupplierChange = (e) => {
    const supplierId = e.target.value;
    const supplier = suppliers.find(s => s.id === supplierId);
    if (supplier) {
      setFormData({
        ...formData,
        supplier_name: supplier.name,
        supplier_gstin: supplier.gstin || '',
      });
    }
  };

  const handleAddItem = () => {
    const item = items.find(i => i.id === newItem.item_id);
    if (!item) return;

    const amount = item.cost_price * newItem.quantity;
    setInvoiceItems([...invoiceItems, {
      item_id: item.id,
      item_name: item.name,
      hsn: item.hsn,
      quantity: newItem.quantity,
      rate: item.cost_price,
      amount: amount,
      gst_rate: item.gst_rate,
      batch_no: newItem.batch_no,
      expiry_date: newItem.expiry_date,
    }]);
    setNewItem({ item_id: '', quantity: 1, batch_no: '', expiry_date: '' });
  };

  const handleRemoveItem = (index) => {
    setInvoiceItems(invoiceItems.filter((_, i) => i !== index));
  };

  const calculateTotals = () => {
    const subtotal = invoiceItems.reduce((sum, item) => sum + item.amount, 0);
    const tax = invoiceItems.reduce((sum, item) => sum + (item.amount * item.gst_rate / 100), 0);
    const grandTotal = subtotal + tax;
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
        items: invoiceItems,
      };
      await api.post('/purchases', payload);
      toast.success('Purchase entry created successfully');
      
      // Reset form
      setFormData({
        supplier_name: '',
        supplier_gstin: '',
        invoice_date: new Date().toISOString().split('T')[0],
      });
      setInvoiceItems([]);
    } catch (error) {
      toast.error('Failed to create purchase entry');
    }
  };

  const totals = calculateTotals();

  return (
    <div data-testid="purchase-invoice-page">
      <div className="page-header">
        <div>
          <h1>Create Purchase Entry</h1>
          <p className="page-subtitle">Record inventory purchases</p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="card" style={{ marginBottom: '16px' }}>
          <div className="card-header">
            <h3>Supplier Details</h3>
          </div>
          <div className="card-content">
            <div className="grid grid-3">
              <div className="form-group">
                <label>Select Supplier</label>
                <select onChange={handleSupplierChange} data-testid="supplier-select">
                  <option value="">-- Select Supplier --</option>
                  {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Supplier Name *</label>
                <input 
                  value={formData.supplier_name} 
                  onChange={(e) => setFormData({...formData, supplier_name: e.target.value})} 
                  required
                  data-testid="supplier-name-input"
                />
              </div>
              <div className="form-group">
                <label>Invoice Date *</label>
                <input 
                  type="date" 
                  value={formData.invoice_date} 
                  onChange={(e) => setFormData({...formData, invoice_date: e.target.value})} 
                  required
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
            <div className="grid grid-4" style={{ marginBottom: '16px' }}>
              <div className="form-group">
                <label>Select Item</label>
                <select 
                  value={newItem.item_id} 
                  onChange={(e) => setNewItem({...newItem, item_id: e.target.value})}
                  data-testid="item-select"
                >
                  <option value="">-- Select Item --</option>
                  {items.map(item => (
                    <option key={item.id} value={item.id}>
                      {item.name} - ₹{item.cost_price}
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
              <div className="form-group">
                <label>Batch No</label>
                <input 
                  value={newItem.batch_no} 
                  onChange={(e) => setNewItem({...newItem, batch_no: e.target.value})}
                />
              </div>
              <div className="form-group">
                <label>Expiry Date</label>
                <input 
                  type="date"
                  value={newItem.expiry_date} 
                  onChange={(e) => setNewItem({...newItem, expiry_date: e.target.value})}
                />
              </div>
            </div>
            <button 
              type="button" 
              className="btn btn-secondary" 
              onClick={handleAddItem}
              disabled={!newItem.item_id}
              data-testid="add-item-to-purchase-btn"
            >
              <Plus size={18} />
              Add to Purchase
            </button>

            <div className="table-container" style={{ marginTop: '16px' }}>
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Item</th>
                    <th>Batch</th>
                    <th>Expiry</th>
                    <th>Qty</th>
                    <th>Rate</th>
                    <th>GST %</th>
                    <th>Amount</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {invoiceItems.map((item, idx) => (
                    <tr key={idx}>
                      <td>{idx + 1}</td>
                      <td>{item.item_name}</td>
                      <td className="data-value">{item.batch_no || '-'}</td>
                      <td>{item.expiry_date || '-'}</td>
                      <td className="data-value">{item.quantity}</td>
                      <td className="data-value">₹{item.rate.toFixed(2)}</td>
                      <td className="data-value">{item.gst_rate}%</td>
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

        <div className="card">
          <div className="card-header">
            <h3>Purchase Summary</h3>
          </div>
          <div className="card-content">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxWidth: '400px', marginLeft: 'auto' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Subtotal:</span>
                <span className="data-value">₹{totals.subtotal.toFixed(2)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Input Tax:</span>
                <span className="data-value">₹{totals.tax.toFixed(2)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '2px solid #e2e8f0', paddingTop: '12px', fontWeight: 'bold' }}>
                <span>Grand Total:</span>
                <span className="data-value" style={{ fontSize: '1.25rem' }}>₹{totals.grandTotal.toFixed(2)}</span>
              </div>
              <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '8px' }} data-testid="create-purchase-btn">
                Create Purchase Entry
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};

export default PurchaseInvoice;
