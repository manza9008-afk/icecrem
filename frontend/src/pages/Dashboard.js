import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  TrendingUp, 
  TrendingDown, 
  Package, 
  AlertTriangle,
  IndianRupee,
  ShoppingCart,
  FileText,
  Users
} from 'lucide-react';
import api, { formatCurrency } from '../services/api';
import './Dashboard.css';

const Dashboard = ({ currentBranch }) => {
  const [stats, setStats] = useState(null);
  const [recentActivity, setRecentActivity] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, [currentBranch]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const branchParam = currentBranch?.id ? `?branch_id=${currentBranch.id}` : '';
      
      const [statsRes, activityRes] = await Promise.all([
        api.get(`/dashboard/stats${branchParam}`),
        api.get('/dashboard/recent-activity')
      ]);
      
      setStats(statsRes.data);
      setRecentActivity(activityRes.data);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="dashboard" data-testid="dashboard">
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p className="page-subtitle">
            {currentBranch?.name || 'All Branches'} - Overview
          </p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#e6fffa' }}>
            <TrendingUp size={24} color="#38a169" />
          </div>
          <div>
            <div className="stat-label">Today's Sales</div>
            <div className="stat-value">{formatCurrency(stats?.today_sales || 0)}</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#ebf8ff' }}>
            <IndianRupee size={24} color="#3182ce" />
          </div>
          <div>
            <div className="stat-label">Monthly Sales</div>
            <div className="stat-value">{formatCurrency(stats?.monthly_sales || 0)}</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#fef3c7' }}>
            <TrendingDown size={24} color="#d69e2e" />
          </div>
          <div>
            <div className="stat-label">Today's Purchases</div>
            <div className="stat-value">{formatCurrency(stats?.today_purchases || 0)}</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#fed7d7' }}>
            <AlertTriangle size={24} color="#e53e3e" />
          </div>
          <div>
            <div className="stat-label">Low Stock Items</div>
            <div className="stat-value">{stats?.low_stock_items || 0}</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#e9d8fd' }}>
            <Users size={24} color="#805ad5" />
          </div>
          <div>
            <div className="stat-label">Outstanding Receivables</div>
            <div className="stat-value">{formatCurrency(stats?.outstanding_receivables || 0)}</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#c6f6d5' }}>
            <ShoppingCart size={24} color="#2f855a" />
          </div>
          <div>
            <div className="stat-label">Pending Orders</div>
            <div className="stat-value">{stats?.pending_orders || 0}</div>
          </div>
        </div>
      </div>

      <div className="grid-2">
        {/* Quick Actions */}
        <div className="card">
          <div className="card-header">Quick Actions</div>
          <div className="card-content quick-actions">
            <Link to="/sales/invoice/gst" className="quick-action-btn">
              <FileText size={20} />
              <span>New GST Invoice</span>
            </Link>
            <Link to="/purchase/invoice" className="quick-action-btn">
              <Package size={20} />
              <span>Purchase Entry</span>
            </Link>
            <Link to="/accounting/voucher/receipt" className="quick-action-btn">
              <IndianRupee size={20} />
              <span>Receipt Voucher</span>
            </Link>
            <Link to="/accounting/voucher/payment" className="quick-action-btn">
              <TrendingDown size={20} />
              <span>Payment Voucher</span>
            </Link>
            <Link to="/inventory/stock" className="quick-action-btn">
              <Package size={20} />
              <span>Stock Summary</span>
            </Link>
            <Link to="/reports/trial-balance" className="quick-action-btn">
              <FileText size={20} />
              <span>Trial Balance</span>
            </Link>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="card">
          <div className="card-header">Recent Activity</div>
          <div className="card-content">
            {recentActivity.length === 0 ? (
              <div className="empty-state">
                <p>No recent activity</p>
              </div>
            ) : (
              <div className="activity-list">
                {recentActivity.map((activity, index) => (
                  <div key={index} className="activity-item">
                    <div className={`activity-icon ${activity.type}`}>
                      {activity.type === 'sales' ? (
                        <TrendingUp size={14} />
                      ) : (
                        <TrendingDown size={14} />
                      )}
                    </div>
                    <div className="activity-content">
                      <div className="activity-desc">{activity.description}</div>
                      <div className="activity-meta">
                        <span className={`amount ${activity.type}`}>
                          {formatCurrency(activity.amount)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
