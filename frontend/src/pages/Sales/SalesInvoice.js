import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Save, Plus, Trash2 } from 'lucide-react';
import api, { formatCurrency, getTodayDate } from '../../services/api';

const SalesInvoice = ({ currentBranch }) => {
  const { type = 'gst' } = useParams();
  const [items, setItems] = useState([]);
  const [godowns, setGodowns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    invoice_date: getTodayDate(), customer_name: '', customer_address: '', customer_gstin: '',
    customer_state: 'Gujarat', customer_state_code: '24', invoice_type: type
  });
  const [lineItems, setLineItems] = useState([{ id: 1, item_id: '', item_name: '', hsn_code: '', godown_id: '', quantity: 1, rate: 0, discount_percent: 0, gst_rate: 18 }]);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { fetchData(); setFormData(f => ({...f, invoice_type: type})); }, [currentBranch, type]);

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
      newItems[index] = { ...newItems[index], item_id: itemId, item_name: item.name, hsn_code: item.hsn_code, rate: item.selling_price, gst_rate: item.gst_rate };
      setLineItems(newItems);
    }
  };

  const updateLineItem = (index, field, value) => {
    const newItems = [...lineItems];
    newItems[index][field] = value;
    setLineItems(newItems);
  };

  const addLineItem = () => {
    setLineItems([...lineItems, { id: Date.now(), item_id: '', item_name: '', hsn_code: '', godown_id: godowns[0]?.id || '', quantity: 1, rate: 0, discount_percent: 0, gst_rate: 18 }]);
  };

  const removeLineItem = (index) => {
    if (lineItems.length <= 1) return;
    setLineItems(lineItems.filter((_, i) => i !== index));
  };

  const calculateTotals = () => {
    let subtotal = 0, discount = 0, taxableAmount = 0, cgst = 0, sgst = 0;
    lineItems.forEach(item => {
      const amount = item.quantity * item.rate;
      const discAmt = amount * (item.discount_percent / 100);
      const taxable = amount - discAmt;
      const tax = taxable * (item.gst_rate / 100);
      subtotal += amount;
      discount += discAmt;
      taxableAmount += taxable;
      cgst += tax / 2;
      sgst += tax / 2;
    });
    const grandTotal = taxableAmount + cgst + sgst;
    return { subtotal, discount, taxableAmount, cgst, sgst, grandTotal };
  };

  const totals = calculateTotals();

  const handleSave = async () => {
    if (!currentBranch) { alert('Select a branch'); return; }
    if (!formData.customer_name) { alert('Enter customer name'); return; }
    const validItems = lineItems.filter(i => i.item_id && i.quantity > 0);
    if (validItems.length === 0) { alert('Add at least one item'); return; }

    setSaving(true);
    try {
      const invoiceItems = validItems.map(i => ({
        item_id: i.item_id, item_name: i.item_name, hsn_code: i.hsn_code, godown_id: i.godown_id || godowns[0]?.id,
        quantity: parseFloat(i.quantity), rate: parseFloat(i.rate), discount_percent: parseFloat(i.discount_percent) || 0,
        discount_amount: (i.quantity * i.rate * i.discount_percent / 100),
        taxable_amount: i.quantity * i.rate * (1 - i.discount_percent / 100),
        gst_rate: parseFloat(i.gst_rate)
      }));

      await api.post('/sales/invoices', {
        branch_id: currentBranch.id, invoice_type: formData.invoice_type,
        customer_name: formData.customer_name, customer_address: formData.customer_address,
        customer_gstin: formData.customer_gstin, customer_state: formData.customer_state,
        customer_state_code: formData.customer_state_code, invoice_date: formData.invoice_date,
        items: invoiceItems, subtotal: totals.subtotal, discount_amount: totals.discount,
        taxable_amount: totals.taxableAmount, cgst_amount: totals.cgst, sgst_amount: totals.sgst,
        igst_amount: 0, round_off: 0, grand_total: totals.grandTotal
      });
      alert('Invoice saved!');
      resetForm();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error saving invoice');
    } finally { setSaving(false); }
  };

  const resetForm = () => {
    setFormData({ invoice_date: getTodayDate(), customer_name: '', customer_address: '', customer_gstin: '', customer_state: 'Gujarat', customer_state_code: '24', invoice_type: type });
    setLineItems([{ id: 1, item_id: '', item_name: '', hsn_code: '', godown_id: godowns[0]?.id || '', quantity: 1, rate: 0, discount_percent: 0, gst_rate: 18 }]);
  };

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="sales-invoice">
      <div className="page-header">
        <div><h1>{type === 'gst' ? 'GST Invoice' : 'Kacha Bill'}</h1><p className="page-subtitle">{currentBranch?.name}</p></div>
        <div className="btn-group">
          <button className="btn btn-secondary" onClick={resetForm}>Clear</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}><Save size={16} /> {saving ? 'Saving...' : 'Save Invoice'}</button>
        </div>
      </div>

      <div className="card">
        <div className="card-header">Customer Details</div>
        <div className="card-content">
          <div className="form-row">
            <div className="form-group" style={{maxWidth: '150px'}}><label className="form-label">Date *</label><input type="date" className="form-control" value={formData.invoice_date} onChange={e => setFormData({...formData, invoice_date: e.target.value})} /></div>
            <div className="form-group"><label className="form-label">Customer Name *</label><input type="text" className="form-control" value={formData.customer_name} onChange={e => setFormData({...formData, customer_name: e.target.value})} /></div>
            {type === 'gst' && <div className="form-group" style={{maxWidth: '200px'}}><label className="form-label">GSTIN</label><input type="text" className="form-control" value={formData.customer_gstin} onChange={e => setFormData({...formData, customer_gstin: e.target.value.toUpperCase()})} maxLength={15} /></div>}
          </div>
          <div className="form-row">
            <div className="form-group"><label className="form-label">Address</label><input type="text" className="form-control" value={formData.customer_address} onChange={e => setFormData({...formData, customer_address: e.target.value})} /></div>
            <div className="form-group" style={{maxWidth: '150px'}}><label className="form-label">State</label><input type="text" className="form-control" value={formData.customer_state} onChange={e => setFormData({...formData, customer_state: e.target.value})} /></div>
            <div className="form-group" style={{maxWidth: '80px'}}><label className="form-label">Code</label><input type="text" className="form-control" value={formData.customer_state_code} onChange={e => setFormData({...formData, customer_state_code: e.target.value})} maxLength={2} /></div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">Invoice Items</div>
        <div className="card-content">
          <table className="input-grid">
            <thead><tr><th>#</th><th>Item</th><th>HSN</th><th>Godown</th><th className="text-right">Qty</th><th className="text-right">Rate</th><th className="text-right">Disc %</th><th className="text-right">GST %</th><th className="text-right">Amount</th><th></th></tr></thead>
            <tbody>
              {lineItems.map((item, index) => {
                const amount = item.quantity * item.rate;
                const discAmount = amount * (item.discount_percent / 100);
                const taxable = amount - discAmount;
                const tax = taxable * (item.gst_rate / 100);
                const total = taxable + tax;
                return (
                  <tr key={item.id}>
                    <td className="text-center">{index + 1}</td>
                    <td><select className="form-control" value={item.item_id} onChange={e => handleItemChange(index, e.target.value)}><option value="">Select</option>{items.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}</select></td>
                    <td><input type="text" className="form-control" value={item.hsn_code} readOnly style={{width: '80px'}} /></td>
                    <td><select className="form-control" value={item.godown_id} onChange={e => updateLineItem(index, 'godown_id', e.target.value)} style={{width: '100px'}}>{godowns.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}</select></td>
                    <td><input type="number" className="form-control text-right" value={item.quantity} onChange={e => updateLineItem(index, 'quantity', e.target.value)} style={{width: '70px'}} /></td>
                    <td><input type="number" step="0.01" className="form-control text-right" value={item.rate} onChange={e => updateLineItem(index, 'rate', e.target.value)} style={{width: '100px'}} /></td>
                    <td><input type="number" step="0.01" className="form-control text-right" value={item.discount_percent} onChange={e => updateLineItem(index, 'discount_percent', e.target.value)} style={{width: '60px'}} /></td>
                    <td><select className="form-control" value={item.gst_rate} onChange={e => updateLineItem(index, 'gst_rate', e.target.value)} style={{width: '70px'}}><option value={0}>0%</option><option value={5}>5%</option><option value={12}>12%</option><option value={18}>18%</option><option value={28}>28%</option></select></td>
                    <td className="text-right" style={{fontFamily: 'var(--font-mono)'}}>{formatCurrency(total)}</td>
                    <td><button className="btn btn-sm btn-danger" onClick={() => removeLineItem(index)} disabled={lineItems.length <= 1}><Trash2 size={14} /></button></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <button className="btn btn-secondary btn-sm" onClick={addLineItem} style={{marginTop: '8px'}}><Plus size={14} /> Add Item</button>

          <div className="totals-panel" style={{maxWidth: '350px', marginLeft: 'auto', marginTop: '16px'}}>
            <div className="totals-row"><span className="label">Subtotal</span><span className="value">{formatCurrency(totals.subtotal)}</span></div>
            <div className="totals-row"><span className="label">Discount</span><span className="value">-{formatCurrency(totals.discount)}</span></div>
            <div className="totals-row"><span className="label">Taxable Amount</span><span className="value">{formatCurrency(totals.taxableAmount)}</span></div>
            {type === 'gst' && (
              <>
                <div className="totals-row"><span className="label">CGST</span><span className="value">{formatCurrency(totals.cgst)}</span></div>
                <div className="totals-row"><span className="label">SGST</span><span className="value">{formatCurrency(totals.sgst)}</span></div>
              </>
            )}
            <div className="totals-row highlight"><span className="label">Grand Total</span><span className="value">{formatCurrency(totals.grandTotal)}</span></div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SalesInvoice;
