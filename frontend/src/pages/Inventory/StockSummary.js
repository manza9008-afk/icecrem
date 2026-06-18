import React, { useState, useEffect } from 'react';
import { AlertTriangle, Package, Printer } from 'lucide-react';
import api, { formatNumber } from '../../services/api';

const StockSummary = ({ currentBranch }) => {
  const [stock, setStock] = useState([]);
  const [godowns, setGodowns] = useState([]);
  const [selectedGodown, setSelectedGodown] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setSelectedGodown('');
    fetchGodowns();
  }, [currentBranch]);

  useEffect(() => { fetchStock(); }, [currentBranch, selectedGodown]);

  const fetchGodowns = async () => {
    if (!currentBranch?.id) {
      setGodowns([]);
      return;
    }
    try {
      const response = await api.get(`/branches/${currentBranch.id}/godowns`);
      setGodowns(response.data);
    } catch (error) {
      console.error('Error:', error);
      setGodowns([]);
    }
  };

  const fetchStock = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (currentBranch?.id) params.append('branch_id', currentBranch.id);
      if (selectedGodown) params.append('godown_id', selectedGodown);
      const query = params.toString() ? `?${params.toString()}` : '';
      const response = await api.get(`/inventory/ready-stock${query}`);
      setStock(response.data);
    } catch (error) { console.error('Error:', error); }
    finally { setLoading(false); }
  };

  const totalInQty = stock.reduce((sum, item) => sum + (item.in_qty || 0), 0);
  const totalOutQty = stock.reduce((sum, item) => sum + (item.out_qty || 0), 0);
  const totalStockQty = stock.reduce((sum, item) => sum + (item.ready_qty || 0), 0);
  const alertCount = stock.filter(item => item.is_low_stock).length;

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="stock-summary">
      <div className="page-header">
        <div><h1>Stock</h1><p className="page-subtitle">{currentBranch?.name || 'All Branches'} | Item-wise in and out quantity view</p></div>
        <button className="btn btn-secondary" onClick={() => window.print()}><Printer size={16} /> Print</button>
      </div>

      <div className="filter-bar">
        <div className="filter-group">
          <label>Stock:</label>
          <select value={selectedGodown} onChange={e => setSelectedGodown(e.target.value)}>
            <option value="">All Stock</option>
            {godowns.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
          </select>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon" style={{background: '#e6fffa'}}><Package size={24} color="#38a169" /></div>
          <div><div className="stat-label">Total Items</div><div className="stat-value">{stock.length}</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{background: '#fff7ed'}}><Package size={24} color="#ea580c" /></div>
          <div><div className="stat-label">In Qty</div><div className="stat-value">{formatNumber(totalInQty, 2)}</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{background: '#fef2f2'}}><Package size={24} color="#dc2626" /></div>
          <div><div className="stat-label">Out Qty</div><div className="stat-value">{formatNumber(totalOutQty, 2)}</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{background: '#eef2ff'}}><Package size={24} color="#4f46e5" /></div>
          <div><div className="stat-label">Stock Qty</div><div className="stat-value">{formatNumber(totalStockQty, 2)}</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{background: '#fff1f2'}}><Package size={24} color="#e11d48" /></div>
          <div><div className="stat-label">Low Stock Alerts</div><div className="stat-value">{alertCount}</div></div>
        </div>
      </div>

      <div className="card">
        <table className="data-grid">
          <thead>
            <tr>
              <th>Item Name</th>
              <th className="text-right">In Qty</th>
              <th className="text-right">Out Qty</th>
              <th className="text-right">Stock Qty</th>
              <th className="text-right">Alert Qty</th>
              <th>Alert</th>
            </tr>
          </thead>
          <tbody>
            {stock.map((s, i) => {
              const isAlert = Boolean(s.is_low_stock);
              const threshold = Number(s.low_stock_threshold || 0);
              return (
                <tr key={i} className={isAlert ? 'low-stock-row' : ''}>
                  <td><strong>{s.item_name}</strong></td>
                  <td className="numeric">{formatNumber(s.in_qty, 2)}</td>
                  <td className="numeric">{formatNumber(s.out_qty, 2)}</td>
                  <td className="numeric">{formatNumber(s.ready_qty, 2)}</td>
                  <td className="numeric">{threshold > 0 ? formatNumber(threshold, 2) : '-'}</td>
                  <td>
                    {isAlert ? (
                      <span className="badge badge-danger"><AlertTriangle size={11} /> Low {formatNumber(s.ready_qty, 2)}</span>
                    ) : (
                      <span className="badge badge-success">OK</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {stock.length === 0 && <div className="empty-state"><p>No stock found</p></div>}
      </div>
    </div>
  );
};

export default StockSummary;