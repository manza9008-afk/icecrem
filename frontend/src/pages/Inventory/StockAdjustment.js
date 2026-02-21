import React, { useState, useEffect } from 'react';
import { Save, Plus, Trash2 } from 'lucide-react';
import api, { formatCurrency, getTodayDate, formatDate, formatNumber } from '../../services/api';

const StockAdjustment = ({ currentBranch }) => {
  const [items, setItems] = useState([]);
  const [godowns, setGodowns] = useState([]);
  const [adjustments, setAdjustments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  
  const [formData, setFormData] = useState({
    adjustment_date: getTodayDate(),
    godown_id: '',
    adjustment_type: 'physical_count',
    reason: '',
    remarks: ''
  });
  
  const [lineItems, setLineItems] = useState([
    { id: 1, item_id: '', item_name: '', system_qty: 0, physical_qty: 0, difference: 0, rate: 0 }
  ]);

  useEffect(() => {
    fetchData();
  }, [currentBranch]);

  const fetchData = async () => {
    try {
      const [itemsRes, adjustmentsRes] = await Promise.all([
        api.get('/inventory/items'),
        api.get('/inventory/stock/adjustments' + (currentBranch?.id ? `?branch_id=${currentBranch.id}` : ''))
      ]);
      setItems(itemsRes.data);
      setAdjustments(adjustmentsRes.data);
      
      if (currentBranch?.id) {
        const godownsRes = await api.get(`/branches/${currentBranch.id}/godowns`);
        setGodowns(godownsRes.data);
      }
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleItemChange = async (index, itemId) => {
    const item = items.find(i => i.id === itemId);
    if (item && formData.godown_id) {
      try {
        const stockRes = await api.get(`/inventory/stock?item_id=${itemId}&godown_id=${formData.godown_id}`);
        const systemQty = stockRes.data.reduce((sum, s) => sum + s.total_quantity, 0);
        const avgCost = stockRes.data.length > 0 ? stockRes.data[0].average_cost : item.cost_price;
        
        const newItems = [...lineItems];
        newItems[index] = {
          ...newItems[index],
          item_id: itemId,
          item_name: item.name,
          system_qty: systemQty,
          physical_qty: systemQty,
          difference: 0,
          rate: avgCost
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
    
    if (field === 'physical_qty') {
      newItems[index].difference = parseFloat(value || 0) - newItems[index].system_qty;
    }
    
    setLineItems(newItems);
  };

  const addLineItem = () => {
    setLineItems([...lineItems, {
      id: Date.now(),
      item_id: '',
      item_name: '',
      system_qty: 0,
      physical_qty: 0,
      difference: 0,
      rate: 0
    }]);
  };

  const removeLineItem = (index) => {
    if (lineItems.length <= 1) return;
    setLineItems(lineItems.filter((_, i) => i !== index));
  };

  const calculateTotals = () => {
    let totalIncrease = 0, totalDecrease = 0;
    lineItems.forEach(item => {
      const value = Math.abs(item.difference) * item.rate;
      if (item.difference > 0) totalIncrease += value;
      else if (item.difference < 0) totalDecrease += value;
    });
    return { totalIncrease, totalDecrease, netValue: totalIncrease - totalDecrease };
  };

  const totals = calculateTotals();

  const handleSave = async () => {
    if (!currentBranch) { alert('Select a branch'); return; }
    if (!formData.godown_id) { alert('Select a godown'); return; }
    if (!formData.reason) { alert('Enter adjustment reason'); return; }
    
    const validItems = lineItems.filter(i => i.item_id && i.difference !== 0);
    if (validItems.length === 0) { alert('No adjustments to save'); return; }

    setSaving(true);
    try {
      const adjustmentItems = validItems.map(i => ({
        item_id: i.item_id,
        item_name: i.item_name,
        system_qty: i.system_qty,
        physical_qty: parseFloat(i.physical_qty),
        difference: i.difference,
        rate: i.rate,
        value: Math.abs(i.difference) * i.rate
      }));

      await api.post('/inventory/stock/adjustment', {
        branch_id: currentBranch.id,
        ...formData,
        items: adjustmentItems,
        total_increase_value: totals.totalIncrease,
        total_decrease_value: totals.totalDecrease,
        net_value: totals.netValue
      });
      
      alert('Stock Adjustment saved!');
      resetForm();
      fetchData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error saving adjustment');
    } finally {
      setSaving(false);
    }
  };

  const resetForm = () => {
    setShowForm(false);
    setFormData({
      adjustment_date: getTodayDate(),
      godown_id: godowns[0]?.id || '',
      adjustment_type: 'physical_count',
      reason: '',
      remarks: ''
    });
    setLineItems([{ id: 1, item_id: '', item_name: '', system_qty: 0, physical_qty: 0, difference: 0, rate: 0 }]);
  };

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  if (showForm) {
    return (
      <div data-testid="stock-adjustment-form">
        <div className="page-header">
          <div>
            <h1>Stock Adjustment</h1>
            <p className="page-subtitle">Physical Stock Reconciliation</p>
          </div>
          <div className="btn-group">
            <button className="btn btn-secondary" onClick={resetForm}>Cancel</button>
            <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
              <Save size={16} /> {saving ? 'Saving...' : 'Save Adjustment'}
            </button>
          </div>
        </div>

        <div className="card">
          <div className="card-header">Adjustment Details</div>
          <div className="card-content">
            <div className="form-row">
              <div className="form-group" style={{ maxWidth: '150px' }}>
                <label className="form-label">Date *</label>
                <input type="date" className="form-control" value={formData.adjustment_date}
                  onChange={e => setFormData({ ...formData, adjustment_date: e.target.value })} />
              </div>
              <div className="form-group" style={{ maxWidth: '200px' }}>
                <label className="form-label">Godown *</label>
                <select className="form-control" value={formData.godown_id}
                  onChange={e => setFormData({ ...formData, godown_id: e.target.value })}>
                  <option value="">Select Godown</option>
                  {godowns.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ maxWidth: '200px' }}>
                <label className="form-label">Adjustment Type</label>
                <select className="form-control" value={formData.adjustment_type}
                  onChange={e => setFormData({ ...formData, adjustment_type: e.target.value })}>
                  <option value="physical_count">Physical Count</option>
                  <option value="damage">Damage/Wastage</option>
                  <option value="expiry">Expiry Write-off</option>
                  <option value="theft">Theft/Loss</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Reason *</label>
                <input type="text" className="form-control" value={formData.reason}
                  onChange={e => setFormData({ ...formData, reason: e.target.value })}
                  placeholder="E.g., Physical verification on 20-Feb-2026" />
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">Stock Items</div>
          <div className="card-content">
            <table className="input-grid">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Item</th>
                  <th className="text-right">System Qty</th>
                  <th className="text-right">Physical Qty *</th>
                  <th className="text-right">Difference</th>
                  <th className="text-right">Rate</th>
                  <th className="text-right">Value</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {lineItems.map((item, index) => {
                  const value = Math.abs(item.difference) * item.rate;
                  return (
                    <tr key={item.id}>
                      <td className="text-center">{index + 1}</td>
                      <td>
                        <select className="form-control" value={item.item_id}
                          onChange={e => handleItemChange(index, e.target.value)}
                          disabled={!formData.godown_id}>
                          <option value="">Select Item</option>
                          {items.map(i => <option key={i.id} value={i.id}>{i.code} - {i.name}</option>)}
                        </select>
                      </td>
                      <td className="text-right" style={{ fontFamily: 'var(--font-mono)' }}>{formatNumber(item.system_qty)}</td>
                      <td>
                        <input type="number" className="form-control text-right" value={item.physical_qty}
                          onChange={e => updateLineItem(index, 'physical_qty', e.target.value)}
                          style={{ width: '100px' }} />
                      </td>
                      <td className="text-right" style={{
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 'bold',
                        color: item.difference > 0 ? 'var(--success)' : item.difference < 0 ? 'var(--danger)' : ''
                      }}>
                        {item.difference > 0 ? '+' : ''}{formatNumber(item.difference)}
                      </td>
                      <td className="text-right" style={{ fontFamily: 'var(--font-mono)' }}>{formatCurrency(item.rate)}</td>
                      <td className="text-right" style={{ fontFamily: 'var(--font-mono)' }}>{formatCurrency(value)}</td>
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
            <button className="btn btn-secondary btn-sm" onClick={addLineItem} style={{ marginTop: '8px' }} disabled={!formData.godown_id}>
              <Plus size={14} /> Add Item
            </button>

            <div className="totals-panel" style={{ maxWidth: '350px', marginLeft: 'auto', marginTop: '16px' }}>
              <div className="totals-row">
                <span className="label">Stock Increase Value</span>
                <span className="value" style={{ color: 'var(--success)' }}>+{formatCurrency(totals.totalIncrease)}</span>
              </div>
              <div className="totals-row">
                <span className="label">Stock Decrease Value</span>
                <span className="value" style={{ color: 'var(--danger)' }}>-{formatCurrency(totals.totalDecrease)}</span>
              </div>
              <div className="totals-row highlight">
                <span className="label">Net Adjustment</span>
                <span className="value" style={{ color: totals.netValue >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                  {totals.netValue >= 0 ? '+' : ''}{formatCurrency(totals.netValue)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="stock-adjustment">
      <div className="page-header">
        <div>
          <h1>Stock Adjustments</h1>
          <p className="page-subtitle">Physical Stock Reconciliation History</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>
          <Plus size={16} /> New Adjustment
        </button>
      </div>

      <div className="card">
        <table className="data-grid">
          <thead>
            <tr>
              <th>Date</th>
              <th>Adjustment No.</th>
              <th>Godown</th>
              <th>Type</th>
              <th>Reason</th>
              <th className="text-right">Net Value</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {adjustments.map(adj => (
              <tr key={adj.id}>
                <td>{formatDate(adj.adjustment_date)}</td>
                <td><strong>{adj.adjustment_number}</strong></td>
                <td>{adj.godown_name}</td>
                <td>{adj.adjustment_type?.replace('_', ' ').toUpperCase()}</td>
                <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>{adj.reason}</td>
                <td className="numeric" style={{ color: adj.net_value >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                  {adj.net_value >= 0 ? '+' : ''}{formatCurrency(adj.net_value)}
                </td>
                <td><span className="badge badge-success">{adj.status?.toUpperCase()}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
        {adjustments.length === 0 && <div className="empty-state"><p>No stock adjustments found</p></div>}
      </div>
    </div>
  );
};

export default StockAdjustment;
