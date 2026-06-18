import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';

// Layouts
import Sidebar from './components/Sidebar';
import Header from './components/Header';

// Pages
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';

// Masters
import BranchMaster from './pages/Masters/BranchMaster';
import GodownMaster from './pages/Masters/GodownMaster';
import AccountGroups from './pages/Masters/AccountGroups';
import LedgerMaster from './pages/Masters/LedgerMaster';
import ItemMaster from './pages/Masters/ItemMaster';
import CustomerMaster from './pages/Masters/CustomerMaster';
import SupplierMaster from './pages/Masters/SupplierMaster';

// Accounting
import VoucherEntry from './pages/Accounting/VoucherEntry';
import VoucherList from './pages/Accounting/VoucherList';

// Sales
import Quotation from './pages/Sales/Quotation';
import SalesOrder from './pages/Sales/SalesOrder';
import SalesInvoice from './pages/Sales/SalesInvoice';
import SalesHistory from './pages/Sales/SalesHistory';

// Purchase
import PurchaseOrder from './pages/Purchase/PurchaseOrder';
import PurchaseInvoice from './pages/Purchase/PurchaseInvoice';
import PurchaseHistory from './pages/Purchase/PurchaseHistory';

// Inventory
import StockSummary from './pages/Inventory/StockSummary';
import StockLedger from './pages/Inventory/StockLedger';
import StockTransfer from './pages/Inventory/StockTransfer';
import StockAdjustment from './pages/Inventory/StockAdjustment';
import StockOutEntry from './pages/Inventory/StockOutEntry';
import StockOutHistory from './pages/Inventory/StockOutHistory';

// Reports
import TrialBalance from './pages/Reports/TrialBalance';
import ProfitLoss from './pages/Reports/ProfitLoss';
import BalanceSheet from './pages/Reports/BalanceSheet';
import DayBook from './pages/Reports/DayBook';
import LedgerStatement from './pages/Reports/LedgerStatement';
import RatioAnalysis from './pages/Reports/RatioAnalysis';
import OutstandingReport from './pages/Reports/OutstandingReport';

// GST
import GSTR1Report from './pages/GST/GSTR1Report';
import GSTR3BReport from './pages/GST/GSTR3BReport';
import HSNSummary from './pages/GST/HSNSummary';
import TaxLiability from './pages/GST/TaxLiability';

