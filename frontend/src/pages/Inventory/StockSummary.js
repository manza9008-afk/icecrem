import React, { useState, useEffect } from 'react';
<<<<<<< HEAD
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
=======
import { Package } from 'lucide-react';
import api, { formatCurrency, formatNumber } from '../../services/api';

const StockSummary = ({ currentBranch }) => {
  const [stock, setStock] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchStock(); }, [currentBranch]);

  const fetchStock = async () => {
    try {
      const branchParam = currentBranch?.id ? `?branch_id=${currentBranch.id}` : '';
      const response = await api.get(`/inventory/stock${branchParam}`);
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68
      setStock(response.data);
    } catch (error) { console.error('Error:', error); }
    finally { setLoading(false); }
  };

<<<<<<< HEAD
  const totalInQty = stock.reduce((sum, item) => sum + (item.in_qty || 0), 0);
  const totalOutQty = stock.reduce((sum, item) => sum + (item.out_qty || 0), 0);
  const totalStockQty = stock.reduce((sum, item) => sum + (item.ready_qty || 0), 0);
  const alertCount = stock.filter(item => item.is_low_stock).length;
=======
  const totalValue = stock.reduce((sum, s) => sum + s.total_value, 0);
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="stock-summary">
<<<<<<< HEAD
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
=======
      <div className="page-header"><div><h1>Stock Summary</h1><p className="page-subtitle">{currentBranch?.name || 'All Branches'} | FIFO Valuation</p></div></div>
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68
      
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon" style={{background: '#e6fffa'}}><Package size={24} color="#38a169" /></div>
          <div><div className="stat-label">Total Items</div><div className="stat-value">{stock.length}</div></div>
        </div>
        <div className="stat-card">
<<<<<<< HEAD
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
=======
          <div className="stat-icon" style={{background: '#ebf8ff'}}><Package size={24} color="#3182ce" /></div>
          <div><div className="stat-label">Total Stock Value</div><div className="stat-value">{formatCurrency(totalValue)}</div></div>
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68
        </div>
      </div>

      <div className="card">
        <table className="data-grid">
<<<<<<< HEAD
          <thead><tr><th>Item Name</th><th className="text-right">In Qty</th><th className="text-right">Out Qty</th><th className="text-right">Stock Qty</th><th className="text-right">Alert Qty</th><th>Alert</th></tr></thead>
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
=======
          <thead><tr><th>Item Code</th><th>Item Name</th><th>Godown</th><th className="text-right">Qty</th><th className="text-right">Avg Cost</th><th className="text-right">Total Value</th><th className="text-right">Batches</th></tr></thead>
          <tbody>
            {stock.map((s, i) => (
              <tr key={i}>
                <td><strong>{s.item_code}</strong></td>
                <td>{s.item_name}</td>
                <td>{s.godown_name}</td>
                <td className="numeric">{formatNumber(s.total_quantity, 2)}</td>
                <td className="numeric">{formatCurrency(s.average_cost)}</td>
                <td className="numeric">{formatCurrency(s.total_value)}</td>
                <td className="numeric">{s.batch_count}</td>
              </tr>
            ))}
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68
          </tbody>
        </table>
        {stock.length === 0 && <div className="empty-state"><p>No stock found</p></div>}
      </div>
    </div>
  );
};

export default StockSummary;
