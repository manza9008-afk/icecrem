import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Search } from 'lucide-react';
import api from '../../services/api';

const LedgerMaster = ({ currentBranch }) => {
  const [ledgers, setLedgers] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingLedger, setEditingLedger] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterGroup, setFilterGroup] = useState('');
  const [formData, setFormData] = useState({
    name: '', code: '', account_group_id: '', opening_balance: 0, balance_type: 'debit',
    gstin: '', pan: '', address: '', city: '', state: '', state_code: '', pincode: '',
    phone: '', email: '', credit_limit: 0, credit_days: 0, is_party: false
  });

  useEffect(() => { fetchData(); }, [currentBranch]);

  const fetchData = async () => {
    try {
      const branchParam = currentBranch?.id ? `?branch_id=${currentBranch.id}` : '';
      const [ledgerRes, groupRes] = await Promise.all([
        api.get(`/accounting/ledgers${branchParam}`),
        api.get('/accounting/account-groups')
      ]);
      setLedgers(ledgerRes.data);
      setGroups(groupRes.data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!currentBranch) { alert('Please select a branch'); return; }
    try {
      const submitData = { ...formData, branch_id: currentBranch.id };
      if (editingLedger) {
        await api.put(`/accounting/ledgers/${editingLedger.id}`, submitData);
      } else {
        await api.post('/accounting/ledgers', submitData);
      }
      fetchData();
      closeModal();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error saving ledger');
    }
  };

  const handleEdit = (ledger) => {
    setEditingLedger(ledger);
    setFormData({
      name: ledger.name, code: ledger.code || '', account_group_id: ledger.account_group_id,
      opening_balance: ledger.opening_balance || 0, balance_type: ledger.balance_type || 'debit',
      gstin: ledger.gstin || '', pan: ledger.pan || '', address: ledger.address || '',
      city: ledger.city || '', state: ledger.state || '', state_code: ledger.state_code || '',
      pincode: ledger.pincode || '', phone: ledger.phone || '', email: ledger.email || '',
      credit_limit: ledger.credit_limit || 0, credit_days: ledger.credit_days || 0,
      is_party: ledger.is_party || false
    });
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingLedger(null);
    setFormData({
      name: '', code: '', account_group_id: '', opening_balance: 0, balance_type: 'debit',
      gstin: '', pan: '', address: '', city: '', state: '', state_code: '', pincode: '',
      phone: '', email: '', credit_limit: 0, credit_days: 0, is_party: false
    });
  };

  const filteredLedgers = ledgers.filter(l => {
    const matchSearch = !searchTerm || l.name.toLowerCase().includes(searchTerm.toLowerCase()) || l.code?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchGroup = !filterGroup || l.account_group_id === filterGroup;
    return matchSearch && matchGroup;
  });

  const partyGroups = groups.filter(g => ['A0103', 'L0101'].includes(g.code));

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="ledger-master">
      <div className="page-header">
        <div>
          <h1>Ledger Master</h1>
          <p className="page-subtitle">{currentBranch?.name || 'All Branches'}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)} disabled={!currentBranch}>
          <Plus size={16} /> Add Ledger
        </button>
      </div>

      <div className="filter-bar">
        <div className="filter-group">
          <Search size={14} />
          <input type="text" placeholder="Search ledgers..." value={searchTerm} onChange={e => setSearchTerm(e.target.value)} />
        </div>
        <div className="filter-group">
          <label>Group:</label>
          <select value={filterGroup} onChange={e => setFilterGroup(e.target.value)}>
            <option value="">All Groups</option>
            {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
          </select>
        </div>
      </div>

      <div className="card">
        <table className="data-grid">
          <thead>
            <tr>
              <th>Code</th>
              <th>Ledger Name</th>
              <th>Group</th>
              <th>Type</th>
              <th className="text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredLedgers.map(ledger => (
              <tr key={ledger.id}>
                <td><strong>{ledger.code}</strong></td>
                <td>{ledger.name} {ledger.is_party && <span className="badge badge-info" style={{marginLeft: '6px'}}>Party</span>}</td>
                <td>{ledger.group_name}</td>
                <td>{ledger.account_type}</td>
                <td className="text-center">
                  <button className="btn btn-sm btn-secondary" onClick={() => handleEdit(ledger)}><Edit2 size={14} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredLedgers.length === 0 && <div className="empty-state"><p>No ledgers found</p></div>}
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="modal" style={{width: '700px', maxHeight: '90vh', overflow: 'auto'}}>
            <div className="modal-header">
              <h3>{editingLedger ? 'Edit Ledger' : 'Add Ledger'}</h3>
              <button className="modal-close" onClick={closeModal}>&times;</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Ledger Name *</label>
                    <input type="text" className="form-control" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} required />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Code</label>
                    <input type="text" className="form-control" value={formData.code} onChange={e => setFormData({...formData, code: e.target.value.toUpperCase()})} />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Account Group *</label>
                    <select className="form-control" value={formData.account_group_id} onChange={e => setFormData({...formData, account_group_id: e.target.value})} required>
                      <option value="">Select Group</option>
                      {groups.map(g => <option key={g.id} value={g.id}>{g.code} - {g.name}</option>)}
                    </select>
                  </div>
                </div>
                <div className="form-group">
                  <label style={{display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer'}}>
                    <input type="checkbox" checked={formData.is_party} onChange={e => setFormData({...formData, is_party: e.target.checked})} />
                    <span>Is Party (Customer/Supplier)</span>
                  </label>
                </div>
                {formData.is_party && (
                  <>
                    <hr style={{margin: '16px 0', border: 'none', borderTop: '1px solid var(--border-color)'}} />
                    <h4 style={{marginBottom: '12px', fontSize: '12px', color: 'var(--text-secondary)'}}>PARTY DETAILS</h4>
                    <div className="form-row">
                      <div className="form-group">
                        <label className="form-label">GSTIN</label>
                        <input type="text" className="form-control" value={formData.gstin} onChange={e => setFormData({...formData, gstin: e.target.value.toUpperCase()})} maxLength={15} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">PAN</label>
                        <input type="text" className="form-control" value={formData.pan} onChange={e => setFormData({...formData, pan: e.target.value.toUpperCase()})} maxLength={10} />
                      </div>
                    </div>
                    <div className="form-group">
                      <label className="form-label">Address</label>
                      <textarea className="form-control" rows="2" value={formData.address} onChange={e => setFormData({...formData, address: e.target.value})} />
                    </div>
                    <div className="form-row">
                      <div className="form-group">
                        <label className="form-label">City</label>
                        <input type="text" className="form-control" value={formData.city} onChange={e => setFormData({...formData, city: e.target.value})} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">State</label>
                        <input type="text" className="form-control" value={formData.state} onChange={e => setFormData({...formData, state: e.target.value})} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">State Code</label>
                        <input type="text" className="form-control" value={formData.state_code} onChange={e => setFormData({...formData, state_code: e.target.value})} maxLength={2} />
                      </div>
                    </div>
                    <div className="form-row">
                      <div className="form-group">
                        <label className="form-label">Phone</label>
                        <input type="text" className="form-control" value={formData.phone} onChange={e => setFormData({...formData, phone: e.target.value})} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Email</label>
                        <input type="email" className="form-control" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} />
                      </div>
                    </div>
                    <div className="form-row">
                      <div className="form-group">
                        <label className="form-label">Credit Limit</label>
                        <input type="number" step="0.01" className="form-control" value={formData.credit_limit} onChange={e => setFormData({...formData, credit_limit: parseFloat(e.target.value) || 0})} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Credit Days</label>
                        <input type="number" className="form-control" value={formData.credit_days} onChange={e => setFormData({...formData, credit_days: parseInt(e.target.value) || 0})} />
                      </div>
                    </div>
                  </>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={closeModal}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save Ledger</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default LedgerMaster;