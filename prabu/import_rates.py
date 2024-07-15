import pandas as pd

def get_forex_rates(currency, required_dates):
    # Define the URL based on the currency
    url = f"https://raw.githubusercontent.com/sahilgupta/sbi-fx-ratekeeper/main/csv_files/SBI_REFERENCE_RATES_{currency}.csv"
    
    try:
        # Read the CSV file from the GitHub repository for the specified currency rates
        rates = pd.read_csv(url)

        # Debug: print the first few rows to understand the structure
        print("First few rows of the dataframe:")
        print(rates.head())

        # Convert the date column to datetime for easier filtering
        rates['DATE'] = pd.to_datetime(rates.iloc[:, 0], errors='coerce')

        # Debug: print the dataframe after date conversion
        print("Dataframe after date conversion:")
        print(rates.head())

        # Filter the data for the required dates
        filtered_rates = rates[rates['DATE'].dt.normalize().isin(pd.to_datetime(required_dates))]

        # Return the filtered data with DATE and the third column (TT buying rate)
        return filtered_rates.iloc[:, [0, 2]]
    except Exception as e:
        print(f"An error occurred: {e}")
        return pd.DataFrame(columns=['DATE', 'TT BUY'])

# Define the required dates
required_dates = [
    "2023-08-31", "2023-09-30", "2023-10-31", 
    "2023-11-30", "2023-12-30", "2024-01-31", 
    "2024-02-29", "2024-03-30"
]

# Call the function for SGD
sgd_rates = get_forex_rates("SGD", required_dates)
print("Filtered rates:")
print(sgd_rates)
