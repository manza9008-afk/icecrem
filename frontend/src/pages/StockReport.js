import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Download } from 'lucide-react';
import { toast } from 'sonner';

const StockReport = () => {
  const [stock, setStock] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStock();
  }, []);

  const fetchStock = async () => {
    try {
      const response = await api.get('/reports/stock-summary');
      setStock(response.data);
    } catch (error) {
      toast.error('Failed to fetch stock report');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading-container"><div className="spinner" /></div>;
  }

  const totalStockValue = stock.reduce((sum, item) => sum + item.stock_value, 0);

  return (
    <div data-testid="stock-report-page">
      <div className="page-header">
        <div>
          <h1>Stock Report</h1>
          <p className="page-subtitle">Current inventory status</p>
        </div>
        <button className="btn btn-secondary">
          <Download size={18} />
          Export to Excel
        </button>
      </div>

      <div className="card" style={{ marginBottom: '16px' }}>
        <div className="card-content">
          <div className="stat-label">Total Stock Value</div>
          <div className="stat-value data-value">₹{totalStockValue.toFixed(2)}</div>
        </div>
      </div>

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>SKU</th>
                <th>Item Name</th>
                <th>Category</th>
                <th>Current Stock</th>
                <th>Unit</th>
                <th>Cost Price</th>
                <th>Stock Value</th>
              </tr>
            </thead>
            <tbody>
              {stock.map((item) => (
                <tr key={item.item_id} data-testid={`stock-row-${item.sku}`}>
                  <td className="data-value">{item.sku}</td>
                  <td>{item.item_name}</td>
                  <td>{item.category}</td>
                  <td className="data-value">{item.current_stock}</td>
                  <td>{item.unit}</td>
                  <td className="data-value">₹{item.cost_price.toFixed(2)}</td>
                  <td className="data-value">₹{item.stock_value.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default StockReport;
