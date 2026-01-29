#!/usr/bin/env python3
"""
WCO 2026 Hackathon - Customs E-Commerce Dashboard (Interactive Version)
Allows users to upload their own data files and download processed results
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime
import os
import io
import sys

# Import the processing pipeline
sys.path.append(os.path.dirname(__file__))
from main_interactive import process_uploaded_data

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
    .upload-section {
        background-color: #e8f4f8;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
    }
    </style>
""", unsafe_allow_html=True)


def load_default_data():
    """Load default data files"""
    try:
        # Get the directory of this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Try multiple path configurations (local and Azure)
        possible_paths = [
            # Local development path
            (os.path.join(current_dir, '..', 'input-data', 'ecommerce_orders.csv'),
             os.path.join(current_dir, '..', 'input-data', 'tariff.csv')),
            # Azure deployment path
            (os.path.join('/home/site/wwwroot', 'input-data', 'ecommerce_orders.csv'),
             os.path.join('/home/site/wwwroot', 'input-data', 'tariff.csv')),
            # Alternative Azure path
            (os.path.join(current_dir, 'input-data', 'ecommerce_orders.csv'),
             os.path.join(current_dir, 'input-data', 'tariff.csv')),
        ]
        
        # Try each path configuration
        for orders_path, tariff_path in possible_paths:
            if os.path.exists(orders_path) and os.path.exists(tariff_path):
                orders_df = pd.read_csv(orders_path)
                tariff_df = pd.read_csv(tariff_path)
                return orders_df, tariff_df, True
        
        # If no paths work, raise an error
        raise FileNotFoundError("Default data files not found. Please upload your own data files.")
        
    except Exception as e:
        st.error(f"Error loading default data: {e}")
        st.info("💡 Tip: Please use the 'Upload' feature to provide your own data files.")
        return None, None, False


def process_and_cache_data(orders_df, tariff_df):
    """Process data and cache results"""
    try:
        processed_df, summary, alerts_df = process_uploaded_data(orders_df, tariff_df)
        return processed_df, summary, alerts_df, True
    except Exception as e:
        st.error(f"Error processing data: {e}")
        st.error("Please ensure your data files have the correct format.")
        return None, None, None, False


