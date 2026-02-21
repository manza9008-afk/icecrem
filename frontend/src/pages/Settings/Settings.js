import React, { useState, useEffect } from 'react';
import { Save, Building, Calendar, Database, Shield, FileText } from 'lucide-react';
import api from '../../services/api';

const Settings = ({ currentBranch }) => {
  const [activeTab, setActiveTab] = useState('company');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  const [companyData, setCompanyData] = useState({});
  const [financialYears, setFinancialYears] = useState([]);
  const [systemConfig, setSystemConfig] = useState({});
  const [systemStats, setSystemStats] = useState({});

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [companyRes, fyRes, configRes, statsRes] = await Promise.all([
        api.get('/system/company'),
        api.get('/system/financial-years'),
        api.get('/system/config'),
        api.get('/system/stats')
      ]);
      setCompanyData(companyRes.data);
      setFinancialYears(fyRes.data);
      setSystemConfig(configRes.data);
      setSystemStats(statsRes.data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveCompanySettings = async () => {
    setSaving(true);
    try {
      await api.put('/system/company', companyData);
      alert('Company settings saved!');
    } catch (error) {
      alert(error.response?.data?.detail || 'Error saving settings');
    } finally {
      setSaving(false);
    }
  };

  const saveSystemConfig = async () => {
    setSaving(true);
    try {
      await api.put('/system/config', systemConfig);
      alert('System configuration saved!');
    } catch (error) {
      alert(error.response?.data?.detail || 'Error saving configuration');
    } finally {
      setSaving(false);
    }
  };

  const activateFinancialYear = async (fyId) => {
    if (!window.confirm('Activate this financial year? This will deactivate other years.')) return;
    try {
      await api.put(`/system/financial-years/${fyId}/activate`);
      fetchData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error activating financial year');
    }
  };

  const createBackup = async () => {
    if (!window.confirm('Create a full backup? This may take a moment.')) return;
    try {
      const response = await api.get('/system/backup', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `hooren_erp_backup_${new Date().toISOString().slice(0,10)}.json.gz`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      alert('Error creating backup');
    }
  };

  const optimizeDatabase = async () => {
    if (!window.confirm('Optimize database? This will create indexes for better performance.')) return;
    try {
      const response = await api.post('/system/optimize');
      alert(`Optimization complete!\n${response.data.optimizations.length} optimizations applied.`);
    } catch (error) {
      alert('Error optimizing database');
    }
  };

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div data-testid="settings">
      <div className="page-header">
        <div>
          <h1>Settings</h1>
          <p className="page-subtitle">System Configuration & Administration</p>
        </div>
      </div>

      <div className="tabs-container">
        <div className="tabs">
          <button className={`tab ${activeTab === 'company' ? 'active' : ''}`} onClick={() => setActiveTab('company')}>
            <Building size={16} /> Company
          </button>
          <button className={`tab ${activeTab === 'financial-year' ? 'active' : ''}`} onClick={() => setActiveTab('financial-year')}>
            <Calendar size={16} /> Financial Year
          </button>
          <button className={`tab ${activeTab === 'system' ? 'active' : ''}`} onClick={() => setActiveTab('system')}>
            <Shield size={16} /> System Config
          </button>
          <button className={`tab ${activeTab === 'backup' ? 'active' : ''}`} onClick={() => setActiveTab('backup')}>
            <Database size={16} /> Backup
          </button>
        </div>
      </div>

      {activeTab === 'company' && (
        <div className="card">
          <div className="card-header">
            Company Information
            <button className="btn btn-primary btn-sm" onClick={saveCompanySettings} disabled={saving}>
              <Save size={14} /> {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
          <div className="card-content">
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Business Name *</label>
                <input type="text" className="form-control" value={companyData.name || ''} 
                  onChange={e => setCompanyData({...companyData, name: e.target.value})} />
              </div>
              <div className="form-group">
                <label className="form-label">Legal Name</label>
                <input type="text" className="form-control" value={companyData.legal_name || ''} 
                  onChange={e => setCompanyData({...companyData, legal_name: e.target.value})} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">GSTIN *</label>
                <input type="text" className="form-control" value={companyData.gstin || ''} maxLength={15}
                  onChange={e => setCompanyData({...companyData, gstin: e.target.value.toUpperCase()})} />
              </div>
              <div className="form-group">
                <label className="form-label">PAN</label>
                <input type="text" className="form-control" value={companyData.pan || ''} maxLength={10}
                  onChange={e => setCompanyData({...companyData, pan: e.target.value.toUpperCase()})} />
              </div>
              <div className="form-group">
                <label className="form-label">CIN</label>
                <input type="text" className="form-control" value={companyData.cin || ''} 
                  onChange={e => setCompanyData({...companyData, cin: e.target.value})} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group" style={{ flex: 2 }}>
                <label className="form-label">Address</label>
                <input type="text" className="form-control" value={companyData.address || ''} 
                  onChange={e => setCompanyData({...companyData, address: e.target.value})} />
              </div>
              <div className="form-group">
                <label className="form-label">City</label>
                <input type="text" className="form-control" value={companyData.city || ''} 
                  onChange={e => setCompanyData({...companyData, city: e.target.value})} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">State</label>
                <input type="text" className="form-control" value={companyData.state || ''} 
                  onChange={e => setCompanyData({...companyData, state: e.target.value})} />
              </div>
              <div className="form-group" style={{ maxWidth: '100px' }}>
                <label className="form-label">State Code</label>
                <input type="text" className="form-control" value={companyData.state_code || ''} maxLength={2}
                  onChange={e => setCompanyData({...companyData, state_code: e.target.value})} />
              </div>
              <div className="form-group" style={{ maxWidth: '120px' }}>
                <label className="form-label">PIN Code</label>
                <input type="text" className="form-control" value={companyData.pin_code || ''} maxLength={6}
                  onChange={e => setCompanyData({...companyData, pin_code: e.target.value})} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Phone</label>
                <input type="text" className="form-control" value={companyData.phone || ''} 
                  onChange={e => setCompanyData({...companyData, phone: e.target.value})} />
              </div>
              <div className="form-group">
                <label className="form-label">Email</label>
                <input type="email" className="form-control" value={companyData.email || ''} 
                  onChange={e => setCompanyData({...companyData, email: e.target.value})} />
              </div>
              <div className="form-group">
                <label className="form-label">Website</label>
                <input type="text" className="form-control" value={companyData.website || ''} 
                  onChange={e => setCompanyData({...companyData, website: e.target.value})} />
              </div>
            </div>

            <h4 style={{ marginTop: '20px', marginBottom: '12px' }}>Bank Details</h4>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Bank Name</label>
                <input type="text" className="form-control" value={companyData.bank_name || ''} 
                  onChange={e => setCompanyData({...companyData, bank_name: e.target.value})} />
              </div>
              <div className="form-group">
                <label className="form-label">Account Number</label>
                <input type="text" className="form-control" value={companyData.bank_account || ''} 
                  onChange={e => setCompanyData({...companyData, bank_account: e.target.value})} />
              </div>
              <div className="form-group">
                <label className="form-label">IFSC Code</label>
                <input type="text" className="form-control" value={companyData.bank_ifsc || ''} 
                  onChange={e => setCompanyData({...companyData, bank_ifsc: e.target.value.toUpperCase()})} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Branch</label>
                <input type="text" className="form-control" value={companyData.bank_branch || ''} 
                  onChange={e => setCompanyData({...companyData, bank_branch: e.target.value})} />
              </div>
              <div className="form-group">
                <label className="form-label">UPI ID</label>
                <input type="text" className="form-control" value={companyData.upi_id || ''} 
                  onChange={e => setCompanyData({...companyData, upi_id: e.target.value})} />
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'financial-year' && (
        <div className="card">
          <div className="card-header">Financial Years</div>
          <div className="card-content">
            <table className="data-grid">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Start Date</th>
                  <th>End Date</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {financialYears.map(fy => (
                  <tr key={fy.id}>
                    <td><strong>{fy.code}</strong></td>
                    <td>{fy.name}</td>
                    <td>{fy.start_date}</td>
                    <td>{fy.end_date}</td>
                    <td>
                      {fy.is_active && <span className="badge badge-success">ACTIVE</span>}
                      {fy.is_locked && <span className="badge badge-warning" style={{ marginLeft: '4px' }}>LOCKED</span>}
                    </td>
                    <td>
                      {!fy.is_active && (
                        <button className="btn btn-sm btn-primary" onClick={() => activateFinancialYear(fy.id)}>
                          Activate
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'system' && (
        <div className="card">
          <div className="card-header">
            System Configuration
            <button className="btn btn-primary btn-sm" onClick={saveSystemConfig} disabled={saving}>
              <Save size={14} /> {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
          <div className="card-content">
            <h4>Voucher Numbering</h4>
            <div className="form-row" style={{ marginTop: '8px' }}>
              <label className="checkbox-label">
                <input type="checkbox" checked={systemConfig.voucher_numbering?.auto_generate || false}
                  onChange={e => setSystemConfig({
                    ...systemConfig,
                    voucher_numbering: {...systemConfig.voucher_numbering, auto_generate: e.target.checked}
                  })} />
                Auto-generate voucher numbers
              </label>
              <label className="checkbox-label">
                <input type="checkbox" checked={systemConfig.voucher_numbering?.prefix_with_branch || false}
                  onChange={e => setSystemConfig({
                    ...systemConfig,
                    voucher_numbering: {...systemConfig.voucher_numbering, prefix_with_branch: e.target.checked}
                  })} />
                Include branch code in prefix
              </label>
              <label className="checkbox-label">
                <input type="checkbox" checked={systemConfig.voucher_numbering?.reset_on_fy || false}
                  onChange={e => setSystemConfig({
                    ...systemConfig,
                    voucher_numbering: {...systemConfig.voucher_numbering, reset_on_fy: e.target.checked}
                  })} />
                Reset numbering on new financial year
              </label>
            </div>

            <h4 style={{ marginTop: '20px' }}>Stock Settings</h4>
            <div className="form-row" style={{ marginTop: '8px' }}>
              <div className="form-group" style={{ maxWidth: '200px' }}>
                <label className="form-label">Valuation Method</label>
                <select className="form-control" value={systemConfig.stock_settings?.valuation_method || 'FIFO'}
                  onChange={e => setSystemConfig({
                    ...systemConfig,
                    stock_settings: {...systemConfig.stock_settings, valuation_method: e.target.value}
                  })}>
                  <option value="FIFO">FIFO (First In First Out)</option>
                  <option value="LIFO">LIFO (Last In First Out)</option>
                  <option value="AVERAGE">Average Cost</option>
                </select>
              </div>
              <label className="checkbox-label">
                <input type="checkbox" checked={systemConfig.stock_settings?.allow_negative_stock || false}
                  onChange={e => setSystemConfig({
                    ...systemConfig,
                    stock_settings: {...systemConfig.stock_settings, allow_negative_stock: e.target.checked}
                  })} />
                Allow negative stock
              </label>
              <label className="checkbox-label">
                <input type="checkbox" checked={systemConfig.stock_settings?.track_batch_expiry || false}
                  onChange={e => setSystemConfig({
                    ...systemConfig,
                    stock_settings: {...systemConfig.stock_settings, track_batch_expiry: e.target.checked}
                  })} />
                Track batch expiry dates
              </label>
            </div>

            <h4 style={{ marginTop: '20px' }}>GST Settings</h4>
            <div className="form-row" style={{ marginTop: '8px' }}>
              <div className="form-group" style={{ maxWidth: '200px' }}>
                <label className="form-label">Default Tax Type</label>
                <select className="form-control" value={systemConfig.gst_settings?.default_tax_type || 'intra'}
                  onChange={e => setSystemConfig({
                    ...systemConfig,
                    gst_settings: {...systemConfig.gst_settings, default_tax_type: e.target.value}
                  })}>
                  <option value="intra">Intra-State (CGST+SGST)</option>
                  <option value="inter">Inter-State (IGST)</option>
                </select>
              </div>
              <label className="checkbox-label">
                <input type="checkbox" checked={systemConfig.gst_settings?.enable_eway_bill || false}
                  onChange={e => setSystemConfig({
                    ...systemConfig,
                    gst_settings: {...systemConfig.gst_settings, enable_eway_bill: e.target.checked}
                  })} />
                Enable E-Way Bill
              </label>
              <label className="checkbox-label">
                <input type="checkbox" checked={systemConfig.gst_settings?.enable_e_invoice || false}
                  onChange={e => setSystemConfig({
                    ...systemConfig,
                    gst_settings: {...systemConfig.gst_settings, enable_e_invoice: e.target.checked}
                  })} />
                Enable E-Invoice
              </label>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'backup' && (
        <div className="card">
          <div className="card-header">Backup & Maintenance</div>
          <div className="card-content">
            <div className="grid-3" style={{ gap: '20px' }}>
              <div className="stat-card" style={{ cursor: 'pointer' }} onClick={createBackup}>
                <Database size={32} color="var(--primary)" />
                <h3>Create Backup</h3>
                <p>Download complete database backup</p>
              </div>
              <div className="stat-card" style={{ cursor: 'pointer' }} onClick={optimizeDatabase}>
                <Shield size={32} color="var(--success)" />
                <h3>Optimize Database</h3>
                <p>Create indexes for better performance</p>
              </div>
              <div className="stat-card">
                <FileText size={32} color="var(--info)" />
                <h3>System Stats</h3>
                <p>View database statistics</p>
              </div>
            </div>

            <h4 style={{ marginTop: '30px' }}>Database Statistics</h4>
            <div className="grid-4" style={{ marginTop: '12px' }}>
              <div className="mini-stat">
                <span className="label">Branches</span>
                <span className="value">{systemStats.database?.branches || 0}</span>
              </div>
              <div className="mini-stat">
                <span className="label">Ledgers</span>
                <span className="value">{systemStats.database?.ledgers || 0}</span>
              </div>
              <div className="mini-stat">
                <span className="label">Items</span>
                <span className="value">{systemStats.database?.items || 0}</span>
              </div>
              <div className="mini-stat">
                <span className="label">Vouchers</span>
                <span className="value">{systemStats.transactions?.vouchers || 0}</span>
              </div>
              <div className="mini-stat">
                <span className="label">Sales Invoices</span>
                <span className="value">{systemStats.transactions?.sales_invoices || 0}</span>
              </div>
              <div className="mini-stat">
                <span className="label">Purchase Invoices</span>
                <span className="value">{systemStats.transactions?.purchase_invoices || 0}</span>
              </div>
              <div className="mini-stat">
                <span className="label">Data Size</span>
                <span className="value">{systemStats.storage?.data_size_mb || 0} MB</span>
              </div>
              <div className="mini-stat">
                <span className="label">Total Size</span>
                <span className="value">{systemStats.storage?.total_size_mb || 0} MB</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Settings;
