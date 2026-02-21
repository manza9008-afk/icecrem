import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Search } from 'lucide-react';
import api from '../../services/api';

const CustomerMaster = () => {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [formData, setFormData] = useState({ name: '', gstin: '', pan: '', address: '', city: '', state: 'Gujarat', state_code: '24', pincode: '', phone: '', email: '', credit_limit: 0, credit_days: 0 });

  useEffect(() => { fetchCustomers(); }, []);

  const fetchCustomers = async () => {
    try { const response = await api.get('/customers'); setCustomers(response.data); } 
    catch (error) { console.error('Error:', error); } 
    finally { setLoading(false); }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingCustomer) { await api.put(`/customers/${editingCustomer.id}`, formData); } 
      else { await api.post('/customers', formData); }
      fetchCustomers(); closeModal();
    } catch (error) { alert(error.response?.data?.detail || 'Error'); }
  };

  const handleEdit = (c) => { setEditingCustomer(c); setFormData({...c}); setShowModal(true); };
  const closeModal = () => { setShowModal(false); setEditingCustomer(null); setFormData({ name: '', gstin: '', pan: '', address: '', city: '', state: 'Gujarat', state_code: '24', pincode: '', phone: '', email: '', credit_limit: 0, credit_days: 0 }); };

  const filtered = customers.filter(c => !searchTerm || c.name.toLowerCase().includes(searchTerm.toLowerCase()) || c.gstin?.includes(searchTerm.toUpperCase()));

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="customer-master">
      <div className="page-header"><div><h1>Customer Master</h1></div><button className="btn btn-primary" onClick={() => setShowModal(true)}><Plus size={16} /> Add Customer</button></div>
      <div className="filter-bar"><div className="filter-group"><Search size={14} /><input type="text" placeholder="Search..." value={searchTerm} onChange={e => setSearchTerm(e.target.value)} /></div></div>
      <div className="card">
        <table className="data-grid">
          <thead><tr><th>Name</th><th>GSTIN</th><th>City</th><th>Phone</th><th className="text-center">Actions</th></tr></thead>
          <tbody>{filtered.map(c => (<tr key={c.id}><td><strong>{c.name}</strong></td><td>{c.gstin}</td><td>{c.city}</td><td>{c.phone}</td><td className="text-center"><button className="btn btn-sm btn-secondary" onClick={() => handleEdit(c)}><Edit2 size={14} /></button></td></tr>))}</tbody>
        </table>
      </div>
      {showModal && (
        <div className="modal-overlay"><div className="modal" style={{width: '600px'}}>
          <div className="modal-header"><h3>{editingCustomer ? 'Edit' : 'Add'} Customer</h3><button className="modal-close" onClick={closeModal}>&times;</button></div>
          <form onSubmit={handleSubmit}><div className="modal-body">
            <div className="form-group"><label className="form-label">Name *</label><input type="text" className="form-control" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} required /></div>
            <div className="form-row"><div className="form-group"><label className="form-label">GSTIN</label><input type="text" className="form-control" value={formData.gstin} onChange={e => setFormData({...formData, gstin: e.target.value.toUpperCase()})} maxLength={15} /></div><div className="form-group"><label className="form-label">PAN</label><input type="text" className="form-control" value={formData.pan} onChange={e => setFormData({...formData, pan: e.target.value.toUpperCase()})} maxLength={10} /></div></div>
            <div className="form-group"><label className="form-label">Address</label><textarea className="form-control" rows="2" value={formData.address} onChange={e => setFormData({...formData, address: e.target.value})} /></div>
            <div className="form-row"><div className="form-group"><label className="form-label">City</label><input type="text" className="form-control" value={formData.city} onChange={e => setFormData({...formData, city: e.target.value})} /></div><div className="form-group"><label className="form-label">State</label><input type="text" className="form-control" value={formData.state} onChange={e => setFormData({...formData, state: e.target.value})} /></div><div className="form-group"><label className="form-label">Code</label><input type="text" className="form-control" value={formData.state_code} onChange={e => setFormData({...formData, state_code: e.target.value})} maxLength={2} /></div></div>
            <div className="form-row"><div className="form-group"><label className="form-label">Phone</label><input type="text" className="form-control" value={formData.phone} onChange={e => setFormData({...formData, phone: e.target.value})} /></div><div className="form-group"><label className="form-label">Email</label><input type="email" className="form-control" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} /></div></div>
          </div><div className="modal-footer"><button type="button" className="btn btn-secondary" onClick={closeModal}>Cancel</button><button type="submit" className="btn btn-primary">Save</button></div></form>
        </div></div>
      )}
    </div>
  );
};

export default CustomerMaster;
