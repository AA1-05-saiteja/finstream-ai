"""
FinStream AI - Bank Statement Analyzer & Intelligence Engine
Parses, cleans, and standardizes multi-format bank statements (CSV, XLSX),
computes data quality audits, runs transactions through the 23-feature dual-ML
risk model (XGBoost + Isolation Forest + SHAP), and aggregates financial insights.
"""

from datetime import datetime, timezone
import io
import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from models.predict import load_inference_engine
from streaming.feature_engineering import RealTimeFeatureEngine

logger = logging.getLogger("statement_analyzer")

# Common Category keyword patterns for financial narrations
CATEGORY_KEYWORD_PATTERNS = {
    "DINING": [
        "zomato", "swiggy", "starbucks", "mcdonald", "kfc", "dominos", "pizza",
        "restaurant", "cafe", "coffee", "bistro", "burger", "subway", "barbeque", "dhaba"
    ],
    "GROCERY": [
        "dmart", "blinkit", "zepto", "bigbasket", "instamart", "grocery", "supermarket",
        "kirana", "provisions", "nature basket", "spencer", "reliance fresh"
    ],
    "SHOPPING": [
        "amazon", "flipkart", "myntra", "ajio", "zara", "h&m", "retail", "mall",
        "clothing", "apparel", "footwear", "decathlon", "store"
    ],
    "TRAVEL": [
        "uber", "ola", "irctc", "makemytrip", "goibibo", "yatra", "indigo", "air india",
        "vistara", "flight", "railway", "metro", "fuel", "petrol", "diesel", "hpcl", "bpcl", "iocl", "toll"
    ],
    "ELECTRONICS": [
        "apple", "croma", "reliance digital", "vijay sales", "samsung", "electronics", "gadget"
    ],
    "LUXURY": [
        "tanishq", "malabar", "kalyan", "jewel", "gold", "diamond", "rolex", "luxury", "boutique"
    ],
    "ENTERTAINMENT": [
        "netflix", "hotstar", "prime video", "bookmyshow", "pvr", "inox", "cinema", "spotify", "youtube"
    ],
    "UTILITIES": [
        "bescom", "tneb", "electricity", "airtel", "jio", "vodafone", "broadband", "water", "gas", "bill", "recharge"
    ],
}

INDIAN_CITIES_SAMPLE = ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai", "Kolkata", "Pune", "Ahmedabad", "Jaipur"]


