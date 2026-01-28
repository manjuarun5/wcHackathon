#!/usr/bin/env python3
"""
WCO 2026 Hackathon - Customs E-Commerce Dashboard
Simple UI for exploring processing results
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime
import os

# Page configuration
st.set_page_config(
    page_title="Customs E-Commerce Dashboard",
    page_icon="🌐",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .risk-high {
        color: #ff4b4b;
        font-weight: bold;
    }
    .risk-medium {
        color: #ffa500;
        font-weight: bold;
    }
    .risk-low {
        color: #00cc00;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Load processed customs data"""
    try:
        # Load main results
        df = pd.read_csv('../output-data/customs_processing_results.csv')
        
        # Load summary
        with open('../output-data/processing_summary.json', 'r') as f:
            summary = json.load(f)
        
        # Load alerts if available
        alerts_df = None
        if os.path.exists('../output-data/high_priority_alerts.csv'):
            alerts_df = pd.read_csv('../output-data/high_priority_alerts.csv')
        
        return df, summary, alerts_df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.info("Please run main-new.py first to generate the output files.")
        return None, None, None

def main():
    """Main dashboard function"""
    
    # Header
    st.title("🌐 WCO 2026 Hackathon - Customs E-Commerce Dashboard")
    st.markdown("**Mission:** Operationalizing the WCO Framework of Standards")
    st.markdown("**Location:** Abu Dhabi Customs Entry Point")
    st.divider()
    
    # Load data
    df, summary, alerts_df = load_data()
    
    if df is None:
        return
    
    # Sidebar filters
    st.sidebar.header("📊 Filters")
    
    # Date range filter
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        date_range = st.sidebar.date_input(
            "Date Range",
            value=(df['date'].min(), df['date'].max()),
            min_value=df['date'].min(),
            max_value=df['date'].max()
        )
        
        if len(date_range) == 2:
            df = df[(df['date'] >= pd.to_datetime(date_range[0])) & 
                   (df['date'] <= pd.to_datetime(date_range[1]))]
    
    # Risk filter
    risk_filter = st.sidebar.multiselect(
        "Risk Category",
        options=['All', 'No Risk', 'Category A (Dangerous)', 'Category B (Restricted)'],
        default=['All']
    )
    
    if 'All' not in risk_filter and 'No Risk' not in risk_filter:
        if 'Category A (Dangerous)' in risk_filter:
            df = df[df['risk_flag_code'].str.contains('A', na=False)]
        if 'Category B (Restricted)' in risk_filter:
            df = df[df['risk_flag_code'].str.contains('B', na=False)]
    elif 'No Risk' in risk_filter and 'All' not in risk_filter:
        df = df[df['risk_flag_code'] == 'NONE']
    
    # Split shipment filter
    split_filter = st.sidebar.radio(
        "Split Shipments",
        options=['All', 'Yes', 'No']
    )
    
    if split_filter == 'Yes':
        df = df[df['split_shipment_detected'] == 'Y']
    elif split_filter == 'No':
        df = df[df['split_shipment_detected'] == 'N']
    
    # Summary metrics
    st.header("📈 Key Performance Indicators")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Total Items",
            f"{len(df):,}",
            delta=None
        )
    
    with col2:
        st.metric(
            "Total Orders",
            f"{df['order_id'].nunique():,}",
            delta=None
        )
    
    with col3:
        total_duty = df['duty'].sum() if 'duty' in df.columns else 0
        st.metric(
            "Revenue Collected",
            f"{total_duty:,.2f} AED",
            delta=None
        )
    
    with col4:
        split_count = (df['split_shipment_detected'] == 'Y').sum()
        st.metric(
            "Split Shipments",
            f"{split_count:,}",
            delta=f"{split_count/len(df)*100:.1f}%" if len(df) > 0 else "0%"
        )
    
    with col5:
        risk_count = (df['risk_flag_code'] != 'NONE').sum()
        st.metric(
            "Items Flagged",
            f"{risk_count:,}",
            delta=f"{risk_count/len(df)*100:.1f}%" if len(df) > 0 else "0%"
        )
    
    st.divider()
    
    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔍 Split Shipment Detections",
        "💰 Duty Calculations",
        "🛡️ Risk Flags",
        "📊 Analytics",
        "⚠️ High Priority Alerts"
    ])
    
    with tab1:
        st.header("Split Shipment Detections (Breaches)")
        
        # Filter for split shipments
        split_df = df[df['split_shipment_detected'] == 'Y'].copy()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Total Split Shipment Cases",
                f"{len(split_df):,}",
                delta=f"{len(split_df)/len(df)*100:.1f}% of total" if len(df) > 0 else "0%"
            )
        
        with col2:
            if 'daily_total_value_aed' in split_df.columns:
                revenue_at_risk = split_df['daily_total_value_aed'].sum()
                st.metric(
                    "Revenue at Risk",
                    f"{revenue_at_risk:,.2f} AED"
                )
        
        # Display split shipments
        if len(split_df) > 0:
            st.subheader("Split Shipment Details")
            
            display_cols = ['order_id', 'importer_name', 'date', 'order_count', 
                          'daily_total_value_aed', 'duty', 'product_title']
            display_cols = [col for col in display_cols if col in split_df.columns]
            
            st.dataframe(
                split_df[display_cols].sort_values('daily_total_value_aed', ascending=False),
                use_container_width=True,
                height=400
            )
            
            # Chart: Split shipments by importer
            if 'importer_name' in split_df.columns:
                top_split_importers = split_df.groupby('importer_name').size().sort_values(ascending=False).head(10)
                
                fig = px.bar(
                    x=top_split_importers.values,
                    y=top_split_importers.index,
                    orientation='h',
                    title="Top 10 Importers with Split Shipments",
                    labels={'x': 'Number of Split Shipment Items', 'y': 'Importer'}
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No split shipments detected in the filtered data.")
    
    with tab2:
        st.header("Duty Calculations")
        
        if 'duty' in df.columns:
            dutiable_df = df[df['duty'] > 0].copy()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Total Duty",
                    f"{df['duty'].sum():,.2f} AED"
                )
            
            with col2:
                st.metric(
                    "Dutiable Items",
                    f"{len(dutiable_df):,}",
                    delta=f"{len(dutiable_df)/len(df)*100:.1f}%" if len(df) > 0 else "0%"
                )
            
            with col3:
                avg_duty = df['duty'].sum() / len(dutiable_df) if len(dutiable_df) > 0 else 0
                st.metric(
                    "Avg Duty/Item",
                    f"{avg_duty:.2f} AED"
                )
            
            # Display dutiable items
            if len(dutiable_df) > 0:
                st.subheader("Dutiable Items")
                
                display_cols = ['order_id', 'product_title', 'item_price_aed', 
                              'hs_code', 'tariff_rate', 'duty']
                display_cols = [col for col in display_cols if col in dutiable_df.columns]
                
                st.dataframe(
                    dutiable_df[display_cols].sort_values('duty', ascending=False),
                    use_container_width=True,
                    height=400
                )
                
                # Chart: Duty distribution
                if 'hs_code' in dutiable_df.columns:
                    duty_by_hs = dutiable_df.groupby('hs_code')['duty'].sum().sort_values(ascending=False).head(10)
                    
                    fig = px.bar(
                        x=duty_by_hs.index,
                        y=duty_by_hs.values,
                        title="Top 10 HS Codes by Duty Collected",
                        labels={'x': 'HS Code', 'y': 'Total Duty (AED)'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Duty information not available in the data.")
    
    with tab3:
        st.header("Risk Flags & Security Alerts")
        
        risk_df = df[df['risk_flag_code'] != 'NONE'].copy()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Items Flagged",
                f"{len(risk_df):,}",
                delta=f"{len(risk_df)/len(df)*100:.1f}%" if len(df) > 0 else "0%"
            )
        
        with col2:
            category_a = (df['risk_flag_code'].str.contains('A', na=False)).sum()
            st.metric(
                "Dangerous Goods (A)",
                f"{category_a:,}",
                delta="High Risk",
                delta_color="inverse"
            )
        
        with col3:
            category_b = (df['risk_flag_code'].str.contains('B', na=False)).sum()
            st.metric(
                "Restricted Items (B)",
                f"{category_b:,}",
                delta="Medium Risk",
                delta_color="off"
            )
        
        # Display risk items
        if len(risk_df) > 0:
            st.subheader("Flagged Items with Rationale")
            
            display_cols = ['order_id', 'product_title', 'risk_flag_code', 'risk_reason', 
                          'item_price_aed', 'duty']
            display_cols = [col for col in display_cols if col in risk_df.columns]
            
            st.dataframe(
                risk_df[display_cols],
                use_container_width=True,
                height=400
            )
            
            # Chart: Risk distribution
            risk_counts = risk_df['risk_flag_code'].value_counts()
            
            fig = px.pie(
                values=risk_counts.values,
                names=risk_counts.index,
                title="Risk Flag Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No risk flags in the filtered data.")
    
    with tab4:
        st.header("Analytics & Insights")
        
        # Daily trends
        if 'date' in df.columns:
            daily_stats = df.groupby('date').agg({
                'order_id': 'nunique',
                'duty': 'sum',
                'split_shipment_detected': lambda x: (x == 'Y').sum(),
                'risk_flag_code': lambda x: (x != 'NONE').sum()
            }).reset_index()
            
            daily_stats.columns = ['Date', 'Orders', 'Duty (AED)', 'Split Shipments', 'Risk Flags']
            
            # Line chart for trends
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=daily_stats['Date'],
                y=daily_stats['Orders'],
                name='Orders',
                mode='lines+markers'
            ))
            
            fig.add_trace(go.Scatter(
                x=daily_stats['Date'],
                y=daily_stats['Split Shipments'],
                name='Split Shipments',
                mode='lines+markers'
            ))
            
            fig.add_trace(go.Scatter(
                x=daily_stats['Date'],
                y=daily_stats['Risk Flags'],
                name='Risk Flags',
                mode='lines+markers'
            ))
            
            fig.update_layout(
                title='Daily Trends',
                xaxis_title='Date',
                yaxis_title='Count',
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Duty trend
            fig2 = px.area(
                daily_stats,
                x='Date',
                y='Duty (AED)',
                title='Daily Duty Collection'
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # Top importers
        if 'importer_name' in df.columns:
            st.subheader("Top Importers")
            
            top_importers = df.groupby('importer_name').agg({
                'order_id': 'nunique',
                'item_price_aed': 'sum',
                'duty': 'sum',
                'split_shipment_detected': lambda x: (x == 'Y').sum(),
                'risk_flag_code': lambda x: (x != 'NONE').sum()
            }).reset_index()
            
            top_importers.columns = ['Importer', 'Orders', 'Total Value (AED)', 
                                    'Duty (AED)', 'Split Shipments', 'Risk Flags']
            top_importers = top_importers.sort_values('Total Value (AED)', ascending=False).head(20)
            
            st.dataframe(
                top_importers,
                use_container_width=True,
                height=400
            )
    
    with tab5:
        st.header("⚠️ High Priority Alerts")
        
        if alerts_df is not None and len(alerts_df) > 0:
            st.warning(f"**{len(alerts_df):,} items require immediate attention**")
            
            # Filter options
            alert_type = st.selectbox(
                "Filter by Alert Type",
                options=['All', 'Revenue Risk', 'Security Risk', 'Classification Review']
            )
            
            filtered_alerts = alerts_df.copy()
            
            if alert_type == 'Revenue Risk':
                filtered_alerts = filtered_alerts[filtered_alerts['revenue_risk'] == True]
            elif alert_type == 'Security Risk':
                filtered_alerts = filtered_alerts[filtered_alerts['risk_flag_code'] != 'NONE']
            elif alert_type == 'Classification Review':
                filtered_alerts = filtered_alerts[filtered_alerts['classification_status'] == 'NO_MATCH']
            
            st.dataframe(
                filtered_alerts,
                use_container_width=True,
                height=500
            )
            
            # Download button
            csv = filtered_alerts.to_csv(index=False)
            st.download_button(
                label="📥 Download Alerts CSV",
                data=csv,
                file_name=f"high_priority_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.success("No high-priority alerts in the current dataset!")
    
    # Footer
    st.divider()
    st.markdown("""
        <div style='text-align: center; color: #666;'>
            <p>WCO 2026 Hackathon | Abu Dhabi Customs Entry Point</p>
            <p>Powered by the WCO Framework of Standards</p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
