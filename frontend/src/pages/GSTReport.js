import React, { useState } from 'react';
import { Download } from 'lucide-react';
import api from '../services/api';
import { toast } from 'sonner';

const GSTReport = () => {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    if (!startDate || !endDate) {
      toast.error('Please select date range');
      return;
    }

    setLoading(true);
    try {
      const response = await api.get(`/reports/gst-summary?start_date=${startDate}&end_date=${endDate}`);
      setReport(response.data);
    } catch (error) {
      toast.error('Failed to generate report');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="gst-report-page">
      <div className="page-header">
        <div>
          <h1>GST Report</h1>
          <p className="page-subtitle">GST summary and returns</p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '16px' }}>
        <div className="card-header">
          <h3>Generate Report</h3>
        </div>
        <div className="card-content">
          <div className="grid grid-3">
            <div className="form-group">
              <label>Start Date</label>
              <input 
                type="date" 
                value={startDate} 
                onChange={(e) => setStartDate(e.target.value)}
                data-testid="gst-start-date"
              />
            </div>
            <div className="form-group">
              <label>End Date</label>
              <input 
                type="date" 
                value={endDate} 
                onChange={(e) => setEndDate(e.target.value)}
                data-testid="gst-end-date"
              />
            </div>
            <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end' }}>
              <button 
                className="btn btn-primary" 
                onClick={handleGenerate} 
                disabled={loading}
                data-testid="generate-gst-report-btn"
              >
                {loading ? 'Generating...' : 'Generate Report'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {report && (
        <div className="grid grid-3">
          <div className="card">
            <div className="card-content">
              <div className="stat-label">Total Sales</div>
              <div className="stat-value data-value">₹{report.total_sales.toFixed(2)}</div>
            </div>
          </div>
          <div className="card">
            <div className="card-content">
              <div className="stat-label">Total Tax Collected</div>
              <div className="stat-value data-value">₹{report.total_tax_collected.toFixed(2)}</div>
            </div>
          </div>
          <div className="card">
            <div className="card-content">
              <div className="stat-label">Invoices Count</div>
              <div className="stat-value data-value">{report.invoices_count}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GSTReport;
