import React, { useState, useEffect, useCallback, Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';

// Layouts
import Sidebar from './components/Sidebar';
import Header from './components/Header';

// Pages
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';

// Masters
const BranchMaster = lazy(() => import('./pages/Masters/BranchMaster'));
const GodownMaster = lazy(() => import('./pages/Masters/GodownMaster'));
const AccountGroups = lazy(() => import('./pages/Masters/AccountGroups'));
const LedgerMaster = lazy(() => import('./pages/Masters/LedgerMaster'));
const ItemMaster = lazy(() => import('./pages/Masters/ItemMaster'));
const CustomerMaster = lazy(() => import('./pages/Masters/CustomerMaster'));
const SupplierMaster = lazy(() => import('./pages/Masters/SupplierMaster'));

// Accounting
const VoucherEntry = lazy(() => import('./pages/Accounting/VoucherEntry'));
const VoucherList = lazy(() => import('./pages/Accounting/VoucherList'));

// Sales
const Quotation = lazy(() => import('./pages/Sales/Quotation'));
const SalesOrder = lazy(() => import('./pages/Sales/SalesOrder'));
const SalesInvoice = lazy(() => import('./pages/Sales/SalesInvoice'));
const SalesHistory = lazy(() => import('./pages/Sales/SalesHistory'));

// Purchase
const PurchaseOrder = lazy(() => import('./pages/Purchase/PurchaseOrder'));
const PurchaseInvoice = lazy(() => import('./pages/Purchase/PurchaseInvoice'));
const PurchaseHistory = lazy(() => import('./pages/Purchase/PurchaseHistory'));

// Inventory
const StockSummary = lazy(() => import('./pages/Inventory/StockSummary'));
const StockLedger = lazy(() => import('./pages/Inventory/StockLedger'));
const StockTransfer = lazy(() => import('./pages/Inventory/StockTransfer'));
const StockAdjustment = lazy(() => import('./pages/Inventory/StockAdjustment'));
const StockOutEntry = lazy(() => import('./pages/Inventory/StockOutEntry'));
const StockOutHistory = lazy(() => import('./pages/Inventory/StockOutHistory'));

// Reports
const TrialBalance = lazy(() => import('./pages/Reports/TrialBalance'));
const ProfitLoss = lazy(() => import('./pages/Reports/ProfitLoss'));
const BalanceSheet = lazy(() => import('./pages/Reports/BalanceSheet'));
const DayBook = lazy(() => import('./pages/Reports/DayBook'));
const LedgerStatement = lazy(() => import('./pages/Reports/LedgerStatement'));
const RatioAnalysis = lazy(() => import('./pages/Reports/RatioAnalysis'));
const OutstandingReport = lazy(() => import('./pages/Reports/OutstandingReport'));

// GST
const GSTR1Report = lazy(() => import('./pages/GST/GSTR1Report'));
const GSTR3BReport = lazy(() => import('./pages/GST/GSTR3BReport'));
const HSNSummary = lazy(() => import('./pages/GST/HSNSummary'));
const TaxLiability = lazy(() => import('./pages/GST/TaxLiability'));

// Settings
const Settings = lazy(() => import('./pages/Settings/Settings'));
const UserManagement = lazy(() => import('./pages/Settings/UserManagement'));
const AuditLogs = lazy(() => import('./pages/Settings/AuditLogs'));

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
            <Suspense fallback={<div className="loading-container"><div className="spinner"></div></div>}>
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
              <Route path="/inventory/stock-ledger" element={<StockLedger currentBranch={currentBranch} showDate={true} />} />
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
            </Suspense>
          </div>
        </div>
      </div>
    </Router>
  );
}

export default App;
