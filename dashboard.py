import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe

# Authenticate with Google Sheets using your credentials JSON file
from oauth2client.service_account import ServiceAccountCredentials
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('your-credentials.json', scope)
gc = gspread.authorize(credentials)

# Load the Google Sheet by its URL or title
sheet_url = private_gsheets_url 
worksheet = gc.open_by_url(sheet_url).sheet1

# Read the data from the Google Sheet into a Pandas DataFrame
data = get_as_dataframe(worksheet)

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
        popup=filtered_data[['Price ()', 'Date of Sale (dd/mm/yyyy)']].agg(
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
