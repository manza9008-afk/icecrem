-- HOOREN FOOD PRODUCTS ERP System
-- MySQL Database Schema
-- Compatible with MySQL 5.7+ / MariaDB 10.2+

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";

CREATE DATABASE IF NOT EXISTS `hooren_erp` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `hooren_erp`;

-- =====================================================
-- USERS & AUTHENTICATION
-- =====================================================

CREATE TABLE `users` (
  `id` INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(50) NOT NULL UNIQUE,
  `password_hash` VARCHAR(255) NOT NULL,
  `email` VARCHAR(100),
  `full_name` VARCHAR(100) NOT NULL,
  `require_password_change` TINYINT(1) DEFAULT 1,
  `last_login` DATETIME,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert default admin user (password: Hooren@2026#Secure)
INSERT INTO `users` (`username`, `password_hash`, `email`, `full_name`, `require_password_change`) 
VALUES ('hooren_admin', '$2y$10$zQXMZY4vK9XxN7wLkH0KL.xJ8VN7xQz5H0wK8N7xQz5H0wK8N7xQz', 'maanzaicecream@gmail.com', 'Admin User', 1);

-- =====================================================
-- COMPANY SETTINGS
-- =====================================================

CREATE TABLE `company_settings` (
  `id` INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `business_name` VARCHAR(200) NOT NULL,
  `trade_name` VARCHAR(200),
  `gstin` VARCHAR(15),
  `address` TEXT,
  `phone` VARCHAR(20),
  `email` VARCHAR(100),
  `bank_name` VARCHAR(100),
  `account_number` VARCHAR(50),
  `ifsc` VARCHAR(11),
  `branch` VARCHAR(100),
  `logo_path` VARCHAR(255),
  `invoice_terms` TEXT,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert default company settings
INSERT INTO `company_settings` 
(`business_name`, `trade_name`, `gstin`, `address`, `phone`, `email`, `bank_name`, `account_number`, `ifsc`, `branch`, `invoice_terms`) 
VALUES 
('HOOREN FOOD PRODUCTS', 'HOOREN FOOD PRODUCT', '24AAHFH1702M1ZK', 
'Survey No 409, R.S. No 409, At Ranuj, Post Ranuj, Taluka Patan, Patan, Gujarat – 384275', 
'9725368208', 'maanzaicecream@gmail.com', 'Kotak Mahindra Bank', '0711473537', 'KKBK0000848', 'Siddhpur',
'1. Goods once sold will not be taken back.\n2. Interest @18% per annum if payment delayed.\n3. Subject to Patan jurisdiction only.');

-- =====================================================
-- CHART OF ACCOUNTS
-- =====================================================

CREATE TABLE `chart_of_accounts` (
  `id` INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `account_code` VARCHAR(20) NOT NULL UNIQUE,
  `account_name` VARCHAR(100) NOT NULL,
  `account_type` ENUM('Asset', 'Liability', 'Income', 'Expense', 'Capital') NOT NULL,
  `parent_id` INT(11) UNSIGNED,
  `is_active` TINYINT(1) DEFAULT 1,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `parent_id` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert default chart of accounts
INSERT INTO `chart_of_accounts` (`account_code`, `account_name`, `account_type`) VALUES
('1000', 'Assets', 'Asset'),
('1100', 'Current Assets', 'Asset'),
('1200', 'Cash & Bank', 'Asset'),
('1300', 'Sundry Debtors', 'Asset'),
('1400', 'Stock', 'Asset'),
('2000', 'Liabilities', 'Liability'),
('2100', 'Current Liabilities', 'Liability'),
('2200', 'Sundry Creditors', 'Liability'),
('2300', 'GST Payable', 'Liability'),
('3000', 'Capital', 'Capital'),
('4000', 'Income', 'Income'),
('4100', 'Sales', 'Income'),
('5000', 'Expenses', 'Expense'),
('5100', 'Purchase', 'Expense'),
('5200', 'Operating Expenses', 'Expense');

-- =====================================================
-- LEDGERS
-- =====================================================

CREATE TABLE `ledgers` (
  `id` INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(200) NOT NULL,
  `account_id` INT(11) UNSIGNED NOT NULL,
  `opening_balance` DECIMAL(15,2) DEFAULT 0.00,
  `current_balance` DECIMAL(15,2) DEFAULT 0.00,
  `is_active` TINYINT(1) DEFAULT 1,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `account_id` (`account_id`),
  CONSTRAINT `fk_ledger_account` FOREIGN KEY (`account_id`) REFERENCES `chart_of_accounts` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- ITEMS (PRODUCTS)
-- =====================================================

CREATE TABLE `items` (
  `id` INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(200) NOT NULL,
  `sku` VARCHAR(50) NOT NULL UNIQUE,
  `category` VARCHAR(100),
  `hsn` VARCHAR(10) DEFAULT '2105',
  `gst_rate` DECIMAL(5,2) DEFAULT 12.00,
  `unit` VARCHAR(20) DEFAULT 'Piece',
  `cost_price` DECIMAL(10,2) NOT NULL,
  `selling_price` DECIMAL(10,2) NOT NULL,
  `reorder_level` INT(11) DEFAULT 10,
  `is_active` TINYINT(1) DEFAULT 1,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- STOCK MANAGEMENT
-- =====================================================

CREATE TABLE `stock_transactions` (
  `id` INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `item_id` INT(11) UNSIGNED NOT NULL,
  `transaction_type` ENUM('opening', 'purchase', 'sale', 'adjustment') NOT NULL,
  `quantity` DECIMAL(10,2) NOT NULL,
  `batch_no` VARCHAR(50),
  `expiry_date` DATE,
  `reference_type` VARCHAR(50),
  `reference_id` INT(11) UNSIGNED,
  `reference_number` VARCHAR(50),
  `transaction_date` DATETIME NOT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `item_id` (`item_id`),
  CONSTRAINT `fk_stock_item` FOREIGN KEY (`item_id`) REFERENCES `items` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- View for current stock
CREATE VIEW `v_current_stock` AS
SELECT 
  i.id as item_id,
  i.name as item_name,
  i.sku,
  i.category,
  i.unit,
  i.cost_price,
  i.selling_price,
  i.reorder_level,
  COALESCE(SUM(st.quantity), 0) as current_stock,
  COALESCE(SUM(st.quantity), 0) * i.cost_price as stock_value
FROM items i
LEFT JOIN stock_transactions st ON i.id = st.item_id
WHERE i.is_active = 1
GROUP BY i.id;

-- =====================================================
-- CUSTOMERS
-- =====================================================

CREATE TABLE `customers` (
  `id` INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(200) NOT NULL,
  `address` TEXT,
  `gstin` VARCHAR(15),
  `pan` VARCHAR(10),
  `phone` VARCHAR(20) NOT NULL,
  `email` VARCHAR(100),
  `credit_limit` DECIMAL(15,2) DEFAULT 0.00,
  `ledger_id` INT(11) UNSIGNED,
  `is_active` TINYINT(1) DEFAULT 1,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ledger_id` (`ledger_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- SUPPLIERS
-- =====================================================

CREATE TABLE `suppliers` (
  `id` INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(200) NOT NULL,
  `address` TEXT,
  `gstin` VARCHAR(15),
  `pan` VARCHAR(10),
  `phone` VARCHAR(20) NOT NULL,
  `email` VARCHAR(100),
  `ledger_id` INT(11) UNSIGNED,
  `is_active` TINYINT(1) DEFAULT 1,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ledger_id` (`ledger_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- SALES INVOICES
-- =====================================================

CREATE TABLE `sales_invoices` (
  `id` INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `invoice_number` VARCHAR(50) NOT NULL UNIQUE,
  `invoice_type` ENUM('gst', 'kacha') NOT NULL,
  `invoice_date` DATE NOT NULL,
  `customer_id` INT(11) UNSIGNED,
  `customer_name` VARCHAR(200) NOT NULL,
  `customer_gstin` VARCHAR(15),
  `customer_address` TEXT,
  `subtotal` DECIMAL(15,2) NOT NULL,
  `cgst` DECIMAL(15,2) DEFAULT 0.00,
  `sgst` DECIMAL(15,2) DEFAULT 0.00,
  `igst` DECIMAL(15,2) DEFAULT 0.00,
  `discount` DECIMAL(15,2) DEFAULT 0.00,
  `round_off` DECIMAL(10,2) DEFAULT 0.00,
  `grand_total` DECIMAL(15,2) NOT NULL,
  `notes` TEXT,
  `created_by` INT(11) UNSIGNED,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `customer_id` (`customer_id`),
  KEY `invoice_date` (`invoice_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `sales_invoice_items` (
  `id` INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `invoice_id` INT(11) UNSIGNED NOT NULL,
  `item_id` INT(11) UNSIGNED NOT NULL,
  `item_name` VARCHAR(200) NOT NULL,
  `hsn` VARCHAR(10),
  `quantity` DECIMAL(10,2) NOT NULL,
  `rate` DECIMAL(10,2) NOT NULL,
  `amount` DECIMAL(15,2) NOT NULL,
  `gst_rate` DECIMAL(5,2),
  `batch_no` VARCHAR(50),
  `expiry_date` DATE,
  PRIMARY KEY (`id`),
  KEY `invoice_id` (`invoice_id`),
  KEY `item_id` (`item_id`),
  CONSTRAINT `fk_sales_item_invoice` FOREIGN KEY (`invoice_id`) REFERENCES `sales_invoices` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_sales_item_item` FOREIGN KEY (`item_id`) REFERENCES `items` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- PURCHASE INVOICES
-- =====================================================

CREATE TABLE `purchase_invoices` (
  `id` INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `invoice_number` VARCHAR(50) NOT NULL UNIQUE,
  `invoice_date` DATE NOT NULL,
  `supplier_id` INT(11) UNSIGNED,
  `supplier_name` VARCHAR(200) NOT NULL,
  `supplier_gstin` VARCHAR(15),
  `subtotal` DECIMAL(15,2) NOT NULL,
  `cgst` DECIMAL(15,2) DEFAULT 0.00,
  `sgst` DECIMAL(15,2) DEFAULT 0.00,
  `igst` DECIMAL(15,2) DEFAULT 0.00,
  `grand_total` DECIMAL(15,2) NOT NULL,
  `created_by` INT(11) UNSIGNED,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `supplier_id` (`supplier_id`),
  KEY `invoice_date` (`invoice_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `purchase_invoice_items` (
  `id` INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `invoice_id` INT(11) UNSIGNED NOT NULL,
  `item_id` INT(11) UNSIGNED NOT NULL,
  `item_name` VARCHAR(200) NOT NULL,
  `hsn` VARCHAR(10),
  `quantity` DECIMAL(10,2) NOT NULL,
  `rate` DECIMAL(10,2) NOT NULL,
  `amount` DECIMAL(15,2) NOT NULL,
  `gst_rate` DECIMAL(5,2),
  `batch_no` VARCHAR(50),
  `expiry_date` DATE,
  PRIMARY KEY (`id`),
  KEY `invoice_id` (`invoice_id`),
  KEY `item_id` (`item_id`),
  CONSTRAINT `fk_purchase_item_invoice` FOREIGN KEY (`invoice_id`) REFERENCES `purchase_invoices` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_purchase_item_item` FOREIGN KEY (`item_id`) REFERENCES `items` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- VOUCHERS (Journal, Payment, Receipt, Contra)
-- =====================================================

CREATE TABLE `vouchers` (
  `id` INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `voucher_type` ENUM('journal', 'payment', 'receipt', 'contra', 'debit_note', 'credit_note') NOT NULL,
  `voucher_number` VARCHAR(50) NOT NULL UNIQUE,
  `voucher_date` DATE NOT NULL,
  `narration` TEXT,
  `total_amount` DECIMAL(15,2) NOT NULL,
  `created_by` INT(11) UNSIGNED,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `voucher_date` (`voucher_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `voucher_entries` (
  `id` INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `voucher_id` INT(11) UNSIGNED NOT NULL,
  `ledger_id` INT(11) UNSIGNED NOT NULL,
  `entry_type` ENUM('debit', 'credit') NOT NULL,
  `amount` DECIMAL(15,2) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `voucher_id` (`voucher_id`),
  KEY `ledger_id` (`ledger_id`),
  CONSTRAINT `fk_entry_voucher` FOREIGN KEY (`voucher_id`) REFERENCES `vouchers` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_entry_ledger` FOREIGN KEY (`ledger_id`) REFERENCES `ledgers` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- INVOICE SETTINGS
-- =====================================================

CREATE TABLE `invoice_settings` (
  `id` INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `invoice_type` VARCHAR(20) NOT NULL UNIQUE,
  `prefix` VARCHAR(10) NOT NULL,
  `next_number` INT(11) DEFAULT 1,
  `financial_year` VARCHAR(10),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert default invoice settings
INSERT INTO `invoice_settings` (`invoice_type`, `prefix`, `next_number`, `financial_year`) VALUES
('gst', 'GST', 1, '2025-26'),
('kacha', 'KB', 1, '2025-26'),
('purchase', 'PUR', 1, '2025-26');

-- =====================================================
-- EMAIL SETTINGS
-- =====================================================

CREATE TABLE `email_settings` (
  `id` INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `smtp_host` VARCHAR(100),
  `smtp_port` INT(5) DEFAULT 587,
  `smtp_username` VARCHAR(100),
  `smtp_password` VARCHAR(255),
  `from_email` VARCHAR(100),
  `from_name` VARCHAR(100),
  `is_enabled` TINYINT(1) DEFAULT 0,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- AUDIT LOG
-- =====================================================

CREATE TABLE `audit_log` (
  `id` INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` INT(11) UNSIGNED,
  `action` VARCHAR(50) NOT NULL,
  `table_name` VARCHAR(50),
  `record_id` INT(11) UNSIGNED,
  `old_value` TEXT,
  `new_value` TEXT,
  `ip_address` VARCHAR(45),
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- STORED PROCEDURES
-- =====================================================

DELIMITER //

-- Procedure to get Trial Balance
CREATE PROCEDURE `get_trial_balance`()
BEGIN
  SELECT 
    l.id,
    l.name as ledger_name,
    a.account_name as account_group,
    CASE 
      WHEN l.current_balance >= 0 THEN l.current_balance 
      ELSE 0 
    END as debit,
    CASE 
      WHEN l.current_balance < 0 THEN ABS(l.current_balance) 
      ELSE 0 
    END as credit
  FROM ledgers l
  JOIN chart_of_accounts a ON l.account_id = a.id
  WHERE l.is_active = 1
  ORDER BY a.account_type, l.name;
END //

-- Procedure to post accounting entry
CREATE PROCEDURE `post_accounting_entry`(
  IN p_transaction_type VARCHAR(20),
  IN p_reference_id INT,
  IN p_amount DECIMAL(15,2),
  IN p_date DATE
)
BEGIN
  -- Implementation for double-entry posting
  -- This will be called from PHP for each transaction
END //

DELIMITER ;

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

CREATE INDEX idx_sales_date ON sales_invoices(invoice_date);
CREATE INDEX idx_purchase_date ON purchase_invoices(invoice_date);
CREATE INDEX idx_stock_item_date ON stock_transactions(item_id, transaction_date);
CREATE INDEX idx_ledger_balance ON ledgers(current_balance);

-- =====================================================
-- END OF SCHEMA
-- =====================================================
