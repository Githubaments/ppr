import streamlit as st
import pandas as pd
import plotly.express as px

@st.cache
def load_data(file_path):
    return pd.read_csv(file_path)

def main():
    st.title("Personal Health Dashboard")

    file_path = st.file_uploader("Upload your personal data CSV file", type=["csv"])
    if file_path is not None:
        df = load_data(file_path)
        st.dataframe(df)

        # Choose the header to plot
        selected_header = st.selectbox("Select a header to plot over time", df.columns)

        # Plotting the selected header over time using Plotly
        fig = px.line(df, x='Time of Measurement', y=selected_header)
        st.plotly_chart(fig)

        # Showing some statistics
        st.write("### Personal Data Statistics")
        st.write("Mean value: ", df[selected_header].mean())
        st.write("Minimum value: ", df[selected_header].min())
        st.write("Maximum value: ", df[selected_header].max())

    google_fit_path = st.file_uploader("Upload your Google Fit data CSV file", type=["csv"])
    if google_fit_path is not None:
        df_google_fit = load_data(google_fit_path)
        st.dataframe(df_google_fit)

        # Choose the header to plot
        selected_header_google_fit = st.selectbox("Select a header to plot over time", df_google_fit.columns)

        # Plotting the selected header over time using Plotly
        fig_google_fit = px.line(df_google_fit, x='Time of Measurement', y=selected_header_google_fit)
        st.plotly_chart(fig_google_fit)

        # Showing some statistics
        st.write("### Google Fit Data Statistics")
        st.write("Mean value: ", df_google_fit[selected_header_google_fit].mean())
        st.write("Minimum value: ", df_google_fit[selected_header_google_fit].min())
        st.write("Maximum value: ", df_google_fit[selected_header_google_fit].max())

        # 7-day moving average of heart points
        df_google_fit['7-day avg heart points'] = df_google_fit['Heart Points'].rolling(window=7).mean()
        fig_7day_avg = px.line(df_google_fit, x='Time of Measurement', y='7-day avg heart points')
        st.plotly_chart(fig_7day_avg)

        # Count of days with more than 10,000 steps
        df_google_fit['over_10000'] = df_google_fit['Steps'] >= 10000
        fig_steps = px.bar(df_google_fit, x='Time of Measurement', y='over_10000', color='over_10000')
       
