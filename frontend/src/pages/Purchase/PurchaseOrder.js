import React, { useState, useEffect } from 'react';
import { Save, Plus, Trash2, Eye } from 'lucide-react';
import api, { formatCurrency, getTodayDate, formatDate } from '../../services/api';

const PurchaseOrder = ({ currentBranch }) => {
  const [items, setItems] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState(null);
  
  const [formData, setFormData] = useState({
    order_date: getTodayDate(),
    expected_delivery_date: '',
    supplier_name: '',
    supplier_address: '',
    supplier_gstin: '',
    supplier_contact: '',
    remarks: ''
  });
  
  const [lineItems, setLineItems] = useState([
    { id: 1, item_id: '', item_name: '', hsn_code: '', quantity: 1, rate: 0, gst_rate: 18 }
  ]);

  useEffect(() => {
    fetchData();
  }, [currentBranch]);

  const fetchData = async () => {
    try {
      const [itemsRes, ordersRes] = await Promise.all([
        api.get('/inventory/items'),
        api.get('/purchase/orders' + (currentBranch?.id ? `?branch_id=${currentBranch.id}` : ''))
      ]);
      setItems(itemsRes.data);
      setOrders(ordersRes.data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleItemChange = (index, itemId) => {
    const item = items.find(i => i.id === itemId);
    if (item) {
      const newItems = [...lineItems];
      newItems[index] = {
        ...newItems[index],
        item_id: itemId,
        item_name: item.name,
        hsn_code: item.hsn_code,
        rate: item.cost_price,
        gst_rate: item.gst_rate
      };
      setLineItems(newItems);
    }
  };

  const updateLineItem = (index, field, value) => {
    const newItems = [...lineItems];
    newItems[index][field] = value;
    setLineItems(newItems);
  };

  const addLineItem = () => {
    setLineItems([...lineItems, {
      id: Date.now(),
      item_id: '',
      item_name: '',
      hsn_code: '',
      quantity: 1,
      rate: 0,
      gst_rate: 18
    }]);
  };

  const removeLineItem = (index) => {
    if (lineItems.length <= 1) return;
    setLineItems(lineItems.filter((_, i) => i !== index));
  };

  const calculateTotals = () => {
    let subtotal = 0, cgst = 0, sgst = 0;
    lineItems.forEach(item => {
      const taxable = item.quantity * item.rate;
      const tax = taxable * (item.gst_rate / 100);
      subtotal += taxable;
      cgst += tax / 2;
      sgst += tax / 2;
    });
    return { subtotal, cgst, sgst, grandTotal: subtotal + cgst + sgst };
  };

  const totals = calculateTotals();

  const handleSave = async () => {
    if (!currentBranch) { alert('Select a branch'); return; }
    if (!formData.supplier_name) { alert('Enter supplier name'); return; }
    const validItems = lineItems.filter(i => i.item_id && i.quantity > 0);
    if (validItems.length === 0) { alert('Add at least one item'); return; }

    setSaving(true);
    try {
      const orderItems = validItems.map(i => ({
        item_id: i.item_id,
        item_name: i.item_name,
        hsn_code: i.hsn_code,
        quantity: parseFloat(i.quantity),
        rate: parseFloat(i.rate),
        gst_rate: parseFloat(i.gst_rate),
        amount: i.quantity * i.rate
      }));

      await api.post('/purchase/orders', {
        branch_id: currentBranch.id,
        ...formData,
        items: orderItems,
        subtotal: totals.subtotal,
        cgst_amount: totals.cgst,
        sgst_amount: totals.sgst,
        grand_total: totals.grandTotal
      });
      
      alert('Purchase Order saved!');
      resetForm();
      fetchData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error saving order');
    } finally {
      setSaving(false);
    }
  };

  const resetForm = () => {
    setShowForm(false);
    setFormData({
      order_date: getTodayDate(),
      expected_delivery_date: '',
      supplier_name: '',
      supplier_address: '',
      supplier_gstin: '',
      supplier_contact: '',
      remarks: ''
    });
    setLineItems([{ id: 1, item_id: '', item_name: '', hsn_code: '', quantity: 1, rate: 0, gst_rate: 18 }]);
  };

  const getStatusClass = (status) => {
    switch (status) {
      case 'pending': return 'badge-warning';
      case 'partial': return 'badge-info';
      case 'completed': return 'badge-success';
      case 'cancelled': return 'badge-danger';
      default: return 'badge-secondary';
    }
  };

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  if (showForm) {
    return (
      <div data-testid="purchase-order-form">
        <div className="page-header">
          <div>
            <h1>New Purchase Order</h1>
            <p className="page-subtitle">{currentBranch?.name}</p>
          </div>
          <div className="btn-group">
            <button className="btn btn-secondary" onClick={resetForm}>Cancel</button>
            <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
              <Save size={16} /> {saving ? 'Saving...' : 'Save Order'}
            </button>
          </div>
        </div>

        <div className="card">
          <div className="card-header">Order Details</div>
          <div className="card-content">
            <div className="form-row">
              <div className="form-group" style={{ maxWidth: '150px' }}>
                <label className="form-label">Order Date *</label>
                <input type="date" className="form-control" value={formData.order_date}
                  onChange={e => setFormData({ ...formData, order_date: e.target.value })} />
              </div>
              <div className="form-group" style={{ maxWidth: '150px' }}>
                <label className="form-label">Expected Delivery</label>
                <input type="date" className="form-control" value={formData.expected_delivery_date}
                  onChange={e => setFormData({ ...formData, expected_delivery_date: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Supplier Name *</label>
                <input type="text" className="form-control" value={formData.supplier_name}
                  onChange={e => setFormData({ ...formData, supplier_name: e.target.value })} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Address</label>
                <input type="text" className="form-control" value={formData.supplier_address}
                  onChange={e => setFormData({ ...formData, supplier_address: e.target.value })} />
              </div>
              <div className="form-group" style={{ maxWidth: '200px' }}>
                <label className="form-label">Supplier GSTIN</label>
                <input type="text" className="form-control" value={formData.supplier_gstin}
                  onChange={e => setFormData({ ...formData, supplier_gstin: e.target.value.toUpperCase() })} maxLength={15} />
              </div>
              <div className="form-group" style={{ maxWidth: '150px' }}>
                <label className="form-label">Contact</label>
                <input type="text" className="form-control" value={formData.supplier_contact}
                  onChange={e => setFormData({ ...formData, supplier_contact: e.target.value })} />
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">Order Items</div>
          <div className="card-content">
            <table className="input-grid">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Item</th>
                  <th>HSN</th>
                  <th className="text-right">Qty</th>
                  <th className="text-right">Rate</th>
                  <th className="text-right">GST %</th>
                  <th className="text-right">Amount</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {lineItems.map((item, index) => {
                  const taxable = item.quantity * item.rate;
                  const tax = taxable * (item.gst_rate / 100);
                  const total = taxable + tax;
                  return (
                    <tr key={item.id}>
                      <td className="text-center">{index + 1}</td>
                      <td>
                        <select className="form-control" value={item.item_id} onChange={e => handleItemChange(index, e.target.value)}>
                          <option value="">Select Item</option>
                          {items.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}
                        </select>
                      </td>
                      <td><input type="text" className="form-control" value={item.hsn_code} readOnly style={{ width: '80px' }} /></td>
                      <td><input type="number" className="form-control text-right" value={item.quantity} onChange={e => updateLineItem(index, 'quantity', e.target.value)} style={{ width: '70px' }} /></td>
                      <td><input type="number" step="0.01" className="form-control text-right" value={item.rate} onChange={e => updateLineItem(index, 'rate', e.target.value)} style={{ width: '100px' }} /></td>
                      <td>
                        <select className="form-control" value={item.gst_rate} onChange={e => updateLineItem(index, 'gst_rate', e.target.value)} style={{ width: '70px' }}>
                          <option value={0}>0%</option>
                          <option value={5}>5%</option>
                          <option value={12}>12%</option>
                          <option value={18}>18%</option>
                          <option value={28}>28%</option>
                        </select>
                      </td>
                      <td className="text-right" style={{ fontFamily: 'var(--font-mono)' }}>{formatCurrency(total)}</td>
                      <td>
                        <button className="btn btn-sm btn-danger" onClick={() => removeLineItem(index)} disabled={lineItems.length <= 1}>
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <button className="btn btn-secondary btn-sm" onClick={addLineItem} style={{ marginTop: '8px' }}>
              <Plus size={14} /> Add Item
            </button>

            <div className="totals-panel" style={{ maxWidth: '350px', marginLeft: 'auto', marginTop: '16px' }}>
              <div className="totals-row"><span className="label">Subtotal</span><span className="value">{formatCurrency(totals.subtotal)}</span></div>
              <div className="totals-row"><span className="label">CGST</span><span className="value">{formatCurrency(totals.cgst)}</span></div>
              <div className="totals-row"><span className="label">SGST</span><span className="value">{formatCurrency(totals.sgst)}</span></div>
              <div className="totals-row highlight"><span className="label">Grand Total</span><span className="value">{formatCurrency(totals.grandTotal)}</span></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="purchase-order">
      <div className="page-header">
        <div>
          <h1>Purchase Orders</h1>
          <p className="page-subtitle">{currentBranch?.name || 'All Branches'}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>
          <Plus size={16} /> New Purchase Order
        </button>
      </div>

      <div className="card">
        <table className="data-grid">
          <thead>
            <tr>
              <th>Date</th>
              <th>Order No.</th>
              <th>Supplier</th>
              <th>Expected Delivery</th>
              <th className="text-right">Amount</th>
              <th>Status</th>
              <th className="text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {orders.map(order => (
              <tr key={order.id}>
                <td>{formatDate(order.order_date)}</td>
                <td><strong>{order.order_number}</strong></td>
                <td>{order.supplier_name}</td>
                <td>{order.expected_delivery_date ? formatDate(order.expected_delivery_date) : '-'}</td>
                <td className="numeric">{formatCurrency(order.grand_total)}</td>
                <td>
                  <span className={`badge ${getStatusClass(order.status)}`}>
                    {order.status?.toUpperCase()}
                  </span>
                </td>
                <td className="text-center">
                  <button className="btn btn-sm btn-secondary" onClick={() => setSelectedOrder(order)}>
                    <Eye size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {orders.length === 0 && <div className="empty-state"><p>No purchase orders found</p></div>}
      </div>

      {selectedOrder && (
        <div className="modal-overlay">
          <div className="modal" style={{ width: '700px', maxHeight: '90vh', overflow: 'auto' }}>
            <div className="modal-header">
              <h3>Purchase Order: {selectedOrder.order_number}</h3>
              <button className="modal-close" onClick={() => setSelectedOrder(null)}>&times;</button>
            </div>
            <div className="modal-body">
              <div className="form-row">
                <div><strong>Date:</strong> {formatDate(selectedOrder.order_date)}</div>
                <div><strong>Expected:</strong> {selectedOrder.expected_delivery_date ? formatDate(selectedOrder.expected_delivery_date) : 'N/A'}</div>
                <div><strong>Status:</strong> <span className={`badge ${getStatusClass(selectedOrder.status)}`}>{selectedOrder.status?.toUpperCase()}</span></div>
              </div>
              <div style={{ marginTop: '12px' }}>
                <strong>Supplier:</strong> {selectedOrder.supplier_name}
                {selectedOrder.supplier_gstin && <span style={{ marginLeft: '12px', color: 'var(--text-muted)' }}>GSTIN: {selectedOrder.supplier_gstin}</span>}
              </div>
              <table className="data-grid" style={{ marginTop: '16px' }}>
                <thead><tr><th>Item</th><th>HSN</th><th className="text-right">Ordered</th><th className="text-right">Received</th><th className="text-right">Pending</th><th className="text-right">Amount</th></tr></thead>
                <tbody>
                  {selectedOrder.items?.map((item, i) => (
                    <tr key={i}>
                      <td>{item.item_name}</td>
                      <td>{item.hsn_code}</td>
                      <td className="numeric">{item.quantity}</td>
                      <td className="numeric">{item.received_qty || 0}</td>
                      <td className="numeric" style={{ color: (item.pending_qty || item.quantity) > 0 ? 'var(--warning)' : 'var(--success)' }}>{item.pending_qty || item.quantity}</td>
                      <td className="numeric">{formatCurrency(item.amount || item.quantity * item.rate)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr style={{ fontWeight: 'bold', background: 'var(--bg-secondary)' }}>
                    <td colSpan={5}>Grand Total</td>
                    <td className="numeric">{formatCurrency(selectedOrder.grand_total)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setSelectedOrder(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PurchaseOrder;
