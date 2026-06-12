<<<<<<< HEAD
import React, { useEffect, useState } from 'react';
import { Plus, Printer, Save } from 'lucide-react';
import api, { formatDate, formatNumber, getTodayDate, getItemSizeLabel } from '../../services/api';

const StockLedger = ({ currentBranch }) => {
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

  const totalInQty = movements.reduce((sum, item) => sum + (item.in_qty || 0), 0);
  const totalOutQty = movements.reduce((sum, item) => sum + (item.out_qty || 0), 0);
  const alertCount = movements.filter(item => item.is_low_stock).length;

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
          <div><div className="stat-label">Rows</div><div className="stat-value">{movements.length}</div></div>
        </div>
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
                <input type="date" className="form-control" value={outForm.transaction_date} onChange={e => setOutForm({ ...outForm, transaction_date: e.target.value })} />
              </div>
              <div className="form-group" style={{ maxWidth: '220px' }}>
                <label className="form-label">Stock *</label>
                <select className="form-control" value={outForm.godown_id} onChange={e => setOutForm({ ...outForm, godown_id: e.target.value })}>
                  <option value="">Select Stock</option>
                  {godowns.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Item *</label>
                <select className="form-control" value={outForm.item_id} onChange={e => handleOutItemChange(e.target.value)}>
                  <option value="">Select Item</option>
                  {items.map(i => <option key={i.id} value={i.id}>{i.code} - {i.name}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ maxWidth: '130px' }}>
                <label className="form-label">Out Qty *</label>
                <input type="number" className="form-control text-right" value={outForm.quantity} onChange={e => setOutForm({ ...outForm, quantity: e.target.value })} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Remarks</label>
                <input type="text" className="form-control" value={outForm.remarks} onChange={e => setOutForm({ ...outForm, remarks: e.target.value })} />
              </div>
              <div className="form-group" style={{ maxWidth: '150px', alignSelf: 'end' }}>
                <button className="btn btn-primary" onClick={saveOutQty} disabled={savingOut}><Save size={16} /> {savingOut ? 'Saving...' : 'Save'}</button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <table className="data-grid">
          <thead>
            <tr>
              <th>Date</th>
              <th>Item Name</th>
              <th>Size</th>
              <th>Type</th>
              <th className="text-right">In Qty</th>
              <th className="text-right">Out Qty</th>
              <th>Alert</th>
            </tr>
          </thead>
          <tbody>
            {movements.map((movement) => {
              const isAlert = Boolean(movement.is_low_stock);
              return (
                <tr key={movement.id} className={isAlert ? 'low-stock-row' : ''}>
                  <td>{formatDate(movement.date)}</td>
                  <td><strong>{movement.item_name}</strong></td>
                  <td>{movement.size || '-'}</td>
                  <td>{movement.movement_type || '-'}</td>
                  <td className="numeric">{movement.in_qty ? formatNumber(movement.in_qty, 2) : '-'}</td>
                  <td className="numeric">{movement.out_qty ? formatNumber(movement.out_qty, 2) : '-'}</td>
                  <td>{isAlert ? <span className="badge badge-danger">Stock {formatNumber(movement.balance_qty, 2)}</span> : <span className="badge badge-success">OK</span>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {movements.length === 0 && <div className="empty-state"><p>No inventory movement found</p></div>}
      </div>
=======
import React, { useState, useEffect } from 'react';
import api, { formatCurrency, formatNumber, formatDate } from '../../services/api';

const StockLedger = ({ currentBranch }) => {
  const [items, setItems] = useState([]);
  const [selectedItem, setSelectedItem] = useState('');
  const [ledger, setLedger] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { fetchItems(); }, []);

  const fetchItems = async () => {
    try { const res = await api.get('/inventory/items'); setItems(res.data); } 
    catch (e) { console.error(e); }
  };

  const fetchLedger = async () => {
    if (!selectedItem) return;
    setLoading(true);
    try {
      const branchParam = currentBranch?.id ? `&branch_id=${currentBranch.id}` : '';
      const res = await api.get(`/inventory/stock/ledger/${selectedItem}?${branchParam}`);
      setLedger(res.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  return (
    <div data-testid="stock-ledger">
      <div className="page-header"><div><h1>Stock Ledger</h1><p className="page-subtitle">Item-wise stock movements</p></div></div>
      
      <div className="filter-bar">
        <div className="filter-group">
          <label>Select Item:</label>
          <select value={selectedItem} onChange={e => setSelectedItem(e.target.value)} style={{minWidth: '250px'}}>
            <option value="">-- Select Item --</option>
            {items.map(i => <option key={i.id} value={i.id}>{i.code} - {i.name}</option>)}
          </select>
        </div>
        <button className="btn btn-primary" onClick={fetchLedger} disabled={!selectedItem || loading}>
          {loading ? 'Loading...' : 'View Ledger'}
        </button>
      </div>

      {ledger && (
        <div className="card">
          <div className="card-header">{ledger.item_code} - {ledger.item_name}</div>
          <div className="card-content">
            <div className="form-row" style={{marginBottom: '16px'}}>
              <div><strong>Opening:</strong> {formatNumber(ledger.opening_qty)} units ({formatCurrency(ledger.opening_value)})</div>
              <div><strong>Closing:</strong> {formatNumber(ledger.closing_qty)} units ({formatCurrency(ledger.closing_value)})</div>
              <div><strong>Avg Cost:</strong> {formatCurrency(ledger.average_cost)}</div>
            </div>
            <table className="data-grid">
              <thead><tr><th>Date</th><th>Voucher</th><th>Type</th><th>Batch</th><th className="text-right">In Qty</th><th className="text-right">Out Qty</th><th className="text-right">Rate</th><th className="text-right">Balance</th></tr></thead>
              <tbody>
                {ledger.transactions.map((t, i) => (
                  <tr key={i}>
                    <td>{formatDate(t.date)}</td>
                    <td>{t.voucher_number}</td>
                    <td>{t.voucher_type}</td>
                    <td>{t.batch_number}</td>
                    <td className="numeric" style={{color: t.in_qty > 0 ? 'var(--success)' : ''}}>{t.in_qty > 0 ? formatNumber(t.in_qty) : '-'}</td>
                    <td className="numeric" style={{color: t.out_qty > 0 ? 'var(--danger)' : ''}}>{t.out_qty > 0 ? formatNumber(t.out_qty) : '-'}</td>
                    <td className="numeric">{formatCurrency(t.rate)}</td>
                    <td className="numeric">{formatNumber(t.balance_qty)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {ledger.transactions.length === 0 && <div className="empty-state"><p>No transactions found</p></div>}
          </div>
        </div>
      )}
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68
    </div>
  );
};

export default StockLedger;
