import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Plus, Edit2, X } from 'lucide-react';
import { toast } from 'sonner';

const SupplierMaster = () => {
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    address: '',
    gstin: '',
    pan: '',
    phone: '',
    email: '',
  });

  useEffect(() => {
    fetchSuppliers();
  }, []);

  const fetchSuppliers = async () => {
    try {
      const response = await api.get('/suppliers');
      setSuppliers(response.data);
    } catch (error) {
      toast.error('Failed to fetch suppliers');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingSupplier) {
        await api.put(`/suppliers/${editingSupplier.id}`, formData);
        toast.success('Supplier updated successfully');
      } else {
        await api.post('/suppliers', formData);
        toast.success('Supplier created successfully');
      }
      setShowForm(false);
      setEditingSupplier(null);
      resetForm();
      fetchSuppliers();
    } catch (error) {
      toast.error('Operation failed');
    }
  };

  const handleEdit = (supplier) => {
    setEditingSupplier(supplier);
    setFormData(supplier);
    setShowForm(true);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      address: '',
      gstin: '',
      pan: '',
      phone: '',
      email: '',
    });
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  if (loading) {
    return <div className="loading-container"><div className="spinner" /></div>;
  }

  return (
    <div data-testid="supplier-master-page">
      <div className="page-header">
        <div>
          <h1>Supplier Master</h1>
          <p className="page-subtitle">Manage supplier information</p>
        </div>
        <button className="btn btn-primary" onClick={() => { setShowForm(true); setEditingSupplier(null); resetForm(); }} data-testid="add-supplier-btn">
          <Plus size={18} />
          Add Supplier
        </button>
      </div>

      {showForm && (
        <div className="modal-overlay" data-testid="supplier-form-modal">
          <div className="modal-content">
            <div className="modal-header">
              <h2>{editingSupplier ? 'Edit Supplier' : 'Add New Supplier'}</h2>
              <button className="btn btn-ghost" onClick={() => { setShowForm(false); setEditingSupplier(null); }}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="grid grid-2">
                <div className="form-group">
                  <label>Supplier Name *</label>
                  <input name="name" value={formData.name} onChange={handleChange} required data-testid="supplier-name-input" />
                </div>
                <div className="form-group">
                  <label>Phone *</label>
                  <input name="phone" value={formData.phone} onChange={handleChange} required data-testid="supplier-phone-input" />
                </div>
                <div className="form-group" style={{ gridColumn: 'span 2' }}>
                  <label>Address *</label>
                  <textarea name="address" value={formData.address} onChange={handleChange} required rows="2" />
                </div>
                <div className="form-group">
                  <label>GSTIN</label>
                  <input name="gstin" value={formData.gstin} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label>PAN</label>
                  <input name="pan" value={formData.pan} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label>Email</label>
                  <input type="email" name="email" value={formData.email} onChange={handleChange} />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => { setShowForm(false); setEditingSupplier(null); }}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" data-testid="supplier-save-btn">
                  {editingSupplier ? 'Update' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Phone</th>
                <th>GSTIN</th>
                <th>Address</th>
                <th>Email</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map((supplier) => (
                <tr key={supplier.id} data-testid={`supplier-row-${supplier.name}`}>
                  <td>{supplier.name}</td>
                  <td className="data-value">{supplier.phone}</td>
                  <td className="data-value">{supplier.gstin || '-'}</td>
                  <td>{supplier.address}</td>
                  <td>{supplier.email || '-'}</td>
                  <td>
                    <button className="btn btn-ghost" onClick={() => handleEdit(supplier)} data-testid="edit-supplier-btn">
                      <Edit2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default SupplierMaster;
