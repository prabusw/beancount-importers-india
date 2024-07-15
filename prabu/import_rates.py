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

def get_forex_rates(currency, start_date, end_date):
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

        # Return the filtered data with DATE and the third column (TT buying rate)
        return filtered_rates.iloc[:, [0, 2]]
    except Exception as e:
        print(f"An error occurred: {e}")
        return pd.DataFrame(columns=['DATE', 'TT BUY'])

# Define the date range
start_date = pd.to_datetime("2023-04-01")
end_date = pd.to_datetime("2024-03-31")
currency = "USD"

# For THB, remember to change the column reference to -2 from 2 in the line return filtered_rates.iloc[:, [0, -2]]

# Call the function for SGD
my_rates = get_forex_rates(currency, start_date, end_date)
print("Exchange rates for", currency)
print(my_rates)

# You can create a function that determines the required dates based on the logic of either picking the end of the month or the nearest available date to the end of the month. This function will iterate over each month, check if the last day of the month is available, and if not, keep checking one day less until a date is found.

# Here’s the updated script to include this logic:

# In this script:

#     get_end_of_month_dates: Generates the end-of-month dates for the specified year and months.
#     adjust_dates_to_available: Adjusts the end-of-month dates to the nearest available date in the data.
#     get_forex_rates: Combines the previous logic to filter and format the dates based on the adjusted dates.

# This way, the script dynamically adjusts the required dates to the nearest available dates in the dataset.

# To achieve the desired behavior of specifying a date range (e.g., 2023-04-01 to 2024-03-31) and dynamically adjusting to the nearest available date, we can modify the script as follows:

#     Define the start and end dates.
#     Generate end-of-month dates within this range.
#     Adjust those dates to the nearest available dates in the dataset.
# # Explanation:

#     get_end_of_month_dates: Generates the end-of-month dates for each month within the specified date range.
#     adjust_dates_to_available: Adjusts the end-of-month dates to the nearest available date in the data.
#     get_forex_rates: Combines the previous logic to filter and format the dates based on the adjusted dates.
#     start_date and end_date: Specifies the date range for the query.

# This script will now correctly handle the date range and adjust to the nearest available dates as required.

# The SettingWithCopyWarning warning occurs when you try to modify a copy of a slice from a DataFrame. This can be avoided by using the .loc accessor to set values in the DataFrame.

# Earlier Error message

# data/docs/prabu/beancount/prabu/import_rates_c.py:41: SettingWithCopyWarning: 
# A value is trying to be set on a copy of a slice from a DataFrame.
# Try using .loc[row_indexer,col_indexer] = value instead

# See the caveats in the documentation: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
#   filtered_rates['DATE'] = filtered_rates['DATE'].dt.strftime('%Y-%m-%d')

# Here's the updated script that addresses the SettingWithCopyWarning:

# Explanation:

#     get_end_of_month_dates: Generates the end-of-month dates for each month within the specified date range.
#     adjust_dates_to_available: Adjusts the end-of-month dates to the nearest available date in the data.
#     get_forex_rates:
#         Combines the previous logic to filter and format the dates based on the adjusted dates.
#         Copies the filtered DataFrame (filtered_rates = rates[rates['DATE'].dt.normalize().isin(pd.to_datetime(required_dates))].copy()) to avoid modifying a view.
#         Uses .loc to update the DATE column (filtered_rates.loc[:, 'DATE'] = filtered_rates['DATE'].dt.strftime('%Y-%m-%d')), avoiding the SettingWithCopyWarning.

# This ensures that the SettingWithCopyWarning is avoided while achieving the desired functionality.
