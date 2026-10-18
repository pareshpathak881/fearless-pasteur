-- Project Atlas Database Schema & Seed Data
-- Cognitive Market Research & Consulting Copilot

CREATE DATABASE IF NOT EXISTS copilot_db;
USE copilot_db;

-- 1. Reports Master Table
CREATE TABLE IF NOT EXISTS reports (
    id VARCHAR(20) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    publisher VARCHAR(100) NOT NULL,
    published DATE NOT NULL,
    sector VARCHAR(100) NOT NULL,
    access VARCHAR(50) NOT NULL
);

-- 2. Market Metrics Table
CREATE TABLE IF NOT EXISTS market_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report VARCHAR(20) NOT NULL,
    metric VARCHAR(100) NOT NULL,
    region VARCHAR(100) NOT NULL,
    year_period VARCHAR(50) NOT NULL,
    value VARCHAR(100) NOT NULL,
    scope_note TEXT,
    FOREIGN KEY (report) REFERENCES reports(id) ON DELETE CASCADE
);

-- 3. Clients & Entitlements Table (Confidential)
CREATE TABLE IF NOT EXISTS clients (
    id VARCHAR(20) PRIMARY KEY,
    company VARCHAR(100) NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    purchased_reports TEXT NOT NULL
);

-- 4. Analyst Escalation Tickets Table
CREATE TABLE IF NOT EXISTS escalations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id VARCHAR(50) NOT NULL UNIQUE,
    client_id VARCHAR(20) NOT NULL,
    query TEXT NOT NULL,
    reason TEXT NOT NULL,
    confidence FLOAT DEFAULT 0.0,
    status VARCHAR(50) DEFAULT 'pending_analyst_review',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Chat History & Feedback Table (CodeIgniter 3 integration)
CREATE TABLE IF NOT EXISTS chat_feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id VARCHAR(20) NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    query TEXT NOT NULL,
    response_text TEXT NOT NULL,
    rating VARCHAR(20) DEFAULT NULL, -- 'thumbs_up' or 'thumbs_down'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Security Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    client_id VARCHAR(50),
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed Data: Reports
INSERT INTO reports (id, title, publisher, published, sector, access) VALUES
('R-101', 'Global Smart Water Meter Market 2025', 'CMR', '2025-03-10', 'Utilities', 'paid'),
('R-102', 'Smart Water Metering: Industry Outlook 2024', 'Aquila Insights (third party)', '2024-06-18', 'Utilities', 'public excerpt'),
('R-103', 'Residential Water Purifier Market 2025', 'CMR', '2025-01-22', 'Consumer Durables', 'paid'),
('R-104', 'Commercial & Industrial Water Filtration Systems 2025', 'CMR', '2025-02-15', 'Utilities', 'paid'),
('R-105', 'IoT Wastewater Management & Monitoring Market 2024-2030', 'Apex Tech Insights', '2024-11-05', 'Utilities', 'paid'),
('R-106', 'APAC Municipal Water Infrastructure Investment Report 2025', 'Blue River Analytics', '2025-04-01', 'Utilities', 'paid')
ON DUPLICATE KEY UPDATE title=VALUES(title);

-- Seed Data: Market Metrics
INSERT INTO market_metrics (report, metric, region, year_period, value, scope_note) VALUES
('R-101', 'Market size', 'Global', '2024', 'USD 4.21 B', 'Includes hardware, software and services'),
('R-101', 'CAGR', 'Global', '2025-2030', '11.2 %', 'Forecast period stated as 2025-2030'),
('R-101', 'Regional share', 'APAC', '2024', '38 %', 'Share of global market size'),
('R-102', 'Market size', 'Global', '2024', 'USD 3.87 B', 'AMR / AMI hardware only'),
('R-102', 'CAGR', 'Global', '2024-2029', '9.8 %', 'Different forecast window from R-101'),
('R-102', 'Regional share', 'APAC', '2024', '41 %', 'Share of hardware market'),
('R-103', 'Market size', 'Global', '2024', 'USD 9.45 B', 'Covers POU/POE units and replacement cartridges'),
('R-103', 'CAGR', 'Global', '2025-2030', '8.4 %', 'Forecast period 2025-2030'),
('R-103', 'Regional share', 'APAC', '2024', '44 %', 'Share of global revenue in 2024'),
('R-104', 'Market size', 'Global', '2024', 'USD 6.15 B', 'Modular multi-media filters, MBR, EDI, continuous skids'),
('R-104', 'CAGR', 'Global', '2025-2030', '7.1 %', 'Forecast period 2025-2030'),
('R-105', 'Market size', 'Global', '2024', 'USD 2.95 B', 'Sensors, telemetry nodes, cloud SCADA'),
('R-105', 'CAGR', 'Global', '2024-2030', '13.5 %', 'Forecast period 2024-2030'),
('R-106', 'Municipal Capex', 'APAC', '2024', 'USD 54.2 B', 'Municipal infrastructure investment across APAC'),
('R-106', 'Smart Meter Adoption', 'APAC', '2024-2030', '22% to 58%', 'Penetration rate expansion by 2030');

-- Seed Data: Clients
INSERT INTO clients (id, company, contact_email, purchased_reports) VALUES
('C-01', 'Northwind Utilities', 'ops@example.com', 'R-101, R-103'),
('C-02', 'Blue Delta Infra', 'procurement@example.com', 'R-103')
ON DUPLICATE KEY UPDATE company=VALUES(company);

-- Dual-User Security Model
-- 1. Read-write user for application backend
CREATE USER IF NOT EXISTS 'copilot_rw'@'%' IDENTIFIED BY 'copilot_secure_pass_2025';
GRANT ALL PRIVILEGES ON copilot_db.* TO 'copilot_rw'@'%';

-- 2. Read-only user strictly for NL-to-SQL analytics tool (no access to clients or audit logs)
CREATE USER IF NOT EXISTS 'analyst_ro'@'%' IDENTIFIED BY 'analyst_ro_pass_2025';
GRANT SELECT ON copilot_db.reports TO 'analyst_ro'@'%';
GRANT SELECT ON copilot_db.market_metrics TO 'analyst_ro'@'%';

FLUSH PRIVILEGES;
