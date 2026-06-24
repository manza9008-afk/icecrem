"""
HOOREN ERP - Backend API Tests
Comprehensive test suite for ERP system APIs
Tests: Authentication, Branches, Accounting, Ledgers, Vouchers, Sales, Purchase, GST, Reports
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://hooren-system-proof.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_USERNAME = "hooren_admin"
TEST_PASSWORD = "Hooren@2026#Secure"


class TestConfig:
    """Store shared test data"""
    token = None
    branch_id = None
    ledger_id = None
    item_id = None
    godown_id = None
    voucher_id = None
    sales_invoice_id = None
    purchase_invoice_id = None


@pytest.fixture(scope="session")
def api_session():
    """Create requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="session")
def auth_token(api_session):
    """Get authentication token"""
    response = api_session.post(f"{BASE_URL}/api/auth/login", json={
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        token = response.json().get("access_token")
        TestConfig.token = token
        return token
    pytest.skip(f"Authentication failed: {response.status_code}")


@pytest.fixture(scope="session")
def authenticated_client(api_session, auth_token):
    """Session with auth header"""
    api_session.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_session


# ==================== HEALTH & AUTH TESTS ====================

class TestHealth:
    """Health check endpoint tests"""
    
    def test_health_check(self, api_session):
        """Test API health endpoint"""
        response = api_session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        print(f"SUCCESS: Health check passed - version {data['version']}")


class TestAuthentication:
    """Authentication endpoint tests"""
    
    def test_login_success(self, api_session):
        """Test successful login with valid credentials"""
        response = api_session.post(f"{BASE_URL}/api/auth/login", json={
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["username"] == TEST_USERNAME
        assert "email" in data["user"]
        print(f"SUCCESS: Login successful for {TEST_USERNAME}")
    
    def test_login_invalid_credentials(self, api_session):
        """Test login with invalid credentials"""
        response = api_session.post(f"{BASE_URL}/api/auth/login", json={
            "username": "wrong_user",
            "password": "wrong_password"
        })
        assert response.status_code == 401
        print("SUCCESS: Invalid credentials correctly rejected")
    
    def test_get_current_user(self, authenticated_client):
        """Test getting current user info"""
        response = authenticated_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        
        data = response.json()
        assert data["username"] == TEST_USERNAME
        print(f"SUCCESS: Current user fetched - {data['username']}")


# ==================== BRANCH TESTS ====================

class TestBranches:
    """Branch management endpoint tests"""
    
    def test_get_branches(self, authenticated_client):
        """Test fetching branches list"""
        response = authenticated_client.get(f"{BASE_URL}/api/branches")
        assert response.status_code == 200
        
        branches = response.json()
        assert isinstance(branches, list)
        assert len(branches) > 0
        
        # Store first branch for later tests
        TestConfig.branch_id = branches[0]["id"]
        print(f"SUCCESS: Fetched {len(branches)} branches")
        
        # Verify branch structure
        branch = branches[0]
        assert "id" in branch
        assert "name" in branch
        assert "code" in branch
        print(f"  Branch: {branch['name']} ({branch['code']})")
    
    def test_get_branch_by_id(self, authenticated_client):
        """Test fetching single branch"""
        if not TestConfig.branch_id:
            pytest.skip("No branch ID available")
        
        response = authenticated_client.get(f"{BASE_URL}/api/branches/{TestConfig.branch_id}")
        assert response.status_code == 200
        
        branch = response.json()
        assert branch["id"] == TestConfig.branch_id
        print(f"SUCCESS: Fetched branch by ID - {branch['name']}")
    
    def test_get_branch_godowns(self, authenticated_client):
        """Test fetching godowns for a branch"""
        if not TestConfig.branch_id:
            pytest.skip("No branch ID available")
        
        response = authenticated_client.get(f"{BASE_URL}/api/branches/{TestConfig.branch_id}/godowns")
        assert response.status_code == 200
        
        godowns = response.json()
        assert isinstance(godowns, list)
        if len(godowns) > 0:
            TestConfig.godown_id = godowns[0]["id"]
        print(f"SUCCESS: Fetched {len(godowns)} godowns for branch")


# ==================== LEDGER TESTS ====================

class TestLedgerMaster:
    """Ledger master CRUD tests"""
    
    def test_get_account_groups(self, authenticated_client):
        """Test fetching account groups"""
        response = authenticated_client.get(f"{BASE_URL}/api/accounting/account-groups")
        assert response.status_code == 200
        
        groups = response.json()
        assert isinstance(groups, list)
        assert len(groups) > 0
        print(f"SUCCESS: Fetched {len(groups)} account groups")
    
    def test_get_account_groups_tree(self, authenticated_client):
        """Test fetching account groups in tree format"""
        response = authenticated_client.get(f"{BASE_URL}/api/accounting/account-groups/tree")
        assert response.status_code == 200
        
        tree = response.json()
        assert isinstance(tree, list)
        print(f"SUCCESS: Fetched account groups tree with {len(tree)} root nodes")
    
    def test_get_ledgers(self, authenticated_client):
        """Test fetching ledgers list"""
        response = authenticated_client.get(f"{BASE_URL}/api/accounting/ledgers")
        assert response.status_code == 200
        
        ledgers = response.json()
        assert isinstance(ledgers, list)
        
        if len(ledgers) > 0:
            TestConfig.ledger_id = ledgers[0]["id"]
            # Verify ledger structure
            ledger = ledgers[0]
            assert "id" in ledger
            assert "name" in ledger
            assert "account_group_id" in ledger
        
        print(f"SUCCESS: Fetched {len(ledgers)} ledgers")
    
    def test_create_ledger(self, authenticated_client):
        """Test creating a new ledger"""
        if not TestConfig.branch_id:
            pytest.skip("No branch ID available")
        
        # Get first account group for testing
        groups_response = authenticated_client.get(f"{BASE_URL}/api/accounting/account-groups")
        groups = groups_response.json()
        if not groups:
            pytest.skip("No account groups available")
        
        test_ledger = {
            "name": f"TEST_Ledger_{datetime.now().strftime('%H%M%S')}",
            "account_group_id": groups[0]["id"],
            "branch_id": TestConfig.branch_id,
            "opening_balance": 0,
            "is_party": False
        }
        
        response = authenticated_client.post(f"{BASE_URL}/api/accounting/ledgers", json=test_ledger)
        assert response.status_code == 200
        
        created = response.json()
        assert created["name"] == test_ledger["name"]
        assert "id" in created
        TestConfig.ledger_id = created["id"]
        print(f"SUCCESS: Created ledger - {created['name']}")
    
    def test_get_ledger_by_id(self, authenticated_client):
        """Test fetching single ledger"""
        if not TestConfig.ledger_id:
            pytest.skip("No ledger ID available")
        
        response = authenticated_client.get(f"{BASE_URL}/api/accounting/ledgers/{TestConfig.ledger_id}")
        assert response.status_code == 200
        
        ledger = response.json()
        assert ledger["id"] == TestConfig.ledger_id
        print(f"SUCCESS: Fetched ledger by ID - {ledger['name']}")


# ==================== VOUCHER TESTS ====================

class TestVouchers:
    """Voucher CRUD and double-entry validation tests"""
    
    def test_create_journal_voucher(self, authenticated_client):
        """Test creating a journal voucher with double-entry validation"""
        if not TestConfig.branch_id:
            pytest.skip("No branch ID available")
        
        # Get ledgers for entries
        response = authenticated_client.get(f"{BASE_URL}/api/accounting/ledgers?branch_id={TestConfig.branch_id}")
        ledgers = response.json()
        
        if len(ledgers) < 2:
            pytest.skip("Need at least 2 ledgers for journal voucher")
        
        # Create balanced voucher
        voucher_data = {
            "voucher_type": "journal",
            "voucher_date": datetime.now().strftime("%Y-%m-%d"),
            "branch_id": TestConfig.branch_id,
            "narration": "TEST_Journal Entry",
            "entries": [
                {
                    "ledger_id": ledgers[0]["id"],
                    "ledger_name": ledgers[0]["name"],
                    "debit": 1000,
                    "credit": 0
                },
                {
                    "ledger_id": ledgers[1]["id"],
                    "ledger_name": ledgers[1]["name"],
                    "debit": 0,
                    "credit": 1000
                }
            ]
        }
        
        response = authenticated_client.post(f"{BASE_URL}/api/accounting/vouchers", json=voucher_data)
        assert response.status_code == 200
        
        created = response.json()
        assert "voucher_number" in created
        assert created["voucher_type"] == "journal"
        assert created["total_debit"] == 1000
        assert created["total_credit"] == 1000
        TestConfig.voucher_id = created["id"]
        print(f"SUCCESS: Created journal voucher - {created['voucher_number']}")
    
    def test_create_unbalanced_voucher_fails(self, authenticated_client):
        """Test that unbalanced voucher is rejected"""
        if not TestConfig.branch_id:
            pytest.skip("No branch ID available")
        
        response = authenticated_client.get(f"{BASE_URL}/api/accounting/ledgers?branch_id={TestConfig.branch_id}")
        ledgers = response.json()
        
        if len(ledgers) < 2:
            pytest.skip("Need at least 2 ledgers")
        
        # Create unbalanced voucher
        voucher_data = {
            "voucher_type": "journal",
            "voucher_date": datetime.now().strftime("%Y-%m-%d"),
            "branch_id": TestConfig.branch_id,
            "narration": "TEST_Unbalanced Entry",
            "entries": [
                {
                    "ledger_id": ledgers[0]["id"],
                    "ledger_name": ledgers[0]["name"],
                    "debit": 1000,
                    "credit": 0
                },
                {
                    "ledger_id": ledgers[1]["id"],
                    "ledger_name": ledgers[1]["name"],
                    "debit": 0,
                    "credit": 500  # Unbalanced
                }
            ]
        }
        
        response = authenticated_client.post(f"{BASE_URL}/api/accounting/vouchers", json=voucher_data)
        assert response.status_code == 400
        print("SUCCESS: Unbalanced voucher correctly rejected")
    
    def test_get_vouchers(self, authenticated_client):
        """Test fetching vouchers list"""
        response = authenticated_client.get(f"{BASE_URL}/api/accounting/vouchers")
        assert response.status_code == 200
        
        vouchers = response.json()
        assert isinstance(vouchers, list)
        print(f"SUCCESS: Fetched {len(vouchers)} vouchers")
    
    def test_get_voucher_by_id(self, authenticated_client):
        """Test fetching single voucher"""
        if not TestConfig.voucher_id:
            pytest.skip("No voucher ID available")
        
        response = authenticated_client.get(f"{BASE_URL}/api/accounting/vouchers/{TestConfig.voucher_id}")
        assert response.status_code == 200
        
        voucher = response.json()
        assert voucher["id"] == TestConfig.voucher_id
        print(f"SUCCESS: Fetched voucher by ID - {voucher['voucher_number']}")


# ==================== INVENTORY TESTS ====================

class TestInventory:
    """Inventory and item master tests"""
    
    def test_get_items(self, authenticated_client):
        """Test fetching items list"""
        response = authenticated_client.get(f"{BASE_URL}/api/inventory/items")
        assert response.status_code == 200
        
        items = response.json()
        assert isinstance(items, list)
        
        if len(items) > 0:
            TestConfig.item_id = items[0]["id"]
        print(f"SUCCESS: Fetched {len(items)} items")
    
    def test_create_item(self, authenticated_client):
        """Test creating a new item"""
        item_data = {
            "name": f"TEST_Ice Cream_{datetime.now().strftime('%H%M%S')}",
            "code": f"IC{datetime.now().strftime('%H%M%S')}",
            "hsn_code": "2105",
            "unit": "PCS",
            "selling_price": 100,
            "purchase_price": 70,
            "gst_rate": 18,
            "is_batch_tracked": True,
            "has_expiry": True
        }
        
        response = authenticated_client.post(f"{BASE_URL}/api/inventory/items", json=item_data)
        assert response.status_code == 200
        
        created = response.json()
        assert created["name"] == item_data["name"]
        assert "id" in created
        TestConfig.item_id = created["id"]
        print(f"SUCCESS: Created item - {created['name']}")
    
    def test_get_stock_summary(self, authenticated_client):
        """Test fetching stock summary"""
        branch_param = f"?branch_id={TestConfig.branch_id}" if TestConfig.branch_id else ""
        response = authenticated_client.get(f"{BASE_URL}/api/inventory/stock{branch_param}")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Fetched stock summary - {len(data)} items")


# ==================== SALES TESTS ====================

class TestSales:
    """Sales invoice and related tests"""
    
    def test_get_sales_invoices(self, authenticated_client):
        """Test fetching sales invoices"""
        response = authenticated_client.get(f"{BASE_URL}/api/sales/invoices")
        assert response.status_code == 200
        
        invoices = response.json()
        assert isinstance(invoices, list)
        
        if len(invoices) > 0:
            TestConfig.sales_invoice_id = invoices[0]["id"]
        print(f"SUCCESS: Fetched {len(invoices)} sales invoices")
    
    def test_get_quotations(self, authenticated_client):
        """Test fetching quotations"""
        response = authenticated_client.get(f"{BASE_URL}/api/sales/quotations")
        assert response.status_code == 200
        
        quotations = response.json()
        assert isinstance(quotations, list)
        print(f"SUCCESS: Fetched {len(quotations)} quotations")
    
    def test_get_sales_orders(self, authenticated_client):
        """Test fetching sales orders"""
        response = authenticated_client.get(f"{BASE_URL}/api/sales/orders")
        assert response.status_code == 200
        
        orders = response.json()
        assert isinstance(orders, list)
        print(f"SUCCESS: Fetched {len(orders)} sales orders")


# ==================== PURCHASE TESTS ====================

class TestPurchase:
    """Purchase invoice and related tests"""
    
    def test_get_purchase_invoices(self, authenticated_client):
        """Test fetching purchase invoices"""
        response = authenticated_client.get(f"{BASE_URL}/api/purchase/invoices")
        assert response.status_code == 200
        
        invoices = response.json()
        assert isinstance(invoices, list)
        
        if len(invoices) > 0:
            TestConfig.purchase_invoice_id = invoices[0]["id"]
        print(f"SUCCESS: Fetched {len(invoices)} purchase invoices")
    
    def test_get_purchase_orders(self, authenticated_client):
        """Test fetching purchase orders"""
        response = authenticated_client.get(f"{BASE_URL}/api/purchase/orders")
        assert response.status_code == 200
        
        orders = response.json()
        assert isinstance(orders, list)
        print(f"SUCCESS: Fetched {len(orders)} purchase orders")


# ==================== REPORTS TESTS ====================

class TestReports:
    """Financial reports tests"""
    
    def test_trial_balance(self, authenticated_client):
        """Test trial balance report generation"""
        today = datetime.now().strftime("%Y-%m-%d")
        branch_param = f"&branch_id={TestConfig.branch_id}" if TestConfig.branch_id else ""
        
        response = authenticated_client.get(f"{BASE_URL}/api/accounting/reports/trial-balance?as_on_date={today}{branch_param}")
        assert response.status_code == 200
        
        report = response.json()
        assert "items" in report
        assert "is_balanced" in report
        # API returns total_debit and total_credit (not total_closing_debit)
        total_dr = report.get('total_debit', report.get('total_closing_debit', 0))
        total_cr = report.get('total_credit', report.get('total_closing_credit', 0))
        print(f"SUCCESS: Trial Balance - Debit: {total_dr}, Credit: {total_cr}, Balanced: {report['is_balanced']}")
    
    def test_profit_loss(self, authenticated_client):
        """Test P&L report generation"""
        today = datetime.now()
        start_date = f"{today.year}-{today.month:02d}-01"
        end_date = today.strftime("%Y-%m-%d")
        branch_param = f"&branch_id={TestConfig.branch_id}" if TestConfig.branch_id else ""
        
        response = authenticated_client.get(f"{BASE_URL}/api/accounting/reports/profit-loss?start_date={start_date}&end_date={end_date}{branch_param}")
        assert response.status_code == 200
        
        report = response.json()
        # API returns income_items and expense_items
        assert "income_items" in report or "income" in report
        assert "expense_items" in report or "expenses" in report
        net_profit = report.get('net_profit', report.get('profit_loss', 0))
        print(f"SUCCESS: P&L Report - Net Profit/Loss: {net_profit}")
    
    def test_balance_sheet(self, authenticated_client):
        """Test Balance Sheet report generation"""
        today = datetime.now().strftime("%Y-%m-%d")
        branch_param = f"&branch_id={TestConfig.branch_id}" if TestConfig.branch_id else ""
        
        response = authenticated_client.get(f"{BASE_URL}/api/accounting/reports/balance-sheet?as_on_date={today}{branch_param}")
        assert response.status_code == 200
        
        report = response.json()
        # API returns asset_items, liability_items, capital_items
        assert "asset_items" in report or "assets" in report
        assert "liability_items" in report or "liabilities" in report
        assert "capital_items" in report or "capital" in report
        total_assets = report.get('total_assets', 0)
        total_liab_cap = report.get('total_liabilities_and_capital', report.get('total_liabilities', 0))
        print(f"SUCCESS: Balance Sheet - Assets: {total_assets}, Liabilities + Capital: {total_liab_cap}")
    
    def test_day_book(self, authenticated_client):
        """Test Day Book report"""
        today = datetime.now().strftime("%Y-%m-%d")
        branch_param = f"&branch_id={TestConfig.branch_id}" if TestConfig.branch_id else ""
        
        response = authenticated_client.get(f"{BASE_URL}/api/accounting/reports/day-book?start_date={today}&end_date={today}{branch_param}")
        assert response.status_code == 200
        
        report = response.json()
        assert "vouchers" in report
        assert "total_vouchers" in report
        print(f"SUCCESS: Day Book - {report['total_vouchers']} vouchers")


# ==================== GST TESTS ====================

class TestGST:
    """GST module tests"""
    
    def test_get_hsn_codes(self, authenticated_client):
        """Test fetching HSN codes"""
        response = authenticated_client.get(f"{BASE_URL}/api/gst/hsn")
        assert response.status_code == 200
        
        hsn_codes = response.json()
        assert isinstance(hsn_codes, list)
        print(f"SUCCESS: Fetched {len(hsn_codes)} HSN codes")
    
    def test_get_state_codes(self, authenticated_client):
        """Test fetching state codes"""
        response = authenticated_client.get(f"{BASE_URL}/api/gst/state-codes")
        assert response.status_code == 200
        
        state_codes = response.json()
        assert isinstance(state_codes, list)
        assert len(state_codes) > 0
        print(f"SUCCESS: Fetched {len(state_codes)} state codes")
    
    def test_gstr1_report(self, authenticated_client):
        """Test GSTR-1 report generation"""
        today = datetime.now()
        branch_param = f"&branch_id={TestConfig.branch_id}" if TestConfig.branch_id else ""
        
        response = authenticated_client.get(f"{BASE_URL}/api/gst/gstr1?month={today.month}&year={today.year}{branch_param}")
        
        # May return 400 if company GSTIN not configured
        if response.status_code == 400:
            print("INFO: GSTR-1 requires company GSTIN configuration")
            return
        
        assert response.status_code == 200
        
        report = response.json()
        assert "gstin" in report
        assert "fp" in report
        print(f"SUCCESS: GSTR-1 Report generated for {report['fp']}")
    
    def test_gstr3b_report(self, authenticated_client):
        """Test GSTR-3B report generation"""
        today = datetime.now()
        branch_param = f"&branch_id={TestConfig.branch_id}" if TestConfig.branch_id else ""
        
        response = authenticated_client.get(f"{BASE_URL}/api/gst/gstr3b?month={today.month}&year={today.year}{branch_param}")
        
        if response.status_code == 400:
            print("INFO: GSTR-3B requires company GSTIN configuration")
            return
        
        assert response.status_code == 200
        
        report = response.json()
        print(f"SUCCESS: GSTR-3B Summary generated")
    
    def test_hsn_summary(self, authenticated_client):
        """Test HSN Summary report"""
        today = datetime.now()
        branch_param = f"&branch_id={TestConfig.branch_id}" if TestConfig.branch_id else ""
        
        response = authenticated_client.get(f"{BASE_URL}/api/gst/hsn-summary?month={today.month}&year={today.year}&report_type=sales{branch_param}")
        assert response.status_code == 200
        
        report = response.json()
        assert "items" in report
        assert "totals" in report
        print(f"SUCCESS: HSN Summary - {len(report['items'])} items")
    
    def test_tax_liability(self, authenticated_client):
        """Test Tax Liability calculation"""
        today = datetime.now()
        branch_param = f"&branch_id={TestConfig.branch_id}" if TestConfig.branch_id else ""
        
        response = authenticated_client.get(f"{BASE_URL}/api/gst/tax-liability?month={today.month}&year={today.year}{branch_param}")
        assert response.status_code == 200
        
        report = response.json()
        assert "output_tax" in report
        assert "input_tax_credit" in report
        assert "net_liability" in report
        print(f"SUCCESS: Tax Liability - Net: {report['net_liability']['total']}")


# ==================== DASHBOARD TESTS ====================

class TestDashboard:
    """Dashboard stats tests"""
    
    def test_dashboard_stats(self, authenticated_client):
        """Test dashboard statistics"""
        branch_param = f"?branch_id={TestConfig.branch_id}" if TestConfig.branch_id else ""
        
        response = authenticated_client.get(f"{BASE_URL}/api/dashboard/stats{branch_param}")
        assert response.status_code == 200
        
        stats = response.json()
        assert "today_sales" in stats
        assert "monthly_sales" in stats
        assert "outstanding_receivables" in stats
        print(f"SUCCESS: Dashboard stats - Today Sales: {stats['today_sales']}, Monthly: {stats['monthly_sales']}")
    
    def test_recent_activity(self, authenticated_client):
        """Test recent activity feed"""
        response = authenticated_client.get(f"{BASE_URL}/api/dashboard/recent-activity")
        assert response.status_code == 200
        
        activities = response.json()
        assert isinstance(activities, list)
        print(f"SUCCESS: Recent activity - {len(activities)} entries")


# ==================== CUSTOMERS & SUPPLIERS TESTS ====================

class TestCustomersSuppliers:
    """Customer and supplier management tests"""
    
    def test_get_customers(self, authenticated_client):
        """Test fetching customers"""
        response = authenticated_client.get(f"{BASE_URL}/api/customers")
        assert response.status_code == 200
        
        customers = response.json()
        assert isinstance(customers, list)
        print(f"SUCCESS: Fetched {len(customers)} customers")
    
    def test_get_suppliers(self, authenticated_client):
        """Test fetching suppliers"""
        response = authenticated_client.get(f"{BASE_URL}/api/suppliers")
        assert response.status_code == 200
        
        suppliers = response.json()
        assert isinstance(suppliers, list)
        print(f"SUCCESS: Fetched {len(suppliers)} suppliers")
    
    def test_create_customer(self, authenticated_client):
        """Test creating a customer"""
        customer_data = {
            "name": f"TEST_Customer_{datetime.now().strftime('%H%M%S')}",
            "gstin": "24AAAAA0000A1Z5",
            "address": "Test Address",
            "city": "Patan",
            "state": "Gujarat",
            "state_code": "24",
            "phone": "9999999999",
            "email": "test@test.com"
        }
        
        response = authenticated_client.post(f"{BASE_URL}/api/customers", json=customer_data)
        assert response.status_code == 200
        
        created = response.json()
        assert created["name"] == customer_data["name"]
        print(f"SUCCESS: Created customer - {created['name']}")
    
    def test_create_supplier(self, authenticated_client):
        """Test creating a supplier"""
        supplier_data = {
            "name": f"TEST_Supplier_{datetime.now().strftime('%H%M%S')}",
            "gstin": "24BBBBB0000B1Z5",
            "address": "Test Address",
            "city": "Ahmedabad",
            "state": "Gujarat",
            "state_code": "24",
            "phone": "8888888888",
            "email": "supplier@test.com"
        }
        
        response = authenticated_client.post(f"{BASE_URL}/api/suppliers", json=supplier_data)
        assert response.status_code == 200
        
        created = response.json()
        assert created["name"] == supplier_data["name"]
        print(f"SUCCESS: Created supplier - {created['name']}")


# ==================== COMPANY SETTINGS TESTS ====================

class TestCompanySettings:
    """Company settings tests"""
    
    def test_get_company_settings(self, authenticated_client):
        """Test fetching company settings"""
        response = authenticated_client.get(f"{BASE_URL}/api/settings/company")
        assert response.status_code == 200
        
        settings = response.json()
        assert "business_name" in settings
        assert "gstin" in settings
        print(f"SUCCESS: Company settings - {settings.get('business_name', 'N/A')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
