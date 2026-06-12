import React, { useState, useEffect } from 'react';
import { ChevronRight, ChevronDown, Plus, Edit2 } from 'lucide-react';
import api from '../../services/api';

const AccountGroups = () => {
  const [groups, setGroups] = useState([]);
  const [flatGroups, setFlatGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingGroup, setEditingGroup] = useState(null);
  const [expandedNodes, setExpandedNodes] = useState(new Set());
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [formData, setFormData] = useState({
    code: '', name: '', account_type: 'Asset', parent_id: '', nature: 'debit',
    affects_gross_profit: false, description: ''
  });

  useEffect(() => { fetchGroups(); }, []);

  const fetchGroups = async () => {
    try {
      const [treeRes, flatRes] = await Promise.all([
        api.get('/accounting/account-groups/tree'),
        api.get('/accounting/account-groups')
      ]);
      setGroups(treeRes.data);
      setFlatGroups(flatRes.data);
      // Auto-expand root nodes
      setExpandedNodes(new Set(treeRes.data.map(g => g.id)));
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleNode = (id) => {
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedNodes(newExpanded);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const submitData = { ...formData };
      if (!submitData.parent_id) delete submitData.parent_id;
      
      if (editingGroup) {
        await api.put(`/accounting/account-groups/${editingGroup.id}`, submitData);
      } else {
        await api.post('/accounting/account-groups', submitData);
      }
      fetchGroups();
      closeModal();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error saving group');
    }
  };

  const handleEdit = (group) => {
    setEditingGroup(group);
    setFormData({
      code: group.code, name: group.name, account_type: group.account_type,
      parent_id: group.parent_id || '', nature: group.nature,
      affects_gross_profit: group.affects_gross_profit, description: group.description || ''
    });
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingGroup(null);
    setFormData({
      code: '', name: '', account_type: 'Asset', parent_id: '', nature: 'debit',
      affects_gross_profit: false, description: ''
    });
  };

  const renderTreeNode = (node, level = 0) => {
    const hasChildren = node.children && node.children.length > 0;
    const isExpanded = expandedNodes.has(node.id);
    const isSelected = selectedGroup?.id === node.id;

    return (
      <div key={node.id} className="tree-node">
        <div 
          className={`tree-node-content ${isSelected ? 'selected' : ''}`}
          style={{ paddingLeft: `${level * 20 + 8}px` }}
          onClick={() => setSelectedGroup(node)}
        >
          <span className="tree-toggle" onClick={(e) => { e.stopPropagation(); hasChildren && toggleNode(node.id); }}>
            {hasChildren ? (isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />) : <span style={{width: 14}}></span>}
          </span>
          <span style={{ flex: 1 }}>
            <strong>{node.code}</strong> - {node.name}
          </span>
          <span className={`badge badge-${node.nature === 'debit' ? 'info' : 'success'}`} style={{fontSize: '9px'}}>
            {node.nature.toUpperCase()}
          </span>
          {!node.is_system && (
            <button className="btn btn-sm btn-secondary" onClick={(e) => { e.stopPropagation(); handleEdit(node); }} style={{marginLeft: '8px', padding: '2px 6px'}}>
              <Edit2 size={12} />
            </button>
          )}
        </div>
        {hasChildren && isExpanded && (
          <div className="tree-children">
            {node.children.map(child => renderTreeNode(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="account-groups">
      <div className="page-header">
        <div>
          <h1>Account Groups</h1>
          <p className="page-subtitle">Chart of Accounts Hierarchy</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={16} /> Add Group
        </button>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header">Account Group Tree</div>
          <div className="card-content" style={{maxHeight: '600px', overflowY: 'auto'}}>
            <div className="tree-view">
              {groups.map(group => renderTreeNode(group))}
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">Group Details</div>
          <div className="card-content">
            {selectedGroup ? (
              <div>
                <div className="form-group">
                  <label className="form-label">Code</label>
                  <div>{selectedGroup.code}</div>
                </div>
                <div className="form-group">
                  <label className="form-label">Name</label>
                  <div>{selectedGroup.name}</div>
                </div>
                <div className="form-group">
                  <label className="form-label">Account Type</label>
                  <div>{selectedGroup.account_type}</div>
                </div>
                <div className="form-group">
                  <label className="form-label">Nature</label>
                  <div className={`badge badge-${selectedGroup.nature === 'debit' ? 'info' : 'success'}`}>
                    {selectedGroup.nature.toUpperCase()}
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Affects Gross Profit</label>
                  <div>{selectedGroup.affects_gross_profit ? 'Yes' : 'No'}</div>
                </div>
                <div className="form-group">
                  <label className="form-label">System Group</label>
                  <div>{selectedGroup.is_system ? 'Yes (Cannot Edit)' : 'No'}</div>
                </div>
              </div>
            ) : (
              <div className="empty-state">
                <p>Select a group to view details</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="modal" style={{width: '500px'}}>
            <div className="modal-header">
              <h3>{editingGroup ? 'Edit Account Group' : 'Add Account Group'}</h3>
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
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Account Type *</label>
                    <select className="form-control" value={formData.account_type} onChange={e => setFormData({...formData, account_type: e.target.value})}>
                      <option value="Asset">Asset</option>
                      <option value="Liability">Liability</option>
                      <option value="Capital">Capital</option>
                      <option value="Income">Income</option>
                      <option value="Expense">Expense</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Nature *</label>
                    <select className="form-control" value={formData.nature} onChange={e => setFormData({...formData, nature: e.target.value})}>
                      <option value="debit">Debit</option>
                      <option value="credit">Credit</option>
                    </select>
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Parent Group</label>
                  <select className="form-control" value={formData.parent_id} onChange={e => setFormData({...formData, parent_id: e.target.value})}>
                    <option value="">-- Primary Group --</option>
                    {flatGroups.filter(g => g.id !== editingGroup?.id).map(g => (
                      <option key={g.id} value={g.id}>{g.code} - {g.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label style={{display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer'}}>
                    <input type="checkbox" checked={formData.affects_gross_profit} onChange={e => setFormData({...formData, affects_gross_profit: e.target.checked})} />
                    <span>Affects Gross Profit (Trading Account)</span>
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

export default AccountGroups;