class BankStatementAnalyzer:
    """
    Intelligent bank statement parser and risk evaluator.
    Handles varied column schemas, currency formats, direction derivations,
    and coordinates real-time feature extraction and ML scoring.
    """

    def __init__(self):
        self.feature_engine = RealTimeFeatureEngine()

    @staticmethod
    def _normalize_col_name(col: str) -> str:
        """Converts arbitrary column header to lowercase alphanumeric slug."""
        return re.sub(r"[^a-z0-9]", "", str(col).lower())

    def detect_columns(self, df: pd.DataFrame) -> Dict[str, Optional[str]]:
        """
        Maps statement DataFrame columns to standard semantic roles using regex matching.
        """
        detected: Dict[str, Optional[str]] = {
            "date": None,
            "id": None,
            "description": None,
            "debit": None,
            "credit": None,
            "amount": None,
            "balance": None,
            "category": None,
            "merchant": None,
            "channel": None,
            "city": None,
        }

        patterns = {
            "date": r"(date|timestamp|posting|valuedate)",
            "id": r"(txnid|transactionid|transactionref|refno|referenceno|reference|chqno|chequeno|utr|^id$|^ref$)",
            "description": r"(particular|narration|desc|detail|remark|memo|note)",
            "debit": r"(debit|withdrawal|withdrawn|dramount|^dr|dr$)",
            "credit": r"(credit|deposit|cramount|^cr|cr$)",
            "amount": r"(amount|netamt)",
            "balance": r"(balance|closingbal|availbal)",
            "category": r"(categor|vertical|expense)",
            "merchant": r"(merchant|payee|beneficiary)",
            "channel": r"(channel|paymentmode|txntype)",
            "city": r"(city|branch|location)",
        }

        normalized_cols = {col: self._normalize_col_name(col) for col in df.columns}

        for role, regex in patterns.items():
            for orig_col, norm in normalized_cols.items():
                if re.search(regex, norm):
                    detected[role] = orig_col
                    break

        return detected

    @staticmethod
    def _clean_numeric(val: Any) -> float:
        """Safely parses float from strings containing currency symbols, commas, or signs."""
        if pd.isna(val) or val is None or val == "":
            return 0.0
        if isinstance(val, (int, float)):
            return float(val) if not math.isnan(val) else 0.0
        clean_str = re.sub(r"[^\d.-]", "", str(val).strip())
        try:
            return float(clean_str) if clean_str else 0.0
        except ValueError:
            return 0.0

    @staticmethod
    def _infer_category_from_text(text: str) -> str:
        """Heuristic category deduction from transaction narration."""
        clean = str(text).lower()
        for cat, keywords in CATEGORY_KEYWORD_PATTERNS.items():
            for kw in keywords:
                if kw in clean:
                    return cat
        return "GENERAL"

    def parse_dataframe(self, df: pd.DataFrame) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Cleans and standardizes raw statement DataFrame into a canonical list of transactions.
        Returns (transactions_list, quality_audit_dict).
        """
        orig_row_count = len(df)
        warnings: List[str] = []

        # 1. Drop completely empty rows
        df = df.dropna(how="all").copy()

        if df.empty:
            return [], {
                "original_rows": orig_row_count,
                "valid_transactions": 0,
                "removed_duplicates": 0,
                "invalid_rows": orig_row_count,
                "date_range": {"start": None, "end": None},
                "warnings": ["Uploaded statement contains no readable rows."],
            }

        # 2. Identify semantic columns
        col_map = self.detect_columns(df)
        if not col_map["date"]:
            warnings.append("Date column could not be automatically detected. Attempting fallback to first column.")
            col_map["date"] = df.columns[0]

        has_separate_dr_cr = bool(col_map["debit"] and col_map["credit"])
        if not has_separate_dr_cr and not col_map["amount"]:
            warnings.append("No explicit Amount or Debit/Credit columns found. Attempting search for numerical fields.")
            for col in df.columns:
                if df[col].dtype in [np.float64, np.int64]:
                    col_map["amount"] = col
                    break

        # 3. Deduplication check
        initial_count = len(df)
        df = df.drop_duplicates().copy()
        removed_duplicates = initial_count - len(df)
        if removed_duplicates > 0:
            warnings.append(f"Removed {removed_duplicates} identical duplicate transaction rows.")

        # 4. Standardize rows
        parsed_records: List[Dict[str, Any]] = []
        invalid_rows = 0

        for idx, row in df.iterrows():
            # Date Parsing
            raw_date = row.get(col_map["date"])
            try:
                date_dt = pd.to_datetime(raw_date, errors="coerce")
                if pd.isna(date_dt):
                    date_dt = datetime.now(timezone.utc)
                elif date_dt.tzinfo is None:
                    date_dt = date_dt.replace(tzinfo=timezone.utc)
            except Exception:
                date_dt = datetime.now(timezone.utc)

            # Amount & Direction Parsing
            debit_val = self._clean_numeric(row.get(col_map["debit"])) if col_map["debit"] else 0.0
            credit_val = self._clean_numeric(row.get(col_map["credit"])) if col_map["credit"] else 0.0

            if has_separate_dr_cr:
                if debit_val > 0:
                    amount = round(debit_val, 2)
                    direction = "DEBIT"
                    tx_type = "PURCHASE"
                elif credit_val > 0:
                    amount = round(credit_val, 2)
                    direction = "CREDIT"
                    tx_type = "DEPOSIT"
                else:
                    invalid_rows += 1
                    continue
            else:
                raw_amt = self._clean_numeric(row.get(col_map["amount"]))
                if raw_amt == 0.0:
                    invalid_rows += 1
                    continue
                amount = round(abs(raw_amt), 2)
                direction = "CREDIT" if raw_amt > 0 and "cr" in str(row.values).lower() else "DEBIT"
                tx_type = "DEPOSIT" if direction == "CREDIT" else "PURCHASE"

            # Metadata extraction
            tx_id = str(row.get(col_map["id"]) or f"STX{idx+1:05d}").strip()
            description = str(row.get(col_map["description"]) or f"Transaction {tx_id}").strip()

            category = str(row.get(col_map["category"]) or "").strip().upper()
            if not category or category == "NAN":
                category = self._infer_category_from_text(description)

            merchant = str(row.get(col_map["merchant"]) or "").strip()
            if not merchant or merchant == "NAN":
                merchant = description[:24]

            channel = str(row.get(col_map["channel"]) or "UPI").strip().upper()
            if channel not in ["UPI", "POS", "ONLINE", "ATM", "NET_BANKING"]:
                channel = "UPI" if "upi" in description.lower() else "ONLINE"

            city = str(row.get(col_map["city"]) or "Mumbai").strip()
            if not city or city == "NAN":
                city = "Mumbai"

            balance = self._clean_numeric(row.get(col_map["balance"])) if col_map["balance"] else 0.0

            parsed_records.append({
                "transaction_id": tx_id,
                "timestamp": date_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "date_dt": date_dt,
                "amount": amount,
                "currency": "INR",
                "direction": direction,
                "transaction_type": tx_type,
                "description": description,
                "merchant_id": merchant,
                "merchant_category": category,
                "city": city,
                "device_id": f"DEV_STMT_{idx%15:03d}",
                "channel": channel,
                "card_present": channel in ["POS", "ATM"],
                "balance": balance,
                "scenario_label": "STATEMENT_HISTORICAL",
            })

        # 5. Chronological Sort
        parsed_records.sort(key=lambda r: r["date_dt"])

        # Determine date range
        start_date = parsed_records[0]["date_dt"].strftime("%Y-%m-%d") if parsed_records else None
        end_date = parsed_records[-1]["date_dt"].strftime("%Y-%m-%d") if parsed_records else None

        # Clean date_dt before JSON serialization
        for r in parsed_records:
            r.pop("date_dt", None)

        audit = {
            "original_rows": orig_row_count,
            "valid_transactions": len(parsed_records),
            "removed_duplicates": removed_duplicates,
            "invalid_rows": invalid_rows,
            "date_range": {"start": start_date, "end": end_date},
            "warnings": warnings,
        }

        return parsed_records, audit

    def read_file_to_dataframe(self, file_bytes: bytes, filename: str) -> pd.DataFrame:
        """Parses byte payload of CSV or XLSX into a pandas DataFrame."""
        fn = filename.lower()
        if fn.endswith(".xlsx") or fn.endswith(".xls"):
            return pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
        elif fn.endswith(".csv"):
            try:
                return pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8")
            except UnicodeDecodeError:
                return pd.read_csv(io.BytesIO(file_bytes), encoding="latin1")
        else:
            raise ValueError(f"Unsupported file format '{filename}'. Supported formats are CSV and XLSX.")

    def analyze_statement(
        self,
        transactions: Any,
        audit: Optional[Dict[str, Any]] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes real FinStream AI dual-ML risk scoring (XGBoost + Isolation Forest)
        and SHAP explanation on every transaction in chronological sequence, then
        computes financial summaries, risk tiers, and category/monthly breakdowns.
        """
        if isinstance(transactions, (bytes, str)):
            raw_bytes = transactions.encode("utf-8") if isinstance(transactions, str) else transactions
            fn = filename or "statement.csv"
            df = self.read_file_to_dataframe(raw_bytes, fn)
            parsed_txs, parsed_audit = self.parse_dataframe(df)
            res = self.analyze_statement(parsed_txs, parsed_audit, filename=fn)
            res["filename"] = fn
            return res

        if audit is None:
            audit = {"original_rows": len(transactions), "valid_transactions": len(transactions)}

        if not transactions:
            return {
                "summary": {
                    "total_transactions": 0,
                    "total_debit": 0.0,
                    "total_credit": 0.0,
                    "highest_transaction": 0.0,
                    "lowest_transaction": 0.0,
                    "average_transaction": 0.0,
                    "highest_transaction_amount": 0.0,
                    "lowest_transaction_amount": 0.0,
                    "average_transaction_amount": 0.0,
                    "high_risk_count": 0,
                    "medium_risk_count": 0,
                    "low_risk_count": 0,
                    "avg_risk_score": 0.0,
                },
                "audit": audit,
                "highest_risk_transactions": [],
                "medium_risk_transactions": [],
                "lowest_risk_transactions": [],
                "category_breakdown": [],
                "daily_timeline": [],
                "transactions": [],
            }

        # 1. Initialize ML inference engine & feature engine
        inference_engine = load_inference_engine()
        self.feature_engine.reset()

        analyzed_transactions: List[Dict[str, Any]] = []
        score_sum = 0.0
        high_count = 0
        med_count = 0
        low_count = 0

        total_debit = 0.0
        total_credit = 0.0
        amounts = []

        category_stats: Dict[str, Dict[str, Any]] = {}
        daily_stats: Dict[str, Dict[str, Any]] = {}

        # 2. Process each transaction in chronological order through the real ML pipeline
        for tx in transactions:
            amt = float(tx.get("amount", 0.0))
            direction = tx.get("direction", "DEBIT")
            cat = tx.get("merchant_category", "GENERAL")
            date_str = str(tx.get("timestamp", ""))[:10]  # YYYY-MM-DD

            amounts.append(amt)
            if direction == "DEBIT":
                total_debit += amt
            else:
                total_credit += amt

            # Enrich through real 23-feature sliding window
            enriched = self.feature_engine.enrich_transaction(tx)

            # Score through real XGBoost + Isolation Forest + SHAP
            prediction = inference_engine.predict_single(enriched, explain=True, top_n_shap=5)

            score = float(prediction.get("hybrid_risk_score", 0.0))
            risk_lvl = str(prediction.get("risk_level", "LOW")).upper()
            score_sum += score

            if risk_lvl == "HIGH":
                high_count += 1
            elif risk_lvl == "MEDIUM":
                med_count += 1
            else:
                low_count += 1

            # Extract 23 model features
            from features.feature_definitions import ALL_ENGINEERED_FEATURE_COLUMNS
            feature_profile = {k: enriched.get(k) for k in ALL_ENGINEERED_FEATURE_COLUMNS if k in enriched}

            top_shap = prediction.get("top_shap_features", [])
            if top_shap:
                primary = top_shap[0]
                dir_str = "increased" if primary.get("shap_value", 0) > 0 else "reduced"
                explanation_text = f"Primary risk factor: {primary.get('feature')} {dir_str} score by {abs(primary.get('shap_value', 0)):.4f}."
            else:
                explanation_text = "Transaction matches standard customer profile."

            evaluated_tx = {
                **tx,
                "hybrid_risk_score": round(score, 4),
                "risk_level": risk_lvl,
                "xgboost_probability": round(float(prediction.get("xgboost_probability", 0.0)), 4),
                "isolation_forest_normalized": round(float(prediction.get("isolation_forest_normalized", 0.0)), 4),
                "isolation_forest_score": round(float(prediction.get("isolation_forest_score", 0.0)), 4),
                "top_shap_features": top_shap,
                "explanation_text": explanation_text,
                "features": feature_profile,
            }
            analyzed_transactions.append(evaluated_tx)

            # Category aggregation
            if cat not in category_stats:
                category_stats[cat] = {"category": cat, "transactions": 0, "amount": 0.0, "high_risk": 0}
            category_stats[cat]["transactions"] += 1
            category_stats[cat]["amount"] = round(category_stats[cat]["amount"] + amt, 2)
            if risk_lvl == "HIGH":
                category_stats[cat]["high_risk"] += 1

            # Daily timeline aggregation
            if date_str not in daily_stats:
                daily_stats[date_str] = {
                    "date": date_str,
                    "total_amount": 0.0,
                    "transaction_count": 0,
                    "high_risk_count": 0,
                    "score_sum": 0.0,
                }
            daily_stats[date_str]["total_amount"] = round(daily_stats[date_str]["total_amount"] + amt, 2)
            daily_stats[date_str]["transaction_count"] += 1
            daily_stats[date_str]["score_sum"] += score
            if risk_lvl == "HIGH":
                daily_stats[date_str]["high_risk_count"] += 1

        # 3. Calculate Financial & Risk Totals
        total_tx = len(analyzed_transactions)
        avg_amt = round(sum(amounts) / total_tx, 2) if total_tx > 0 else 0.0
        highest_amt = max(amounts) if amounts else 0.0
        lowest_amt = min(amounts) if amounts else 0.0
        avg_score = round(score_sum / total_tx, 4) if total_tx > 0 else 0.0

        # 4. Filter rankings: Highest Risk, Medium Risk, Lowest Risk
        sorted_by_risk_desc = sorted(analyzed_transactions, key=lambda t: t["hybrid_risk_score"], reverse=True)
        sorted_by_risk_asc = sorted(analyzed_transactions, key=lambda t: t["hybrid_risk_score"])

        highest_risk_txs = [t for t in sorted_by_risk_desc if t["risk_level"] == "HIGH"][:15]
        if not highest_risk_txs:
            # Fallback to top scored if no high risk
            highest_risk_txs = sorted_by_risk_desc[:10]

        medium_risk_txs = [t for t in analyzed_transactions if t["risk_level"] == "MEDIUM"][:15]

        lowest_risk_txs = [t for t in sorted_by_risk_asc if t["risk_level"] == "LOW"][:15]

        # 5. Format Timeline & Categories
        timeline_list = []
        for day in sorted(daily_stats.keys()):
            item = daily_stats[day]
            count = item["transaction_count"]
            timeline_list.append({
                "date": day,
                "total_amount": item["total_amount"],
                "transaction_count": count,
                "high_risk_count": item["high_risk_count"],
                "avg_risk_score": round(item["score_sum"] / count, 4) if count > 0 else 0.0,
            })

        cat_list = sorted(list(category_stats.values()), key=lambda c: c["amount"], reverse=True)

        summary = {
            "total_transactions": total_tx,
            "total_debit": round(total_debit, 2),
            "total_credit": round(total_credit, 2),
            "highest_transaction": highest_amt,
            "lowest_transaction": lowest_amt,
            "average_transaction": avg_amt,
            "highest_transaction_amount": highest_amt,
            "lowest_transaction_amount": lowest_amt,
            "average_transaction_amount": avg_amt,
            "high_risk_count": high_count,
            "medium_risk_count": med_count,
            "low_risk_count": low_count,
            "avg_risk_score": avg_score,
            "highest_risk_transaction": highest_risk_txs[0] if highest_risk_txs else None,
            "lowest_risk_transaction": lowest_risk_txs[0] if lowest_risk_txs else None,
        }

        res = {
            "summary": summary,
            "audit": audit,
            "highest_risk_transactions": highest_risk_txs,
            "medium_risk_transactions": medium_risk_txs,
            "lowest_risk_transactions": lowest_risk_txs,
            "category_breakdown": cat_list,
            "daily_timeline": timeline_list,
            "transactions": analyzed_transactions,
        }
        if filename:
            res["filename"] = filename
        return res

    @staticmethod
    def export_analysis_report(statement_analysis: Dict[str, Any], file_format: str = "csv") -> Tuple[bytes, str, str]:
        """
        Exports the analyzed statement transactions and risk assessments into a clean CSV or XLSX file.
        Returns (file_bytes, mime_type, filename).
        """
        txs = statement_analysis.get("transactions", [])
        export_rows = []

        for t in txs:
            top_shap_str = "; ".join([
                f"{item.get('feature')}: {item.get('shap_value'):+.4f}"
                for item in t.get("top_shap_features", [])[:3]
            ])
            export_rows.append({
                "Transaction ID": t.get("transaction_id"),
                "Date": t.get("timestamp"),
                "Description": t.get("description"),
                "Direction": t.get("direction"),
                "Amount (INR)": t.get("amount"),
                "Category": t.get("merchant_category"),
                "Channel": t.get("channel"),
                "City": t.get("city"),
                "Risk Score": t.get("hybrid_risk_score"),
                "Risk Level": t.get("risk_level"),
                "XGBoost Probability": t.get("xgboost_probability"),
                "Isolation Forest Score": t.get("isolation_forest_normalized"),
                "Top SHAP Factors": top_shap_str,
            })

        df = pd.DataFrame(export_rows)
        ts_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        if file_format.lower() == "xlsx":
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Risk Analysis")
            buffer.seek(0)
            return buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"finstream_statement_analysis_{ts_slug}.xlsx"
        else:
            csv_str = df.to_csv(index=False, encoding="utf-8")
            return csv_str.encode("utf-8"), "text/csv", f"finstream_statement_analysis_{ts_slug}.csv"

    @staticmethod
    def generate_sample_statement_csv(num_days: int = 30) -> str:
        """
        Generates a synthetic 1-month bank statement CSV representing realistic
        Indian banking activity (UPI, POS, Online, ATMs) with normal transactions
        and a few suspicious outliers for rich demonstration.
        """
        import random
        from datetime import timedelta

        base_date = datetime(2026, 9, 1, 9, 0, 0, tzinfo=timezone.utc)
        rows = ["Date,Transaction ID,Description,Debit,Credit,Balance,Category,Channel,City"]
        current_balance = 85400.0

        tx_counter = 1000

        # Normal daily transactions
        for day in range(num_days):
            day_date = base_date + timedelta(days=day)
            num_txs = random.randint(2, 5)

            for _ in range(num_txs):
                tx_counter += 1
                tx_id = f"STMT{tx_counter}"
                time_offset = timedelta(hours=random.randint(8, 22), minutes=random.randint(0, 59))
                tx_time = (day_date + time_offset).strftime("%Y-%m-%d %H:%M")

                is_credit = random.random() < 0.15  # 15% credits (salary, refund, interest)
                if is_credit:
                    amt = round(random.uniform(500.0, 45000.0), 2)
                    current_balance += amt
                    rows.append(f"{tx_time},{tx_id},Salary / Fund Transfer,,{amt:.2f},{current_balance:.2f},GENERAL,NET_BANKING,Mumbai")
                else:
                    cat = random.choice(["GROCERY", "DINING", "SHOPPING", "TRAVEL", "UTILITIES"])
                    merchant = random.choice(CATEGORY_KEYWORD_PATTERNS.get(cat, ["Store"]))
                    amt = round(random.uniform(150.0, 3200.0), 2)
                    current_balance -= amt
                    channel = random.choice(["UPI", "POS", "ONLINE"])
                    city = random.choice(["Mumbai", "Bengaluru", "Delhi"])
                    rows.append(f"{tx_time},{tx_id},UPI/{merchant.title()}/Payment,{amt:.2f},,{current_balance:.2f},{cat},{channel},{city}")

        # Inject 3 specific demonstration anomalies
        # Anomaly 1: High Amount luxury outlier on Day 12
        tx_counter += 1
        t12 = (base_date + timedelta(days=12, hours=15, minutes=30)).strftime("%Y-%m-%d %H:%M")
        current_balance -= 185000.0
        rows.append(f"{t12},STMT{tx_counter},Tanishq Jewelers Flagship Luxury Purchase,185000.00,,{current_balance:.2f},LUXURY,ONLINE,Mumbai")

        # Anomaly 2: Rapid Velocity Spike on Day 21 (multiple rapid purchases)
        for i in range(4):
            tx_counter += 1
            t21 = (base_date + timedelta(days=21, hours=23, minutes=10 + i*2)).strftime("%Y-%m-%d %H:%M")
            amt = 12500.0 + (i * 4500.0)
            current_balance -= amt
            rows.append(f"{t21},STMT{tx_counter},Apple Electronics Store Order #{i+1},{amt:.2f},,{current_balance:.2f},ELECTRONICS,ONLINE,Delhi")

        return "\n".join(rows)


