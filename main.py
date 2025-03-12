import streamlit as st
import requests
import time
from datetime import datetime, timedelta
import mysql.connector
import pandas as pd

# Set page configuration for better layout
st.set_page_config(
    page_title="Crypto Market Data",
    page_icon="📈",
    layout="wide"
)

# Apply custom CSS for dark mode compatibility
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        margin-top: 1rem;
    }
    .price-data {
        font-size: 1.2rem;
        background-color: rgba(61, 65, 75, 0.5);
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        color: white;
    }
    .timer {
        font-size: 1rem;
        color: #e0e0e0;
        background-color: rgba(61, 65, 75, 0.5);
        padding: 0.5rem;
        border-radius: 0.3rem;
    }
    .dataframe {
        font-size: 0.9rem;
    }
    .price-data table {
        color: white;
    }
    .price-data td {
        padding: 5px 10px;
    }
</style>
""", unsafe_allow_html=True)

# Set your Alpaca API credentials
API_KEY = 'PK5K5WNB8QPSATC3GVLB'
SECRET_KEY = 'GCeYxJenpWlwSZwzBm2Cj7uBYOYYSt04vm1QHdo1'

HEADERS = {
    "Apca-Api-Key-Id": API_KEY,
    "Apca-Api-Secret-Key": SECRET_KEY
}

# Database configuration
DB_CONFIG = {
    'host': 'sql5.freesqldatabase.com',
    'database': 'sql5767357',
    'user': 'sql5767357',
    'password': 'tVwMEmS9Lm',
    'port': 3306
}

# Function to initialize database (create table if not exists)
def initialize_database():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Create crypto_prices table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS crypto_prices (
            id INT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            bid_price DECIMAL(20, 8) NOT NULL,
            ask_price DECIMAL(20, 8) NOT NULL,
            last_trade_price DECIMAL(20, 8) NOT NULL,
            timestamp DATETIME NOT NULL
        )
        ''')
        
        # Create sync_control table for coordinating updates
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_control (
            id INT PRIMARY KEY DEFAULT 1,
            last_update DATETIME NOT NULL,
            next_update DATETIME NOT NULL
        )
        ''')
        
        # Initialize sync_control if it doesn't have data
        cursor.execute('SELECT COUNT(*) FROM sync_control')
        if cursor.fetchone()[0] == 0:
            next_update = datetime.now() + timedelta(seconds=30)
            cursor.execute('''
            INSERT INTO sync_control (last_update, next_update)
            VALUES (%s, %s)
            ''', (datetime.now(), next_update))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Database initialization error: {e}")
        return False

# Function to get sync timing information
def get_sync_timing():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT last_update, next_update FROM sync_control WHERE id = 1')
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return result['last_update'], result['next_update']
    except Exception as e:
        st.error(f"Sync timing error: {e}")
        return datetime.now(), datetime.now() + timedelta(seconds=30)

# Function to update sync timing
def update_sync_timing(price_refresh_interval):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        now = datetime.now()
        next_update = now + timedelta(seconds=price_refresh_interval)
        
        cursor.execute('''
        UPDATE sync_control
        SET last_update = %s, next_update = %s
        WHERE id = 1
        ''', (now, next_update))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Update sync timing error: {e}")
        return False

# Function to add data to database
def add_to_database(symbol, bid, ask, last_trade):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check current row count
        cursor.execute("SELECT COUNT(*) FROM crypto_prices")
        count = cursor.fetchone()[0]
        
        # If we have 100 or more rows, delete the oldest 10
        if count >= 100:
            cursor.execute("DELETE FROM crypto_prices ORDER BY timestamp ASC LIMIT 10")
        
        # Insert new data
        cursor.execute('''
        INSERT INTO crypto_prices (symbol, bid_price, ask_price, last_trade_price, timestamp)
        VALUES (%s, %s, %s, %s, %s)
        ''', (symbol, bid, ask, last_trade, datetime.now()))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Database insertion error: {e}")
        return False

# Function to get data from database
def get_database_data(limit=100):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
        SELECT * FROM crypto_prices 
        ORDER BY timestamp DESC 
        LIMIT %s
        ''', (limit,))
        
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return result
    except Exception as e:
        st.error(f"Database retrieval error: {e}")
        return []

# Function to fetch crypto market data from Alpaca
def get_crypto_data(symbol="BTC/USD"):
    try:
        # Fetch order book (bid/ask prices)
        orderbook_url = f"https://data.alpaca.markets/v1beta3/crypto/us/latest/orderbooks?symbols={symbol}"
        orderbook_response = requests.get(orderbook_url, headers=HEADERS).json()
        bid_price = orderbook_response['orderbooks'][symbol]['b'][0]['p']
        ask_price = orderbook_response['orderbooks'][symbol]['a'][0]['p']
        
        # Fetch last trade price
        trade_url = f"https://data.alpaca.markets/v1beta3/crypto/us/latest/trades?symbols={symbol}"
        trade_response = requests.get(trade_url, headers=HEADERS).json()
        last_trade_price = trade_response['trades'][symbol]['p']
        
        return float(bid_price), float(ask_price), float(last_trade_price)
    except Exception as e:
        st.error(f"API error: {e}")
        return None, None, None

# Initialize the database
if not initialize_database():
    st.error("Failed to initialize database. Please check your database configuration.")
    st.stop()

# Streamlit UI
st.markdown('<div class="main-header">Live Crypto Market Data (Alpaca API)</div>', unsafe_allow_html=True)

# Create layout columns for the entire app
col1, col2 = st.columns([1, 2])

with col1:
    symbol = st.selectbox("Select Cryptocurrency Pair", ["BTC/USD", "ETH/USD", "SOL/USD"])
    data_placeholder = st.empty()
    timer_placeholder = st.empty()

with col2:
    st.markdown('<div class="sub-header">Historical Price Data</div>', unsafe_allow_html=True)
    db_data_placeholder = st.empty()

# Refresh intervals
price_refresh_interval = 30  # seconds
db_refresh_interval = 60     # seconds (1 minute)
db_update_counter = 0

# Get initial sync timing
last_update, next_update = get_sync_timing()

# Main loop
while True:
    # Get current time
    now = datetime.now()
    
    # Check if it's time to update based on the sync_control table
    current_time = datetime.now()
    last_update, next_update = get_sync_timing()
    
    # Calculate seconds until next update
    seconds_until_update = max(0, int((next_update - current_time).total_seconds()))
    
    # If it's time to update (within 1 second margin)
    if seconds_until_update <= 1:
        # Fetch crypto data
        bid, ask, last_trade = get_crypto_data(symbol)
        
        if bid is not None and ask is not None and last_trade is not None:
            # Format prices to 2 decimal places for display
            bid_formatted = f"${bid:,.2f}"
            ask_formatted = f"${ask:,.2f}"
            last_trade_formatted = f"${last_trade:,.2f}"
            
            # Update display with better formatting for dark mode
            data_placeholder.markdown(f"""
            <div class="price-data">
                <h3>{symbol} Current Prices</h3>
                <table>
                    <tr><td><b>Bid Price:</b></td><td>{bid_formatted}</td></tr>
                    <tr><td><b>Ask Price:</b></td><td>{ask_formatted}</td></tr>
                    <tr><td><b>Last Trade:</b></td><td>{last_trade_formatted}</td></tr>
                    <tr><td><b>Updated:</b></td><td>{current_time.strftime('%H:%M:%S')}</td></tr>
                </table>
            </div>
            """, unsafe_allow_html=True)
            
            # Add to database every minute (based on db_update_counter)
            db_update_counter += 1
            if db_update_counter >= (db_refresh_interval // price_refresh_interval):
                add_to_database(symbol, bid, ask, last_trade)
                db_update_counter = 0
                
                # Refresh database display
                db_data = get_database_data()
                if db_data:
                    df = pd.DataFrame(db_data)
                    # Format timestamp for better display
                    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
                    # Format price columns
                    for col in ['bid_price', 'ask_price', 'last_trade_price']:
                        df[col] = df[col].apply(lambda x: f"${float(x):,.2f}")
                    
                    # Rename columns for better display
                    df.columns = ['ID', 'Symbol', 'Bid Price', 'Ask Price', 'Last Trade', 'Timestamp']
                    db_data_placeholder.dataframe(df, use_container_width=True)
                else:
                    db_data_placeholder.info("No data in database yet")
        else:
            data_placeholder.error("Failed to retrieve data. Check API keys or network.")
        
        # Update the sync timing for all instances
        update_sync_timing(price_refresh_interval)
        
        # Refresh sync timing after update
        last_update, next_update = get_sync_timing()
    
    # Display countdown timer with synchronized timing
    current_time = datetime.now()
    seconds_until_update = max(0, int((next_update - current_time).total_seconds()))
    
    # For database update countdown
    db_seconds_remaining = db_refresh_interval - ((db_update_counter * price_refresh_interval) + (price_refresh_interval - seconds_until_update))
    if db_seconds_remaining <= 0:
        db_update_text = "less than a second"
    else:
        db_update_text = f"{db_seconds_remaining} seconds"
    
    # Update the timer display
    timer_placeholder.markdown(f"""
    <div class="timer">
        <p>⏱️ <b>Next price update in:</b> {seconds_until_update} seconds</p>
        <p>💾 <b>Next database update in:</b> {db_update_text}</p>
        <p>🔄 <b>Sync status:</b> Active</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sleep for 1 second before checking again
    time.sleep(1)
