#!/usr/bin/env python3
"""
WCO 2026 Hackathon - Customs E-Commerce Processing Pipeline (Interactive Version)
Allows users to upload their own data files and download processed results
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
import os
import sys
warnings.filterwarnings('ignore')


class CustomsECommercePipeline:
    """
    Customs E-Commerce Processing Pipeline
    Implements the WCO Framework of Standards with 4 Logic Gates
    """
    
    def __init__(self, orders_df: pd.DataFrame, tariff_df: pd.DataFrame):
        """Initialize the pipeline with order and tariff dataframes"""
        self.df = orders_df.copy()
        self.tariff_df = tariff_df.copy()
        
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
        self.USE_API = True  # Set to True to use external API
        
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
    
    def prepare_data(self):
        """Prepare and clean the order data"""
        # Parse timestamp to datetime
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], format='%d/%m/%Y %H:%M', errors='coerce')
        self.df['date'] = pd.to_datetime(self.df['timestamp']).dt.date
        
        # Remove rows with invalid dates
        self.df = self.df[self.df['date'].notna()].copy()
        
        # Convert prices to AED
        self.df['item_price_aed'] = self.df['item_price_inr'] * self.INR_TO_AED
        self.df['total_order_value_aed'] = self.df['total_order_value_inr'] * self.INR_TO_AED
        
        # Create unique identifier for importer-address-date
        self.df['importer_key'] = (
            self.df['importer_name'].str.strip().str.lower() + '|' +
            self.df['delivery_address'].str.strip().str.lower() + '|' +
            self.df['date'].astype(str)
        )
        
        return self.df
    
    def level_1_identity_engine(self):
        """LEVEL 1: Identity Engine - Detect Split Shipments"""
        # Calculate daily totals per importer
        daily_totals = self.df.groupby('importer_key').agg({
            'importer_name': 'first',
            'delivery_address': 'first',
            'date': 'first',
            'order_id': 'nunique',
            'item_price_aed': 'sum',
            'pid': 'count'
        }).reset_index()
        
        daily_totals.columns = ['importer_key', 'importer_name', 'delivery_address', 
                               'date', 'order_count', 'daily_total_value_aed', 'item_count']
        
        # Flag split shipments
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
        
        self.df['split_shipment_detected'] = self.df['is_split_shipment'].map({True: 'Y', False: 'N'})
        
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
                hs_code = data.get('hs_code', '999999')
                return hs_code, 'API_MATCH'
            else:
                return '999999', 'API_ERROR'
        except Exception as e:
            return '999999', 'API_ERROR'
    
    def classify_item_rule_based(self, text: str) -> Tuple[str, str]:
        """Classify item using rule-based pattern matching"""
        text_lower = text.lower()
        
        for pattern, hs_code in self.hs_classification_rules.items():
            if re.search(pattern, text_lower):
                return hs_code, 'RULE_MATCH'
        
        return '999999', 'NO_MATCH'
    
    def level_2_classification_engine(self):
        """LEVEL 2: Classification Engine - Assign HS Codes"""
        def classify_row(row):
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
        
        classification_results = self.df.apply(classify_row, axis=1)
        self.df['hs_code'] = classification_results['hs_code']
        self.df['classification_status'] = classification_results['classification_status']
        self.df['hs_chapter'] = self.df['hs_code'].str[:2].astype(int, errors='ignore')
        
        return self.df
    
    def get_tariff_rate(self, hs_chapter: int) -> float:
        """Get tariff rate from tariff table based on HS chapter"""
        try:
            hs_chapter = int(hs_chapter)
            for _, row in self.tariff_df.iterrows():
                chapter_start = int(row['Chapter_Start'])
                chapter_end = int(row['Chapter_End'])
                if chapter_start <= hs_chapter <= chapter_end:
                    return float(row['Simplified_Duty_Rate']) / 100
            return 0.05
        except:
            return 0.05
    
    def level_3_valuation_engine(self):
        """LEVEL 3: Valuation Engine - Calculate Duties"""
        self.df['tariff_rate'] = self.df['hs_chapter'].apply(self.get_tariff_rate)
        
        self.df['duty_aed'] = np.where(
            self.df['daily_total_value_aed'] > self.DE_MINIMIS_THRESHOLD,
            self.df['item_price_aed'] * self.df['tariff_rate'],
            0
        )
        
        self.df['duty_aed'] = self.df['duty_aed'].round(2)
        
        return self.df
    
    def level_4_protection_engine(self):
        """LEVEL 4: Protection Engine - Flag Safety & Security Risks"""
        def check_risk(row):
            text = ' '.join([
                str(row.get('product_category', '')),
                str(row.get('product_title', '')),
                str(row.get('description', ''))
            ]).lower()
            
            risk_codes = []
            risk_reasons = []
            
            for risk_name, profile in self.risk_profiles.items():
                for keyword in profile['keywords']:
                    if keyword.lower() in text:
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
        
        risk_results = self.df.apply(check_risk, axis=1)
        self.df['risk_flag_code'] = risk_results['risk_flag_code']
        self.df['risk_reason'] = risk_results['risk_reason']
        
        return self.df
    
    def run_pipeline(self):
        """Execute the complete customs processing pipeline"""
        self.prepare_data()
        self.level_1_identity_engine()
        self.level_2_classification_engine()
        self.level_3_valuation_engine()
        self.level_4_protection_engine()
        
        return self.df
    
    def get_summary_statistics(self):
        """Generate summary statistics"""
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
        
        return summary


def process_uploaded_data(orders_df: pd.DataFrame, tariff_df: pd.DataFrame):
    """
    Process uploaded data files and return results
    
    Args:
        orders_df: DataFrame containing e-commerce orders
        tariff_df: DataFrame containing tariff information
    
    Returns:
        Tuple of (processed_df, summary_dict, alerts_df)
    """
    # Initialize and run pipeline
    pipeline = CustomsECommercePipeline(orders_df, tariff_df)
    processed_df = pipeline.run_pipeline()
    summary = pipeline.get_summary_statistics()
    
    # Generate alerts
    alerts_df = processed_df[
        (processed_df['revenue_risk']) | 
        (processed_df['risk_flag_code'] != 'NONE') |
        (processed_df['classification_status'] == 'NO_MATCH')
    ].copy()
    
    return processed_df, summary, alerts_df


if __name__ == "__main__":
    # Default execution with sample data
    print("Loading default data files...")
    orders_df = pd.read_csv('../input-data/ecommerce_orders.csv')
    tariff_df = pd.read_csv('../input-data/tariff.csv')
    
    processed_df, summary, alerts_df = process_uploaded_data(orders_df, tariff_df)
    
    print("\n" + "=" * 80)
    print("✅ PROCESSING COMPLETE")
    print("=" * 80)
    print(f"\nProcessed {len(processed_df):,} items")
    print(f"Generated {len(alerts_df):,} alerts")
    print(f"Total duty: {processed_df['duty_aed'].sum():,.2f} AED")
