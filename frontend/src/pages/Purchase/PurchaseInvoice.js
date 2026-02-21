import React, { useState, useEffect } from 'react';
import { Save, Plus, Trash2 } from 'lucide-react';
import api, { formatCurrency, getTodayDate } from '../../services/api';

const PurchaseInvoice = ({ currentBranch }) => {
  const [items, setItems] = useState([]);
  const [godowns, setGodowns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    invoice_date: getTodayDate(), supplier_name: '', supplier_address: '', supplier_gstin: '',
    supplier_state: 'Gujarat', supplier_state_code: '24', supplier_invoice_number: '', supplier_invoice_date: getTodayDate()
  });
  const [lineItems, setLineItems] = useState([{ id: 1, item_id: '', item_name: '', hsn_code: '', godown_id: '', batch_number: '', expiry_date: '', quantity: 1, rate: 0, gst_rate: 18 }]);

  useEffect(() => { fetchData(); }, [currentBranch]);

  const fetchData = async () => {
    try {
      const [itemsRes, godownsRes] = await Promise.all([
        api.get('/inventory/items'),
        currentBranch?.id ? api.get(`/branches/${currentBranch.id}/godowns`) : Promise.resolve({ data: [] })
      ]);
      setItems(itemsRes.data);
      setGodowns(godownsRes.data);
    } catch (error) { console.error('Error:', error); }
    finally { setLoading(false); }
  };

  const handleItemChange = (index, itemId) => {
    const item = items.find(i => i.id === itemId);
    if (item) {
      const newItems = [...lineItems];
      newItems[index] = { ...newItems[index], item_id: itemId, item_name: item.name, hsn_code: item.hsn_code, rate: item.cost_price, gst_rate: item.gst_rate };
      setLineItems(newItems);
    }
  };

  const updateLineItem = (index, field, value) => {
    const newItems = [...lineItems];
    newItems[index][field] = value;
    setLineItems(newItems);
  };

  const addLineItem = () => {
    setLineItems([...lineItems, { id: Date.now(), item_id: '', item_name: '', hsn_code: '', godown_id: godowns[0]?.id || '', batch_number: '', expiry_date: '', quantity: 1, rate: 0, gst_rate: 18 }]);
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
    if (!formData.supplier_invoice_number) { alert('Enter supplier invoice number'); return; }
    const validItems = lineItems.filter(i => i.item_id && i.quantity > 0);
    if (validItems.length === 0) { alert('Add at least one item'); return; }

    setSaving(true);
    try {
      const invoiceItems = validItems.map(i => ({
        item_id: i.item_id, item_name: i.item_name, hsn_code: i.hsn_code, godown_id: i.godown_id || godowns[0]?.id,
        batch_number: i.batch_number, expiry_date: i.expiry_date || null,
        quantity: parseFloat(i.quantity), rate: parseFloat(i.rate),
        taxable_amount: i.quantity * i.rate, gst_rate: parseFloat(i.gst_rate)
      }));

      await api.post('/purchase/invoices', {
        branch_id: currentBranch.id,
        supplier_name: formData.supplier_name, supplier_address: formData.supplier_address,
        supplier_gstin: formData.supplier_gstin, supplier_state: formData.supplier_state,
        supplier_state_code: formData.supplier_state_code,
        supplier_invoice_number: formData.supplier_invoice_number,
        supplier_invoice_date: formData.supplier_invoice_date,
        invoice_date: formData.invoice_date,
        items: invoiceItems, subtotal: totals.subtotal, discount_amount: 0,
        taxable_amount: totals.subtotal, cgst_amount: totals.cgst, sgst_amount: totals.sgst,
        igst_amount: 0, round_off: 0, grand_total: totals.grandTotal
      });
      alert('Purchase entry saved!');
      resetForm();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error');
    } finally { setSaving(false); }
  };

  const resetForm = () => {
    setFormData({ invoice_date: getTodayDate(), supplier_name: '', supplier_address: '', supplier_gstin: '', supplier_state: 'Gujarat', supplier_state_code: '24', supplier_invoice_number: '', supplier_invoice_date: getTodayDate() });
    setLineItems([{ id: 1, item_id: '', item_name: '', hsn_code: '', godown_id: godowns[0]?.id || '', batch_number: '', expiry_date: '', quantity: 1, rate: 0, gst_rate: 18 }]);
  };

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="purchase-invoice">
      <div className="page-header">
        <div><h1>Purchase Entry</h1><p className="page-subtitle">{currentBranch?.name}</p></div>
        <div className="btn-group">
          <button className="btn btn-secondary" onClick={resetForm}>Clear</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}><Save size={16} /> {saving ? 'Saving...' : 'Save'}</button>
        </div>
      </div>

      <div className="card">
        <div className="card-header">Supplier & Invoice Details</div>
        <div className="card-content">
          <div className="form-row">
            <div className="form-group"><label className="form-label">Supplier Name *</label><input type="text" className="form-control" value={formData.supplier_name} onChange={e => setFormData({...formData, supplier_name: e.target.value})} /></div>
            <div className="form-group" style={{maxWidth: '200px'}}><label className="form-label">Supplier GSTIN</label><input type="text" className="form-control" value={formData.supplier_gstin} onChange={e => setFormData({...formData, supplier_gstin: e.target.value.toUpperCase()})} maxLength={15} /></div>
          </div>
          <div className="form-row">
            <div className="form-group" style={{maxWidth: '200px'}}><label className="form-label">Supplier Invoice No. *</label><input type="text" className="form-control" value={formData.supplier_invoice_number} onChange={e => setFormData({...formData, supplier_invoice_number: e.target.value})} /></div>
            <div className="form-group" style={{maxWidth: '150px'}}><label className="form-label">Supplier Inv. Date *</label><input type="date" className="form-control" value={formData.supplier_invoice_date} onChange={e => setFormData({...formData, supplier_invoice_date: e.target.value})} /></div>
            <div className="form-group" style={{maxWidth: '150px'}}><label className="form-label">Entry Date *</label><input type="date" className="form-control" value={formData.invoice_date} onChange={e => setFormData({...formData, invoice_date: e.target.value})} /></div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">Purchase Items</div>
        <div className="card-content">
          <table className="input-grid">
            <thead><tr><th>#</th><th>Item</th><th>Godown</th><th>Batch</th><th>Expiry</th><th className="text-right">Qty</th><th className="text-right">Rate</th><th className="text-right">GST%</th><th className="text-right">Amount</th><th></th></tr></thead>
            <tbody>
              {lineItems.map((item, index) => {
                const taxable = item.quantity * item.rate;
                const tax = taxable * (item.gst_rate / 100);
                return (
                  <tr key={item.id}>
                    <td className="text-center">{index + 1}</td>
                    <td><select className="form-control" value={item.item_id} onChange={e => handleItemChange(index, e.target.value)}><option value="">Select</option>{items.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}</select></td>
                    <td><select className="form-control" value={item.godown_id} onChange={e => updateLineItem(index, 'godown_id', e.target.value)} style={{width: '100px'}}>{godowns.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}</select></td>
                    <td><input type="text" className="form-control" value={item.batch_number} onChange={e => updateLineItem(index, 'batch_number', e.target.value)} style={{width: '100px'}} placeholder="Auto" /></td>
                    <td><input type="date" className="form-control" value={item.expiry_date} onChange={e => updateLineItem(index, 'expiry_date', e.target.value)} style={{width: '130px'}} /></td>
                    <td><input type="number" className="form-control text-right" value={item.quantity} onChange={e => updateLineItem(index, 'quantity', e.target.value)} style={{width: '70px'}} /></td>
                    <td><input type="number" step="0.01" className="form-control text-right" value={item.rate} onChange={e => updateLineItem(index, 'rate', e.target.value)} style={{width: '100px'}} /></td>
                    <td><select className="form-control" value={item.gst_rate} onChange={e => updateLineItem(index, 'gst_rate', e.target.value)} style={{width: '70px'}}><option value={0}>0%</option><option value={5}>5%</option><option value={12}>12%</option><option value={18}>18%</option><option value={28}>28%</option></select></td>
                    <td className="text-right" style={{fontFamily: 'var(--font-mono)'}}>{formatCurrency(taxable + tax)}</td>
                    <td><button className="btn btn-sm btn-danger" onClick={() => removeLineItem(index)} disabled={lineItems.length <= 1}><Trash2 size={14} /></button></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <button className="btn btn-secondary btn-sm" onClick={addLineItem} style={{marginTop: '8px'}}><Plus size={14} /> Add Item</button>

          <div className="totals-panel" style={{maxWidth: '350px', marginLeft: 'auto', marginTop: '16px'}}>
            <div className="totals-row"><span className="label">Subtotal</span><span className="value">{formatCurrency(totals.subtotal)}</span></div>
            <div className="totals-row"><span className="label">CGST</span><span className="value">{formatCurrency(totals.cgst)}</span></div>
            <div className="totals-row"><span className="label">SGST</span><span className="value">{formatCurrency(totals.sgst)}</span></div>
            <div className="totals-row highlight"><span className="label">Grand Total</span><span className="value">{formatCurrency(totals.grandTotal)}</span></div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PurchaseInvoice;
