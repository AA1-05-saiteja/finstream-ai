# Phase 2 — Synthetic Transaction Generator & Behavioral Simulation

This document explains the design, mathematical distributions, behavioral state management, and scenario generation logic in **FinStream AI**.

## 1. Objective & Behavioral Philosophy
Real financial fraud detection relies heavily on contextual and behavioral anomalies (e.g., sudden spikes above standard spending, unfamiliar merchant verticals, geographical displacement, or rapid burst velocities). To train and test ML models realistically without using sensitive banking data, the generator models synthetic customer personas rather than generating uniformly random numbers.

## 2. Behavioral Persona & Account Pool
Each synthetic account (`ACC0001` ... `ACC1000`) is assigned:
- **User Classification**:
  - `NORMAL_USER` (~85%): Average amount ₹300 – ₹2,200, low standard deviation, prefers everyday categories (groceries, dining, utilities), uses 1–2 known devices.
  - `HIGH_VALUE_USER` (~15%): Average amount ₹8,000 – ₹25,000, higher dispersion, prefers travel, luxury, and high-end electronics.
- **Home City**: Pinned to major Indian metropolitan regions (`Hyderabad`, `Bengaluru`, `Chennai`, `Mumbai`, `Delhi`, `Pune`, `Kolkata`, `Ahmedabad`).
- **Device Fingerprints**: Registered known device IDs (`DEVxxxx`).
- **Channel Affinity**: Online, POS (Point of Sale), Mobile, and ATM.

## 3. Supported Anomaly Scenarios

| Scenario | Behavioral Mechanism | Analytical Target |
| :--- | :--- | :--- |
| `normal` | Sampled from account Gaussian baseline clipped to valid bounds. | Normal baseline inference |
| `high_amount` | Multiplies baseline spending by 12x–35x (e.g. ₹65,000 – ₹350,000) on high-risk categories. | Spending deviation & Z-score features |
| `velocity_spike` | Emits a rapid burst of 3–6 transactions for the same account 1–4 seconds apart. | Rolling window transaction velocity (1m/5m/1h) |
| `new_device` | Emits a transaction originating from an unseen device ID. | `is_new_device` categorical feature |
| `unusual_merchant` | Emits a transaction targeting an uncharacteristic merchant category. | Merchant category shift detection |
| `unusual_location` | Emits a transaction originating from a city distant from the account's home city. | Location displacement anomaly |
| `rapid_device_switching` | Generates successive transactions cycling through new devices. | Device velocity anomaly |
| `mixed` | Probabilistic blend representing realistic live traffic. | End-to-end streaming workload |

## 4. Pydantic Transaction Schema

```json
{
  "transaction_id": "TX000001",
  "timestamp": "2026-10-01T12:30:20Z",
  "account_id": "ACC0102",
  "amount": 1250.50,
  "currency": "INR",
  "merchant_id": "MER_GROC_004",
  "merchant_category": "groceries",
  "city": "Hyderabad",
  "device_id": "DEV0021",
  "channel": "POS",
  "card_present": true,
  "transaction_type": "PURCHASE"
}
```

## 5. Execution Commands

```powershell
# Continuous generation at 5 TPS (mixed scenario)
python -m producer.transaction_generator --rate 5

# Deterministic generation for 30 seconds with 500 accounts
python -m producer.transaction_generator --rate 10 --accounts 500 --duration 30 --seed 42

# Explicit suspicious high amount scenario
python -m producer.transaction_generator --scenario high_amount --rate 2 --duration 10
```
