import React, { useState, useEffect } from 'react';
import { Search, Eye, Filter } from 'lucide-react';
import api, { formatDate, getTodayDate } from '../../services/api';

const AuditLogs = ({ currentBranch }) => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedLog, setSelectedLog] = useState(null);
  
  const [filters, setFilters] = useState({
    entity_type: '',
    action: '',
    user_id: '',
    start_date: '',
    end_date: getTodayDate()
  });

  const entityTypes = ['user', 'role', 'voucher', 'ledger', 'item', 'sales_invoice', 'purchase_invoice', 'backup'];
  const actions = ['LOGIN', 'LOGOUT', 'USER_CREATED', 'USER_UPDATED', 'USER_DEACTIVATED', 'ROLE_CREATED', 'ROLE_UPDATED', 'SYSTEM_RESTORE'];

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.entity_type) params.append('entity_type', filters.entity_type);
      if (filters.action) params.append('action', filters.action);
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      params.append('limit', '500');
      
      const response = await api.get(`/security/audit-logs?${params.toString()}`);
      setLogs(response.data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const getActionBadgeClass = (action) => {
    if (action.includes('CREATE')) return 'badge-success';
    if (action.includes('UPDATE')) return 'badge-info';
    if (action.includes('DELETE') || action.includes('DEACTIVATE')) return 'badge-danger';
    if (action.includes('LOGIN')) return 'badge-primary';
    return 'badge-secondary';
  };

  return (
    <div data-testid="audit-logs">
      <div className="page-header">
        <div>
          <h1>Audit Logs</h1>
          <p className="page-subtitle">System Activity Tracking</p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '16px' }}>
        <div className="card-content">
          <div className="form-row">
            <div className="form-group" style={{ maxWidth: '150px' }}>
              <label className="form-label">Entity Type</label>
              <select className="form-control" value={filters.entity_type}
                onChange={e => setFilters({...filters, entity_type: e.target.value})}>
                <option value="">All Types</option>
                {entityTypes.map(type => (
                  <option key={type} value={type}>{type.toUpperCase()}</option>
                ))}
              </select>
            </div>
            <div className="form-group" style={{ maxWidth: '200px' }}>
              <label className="form-label">Action</label>
              <select className="form-control" value={filters.action}
                onChange={e => setFilters({...filters, action: e.target.value})}>
                <option value="">All Actions</option>
                {actions.map(action => (
                  <option key={action} value={action}>{action}</option>
                ))}
              </select>
            </div>
            <div className="form-group" style={{ maxWidth: '150px' }}>
              <label className="form-label">Start Date</label>
              <input type="date" className="form-control" value={filters.start_date}
                onChange={e => setFilters({...filters, start_date: e.target.value})} />
            </div>
            <div className="form-group" style={{ maxWidth: '150px' }}>
              <label className="form-label">End Date</label>
              <input type="date" className="form-control" value={filters.end_date}
                onChange={e => setFilters({...filters, end_date: e.target.value})} />
            </div>
            <div className="form-group" style={{ alignSelf: 'flex-end' }}>
              <button className="btn btn-primary" onClick={fetchLogs}>
                <Filter size={16} /> Apply Filter
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        {loading ? (
          <div className="loading-container"><div className="spinner"></div></div>
        ) : (
          <table className="data-grid">
            <thead>
              <tr>
                <th>Date/Time</th>
                <th>User</th>
                <th>Action</th>
                <th>Entity Type</th>
                <th>Entity ID</th>
                <th className="text-center">Details</th>
              </tr>
            </thead>
            <tbody>
              {logs.map(log => (
                <tr key={log.id}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                    {log.created_at?.replace('T', ' ').slice(0, 19)}
                  </td>
                  <td><strong>{log.username}</strong></td>
                  <td>
                    <span className={`badge ${getActionBadgeClass(log.action)}`}>
                      {log.action}
                    </span>
                  </td>
                  <td>{log.entity_type?.toUpperCase()}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {log.entity_id?.slice(0, 20)}...
                  </td>
                  <td className="text-center">
                    <button className="btn btn-sm btn-secondary" onClick={() => setSelectedLog(log)}>
                      <Eye size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {!loading && logs.length === 0 && <div className="empty-state"><p>No audit logs found</p></div>}
      </div>

      {selectedLog && (
        <div className="modal-overlay">
          <div className="modal" style={{ width: '700px', maxHeight: '90vh', overflow: 'auto' }}>
            <div className="modal-header">
              <h3>Audit Log Details</h3>
              <button className="modal-close" onClick={() => setSelectedLog(null)}>&times;</button>
            </div>
            <div className="modal-body">
              <table className="data-grid" style={{ fontSize: '12px' }}>
                <tbody>
                  <tr>
                    <th style={{ width: '150px' }}>Timestamp</th>
                    <td>{selectedLog.created_at?.replace('T', ' ')}</td>
                  </tr>
                  <tr>
                    <th>User</th>
                    <td>{selectedLog.username}</td>
                  </tr>
                  <tr>
                    <th>Action</th>
                    <td><span className={`badge ${getActionBadgeClass(selectedLog.action)}`}>{selectedLog.action}</span></td>
                  </tr>
                  <tr>
                    <th>Entity Type</th>
                    <td>{selectedLog.entity_type?.toUpperCase()}</td>
                  </tr>
                  <tr>
                    <th>Entity ID</th>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{selectedLog.entity_id}</td>
                  </tr>
                  <tr>
                    <th>Data Hash</th>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '10px' }}>{selectedLog.data_hash}</td>
                  </tr>
                </tbody>
              </table>

              {selectedLog.old_data && (
                <>
                  <h4 style={{ marginTop: '16px' }}>Old Data</h4>
                  <pre style={{ background: '#fee', padding: '10px', borderRadius: '4px', fontSize: '11px', overflow: 'auto', maxHeight: '200px' }}>
                    {JSON.stringify(selectedLog.old_data, null, 2)}
                  </pre>
                </>
              )}

              {selectedLog.new_data && (
                <>
                  <h4 style={{ marginTop: '16px' }}>New Data</h4>
                  <pre style={{ background: '#efe', padding: '10px', borderRadius: '4px', fontSize: '11px', overflow: 'auto', maxHeight: '200px' }}>
                    {JSON.stringify(selectedLog.new_data, null, 2)}
                  </pre>
                </>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setSelectedLog(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AuditLogs;
