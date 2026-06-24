import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Building2,
  Package, 
  Users, 
  Truck, 
  FileText,
  BookOpen,
  BarChart3,
  Receipt,
  Settings,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Warehouse,
  CreditCard,
  FileSpreadsheet,
  Calculator,
  IndianRupee
} from 'lucide-react';
import './Sidebar.css';

const Sidebar = ({ collapsed, onToggle }) => {
  const location = useLocation();
  const [expandedMenus, setExpandedMenus] = useState({});

  const menuItems = [
    { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
    { 
      icon: Building2, 
      label: 'Masters', 
      children: [
        { label: 'Branches', path: '/masters/branches' },
        { label: 'Godowns', path: '/masters/godowns' },
        { label: 'Account Groups', path: '/masters/account-groups' },
        { label: 'Ledgers', path: '/masters/ledgers' },
        { label: 'Items', path: '/masters/items' },
        { label: 'Customers', path: '/masters/customers' },
        { label: 'Suppliers', path: '/masters/suppliers' },
        { label: 'Stock Maintenance', path: '/masters/stock-maintenance' },
        { label: 'Out Qty', path: '/masters/stock-out-entry' },
      ]
    },
    { 
      icon: BookOpen, 
      label: 'Accounting', 
      children: [
        { label: 'Journal Entry', path: '/accounting/voucher/journal' },
        { label: 'Payment', path: '/accounting/voucher/payment' },
        { label: 'Receipt', path: '/accounting/voucher/receipt' },
        { label: 'Contra', path: '/accounting/voucher/contra' },
        { label: 'View Vouchers', path: '/accounting/vouchers' },
      ]
    },
    // { 
    //   icon: Receipt, 
    //   label: 'Sales', 
    //   children: [
    //     { label: 'Quotation', path: '/sales/quotation' },
    //     { label: 'Sales Order', path: '/sales/order' },
    //     { label: 'GST Invoice', path: '/sales/invoice/gst' },
    //     { label: 'Kacha Bill', path: '/sales/invoice/kacha' },
    //     { label: 'Sales History', path: '/sales/history' },
    //   ]
    // },
    { 
      icon: Truck, 
      label: 'Purchase', 
      children: [
        { label: 'Purchase Order', path: '/purchase/order' },
        { label: 'Item In', path: '/purchase/invoice' },
        { label: 'In History', path: '/purchase/history' },
      ]
    },
    { 
      icon: Warehouse, 
      label: 'Inventory', 
      children: [
        { label: 'Out Entry', path: '/inventory/out-entry' },
        { label: 'Out History', path: '/inventory/out-history' },
        { label: 'Inventory In / Out', path: '/inventory/ledger' },
        { label: 'Ready Stock', path: '/inventory/stock' },
        { label: 'Stock Maintenance', path: '/inventory/adjustment' },
        { label: 'Stock Transfer', path: '/inventory/transfer' },
      ]
    },
    { 
      icon: BarChart3, 
      label: 'Reports', 
      children: [
        { label: 'Trial Balance', path: '/reports/trial-balance' },
        { label: 'Profit & Loss', path: '/reports/profit-loss' },
        { label: 'Balance Sheet', path: '/reports/balance-sheet' },
        { label: 'Day Book', path: '/reports/day-book' },
        { label: 'Ledger Statement', path: '/reports/ledger-statement' },
        { label: 'Outstanding & Aging', path: '/reports/outstanding' },
        { label: 'Ratio Analysis', path: '/reports/ratio-analysis' },
      ]
    },
    { 
      icon: IndianRupee, 
      label: 'GST', 
      children: [
        { label: 'GSTR-1', path: '/gst/gstr1' },
        { label: 'GSTR-3B', path: '/gst/gstr3b' },
        { label: 'HSN Summary', path: '/gst/hsn-summary' },
        { label: 'Tax Liability', path: '/gst/tax-liability' },
      ]
    },
    { 
      icon: Settings, 
      label: 'Settings', 
      children: [
        { label: 'Company', path: '/settings' },
        { label: 'Users & Roles', path: '/settings/users' },
        { label: 'Audit Logs', path: '/settings/audit-logs' },
      ]
    },
  ];

  const toggleMenu = (label) => {
    setExpandedMenus(prev => ({
      ...prev,
      [label]: !prev[label]
    }));
  };

  const isActiveParent = (children) => {
    return children?.some(child => location.pathname.startsWith(child.path));
  };

  useEffect(() => {
    // Auto-expand parent menu based on current path
    menuItems.forEach(item => {
      if (item.children && isActiveParent(item.children)) {
        setExpandedMenus(prev => ({ ...prev, [item.label]: true }));
      }
    });
  }, [location.pathname]);

  return (
    <div className={`sidebar ${collapsed ? 'collapsed' : ''}`} data-testid="sidebar">
      <div className="sidebar-header">
        {!collapsed && (
          <div className="logo-section">
            <div className="company-logo">H</div>
            <div className="company-info">
              <div className="company-name">HOOREN ERP</div>
              <div className="company-tagline">Food Products</div>
            </div>
          </div>
        )}
        <button 
          className="toggle-btn" 
          onClick={onToggle}
          data-testid="sidebar-toggle"
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      <nav className="sidebar-nav">
        {menuItems.map((item, idx) => (
          <div key={idx} className="nav-group">
            {item.path ? (
              <Link 
                to={item.path} 
                className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
                data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
                title={collapsed ? item.label : ''}
              >
                <item.icon size={18} />
                {!collapsed && <span>{item.label}</span>}
              </Link>
            ) : (
              <>
                <div 
                  className={`nav-item nav-parent ${isActiveParent(item.children) ? 'active-parent' : ''}`}
                  onClick={() => !collapsed && toggleMenu(item.label)}
                  data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
                  title={collapsed ? item.label : ''}
                >
                  <item.icon size={18} />
                  {!collapsed && (
                    <>
                      <span>{item.label}</span>
                      <span className="expand-icon">
                        {expandedMenus[item.label] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </span>
                    </>
                  )}
                </div>
                {!collapsed && expandedMenus[item.label] && item.children && (
                  <div className="nav-children">
                    {item.children.map((child, childIdx) => (
                      <Link
                        key={childIdx}
                        to={child.path}
                        className={`nav-child ${location.pathname === child.path ? 'active' : ''}`}
                        data-testid={`nav-${child.label.toLowerCase().replace(/\s+/g, '-')}`}
                      >
                        {child.label}
                      </Link>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        {!collapsed && (
          <div className="footer-info">
            <span>v1.0.0</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default Sidebar;
