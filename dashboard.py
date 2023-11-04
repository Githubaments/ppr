import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2 import service_account


# Authenticate with Google Sheets using your credentials JSON file
from oauth2client.service_account import ServiceAccountCredentials

# Create a function to load the data and cache it
@st.cache_data
def load_data():
    # Create a connection object.
    credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive", ],
        )
        
    gc = gspread.authorize(credentials)

    sheet = gc.open('PPR').sheet1


    # Load the Google Sheet by its URL or title
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    return df

# Load the data using the cache
data = load_data()

# Create user inputs for filtering by Eircode and Address
eircode_input = st.text_input("Enter Eircode:")
address_input = st.text_input("Enter Address:")

# Extract the first three characters from the full Eircode input
eircode_prefix = eircode_input[:3].upper() if eircode_input else ""

# Filter the data based on user inputs
filtered_data = data.copy()

exact_match = None  # Initialize a flag for exact Eircode match

if eircode_prefix:
    filtered_data = filtered_data[filtered_data['Eircode'].str.startswith(eircode_prefix)]
    exact_match = data[data['Eircode'] == eircode_input]  # Check for an exact match

if address_input:
    filtered_data = filtered_data[filtered_data['Address'].str.contains(address_input, case=False, na=False)]

# Remove duplicate rows based on the whole row
filtered_data = filtered_data.drop_duplicates()

# Create a Streamlit map to display data points using Latitude and Longitude columns
st.title('Google Sheet Data on Map')

# Check if Latitude and Longitude columns exist in the data
if 'Latitude' in filtered_data.columns and 'Longitude' in filtered_data.columns:
    st.map(filtered_data[['Latitude', 'Longitude']].assign(
        popup=filtered_data[['Price', 'Date of Sale (dd/mm/yyyy)']].agg(
            lambda x: f"Price: {x['Price']}, Date: {x['Date of Sale (dd/mm/yyyy)']}",
            axis=1
        )
    ))
else:
    st.error("Latitude and/or Longitude columns not found in the Google Sheet.")

# Display a special message and exact match data if an exact match is found
if exact_match is not None and not exact_match.empty:
    st.subheader("Exact Eircode Match Found:")
    st.write(exact_match)

# Display the filtered data
st.subheader("Filtered Data:")
st.write(filtered_data)
