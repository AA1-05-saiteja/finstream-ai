"""
FinStream AI - Bank Statement Intelligence API Routes
Handles statement upload (CSV/XLSX), local data cleaning, dual-ML evaluation,
insight aggregation, and report exporting.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile

from backend.statement_analyzer import BankStatementAnalyzer

router = APIRouter(prefix="/statement", tags=["Bank Statement Intelligence"])

analyzer = BankStatementAnalyzer()

# In-memory storage for latest analyzed bank statement
_latest_statement_analysis: Optional[Dict[str, Any]] = None
_statement_transactions_lookup: Dict[str, Dict[str, Any]] = {}


def get_latest_statement() -> Optional[Dict[str, Any]]:
    """Returns the most recently analyzed statement data."""
    return _latest_statement_analysis


def get_statement_transaction_by_id(tx_id: str) -> Optional[Dict[str, Any]]:
    """Lookup a transaction from the statement cache."""
    return _statement_transactions_lookup.get(tx_id)


@router.post(
    "/upload",
    summary="Upload & Analyze Bank Statement",
    description="Accepts a 1-month bank statement (CSV or XLSX), cleans the data, runs the dual ML risk pipeline, and returns complete financial and risk intelligence.",
)
async def upload_statement(file: UploadFile = File(...)):
    """Uploads and analyzes a bank statement file."""
    global _latest_statement_analysis, _statement_transactions_lookup
    filename = file.filename or "statement.csv"
    fn_lower = filename.lower()

    if not (fn_lower.endswith(".csv") or fn_lower.endswith(".xlsx") or fn_lower.endswith(".xls")):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{filename}'. Please upload a CSV or XLSX file.",
        )

    try:
        contents = await file.read()
        df = analyzer.read_file_to_dataframe(contents, filename)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {exc}")

    if df.empty:
        raise HTTPException(status_code=400, detail="The uploaded bank statement contains no data rows.")

    txs, audit = analyzer.parse_dataframe(df)
    if not txs:
        raise HTTPException(
            status_code=400,
            detail="No valid transactions could be parsed from the uploaded statement. Please check the column headers.",
        )

    # Execute ML Risk Scoring and Analysis
    analysis = analyzer.analyze_statement(txs, audit)
    analysis["filename"] = filename

    # Update in-memory caches
    _latest_statement_analysis = analysis
    for t in analysis.get("transactions", []):
        _statement_transactions_lookup[t["transaction_id"]] = t

    return analysis


@router.post(
    "/sample",
    summary="Load Sample 1-Month Statement",
    description="Generates a realistic synthetic 1-month Indian banking statement CSV, executes the dual-ML pipeline, and returns the analysis for instant testing.",
)
def load_sample_statement(days: int = 30):
    """Generates and analyzes a realistic bank statement."""
    global _latest_statement_analysis, _statement_transactions_lookup
    import io
    import pandas as pd

    sample_csv = analyzer.generate_sample_statement_csv(num_days=days)
    df = pd.read_csv(io.StringIO(sample_csv))
    txs, audit = analyzer.parse_dataframe(df)

    analysis = analyzer.analyze_statement(txs, audit)
    analysis["filename"] = f"synthetic_statement_{days}d.csv"

    _latest_statement_analysis = analysis
    for t in analysis.get("transactions", []):
        _statement_transactions_lookup[t["transaction_id"]] = t

    return analysis


@router.get(
    "/latest",
    summary="Get Latest Analyzed Statement",
    description="Retrieves the most recently uploaded and evaluated bank statement report.",
)
def get_latest():
    """Returns latest analyzed statement."""
    if _latest_statement_analysis is None:
        return {"status": "empty", "message": "No statement has been uploaded yet."}
    return _latest_statement_analysis


@router.get(
    "/export",
    summary="Download Statement Analysis Report",
    description="Exports the analyzed statement and risk classifications as a downloadable CSV or XLSX file.",
)
def export_statement(format: str = Query(default="csv", pattern="^(csv|xlsx)$")):
    """Downloads the analyzed statement report."""
    if _latest_statement_analysis is None or not _latest_statement_analysis.get("transactions"):
        raise HTTPException(status_code=404, detail="No analyzed statement available to export.")

    content, mime, filename = analyzer.export_analysis_report(_latest_statement_analysis, file_format=format)
    return Response(
        content=content,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/transaction/{transaction_id}",
    summary="Get Statement Transaction Detail",
    description="Retrieves the complete profile, 23 model features, and SHAP explanation for a transaction from the analyzed statement.",
)
def get_statement_tx_detail(transaction_id: str):
    """Transaction deep dive endpoint."""
    tx = _statement_transactions_lookup.get(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction '{transaction_id}' not found in analyzed statements.")
    return tx
