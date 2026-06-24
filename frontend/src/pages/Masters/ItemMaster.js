import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Search, AlertTriangle } from 'lucide-react';
import api from '../../services/api';


const emptyItemForm = {
  code: '', name: '', print_name: '', category: 'General', hsn_code: '', unit: 'NOS',
  alternate_unit: '', conversion_factor: 1, gst_rate: 18, cess_rate: 0,
  cost_price: 0, selling_price: 0, mrp: 0, min_stock: 0, max_stock: 0, reorder_level: 0,
  is_batch_wise: true, is_expiry_tracking: true, description: ''
};

const getAlertQty = (item) => Number(item?.min_stock || item?.reorder_level || 0);

const ItemMaster = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [formData, setFormData] = useState(emptyItemForm);

  useEffect(() => { fetchItems(); }, []);

  const fetchItems = async () => {
    try {
      const response = await api.get('/inventory/items');
      setItems(response.data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const lowStockQty = Number(formData.min_stock || 0);
      const payload = {
        ...formData,
        conversion_factor: Number(formData.conversion_factor || 1),
        gst_rate: Number(formData.gst_rate || 0),
        cess_rate: Number(formData.cess_rate || 0),
        cost_price: Number(formData.cost_price || 0),
        selling_price: Number(formData.selling_price || 0),
        mrp: Number(formData.mrp || 0),
        min_stock: lowStockQty,
        reorder_level: lowStockQty,
        max_stock: Number(formData.max_stock || 0)
      };

      if (editingItem) {
        await api.put(`/inventory/items/${editingItem.id}`, payload);
      } else {
        await api.post('/inventory/items', payload);
      }
      fetchItems();
      closeModal();
    } catch (error) {
      const errorMessage =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        (error.message === 'Network Error'
          ? 'Request could not reach the backend from this page. Refresh and check the allowed localhost port.'
          : error.message) ||
        'Error saving item';
      alert(errorMessage);
    }
  };

  const handleEdit = (item) => {
    setEditingItem(item);
    setFormData({...emptyItemForm, ...item, min_stock: getAlertQty(item), reorder_level: getAlertQty(item)});
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingItem(null);
    setFormData(emptyItemForm);
  };

  const filteredItems = items.filter(i => !searchTerm || i.name.toLowerCase().includes(searchTerm.toLowerCase()) || i.code.toLowerCase().includes(searchTerm.toLowerCase()));

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="item-master">
      <div className="page-header">
        <div><h1>Item Master</h1><p className="page-subtitle">Manage inventory items</p></div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}><Plus size={16} /> Add Item</button>
      </div>

      <div className="filter-bar">
        <div className="filter-group">
          <Search size={14} />
          <input type="text" placeholder="Search items..." value={searchTerm} onChange={e => setSearchTerm(e.target.value)} />
        </div>
      </div>

      <div className="card">
        <table className="data-grid">
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Category</th>
              <th>Unit</th>
              <th className="text-right">Low Stock Alert</th>
              <th className="text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredItems.map(item => (
              <tr key={item.id}>
                <td><strong>{item.code}</strong></td>
                <td>{item.name}</td>
                <td>{item.category}</td>
                <td>{item.unit}</td>
                <td className="numeric">{getAlertQty(item)}</td>
                <td className="text-center"><button className="btn btn-sm btn-secondary" onClick={() => handleEdit(item)}><Edit2 size={14} /></button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="modal" style={{width: '700px', maxHeight: '90vh', overflow: 'auto'}}>
            <div className="modal-header">
              <h3>{editingItem ? 'Edit Item' : 'Add Item'}</h3>
              <button className="modal-close" onClick={closeModal}>&times;</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="form-row">
                  <div className="form-group"><label className="form-label">Item Code *</label><input type="text" className="form-control" value={formData.code} onChange={e => setFormData({...formData, code: e.target.value.toUpperCase()})} required /></div>
                  <div className="form-group"><label className="form-label">Item Name *</label><input type="text" className="form-control" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} required /></div>
                </div>
                <div className="form-row">
                  <div className="form-group"><label className="form-label">Category</label><input type="text" className="form-control" value={formData.category} onChange={e => setFormData({...formData, category: e.target.value})} /></div>
                  <div className="form-group"><label className="form-label">Unit *</label><select className="form-control" value={formData.unit} onChange={e => setFormData({...formData, unit: e.target.value})}><option>NOS</option><option>BOX</option><option>PCS</option></select></div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Low Stock Alert Qty</label>
                    <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                      <AlertTriangle size={16} color="#e53e3e" />
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        className="form-control"
                        value={formData.min_stock}
                        onChange={e => setFormData({...formData, min_stock: e.target.value})}
                      />
                    </div>
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group"><label style={{display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer'}}><input type="checkbox" checked={formData.is_batch_wise} onChange={e => setFormData({...formData, is_batch_wise: e.target.checked})} /><span>Batch-wise Tracking</span></label></div>
                  <div className="form-group"><label style={{display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer'}}><input type="checkbox" checked={formData.is_expiry_tracking} onChange={e => setFormData({...formData, is_expiry_tracking: e.target.checked})} /><span>Expiry Tracking</span></label></div>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={closeModal}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save Item</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default ItemMaster;
