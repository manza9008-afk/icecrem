import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2 } from 'lucide-react';
import api from '../../services/api';

const GodownMaster = ({ currentBranch }) => {
  const [godowns, setGodowns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingGodown, setEditingGodown] = useState(null);
  const [formData, setFormData] = useState({ code: '', name: '', address: '', is_default: false });

  useEffect(() => { fetchGodowns(); }, [currentBranch]);

  const fetchGodowns = async () => {
    try {
      const response = await api.get('/branches/godowns/all');
      setGodowns(currentBranch ? response.data.filter(g => g.branch_id === currentBranch.id) : response.data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!currentBranch) { alert('Please select a branch first'); return; }
    try {
      if (editingGodown) {
        await api.put(`/branches/godowns/${editingGodown.id}`, formData);
      } else {
        await api.post(`/branches/${currentBranch.id}/godowns`, formData);
      }
      fetchGodowns();
      closeModal();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error saving godown');
    }
  };

  const handleEdit = (godown) => {
    setEditingGodown(godown);
    setFormData({ code: godown.code, name: godown.name, address: godown.address || '', is_default: godown.is_default });
    setShowModal(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this godown?')) return;
    try {
      await api.delete(`/branches/godowns/${id}`);
      fetchGodowns();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error deleting godown');
    }
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingGodown(null);
    setFormData({ code: '', name: '', address: '', is_default: false });
  };

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="godown-master">
      <div className="page-header">
        <div>
          <h1>Godown Master</h1>
          <p className="page-subtitle">{currentBranch?.name || 'All Branches'}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)} disabled={!currentBranch}>
          <Plus size={16} /> Add Godown
        </button>
      </div>

      <div className="card">
        <table className="data-grid">
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Branch</th>
              <th>Address</th>
              <th>Default</th>
              <th className="text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {godowns.map(godown => (
              <tr key={godown.id}>
                <td><strong>{godown.code}</strong></td>
                <td>{godown.name}</td>
                <td>{godown.branch_name}</td>
                <td>{godown.address}</td>
                <td>{godown.is_default ? <span className="badge badge-info">Default</span> : '-'}</td>
                <td className="text-center">
                  <button className="btn btn-sm btn-secondary" onClick={() => handleEdit(godown)} style={{marginRight: '4px'}}><Edit2 size={14} /></button>
                  <button className="btn btn-sm btn-danger" onClick={() => handleDelete(godown.id)} disabled={godown.is_default}><Trash2 size={14} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="modal" style={{width: '500px'}}>
            <div className="modal-header">
              <h3>{editingGodown ? 'Edit Godown' : 'Add Godown'}</h3>
              <button className="modal-close" onClick={closeModal}>&times;</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Code *</label>
                    <input type="text" className="form-control" value={formData.code} onChange={e => setFormData({...formData, code: e.target.value})} required />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Name *</label>
                    <input type="text" className="form-control" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} required />
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Address</label>
                  <textarea className="form-control" rows="2" value={formData.address} onChange={e => setFormData({...formData, address: e.target.value})} />
                </div>
                <div className="form-group">
                  <label style={{display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer'}}>
                    <input type="checkbox" checked={formData.is_default} onChange={e => setFormData({...formData, is_default: e.target.checked})} />
                    <span>Default Godown</span>
                  </label>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={closeModal}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default GodownMaster;
