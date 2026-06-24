import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Save, Plus, Trash2, Calculator } from 'lucide-react';
import api, { formatCurrency, getTodayDate } from '../../services/api';

const VoucherEntry = ({ currentBranch }) => {
  const { type = 'journal' } = useParams();
  const navigate = useNavigate();
  const [ledgers, setLedgers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [voucherDate, setVoucherDate] = useState(getTodayDate());
  const [narration, setNarration] = useState('');
  const [entries, setEntries] = useState([
    { id: 1, ledger_id: '', ledger_name: '', debit: 0, credit: 0 },
    { id: 2, ledger_id: '', ledger_name: '', debit: 0, credit: 0 }
  ]);
  const [activeRow, setActiveRow] = useState(0);
  const inputRefs = useRef([]);

  const voucherTypeLabels = {
    journal: 'Journal Entry', payment: 'Payment Voucher', receipt: 'Receipt Voucher', contra: 'Contra Voucher'
  };

  useEffect(() => { fetchLedgers(); }, [currentBranch]);

  const fetchLedgers = async () => {
    try {
      const branchParam = currentBranch?.id ? `?branch_id=${currentBranch.id}` : '';
      const response = await api.get(`/accounting/ledgers${branchParam}`);
      setLedgers(response.data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const totalDebit = entries.reduce((sum, e) => sum + (parseFloat(e.debit) || 0), 0);
  const totalCredit = entries.reduce((sum, e) => sum + (parseFloat(e.credit) || 0), 0);
  const difference = Math.abs(totalDebit - totalCredit);
  const isBalanced = difference < 0.01;

  const updateEntry = (index, field, value) => {
    const newEntries = [...entries];
    newEntries[index][field] = value;
    
    if (field === 'ledger_id') {
      const ledger = ledgers.find(l => l.id === value);
      newEntries[index].ledger_name = ledger?.name || '';
    }
    
    setEntries(newEntries);
  };

  const addRow = () => {
    setEntries([...entries, { id: Date.now(), ledger_id: '', ledger_name: '', debit: 0, credit: 0 }]);
  };

  const removeRow = (index) => {
    if (entries.length <= 2) return;
    setEntries(entries.filter((_, i) => i !== index));
  };

  const handleKeyDown = (e, rowIndex, field) => {
    if (e.key === 'Tab' && !e.shiftKey && field === 'credit' && rowIndex === entries.length - 1) {
      e.preventDefault();
      addRow();
      setTimeout(() => {
        const nextRef = inputRefs.current[`${rowIndex + 1}-ledger`];
        if (nextRef) nextRef.focus();
      }, 50);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (field === 'credit' && rowIndex < entries.length - 1) {
        const nextRef = inputRefs.current[`${rowIndex + 1}-ledger`];
        if (nextRef) nextRef.focus();
      }
    }
  };

  const handleSave = async () => {
    if (!currentBranch) { alert('Please select a branch'); return; }
    if (!isBalanced) { alert('Voucher must be balanced (Dr = Cr)'); return; }
    
    const validEntries = entries.filter(e => e.ledger_id && (e.debit > 0 || e.credit > 0));
    if (validEntries.length < 2) { alert('At least 2 entries required'); return; }

    setSaving(true);
    try {
      await api.post('/accounting/vouchers', {
        voucher_type: type, voucher_date: voucherDate, branch_id: currentBranch.id,
        entries: validEntries.map(e => ({ ledger_id: e.ledger_id, ledger_name: e.ledger_name, debit: parseFloat(e.debit) || 0, credit: parseFloat(e.credit) || 0 })),
        narration
      });
      alert('Voucher saved successfully');
      resetForm();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error saving voucher');
    } finally {
      setSaving(false);
    }
  };

  const resetForm = () => {
    setVoucherDate(getTodayDate());
    setNarration('');
    setEntries([
      { id: 1, ledger_id: '', ledger_name: '', debit: 0, credit: 0 },
      { id: 2, ledger_id: '', ledger_name: '', debit: 0, credit: 0 }
    ]);
  };

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="voucher-entry">
      <div className="page-header">
        <div>
          <h1>{voucherTypeLabels[type] || 'Voucher Entry'}</h1>
          <p className="page-subtitle">{currentBranch?.name || 'Select Branch'}</p>
        </div>
        <div className="btn-group">
          <button className="btn btn-secondary" onClick={resetForm}>Clear</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving || !isBalanced}>
            <Save size={16} /> {saving ? 'Saving...' : 'Save Voucher (Ctrl+S)'}
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-content">
          <div className="form-row">
            <div className="form-group" style={{maxWidth: '200px'}}>
              <label className="form-label">Voucher Date</label>
              <input type="date" className="form-control" value={voucherDate} onChange={e => setVoucherDate(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Narration</label>
              <input type="text" className="form-control" value={narration} onChange={e => setNarration(e.target.value)} placeholder="Enter narration" />
            </div>
          </div>

          <div style={{marginTop: '16px'}}>
            <table className="input-grid">
              <thead>
                <tr>
                  <th style={{width: '50px'}}>#</th>
                  <th style={{width: '40%'}}>Ledger Account</th>
                  <th style={{width: '25%'}} className="text-right">Debit (Dr)</th>
                  <th style={{width: '25%'}} className="text-right">Credit (Cr)</th>
                  <th style={{width: '50px'}}></th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry, index) => (
                  <tr key={entry.id} className={activeRow === index ? 'active' : ''} onClick={() => setActiveRow(index)}>
                    <td className="text-center">{index + 1}</td>
                    <td>
                      <select
                        ref={el => inputRefs.current[`${index}-ledger`] = el}
                        className="form-control"
                        value={entry.ledger_id}
                        onChange={e => updateEntry(index, 'ledger_id', e.target.value)}
                        onKeyDown={e => handleKeyDown(e, index, 'ledger')}
                      >
                        <option value="">-- Select Ledger --</option>
                        {ledgers.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
                      </select>
                    </td>
                    <td>
                      <input
                        type="number"
                        step="0.01"
                        className="form-control text-right"
                        value={entry.debit || ''}
                        onChange={e => updateEntry(index, 'debit', e.target.value)}
                        onKeyDown={e => handleKeyDown(e, index, 'debit')}
                        onFocus={e => e.target.select()}
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        step="0.01"
                        className="form-control text-right"
                        value={entry.credit || ''}
                        onChange={e => updateEntry(index, 'credit', e.target.value)}
                        onKeyDown={e => handleKeyDown(e, index, 'credit')}
                        onFocus={e => e.target.select()}
                      />
                    </td>
                    <td className="text-center">
                      <button className="btn btn-sm btn-danger" onClick={() => removeRow(index)} disabled={entries.length <= 2}>
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            
            <button className="btn btn-secondary btn-sm" onClick={addRow} style={{marginTop: '8px'}}>
              <Plus size={14} /> Add Row
            </button>
          </div>

          <div className="totals-panel" style={{maxWidth: '400px', marginLeft: 'auto'}}>
            <div className="totals-row">
              <span className="label">Total Debit</span>
              <span className="value debit">{formatCurrency(totalDebit)}</span>
            </div>
            <div className="totals-row">
              <span className="label">Total Credit</span>
              <span className="value credit">{formatCurrency(totalCredit)}</span>
            </div>
            <div className="totals-row highlight">
              <span className="label">Difference</span>
              <span className="value" style={{color: isBalanced ? 'var(--success)' : 'var(--danger)'}}>
                {formatCurrency(difference)} {isBalanced && '✓'}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="keyboard-hint" style={{marginTop: '12px', textAlign: 'center'}}>
        <span className="key">Tab</span> Next field &nbsp;|&nbsp;
        <span className="key">Enter</span> Next row &nbsp;|&nbsp;
        <span className="key">Tab</span> on last row adds new row
      </div>
    </div>
  );
};

export default VoucherEntry;
