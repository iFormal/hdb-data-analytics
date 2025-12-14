import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
API_URL = "https://data.gov.sg/api/action/datastore_search"
RESOURCE_ID = "d_8b84c4ee58e3cfc0ece0d773c8ca6abc"
MAX_RECORDS_TO_LOAD = 10000 

# --- CORE ENGINE FUNCTIONS ---

# Caching the data load to avoid repeated API calls
@st.cache_data
def load_all_data():
    params = {
        "resource_id": RESOURCE_ID, 
        "limit": MAX_RECORDS_TO_LOAD,
        "sort": "month desc"
    }
    
    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        data_packet = response.json()
        return pd.DataFrame(data_packet['result']['records'])
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")
        return None

def clean_data(df):
    if df is None:
        return None
        
    df_clean = df.copy()
    
    # Type Casting
    cols_to_numeric = ['resale_price', 'floor_area_sqm']
    for col in cols_to_numeric:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

    # Year Extraction
    if 'month' in df_clean.columns:
        df_clean['month'] = pd.to_datetime(df_clean['month'])
        df_clean['year'] = df_clean['month'].dt.year 

    # Drop invalid rows
    df_clean = df_clean.dropna(subset=['resale_price'])
    
    return df_clean

# --- FRONT END ---

def run_dashboard():
    st.set_page_config(
        page_title="HDB Insights | James Ang",
        page_icon="🏠",
        layout="wide"
    )

    st.title("🇸🇬 Singapore Housing Insights")
    with st.expander("ℹ️ About this Project"):
        st.markdown("""
        **Built by James Ang.**
        This dashboard retrieves real-time resale flat prices from the [Data.gov.sg API](https://data.gov.sg/).
        
        **Tech Stack:** Python, Streamlit, Pandas, Matplotlib.
        """)
    st.markdown("---")

    # --- LOADING DATA ---
    with st.spinner(f"Fetching {MAX_RECORDS_TO_LOAD} records from government database..."):
        full_df = load_all_data()

    if full_df is None or full_df.empty:
        st.stop()
        
    clean_df = clean_data(full_df)

    # --- SIDEBAR FILTERS ---
    st.sidebar.header("🔍 Filter Options")

    # Limit Slider
    max_slider_val = min(clean_df.shape[0], MAX_RECORDS_TO_LOAD)
    records_to_analyze = st.sidebar.slider(
        "Sample Size (Most Recent)", 
        100, max_slider_val, min(2000, max_slider_val), 100
    )
    current_df = clean_df.head(records_to_analyze)

    # Town Selection
    all_towns = sorted(current_df['town'].unique())
    selected_towns = st.sidebar.multiselect("Select Towns", all_towns, default=all_towns[:5])
    
    if selected_towns:
        filtered_df = current_df[current_df['town'].isin(selected_towns)]
    else:
        filtered_df = current_df 

    # Year Slider
    if 'year' in clean_df.columns:
        min_year = int(filtered_df['year'].min())
        max_year = int(filtered_df['year'].max())
        
        if min_year < max_year:
            year_range = st.sidebar.slider("Filter by Year", min_year, max_year, (min_year, max_year))
            filtered_df = filtered_df[
                (filtered_df['year'] >= year_range[0]) & (filtered_df['year'] <= year_range[1])
            ]
        else:
            st.sidebar.info(f"📅 Data limited to {min_year}")

    if filtered_df.empty:
        st.warning("No data found for these filters.")
        st.stop()

    # --- MAIN DASHBOARD LAYOUT ---
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Avg Price", f"S${filtered_df['resale_price'].mean():,.0f}")
    col2.metric("Avg Size", f"{filtered_df['floor_area_sqm'].mean():,.0f} sqm")
    col3.metric("Transactions", f"{filtered_df.shape[0]:,}")

    st.markdown("---")

    tab1, tab2 = st.tabs(["📊 Price Analysis", "📄 Raw Data"])
    
    with tab1:
        st.subheader("Price Comparison by Flat Type")
        
        try:
            pivot_data = filtered_df.groupby(['town', 'flat_type'])['resale_price'].mean().unstack()
            
            # Matplotlib Figure
            fig, ax = plt.subplots(figsize=(10, 6))
            pivot_data.plot(kind='bar', ax=ax, width=0.8, colormap='viridis')
            
            ax.set_ylabel("Price (SGD)")
            ax.set_xlabel("Town")
            ax.grid(axis='y', linestyle='--', alpha=0.3)
            
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1000:.0f}K'))
            plt.xticks(rotation=45, ha='right')
            
            st.pyplot(fig)
            
        except Exception as e:
            st.info("Not enough data to generate the chart. Try selecting more records.")

    with tab2:
        st.dataframe(filtered_df.sort_values(by='resale_price', ascending=False))

if __name__ == "__main__":
    run_dashboard()