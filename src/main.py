#!/usr/bin/env python3
"""
WCO 2026 Hackathon - Customs E-Commerce Processing Pipeline
Mission: Operationalizing the WCO Framework of Standards on Cross-Border E-Commerce

This pipeline processes advance electronic data from e-commerce orders and applies
four logic gates for risk assessment and revenue collection.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import re
import json
from collections import defaultdict
import requests
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


class CustomsECommercePipeline:
    """
    Customs E-Commerce Processing Pipeline
    Implements the WCO Framework of Standards with 4 Logic Gates
    """
    
    def __init__(self, orders_file: str, tariff_file: str):
        """Initialize the pipeline with order and tariff data"""
        self.orders_file = orders_file
        self.tariff_file = tariff_file
        self.df = None
        self.tariff_df = None
        
        # Constants
        self.INR_TO_AED = 0.044
        self.DE_MINIMIS_THRESHOLD = 1000  # AED
        
        # HS Code API Configuration (optional)
        self.HS_API_URL = "https://adc-rms-dev2.ttekglobal.com/api/hs-code-predictor/hs-code-classification"
        self.HS_API_HEADERS = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Basic dHRlazpzSzhpTHVRQUhtbG5JNGF4'
        }
        self.USE_API = False  # Set to True to use external API
        
        # Risk profiles from Risk Intelligence document
        self.risk_profiles = {
            'A1_LITHIUM_BATTERIES': {
                'keywords': ['power bank', 'lithium', 'li-ion', 'li ion', 'battery', 'portable charger'],
                'category': 'A - DANGEROUS GOODS',
                'reason': 'Fire hazard / Thermal runaway',
                'action': 'FLAG FOR INSPECTION - Verify if battery is contained in equipment',
                'code': 'A1'
            },
            'A2_WEAPONS': {
                'keywords': ['knife', 'dagger', 'blade', 'sword', 'cutter', 'machete'],
                'category': 'A - DANGEROUS GOODS',
                'reason': 'Physical security threat / Prohibited items',
                'action': 'FLAG FOR PHYSICAL EXAM - Check if kitchenware or prohibited weapon',
                'code': 'A2'
            },
            'B1_DRONES': {
                'keywords': ['drone', 'quadcopter', 'spy camera', 'hidden camera', 'uav'],
                'category': 'B - RESTRICTED & CONTROLLED',
                'reason': 'Security / Privacy / Airspace regulation',
                'action': 'HOLD FOR PERMIT CHECK',
                'code': 'B1'
            },
            'B2_PRECIOUS_METALS': {
                'keywords': ['gold', 'diamond', 'silver', 'jewellery', 'jewelry'],
                'category': 'B - RESTRICTED & CONTROLLED',
                'reason': 'Money Laundering / Smuggling / Revenue Leakage',
                'action': 'VALUATION ALERT - Cross-reference with Level 3 Engine',
                'code': 'B2',
                'value_threshold': 5000  # AED
            }
        }
        
        # HS Code classification rules (fallback if API not used)
        self.hs_classification_rules = {
            # Clothing & Textiles
            r'mens.*shirt': '620520',
            r'mens.*jeans': '620342',
            r'mens.*trouser|mens.*pant': '620349',
            r'mens.*jacket': '620333',
            r'womens.*shirt|ladies.*shirt|womens.*top|ladies.*top': '620640',
            r'womens.*jeans|ladies.*jeans': '620462',
            r'womens.*dress|ladies.*dress': '620444',
            r'muffler|scarf': '621410',
            r'towel': '630260',
            
            # Electronics
            r'power bank|portable charger': '850760',
            r'battery|lithium': '850760',
            r'mobile|phone|smartphone': '851712',
            r'tablet|ipad': '847130',
            r'router|modem': '851762',
            r'camera|webcam': '852580',
            r'drone|quadcopter|uav': '880692',
            
            # Automotive
            r'car mat|floor mat|car interior': '570500',
            r'car accessory|auto accessory': '870899',
            
            # Jewelry
            r'necklace|chain': '711719',
            r'bangle|bracelet': '711719',
            r'ring': '711319',
            r'earring': '711711',
            
            # Home & Garden
            r'plant container|pot|planter': '691390',
            r'furniture': '940380',
            
            # Cases & Covers
            r'case.*phone|cover.*phone|phone.*case|phone.*cover': '392690',
            r'case.*tablet|cover.*tablet|tablet.*case|tablet.*cover': '420292',
        }
    
    def load_data(self):
        """Load and prepare the order and tariff data"""
        print("=" * 80)
        print("🌐 WCO 2026 HACKATHON - CUSTOMS E-COMMERCE PROCESSING PIPELINE")
        print("=" * 80)
        print("Mission: Operationalizing the WCO Framework of Standards")
        print("Location: Abu Dhabi Customs Entry Point")
        print("=" * 80)
        
        print("\n📦 Loading E-Commerce Orders...")
        self.df = pd.read_csv(self.orders_file, low_memory=False)
        
        # Parse timestamp to datetime
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], format='%d/%m/%Y %H:%M', errors='coerce')
        self.df['date'] = pd.to_datetime(self.df['timestamp']).dt.date
        
        # Track invalid dates
        total_records = len(self.df)
        invalid_dates = self.df['date'].isna().sum()
        
        # Remove rows with invalid dates
        self.df = self.df[self.df['date'].notna()].copy()
        
        print(f"   Total records in file: {total_records:,}")
        print(f"   Records with valid dates: {len(self.df):,} ({len(self.df)/total_records*100:.1f}%)")
        if invalid_dates > 0:
            print(f"   ⚠️  Records excluded (invalid dates): {invalid_dates:,}")
        
        # Convert prices to AED
        self.df['item_price_aed'] = self.df['item_price_inr'] * self.INR_TO_AED
        self.df['total_order_value_aed'] = self.df['total_order_value_inr'] * self.INR_TO_AED
        
        # Create unique identifier for importer-address-date
        self.df['importer_key'] = (
            self.df['importer_name'].str.strip().str.lower() + '|' +
            self.df['delivery_address'].str.strip().str.lower() + '|' +
            self.df['date'].astype(str)
        )
        
        print(f"\n✅ Data Loading Complete:")
        print(f"   • Items: {len(self.df):,}")
        print(f"   • Orders: {self.df['order_id'].nunique():,}")
        print(f"   • Unique importers: {self.df['importer_name'].nunique():,}")
        print(f"   • Date range: {self.df['date'].min()} to {self.df['date'].max()}")
        
        # Load tariff data
        print(f"\n📋 Loading Tariff Book...")
        self.tariff_df = pd.read_csv(self.tariff_file)
        print(f"   ✅ Loaded {len(self.tariff_df)} tariff sections")
        
        return self.df
    
    def level_1_identity_engine(self):
        """
        LEVEL 1: Identity Engine - Detect Split Shipments
        
        Goal: Identify the true daily total value for each unique person
        Logic: Aggregate by Importer Name + Delivery Address + Date
        """
        print("\n" + "=" * 80)
        print("🔍 LEVEL 1: IDENTITY ENGINE - Detecting Split Shipments")
        print("=" * 80)
        
        # Calculate daily totals per importer
        daily_totals = self.df.groupby('importer_key').agg({
            'importer_name': 'first',
            'delivery_address': 'first',
            'date': 'first',
            'order_id': 'nunique',  # Count unique orders
            'item_price_aed': 'sum',  # Total value for the day
            'pid': 'count'  # Count items
        }).reset_index()
        
        daily_totals.columns = ['importer_key', 'importer_name', 'delivery_address', 
                               'date', 'order_count', 'daily_total_value_aed', 'item_count']
        
        # Flag split shipments (multiple orders on same day)
        daily_totals['is_split_shipment'] = daily_totals['order_count'] > 1
        daily_totals['exceeds_threshold'] = daily_totals['daily_total_value_aed'] > self.DE_MINIMIS_THRESHOLD
        daily_totals['revenue_risk'] = daily_totals['is_split_shipment'] & daily_totals['exceeds_threshold']
        
        # Merge back to main dataframe
        self.df = self.df.merge(
            daily_totals[['importer_key', 'daily_total_value_aed', 'order_count', 
                         'is_split_shipment', 'exceeds_threshold', 'revenue_risk']],
            on='importer_key',
            how='left'
        )
        
        # Add split shipment flag (Y/N)
        self.df['split_shipment_detected'] = self.df['is_split_shipment'].map({True: 'Y', False: 'N'})
        
        # Statistics
        split_shipments = daily_totals[daily_totals['is_split_shipment']]
        revenue_risks = daily_totals[daily_totals['revenue_risk']]
        
        print(f"\n📊 Results:")
        print(f"   • Total importer-days: {len(daily_totals):,}")
        print(f"   • Split shipments detected: {len(split_shipments):,} ({len(split_shipments)/len(daily_totals)*100:.1f}%)")
        print(f"   • Revenue risks (split + exceeds threshold): {len(revenue_risks):,} ({len(revenue_risks)/len(daily_totals)*100:.1f}%)")
        print(f"   • Potential revenue at risk: {revenue_risks['daily_total_value_aed'].sum():,.2f} AED")
        
        return self.df
    
    def get_hs_code_from_api(self, description: str) -> Tuple[str, str]:
        """Get HS code from external API"""
        try:
            payload = {"goods_description": description}
            response = requests.post(
                self.HS_API_URL,
                headers=self.HS_API_HEADERS,
                json=payload,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                # Adjust based on actual API response structure
                hs_code = data.get('hs_code', '999999')
                return hs_code, 'API_MATCH'
            else:
                return '999999', 'API_ERROR'
        except Exception as e:
            return '999999', 'API_ERROR'
    
    def classify_item_rule_based(self, text: str) -> Tuple[str, str]:
        """Classify item using rule-based pattern matching"""
        text_lower = text.lower()
        
        # Try to match classification rules
        for pattern, hs_code in self.hs_classification_rules.items():
            if re.search(pattern, text_lower):
                return hs_code, 'RULE_MATCH'
        
        # Fallback for unclassified items
        return '999999', 'NO_MATCH'
    
    def level_2_classification_engine(self):
        """
        LEVEL 2: Classification Engine - Assign HS Codes
        
        Goal: Assign HS codes to items using NLP or external API
        Method: External API (optional) or rule-based pattern matching
        """
        print("\n" + "=" * 80)
        print("🏷️  LEVEL 2: CLASSIFICATION ENGINE - Assigning HS Codes")
        print("=" * 80)
        
        if self.USE_API:
            print("   Using external HS code prediction API...")
        else:
            print("   Using rule-based classification...")
        
        def classify_row(row):
            # Combine all text fields for classification
            text = ' '.join([
                str(row.get('product_category', '')),
                str(row.get('product_title', '')),
                str(row.get('description', ''))
            ])
            
            if self.USE_API:
                hs_code, status = self.get_hs_code_from_api(text)
            else:
                hs_code, status = self.classify_item_rule_based(text)
            
            return pd.Series({
                'hs_code': hs_code,
                'classification_status': status
            })
        
        # Apply classification
        print("   Processing items...")
        classification_results = self.df.apply(classify_row, axis=1)
        self.df['hs_code'] = classification_results['hs_code']
        self.df['classification_status'] = classification_results['classification_status']
        
        # Extract chapter (first 2 digits) for tariff lookup
        self.df['hs_chapter'] = self.df['hs_code'].str[:2].astype(int, errors='ignore')
        
        # Statistics
        matched = len(self.df[self.df['classification_status'].str.contains('MATCH')])
        unmatched = len(self.df[self.df['classification_status'] == 'NO_MATCH'])
        
        print(f"\n📊 Results:")
        print(f"   • Successfully classified: {matched:,} items ({matched/len(self.df)*100:.1f}%)")
        print(f"   • Requires manual review: {unmatched:,} items ({unmatched/len(self.df)*100:.1f}%)")
        print(f"   • Unique HS codes assigned: {self.df['hs_code'].nunique():,}")
        
        return self.df
    
    def get_tariff_rate(self, hs_chapter: int) -> float:
        """Get tariff rate from tariff table based on HS chapter"""
        try:
            hs_chapter = int(hs_chapter)
            for _, row in self.tariff_df.iterrows():
                chapter_start = int(row['Chapter_Start'])
                chapter_end = int(row['Chapter_End'])
                if chapter_start <= hs_chapter <= chapter_end:
                    return float(row['Simplified_Duty_Rate']) / 100  # Convert percentage to decimal
            return 0.05  # Default 5% if not found
        except:
            return 0.05
    
    def level_3_valuation_engine(self):
        """
        LEVEL 3: Valuation Engine - Calculate Duties
        
        Goal: Apply de minimis rule and calculate duty
        Logic: If daily total > 1000 AED, apply tariff to individual items
        """
        print("\n" + "=" * 80)
        print("💰 LEVEL 3: VALUATION ENGINE - Calculating Duties")
        print("=" * 80)
        
        # Get tariff rate for each item based on HS chapter
        print("   Applying tariff rates from tariff book...")
        self.df['tariff_rate'] = self.df['hs_chapter'].apply(self.get_tariff_rate)
        
        # Calculate duty based on de minimis rule
        # If daily total > 1000 AED, calculate duty; otherwise duty = 0
        self.df['duty_aed'] = np.where(
            self.df['daily_total_value_aed'] > self.DE_MINIMIS_THRESHOLD,
            self.df['item_price_aed'] * self.df['tariff_rate'],
            0
        )
        
        # Round to 2 decimal places
        self.df['duty_aed'] = self.df['duty_aed'].round(2)
        
        # Calculate summary statistics
        total_duty = self.df['duty_aed'].sum()
        dutiable_items = len(self.df[self.df['duty_aed'] > 0])
        duty_free_items = len(self.df[self.df['duty_aed'] == 0])
        
        print(f"\n📊 Results:")
        print(f"   • Total customs duty: {total_duty:,.2f} AED")
        print(f"   • Dutiable items: {dutiable_items:,} ({dutiable_items/len(self.df)*100:.1f}%)")
        print(f"   • Duty-free items: {duty_free_items:,} ({duty_free_items/len(self.df)*100:.1f}%)")
        if dutiable_items > 0:
            print(f"   • Average duty per dutiable item: {total_duty/dutiable_items:.2f} AED")
        
        return self.df
    
    def level_4_protection_engine(self):
        """
        LEVEL 4: Protection Engine - Flag Safety & Security Risks
        
        Goal: Flag prohibited or restricted items
        Logic: Match against risk profiles from Risk Intelligence
        """
        print("\n" + "=" * 80)
        print("🛡️  LEVEL 4: PROTECTION ENGINE - Scanning for Risks")
        print("=" * 80)
        
        def check_risk(row):
            """Check if item matches any risk profile"""
            # Combine text fields
            text = ' '.join([
                str(row.get('product_category', '')),
                str(row.get('product_title', '')),
                str(row.get('description', ''))
            ]).lower()
            
            risk_codes = []
            risk_reasons = []
            
            for risk_name, profile in self.risk_profiles.items():
                # Check if any keyword matches
                for keyword in profile['keywords']:
                    if keyword.lower() in text:
                        # Special check for precious metals (value threshold)
                        if risk_name == 'B2_PRECIOUS_METALS':
                            if row['item_price_aed'] > profile.get('value_threshold', 5000):
                                risk_codes.append(profile['code'])
                                risk_reasons.append(f"{profile['reason']} - {profile['action']}")
                                break
                        else:
                            risk_codes.append(profile['code'])
                            risk_reasons.append(f"{profile['reason']} - {profile['action']}")
                            break
            
            return pd.Series({
                'risk_flag_code': '|'.join(risk_codes) if risk_codes else 'NONE',
                'risk_reason': '|'.join(risk_reasons) if risk_reasons else 'NONE'
            })
        
        # Apply risk checking
        print("   Scanning items for risk indicators...")
        risk_results = self.df.apply(check_risk, axis=1)
        self.df['risk_flag_code'] = risk_results['risk_flag_code']
        self.df['risk_reason'] = risk_results['risk_reason']
        
        # Statistics
        flagged = len(self.df[self.df['risk_flag_code'] != 'NONE'])
        category_a = len(self.df[self.df['risk_flag_code'].str.contains('A', na=False)])
        category_b = len(self.df[self.df['risk_flag_code'].str.contains('B', na=False)])
        
        print(f"\n📊 Results:")
        print(f"   • Items flagged for inspection: {flagged:,} ({flagged/len(self.df)*100:.1f}%)")
        print(f"   • Category A (Dangerous Goods): {category_a:,}")
        print(f"   • Category B (Restricted Items): {category_b:,}")
        
        # Show top risk types
        if flagged > 0:
            risk_summary = self.df[self.df['risk_flag_code'] != 'NONE']['risk_flag_code'].value_counts().head(5)
            print("\n   Top Risk Flags:")
            for risk_code, count in risk_summary.items():
                print(f"      • {risk_code}: {count:,} items")
        
        return self.df
    
    def generate_outputs(self):
        """Generate output files with processing results"""
        print("\n" + "=" * 80)
        print("📊 GENERATING OUTPUT FILES")
        print("=" * 80)
        
        # Main output with requested columns
        output_columns = [
            'order_id',
            'split_shipment_detected',
            'duty_aed',
            'risk_flag_code',
            'risk_reason',
            # Additional useful columns
            'timestamp',
            'date',
            'importer_name',
            'delivery_address',
            'product_title',
            'description',
            'item_price_inr',
            'item_price_aed',
            'daily_total_value_aed',
            'order_count',
            'exceeds_threshold',
            'hs_code',
            'tariff_rate',
            'classification_status'
        ]
        
        # Rename duty column for output
        output_df = self.df.copy()
        output_df.rename(columns={'duty_aed': 'duty'}, inplace=True)
        
        # Generate CSV output
        csv_output_path = '../output-data/customs_processing_results.csv'
        output_df[['order_id', 'split_shipment_detected', 'duty', 'risk_flag_code', 'risk_reason'] + 
                   [col for col in output_columns if col not in ['order_id', 'split_shipment_detected', 'duty_aed', 'risk_flag_code', 'risk_reason']]].to_csv(
            csv_output_path, index=False
        )
        print(f"   ✅ CSV output: {csv_output_path}")
        
        # Generate JSON output (summary per order)
        order_summary = self.df.groupby('order_id').agg({
            'split_shipment_detected': 'first',
            'duty_aed': 'sum',
            'risk_flag_code': lambda x: '|'.join(set([r for r in x if r != 'NONE'])) or 'NONE',
            'risk_reason': lambda x: '|'.join(set([r for r in x if r != 'NONE'])) or 'NONE',
            'importer_name': 'first',
            'daily_total_value_aed': 'first',
            'item_price_aed': 'sum'
        }).reset_index()
        
        order_summary.rename(columns={'duty_aed': 'total_duty_aed'}, inplace=True)
        
        json_output_path = '../output-data/customs_processing_results.json'
        order_summary.to_json(json_output_path, orient='records', indent=2)
        print(f"   ✅ JSON output: {json_output_path}")
        
        # Generate summary statistics
        summary = {
            'processing_timestamp': datetime.now().isoformat(),
            'total_items_processed': len(self.df),
            'total_orders': self.df['order_id'].nunique(),
            'unique_importers': self.df['importer_name'].nunique(),
            'date_range': {
                'start': str(self.df['date'].min()),
                'end': str(self.df['date'].max())
            },
            'level_1_identity': {
                'split_shipments_detected': int(self.df[self.df['split_shipment_detected'] == 'Y']['order_id'].nunique()),
                'revenue_risks': int(self.df['revenue_risk'].sum()),
                'affected_value_aed': float(self.df[self.df['revenue_risk']]['daily_total_value_aed'].sum())
            },
            'level_2_classification': {
                'items_classified': int(self.df[self.df['classification_status'].str.contains('MATCH')].count()['hs_code']),
                'items_requiring_review': int((self.df['classification_status'] == 'NO_MATCH').sum()),
                'unique_hs_codes': int(self.df['hs_code'].nunique())
            },
            'level_3_valuation': {
                'total_duty_collected_aed': float(self.df['duty_aed'].sum()),
                'dutiable_items': int((self.df['duty_aed'] > 0).sum()),
                'duty_free_items': int((self.df['duty_aed'] == 0).sum())
            },
            'level_4_protection': {
                'items_flagged': int((self.df['risk_flag_code'] != 'NONE').sum()),
                'category_a_dangerous': int(self.df['risk_flag_code'].str.contains('A', na=False).sum()),
                'category_b_restricted': int(self.df['risk_flag_code'].str.contains('B', na=False).sum())
            }
        }
        
        summary_path = '../output-data/processing_summary.json'
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"   ✅ Summary: {summary_path}")
        
        # Generate high-priority alerts
        alerts = self.df[
            (self.df['revenue_risk']) | 
            (self.df['risk_flag_code'] != 'NONE') |
            (self.df['classification_status'] == 'NO_MATCH')
        ].copy()
        
        if len(alerts) > 0:
            alerts_path = '../output-data/high_priority_alerts.csv'
            alerts.to_csv(alerts_path, index=False)
            print(f"   ⚠️  High-priority alerts: {alerts_path} ({len(alerts):,} items)")
        
        print(f"\n✅ All output files generated successfully!")
        
        return {
            'csv_output': csv_output_path,
            'json_output': json_output_path,
            'summary': summary_path,
            'alerts': alerts_path if len(alerts) > 0 else None
        }
    
    def run_pipeline(self):
        """Execute the complete customs processing pipeline"""
        # Load data
        self.load_data()
        
        # Execute all four logic gates
        self.level_1_identity_engine()
        self.level_2_classification_engine()
        self.level_3_valuation_engine()
        self.level_4_protection_engine()
        
        # Generate outputs
        output_files = self.generate_outputs()
        
        print("\n" + "=" * 80)
        print("✅ PIPELINE EXECUTION COMPLETE")
        print("=" * 80)
        
        # Final summary
        print(f"\n📈 FINAL STATISTICS:")
        print(f"   • Total items processed: {len(self.df):,}")
        print(f"   • Total orders processed: {self.df['order_id'].nunique():,}")
        print(f"   • Revenue collected: {self.df['duty_aed'].sum():,.2f} AED")
        print(f"   • Items requiring inspection: {(self.df['risk_flag_code'] != 'NONE').sum():,}")
        print(f"   • Split shipment breaches: {(self.df['split_shipment_detected'] == 'Y').sum():,}")
        
        return self.df, output_files


def main():
    """Main execution function"""
    # Initialize the pipeline
    pipeline = CustomsECommercePipeline(
        orders_file='../input-data/ecommerce_orders.csv',
        tariff_file='../input-data/tariff.csv'
    )
    
    # Run the pipeline
    results_df, output_files = pipeline.run_pipeline()
    
    print("\n" + "=" * 80)
    print("🎯 OUTPUT FILES READY FOR REVIEW")
    print("=" * 80)
    print("\nGenerated files:")
    for key, path in output_files.items():
        if path:
            print(f"   • {key}: {path}")
    
    return results_df, output_files


if __name__ == "__main__":
    results_df, output_files = main()
