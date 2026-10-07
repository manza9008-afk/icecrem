import React, { useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, Printer, RefreshCw } from 'lucide-react';
import api, { formatDate, formatNumber, getItemSizeLabel } from '../../services/api';

const StockOutHistory = ({ currentBranch }) => {
  const [outwards, setOutwards] = useState([]);
  const [items, setItems] = useState([]);
  const [godowns, setGodowns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedGodown, setSelectedGodown] = useState('');
  const [selectedItem, setSelectedItem] = useState('');
  const [expandedKey, setExpandedKey] = useState(null);

  useEffect(() => {
    setSelectedGodown('');
    setSelectedItem('');
    fetchMasters();
  }, [currentBranch]);

  useEffect(() => {
    fetchOutwards();
  }, [currentBranch, selectedGodown, selectedItem, startDate, endDate]);

  const fetchMasters = async () => {
    try {
      const [itemsRes, godownsRes] = await Promise.all([
        api.get('/inventory/items'),
        currentBranch?.id ? api.get(`/branches/${currentBranch.id}/godowns`) : Promise.resolve({ data: [] })
      ]);
      setItems(itemsRes.data);
      setGodowns(godownsRes.data);
    } catch (error) {
      console.error(error);
      setItems([]);
      setGodowns([]);
    }
  };

  const fetchOutwards = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (currentBranch?.id) params.append('branch_id', currentBranch.id);
      if (selectedGodown) params.append('godown_id', selectedGodown);
      if (selectedItem) params.append('item_id', selectedItem);
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);

      const response = await api.get(`/inventory/stock/outwards?${params.toString()}`);
      setOutwards(response.data);
    } catch (error) {
      console.error(error);
      setOutwards([]);
    } finally {
      setLoading(false);
    }
  };

  const totalQty = useMemo(
    () => outwards.reduce((sum, outward) => sum + Number(outward.quantity || 0), 0),
    [outwards]
  );

  // Each saved product is its own outward row, so group rows by date + stock for the dropdown view
  const groups = useMemo(() => {
    const map = new Map();
    outwards.forEach(o => {
      const key = `${o.transaction_date}__${o.godown_id}`;
      if (!map.has(key)) {
        map.set(key, { key, transaction_date: o.transaction_date, godown_name: o.godown_name, rows: [], qty: 0 });
      }
      const group = map.get(key);
      group.rows.push(o);
      group.qty += Number(o.quantity || 0);
    });
    return [...map.values()];
  }, [outwards]);

  const itemsById = useMemo(() => new Map(items.map(i => [i.id, i])), [items]);

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="stock-out-history">
      <div className="page-header">
        <div>
          <h1>Inventory Out History</h1>
          <p className="page-subtitle">{currentBranch?.name || 'All Branches'}</p>
        </div>
        <div className="btn-group">
          <button className="btn btn-secondary" onClick={fetchOutwards}>
            <RefreshCw size={16} /> Refresh
          </button>
          <button className="btn btn-secondary" onClick={() => window.print()}>
            <Printer size={16} /> Print
          </button>
        </div>
      </div>

      <div className="filter-bar">
        <div className="filter-group">
          <label>Stock:</label>
          <select value={selectedGodown} onChange={e => setSelectedGodown(e.target.value)}>
            <option value="">All Stock</option>
            {godowns.map(godown => <option key={godown.id} value={godown.id}>{godown.name}</option>)}
          </select>
        </div>
        <div className="filter-group">
          <label>Item:</label>
          <select value={selectedItem} onChange={e => setSelectedItem(e.target.value)}>
            <option value="">All Items</option>
            {items.map(item => (
              <option key={item.id} value={item.id}>
                {item.code ? `${item.code} - ` : ''}{item.name}
              </option>
            ))}
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
          <div>
            <div className="stat-label">Entries</div>
            <div className="stat-value">{outwards.length}</div>
          </div>
        </div>
        <div className="stat-card">
          <div>
            <div className="stat-label">Total Out Qty</div>
            <div className="stat-value">{formatNumber(totalQty, 2)}</div>
          </div>
        </div>
      </div>

      <div className="card">
        <table className="data-grid">
          <thead>
            <tr>
              <th style={{ width: '32px' }}></th>
              <th>Date</th>
              <th>Stock</th>
              <th className="text-right">Items</th>
              <th className="text-right">Qty Out</th>
            </tr>
          </thead>
          <tbody>
            {groups.map(group => {
              const isOpen = expandedKey === group.key;
              return (
                <React.Fragment key={group.key}>
                  <tr onClick={() => setExpandedKey(isOpen ? null : group.key)} style={{ cursor: 'pointer' }} title="Click to see products">
                    <td>{isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</td>
                    <td><strong>{formatDate(group.transaction_date)}</strong></td>
                    <td>{group.godown_name || '-'}</td>
                    <td className="numeric">{group.rows.length}</td>
                    <td className="numeric">{formatNumber(group.qty, 2)}</td>
                  </tr>
                  {isOpen && (
                    <tr>
                      <td></td>
                      <td colSpan={4} style={{ padding: '8px 16px' }}>
                        <table className="data-grid">
                          <thead>
                            <tr>
                              <th>#</th>
                              <th>Out No.</th>
                              <th>Product Name</th>
                              <th>Size</th>
                              <th className="text-right">Qty Out</th>
                              <th>Remarks</th>
                              <th>Created By</th>
                            </tr>
                          </thead>
                          <tbody>
                            {group.rows.map((outward, idx) => {
                              const item = itemsById.get(outward.item_id);
                              return (
                                <tr key={outward.id}>
                                  <td>{idx + 1}</td>
                                  <td>{outward.outward_number}</td>
                                  <td>
                                    <strong>{outward.item_name}</strong>
                                    {outward.item_code && <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{outward.item_code}</div>}
                                  </td>
                                  <td>{outward.size || getItemSizeLabel(item) || '-'}</td>
                                  <td className="numeric">{formatNumber(outward.quantity, 2)}</td>
                                  <td style={{ maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis' }}>{outward.remarks || '-'}</td>
                                  <td>{outward.created_by || '-'}</td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
          {outwards.length > 0 && (
            <tfoot>
              <tr style={{ fontWeight: 600 }}>
                <td colSpan={3} className="text-right">Total</td>
                <td className="numeric">{outwards.length}</td>
                <td className="numeric">{formatNumber(totalQty, 2)}</td>
              </tr>
            </tfoot>
          )}
        </table>
        {outwards.length === 0 && <div className="empty-state"><p>No inventory out history found</p></div>}
      </div>
    </div>
  );
};

export default StockOutHistory;