# =============================================================================
# Standalone Module-Level Utilities
# =============================================================================

def detect_statement_columns(headers: List[str]) -> Dict[str, Optional[str]]:
    """Convenience wrapper to detect semantic column roles from a list of header strings."""
    analyzer = BankStatementAnalyzer()
    df = pd.DataFrame(columns=headers)
    return analyzer.detect_columns(df)


def clean_and_normalize_statement(file_content: bytes, filename: str = "statement.csv") -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Convenience wrapper to parse and clean raw statement file bytes."""
    analyzer = BankStatementAnalyzer()
    if filename.lower().endswith(".xlsx"):
        df = pd.read_excel(io.BytesIO(file_content))
    else:
        df = pd.read_csv(io.BytesIO(file_content))
    return analyzer.parse_dataframe(df)


def generate_sample_statement_csv(days: int = 30) -> bytes:
    """Convenience wrapper to generate sample statement CSV as bytes."""
    analyzer = BankStatementAnalyzer()
    return analyzer.generate_sample_statement_csv(days).encode("utf-8")


def export_analysis_report(statement_analysis: Dict[str, Any], file_format: str = "csv") -> bytes:
    """Convenience wrapper to export statement analysis as CSV or XLSX bytes."""
    content_bytes, _, _ = BankStatementAnalyzer.export_analysis_report(statement_analysis, file_format)
    return content_bytes

