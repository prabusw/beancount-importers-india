import pandas as pd
import calendar

def get_end_of_month_dates(year, months):
    end_of_month_dates = []
    for month in months:
        last_day = calendar.monthrange(year, month)[1]
        end_of_month_dates.append(f"{year}-{month:02d}-{last_day:02d}")
    return end_of_month_dates

def adjust_dates_to_available(rates, dates):
    adjusted_dates = []
    for date in dates:
        current_date = pd.to_datetime(date)
        while current_date not in rates['DATE'].dt.normalize().values:
            current_date -= pd.Timedelta(days=1)
        adjusted_dates.append(current_date.strftime('%Y-%m-%d'))
    return adjusted_dates

def get_forex_rates(currency, year, months):
    # Define the URL based on the currency
    url = f"https://raw.githubusercontent.com/sahilgupta/sbi-fx-ratekeeper/main/csv_files/SBI_REFERENCE_RATES_{currency}.csv"
    
    try:
        # Read the CSV file from the GitHub repository for the specified currency rates
        rates = pd.read_csv(url)
        
        # Convert the date column to datetime for easier filtering
        rates['DATE'] = pd.to_datetime(rates.iloc[:, 0], errors='coerce')

        # Get end-of-month dates
        end_of_month_dates = get_end_of_month_dates(year, months)

        # Adjust dates to available dates
        required_dates = adjust_dates_to_available(rates, end_of_month_dates)

        # Filter the data for the required dates
        filtered_rates = rates[rates['DATE'].dt.normalize().isin(pd.to_datetime(required_dates))]

        # Format the DATE column to YYYY-MM-DD
        filtered_rates['DATE'] = filtered_rates['DATE'].dt.strftime('%Y-%m-%d')

        # Return the filtered data with DATE and the third column (TT buying rate)
        return filtered_rates.iloc[:, [0, 2]]
    except Exception as e:
        print(f"An error occurred: {e}")
        return pd.DataFrame(columns=['DATE', 'TT BUY'])

# Define the year and months for which you want the rates
year = 2023
months = [8, 9, 10, 11, 12, 1, 2, 3]

# Call the function for SGD
sgd_rates = get_forex_rates("SGD", year, months)
print("Filtered rates:")
print(sgd_rates)
