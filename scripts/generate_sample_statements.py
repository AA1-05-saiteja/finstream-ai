"""
Generates synthetic demonstration bank statements for FinStream AI.
- data/sample_data/normal_monthly_statement.csv
- data/sample_data/suspicious_anomalies_statement.xlsx

All records are 100% synthetically generated for academic demonstration.
"""

from datetime import datetime
import pandas as pd

def generate_normal_statement():
    rows = [
        # Date, Transaction ID, Description, Debit, Credit, Balance, Category, Merchant, Channel
        ("2026-10-01 09:30:00", "TXN1001", "Monthly Salary Credit - InnoTech Solutions", None, 150000.0, 275000.0, "Salary", "InnoTech Solutions", "NEFT"),
        ("2026-10-02 11:15:00", "TXN1002", "UPI/Swiggy/Order-88219/Lunch", 540.0, None, 274460.0, "Dining", "Swiggy", "UPI"),
        ("2026-10-03 10:00:00", "TXN1003", "NEFT/House Rent Oct 2026/Landlord HDFC", 32000.0, None, 242460.0, "Transfer", "Landlord Rental", "NEFT"),
        ("2026-10-04 18:45:00", "TXN1004", "POS/DMart Supermarket/Groceries", 4650.0, None, 237810.0, "Grocery", "DMart", "POS"),
        ("2026-10-05 08:30:00", "TXN1005", "UPI/Uber India/Daily Commute", 320.0, None, 237490.0, "Travel", "Uber", "UPI"),
        ("2026-10-06 20:10:00", "TXN1006", "UPI/Zomato/Dinner with Friends", 980.0, None, 236510.0, "Dining", "Zomato", "UPI"),
        ("2026-10-07 14:20:00", "TXN1007", "POS/Apollo Pharmacy/Health Supplements", 1250.0, None, 235260.0, "Healthcare", "Apollo Pharmacy", "POS"),
        ("2026-10-08 19:30:00", "TXN1008", "ECOM/Amazon India/Household Supplies", 2850.0, None, 232410.0, "Shopping", "Amazon", "NetBanking"),
        ("2026-10-09 12:00:00", "TXN1009", "UPI/Blinkit/Instant Grocery Delivery", 420.0, None, 231990.0, "Grocery", "Blinkit", "UPI"),
        ("2026-10-10 16:15:00", "TXN1010", "ATM/Cash Withdrawal/HDFC ATM Indiranagar", 5000.0, None, 226990.0, "Cash", "HDFC Bank ATM", "ATM"),
        ("2026-10-11 11:30:00", "TXN1011", "UPI/Starbucks Coffee/Weekend Meet", 450.0, None, 226540.0, "Dining", "Starbucks", "UPI"),
        ("2026-10-12 10:00:00", "TXN1012", "BillPay/BESCOM Electricity Bill Oct", 2350.0, None, 224190.0, "Utilities", "BESCOM", "NetBanking"),
        ("2026-10-13 10:15:00", "TXN1013", "BillPay/Airtel Broadband Monthly", 1179.0, None, 223011.0, "Utilities", "Airtel", "NetBanking"),
        ("2026-10-14 17:40:00", "TXN1014", "UPI/Zepto/Groceries & Snacks", 380.0, None, 222631.0, "Grocery", "Zepto", "UPI"),
        ("2026-10-15 13:20:00", "TXN1015", "POS/Shell Petrol Pump/Fuel Refill", 2500.0, None, 220131.0, "Travel", "Shell Fuel", "POS"),
        ("2026-10-16 21:00:00", "TXN1016", "ECOM/Netflix/Monthly Standard Plan", 649.0, None, 219482.0, "Entertainment", "Netflix", "NetBanking"),
        ("2026-10-17 15:30:00", "TXN1017", "POS/Myntra Fashion/Festival Apparel", 4200.0, None, 215282.0, "Shopping", "Myntra", "NetBanking"),
        ("2026-10-18 19:45:00", "TXN1018", "UPI/Dominos Pizza/Family Dinner", 890.0, None, 214392.0, "Dining", "Dominos", "UPI"),
        ("2026-10-19 09:10:00", "TXN1019", "UPI/Uber India/Office Commute", 380.0, None, 214012.0, "Travel", "Uber", "UPI"),
        ("2026-10-20 14:00:00", "TXN1020", "UPI/Friend Reimbursement/Lunch Split", None, 650.0, 214662.0, "Transfer", "Arun Kumar", "UPI"),
        ("2026-10-21 17:30:00", "TXN1021", "POS/Nature Basket/Organic Vegetables", 1850.0, None, 212812.0, "Grocery", "Nature Basket", "POS"),
        ("2026-10-22 12:15:00", "TXN1022", "UPI/BookMyShow/Movie Tickets PVR", 760.0, None, 212052.0, "Entertainment", "BookMyShow", "UPI"),
        ("2026-10-23 10:45:00", "TXN1023", "UPI/Swiggy Instamart/Essentials", 520.0, None, 211532.0, "Grocery", "Swiggy", "UPI"),
        ("2026-10-24 16:00:00", "TXN1024", "POS/Decathlon Sports/Gym Gear", 2600.0, None, 208932.0, "Shopping", "Decathlon", "POS"),
        ("2026-10-25 11:20:00", "TXN1025", "UPI/Chai Point/Office Tea Break", 180.0, None, 208752.0, "Dining", "Chai Point", "UPI"),
        ("2026-10-26 18:30:00", "TXN1026", "POS/Reliance Digital/Wireless Earbuds", 3499.0, None, 205253.0, "Electronics", "Reliance Digital", "POS"),
        ("2026-10-27 09:00:00", "TXN1027", "UPI/Metro SmartCard/Online Recharge", 500.0, None, 204753.0, "Travel", "Namma Metro", "UPI"),
        ("2026-10-28 20:00:00", "TXN1028", "UPI/Zomato/Dinner Delivery", 710.0, None, 204043.0, "Dining", "Zomato", "UPI"),
        ("2026-10-29 15:10:00", "TXN1029", "POS/Fabindia/Diwali Gift Items", 3200.0, None, 200843.0, "Shopping", "Fabindia", "POS"),
        ("2026-10-30 11:00:00", "TXN1030", "UPI/BigBasket/Monthly Grocery Part 2", 3650.0, None, 197193.0, "Grocery", "BigBasket", "UPI"),
        ("2026-10-31 19:30:00", "TXN1031", "POS/Barbeque Nation/Team Celebration", 2800.0, None, 194393.0, "Dining", "Barbeque Nation", "POS"),
    ]

    df = pd.DataFrame(rows, columns=[
        "Date", "Transaction ID", "Description", "Debit", "Credit", "Balance", "Category", "Merchant", "Channel"
    ])
    output_path = "data/sample_data/normal_monthly_statement.csv"
    df.to_csv(output_path, index=False)
    print(f"Generated normal statement: {output_path} ({len(df)} transactions)")