// Settings
import Settings from './pages/Settings/Settings';
import UserManagement from './pages/Settings/UserManagement';
import AuditLogs from './pages/Settings/AuditLogs';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [currentBranch, setCurrentBranch] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('user');
    const branchData = localStorage.getItem('currentBranch');
    
    if (token && userData) {
      setIsAuthenticated(true);
      setUser(JSON.parse(userData));
      if (branchData) {
        setCurrentBranch(JSON.parse(branchData));
      }
    }
  }, []);

  const handleLogin = useCallback((token, userData) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(userData));
    setIsAuthenticated(true);
    setUser(userData);
  }, []);

  const handleLogout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('currentBranch');
    setIsAuthenticated(false);
    setUser(null);
    setCurrentBranch(null);
  }, []);

  const handleBranchChange = useCallback((branch) => {
    localStorage.setItem('currentBranch', JSON.stringify(branch));
    setCurrentBranch(branch);
  }, []);

  if (!isAuthenticated) {
    return (
      <Router>
        <Routes>
          <Route path="/login" element={<Login onLogin={handleLogin} />} />
          <Route path="*" element={<Navigate to="/login" />} />
        </Routes>
      </Router>
    );
  }

  return (
    <Router>
      <div className="app-layout">
        <Sidebar 
          collapsed={sidebarCollapsed} 
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} 
        />
        <div className={`main-content ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
          <Header 
            user={user} 
            onLogout={handleLogout} 
            currentBranch={currentBranch}
            onBranchChange={handleBranchChange}
          />
          <div className="page-container">
            <Routes>
              <Route path="/" element={<Dashboard currentBranch={currentBranch} />} />
              
              {/* Masters */}
              <Route path="/masters/branches" element={<BranchMaster />} />
              <Route path="/masters/godowns" element={<GodownMaster currentBranch={currentBranch} />} />
              <Route path="/masters/account-groups" element={<AccountGroups />} />
              <Route path="/masters/ledgers" element={<LedgerMaster currentBranch={currentBranch} />} />
              <Route path="/masters/items" element={<ItemMaster />} />
              <Route path="/masters/customers" element={<CustomerMaster />} />
              <Route path="/masters/suppliers" element={<SupplierMaster />} />
              <Route path="/masters/stock-maintenance" element={<StockAdjustment currentBranch={currentBranch} />} />
              <Route path="/masters/stock-out-entry" element={<StockOutEntry currentBranch={currentBranch} />} />
              
              {/* Accounting */}
              <Route path="/accounting/voucher" element={<VoucherEntry currentBranch={currentBranch} />} />
              <Route path="/accounting/voucher/:type" element={<VoucherEntry currentBranch={currentBranch} />} />
              <Route path="/accounting/vouchers" element={<VoucherList currentBranch={currentBranch} />} />
              
              {/* Sales */}
              <Route path="/sales/quotation" element={<Quotation currentBranch={currentBranch} />} />
              <Route path="/sales/order" element={<SalesOrder currentBranch={currentBranch} />} />
              <Route path="/sales/invoice" element={<SalesInvoice currentBranch={currentBranch} />} />
              <Route path="/sales/invoice/:type" element={<SalesInvoice currentBranch={currentBranch} />} />
              <Route path="/sales/history" element={<SalesHistory currentBranch={currentBranch} />} />
              
              {/* Purchase */}
              <Route path="/purchase/order" element={<PurchaseOrder currentBranch={currentBranch} />} />
              <Route path="/purchase/invoice" element={<PurchaseInvoice currentBranch={currentBranch} />} />
              <Route path="/purchase/history" element={<PurchaseHistory currentBranch={currentBranch} />} />
              
              {/* Inventory */}
              <Route path="/inventory/stock" element={<StockSummary currentBranch={currentBranch} />} />
              <Route path="/inventory/ledger" element={<StockLedger currentBranch={currentBranch} />} />
              <Route path="/inventory/out-entry" element={<StockOutEntry currentBranch={currentBranch} />} />
              <Route path="/inventory/out-history" element={<StockOutHistory currentBranch={currentBranch} />} />
              <Route path="/inventory/transfer" element={<StockTransfer currentBranch={currentBranch} />} />
              <Route path="/inventory/adjustment" element={<StockAdjustment currentBranch={currentBranch} />} />
              
              {/* Reports */}
              <Route path="/reports/trial-balance" element={<TrialBalance currentBranch={currentBranch} />} />
              <Route path="/reports/profit-loss" element={<ProfitLoss currentBranch={currentBranch} />} />
              <Route path="/reports/balance-sheet" element={<BalanceSheet currentBranch={currentBranch} />} />
              <Route path="/reports/day-book" element={<DayBook currentBranch={currentBranch} />} />
              <Route path="/reports/ledger-statement" element={<LedgerStatement currentBranch={currentBranch} />} />
              <Route path="/reports/ratio-analysis" element={<RatioAnalysis currentBranch={currentBranch} />} />
              <Route path="/reports/outstanding" element={<OutstandingReport currentBranch={currentBranch} />} />
              
              {/* GST */}
              <Route path="/gst/gstr1" element={<GSTR1Report currentBranch={currentBranch} />} />
              <Route path="/gst/gstr3b" element={<GSTR3BReport currentBranch={currentBranch} />} />
              <Route path="/gst/hsn-summary" element={<HSNSummary currentBranch={currentBranch} />} />
              <Route path="/gst/tax-liability" element={<TaxLiability currentBranch={currentBranch} />} />
              
              {/* Settings */}
              <Route path="/settings" element={<Settings currentBranch={currentBranch} />} />
              <Route path="/settings/users" element={<UserManagement currentBranch={currentBranch} />} />
              <Route path="/settings/audit-logs" element={<AuditLogs currentBranch={currentBranch} />} />
              
              <Route path="*" element={<Navigate to="/" />} />
            </Routes>
          </div>
        </div>
      </div>
    </Router>
  );
}

export default App;
