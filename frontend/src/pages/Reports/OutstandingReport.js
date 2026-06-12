import React, { useState, useEffect } from 'react';
import { RefreshCw, Download } from 'lucide-react';
import api, { formatCurrency, getTodayDate } from '../../services/api';

const OutstandingReport = ({ currentBranch }) => {
  const [activeTab, setActiveTab] = useState('receivables');
  const [receivablesData, setReceivablesData] = useState(null);
  const [payablesData, setPayablesData] = useState(null);
  const [agingData, setAgingData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [asOnDate, setAsOnDate] = useState(getTodayDate());

  useEffect(() => {
    fetchData();
  }, [currentBranch, asOnDate]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('as_on_date', asOnDate);
      if (currentBranch?.id) params.append('branch_id', currentBranch.id);
      
      const [recRes, payRes, agingRecRes, agingPayRes] = await Promise.all([
        api.get(`/reports/outstanding/receivables?${params.toString()}`),
        api.get(`/reports/outstanding/payables?${params.toString()}`),
        api.get(`/reports/aging/receivables?${params.toString()}`),
        api.get(`/reports/aging/payables?${params.toString()}`)
      ]);
      
      setReceivablesData(recRes.data);
      setPayablesData(payRes.data);
      setAgingData({
        receivables: agingRecRes.data,
        payables: agingPayRes.data
      });
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const ageBuckets = ['0-30', '31-60', '61-90', '91-120', '120+'];

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="outstanding-report">
      <div className="page-header">
        <div>
          <h1>Outstanding & Aging Report</h1>
          <p className="page-subtitle">Receivables and Payables Analysis</p>
        </div>
        <div className="btn-group">
          <input type="date" className="form-control" value={asOnDate}
            onChange={e => setAsOnDate(e.target.value)} style={{ width: '150px' }} />
          <button className="btn btn-primary" onClick={fetchData}>
            <RefreshCw size={16} /> Refresh
          </button>
        </div>
      </div>

      <div className="tabs-container">
        <div className="tabs">
          <button className={`tab ${activeTab === 'receivables' ? 'active' : ''}`}
            onClick={() => setActiveTab('receivables')}>
            Receivables ({formatCurrency(receivablesData?.total_outstanding || 0)})
          </button>
          <button className={`tab ${activeTab === 'payables' ? 'active' : ''}`}
            onClick={() => setActiveTab('payables')}>
            Payables ({formatCurrency(payablesData?.total_outstanding || 0)})
          </button>
          <button className={`tab ${activeTab === 'aging' ? 'active' : ''}`}
            onClick={() => setActiveTab('aging')}>
            Aging Analysis
          </button>
        </div>
      </div>

      {activeTab === 'receivables' && receivablesData && (
        <div className="card">
          <div className="card-header">
            Receivables Outstanding
            <span className="badge badge-success" style={{ marginLeft: '8px' }}>
              {receivablesData.total_parties} Parties | {formatCurrency(receivablesData.total_outstanding)}
            </span>
          </div>
          <div className="card-content">
            <table className="data-grid">
              <thead>
                <tr>
                  <th>Party Name</th>
                  <th>GSTIN</th>
                  <th>Phone</th>
                  <th className="text-right">Credit Limit</th>
                  <th className="text-right">Credit Days</th>
                  <th className="text-right">Outstanding</th>
                </tr>
              </thead>
              <tbody>
                {receivablesData.parties?.map((party, idx) => (
                  <tr key={party.party_id || idx}>
                    <td><strong>{party.party_name}</strong></td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>{party.gstin || '-'}</td>
                    <td>{party.phone || '-'}</td>
                    <td className="numeric">{formatCurrency(party.credit_limit)}</td>
                    <td className="numeric">{party.credit_days}</td>
                    <td className="numeric" style={{ fontWeight: 'bold', color: 'var(--success)' }}>
                      {formatCurrency(party.outstanding)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr style={{ fontWeight: 'bold', background: 'var(--bg-secondary)' }}>
                  <td colSpan={5}>TOTAL</td>
                  <td className="numeric">{formatCurrency(receivablesData.total_outstanding)}</td>
                </tr>
              </tfoot>
            </table>
            {receivablesData.parties?.length === 0 && (
              <div className="empty-state"><p>No outstanding receivables</p></div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'payables' && payablesData && (
        <div className="card">
          <div className="card-header">
            Payables Outstanding
            <span className="badge badge-danger" style={{ marginLeft: '8px' }}>
              {payablesData.total_parties} Parties | {formatCurrency(payablesData.total_outstanding)}
            </span>
          </div>
          <div className="card-content">
            <table className="data-grid">
              <thead>
                <tr>
                  <th>Party Name</th>
                  <th>GSTIN</th>
                  <th>Phone</th>
                  <th className="text-right">Credit Days</th>
                  <th className="text-right">Outstanding</th>
                </tr>
              </thead>
              <tbody>
                {payablesData.parties?.map((party, idx) => (
                  <tr key={party.party_id || idx}>
                    <td><strong>{party.party_name}</strong></td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>{party.gstin || '-'}</td>
                    <td>{party.phone || '-'}</td>
                    <td className="numeric">{party.credit_days}</td>
                    <td className="numeric" style={{ fontWeight: 'bold', color: 'var(--danger)' }}>
                      {formatCurrency(party.outstanding)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr style={{ fontWeight: 'bold', background: 'var(--bg-secondary)' }}>
                  <td colSpan={4}>TOTAL</td>
                  <td className="numeric">{formatCurrency(payablesData.total_outstanding)}</td>
                </tr>
              </tfoot>
            </table>
            {payablesData.parties?.length === 0 && (
              <div className="empty-state"><p>No outstanding payables</p></div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'aging' && agingData && (
        <>
          <div className="card">
            <div className="card-header">Receivables Aging Summary</div>
            <div className="card-content">
              <div className="grid-5" style={{ marginBottom: '16px' }}>
                {ageBuckets.map(bucket => (
                  <div key={bucket} className="mini-stat" style={{
                    borderLeft: bucket === '120+' ? '3px solid var(--danger)' : 
                                bucket === '91-120' ? '3px solid var(--warning)' : '3px solid var(--success)'
                  }}>
                    <span className="label">{bucket} Days</span>
                    <span className="value">{formatCurrency(agingData.receivables?.summary?.[bucket]?.amount || 0)}</span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      {agingData.receivables?.summary?.[bucket]?.count || 0} invoices
                    </span>
                  </div>
                ))}
              </div>
              
              <table className="data-grid">
                <thead>
                  <tr>
                    <th>Customer</th>
                    {ageBuckets.map(b => <th key={b} className="text-right">{b}</th>)}
                    <th className="text-right">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {agingData.receivables?.by_party?.slice(0, 20).map((party, idx) => (
                    <tr key={idx}>
                      <td><strong>{party.party_name}</strong></td>
                      {ageBuckets.map(b => (
                        <td key={b} className="numeric">{party[b] > 0 ? formatCurrency(party[b]) : '-'}</td>
                      ))}
                      <td className="numeric" style={{ fontWeight: 'bold' }}>{formatCurrency(party.total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card" style={{ marginTop: '16px' }}>
            <div className="card-header">Payables Aging Summary</div>
            <div className="card-content">
              <div className="grid-5" style={{ marginBottom: '16px' }}>
                {ageBuckets.map(bucket => (
                  <div key={bucket} className="mini-stat" style={{
                    borderLeft: bucket === '120+' ? '3px solid var(--danger)' : 
                                bucket === '91-120' ? '3px solid var(--warning)' : '3px solid var(--info)'
                  }}>
                    <span className="label">{bucket} Days</span>
                    <span className="value">{formatCurrency(agingData.payables?.summary?.[bucket]?.amount || 0)}</span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      {agingData.payables?.summary?.[bucket]?.count || 0} invoices
                    </span>
                  </div>
                ))}
              </div>
              
              <table className="data-grid">
                <thead>
                  <tr>
                    <th>Supplier</th>
                    {ageBuckets.map(b => <th key={b} className="text-right">{b}</th>)}
                    <th className="text-right">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {agingData.payables?.by_party?.slice(0, 20).map((party, idx) => (
                    <tr key={idx}>
                      <td><strong>{party.party_name}</strong></td>
                      {ageBuckets.map(b => (
                        <td key={b} className="numeric">{party[b] > 0 ? formatCurrency(party[b]) : '-'}</td>
                      ))}
                      <td className="numeric" style={{ fontWeight: 'bold' }}>{formatCurrency(party.total)}</td>
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

export default OutstandingReport;