def generate_suspicious_statement():
    rows = [
        # Normal baseline activity in first few days
        ("2026-10-01 09:30:00", "TXN2001", "Monthly Salary Credit - Fintech Corp", None, 120000.0, 215000.0, "Salary", "Fintech Corp", "NEFT"),
        ("2026-10-02 12:15:00", "TXN2002", "UPI/Swiggy/Lunch Order", 450.0, None, 214550.0, "Dining", "Swiggy", "UPI"),
        ("2026-10-03 10:00:00", "TXN2003", "NEFT/House Rent Monthly", 28000.0, None, 186550.0, "Transfer", "Landlord", "NEFT"),
        ("2026-10-04 14:20:00", "TXN2004", "POS/DMart/Household Groceries", 3450.0, None, 183100.0, "Grocery", "DMart", "POS"),
        
        # ANOMALY 1: Midnight Micro-Probe followed by Sudden Massive Luxury Outlier
        ("2026-10-07 03:02:15", "TXN2005", "UPI/Card Verification Micro-Charge", 10.0, None, 183090.0, "Shopping", "Payment Gateway Probe", "UPI"),
        ("2026-10-07 03:04:45", "TXN2006", "POS/Tanishq Luxury Jewellery High Value", 95000.0, None, 88090.0, "Luxury", "Tanishq Jewellers", "POS"),

        # Routine mid-month transactions
        ("2026-10-10 11:30:00", "TXN2007", "UPI/Uber India/City Travel", 340.0, None, 87750.0, "Travel", "Uber", "UPI"),
        ("2026-10-11 16:45:00", "TXN2008", "POS/Apollo Pharmacy/Medicines", 680.0, None, 87070.0, "Healthcare", "Apollo Pharmacy", "POS"),
        ("2026-10-13 19:15:00", "TXN2009", "UPI/Zomato/Dinner", 720.0, None, 86350.0, "Dining", "Zomato", "UPI"),
        
        # ANOMALY 2: High Velocity Burst (Rapid repeated transactions within 3 minutes)
        ("2026-10-15 22:40:10", "TXN2010", "POS/Electronics MegaStore/Fast Checkout 1", 9999.0, None, 76351.0, "Electronics", "Electronics Store", "POS"),
        ("2026-10-15 22:41:05", "TXN2011", "POS/Electronics MegaStore/Fast Checkout 2", 9999.0, None, 66352.0, "Electronics", "Electronics Store", "POS"),
        ("2026-10-15 22:42:15", "TXN2012", "POS/Electronics MegaStore/Fast Checkout 3", 9999.0, None, 56353.0, "Electronics", "Electronics Store", "POS"),
        ("2026-10-15 22:43:30", "TXN2013", "POS/Electronics MegaStore/Fast Checkout 4", 9999.0, None, 46354.0, "Electronics", "Electronics Store", "POS"),

        # Routine transactions
        ("2026-10-18 10:10:00", "TXN2014", "UPI/Blinkit/Breakfast Milk Bread", 280.0, None, 46074.0, "Grocery", "Blinkit", "UPI"),
        ("2026-10-19 14:00:00", "TXN2015", "BillPay/BESCOM Electric Bill", 1950.0, None, 44124.0, "Utilities", "BESCOM", "NetBanking"),
        
        # ANOMALY 3: Large Round-Sum Wire Transfer to Unknown Beneficiary
        ("2026-10-22 04:15:00", "TXN2016", "IMPS/Urgent Wire Outflow Unknown Acc", 40000.0, None, 4124.0, "Transfer", "Unknown Recipient", "IMPS"),

        # Subsequent recovery and normal spending
        ("2026-10-25 15:00:00", "TXN2017", "UPI/Reimbursement Received", None, 15000.0, 19124.0, "Transfer", "Colleague Transfer", "UPI"),
        ("2026-10-26 12:30:00", "TXN2018", "UPI/Starbucks Coffee", 390.0, None, 18734.0, "Dining", "Starbucks", "UPI"),
        ("2026-10-28 18:20:00", "TXN2019", "POS/DMart/Weekend Supplies", 2150.0, None, 16584.0, "Grocery", "DMart", "POS"),
        ("2026-10-31 20:00:00", "TXN2020", "UPI/Zomato/End of Month Dinner", 850.0, None, 15734.0, "Dining", "Zomato", "UPI"),
    ]

    df = pd.DataFrame(rows, columns=[
        "Date", "Transaction ID", "Description", "Debit", "Credit", "Balance", "Category", "Merchant", "Channel"
    ])
    
    output_path = "data/sample_data/suspicious_anomalies_statement.xlsx"
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Transactions", index=False)
        # Also include a metadata sheet explaining it's synthetic demonstration data
        meta_df = pd.DataFrame([
            {"Key": "Dataset Type", "Value": "SYNTHETIC DEMONSTRATION DATA"},
            {"Key": "Purpose", "Value": "FinStream AI Anomaly & Fraud Detection Validation"},
            {"Key": "Simulated Scenarios", "Value": "1) Micro-probe + Midnight High Value Luxury (₹95,000), 2) Rapid POS Velocity Burst (4 x ₹9,999 within 3 mins), 3) Urgent Off-Hours Wire Transfer (₹40,000 at 04:15 AM)"},
            {"Key": "Disclaimer", "Value": "All entity names, accounts, and transactions are purely fictional for academic testing."}
        ])
        meta_df.to_excel(writer, sheet_name="Notice & Metadata", index=False)
        
    print(f"Generated suspicious statement: {output_path} ({len(df)} transactions)")

if __name__ == "__main__":
    generate_normal_statement()
    generate_suspicious_statement()
