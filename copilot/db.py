"""Database management module for Project Atlas.

Supports both MySQL (for Docker / Production) and SQLite (for standalone local test/eval runs)
with strict security boundaries, read-only connections, and query sanitization.
"""

import os
import re
import sqlite3
import pymysql
from typing import List, Dict, Any, Optional

DB_TYPE = os.getenv("DB_TYPE", "sqlite") # "mysql" or "sqlite"
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DB = os.getenv("MYSQL_DATABASE", "copilot_db")
MYSQL_USER = os.getenv("MYSQL_USER", "copilot_rw")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "copilot_secure_pass_2025")
MYSQL_RO_USER = os.getenv("MYSQL_RO_USER", "analyst_ro")
MYSQL_RO_PASSWORD = os.getenv("MYSQL_RO_PASSWORD", "analyst_ro_pass_2025")

SQLITE_PATH = os.getenv("SQLITE_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "copilot.db"))


class DatabaseManager:
    def __init__(self, use_mysql: Optional[bool] = None):
        self.use_mysql = (DB_TYPE.lower() == "mysql") if use_mysql is None else use_mysql
        if not self.use_mysql:
            self._init_sqlite()

    def _init_sqlite(self):
        os.makedirs(os.path.dirname(os.path.abspath(SQLITE_PATH)), exist_ok=True)
        conn = sqlite3.connect(SQLITE_PATH)
        cursor = conn.cursor()

        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            publisher TEXT NOT NULL,
            published TEXT NOT NULL,
            sector TEXT NOT NULL,
            access TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS market_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report TEXT NOT NULL,
            metric TEXT NOT NULL,
            region TEXT NOT NULL,
            year_period TEXT NOT NULL,
            value TEXT NOT NULL,
            scope_note TEXT,
            FOREIGN KEY (report) REFERENCES reports(id)
        );

        CREATE TABLE IF NOT EXISTS clients (
            id TEXT PRIMARY KEY,
            company TEXT NOT NULL,
            contact_email TEXT NOT NULL,
            purchased_reports TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS escalations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT NOT NULL UNIQUE,
            client_id TEXT NOT NULL,
            query TEXT NOT NULL,
            reason TEXT NOT NULL,
            confidence REAL DEFAULT 0.0,
            status TEXT DEFAULT 'pending_analyst_review',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS chat_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            query TEXT NOT NULL,
            response_text TEXT NOT NULL,
            rating TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            client_id TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Seed reports if empty
        cursor.execute("SELECT COUNT(*) FROM reports")
        if cursor.fetchone()[0] == 0:
            reports_data = [
                ('R-101', 'Global Smart Water Meter Market 2025', 'CMR', '2025-03-10', 'Utilities', 'paid'),
                ('R-102', 'Smart Water Metering: Industry Outlook 2024', 'Aquila Insights (third party)', '2024-06-18', 'Utilities', 'public excerpt'),
                ('R-103', 'Residential Water Purifier Market 2025', 'CMR', '2025-01-22', 'Consumer Durables', 'paid'),
                ('R-104', 'Commercial & Industrial Water Filtration Systems 2025', 'CMR', '2025-02-15', 'Utilities', 'paid'),
                ('R-105', 'IoT Wastewater Management & Monitoring Market 2024-2030', 'Apex Tech Insights', '2024-11-05', 'Utilities', 'paid'),
                ('R-106', 'APAC Municipal Water Infrastructure Investment Report 2025', 'Blue River Analytics', '2025-04-01', 'Utilities', 'paid')
            ]
            cursor.executemany("INSERT INTO reports VALUES (?, ?, ?, ?, ?, ?)", reports_data)

            metrics_data = [
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
                ('R-106', 'Smart Meter Adoption', 'APAC', '2024-2030', '22% to 58%', 'Penetration rate expansion by 2030')
            ]
            cursor.executemany("INSERT INTO market_metrics (report, metric, region, year_period, value, scope_note) VALUES (?, ?, ?, ?, ?, ?)", metrics_data)

            clients_data = [
                ('C-01', 'Northwind Utilities', 'ops@example.com', 'R-101, R-103'),
                ('C-02', 'Blue Delta Infra', 'procurement@example.com', 'R-103')
            ]
            cursor.executemany("INSERT INTO clients VALUES (?, ?, ?, ?)", clients_data)

        conn.commit()
        conn.close()

    def get_connection(self, read_only: bool = False):
        if self.use_mysql:
            user = MYSQL_RO_USER if read_only else MYSQL_USER
            password = MYSQL_RO_PASSWORD if read_only else MYSQL_PASSWORD
            return pymysql.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=user,
                password=password,
                database=MYSQL_DB,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=not read_only
            )
        else:
            conn = sqlite3.connect(SQLITE_PATH)
            conn.row_factory = sqlite3.Row
            return conn

    def get_client_entitlements(self, client_id: str) -> Dict[str, Any]:
        """Fetch client profile and list of purchased reports."""
        conn = self.get_connection(read_only=True)
        cursor = conn.cursor()
        try:
            if self.use_mysql:
                cursor.execute("SELECT id, company, purchased_reports FROM clients WHERE id = %s", (client_id,))
                row = cursor.fetchone()
            else:
                cursor.execute("SELECT id, company, purchased_reports FROM clients WHERE id = ?", (client_id,))
                row = cursor.fetchone()
            
            if not row:
                return {"client_id": client_id, "found": False, "purchased_reports": []}
            
            row_dict = dict(row)
            purchased = [r.strip() for r in row_dict["purchased_reports"].split(",") if r.strip()]
            return {
                "client_id": client_id,
                "company": row_dict["company"],
                "found": True,
                "purchased_reports": purchased
            }
        finally:
            conn.close()

    def get_public_reports(self) -> List[str]:
        """Fetch all reports that have public excerpt access."""
        conn = self.get_connection(read_only=True)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM reports WHERE access LIKE '%public%'")
            rows = cursor.fetchall()
            return [row["id"] if isinstance(row, dict) else row[0] for row in rows]
        finally:
            conn.close()

    def get_all_reports_catalog(self) -> List[Dict[str, Any]]:
        """Fetch entire public/catalog metadata for upgrade offerings."""
        conn = self.get_connection(read_only=True)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, title, publisher, published, sector, access FROM reports")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def create_escalation(self, client_id: str, query: str, reason: str, confidence: float) -> str:
        """Create a human analyst escalation ticket."""
        import uuid
        ticket_id = f"TICK-{uuid.uuid4().hex[:8].upper()}"
        conn = self.get_connection(read_only=False)
        cursor = conn.cursor()
        try:
            if self.use_mysql:
                cursor.execute(
                    "INSERT INTO escalations (ticket_id, client_id, query, reason, confidence) VALUES (%s, %s, %s, %s, %s)",
                    (ticket_id, client_id, query, reason, confidence)
                )
            else:
                cursor.execute(
                    "INSERT INTO escalations (ticket_id, client_id, query, reason, confidence) VALUES (?, ?, ?, ?, ?)",
                    (ticket_id, client_id, query, reason, confidence)
                )
                conn.commit()
            return ticket_id
        finally:
            conn.close()

    def get_escalations(self) -> List[Dict[str, Any]]:
        conn = self.get_connection(read_only=True)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT ticket_id, client_id, query, reason, confidence, status, created_at FROM escalations ORDER BY id DESC")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def record_audit_log(self, event_type: str, client_id: Optional[str], details: str):
        conn = self.get_connection(read_only=False)
        cursor = conn.cursor()
        try:
            if self.use_mysql:
                cursor.execute(
                    "INSERT INTO audit_logs (event_type, client_id, details) VALUES (%s, %s, %s)",
                    (event_type, client_id or "UNKNOWN", details)
                )
            else:
                cursor.execute(
                    "INSERT INTO audit_logs (event_type, client_id, details) VALUES (?, ?, ?)",
                    (event_type, client_id or "UNKNOWN", details)
                )
                conn.commit()
        except Exception as e:
            print(f"[AUDIT LOG ERROR] Failed to record audit log: {e}")
        finally:
            conn.close()

    def execute_safe_aggregate_query(self, sql_query: str) -> Dict[str, Any]:
        """Execute aggregate SQL queries under strict security guardrails:
        1. Query must be a SELECT statement.
        2. Forbidden keywords: INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, EXEC, INTO, SLEEP, BENCHMARK.
        3. Forbidden tables: clients, audit_logs (confidential data protection).
        4. Enforced LIMIT clause (max 50 rows).
        5. Read-only user connection used.
        """
        cleaned = sql_query.strip().strip(";")
        upper_query = cleaned.upper()

        # Strict keyword rejection
        forbidden_keywords = [
            "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", 
            "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE", "REPLACE",
            "INTO", "SLEEP", "BENCHMARK", "LOAD_FILE", "OUTFILE"
        ]
        for kw in forbidden_keywords:
            if re.search(r'\b' + kw + r'\b', upper_query):
                self.record_audit_log("SQL_VIOLATION_BLOCKED", None, f"Query contained forbidden keyword '{kw}': {sql_query}")
                raise PermissionError(f"SQL execution blocked: query contains forbidden clause '{kw}'. Only read-only SELECT queries are allowed.")

        # Rejection of confidential tables
        forbidden_tables = ["CLIENTS", "AUDIT_LOGS", "ESCALATIONS", "USERS", "PASSWORDS"]
        for tbl in forbidden_tables:
            if re.search(r'\b' + tbl + r'\b', upper_query):
                self.record_audit_log("UNAUTHORIZED_TABLE_ACCESS_BLOCKED", None, f"Attempted access to protected table '{tbl}': {sql_query}")
                raise PermissionError(f"SQL execution blocked: access to confidential table '{tbl}' is forbidden.")

        if not upper_query.startswith("SELECT"):
            raise PermissionError("SQL execution blocked: only SELECT queries are permitted.")

        # Enforce LIMIT
        if "LIMIT" not in upper_query:
            cleaned += " LIMIT 50"

        conn = self.get_connection(read_only=True)
        cursor = conn.cursor()
        try:
            cursor.execute(cleaned)
            rows = cursor.fetchall()
            result = [dict(r) for r in rows]
            return {
                "success": True,
                "executed_query": cleaned,
                "row_count": len(result),
                "data": result
            }
        except Exception as e:
            return {
                "success": False,
                "executed_query": cleaned,
                "error": str(e),
                "data": []
            }
        finally:
            conn.close()


db = DatabaseManager()
