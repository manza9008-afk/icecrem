import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Plus, Edit2, Trash2, ChevronRight, ChevronDown, Save, X } from 'lucide-react';
import { toast } from 'sonner';
import './AccountGroups.css';

const AccountGroups = () => {
  const [groups, setGroups] = useState([]);
  const [treeData, setTreeData] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [expandedNodes, setExpandedNodes] = useState(new Set());
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    account_type: 'Asset',
    parent_id: null,
    description: ''
  });

  useEffect(() => {
    fetchAccountGroups();
  }, []);

  const fetchAccountGroups = async () => {
    try {
      const response = await api.get('/accounting/account-groups/tree');
      setTreeData(response.data);
      
      const flatResponse = await api.get('/accounting/account-groups');
      setGroups(flatResponse.data);
    } catch (error) {
      toast.error('Failed to fetch account groups');
    }
  };

  const toggleNode = (nodeId) => {
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(nodeId)) {
      newExpanded.delete(nodeId);
    } else {
      newExpanded.add(nodeId);
    }
    setExpandedNodes(newExpanded);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (selectedGroup) {
        await api.put(`/accounting/account-groups/${selectedGroup.id}`, formData);
        toast.success('Account group updated');
      } else {
        await api.post('/accounting/account-groups', formData);
        toast.success('Account group created');
      }
      setShowForm(false);
      resetForm();
      fetchAccountGroups();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Operation failed');
    }
  };

  const handleEdit = (group) => {
    setSelectedGroup(group);
    setFormData({
      code: group.code,
      name: group.name,
      account_type: group.account_type,
      parent_id: group.parent_id || null,
      description: group.description || ''
    });
    setShowForm(true);
  };

  const handleDelete = async (group) => {
    if (!window.confirm(`Delete account group "${group.name}"?`)) return;
    try {
      await api.delete(`/accounting/account-groups/${group.id}`);
      toast.success('Account group deleted');
      fetchAccountGroups();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Cannot delete');
    }
  };

  const resetForm = () => {
    setSelectedGroup(null);
    setFormData({
      code: '',
      name: '',
      account_type: 'Asset',
      parent_id: null,
      description: ''
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
          {hasChildren && (
            <button 
              className="tree-toggle"
              onClick={(e) => {
                e.stopPropagation();
                toggleNode(node.id);
              }}
            >
              {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </button>
          )}
          {!hasChildren && <span className="tree-spacer" />}
          
          <span className="tree-icon">{getAccountIcon(node.account_type)}</span>
          <span className="tree-label">
            <strong>{node.code}</strong> - {node.name}
          </span>
          <span className="tree-type">[{node.account_type}]</span>
        </div>
        
        {hasChildren && isExpanded && (
          <div className="tree-children">
            {node.children.map(child => renderTreeNode(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  const getAccountIcon = (type) => {
    const icons = {
      'Asset': '💰',
      'Liability': '📋',
      'Capital': '🏛️',
      'Income': '📈',
      'Expense': '📉'
    };
    return icons[type] || '📁';
  };

  return (
    <div className="account-groups-page" data-testid="account-groups-page">
      <div className="accounting-header">
        <div>
          <h1>Chart of Accounts</h1>
          <p className="subtitle">Hierarchical Account Group Structure</p>
        </div>
        <button 
          className="btn btn-primary" 
          onClick={() => { setShowForm(true); resetForm(); }}
          data-testid="add-account-group-btn"
        >
          <Plus size={18} />
          New Account Group
        </button>
      </div>

      <div className="accounting-split-layout">
        {/* LEFT: Tree View */}
        <div className="tree-panel">
          <div className="tree-panel-header">
            <h3>Account Groups Hierarchy</h3>
            <span className="tree-count">{groups.length} groups</span>
          </div>
          <div className="tree-container">
            {treeData.map(node => renderTreeNode(node))}
          </div>
        </div>

        {/* RIGHT: Details Panel */}
        <div className="details-panel">
          {showForm ? (
            <div className="form-container">
              <div className="form-header">
                <h3>{selectedGroup ? 'Edit Account Group' : 'New Account Group'}</h3>
                <button className="btn-icon" onClick={() => { setShowForm(false); resetForm(); }}>
                  <X size={20} />
                </button>
              </div>
              
              <form onSubmit={handleSubmit} className="structured-form">
                <div className="form-row">
                  <div className="form-field">
                    <label>Group Code *</label>
                    <input 
                      value={formData.code}
                      onChange={(e) => setFormData({...formData, code: e.target.value})}
                      required
                      placeholder="e.g. 1000"
                      data-testid="group-code-input"
                    />
                  </div>
                  <div className="form-field">
                    <label>Account Type *</label>
                    <select 
                      value={formData.account_type}
                      onChange={(e) => setFormData({...formData, account_type: e.target.value})}
                      data-testid="account-type-select"
                    >
                      <option value="Asset">Asset</option>
                      <option value="Liability">Liability</option>
                      <option value="Capital">Capital</option>
                      <option value="Income">Income</option>
                      <option value="Expense">Expense</option>
                    </select>
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-field full-width">
                    <label>Group Name *</label>
                    <input 
                      value={formData.name}
                      onChange={(e) => setFormData({...formData, name: e.target.value})}
                      required
                      placeholder="e.g. Current Assets"
                      data-testid="group-name-input"
                    />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-field full-width">
                    <label>Parent Group</label>
                    <select 
                      value={formData.parent_id || ''}
                      onChange={(e) => setFormData({...formData, parent_id: e.target.value || null})}
                      data-testid="parent-group-select"
                    >
                      <option value="">-- No Parent (Top Level) --</option>
                      {groups.map(g => (
                        <option key={g.id} value={g.id}>
                          {g.code} - {g.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-field full-width">
                    <label>Description</label>
                    <textarea 
                      value={formData.description}
                      onChange={(e) => setFormData({...formData, description: e.target.value})}
                      rows="3"
                      placeholder="Optional description"
                    />
                  </div>
                </div>

                <div className="form-actions">
                  <button type="button" className="btn btn-secondary" onClick={() => { setShowForm(false); resetForm(); }}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary" data-testid="save-group-btn">
                    <Save size={18} />
                    {selectedGroup ? 'Update' : 'Save'}
                  </button>
                </div>
              </form>
            </div>
          ) : selectedGroup ? (
            <div className="details-container">
              <div className="details-header">
                <h3>Account Group Details</h3>
                <div className="details-actions">
                  <button className="btn-icon" onClick={() => handleEdit(selectedGroup)} data-testid="edit-group-btn">
                    <Edit2 size={18} />
                  </button>
                  <button className="btn-icon" onClick={() => handleDelete(selectedGroup)} data-testid="delete-group-btn">
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
              
              <table className="details-table">
                <tbody>
                  <tr>
                    <th>Code:</th>
                    <td>{selectedGroup.code}</td>
                  </tr>
                  <tr>
                    <th>Name:</th>
                    <td>{selectedGroup.name}</td>
                  </tr>
                  <tr>
                    <th>Type:</th>
                    <td>
                      <span className="type-badge">{selectedGroup.account_type}</span>
                    </td>
                  </tr>
                  <tr>
                    <th>Nature:</th>
                    <td>{['Asset', 'Expense'].includes(selectedGroup.account_type) ? 'Debit' : 'Credit'}</td>
                  </tr>
                  <tr>
                    <th>Parent:</th>
                    <td>
                      {selectedGroup.parent_id 
                        ? groups.find(g => g.id === selectedGroup.parent_id)?.name || 'N/A'
                        : 'Top Level'
                      }
                    </td>
                  </tr>
                  <tr>
                    <th>Description:</th>
                    <td>{selectedGroup.description || '-'}</td>
                  </tr>
                  <tr>
                    <th>Created:</th>
                    <td>{new Date(selectedGroup.created_at).toLocaleString()}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-details">
              <p>Select an account group from the tree to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AccountGroups;
