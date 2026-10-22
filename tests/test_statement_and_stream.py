"""
FinStream AI - Test Suite for Bank Statement Intelligence & Live Stream Extension
Validates column detection heuristics, data cleaning, dual-ML risk scoring, SHAP explainability,
export facilities (CSV/XLSX), API routes, and frontend page delivery.
"""

import io
from fastapi.testclient import TestClient
import openpyxl
import pytest

from backend.main import create_app
from backend.statement_analyzer import (
    BankStatementAnalyzer,
    detect_statement_columns,
    clean_and_normalize_statement,
    generate_sample_statement_csv,
    export_analysis_report,
)
from database.connection import DatabaseManager
from database.redis_client import RedisRepository
import fakeredis
from backend.dependencies import get_db_manager_dep, get_redis_repo


@pytest.fixture
def client_fixture():
    """Provides a TestClient with isolated in-memory DB and FakeRedis."""
    db_mgr = DatabaseManager(database_url="sqlite:///:memory:")
    db_mgr.create_all_tables()

    fake_client = fakeredis.FakeRedis(decode_responses=True)
    redis_repo = RedisRepository(client=fake_client)

    app = create_app()
    app.dependency_overrides[get_db_manager_dep] = lambda: db_mgr
    app.dependency_overrides[get_redis_repo] = lambda: redis_repo

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    db_mgr.drop_all_tables()
    fake_client.flushall()


# =============================================================================
# Unit Tests: Column Detection & Data Cleaning
# =============================================================================

def test_column_detection_heuristic():
    """Validates heuristic column detection across diverse bank header naming schemes."""
    headers = ["Txn Date", "Transaction Ref", "Particulars/Description", "Withdrawal (Dr)", "Deposit (Cr)", "Account Balance"]
    mapping = detect_statement_columns(headers)

    assert mapping["date"] == "Txn Date"
    assert mapping["id"] == "Transaction Ref"
    assert mapping["description"] == "Particulars/Description"
    assert mapping["debit"] == "Withdrawal (Dr)"
    assert mapping["credit"] == "Deposit (Cr)"
    assert mapping["balance"] == "Account Balance"


def test_data_cleaning_and_normalization():
    """Validates currency symbol stripping, date parsing, duplicate dropping, and sorting."""
    csv_content = '''Date,Description,Debit,Credit,Balance
2026-03-05,Swiggy UPI,₹450.00,,"₹15,000.00"
2026-03-01,Salary Credit,,"₹85,000.00","₹100,000.00"
2026-03-05,Swiggy UPI,₹450.00,,"₹15,000.00"
,,,,
2026-03-03,Amazon Shopping,"₹2,499.50",,"₹14,550.00"
'''
    cleaned_rows, audit = clean_and_normalize_statement(csv_content.encode("utf-8"), "test_statement.csv")

    assert audit["original_rows"] >= 4
    assert audit["removed_duplicates"] == 1  # 1 duplicate swiggy row
    assert len(cleaned_rows) == 3

    # Check chronological ordering: March 1, March 3, March 5
    dates = [r["timestamp"][:10] for r in cleaned_rows]
    assert dates == sorted(dates)
    assert cleaned_rows[0]["direction"] == "CREDIT"
    assert cleaned_rows[0]["amount"] == 85000.0
    assert cleaned_rows[1]["direction"] == "DEBIT"
    assert cleaned_rows[1]["amount"] == 2499.50


# =============================================================================
# Unit Tests: Dual-ML Scoring & SHAP Explanations
# =============================================================================

