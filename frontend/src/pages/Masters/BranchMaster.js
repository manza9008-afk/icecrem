import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Building2 } from 'lucide-react';
import api from '../../services/api';

const BranchMaster = () => {
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingBranch, setEditingBranch] = useState(null);
  const [formData, setFormData] = useState({
    code: '', name: '', address: '', city: '', state: 'Gujarat',
    state_code: '24', pincode: '', gstin: '', phone: '', email: '',
    is_head_office: false
  });

  useEffect(() => { fetchBranches(); }, []);

  const fetchBranches = async () => {
    try {
      const response = await api.get('/branches');
      setBranches(response.data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingBranch) {
        await api.put(`/branches/${editingBranch.id}`, formData);
      } else {
        await api.post('/branches', formData);
      }
      fetchBranches();
      closeModal();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error saving branch');
    }
  };

  const handleEdit = (branch) => {
    setEditingBranch(branch);
    setFormData(branch);
    setShowModal(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this branch?')) return;
    try {
      await api.delete(`/branches/${id}`);
      fetchBranches();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error deleting branch');
    }
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingBranch(null);
    setFormData({
      code: '', name: '', address: '', city: '', state: 'Gujarat',
      state_code: '24', pincode: '', gstin: '', phone: '', email: '',
      is_head_office: false
    });
  };

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="branch-master">
      <div className="page-header">
        <div>
          <h1>Branch Master</h1>
          <p className="page-subtitle">Manage company branches</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)} data-testid="add-branch-btn">
          <Plus size={16} /> Add Branch
        </button>
      </div>

      <div className="card">
        <table className="data-grid">
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>City</th>
              <th>State</th>
              <th>GSTIN</th>
              <th>Phone</th>
              <th>Type</th>
              <th className="text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {branches.map(branch => (
              <tr key={branch.id}>
                <td><strong>{branch.code}</strong></td>
                <td>{branch.name}</td>
                <td>{branch.city}</td>
                <td>{branch.state}</td>
                <td><code>{branch.gstin}</code></td>
                <td>{branch.phone}</td>
                <td>{branch.is_head_office ? <span className="badge badge-info">Head Office</span> : <span className="badge badge-success">Branch</span>}</td>
                <td className="text-center">
                  <button className="btn btn-sm btn-secondary" onClick={() => handleEdit(branch)} style={{marginRight: '4px'}}>
                    <Edit2 size={14} />
                  </button>
                  <button className="btn btn-sm btn-danger" onClick={() => handleDelete(branch.id)} disabled={branch.is_head_office}>
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="modal" style={{width: '600px'}}>
            <div className="modal-header">
              <h3>{editingBranch ? 'Edit Branch' : 'Add Branch'}</h3>
              <button className="modal-close" onClick={closeModal}>&times;</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Branch Code *</label>
                    <input type="text" className="form-control" value={formData.code} onChange={e => setFormData({...formData, code: e.target.value})} required />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Branch Name *</label>
                    <input type="text" className="form-control" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} required />
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Address *</label>
                  <textarea className="form-control" rows="2" value={formData.address} onChange={e => setFormData({...formData, address: e.target.value})} required />
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">City *</label>
                    <input type="text" className="form-control" value={formData.city} onChange={e => setFormData({...formData, city: e.target.value})} required />
                  </div>
                  <div className="form-group">
                    <label className="form-label">State *</label>
                    <input type="text" className="form-control" value={formData.state} onChange={e => setFormData({...formData, state: e.target.value})} required />
                  </div>
                  <div className="form-group">
                    <label className="form-label">State Code</label>
                    <input type="text" className="form-control" value={formData.state_code} onChange={e => setFormData({...formData, state_code: e.target.value})} maxLength={2} />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Pincode</label>
                    <input type="text" className="form-control" value={formData.pincode} onChange={e => setFormData({...formData, pincode: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">GSTIN</label>
                    <input type="text" className="form-control" value={formData.gstin} onChange={e => setFormData({...formData, gstin: e.target.value.toUpperCase()})} maxLength={15} />
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
                <div className="form-group">
                  <label style={{display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer'}}>
                    <input type="checkbox" checked={formData.is_head_office} onChange={e => setFormData({...formData, is_head_office: e.target.checked})} />
                    <span>Head Office</span>
                  </label>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={closeModal}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save Branch</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default BranchMaster;
