import React, { useState, useEffect } from 'react';
import { RefreshCw, Printer } from 'lucide-react';
import api, { formatCurrency, getTodayDate } from '../../services/api';

const RatioAnalysis = ({ currentBranch }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [financialYear, setFinancialYear] = useState('2025-26');

  useEffect(() => {
    fetchData();
  }, [currentBranch, financialYear]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('financial_year', financialYear);
      if (currentBranch?.id) params.append('branch_id', currentBranch.id);
      
      const response = await api.get(`/reports/ratio-analysis?${params.toString()}`);
      setData(response.data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const getRatioStatus = (value, benchmark, isHigherBetter = true) => {
    const numBenchmark = parseFloat(benchmark) || 1;
    if (isHigherBetter) {
      if (value >= numBenchmark) return 'good';
      if (value >= numBenchmark * 0.7) return 'warning';
      return 'poor';
    } else {
      if (value <= numBenchmark) return 'good';
      if (value <= numBenchmark * 1.3) return 'warning';
      return 'poor';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'good': return 'var(--success)';
      case 'warning': return 'var(--warning)';
      case 'poor': return 'var(--danger)';
      default: return 'var(--text-primary)';
    }
  };

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="ratio-analysis">
      <div className="page-header">
        <div>
          <h1>Financial Ratio Analysis</h1>
          <p className="page-subtitle">Key financial metrics and benchmarks</p>
        </div>
        <div className="btn-group">
          <select className="form-control" value={financialYear} onChange={e => setFinancialYear(e.target.value)} style={{ width: '120px' }}>
            <option value="2025-26">FY 2025-26</option>
            <option value="2024-25">FY 2024-25</option>
          </select>
          <button className="btn btn-primary" onClick={fetchData}>
            <RefreshCw size={16} /> Refresh
          </button>
        </div>
      </div>

      {data && (
        <>
          <div className="card">
            <div className="card-header">Key Figures</div>
            <div className="card-content">
              <div className="grid-4">
                <div className="mini-stat">
                  <span className="label">Current Assets</span>
                  <span className="value">{formatCurrency(data.key_figures?.current_assets)}</span>
                </div>
                <div className="mini-stat">
                  <span className="label">Current Liabilities</span>
                  <span className="value">{formatCurrency(data.key_figures?.current_liabilities)}</span>
                </div>
                <div className="mini-stat">
                  <span className="label">Fixed Assets</span>
                  <span className="value">{formatCurrency(data.key_figures?.fixed_assets)}</span>
                </div>
                <div className="mini-stat">
                  <span className="label">Total Assets</span>
                  <span className="value">{formatCurrency(data.key_figures?.total_assets)}</span>
                </div>
                <div className="mini-stat">
                  <span className="label">Inventory</span>
                  <span className="value">{formatCurrency(data.key_figures?.inventory)}</span>
                </div>
                <div className="mini-stat">
                  <span className="label">Receivables</span>
                  <span className="value">{formatCurrency(data.key_figures?.receivables)}</span>
                </div>
                <div className="mini-stat">
                  <span className="label">Payables</span>
                  <span className="value">{formatCurrency(data.key_figures?.payables)}</span>
                </div>
                <div className="mini-stat">
                  <span className="label">Cash & Bank</span>
                  <span className="value">{formatCurrency(data.key_figures?.cash_bank)}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="grid-2" style={{ marginTop: '16px', gap: '16px' }}>
            <div className="card">
              <div className="card-header">Liquidity Ratios</div>
              <div className="card-content">
                <table className="data-grid">
                  <thead>
                    <tr>
                      <th>Ratio</th>
                      <th className="text-right">Value</th>
                      <th className="text-right">Benchmark</th>
                      <th>Interpretation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(data.ratios?.liquidity || {}).map(([key, ratio]) => {
                      const status = getRatioStatus(ratio.value, ratio.benchmark);
                      return (
                        <tr key={key}>
                          <td><strong>{key.replace(/_/g, ' ').toUpperCase()}</strong></td>
                          <td className="numeric" style={{ color: getStatusColor(status), fontWeight: 'bold' }}>
                            {ratio.value?.toFixed(2)}
                          </td>
                          <td className="numeric">{ratio.benchmark}</td>
                          <td style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{ratio.interpretation}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="card">
              <div className="card-header">Leverage Ratios</div>
              <div className="card-content">
                <table className="data-grid">
                  <thead>
                    <tr>
                      <th>Ratio</th>
                      <th className="text-right">Value</th>
                      <th className="text-right">Benchmark</th>
                      <th>Interpretation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(data.ratios?.leverage || {}).map(([key, ratio]) => {
                      const status = getRatioStatus(ratio.value, parseFloat(ratio.benchmark?.replace('<', '')), false);
                      return (
                        <tr key={key}>
                          <td><strong>{key.replace(/_/g, ' ').toUpperCase()}</strong></td>
                          <td className="numeric" style={{ color: getStatusColor(status), fontWeight: 'bold' }}>
                            {ratio.value?.toFixed(2)}
                          </td>
                          <td className="numeric">{ratio.benchmark}</td>
                          <td style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{ratio.interpretation}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="card" style={{ marginTop: '16px' }}>
            <div className="card-header">Efficiency Ratios</div>
            <div className="card-content">
              <table className="data-grid">
                <thead>
                  <tr>
                    <th>Ratio</th>
                    <th className="text-right">Value</th>
                    <th>Unit</th>
                    <th>Interpretation</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.ratios?.efficiency || {}).map(([key, ratio]) => (
                    <tr key={key}>
                      <td><strong>{key.replace(/_/g, ' ').toUpperCase()}</strong></td>
                      <td className="numeric" style={{ fontWeight: 'bold' }}>
                        {typeof ratio.value === 'number' ? ratio.value.toFixed(2) : ratio.value}
                      </td>
                      <td>{ratio.unit}</td>
                      <td style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{ratio.interpretation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card" style={{ marginTop: '16px' }}>
            <div className="card-header">Profitability Ratios</div>
            <div className="card-content">
              <table className="data-grid">
                <thead>
                  <tr>
                    <th>Ratio</th>
                    <th className="text-right">Value</th>
                    <th>Unit</th>
                    <th>Interpretation</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.ratios?.profitability || {}).map(([key, ratio]) => (
                    <tr key={key}>
                      <td><strong>{key.replace(/_/g, ' ').toUpperCase()}</strong></td>
                      <td className="numeric" style={{ fontWeight: 'bold', color: ratio.value > 0 ? 'var(--success)' : 'var(--danger)' }}>
                        {typeof ratio.value === 'number' ? ratio.value.toFixed(2) : ratio.value}
                      </td>
                      <td>{ratio.unit}</td>
                      <td style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{ratio.interpretation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default RatioAnalysis;
