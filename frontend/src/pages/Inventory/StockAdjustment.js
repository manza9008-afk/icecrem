import React, { useState, useEffect } from 'react';
import { Save, Plus, Trash2, Printer } from 'lucide-react';
import api, { getTodayDate, formatDate, formatNumber, getItemSizeLabel } from '../../services/api';

const StockAdjustment = ({ currentBranch }) => {
  const [items, setItems] = useState([]);
  const [stockItems, setStockItems] = useState([]);
  const [godowns, setGodowns] = useState([]);
  const [adjustments, setAdjustments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  
  const [formData, setFormData] = useState({
    adjustment_date: getTodayDate(),
    godown_id: '',
    adjustment_type: 'production',
    reason: '',
    remarks: ''
  });
  
  const [lineItems, setLineItems] = useState([
    { id: 1, item_id: '', item_name: '', size: '', system_qty: 0, physical_qty: 0, difference: 0, rate: 0 }
  ]);

  useEffect(() => {
    fetchData();
  }, [currentBranch]);

  useEffect(() => {
    if (showForm && formData.godown_id) {
      fetchStockItems(formData.godown_id);
    }
  }, [showForm, formData.godown_id, currentBranch]);

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

  const fetchStockItems = async (godownId) => {
    if (!currentBranch?.id || !godownId) {
      setStockItems([]);
      return;
    }
    try {
      const response = await api.get(`/inventory/ready-stock?branch_id=${currentBranch.id}&godown_id=${godownId}`);
      setStockItems(response.data);
    } catch (error) {
      console.error(error);
      setStockItems([]);
    }
  };

  const handleStockChange = (godownId) => {
    setFormData({ ...formData, godown_id: godownId });
    setLineItems([{ id: 1, item_id: '', item_name: '', size: '', system_qty: 0, physical_qty: 0, difference: 0, rate: 0 }]);
    fetchStockItems(godownId);
  };

  const handleItemChange = async (index, itemId) => {
    const item = items.find(i => i.id === itemId);
    const stockItem = stockItems.find(i => i.item_id === itemId);
    if ((item || stockItem) && formData.godown_id) {
      try {
        const stockRes = await api.get(`/inventory/stock?item_id=${itemId}&godown_id=${formData.godown_id}`);
        const systemQty = stockRes.data.reduce((sum, s) => sum + s.total_quantity, 0);
        const newItems = [...lineItems];
        newItems[index] = {
          ...newItems[index],
          item_id: itemId,
          item_name: item?.name || stockItem?.item_name || '',
          size: getItemSizeLabel(item) || stockItem?.size || '',
          system_qty: systemQty,
          physical_qty: systemQty,
          difference: 0,
          rate: 0
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
      size: '',
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
    return { totalIncrease: 0, totalDecrease: 0, netValue: 0 };
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
        size: i.size,
        system_qty: i.system_qty,
        physical_qty: parseFloat(i.physical_qty),
        difference: i.difference,
        rate: 0,
        unit_cost: 0,
        value_difference: 0
      }));

      await api.post('/inventory/stock/adjustment', {
        branch_id: currentBranch.id,
        ...formData,
        items: adjustmentItems,
        total_increase_value: totals.totalIncrease,
        total_decrease_value: totals.totalDecrease,
        net_value: totals.netValue,
        remarks: formData.remarks
      });
      
      alert('Stock maintenance saved!');
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
      adjustment_type: 'production',
      reason: '',
      remarks: ''
    });
    setStockItems([]);
    setLineItems([{ id: 1, item_id: '', item_name: '', size: '', system_qty: 0, physical_qty: 0, difference: 0, rate: 0 }]);
  };

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  if (showForm) {
    return (
      <div data-testid="stock-adjustment-form">
        <div className="page-header">
          <div>
            <h1>Stock Maintenance</h1>
            <p className="page-subtitle">Production and evening stock reconciliation</p>
          </div>
          <div className="btn-group">
            <button className="btn btn-secondary" onClick={resetForm}>Cancel</button>
            <button className="btn btn-secondary" onClick={() => window.print()}>
              <Printer size={16} /> Print
            </button>
            <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
              <Save size={16} /> {saving ? 'Saving...' : 'Save Maintenance'}
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
                <label className="form-label">Stock *</label>
                <select className="form-control" value={formData.godown_id}
                  onChange={e => handleStockChange(e.target.value)}>
                  <option value="">Select Stock</option>
                  {godowns.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ maxWidth: '200px' }}>
                <label className="form-label">Maintenance Type</label>
                <select className="form-control" value={formData.adjustment_type}
                  onChange={e => setFormData({ ...formData, adjustment_type: e.target.value })}>
                  <option value="production">Production</option>
                  <option value="evening_stock">Evening Stock</option>
                  <option value="physical_count">Physical Count</option>
                  <option value="damage">Damage / Wastage</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Reason *</label>
                <input type="text" className="form-control" value={formData.reason}
                  onChange={e => setFormData({ ...formData, reason: e.target.value })}
                  placeholder="E.g., Evening production closing stock" />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Remarks</label>
                <input type="text" className="form-control" value={formData.remarks}
                  onChange={e => setFormData({ ...formData, remarks: e.target.value })}
                  placeholder="Optional print/report note" />
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
                  <th>Size</th>
                  <th className="text-right">System Qty</th>
                  <th className="text-right">Physical Qty *</th>
                  <th className="text-right">Difference</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {lineItems.map((item, index) => (
                  <tr key={item.id}>
                    <td className="text-center">{index + 1}</td>
                    <td>
                      <select className="form-control" value={item.item_id}
                        onChange={e => handleItemChange(index, e.target.value)}
                        disabled={!formData.godown_id}>
                        <option value="">Select Item</option>
                        {stockItems.map(i => <option key={i.item_id} value={i.item_id}>{i.item_name}</option>)}
                      </select>
                      {formData.godown_id && stockItems.length === 0 && (
                        <div style={{ fontSize: '12px', color: 'var(--danger)', marginTop: '4px' }}>
                          No item found in selected stock
                        </div>
                      )}
                    </td>
                    <td>{item.size || '-'}</td>
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
                    <td>
                      <button className="btn btn-sm btn-danger" onClick={() => removeLineItem(index)} disabled={lineItems.length <= 1}>
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button className="btn btn-secondary btn-sm" onClick={addLineItem} style={{ marginTop: '8px' }} disabled={!formData.godown_id}>
              <Plus size={14} /> Add Item
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="stock-adjustment">
      <div className="page-header">
        <div>
          <h1>Stock Maintenance</h1>
          <p className="page-subtitle">Evening production and maintenance history</p>
        </div>
        <div className="btn-group">
          <button className="btn btn-secondary" onClick={() => window.print()}>
            <Printer size={16} /> Print
          </button>
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>
            <Plus size={16} /> New Maintenance
          </button>
        </div>
      </div>

      <div className="card">
        <table className="data-grid">
          <thead>
            <tr>
              <th>Date</th>
              <th>Maintenance No.</th>
              <th>Stock</th>
              <th>Type</th>
              <th>Reason</th>
              <th className="text-right">Items</th>
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
                <td className="numeric">{adj.item_count || adj.items?.length || 0}</td>
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