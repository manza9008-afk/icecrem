import React, { useEffect, useState } from 'react';
import { Plus, Printer, Save } from 'lucide-react';
import api, { formatDate, formatNumber, getTodayDate, getItemSizeLabel } from '../../services/api';

const StockLedger = ({ currentBranch, showDate = false }) => {
  const [movements, setMovements] = useState([]);
  const [items, setItems] = useState([]);
  const [godowns, setGodowns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingOut, setSavingOut] = useState(false);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedGodown, setSelectedGodown] = useState('');
  const [showOutForm, setShowOutForm] = useState(false);
  const [outForm, setOutForm] = useState({
    transaction_date: getTodayDate(),
    item_id: '',
    godown_id: '',
    quantity: 1,
    remarks: ''
  });

  useEffect(() => {
    setSelectedGodown('');
    fetchMasters();
  }, [currentBranch]);

  useEffect(() => {
    fetchMovements();
  }, [currentBranch, selectedGodown, startDate, endDate]);

  const fetchMasters = async () => {
    try {
      const [itemsRes, godownsRes] = await Promise.all([
        api.get('/inventory/items'),
        currentBranch?.id ? api.get(`/branches/${currentBranch.id}/godowns`) : Promise.resolve({ data: [] })
      ]);
      setItems(itemsRes.data);
      setGodowns(godownsRes.data);
      setOutForm(prev => ({ ...prev, godown_id: godownsRes.data[0]?.id || '' }));
    } catch (error) {
      console.error(error);
      setItems([]);
      setGodowns([]);
    }
  };

  const fetchMovements = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (currentBranch?.id) params.append('branch_id', currentBranch.id);
      if (selectedGodown) params.append('godown_id', selectedGodown);
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      const res = await api.get(`/inventory/stock/movements?${params.toString()}`);
      setMovements(res.data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // Group same date + same item + same type into one row
  const groupedMovements = Object.values(
    movements.reduce((acc, m) => {
      const dateStr = m.date ? String(m.date).substring(0, 10) : '';
      const key = `${dateStr}__${m.item_name}__${m.size}__${m.movement_type}`;
      if (!acc[key]) {
        acc[key] = { ...m, date: dateStr, in_qty: m.in_qty || 0, out_qty: m.out_qty || 0 };
      } else {
        acc[key].in_qty += m.in_qty || 0;
        acc[key].out_qty += m.out_qty || 0;
        if (m.is_low_stock) {
          acc[key].is_low_stock = true;
          acc[key].balance_qty = m.balance_qty;
        }
      }
      return acc;
    }, {})
  );

  const totalInQty = groupedMovements.reduce((sum, item) => sum + (item.in_qty || 0), 0);
  const totalOutQty = groupedMovements.reduce((sum, item) => sum + (item.out_qty || 0), 0);
  const alertCount = groupedMovements.filter(item => item.is_low_stock).length;

  const handleOutItemChange = (itemId) => {
    const item = items.find(i => i.id === itemId);
    setOutForm(prev => ({
      ...prev,
      item_id: itemId,
      item_name: item?.name || '',
      size: getItemSizeLabel(item)
    }));
  };

  const saveOutQty = async () => {
    if (!currentBranch?.id) { alert('Select a branch'); return; }
    if (!outForm.item_id) { alert('Select an item'); return; }
    if (!outForm.godown_id) { alert('Select stock'); return; }
    if (Number(outForm.quantity || 0) <= 0) { alert('Enter Out Qty'); return; }

    setSavingOut(true);
    try {
      await api.post('/inventory/stock/outward', {
        branch_id: currentBranch.id,
        godown_id: outForm.godown_id,
        item_id: outForm.item_id,
        quantity: Number(outForm.quantity),
        transaction_date: outForm.transaction_date,
        remarks: outForm.remarks
      });
      alert('Out Qty saved!');
      setOutForm({
        transaction_date: getTodayDate(),
        item_id: '',
        godown_id: outForm.godown_id,
        quantity: 1,
        remarks: ''
      });
      setShowOutForm(false);
      fetchMovements();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error saving Out Qty');
    } finally {
      setSavingOut(false);
    }
  };

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="stock-ledger">
      <div className="page-header">
        <div>
          <h1>Inventory In / Out</h1>
          <p className="page-subtitle">Supplier-free inward and outward movement view</p>
        </div>
        <div className="btn-group">
          <button className="btn btn-secondary" onClick={() => window.print()}><Printer size={16} /> Print</button>
          <button className="btn btn-primary" onClick={() => setShowOutForm(!showOutForm)}><Plus size={16} /> Out Qty</button>
        </div>
      </div>

      <div className="filter-bar">
        <div className="filter-group">
          <label>Stock:</label>
          <select value={selectedGodown} onChange={e => setSelectedGodown(e.target.value)}>
            <option value="">All Stock</option>
            {godowns.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
          </select>
        </div>
        <div className="filter-group">
          <label>From:</label>
          <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />
        </div>
        <div className="filter-group">
          <label>To:</label>
          <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} />
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div><div className="stat-label">Total In Qty</div><div className="stat-value">{formatNumber(totalInQty, 2)}</div></div>
        </div>
        <div className="stat-card">
          <div><div className="stat-label">Total Out Qty</div><div className="stat-value">{formatNumber(totalOutQty, 2)}</div></div>
        </div>
        <div className="stat-card">
          <div><div className="stat-label">Alerts</div><div className="stat-value">{alertCount}</div></div>
        </div>
      </div>

      {showOutForm && (
        <div className="card">
          <div className="card-header">Manual Out Qty</div>
          <div className="card-content">
            <div className="form-row">
              <div className="form-group" style={{ maxWidth: '160px' }}>
                <label className="form-label">Date *</label>
                <input type="date" className="form-control" value={outForm.transaction_date}
                  onChange={e => setOutForm({ ...outForm, transaction_date: e.target.value })} />
              </div>
              <div className="form-group" style={{ maxWidth: '220px' }}>
                <label className="form-label">Stock *</label>
                <select className="form-control" value={outForm.godown_id}
                  onChange={e => setOutForm({ ...outForm, godown_id: e.target.value })}>
                  <option value="">Select Stock</option>
                  {godowns.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Item *</label>
                <select className="form-control" value={outForm.item_id}
                  onChange={e => handleOutItemChange(e.target.value)}>
                  <option value="">Select Item</option>
                  {items.map(i => <option key={i.id} value={i.id}>{i.code} - {i.name}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ maxWidth: '130px' }}>
                <label className="form-label">Out Qty *</label>
                <input type="number" className="form-control text-right" value={outForm.quantity}
                  onChange={e => setOutForm({ ...outForm, quantity: e.target.value })} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Remarks</label>
                <input type="text" className="form-control" value={outForm.remarks}
                  onChange={e => setOutForm({ ...outForm, remarks: e.target.value })} />
              </div>
              <div className="form-group" style={{ maxWidth: '150px', alignSelf: 'end' }}>
                <button className="btn btn-primary" onClick={saveOutQty} disabled={savingOut}>
                  <Save size={16} /> {savingOut ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <table className="data-grid">
          <thead>
            <tr>
              {showDate && <th>Date</th>}
              <th>Item Name</th>
              <th>Size</th>
              <th>Type</th>
              <th className="text-right">In Qty</th>
              <th className="text-right">Out Qty</th>
              <th>Alert</th>
            </tr>
          </thead>
          <tbody>
            {groupedMovements.map((movement, idx) => {
              const isAlert = Boolean(movement.is_low_stock);
              return (
                <tr key={`${movement.id}-${idx}`} className={isAlert ? 'low-stock-row' : ''}>
                  {showDate && <td>{formatDate(movement.date)}</td>}
                  <td><strong>{movement.item_name}</strong></td>
                  <td>{movement.size || '-'}</td>
                  <td>{movement.movement_type || '-'}</td>
                  <td className="numeric">{movement.in_qty ? formatNumber(movement.in_qty, 2) : '-'}</td>
                  <td className="numeric">{movement.out_qty ? formatNumber(movement.out_qty, 2) : '-'}</td>
                  <td>
                    {isAlert
                      ? <span className="badge badge-danger">Stock {formatNumber(movement.balance_qty, 2)}</span>
                      : <span className="badge badge-success">OK</span>
                    }
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {groupedMovements.length === 0 && <div className="empty-state"><p>No inventory movement found</p></div>}
      </div>
    </div>
  );
};

export default StockLedger;