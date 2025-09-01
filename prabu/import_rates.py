import pandas as pd
import calendar
from datetime import datetime

def get_end_of_month_dates(start_date, end_date):
    end_of_month_dates = []
    current_date = start_date

    while current_date <= end_date:
        last_day = calendar.monthrange(current_date.year, current_date.month)[1]
        end_of_month_date = datetime(current_date.year, current_date.month, last_day)
        end_of_month_dates.append(end_of_month_date.strftime('%Y-%m-%d'))
        current_date = current_date + pd.DateOffset(months=1)

    return end_of_month_dates

def adjust_dates_to_available(rates, dates):
    adjusted_dates = []
    for date in dates:
        current_date = pd.to_datetime(date)
        while current_date not in rates['DATE'].dt.normalize().values:
            current_date -= pd.Timedelta(days=1)
        adjusted_dates.append(current_date.strftime('%Y-%m-%d'))
    return adjusted_dates

def adjust_rate_for_currency(currency, rate):
    """
    Adjust exchange rates based on currency-specific quotation methods.
    THB rates from SBI are quoted per 100 INR, so we divide by 100 to get per 1 INR.
    """
    if currency == "THB":
        # THB rates are per 100 INR, convert to per 1 INR
        return rate / 100
    else:
        # Other currencies are already per 1 INR
        return rate

def format_beancount_price(date, currency, rate, base_currency="INR"):
    """Format exchange rate as beancount price directive"""
    return f"{date} price {currency} {rate:.6f} {base_currency}"

def get_forex_rates_beancount(currency, start_date, end_date, base_currency="INR"):
    # Define the URL based on the currency
    url = f"https://raw.githubusercontent.com/sahilgupta/sbi-fx-ratekeeper/main/csv_files/SBI_REFERENCE_RATES_{currency}.csv"

    try:
        # Read the CSV file from the GitHub repository for the specified currency rates
        rates = pd.read_csv(url)

        # Convert the date column to datetime for easier filtering
        rates['DATE'] = pd.to_datetime(rates.iloc[:, 0], errors='coerce')

        # Get end-of-month dates
        end_of_month_dates = get_end_of_month_dates(start_date, end_date)

        # Adjust dates to available dates
        required_dates = adjust_dates_to_available(rates, end_of_month_dates)

        # Filter the data for the required dates
        filtered_rates = rates[rates['DATE'].dt.normalize().isin(pd.to_datetime(required_dates))].copy()

        # Format the DATE column to YYYY-MM-DD using .loc to avoid SettingWithCopyWarning
        filtered_rates.loc[:, 'DATE'] = filtered_rates['DATE'].dt.strftime('%Y-%m-%d')

        # For THB, use column -2, for others use column 2
        rate_column = -2 if currency == "THB" else 2
        result_data = filtered_rates.iloc[:, [0, rate_column]]

        # Generate beancount price directives
        print(f"; Exchange rates for {currency}")
        if currency == "THB":
            print(f"; Note: THB rates converted from per-100-INR to per-1-INR")
        for _, row in result_data.iterrows():
            # Extract just the date part (first 10 characters YYYY-MM-DD)
            date = str(row.iloc[0])[:10]
            raw_rate = row.iloc[1]
            # Adjust rate based on currency quotation method
            adjusted_rate = adjust_rate_for_currency(currency, raw_rate)
            print(format_beancount_price(date, currency, adjusted_rate, base_currency))

        return result_data
    except Exception as e:
        print(f"An error occurred: {e}")
        return pd.DataFrame(columns=['DATE', 'TT BUY'])

# Define the date range
start_date = pd.to_datetime("2024-03-28")
end_date = pd.to_datetime("2025-03-31")

# Example usage for different currencies
currencies = ["USD", "THB", "SGD"]  # Add more currencies as needed

for currency in currencies:
    print(f"\n; === {currency} Exchange Rates ===")
    my_rates = get_forex_rates_beancount(currency, start_date, end_date, "INR")
    print()  # Empty line for readability

# If you want to use just one currency, uncomment and modify the lines below:
# currency = "THB"
# my_rates = get_forex_rates_beancount(currency, start_date, end_date, "INR")
