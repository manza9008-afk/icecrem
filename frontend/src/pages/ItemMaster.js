import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Plus, Edit2, Trash2, X } from 'lucide-react';
import { toast } from 'sonner';

const ItemMaster = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    sku: '',
    category: '',
<<<<<<< HEAD
    hsn: '',
    gst_rate: 0,
    unit: 'Box',
    cost_price: 0,
    selling_price: 0,
    reorder_level: 500,
=======
    hsn: '2105',
    gst_rate: 12,
    unit: 'Box',
    cost_price: 0,
    selling_price: 0,
    reorder_level: 10,
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68
    opening_stock: 0,
  });

  useEffect(() => {
    fetchItems();
  }, []);

  const fetchItems = async () => {
    try {
      const response = await api.get('/items');
      setItems(response.data);
    } catch (error) {
      toast.error('Failed to fetch items');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingItem) {
        await api.put(`/items/${editingItem.id}`, formData);
        toast.success('Item updated successfully');
      } else {
        await api.post('/items', formData);
        toast.success('Item created successfully');
      }
      setShowForm(false);
      setEditingItem(null);
      resetForm();
      fetchItems();
    } catch (error) {
      toast.error('Operation failed');
    }
  };

  const handleEdit = (item) => {
    setEditingItem(item);
    setFormData(item);
    setShowForm(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this item?')) return;
    try {
      await api.delete(`/items/${id}`);
      toast.success('Item deleted successfully');
      fetchItems();
    } catch (error) {
      toast.error('Failed to delete item');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      sku: '',
      category: '',
<<<<<<< HEAD
      hsn: '',
      gst_rate: 0,
      unit: 'Box',
      cost_price: 0,
      selling_price: 0,
      reorder_level: 500,
=======
      hsn: '2105',
      gst_rate: 12,
      unit: 'Box',
      cost_price: 0,
      selling_price: 0,
      reorder_level: 10,
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68
      opening_stock: 0,
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
    <div data-testid="item-master-page">
      <div className="page-header">
        <div>
          <h1>Item Master</h1>
          <p className="page-subtitle">Manage ice cream products and inventory items</p>
        </div>
        <button 
          className="btn btn-primary" 
          onClick={() => { setShowForm(true); setEditingItem(null); resetForm(); }}
          data-testid="add-item-btn"
        >
          <Plus size={18} />
          Add Item
        </button>
      </div>

      {showForm && (
        <div className="modal-overlay" data-testid="item-form-modal">
          <div className="modal-content">
            <div className="modal-header">
              <h2>{editingItem ? 'Edit Item' : 'Add New Item'}</h2>
              <button className="btn btn-ghost" onClick={() => { setShowForm(false); setEditingItem(null); }}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="grid grid-2">
                <div className="form-group">
                  <label>Item Name *</label>
                  <input name="name" value={formData.name} onChange={handleChange} required data-testid="item-name-input" />
                </div>
                <div className="form-group">
                  <label>SKU *</label>
                  <input name="sku" value={formData.sku} onChange={handleChange} required data-testid="item-sku-input" />
                </div>
                <div className="form-group">
                  <label>Category *</label>
                  <input name="category" value={formData.category} onChange={handleChange} required data-testid="item-category-input" />
                </div>
                <div className="form-group">
<<<<<<< HEAD
=======
                  <label>HSN Code</label>
                  <input name="hsn" value={formData.hsn} onChange={handleChange} data-testid="item-hsn-input" />
                </div>
                <div className="form-group">
                  <label>GST Rate (%)</label>
                  <input type="number" name="gst_rate" value={formData.gst_rate} onChange={handleChange} data-testid="item-gst-input" />
                </div>
                <div className="form-group">
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68
                  <label>Unit</label>
                  <select name="unit" value={formData.unit} onChange={handleChange} data-testid="item-unit-select">
                    <option>Box</option>
                    <option>Piece</option>
                    <option>Carton</option>
                    <option>Liter</option>
                  </select>
                </div>
                <div className="form-group">
<<<<<<< HEAD
=======
                  <label>Cost Price</label>
                  <input type="number" step="0.01" name="cost_price" value={formData.cost_price} onChange={handleChange} data-testid="item-cost-input" />
                </div>
                <div className="form-group">
                  <label>Selling Price</label>
                  <input type="number" step="0.01" name="selling_price" value={formData.selling_price} onChange={handleChange} data-testid="item-price-input" />
                </div>
                <div className="form-group">
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68
                  <label>Reorder Level</label>
                  <input type="number" name="reorder_level" value={formData.reorder_level} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label>Opening Stock</label>
                  <input type="number" step="0.01" name="opening_stock" value={formData.opening_stock} onChange={handleChange} disabled={!!editingItem} />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => { setShowForm(false); setEditingItem(null); }}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" data-testid="item-save-btn">
                  {editingItem ? 'Update' : 'Save'}
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
                <th>SKU</th>
                <th>Name</th>
                <th>Category</th>
<<<<<<< HEAD
                <th>Unit</th>
=======
                <th>HSN</th>
                <th>GST %</th>
                <th>Unit</th>
                <th>Cost Price</th>
                <th>Selling Price</th>
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} data-testid={`item-row-${item.sku}`}>
                  <td className="data-value">{item.sku}</td>
                  <td>{item.name}</td>
                  <td>{item.category}</td>
<<<<<<< HEAD
                  <td>{item.unit}</td>
=======
                  <td className="data-value">{item.hsn}</td>
                  <td className="data-value">{item.gst_rate}%</td>
                  <td>{item.unit}</td>
                  <td className="data-value">₹{item.cost_price.toFixed(2)}</td>
                  <td className="data-value">₹{item.selling_price.toFixed(2)}</td>
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68
                  <td>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button className="btn btn-ghost" onClick={() => handleEdit(item)} data-testid="edit-item-btn">
                        <Edit2 size={16} />
                      </button>
                      <button className="btn btn-ghost" onClick={() => handleDelete(item.id)} data-testid="delete-item-btn">
                        <Trash2 size={16} />
                      </button>
                    </div>
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

export default ItemMaster;
