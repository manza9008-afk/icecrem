import React, { useEffect, useState } from 'react';
import { Save, Plus, Trash2 } from 'lucide-react';
import api, { getTodayDate, getItemSizeLabel } from '../../services/api';

const PurchaseInvoice = ({ currentBranch }) => {
  const [items, setItems] = useState([]);
  const [godowns, setGodowns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    invoice_date: getTodayDate(),
  });
  const [lineItems, setLineItems] = useState([
    { id: 1, item_id: '', item_name: '', size: '', hsn_code: '', godown_id: '', quantity: 1, rate: 0, gst_rate: 0 }
  ]);

  useEffect(() => {
    fetchData();
  }, [currentBranch]);

  const fetchData = async () => {
    try {
      const [itemsRes, godownsRes] = await Promise.all([
        api.get('/inventory/items'),
        currentBranch?.id ? api.get(`/branches/${currentBranch.id}/godowns`) : Promise.resolve({ data: [] })
      ]);
      setItems(itemsRes.data);
      setGodowns(godownsRes.data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const focusField = (id, delay = 50) => {
    setTimeout(() => {
      const el = document.getElementById(id);
      if (el) { el.focus(); if (el.select) el.select(); }
    }, delay);
  };

  const handleItemChange = (index, itemId) => {
    const item = items.find(i => i.id === itemId);
    if (!item) return;
    const newItems = [...lineItems];
    newItems[index] = {
      ...newItems[index],
      item_id: itemId,
      item_name: item.name,
      size: getItemSizeLabel(item),
      hsn_code: item.hsn_code,
      rate: 0,
      gst_rate: 0
    };
    setLineItems(newItems);
  };

  const handleItemKeyDown = (e, index) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      focusField(`godown-${index}`);
    }
  };

  const handleGodownKeyDown = (e, index) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      focusField(`qty-${index}`);
    }
  };

  const handleQtyKeyDown = (e, index) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (index === lineItems.length - 1) {
        addLineItem();
        focusField(`item-${index + 1}`, 100);
      } else {
        focusField(`item-${index + 1}`);
      }
    }
  };

  const updateLineItem = (index, field, value) => {
    const newItems = [...lineItems];
    newItems[index][field] = value;
    setLineItems(newItems);
  };

  const addLineItem = () => {
    setLineItems([
      ...lineItems,
      { id: Date.now(), item_id: '', item_name: '', size: '', hsn_code: '', godown_id: godowns[0]?.id || '', quantity: 1, rate: 0, gst_rate: 0 }
    ]);
  };

  const removeLineItem = (index) => {
    if (lineItems.length <= 1) return;
    setLineItems(lineItems.filter((_, i) => i !== index));
  };

  const handleSave = async () => {
    if (!currentBranch) { alert('Select a branch'); return; }
    const validItems = lineItems.filter(i => i.item_id && i.quantity > 0);
    if (validItems.length === 0) { alert('Add at least one item'); return; }

    setSaving(true);
    try {
      const invoiceItems = validItems.map(i => ({
        item_id: i.item_id,
        item_name: i.item_name,
        hsn_code: i.hsn_code,
        godown_id: i.godown_id || godowns[0]?.id,
        batch_number: '',
        expiry_date: null,
        quantity: parseFloat(i.quantity),
        rate: 0,
        taxable_amount: 0,
        gst_rate: 0
      }));

      await api.post('/purchase/invoices', {
        branch_id: currentBranch.id,
        supplier_name: 'Inventory Inward',
        supplier_address: '',
        supplier_gstin: '',
        supplier_state: 'Gujarat',
        supplier_state_code: '24',
        supplier_invoice_number: 'DIRECT-INWARD',
        supplier_invoice_date: formData.invoice_date,
        invoice_date: formData.invoice_date,
        items: invoiceItems,
        subtotal: 0,
        discount_amount: 0,
        taxable_amount: 0,
        cgst_amount: 0,
        sgst_amount: 0,
        igst_amount: 0,
        round_off: 0,
        grand_total: 0
      });

      alert('Inventory inward saved!');
      resetForm();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error');
    } finally {
      setSaving(false);
    }
  };

  const resetForm = () => {
    setFormData({
      invoice_date: getTodayDate(),
    });
    setLineItems([
      { id: 1, item_id: '', item_name: '', size: '', hsn_code: '', godown_id: godowns[0]?.id || '', quantity: 1, rate: 0, gst_rate: 0 }
    ]);
  };

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="purchase-invoice">
      <div className="page-header">
        <div>
          <h1>Inventory In Entry</h1>
          <p className="page-subtitle">{currentBranch?.name}</p>
        </div>
        <div className="btn-group">
          <button className="btn btn-secondary" onClick={resetForm}>Clear</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            <Save size={16} /> {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-header">Inward Details</div>
        <div className="card-content">
          <div className="form-row">
            <div className="form-group" style={{ maxWidth: '180px' }}>
              <label className="form-label">Entry Date *</label>
              <input
                type="date"
                className="form-control"
                value={formData.invoice_date}
                onChange={e => setFormData({ ...formData, invoice_date: e.target.value })}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">Inventory In Items</div>
        <div className="card-content">
          <table className="input-grid">
            <thead>
              <tr>
                <th>#</th>
                <th>Item Name</th>
                <th>Size</th>
                <th>Stock</th>
                <th className="text-right">Qty In</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {lineItems.map((item, index) => (
                <tr key={item.id}>
                  <td className="text-center">{index + 1}</td>
                  <td>
                    <select id={`item-${index}`} className="form-control" value={item.item_id} onChange={e => handleItemChange(index, e.target.value)} onKeyDown={e => handleItemKeyDown(e, index)}>
                      <option value="">Select</option>
                      {items.map(i => <option key={i.id} value={i.id}>{i.code} - {i.name}</option>)}
                    </select>
                  </td>
                  <td>{item.size || '-'}</td>
                  <td>
                    <select id={`godown-${index}`} className="form-control" value={item.godown_id} onChange={e => updateLineItem(index, 'godown_id', e.target.value)} onKeyDown={e => handleGodownKeyDown(e, index)} style={{ width: '120px' }}>
                      {godowns.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
                    </select>
                  </td>
                  <td>
                    <input id={`qty-${index}`} type="number" className="form-control text-right" value={item.quantity} onChange={e => updateLineItem(index, 'quantity', e.target.value)} onKeyDown={e => handleQtyKeyDown(e, index)} style={{ width: '90px' }} />
                  </td>
                  <td>
                    <button className="btn btn-sm btn-danger" onClick={() => removeLineItem(index)} disabled={lineItems.length <= 1}>
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <button className="btn btn-secondary btn-sm" onClick={addLineItem} style={{ marginTop: '8px' }}>
            <Plus size={14} /> Add Item
          </button>
        </div>
      </div>
    </div>
  );
};

export default PurchaseInvoice;