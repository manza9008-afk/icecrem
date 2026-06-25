import React, { useEffect, useState, useRef } from 'react';
import { Plus, Printer, Save, Trash2 } from 'lucide-react';
import api, { formatDate, formatNumber, getItemSizeLabel, getTodayDate } from '../../services/api';

const ItemSearchInput = ({ items, value, onChange, onEnter, inputId, disabled }) => {
  const [search, setSearch] = useState('');
  const [open, setOpen] = useState(false);
  const [highlighted, setHighlighted] = useState(0);
  const wrapperRef = useRef(null);

  const selectedItem = items.find(i => i.id === value);

  const filtered = search
    ? items.filter(i =>
        i.name.toLowerCase().includes(search.toLowerCase()) ||
        String(i.code).toLowerCase().includes(search.toLowerCase())
      )
    : items;

  useEffect(() => { setHighlighted(0); }, [search]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false);
        setSearch('');
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectItem = (item) => {
    onChange(item.id);
    setSearch('');
    setOpen(false);
    onEnter && onEnter();
  };

  const handleKeyDown = (e) => {
    if (disabled) return;
    if (!open) {
      if (e.key === 'Enter' || e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); }
      return;
    }
    if (e.key === 'ArrowDown') { e.preventDefault(); setHighlighted(h => Math.min(h + 1, filtered.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setHighlighted(h => Math.max(h - 1, 0)); }
    else if (e.key === 'Enter') { e.preventDefault(); if (filtered[highlighted]) selectItem(filtered[highlighted]); }
    else if (e.key === 'Escape') { setOpen(false); setSearch(''); }
  };

  return (
    <div ref={wrapperRef} style={{ position: 'relative', minWidth: '200px' }}>
      <input
        id={inputId}
        type="text"
        className="form-control"
        placeholder={disabled ? 'Select stock first' : (selectedItem ? `${selectedItem.code} - ${selectedItem.name}` : 'Search item...')}
        value={open ? search : (selectedItem ? `${selectedItem.code} - ${selectedItem.name}` : '')}
        onChange={e => { setSearch(e.target.value); setOpen(true); }}
        onFocus={() => { if (!disabled) { setOpen(true); setSearch(''); } }}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        autoComplete="off"
      />
      {open && !disabled && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, right: 0,
          background: '#fff', border: '1px solid #ccc', borderRadius: '4px',
          zIndex: 1000, maxHeight: '220px', overflowY: 'auto', boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
        }}>
          {filtered.length === 0 ? (
            <div style={{ padding: '8px 12px', color: '#999' }}>No items found</div>
          ) : (
            filtered.map((i, idx) => (
              <div key={i.id} onMouseDown={() => selectItem(i)} style={{
                padding: '8px 12px', cursor: 'pointer',
                background: idx === highlighted ? '#e8f0fe' : '#fff',
                fontWeight: idx === highlighted ? '600' : 'normal',
                borderBottom: '1px solid #f0f0f0'
              }}>
                <span style={{ color: '#666', marginRight: '8px', fontSize: '13px' }}>{i.code}</span>
                {i.name}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

const StockOutEntry = ({ currentBranch }) => {
  const [items, setItems] = useState([]);
  const [stockItemsByGodown, setStockItemsByGodown] = useState({});
  const [godowns, setGodowns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedEntry, setSavedEntry] = useState(null);
  const [formData, setFormData] = useState({ transaction_date: getTodayDate(), remarks: '' });
  const [lineItems, setLineItems] = useState([
    { id: 1, item_id: '', item_name: '', size: '', godown_id: '', available_qty: 0, quantity: 1 }
  ]);

  useEffect(() => { fetchData(); }, [currentBranch]);

  const fetchData = async () => {
    try {
      const [itemsRes, godownsRes] = await Promise.all([
        api.get('/inventory/items'),
        currentBranch?.id ? api.get(`/branches/${currentBranch.id}/godowns`) : Promise.resolve({ data: [] })
      ]);
      setItems(itemsRes.data);
      setGodowns(godownsRes.data);
      const defaultGodownId = godownsRes.data[0]?.id || '';
      setLineItems([{ id: 1, item_id: '', item_name: '', size: '', godown_id: defaultGodownId, available_qty: 0, quantity: 1 }]);
      if (defaultGodownId) fetchStockItems(defaultGodownId);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStockItems = async (godownId) => {
    if (!currentBranch?.id || !godownId || stockItemsByGodown[godownId]) return;
    try {
      const response = await api.get(`/inventory/ready-stock?branch_id=${currentBranch.id}&godown_id=${godownId}`);
      setStockItemsByGodown(prev => ({ ...prev, [godownId]: response.data }));
    } catch (error) {
      setStockItemsByGodown(prev => ({ ...prev, [godownId]: [] }));
    }
  };

  const focusField = (id, delay = 50) => {
    setTimeout(() => {
      const el = document.getElementById(id);
      if (el) { el.focus(); if (el.select) el.select(); }
    }, delay);
  };

  const handleStockChange = (index, godownId) => {
    fetchStockItems(godownId);
    const newItems = [...lineItems];
    newItems[index] = { ...newItems[index], godown_id: godownId, item_id: '', item_name: '', size: '', available_qty: 0, quantity: 1 };
    setLineItems(newItems);
    focusField(`item-${index}`);
  };

  const handleStockKeyDown = (e, index) => {
    if (e.key === 'Enter') { e.preventDefault(); focusField(`item-${index}`); }
  };

  const handleItemChange = (index, itemId) => {
    const item = items.find(i => i.id === itemId);
    const stockItem = (stockItemsByGodown[lineItems[index].godown_id] || []).find(i => i.item_id === itemId);
    const newItems = [...lineItems];
    newItems[index] = {
      ...newItems[index],
      item_id: itemId,
      item_name: item?.name || stockItem?.item_name || '',
      size: getItemSizeLabel(item) || stockItem?.size || '',
      available_qty: stockItem?.ready_qty || 0,
      quantity: newItems[index].quantity
    };
    setLineItems(newItems);
  };

  const handleQtyKeyDown = (e, index) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (index === lineItems.length - 1) {
        addLineItem();
        focusField(`godown-${index + 1}`, 100);
      } else {
        focusField(`godown-${index + 1}`);
      }
    }
  };

  const updateLineItem = (index, field, value) => {
    const newItems = [...lineItems];
    newItems[index][field] = value;
    setLineItems(newItems);
  };

  const addLineItem = () => {
    setLineItems([...lineItems, { id: Date.now(), item_id: '', item_name: '', size: '', godown_id: godowns[0]?.id || '', available_qty: 0, quantity: 1 }]);
    if (godowns[0]?.id) fetchStockItems(godowns[0].id);
  };

  const removeLineItem = (index) => {
    if (lineItems.length <= 1) return;
    setLineItems(lineItems.filter((_, i) => i !== index));
  };

  const resetForm = () => {
    setFormData({ transaction_date: getTodayDate(), remarks: '' });
    setLineItems([{ id: 1, item_id: '', item_name: '', size: '', godown_id: godowns[0]?.id || '', available_qty: 0, quantity: 1 }]);
    setSavedEntry(null);
  };

  const handleSave = async () => {
    if (!currentBranch?.id) { alert('Select a branch'); return; }
    const validItems = lineItems.filter(i => i.item_id && i.godown_id && Number(i.quantity || 0) > 0);
    if (validItems.length === 0) { alert('Add at least one item'); return; }

    setSaving(true);
    try {
      const savedItems = [];
      for (const item of validItems) {
        const response = await api.post('/inventory/stock/outward', {
          branch_id: currentBranch.id,
          godown_id: item.godown_id,
          item_id: item.item_id,
          quantity: Number(item.quantity),
          transaction_date: formData.transaction_date,
          remarks: formData.remarks
        });
        savedItems.push({ ...item, outward_number: response.data.outward_number, stock_name: godowns.find(g => g.id === item.godown_id)?.name || '' });
      }
      setSavedEntry({ entry_number: savedItems[0]?.outward_number || '', transaction_date: formData.transaction_date, remarks: formData.remarks, items: savedItems });
      setStockItemsByGodown({});
      alert('Inventory out entry saved!');
    } catch (error) {
      alert(error.response?.data?.detail || 'Error saving Inventory Out');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="stock-out-entry">
      <div className="page-header">
        <div>
          <h1>Inventory Out Entry</h1>
          <p className="page-subtitle">{currentBranch?.name}</p>
        </div>
        <div className="btn-group">
          <button className="btn btn-secondary" onClick={resetForm}>Clear</button>
          {savedEntry && <button className="btn btn-secondary" onClick={() => window.print()}><Printer size={16} /> Print</button>}
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            <Save size={16} /> {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-header">Outward Details</div>
        <div className="card-content">
          <div className="form-row">
            <div className="form-group" style={{ maxWidth: '180px' }}>
              <label className="form-label">Entry Date *</label>
              <input type="date" className="form-control" value={formData.transaction_date}
                onChange={e => setFormData({ ...formData, transaction_date: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">Remarks</label>
              <input type="text" className="form-control" value={formData.remarks}
                onChange={e => setFormData({ ...formData, remarks: e.target.value })} />
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">Inventory Out Items</div>
        <div className="card-content">
          <table className="input-grid">
            <thead>
              <tr>
                <th>#</th>
                <th>Stock</th>
                <th>Item Name</th>
                <th>Size</th>
                <th className="text-right">Available</th>
                <th className="text-right">Qty Out</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {lineItems.map((item, index) => (
                <tr key={item.id}>
                  <td className="text-center">{index + 1}</td>
                  <td>
                    <select id={`godown-${index}`} className="form-control" value={item.godown_id}
                      onChange={e => handleStockChange(index, e.target.value)}
                      onKeyDown={e => handleStockKeyDown(e, index)}
                      style={{ width: '130px' }}>
                      <option value="">Select</option>
                      {godowns.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
                    </select>
                  </td>
                  <td>
                    <ItemSearchInput
                      items={items}
                      value={item.item_id}
                      inputId={`item-${index}`}
                      disabled={!item.godown_id}
                      onChange={(itemId) => handleItemChange(index, itemId)}
                      onEnter={() => focusField(`qty-${index}`)}
                    />
                  </td>
                  <td>{item.size || '-'}</td>
                  <td className="numeric">{formatNumber(item.available_qty, 2)}</td>
                  <td>
                    <input id={`qty-${index}`} type="number" className="form-control text-right"
                      value={item.quantity}
                      onChange={e => updateLineItem(index, 'quantity', e.target.value)}
                      onKeyDown={e => handleQtyKeyDown(e, index)}
                      style={{ width: '90px' }} />
                  </td>
                  <td>
                    <button className="btn btn-sm btn-danger" onClick={() => removeLineItem(index)} disabled={lineItems.length <= 1}><Trash2 size={14} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <button className="btn btn-secondary btn-sm" onClick={addLineItem} style={{ marginTop: '8px' }}><Plus size={14} /> Add Item</button>
        </div>
      </div>

      {savedEntry && (
        <div className="card">
          <div className="card-header">Printable Entry</div>
          <div className="card-content">
            <div className="form-row">
              <div><strong>Entry No.:</strong> {savedEntry.entry_number}</div>
              <div><strong>Date:</strong> {formatDate(savedEntry.transaction_date)}</div>
            </div>
            {savedEntry.remarks && <p><strong>Remarks:</strong> {savedEntry.remarks}</p>}
            <table className="data-grid">
              <thead>
                <tr><th>Item</th><th>Size</th><th>Stock</th><th className="text-right">Qty Out</th></tr>
              </thead>
              <tbody>
                {savedEntry.items.map((item, index) => (
                  <tr key={`${item.outward_number}-${index}`}>
                    <td><strong>{item.item_name}</strong></td>
                    <td>{item.size || '-'}</td>
                    <td>{item.stock_name}</td>
                    <td className="numeric">{formatNumber(item.quantity, 2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default StockOutEntry;
