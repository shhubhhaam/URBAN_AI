"""
Load Unified Daily & Monthly Data into PostgreSQL Database
"""

import psycopg2
from psycopg2 import sql, Error
import pandas as pd
import numpy as np
import os

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'urban_admin',
    'password': 'ahmedabad123',
    'database': 'ahmedabad_urban'
}

def create_connection():
    """Create PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✓ Connected to PostgreSQL")
        return conn
    except Error as e:
        print(f"✗ Connection failed: {e}")
        raise


def create_unified_tables(conn):
    """Create tables for unified data"""
    cursor = conn.cursor()
    
    # Daily unified data table
    create_daily_table = """
    DROP TABLE IF EXISTS unified_daily_data;
    CREATE TABLE unified_daily_data (
        id SERIAL PRIMARY KEY,
        area VARCHAR(100) NOT NULL,
        date DATE NOT NULL,
        lst NUMERIC(15, 10) NOT NULL,
        ndvi NUMERIC(15, 10) NOT NULL,
        no2 NUMERIC(15, 10) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT unique_daily UNIQUE(area, date)
    );
    """
    
    # Monthly aggregated data table
    create_monthly_table = """
    DROP TABLE IF EXISTS unified_monthly_data;
    CREATE TABLE unified_monthly_data (
        id SERIAL PRIMARY KEY,
        area VARCHAR(100) NOT NULL,
        month DATE NOT NULL,
        lst_avg NUMERIC(15, 10),
        lst_max NUMERIC(15, 10),
        lst_min NUMERIC(15, 10),
        lst_volatility NUMERIC(15, 10),
        ndvi_avg NUMERIC(15, 10),
        ndvi_peak NUMERIC(15, 10),
        ndvi_volatility NUMERIC(15, 10),
        no2_avg NUMERIC(15, 10),
        no2_peak NUMERIC(15, 10),
        no2_volatility NUMERIC(15, 10),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT unique_monthly UNIQUE(area, month)
    );
    """
    
    # Create indexes
    create_indexes = """
    CREATE INDEX idx_daily_area ON unified_daily_data(area);
    CREATE INDEX idx_daily_date ON unified_daily_data(date);
    CREATE INDEX idx_daily_area_date ON unified_daily_data(area, date);
    
    CREATE INDEX idx_monthly_area ON unified_monthly_data(area);
    CREATE INDEX idx_monthly_month ON unified_monthly_data(month);
    """
    
    try:
        cursor.execute(create_daily_table)
        print("✓ Created unified_daily_data table")
        
        cursor.execute(create_monthly_table)
        print("✓ Created unified_monthly_data table")
        
        cursor.execute(create_indexes)
        print("✓ Created indexes")
        
        conn.commit()
    except Error as e:
        print(f"✗ Table creation failed: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()


def load_daily_data(conn, csv_file):
    """Load daily unified data into PostgreSQL"""
    cursor = conn.cursor()
    
    try:
        df = pd.read_csv(csv_file)
        df['date'] = pd.to_datetime(df['date']).dt.date
        
        print(f"\n📊 Loading daily data: {len(df):,} records")
        
        rows_inserted = 0
        batch_size = 5000
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            
            insert_sql = """
                INSERT INTO unified_daily_data (area, date, lst, ndvi, no2)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (area, date) DO NOTHING
            """
            
            data_tuples = [tuple(row) for row in batch[['area', 'date', 'LST', 'NDVI', 'NO2']].values]
            
            try:
                cursor.executemany(insert_sql, data_tuples)
                rows_inserted += cursor.rowcount
            except Error as e:
                print(f"✗ Batch insert failed: {e}")
                conn.rollback()
                return False
            
            if (i // batch_size + 1) % 5 == 0:
                print(f"   ... {i + batch_size:,} processed")
        
        conn.commit()
        print(f"   ✓ {rows_inserted:,} daily records inserted")
        return True
        
    except Error as e:
        print(f"✗ Daily data loading failed: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()


def load_monthly_data(conn, csv_file):
    """Load monthly aggregated data into PostgreSQL"""
    cursor = conn.cursor()
    
    try:
        df = pd.read_csv(csv_file)
        df['month'] = pd.to_datetime(df['month']).dt.date
        
        print(f"\n📊 Loading monthly data: {len(df):,} records")
        
        rows_inserted = 0
        batch_size = 1000
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            
            insert_sql = """
                INSERT INTO unified_monthly_data 
                (area, month, lst_avg, lst_max, lst_min, lst_volatility,
                 ndvi_avg, ndvi_peak, ndvi_volatility, no2_avg, no2_peak, no2_volatility)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (area, month) DO NOTHING
            """
            
            columns = ['area', 'month', 'lst_avg', 'lst_max', 'lst_min', 'lst_volatility',
                      'ndvi_avg', 'ndvi_peak', 'ndvi_volatility', 'no2_avg', 'no2_peak', 'no2_volatility']
            
            # Convert rows to tuples with NaN → None conversion
            data_tuples = []
            for idx, row in batch[columns].iterrows():
                row_tuple = tuple(None if pd.isna(val) else val for val in row)
                data_tuples.append(row_tuple)
            
            try:
                cursor.executemany(insert_sql, data_tuples)
                rows_inserted += cursor.rowcount
            except Error as e:
                print(f"✗ Batch insert failed: {e}")
                conn.rollback()
                return False
            
            if (i // batch_size + 1) % 5 == 0:
                print(f"   ... {i + batch_size:,} processed")
        
        conn.commit()
        print(f"   ✓ {rows_inserted:,} monthly records inserted")
        return True
        
    except Error as e:
        print(f"✗ Monthly data loading failed: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()


def verify_data(conn):
    """Verify loaded data"""
    cursor = conn.cursor()
    
    print("\n" + "=" * 80)
    print("DATA VERIFICATION")
    print("=" * 80 + "\n")
    
    try:
        # Daily stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT area) as areas,
                MIN(date) as min_date,
                MAX(date) as max_date
            FROM unified_daily_data
        """)
        total, areas, min_date, max_date = cursor.fetchone()
        print(f"✓ Daily Data:")
        print(f"   Total records: {total:,}")
        print(f"   Unique areas: {areas}")
        print(f"   Date range: {min_date} to {max_date}")
        
        # Monthly stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT area) as areas,
                MIN(month) as min_month,
                MAX(month) as max_month
            FROM unified_monthly_data
        """)
        total, areas, min_month, max_month = cursor.fetchone()
        print(f"\n✓ Monthly Data:")
        print(f"   Total records: {total:,}")
        print(f"   Unique areas: {areas}")
        print(f"   Month range: {min_month} to {max_month}")
        
    except Error as e:
        print(f"✗ Verification failed: {e}")
    finally:
        cursor.close()


def main():
    print("\n" + "=" * 80)
    print("LOADING UNIFIED DATA TO PostgreSQL")
    print("=" * 80 + "\n")
    
    conn = None
    try:
        conn = create_connection()
        
        print("\n📋 Creating tables...")
        create_unified_tables(conn)
        
        print("\n📥 Loading data from CSV files...")
        
        daily_success = load_daily_data(conn, 'Ahmedabad_Unified_Daily_Data.csv')
        monthly_success = load_monthly_data(conn, 'Ahmedabad_Monthly_Aggregated.csv')
        
        if daily_success and monthly_success:
            verify_data(conn)
            print("\n" + "=" * 80)
            print("✓ All data loaded successfully to PostgreSQL!")
            print("=" * 80 + "\n")
        else:
            print("\n✗ Some data loading failed")
        
    except Error as e:
        print(f"\n✗ Process failed: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed")


if __name__ == "__main__":
    main()
