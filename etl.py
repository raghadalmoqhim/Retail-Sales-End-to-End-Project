import pandas as pd
from sqlalchemy import create_engine
from urllib.parse import quote_plus


# Load Data

file_path = "Data/retail_sale.xlsx"  
sheet_name = "retail_sales_dataset" 

df = pd.read_excel(file_path, sheet_name=sheet_name)

print("Raw data preview:")
print(df.head())
print("\nColumns:")
print(df.columns.tolist())


#  Cleaning

df.columns = [col.strip().replace(" ", "_") for col in df.columns]

# expected columns after cleaning:
# Transaction_ID, Date, Customer_ID, Gender, Age,
# Product_Category, Quantity, Price_per_Unit, Total_Amount

df = df.drop_duplicates()

df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")

numeric_cols = ["Age", "Quantity", "Price_per_Unit", "Total_Amount"]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=["Transaction_ID", "Date", "Customer_ID", "Product_Category", "Total_Amount"])

# Feature Engineering

def get_age_group(age):
    if pd.isna(age):
        return "Unknown"
    if age <= 27:
        return "18-27"
    elif age <= 37:
        return "28-37"
    elif age <= 47:
        return "38-47"
    elif age <= 57:
        return "48-57"
    else:
        return "58+"

df["Age_Group"] = df["Age"].apply(get_age_group)
df["Year"] = df["Date"].dt.year
df["Month"] = df["Date"].dt.month
df["Month_Name"] = df["Date"].dt.strftime("%b")
df["Quarter"] = df["Date"].dt.quarter

# simulated profit
df["Profit"] = df["Total_Amount"] * 0.30

# DateKey example: 20231124
df["DateKey"] = df["Date"].dt.strftime("%Y%m%d").astype(int)


# Create Dimension Tables

dim_customer = (
    df[["Customer_ID", "Gender", "Age", "Age_Group"]]
    .drop_duplicates()
    .reset_index(drop=True)
)
dim_customer["CustomerKey"] = range(1, len(dim_customer) + 1)
dim_customer = dim_customer[["CustomerKey", "Customer_ID", "Gender", "Age", "Age_Group"]]

dim_product = (
    df[["Product_Category"]]
    .drop_duplicates()
    .reset_index(drop=True)
)
dim_product["ProductKey"] = range(1, len(dim_product) + 1)
dim_product = dim_product[["ProductKey", "Product_Category"]]

dim_date = (
    df[["Date", "DateKey", "Year", "Month", "Month_Name", "Quarter"]]
    .drop_duplicates()
    .sort_values("Date")
    .reset_index(drop=True)
)
dim_date = dim_date[["DateKey", "Date", "Year", "Month", "Month_Name", "Quarter"]]


# Build Fact Table

fact_sales = df.merge(dim_customer, on=["Customer_ID", "Gender", "Age", "Age_Group"], how="left")
fact_sales = fact_sales.merge(dim_product, on="Product_Category", how="left")

fact_sales = fact_sales[
    [
        "Transaction_ID",
        "CustomerKey",
        "ProductKey",
        "DateKey",
        "Quantity",
        "Price_per_Unit",
        "Total_Amount",
        "Profit",
    ]
].copy()

fact_sales = fact_sales.rename(
    columns={
        "Transaction_ID": "SalesID",
        "Price_per_Unit": "UnitPrice",
        "Total_Amount": "SalesAmount",
    }
)


# Save CSV Copies

dim_customer.to_csv("Data/dim_customer.csv", index=False)
dim_product.to_csv("Data/dim_product.csv", index=False)
dim_date.to_csv("Data/dim_date.csv", index=False)
fact_sales.to_csv("Data/fact_sales.csv", index=False)

print("\nFiles exported successfully:")
print("- Data/dim_customer.csv")
print("- Data/dim_product.csv")
print("- Data/dim_date.csv")
print("- Data/fact_sales.csv")


# Load to MySQL

username = "root"
password = quote_plus("your_password")
host = "localhost"
port = 3306
database = "retail_dw"

engine = create_engine(
    f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
)

with engine.connect() as conn:
    print("Connected to MySQL successfully!")

dim_customer.to_sql("dim_customer", con=engine, if_exists="replace", index=False)
dim_product.to_sql("dim_product", con=engine, if_exists="replace", index=False)
dim_date.to_sql("dim_date", con=engine, if_exists="replace", index=False)
fact_sales.to_sql("fact_sales", con=engine, if_exists="replace", index=False)

print("Data loaded to MySQL successfully!")