import React, { useState, useEffect } from 'react';
import { LogOut, User, Building2, ChevronDown } from 'lucide-react';
import api from '../services/api';
import './Header.css';

const Header = ({ user, onLogout, currentBranch, onBranchChange }) => {
  const [branches, setBranches] = useState([]);
  const [showBranchDropdown, setShowBranchDropdown] = useState(false);
  const [showUserDropdown, setShowUserDropdown] = useState(false);

  useEffect(() => {
    fetchBranches();
  }, []);

  const fetchBranches = async () => {
    try {
      const response = await api.get('/branches');
      setBranches(response.data);
      
      // Set default branch if not set
      if (!currentBranch && response.data.length > 0) {
        const defaultBranch = response.data.find(b => b.is_head_office) || response.data[0];
        onBranchChange(defaultBranch);
      }
    } catch (error) {
      console.error('Error fetching branches:', error);
    }
  };

  const handleBranchSelect = (branch) => {
    onBranchChange(branch);
    setShowBranchDropdown(false);
  };

  const formatDate = () => {
    const now = new Date();
    const options = { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' };
    return now.toLocaleDateString('en-IN', options);
  };

  return (
    <header className="header" data-testid="header">
      <div className="header-left">
        <div className="date-display">
          {formatDate()}
        </div>
        <div className="financial-year">
          FY: 2025-26
        </div>
      </div>

      <div className="header-right">
        {/* Branch Selector */}
        <div className="branch-selector">
          <button 
            className="branch-btn"
            onClick={() => setShowBranchDropdown(!showBranchDropdown)}
            data-testid="branch-selector"
          >
            <Building2 size={16} />
            <span>{currentBranch?.name || 'Select Branch'}</span>
            <ChevronDown size={14} />
          </button>
          
          {showBranchDropdown && (
            <div className="dropdown-menu branch-dropdown">
              {branches.map(branch => (
                <div
                  key={branch.id}
                  className={`dropdown-item ${currentBranch?.id === branch.id ? 'active' : ''}`}
                  onClick={() => handleBranchSelect(branch)}
                >
                  <span className="branch-code">{branch.code}</span>
                  <span className="branch-name">{branch.name}</span>
                  {branch.is_head_office && <span className="badge badge-info">HO</span>}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* User Menu */}
        <div className="user-menu">
          <button 
            className="user-btn"
            onClick={() => setShowUserDropdown(!showUserDropdown)}
            data-testid="user-menu"
          >
            <User size={16} />
            <span>{user?.full_name || user?.username}</span>
            <ChevronDown size={14} />
          </button>
          
          {showUserDropdown && (
            <div className="dropdown-menu user-dropdown">
              <div className="dropdown-header">
                <div className="user-name">{user?.full_name}</div>
                <div className="user-email">{user?.email}</div>
              </div>
              <div className="dropdown-divider"></div>
              <button 
                className="dropdown-item danger"
                onClick={onLogout}
                data-testid="logout-btn"
              >
                <LogOut size={14} />
                <span>Logout</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Click outside handler */}
      {(showBranchDropdown || showUserDropdown) && (
        <div 
          className="dropdown-backdrop"
          onClick={() => {
            setShowBranchDropdown(false);
            setShowUserDropdown(false);
          }}
        />
      )}
    </header>
  );
};

export default Header;
