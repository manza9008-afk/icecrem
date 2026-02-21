import React, { useState, useEffect } from 'react';
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
      setStock(response.data);
    } catch (error) { console.error('Error:', error); }
    finally { setLoading(false); }
  };

  const totalValue = stock.reduce((sum, s) => sum + s.total_value, 0);

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="stock-summary">
      <div className="page-header"><div><h1>Stock Summary</h1><p className="page-subtitle">{currentBranch?.name || 'All Branches'} | FIFO Valuation</p></div></div>
      
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon" style={{background: '#e6fffa'}}><Package size={24} color="#38a169" /></div>
          <div><div className="stat-label">Total Items</div><div className="stat-value">{stock.length}</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{background: '#ebf8ff'}}><Package size={24} color="#3182ce" /></div>
          <div><div className="stat-label">Total Stock Value</div><div className="stat-value">{formatCurrency(totalValue)}</div></div>
        </div>
      </div>

      <div className="card">
        <table className="data-grid">
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
          </tbody>
        </table>
        {stock.length === 0 && <div className="empty-state"><p>No stock found</p></div>}
      </div>
    </div>
  );
};

export default StockSummary;
