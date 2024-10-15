import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import requests
from textblob import TextBlob
import numpy as np

def get_stock_data(ticker, start_date, end_date):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date)
        if df.empty:
            st.error(f"No data available for {ticker} in the selected date range.")
            return None
        return df
    except Exception as e:
        st.error(f"Error fetching data for {ticker}: {str(e)}")
        return None

def get_esg_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        esg_data = stock.sustainability
        if esg_data is None or esg_data.empty:
            st.warning(f"No ESG data found for {ticker}")
            return None
        return esg_data
    except Exception as e:
        st.error(f"Error fetching ESG data for {ticker}: {str(e)}")
        return None

def get_company_info(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = {
            'sector': stock.info.get('sector', 'N/A'),
            'industry': stock.info.get('industry', 'N/A'),
            'fullTimeEmployees': stock.info.get('fullTimeEmployees', 'N/A'),
            'country': stock.info.get('country', 'N/A'),
            'marketCap': stock.info.get('marketCap', 'N/A'),
            'forwardPE': stock.info.get('forwardPE', 'N/A'),
            'dividendYield': stock.info.get('dividendYield', 'N/A')
        }
        return info
    except Exception as e:
        st.error(f"Error fetching company info for {ticker}: {str(e)}")
        return None

def compute_returns(data):
    data['Daily Return'] = data['Close'].pct_change()
    data['Cumulative Return'] = (1 + data['Daily Return']).cumprod()
    return data

def compute_moving_averages(data, windows=[50, 200]):
    for window in windows:
        data[f'MA{window}'] = data['Close'].rolling(window=window).mean()
    return data

def display_stock_chart(data, ticker):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=(f'{ticker} Stock Price', 'Volume'),
                        row_heights=[0.7, 0.3])

    fig.add_trace(go.Candlestick(x=data.index,
                open=data['Open'], high=data['High'],
                low=data['Low'], close=data['Close'],
                name='Price'), row=1, col=1)

    fig.add_trace(go.Scatter(x=data.index, y=data['MA50'], name='50 Day MA', line=dict(color='orange', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['MA200'], name='200 Day MA', line=dict(color='red', width=1)), row=1, col=1)

    fig.add_trace(go.Bar(x=data.index, y=data['Volume'], name='Volume', marker_color='blue'), row=2, col=1)

    fig.update_layout(
        title=f'{ticker} Stock Analysis',
        yaxis_title='Stock Price',
        xaxis_rangeslider_visible=False,
        height=800,
        showlegend=True
    )

    fig.update_yaxes(title_text="Volume", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

def display_returns_chart(data, ticker):
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=data.index, y=data['Cumulative Return'], mode='lines', name='Cumulative Return'))

    fig.update_layout(
        title=f'{ticker} Cumulative Returns',
        yaxis_title='Cumulative Return',
        xaxis_title='Date',
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

def display_esg_data(esg_data):
    st.subheader("ESG Data")

    relevant_metrics = ['totalEsg', 'environmentScore', 'socialScore', 'governanceScore']
    numeric_data = esg_data[esg_data.index.isin(relevant_metrics)]

    fig = go.Figure()
    colors = {'totalEsg': 'purple', 'environmentScore': 'green', 'socialScore': 'blue', 'governanceScore': 'orange'}

    for metric in numeric_data.index:
        fig.add_trace(go.Bar(
            x=[metric],
            y=[numeric_data.loc[metric].values[0]],
            name=metric,
            marker_color=colors.get(metric, 'gray')
        ))

    fig.update_layout(
        title="ESG Scores",
        yaxis_title="Score",
        height=400,
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total ESG", f"{esg_data.loc['totalEsg'].values[0]:.2f}")
    col2.metric("Environment", f"{esg_data.loc['environmentScore'].values[0]:.2f}")
    col3.metric("Social", f"{esg_data.loc['socialScore'].values[0]:.2f}")
    col4.metric("Governance", f"{esg_data.loc['governanceScore'].values[0]:.2f}")

    st.subheader("Additional ESG Information")
    additional_info = {
        'ESG Performance': esg_data.loc['esgPerformance'].values[0],
        'Highest Controversy': esg_data.loc['highestControversy'].values[0],
        'Rating Year': esg_data.loc['ratingYear'].values[0],
        'Rating Month': esg_data.loc['ratingMonth'].values[0]
    }
    st.table(pd.DataFrame.from_dict(additional_info, orient='index', columns=['Value']))

def display_company_info(info):
    st.subheader("Company Information")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Sector", info.get('sector', 'N/A'))
        st.metric("Full Time Employees", f"{info.get('fullTimeEmployees', 'N/A'):,}")
    with col2:
        st.metric("Industry", info.get('industry', 'N/A'))
        st.metric("Country", info.get('country', 'N/A'))
    
    st.subheader("Financial Metrics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Market Cap", f"${info.get('marketCap', 'N/A'):,.0f}" if isinstance(info.get('marketCap'), (int, float)) else 'N/A')
    with col2:
        st.metric("Forward P/E", f"{info.get('forwardPE', 'N/A'):.2f}" if isinstance(info.get('forwardPE'), (int, float)) else 'N/A')
    with col3:
        st.metric("Dividend Yield", f"{info.get('dividendYield', 'N/A'):.2%}" if isinstance(info.get('dividendYield'), (int, float)) else 'N/A')

def get_news(ticker):
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        return news
    except Exception as e:
        st.error(f"Error fetching news for {ticker}: {str(e)}")
        return None

def display_news(news):
    st.subheader("Latest News")
    for article in news[:5]:  # Display top 5 news articles
        st.write(f"**{article['title']}**")
        st.write(f"*{datetime.fromtimestamp(article['providerPublishTime']).strftime('%Y-%m-%d %H:%M:%S')}*")
        st.write(article['link'])
        st.write("---")

def get_recommendations(ticker):
    try:
        stock = yf.Ticker(ticker)
        return stock.recommendations
    except Exception as e:
        st.error(f"Error fetching recommendations for {ticker}: {str(e)}")
        return None

def display_recommendations(recommendations):
    if recommendations is not None and not recommendations.empty:
        st.subheader("Analyst Recommendations")
        
        # Prepare data for the last 4 periods
        last_4_periods = recommendations.groupby('period').last().tail(4)
        
        # Create a stacked bar chart
        fig = go.Figure()
        categories = ['strongSell', 'sell', 'hold', 'buy', 'strongBuy']
        colors = ['red', 'lightcoral', 'gray', 'lightgreen', 'green']
        
        for category, color in zip(categories, colors):
            fig.add_trace(go.Bar(
                x=last_4_periods.index,
                y=last_4_periods[category],
                name=category.capitalize(),
                marker_color=color
            ))
        
        fig.update_layout(
            title="Analyst Recommendations (Last 4 Periods)",
            xaxis_title="Period",
            yaxis_title="Number of Analysts",
            barmode='stack',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display the raw data
        st.write("Raw Recommendation Data:")
        st.dataframe(recommendations.tail(10))  # Display last 10 recommendations
    else:
        st.warning("No analyst recommendations available.")

def get_sentiment_score(ticker):
    try:
        stock = yf.Ticker(ticker)
        news = stock.news[:10]  # Get latest 10 news items
        sentiment_scores = []
        for article in news:
            blob = TextBlob(article['title'])
            sentiment_scores.append(blob.sentiment.polarity)
        return np.mean(sentiment_scores)
    except Exception as e:
        st.error(f"Error calculating sentiment for {ticker}: {str(e)}")
        return None

def get_competitors(ticker):
    try:
        stock = yf.Ticker(ticker)
        sector = stock.info.get('sector')
        industry = stock.info.get('industry')
        if sector and industry:
            competitors = yf.Ticker(sector).info.get('componentsSymbols', [])
            return [comp for comp in competitors if comp != ticker][:5]  # Return top 5 competitors
        return []
    except Exception as e:
        st.error(f"Error fetching competitors for {ticker}: {str(e)}")
        return []

def compare_performance(ticker, competitors):
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        data = yf.download([ticker] + competitors, start=start_date, end=end_date)['Adj Close']
        returns = data.pct_change().cumsum()
        return returns
    except Exception as e:
        st.error(f"Error comparing performance: {str(e)}")
        return None

def create_comparison_chart(comparison_data):
    fig = go.Figure()
    for column in comparison_data.columns:
        fig.add_trace(go.Scatter(x=comparison_data.index, y=comparison_data[column], mode='lines', name=column))
    fig.update_layout(title="1 Year Cumulative Returns Comparison", xaxis_title="Date", yaxis_title="Cumulative Returns")
    return fig

def get_innovation_metrics(ticker):
    try:
        stock = yf.Ticker(ticker)
        r_and_d = stock.info.get('researchAndDevelopment', 0)
        revenue = stock.info.get('totalRevenue', 1)  # Avoid division by zero
        r_and_d_intensity = (r_and_d / revenue) * 100 if revenue else 0
        return {
            'R&D Spending': r_and_d,
            'R&D Intensity': r_and_d_intensity
        }
    except Exception as e:
        st.error(f"Error fetching innovation metrics for {ticker}: {str(e)}")
        return None

def create_innovation_chart(innovation_data):
    fig = go.Figure(data=[go.Bar(x=list(innovation_data.keys()), y=list(innovation_data.values()))])
    fig.update_layout(title="Innovation Metrics", xaxis_title="Metric", yaxis_title="Value")
    return fig

def main():
    st.set_page_config(layout="wide", page_title="Enhanced Stock Analysis Dashboard")
    
    # Sidebar
    st.sidebar.title("Stock Analysis Dashboard")
    ticker = st.sidebar.text_input("Enter Stock Ticker", value="NVDA").upper()
    period = st.sidebar.selectbox("Select Time Period", 
                                  options=["1M", "3M", "6M", "1Y", "2Y", "5Y"],
                                  format_func=lambda x: f"{x[:-1]} {'Month' if x[-1]=='M' else 'Year'}{'s' if x[:-1]!='1' else ''}",
                                  index=3)

    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=int(period[:-1]) * (30 if period[-1] == 'M' else 365))).strftime('%Y-%m-%d')

    # Main content
    st.title(f"{ticker} Enhanced Stock Analysis Dashboard")
    st.write(f"Analyzing data from {start_date} to {end_date}")

    # Fetch all data
    with st.spinner('Fetching data...'):
        stock_data = get_stock_data(ticker, start_date, end_date)
        esg_data = get_esg_data(ticker)
        company_info = get_company_info(ticker)
        news = get_news(ticker)
        recommendations = get_recommendations(ticker)
        sentiment_score = get_sentiment_score(ticker)
        competitors = get_competitors(ticker)
        comparison_data = compare_performance(ticker, competitors)
        innovation_data = get_innovation_metrics(ticker)

    if stock_data is not None and not stock_data.empty:
        stock_data = compute_returns(stock_data)
        stock_data = compute_moving_averages(stock_data)

        # Key Metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Current Price", f"${stock_data['Close'].iloc[-1]:.2f}", 
                    f"{stock_data['Daily Return'].iloc[-1]:.2%}")
        col2.metric("50-Day MA", f"${stock_data['MA50'].iloc[-1]:.2f}")
        col3.metric("200-Day MA", f"${stock_data['MA200'].iloc[-1]:.2f}")
