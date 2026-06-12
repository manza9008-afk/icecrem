import React, { useState, useEffect } from 'react';
import { Save, Plus, Trash2, ArrowRight } from 'lucide-react';
import api, { formatCurrency, getTodayDate, formatDate, formatNumber } from '../../services/api';

const StockTransfer = ({ currentBranch }) => {
  const [items, setItems] = useState([]);
  const [godowns, setGodowns] = useState([]);
  const [branches, setBranches] = useState([]);
  const [transfers, setTransfers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  
  const [formData, setFormData] = useState({
    transfer_date: getTodayDate(),
    source_branch_id: '',
    source_godown_id: '',
    destination_branch_id: '',
    destination_godown_id: '',
    remarks: ''
  });
  
  const [lineItems, setLineItems] = useState([
    { id: 1, item_id: '', item_name: '', available_qty: 0, quantity: 0 }
  ]);

  useEffect(() => {
    fetchData();
  }, [currentBranch]);

  const fetchData = async () => {
    try {
      const [itemsRes, branchesRes, transfersRes] = await Promise.all([
        api.get('/inventory/items'),
        api.get('/branches'),
        api.get('/inventory/stock/transfers' + (currentBranch?.id ? `?branch_id=${currentBranch.id}` : ''))
      ]);
      setItems(itemsRes.data);
      setBranches(branchesRes.data);
      setTransfers(transfersRes.data);
      
      if (currentBranch?.id) {
        setFormData(prev => ({ ...prev, source_branch_id: currentBranch.id }));
        const godownsRes = await api.get(`/branches/${currentBranch.id}/godowns`);
        setGodowns(godownsRes.data);
      }
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSourceBranchChange = async (branchId) => {
    setFormData({ ...formData, source_branch_id: branchId, source_godown_id: '' });
    if (branchId) {
      const godownsRes = await api.get(`/branches/${branchId}/godowns`);
      setGodowns(godownsRes.data);
    } else {
      setGodowns([]);
    }
  };

  const handleDestinationBranchChange = async (branchId) => {
    setFormData({ ...formData, destination_branch_id: branchId, destination_godown_id: '' });
  };

  const handleItemChange = async (index, itemId) => {
    const item = items.find(i => i.id === itemId);
    if (item && formData.source_godown_id) {
      try {
        const stockRes = await api.get(`/inventory/stock?item_id=${itemId}&godown_id=${formData.source_godown_id}`);
        const available = stockRes.data.reduce((sum, s) => sum + s.total_quantity, 0);
        const newItems = [...lineItems];
        newItems[index] = {
          ...newItems[index],
          item_id: itemId,
          item_name: item.name,
          available_qty: available,
          quantity: 0
        };
        setLineItems(newItems);
      } catch (e) {
        console.error(e);
      }
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
      available_qty: 0,
      quantity: 0
    }]);
  };

  const removeLineItem = (index) => {
    if (lineItems.length <= 1) return;
    setLineItems(lineItems.filter((_, i) => i !== index));
  };

  const handleSave = async () => {
    if (!formData.source_branch_id || !formData.source_godown_id) { alert('Select source branch and godown'); return; }
    if (!formData.destination_branch_id || !formData.destination_godown_id) { alert('Select destination branch and godown'); return; }
    if (formData.source_godown_id === formData.destination_godown_id) { alert('Source and destination godowns cannot be the same'); return; }
    
    const validItems = lineItems.filter(i => i.item_id && i.quantity > 0);
    if (validItems.length === 0) { alert('Add at least one item with quantity'); return; }
    
    const overQty = validItems.find(i => i.quantity > i.available_qty);
    if (overQty) { alert(`Cannot transfer more than available quantity for ${overQty.item_name}`); return; }

    setSaving(true);
    try {
      const transferItems = validItems.map(i => ({
        item_id: i.item_id,
        item_name: i.item_name,
        quantity: parseFloat(i.quantity)
      }));

      await api.post('/inventory/stock/transfer', {
        ...formData,
        items: transferItems
      });
      
      alert('Stock Transfer completed!');
      resetForm();
      fetchData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error processing transfer');
    } finally {
      setSaving(false);
    }
  };

  const resetForm = () => {
    setShowForm(false);
    setFormData({
      transfer_date: getTodayDate(),
      source_branch_id: currentBranch?.id || '',
      source_godown_id: '',
      destination_branch_id: '',
      destination_godown_id: '',
      remarks: ''
    });
    setLineItems([{ id: 1, item_id: '', item_name: '', available_qty: 0, quantity: 0 }]);
  };

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  if (showForm) {
    const destBranch = branches.find(b => b.id === formData.destination_branch_id);
    const destGodowns = destBranch ? (destBranch.godowns || []) : [];
    
    return (
      <div data-testid="stock-transfer-form">
        <div className="page-header">
          <div>
            <h1>New Stock Transfer</h1>
            <p className="page-subtitle">Inter-Branch/Godown Transfer</p>
          </div>
          <div className="btn-group">
            <button className="btn btn-secondary" onClick={resetForm}>Cancel</button>
            <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
              <Save size={16} /> {saving ? 'Processing...' : 'Complete Transfer'}
            </button>
          </div>
        </div>

        <div className="card">
          <div className="card-header">Transfer Details</div>
          <div className="card-content">
            <div className="form-row">
              <div className="form-group" style={{ maxWidth: '150px' }}>
                <label className="form-label">Transfer Date *</label>
                <input type="date" className="form-control" value={formData.transfer_date}
                  onChange={e => setFormData({ ...formData, transfer_date: e.target.value })} />
              </div>
            </div>
            
            <div className="grid-2" style={{ marginTop: '16px' }}>
              <div style={{ padding: '12px', background: 'var(--bg-secondary)', borderRadius: '4px' }}>
                <h4 style={{ marginBottom: '12px', color: 'var(--danger)' }}>Source (FROM)</h4>
                <div className="form-group">
                  <label className="form-label">Branch *</label>
                  <select className="form-control" value={formData.source_branch_id} onChange={e => handleSourceBranchChange(e.target.value)}>
                    <option value="">Select Branch</option>
                    {branches.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Godown *</label>
                  <select className="form-control" value={formData.source_godown_id} onChange={e => setFormData({ ...formData, source_godown_id: e.target.value })}>
                    <option value="">Select Godown</option>
                    {godowns.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
                  </select>
                </div>
              </div>
              
              <div style={{ padding: '12px', background: '#e6fffa', borderRadius: '4px' }}>
                <h4 style={{ marginBottom: '12px', color: 'var(--success)' }}>Destination (TO)</h4>
                <div className="form-group">
                  <label className="form-label">Branch *</label>
                  <select className="form-control" value={formData.destination_branch_id} onChange={e => handleDestinationBranchChange(e.target.value)}>
                    <option value="">Select Branch</option>
                    {branches.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Godown *</label>
                  <select className="form-control" value={formData.destination_godown_id} onChange={e => setFormData({ ...formData, destination_godown_id: e.target.value })}>
                    <option value="">Select Godown</option>
                    {formData.destination_branch_id && branches.find(b => b.id === formData.destination_branch_id)?.godowns?.map(g => (
                      <option key={g.id} value={g.id}>{g.name}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">Transfer Items</div>
          <div className="card-content">
            <table className="input-grid">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Item</th>
                  <th className="text-right">Available Qty</th>
                  <th className="text-right">Transfer Qty *</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {lineItems.map((item, index) => (
                  <tr key={item.id}>
                    <td className="text-center">{index + 1}</td>
                    <td>
                      <select className="form-control" value={item.item_id} onChange={e => handleItemChange(index, e.target.value)} disabled={!formData.source_godown_id}>
                        <option value="">Select Item</option>
                        {items.map(i => <option key={i.id} value={i.id}>{i.code} - {i.name}</option>)}
                      </select>
                    </td>
                    <td className="text-right" style={{ fontFamily: 'var(--font-mono)' }}>{formatNumber(item.available_qty)}</td>
                    <td>
                      <input type="number" className="form-control text-right" value={item.quantity}
                        onChange={e => updateLineItem(index, 'quantity', Math.min(parseFloat(e.target.value) || 0, item.available_qty))}
                        max={item.available_qty} style={{ width: '100px' }} />
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
            <button className="btn btn-secondary btn-sm" onClick={addLineItem} style={{ marginTop: '8px' }} disabled={!formData.source_godown_id}>
              <Plus size={14} /> Add Item
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="stock-transfer">
      <div className="page-header">
        <div>
          <h1>Stock Transfers</h1>
          <p className="page-subtitle">Inter-Branch/Godown Transfers</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>
          <Plus size={16} /> New Transfer
        </button>
      </div>

      <div className="card">
        <table className="data-grid">
          <thead>
            <tr>
              <th>Date</th>
              <th>Transfer No.</th>
              <th>From</th>
              <th></th>
              <th>To</th>
              <th className="text-right">Items</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {transfers.map(t => (
              <tr key={t.id}>
                <td>{formatDate(t.transfer_date)}</td>
                <td><strong>{t.transfer_number}</strong></td>
                <td>{t.source_godown_name}</td>
                <td className="text-center"><ArrowRight size={16} color="var(--text-muted)" /></td>
                <td>{t.destination_godown_name}</td>
                <td className="numeric">{t.items?.length || 0}</td>
                <td><span className="badge badge-success">{t.status?.toUpperCase()}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
        {transfers.length === 0 && <div className="empty-state"><p>No stock transfers found</p></div>}
      </div>
    </div>
  );
};

export default StockTransfer;