def main():
    """Main dashboard function"""
    
    # Header
    st.title("🌐 WCO 2026 Hackathon - Customs E-Commerce Dashboard")
    st.markdown("**Mission:** Operationalizing the WCO Framework of Standards")
    st.markdown("**Location:** Abu Dhabi Customs Entry Point")
    st.divider()
    
    # Initialize session state
    if 'processed_df' not in st.session_state:
        st.session_state.processed_df = None
        st.session_state.summary = None
        st.session_state.alerts_df = None
        st.session_state.data_loaded = False
    
    # Data Upload Section - Make it collapsible when data is loaded
    with st.expander("📂 Data Upload & Processing", expanded=not st.session_state.data_loaded):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("E-Commerce Orders File")
            orders_file = st.file_uploader(
                "Upload your orders CSV file",
                type=['csv'],
                key='orders_upload',
                help="CSV file containing e-commerce order data"
            )
        
        with col2:
            st.subheader("Tariff Book File")
            tariff_file = st.file_uploader(
                "Upload your tariff CSV file",
                type=['csv'],
                key='tariff_upload',
                help="CSV file containing tariff rate information"
            )
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            process_button = st.button("🔄 Process Uploaded Data", type="primary", use_container_width=True)
        
        with col2:
            load_default_button = st.button("📋 Load Default Data", use_container_width=True)
        
        with col3:
            clear_button = st.button("🗑️ Clear Data", use_container_width=True)
    
    # Handle button clicks
    if clear_button:
        st.session_state.processed_df = None
        st.session_state.summary = None
        st.session_state.alerts_df = None
        st.session_state.data_loaded = False
        st.rerun()
    
    if load_default_button:
        with st.spinner("Loading default data..."):
            orders_df, tariff_df, success = load_default_data()
            if success:
                processed_df, summary, alerts_df, success = process_and_cache_data(orders_df, tariff_df)
                if success:
                    st.session_state.processed_df = processed_df
                    st.session_state.summary = summary
                    st.session_state.alerts_df = alerts_df
                    st.session_state.data_loaded = True
                    st.success("✅ Default data loaded and processed successfully!")
                    st.rerun()
    
    if process_button:
        if orders_file is not None and tariff_file is not None:
            with st.spinner("Processing your data..."):
                try:
                    orders_df = pd.read_csv(orders_file)
                    tariff_df = pd.read_csv(tariff_file)
                    
                    processed_df, summary, alerts_df, success = process_and_cache_data(orders_df, tariff_df)
                    
                    if success:
                        st.session_state.processed_df = processed_df
                        st.session_state.summary = summary
                        st.session_state.alerts_df = alerts_df
                        st.session_state.data_loaded = True
                        st.success("✅ Data processed successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error reading files: {e}")
        else:
            st.warning("⚠️ Please upload both files before processing.")
    
    # Display dashboard if data is loaded
    if not st.session_state.data_loaded:
        st.info("👆 Please upload your data files and click 'Process Uploaded Data' or click 'Load Default Data' to view the dashboard.")
        
        # Show sample format information
        with st.expander("ℹ️ Required File Format Information"):
            st.markdown("""
            ### E-Commerce Orders CSV
            Required columns:
            - `order_id`, `timestamp`, `importer_name`, `delivery_address`
            - `product_category`, `product_title`, `description`
            - `item_price_inr`, `total_order_value_inr`
            - `pid` (product ID)
            
            ### Tariff CSV
            Required columns:
            - `Chapter_Start`, `Chapter_End`, `Simplified_Duty_Rate`
            
            Date format: `DD/MM/YYYY HH:MM`
            """)
        return
    
    df = st.session_state.processed_df
    summary = st.session_state.summary
    alerts_df = st.session_state.alerts_df
    
    # Show success message with data info
    st.success(f"✅ Data loaded successfully! Processing {len(df):,} items from {df['order_id'].nunique():,} orders.")
    
    # Download section
    st.divider()
    st.header("📥 Download Processed Results")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Full results CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="📄 Download Full Results (CSV)",
            data=csv_buffer.getvalue(),
            file_name=f"customs_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Summary JSON
        json_str = json.dumps(summary, indent=2)
        st.download_button(
            label="📊 Download Summary (JSON)",
            data=json_str,
            file_name=f"processing_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col3:
        # Alerts CSV
        if alerts_df is not None and len(alerts_df) > 0:
            alerts_buffer = io.StringIO()
            alerts_df.to_csv(alerts_buffer, index=False)
            st.download_button(
                label="⚠️ Download Alerts (CSV)",
                data=alerts_buffer.getvalue(),
                file_name=f"alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.button("⚠️ No Alerts", disabled=True, use_container_width=True)
    
    with col4:
        # Excel export with all sheets
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Full Results', index=False)
            if alerts_df is not None and len(alerts_df) > 0:
                alerts_df.to_excel(writer, sheet_name='Alerts', index=False)
            
            # Summary as dataframe
            summary_df = pd.DataFrame([summary])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        st.download_button(
            label="📊 Download All (Excel)",
            data=excel_buffer.getvalue(),
            file_name=f"customs_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    st.divider()
    
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
        total_duty = df['duty_aed'].sum() if 'duty_aed' in df.columns else 0
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
        
        if len(split_df) > 0:
            st.subheader("Split Shipment Details")
            
            display_cols = ['order_id', 'importer_name', 'date', 'order_count', 
                          'daily_total_value_aed', 'duty_aed', 'product_title']
            display_cols = [col for col in display_cols if col in split_df.columns]
            
            st.dataframe(
                split_df[display_cols].sort_values('daily_total_value_aed', ascending=False),
                use_container_width=True,
                height=400
            )
            
            # Download split shipments
            split_csv = io.StringIO()
            split_df.to_csv(split_csv, index=False)
            st.download_button(
                label="📥 Download Split Shipments",
                data=split_csv.getvalue(),
                file_name=f"split_shipments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
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
        
        if 'duty_aed' in df.columns:
            dutiable_df = df[df['duty_aed'] > 0].copy()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Total Duty",
                    f"{df['duty_aed'].sum():,.2f} AED"
                )
            
            with col2:
                st.metric(
                    "Dutiable Items",
                    f"{len(dutiable_df):,}",
                    delta=f"{len(dutiable_df)/len(df)*100:.1f}%" if len(df) > 0 else "0%"
                )
            
            with col3:
                avg_duty = df['duty_aed'].sum() / len(dutiable_df) if len(dutiable_df) > 0 else 0
                st.metric(
                    "Avg Duty/Item",
                    f"{avg_duty:.2f} AED"
                )
            
            if len(dutiable_df) > 0:
                st.subheader("Dutiable Items")
                
                display_cols = ['order_id', 'product_title', 'item_price_aed', 
                              'hs_code', 'tariff_rate', 'duty_aed']
                display_cols = [col for col in display_cols if col in dutiable_df.columns]
                
                st.dataframe(
                    dutiable_df[display_cols].sort_values('duty_aed', ascending=False),
                    use_container_width=True,
                    height=400
                )
                
                # Download dutiable items
                dutiable_csv = io.StringIO()
                dutiable_df.to_csv(dutiable_csv, index=False)
                st.download_button(
                    label="📥 Download Dutiable Items",
                    data=dutiable_csv.getvalue(),
                    file_name=f"dutiable_items_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
                
                if 'hs_code' in dutiable_df.columns:
                    duty_by_hs = dutiable_df.groupby('hs_code')['duty_aed'].sum().sort_values(ascending=False).head(10)
                    
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
        
        if len(risk_df) > 0:
            st.subheader("Flagged Items with Rationale")
            
            display_cols = ['order_id', 'product_title', 'risk_flag_code', 'risk_reason', 
                          'item_price_aed', 'duty_aed']
            display_cols = [col for col in display_cols if col in risk_df.columns]
            
            st.dataframe(
                risk_df[display_cols],
                use_container_width=True,
                height=400
            )
            
            # Download risk items
            risk_csv = io.StringIO()
            risk_df.to_csv(risk_csv, index=False)
            st.download_button(
                label="📥 Download Flagged Items",
                data=risk_csv.getvalue(),
                file_name=f"flagged_items_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
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
        
        if 'date' in df.columns:
            daily_stats = df.groupby('date').agg({
                'order_id': 'nunique',
                'duty_aed': 'sum',
                'split_shipment_detected': lambda x: (x == 'Y').sum(),
                'risk_flag_code': lambda x: (x != 'NONE').sum()
            }).reset_index()
            
            daily_stats.columns = ['Date', 'Orders', 'Duty (AED)', 'Split Shipments', 'Risk Flags']
            
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
            
            fig2 = px.area(
                daily_stats,
                x='Date',
                y='Duty (AED)',
                title='Daily Duty Collection'
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        if 'importer_name' in df.columns:
            st.subheader("Top Importers")
            
            top_importers = df.groupby('importer_name').agg({
                'order_id': 'nunique',
                'item_price_aed': 'sum',
                'duty_aed': 'sum',
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
            
            # Download top importers
            importers_csv = io.StringIO()
            top_importers.to_csv(importers_csv, index=False)
            st.download_button(
                label="📥 Download Top Importers",
                data=importers_csv.getvalue(),
                file_name=f"top_importers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    with tab5:
        st.header("⚠️ High Priority Alerts")
        
        if alerts_df is not None and len(alerts_df) > 0:
            st.warning(f"**{len(alerts_df):,} items require immediate attention**")
            
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
            
            # Download alerts
            alerts_csv = io.StringIO()
            filtered_alerts.to_csv(alerts_csv, index=False)
            st.download_button(
                label="📥 Download Filtered Alerts",
                data=alerts_csv.getvalue(),
                file_name=f"alerts_{alert_type.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.success("No high-priority alerts in the current dataset!")
    
    # Footer
    st.divider()
    st.markdown(f"""
        <div style='text-align: center; color: #666;'>
            <p>WCO 2026 Hackathon | Abu Dhabi Customs Entry Point</p>
            <p>Powered by the WCO Framework of Standards</p>
            <p>Last processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
