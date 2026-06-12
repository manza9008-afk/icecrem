import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
<<<<<<< HEAD
  Building2,
  TrendingUp,
  Package, 
  AlertTriangle,
  FileText,
  TrendingDown
=======
  TrendingUp, 
  TrendingDown, 
  Package, 
  AlertTriangle,
  IndianRupee,
  ShoppingCart,
  FileText,
  Users
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68
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

<<<<<<< HEAD
  const inventoryActivity = recentActivity
    .filter((activity) => activity.type === 'purchase')
    .map((activity) => ({
      ...activity,
      description: activity.description.replace('Purchase Invoice', 'Inventory In')
    }));

=======
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68
  return (
    <div className="dashboard" data-testid="dashboard">
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p className="page-subtitle">
<<<<<<< HEAD
            {currentBranch?.name || 'All Branches'} - Inventory overview
=======
            {currentBranch?.name || 'All Branches'} - Overview
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68
          </p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card">
<<<<<<< HEAD
          <div className="stat-icon" style={{ background: '#fff7ed' }}>
            <Package size={24} color="#ea580c" />
          </div>
          <div>
            <div className="stat-label">Today's Inventory In</div>
=======
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
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68
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
<<<<<<< HEAD
          <div className="stat-icon" style={{ background: '#ebf8ff' }}>
            <TrendingDown size={24} color="#3182ce" />
          </div>
          <div>
            <div className="stat-label">Recent In Entries</div>
            <div className="stat-value">{inventoryActivity.length}</div>
=======
          <div className="stat-icon" style={{ background: '#e9d8fd' }}>
            <Users size={24} color="#805ad5" />
          </div>
          <div>
            <div className="stat-label">Outstanding Receivables</div>
            <div className="stat-value">{formatCurrency(stats?.outstanding_receivables || 0)}</div>
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68
          </div>
        </div>

        <div className="stat-card">
<<<<<<< HEAD
          <div className="stat-icon" style={{ background: '#e6fffa' }}>
            <Building2 size={24} color="#38a169" />
          </div>
          <div>
            <div className="stat-label">Current Branch</div>
            <div className="stat-value">{currentBranch?.name || 'All Branches'}</div>
=======
          <div className="stat-icon" style={{ background: '#c6f6d5' }}>
            <ShoppingCart size={24} color="#2f855a" />
          </div>
          <div>
            <div className="stat-label">Pending Orders</div>
            <div className="stat-value">{stats?.pending_orders || 0}</div>
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68
          </div>
        </div>
      </div>

      <div className="grid-2">
        {/* Quick Actions */}
        <div className="card">
          <div className="card-header">Quick Actions</div>
          <div className="card-content quick-actions">
<<<<<<< HEAD
            <Link to="/purchase/invoice" className="quick-action-btn">
              <Package size={20} />
              <span>Inventory In</span>
            </Link>
            <Link to="/inventory/ledger" className="quick-action-btn">
              <TrendingUp size={20} />
              <span>Inventory In / Out</span>
            </Link>
            <Link to="/inventory/stock" className="quick-action-btn">
              <Package size={20} />
              <span>Ready Stock</span>
            </Link>
            <Link to="/inventory/adjustment" className="quick-action-btn">
              <AlertTriangle size={20} />
              <span>Stock Maintenance</span>
            </Link>
            <Link to="/masters/items" className="quick-action-btn">
              <FileText size={20} />
              <span>Items</span>
            </Link>
            <Link to="/purchase/history" className="quick-action-btn">
              <TrendingDown size={20} />
              <span>In History</span>
=======
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
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68
            </Link>
          </div>
        </div>

<<<<<<< HEAD
        {/* Recent Inventory Activity */}
        <div className="card">
          <div className="card-header">Recent Inventory In</div>
          <div className="card-content">
            {inventoryActivity.length === 0 ? (
              <div className="empty-state">
                <p>No inventory in activity</p>
              </div>
            ) : (
              <div className="activity-list">
                {inventoryActivity.map((activity, index) => (
                  <div key={index} className="activity-item">
                    <div className="activity-icon purchase">
                      <Package size={14} />
=======
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
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68
                    </div>
                    <div className="activity-content">
                      <div className="activity-desc">{activity.description}</div>
                      <div className="activity-meta">
<<<<<<< HEAD
                        <span className="amount purchase">
=======
                        <span className={`amount ${activity.type}`}>
>>>>>>> f709e2d3170230ace218f088f0c7a65d0a20ad68
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
