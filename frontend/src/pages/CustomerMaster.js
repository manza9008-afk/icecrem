import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Plus, Edit2, X } from 'lucide-react';
import { toast } from 'sonner';

const CustomerMaster = () => {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    address: '',
    gstin: '',
    pan: '',
    phone: '',
    email: '',
    credit_limit: 0,
  });

  useEffect(() => {
    fetchCustomers();
  }, []);

  const fetchCustomers = async () => {
    try {
      const response = await api.get('/customers');
      setCustomers(response.data);
    } catch (error) {
      toast.error('Failed to fetch customers');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingCustomer) {
        await api.put(`/customers/${editingCustomer.id}`, formData);
        toast.success('Customer updated successfully');
      } else {
        await api.post('/customers', formData);
        toast.success('Customer created successfully');
      }
      setShowForm(false);
      setEditingCustomer(null);
      resetForm();
      fetchCustomers();
    } catch (error) {
      toast.error('Operation failed');
    }
  };

  const handleEdit = (customer) => {
    setEditingCustomer(customer);
    setFormData(customer);
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
      credit_limit: 0,
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
    <div data-testid="customer-master-page">
      <div className="page-header">
        <div>
          <h1>Customer Master</h1>
          <p className="page-subtitle">Manage customer information</p>
        </div>
        <button className="btn btn-primary" onClick={() => { setShowForm(true); setEditingCustomer(null); resetForm(); }} data-testid="add-customer-btn">
          <Plus size={18} />
          Add Customer
        </button>
      </div>

      {showForm && (
        <div className="modal-overlay" data-testid="customer-form-modal">
          <div className="modal-content">
            <div className="modal-header">
              <h2>{editingCustomer ? 'Edit Customer' : 'Add New Customer'}</h2>
              <button className="btn btn-ghost" onClick={() => { setShowForm(false); setEditingCustomer(null); }}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="grid grid-2">
                <div className="form-group">
                  <label>Customer Name *</label>
                  <input name="name" value={formData.name} onChange={handleChange} required data-testid="customer-name-input" />
                </div>
                <div className="form-group">
                  <label>Phone *</label>
                  <input name="phone" value={formData.phone} onChange={handleChange} required data-testid="customer-phone-input" />
                </div>
                <div className="form-group" style={{ gridColumn: 'span 2' }}>
                  <label>Address *</label>
                  <textarea name="address" value={formData.address} onChange={handleChange} required rows="2" data-testid="customer-address-input" />
                </div>
                <div className="form-group">
                  <label>GSTIN</label>
                  <input name="gstin" value={formData.gstin} onChange={handleChange} data-testid="customer-gstin-input" />
                </div>
                <div className="form-group">
                  <label>PAN</label>
                  <input name="pan" value={formData.pan} onChange={handleChange} data-testid="customer-pan-input" />
                </div>
                <div className="form-group">
                  <label>Email</label>
                  <input type="email" name="email" value={formData.email} onChange={handleChange} data-testid="customer-email-input" />
                </div>
                <div className="form-group">
                  <label>Credit Limit</label>
                  <input type="number" step="0.01" name="credit_limit" value={formData.credit_limit} onChange={handleChange} />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => { setShowForm(false); setEditingCustomer(null); }}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" data-testid="customer-save-btn">
                  {editingCustomer ? 'Update' : 'Save'}
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
                <th>Credit Limit</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((customer) => (
                <tr key={customer.id} data-testid={`customer-row-${customer.name}`}>
                  <td>{customer.name}</td>
                  <td className="data-value">{customer.phone}</td>
                  <td className="data-value">{customer.gstin || '-'}</td>
                  <td>{customer.address}</td>
                  <td className="data-value">₹{customer.credit_limit.toFixed(2)}</td>
                  <td>
                    <button className="btn btn-ghost" onClick={() => handleEdit(customer)} data-testid="edit-customer-btn">
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

export default CustomerMaster;
