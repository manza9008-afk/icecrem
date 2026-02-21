import React, { useState, useEffect } from 'react';
import { Eye, Trash2, Search } from 'lucide-react';
import api, { formatCurrency, formatDate } from '../../services/api';

const VoucherList = ({ currentBranch }) => {
  const [vouchers, setVouchers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [voucherType, setVoucherType] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedVoucher, setSelectedVoucher] = useState(null);

  useEffect(() => { fetchVouchers(); }, [currentBranch, voucherType, startDate, endDate]);

  const fetchVouchers = async () => {
    try {
      let url = '/accounting/vouchers?';
      if (currentBranch?.id) url += `branch_id=${currentBranch.id}&`;
      if (voucherType) url += `voucher_type=${voucherType}&`;
      if (startDate) url += `start_date=${startDate}&`;
      if (endDate) url += `end_date=${endDate}&`;
      const response = await api.get(url);
      setVouchers(response.data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    const reason = window.prompt('Enter reason for deletion:');
    if (!reason) return;
    try {
      await api.delete(`/accounting/vouchers/${id}?reason=${encodeURIComponent(reason)}`);
      fetchVouchers();
      alert('Voucher reversed successfully');
    } catch (error) {
      alert(error.response?.data?.detail || 'Error');
    }
  };

  const voucherTypeLabels = {
    journal: 'Journal', payment: 'Payment', receipt: 'Receipt', contra: 'Contra',
    sales: 'Sales', purchase: 'Purchase', debit_note: 'Debit Note', credit_note: 'Credit Note'
  };

  const getStatusBadge = (status) => {
    const classes = { approved: 'badge-success', reversed: 'badge-danger', draft: 'badge-warning' };
    return <span className={`badge ${classes[status] || 'badge-secondary'}`}>{status.toUpperCase()}</span>;
  };

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="voucher-list">
      <div className="page-header">
        <div><h1>Voucher List</h1><p className="page-subtitle">{currentBranch?.name || 'All Branches'}</p></div>
      </div>

      <div className="filter-bar">
        <div className="filter-group">
          <label>Type:</label>
          <select value={voucherType} onChange={e => setVoucherType(e.target.value)}>
            <option value="">All Types</option>
            {Object.entries(voucherTypeLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
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

      <div className="card">
        <table className="data-grid">
          <thead>
            <tr>
              <th>Date</th>
              <th>Voucher No.</th>
              <th>Type</th>
              <th>Narration</th>
              <th className="text-right">Debit</th>
              <th className="text-right">Credit</th>
              <th>Status</th>
              <th className="text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {vouchers.map(v => (
              <tr key={v.id}>
                <td>{formatDate(v.voucher_date)}</td>
                <td><strong>{v.voucher_number}</strong></td>
                <td>{voucherTypeLabels[v.voucher_type] || v.voucher_type}</td>
                <td style={{maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis'}}>{v.narration}</td>
                <td className="numeric">{formatCurrency(v.total_debit)}</td>
                <td className="numeric">{formatCurrency(v.total_credit)}</td>
                <td>{getStatusBadge(v.status)}</td>
                <td className="text-center">
                  <button className="btn btn-sm btn-secondary" onClick={() => setSelectedVoucher(v)} style={{marginRight: '4px'}}><Eye size={14} /></button>
                  <button className="btn btn-sm btn-danger" onClick={() => handleDelete(v.id)} disabled={v.status === 'reversed'}><Trash2 size={14} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {vouchers.length === 0 && <div className="empty-state"><p>No vouchers found</p></div>}
      </div>

      {selectedVoucher && (
        <div className="modal-overlay">
          <div className="modal" style={{width: '600px'}}>
            <div className="modal-header">
              <h3>Voucher: {selectedVoucher.voucher_number}</h3>
              <button className="modal-close" onClick={() => setSelectedVoucher(null)}>&times;</button>
            </div>
            <div className="modal-body">
              <div className="form-row">
                <div><strong>Date:</strong> {formatDate(selectedVoucher.voucher_date)}</div>
                <div><strong>Type:</strong> {voucherTypeLabels[selectedVoucher.voucher_type]}</div>
                <div><strong>Status:</strong> {getStatusBadge(selectedVoucher.status)}</div>
              </div>
              <p style={{marginTop: '12px'}}><strong>Narration:</strong> {selectedVoucher.narration}</p>
              <table className="data-grid" style={{marginTop: '16px'}}>
                <thead><tr><th>Account</th><th className="text-right">Debit</th><th className="text-right">Credit</th></tr></thead>
                <tbody>
                  {selectedVoucher.entries?.map((e, i) => (
                    <tr key={i}><td>{e.ledger_name}</td><td className="numeric">{formatCurrency(e.debit)}</td><td className="numeric">{formatCurrency(e.credit)}</td></tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr style={{fontWeight: 'bold', background: 'var(--bg-secondary)'}}>
                    <td>Total</td><td className="numeric">{formatCurrency(selectedVoucher.total_debit)}</td><td className="numeric">{formatCurrency(selectedVoucher.total_credit)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
            <div className="modal-footer"><button className="btn btn-secondary" onClick={() => setSelectedVoucher(null)}>Close</button></div>
          </div>
        </div>
      )}
    </div>
  );
};

export default VoucherList;