def test_bank_statement_analyzer_end_to_end():
    """Validates full parsing, ML scoring, SHAP attributions, and KPI summaries."""
    analyzer = BankStatementAnalyzer()
    sample_csv = generate_sample_statement_csv(days=15)
    result = analyzer.analyze_statement(sample_csv, filename="sample_15d.csv")

    assert result["filename"] == "sample_15d.csv"
    assert "summary" in result
    assert "audit" in result
    assert "transactions" in result
    assert len(result["transactions"]) > 0

    summary = result["summary"]
    assert summary["total_transactions"] == len(result["transactions"])
    assert summary["total_debit"] >= 0
    assert summary["total_credit"] >= 0
    assert summary["highest_transaction_amount"] >= summary["lowest_transaction_amount"]
    assert summary["average_transaction"] > 0
    assert summary["low_risk_count"] + summary["medium_risk_count"] + summary["high_risk_count"] == summary["total_transactions"]

    # Verify transaction record structure
    first_tx = result["transactions"][0]
    assert "transaction_id" in first_tx
    assert "hybrid_risk_score" in first_tx
    assert 0.0 <= first_tx["hybrid_risk_score"] <= 1.0
    assert first_tx["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
    assert "xgboost_probability" in first_tx
    assert "isolation_forest_normalized" in first_tx
    assert "top_shap_features" in first_tx
    assert "explanation_text" in first_tx
    assert "features" in first_tx
    assert len(first_tx["features"]) == 23

    # Verify risk sections
    assert "highest_risk_transactions" in result
    assert "medium_risk_transactions" in result
    assert "lowest_risk_transactions" in result


def test_export_analysis_report():
    """Validates CSV and XLSX report generation."""
    analyzer = BankStatementAnalyzer()
    sample_csv = generate_sample_statement_csv(days=7)
    result = analyzer.analyze_statement(sample_csv, filename="export_test.csv")

    # CSV Export
    csv_bytes = export_analysis_report(result, file_format="csv")
    assert isinstance(csv_bytes, (bytes, bytearray))
    assert b"Transaction ID" in csv_bytes
    assert b"Risk Score" in csv_bytes

    # XLSX Export
    xlsx_bytes = export_analysis_report(result, file_format="xlsx")
    assert isinstance(xlsx_bytes, (bytes, bytearray))
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    assert "Risk Analysis" in wb.sheetnames
    sheet = wb["Risk Analysis"]
    assert sheet.max_row > 1


# =============================================================================
# Integration Tests: Statement API Routes
# =============================================================================

def test_api_statement_sample_and_latest(client_fixture: TestClient):
    """Tests /api/v1/statement/sample and /api/v1/statement/latest."""
    client = client_fixture

    # Trigger synthetic sample generation
    resp = client.post("/api/v1/statement/sample?days=20")
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "synthetic_statement_20d.csv"
    assert data["summary"]["total_transactions"] > 0

    # Retrieve latest statement
    resp_latest = client.get("/api/v1/statement/latest")
    assert resp_latest.status_code == 200
    latest_data = resp_latest.json()
    assert latest_data["filename"] == "synthetic_statement_20d.csv"

    # Query single transaction detail
    first_id = data["transactions"][0]["transaction_id"]
    resp_tx = client.get(f"/api/v1/statement/transaction/{first_id}")
    assert resp_tx.status_code == 200
    tx_data = resp_tx.json()
    assert tx_data["transaction_id"] == first_id
    assert "features" in tx_data
    assert len(tx_data["features"]) == 23


def test_api_statement_upload_file(client_fixture: TestClient):
    """Tests /api/v1/statement/upload with multipart CSV file."""
    client = client_fixture
    csv_payload = """Date,Reference,Description,Debit,Credit,Balance
2026-03-01,REF001,Salary Credit,,50000,50000
2026-03-02,REF002,Grocery Store,1200,,48800
2026-03-03,REF003,Cafe Coffee,350,,48450
2026-03-04,REF004,Luxury Electronics,45000,,3450
"""
    files = {"file": ("my_bank_statement.csv", csv_payload.encode("utf-8"), "text/csv")}
    resp = client.post("/api/v1/statement/upload", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "my_bank_statement.csv"
    assert data["summary"]["total_transactions"] == 4
    assert data["summary"]["total_credit"] == 50000.0
    assert data["summary"]["total_debit"] == 46550.0


def test_api_statement_export(client_fixture: TestClient):
    """Tests downloading CSV and XLSX exports via /api/v1/statement/export."""
    client = client_fixture

    # Load sample first
    client.post("/api/v1/statement/sample?days=10")

    # Export CSV
    resp_csv = client.get("/api/v1/statement/export?format=csv")
    assert resp_csv.status_code == 200
    assert resp_csv.headers["content-type"].startswith("text/csv")
    assert "attachment;" in resp_csv.headers["content-disposition"]
    assert b"Risk Score" in resp_csv.content

    # Export XLSX
    resp_xlsx = client.get("/api/v1/statement/export?format=xlsx")
    assert resp_xlsx.status_code == 200
    assert "openxmlformats" in resp_xlsx.headers["content-type"]
    assert len(resp_xlsx.content) > 1000


# =============================================================================
# Integration Tests: Live Stream Engine & Contextual Comparison API
# =============================================================================

def test_api_stream_tick_and_alert(client_fixture: TestClient):
    """Tests /api/v1/stream/tick, buffer retrieval, and alert workflow."""
    client = client_fixture

    # Normal tick
    resp_tick = client.post("/api/v1/stream/tick")
    assert resp_tick.status_code == 200
    data = resp_tick.json()
    assert "transaction_id" in data
    assert data["source"] == "LIVE_STREAM"
    assert "hybrid_risk_score" in data
    assert "top_shap_features" in data

    # High-Risk tick to trigger banner alert
    resp_alert = client.post("/api/v1/stream/tick?scenario=high_risk")
    assert resp_alert.status_code == 200
    alert_data = resp_alert.json()
    assert alert_data["risk_level"] == "HIGH"

    # Contextual comparison check
    resp_comp = client.get("/api/v1/stream/comparison")
    assert resp_comp.status_code == 200
    comp_data = resp_comp.json()
    assert "statement_loaded" in comp_data
    assert "stream_count" in comp_data
    assert comp_data["stream_count"] >= 2
    assert comp_data["latest_alert"] is not None
    assert comp_data["latest_alert"]["transaction_id"] == alert_data["transaction_id"]

    # Clear alert
    resp_clear = client.post("/api/v1/stream/clear-alert")
    assert resp_clear.status_code == 200
    assert resp_clear.json()["status"] == "cleared"

    # Verify cleared in comparison
    resp_comp_after = client.get("/api/v1/stream/comparison")
    assert resp_comp_after.json()["latest_alert"] is None


# =============================================================================
# Integration Tests: Frontend HTML Delivery
# =============================================================================

def test_frontend_routes_served(client_fixture: TestClient):
    """Ensures all web dashboard routes are served with HTML status 200."""
    client = client_fixture

    # Home / Live Stream Dashboard
    r_home = client.get("/")
    assert r_home.status_code == 200
    assert "FINSTREAM AI" in r_home.text
    assert "Live Transaction Stream" in r_home.text
    assert "live-alert-banner" in r_home.text

    # Bank Statement Intelligence Page
    r_stmt = client.get("/statement")
    assert r_stmt.status_code == 200
    assert "Bank Statement Intelligence" in r_stmt.text
    assert "One-Month Transaction Intelligence" in r_stmt.text

    # Monthly Insights Page
    r_ins = client.get("/insights")
    assert r_ins.status_code == 200
    assert "Financial Transaction Insights" in r_ins.text

    # Transaction Deep-Dive Page
    r_tx = client.get("/transaction/TX_TEST_001")
    assert r_tx.status_code == 200
    assert "Transaction Intelligence Profile" in r_tx.text
