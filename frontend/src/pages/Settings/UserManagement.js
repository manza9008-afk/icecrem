import React, { useState, useEffect } from 'react';
import { Plus, Edit, UserX, Shield, Eye } from 'lucide-react';
import api, { formatDate } from '../../services/api';

const UserManagement = ({ currentBranch }) => {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editUser, setEditUser] = useState(null);
  const [saving, setSaving] = useState(false);
  
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    email: '',
    full_name: '',
    phone: '',
    role_id: '',
    branch_id: '',
    is_active: true
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [usersRes, rolesRes, branchesRes] = await Promise.all([
        api.get('/security/users'),
        api.get('/security/roles'),
        api.get('/branches')
      ]);
      setUsers(usersRes.data);
      setRoles(rolesRes.data);
      setBranches(branchesRes.data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!formData.username || !formData.email || !formData.role_id) {
      alert('Please fill required fields');
      return;
    }
    if (!editUser && !formData.password) {
      alert('Password is required for new users');
      return;
    }

    setSaving(true);
    try {
      if (editUser) {
        const updateData = { ...formData };
        if (!updateData.password) delete updateData.password;
        await api.put(`/security/users/${editUser.id}`, updateData);
        alert('User updated!');
      } else {
        await api.post('/security/users', formData);
        alert('User created!');
      }
      resetForm();
      fetchData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error saving user');
    } finally {
      setSaving(false);
    }
  };

  const resetForm = () => {
    setShowForm(false);
    setEditUser(null);
    setFormData({
      username: '',
      password: '',
      email: '',
      full_name: '',
      phone: '',
      role_id: '',
      branch_id: '',
      is_active: true
    });
  };

  const openEdit = (user) => {
    setEditUser(user);
    setFormData({
      username: user.username,
      password: '',
      email: user.email,
      full_name: user.full_name,
      phone: user.phone || '',
      role_id: user.role_id,
      branch_id: user.branch_id || '',
      is_active: user.is_active
    });
    setShowForm(true);
  };

  const deactivateUser = async (user) => {
    if (!window.confirm(`Deactivate user ${user.username}?`)) return;
    try {
      await api.delete(`/security/users/${user.id}`);
      fetchData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error deactivating user');
    }
  };

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  if (showForm) {
    return (
      <div data-testid="user-form">
        <div className="page-header">
          <div>
            <h1>{editUser ? 'Edit User' : 'New User'}</h1>
            <p className="page-subtitle">User Account Management</p>
          </div>
          <div className="btn-group">
            <button className="btn btn-secondary" onClick={resetForm}>Cancel</button>
            <button className="btn btn-primary" onClick={handleSubmit} disabled={saving}>
              {saving ? 'Saving...' : 'Save User'}
            </button>
          </div>
        </div>

        <div className="card">
          <div className="card-header">User Details</div>
          <div className="card-content">
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Username *</label>
                <input type="text" className="form-control" value={formData.username}
                  onChange={e => setFormData({...formData, username: e.target.value})}
                  disabled={!!editUser} />
              </div>
              <div className="form-group">
                <label className="form-label">{editUser ? 'New Password (leave blank to keep)' : 'Password *'}</label>
                <input type="password" className="form-control" value={formData.password}
                  onChange={e => setFormData({...formData, password: e.target.value})} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Full Name</label>
                <input type="text" className="form-control" value={formData.full_name}
                  onChange={e => setFormData({...formData, full_name: e.target.value})} />
              </div>
              <div className="form-group">
                <label className="form-label">Email *</label>
                <input type="email" className="form-control" value={formData.email}
                  onChange={e => setFormData({...formData, email: e.target.value})} />
              </div>
              <div className="form-group">
                <label className="form-label">Phone</label>
                <input type="text" className="form-control" value={formData.phone}
                  onChange={e => setFormData({...formData, phone: e.target.value})} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Role *</label>
                <select className="form-control" value={formData.role_id}
                  onChange={e => setFormData({...formData, role_id: e.target.value})}>
                  <option value="">Select Role</option>
                  {roles.map(role => (
                    <option key={role.id} value={role.id}>{role.name} ({role.code})</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Default Branch</label>
                <select className="form-control" value={formData.branch_id}
                  onChange={e => setFormData({...formData, branch_id: e.target.value})}>
                  <option value="">All Branches</option>
                  {branches.map(branch => (
                    <option key={branch.id} value={branch.id}>{branch.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group" style={{ maxWidth: '150px' }}>
                <label className="form-label">Status</label>
                <select className="form-control" value={formData.is_active ? 'active' : 'inactive'}
                  onChange={e => setFormData({...formData, is_active: e.target.value === 'active'})}>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="user-management">
      <div className="page-header">
        <div>
          <h1>User Management</h1>
          <p className="page-subtitle">{users.length} users</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>
          <Plus size={16} /> New User
        </button>
      </div>

      <div className="card">
        <table className="data-grid">
          <thead>
            <tr>
              <th>Username</th>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Branch</th>
              <th>Last Login</th>
              <th>Status</th>
              <th className="text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map(user => (
              <tr key={user.id}>
                <td><strong>{user.username}</strong></td>
                <td>{user.full_name}</td>
                <td>{user.email}</td>
                <td>
                  <span className="badge badge-info">{user.role_code || user.role_name}</span>
                </td>
                <td>{branches.find(b => b.id === user.branch_id)?.name || 'All'}</td>
                <td>{user.last_login ? formatDate(user.last_login) : '-'}</td>
                <td>
                  <span className={`badge ${user.is_active ? 'badge-success' : 'badge-danger'}`}>
                    {user.is_active ? 'ACTIVE' : 'INACTIVE'}
                  </span>
                </td>
                <td className="text-center">
                  <button className="btn btn-sm btn-secondary" onClick={() => openEdit(user)} style={{ marginRight: '4px' }}>
                    <Edit size={14} />
                  </button>
                  {user.is_active && (
                    <button className="btn btn-sm btn-danger" onClick={() => deactivateUser(user)}>
                      <UserX size={14} />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {users.length === 0 && <div className="empty-state"><p>No users found</p></div>}
      </div>

      <div className="card" style={{ marginTop: '20px' }}>
        <div className="card-header">Roles</div>
        <div className="card-content">
          <table className="data-grid">
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
                <th>Description</th>
                <th>Type</th>
              </tr>
            </thead>
            <tbody>
              {roles.map(role => (
                <tr key={role.id}>
                  <td><strong>{role.code}</strong></td>
                  <td>{role.name}</td>
                  <td>{role.description}</td>
                  <td>
                    {role.is_system ? 
                      <span className="badge badge-secondary">SYSTEM</span> : 
                      <span className="badge badge-info">CUSTOM</span>
                    }
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

export default UserManagement;
