"""
PostgreSQL Data Loader for Ahmedabad Environmental Data
Loads cleaned CSV files into PostgreSQL with proper schema and storage
"""

import psycopg2
from psycopg2 import sql, Error
import pandas as pd
import os
from datetime import datetime

# Database connection parameters (matches docker-compose.yml)
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'urban_admin',
    'password': 'ahmedabad123',
    'database': 'ahmedabad_urban'
}

# CSV files to load
CLEANED_FILES = {
    'areas_lst': 'Ahmedabad_Areas_LST_CLEANED.csv',
    'areas_ndvi': 'Ahmedabad_Areas_NDVI_CLEANED.csv',
    'areas_no2': 'Ahmedabad_Areas_NO2_CLEANED.csv'
}

# Column mappings (CSV column -> value column name)
COLUMN_MAPPING = {
    'areas_lst': 'LST',
    'areas_ndvi': 'NDVI',
    'areas_no2': 'NO2'
}


def create_connection():
    """Create PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✓ Connected to PostgreSQL successfully")
        return conn
    except Error as e:
        print(f"✗ Database connection failed: {e}")
        raise


def create_tables(conn):
    """Create PostgreSQL tables with proper schema"""
    cursor = conn.cursor()
    
    # SQL for creating tables with NUMERIC(15,10) precision
    create_lst_table = """
    CREATE TABLE IF NOT EXISTS areas_lst (
        id SERIAL PRIMARY KEY,
        area VARCHAR(100) NOT NULL,
        date DATE NOT NULL,
        lst NUMERIC(15, 10) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT unique_lst_area_date UNIQUE(area, date),
        CONSTRAINT positive_lst CHECK (lst >= 0)
    );
    """
    
    create_ndvi_table = """
    CREATE TABLE IF NOT EXISTS areas_ndvi (
        id SERIAL PRIMARY KEY,
        area VARCHAR(100) NOT NULL,
        date DATE NOT NULL,
        ndvi NUMERIC(15, 10) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT unique_ndvi_area_date UNIQUE(area, date),
        CONSTRAINT ndvi_range CHECK (ndvi >= -1 AND ndvi <= 1)
    );
    """
    
    create_no2_table = """
    CREATE TABLE IF NOT EXISTS areas_no2 (
        id SERIAL PRIMARY KEY,
        area VARCHAR(100) NOT NULL,
        date DATE NOT NULL,
        no2 NUMERIC(15, 10) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT unique_no2_area_date UNIQUE(area, date),
        CONSTRAINT positive_no2 CHECK (no2 >= 0)
    );
    """
    
    # Create indexes for better query performance
    create_indexes = """
    CREATE INDEX IF NOT EXISTS idx_lst_area ON areas_lst(area);
    CREATE INDEX IF NOT EXISTS idx_lst_date ON areas_lst(date);
    CREATE INDEX IF NOT EXISTS idx_lst_area_date ON areas_lst(area, date);
    
    CREATE INDEX IF NOT EXISTS idx_ndvi_area ON areas_ndvi(area);
    CREATE INDEX IF NOT EXISTS idx_ndvi_date ON areas_ndvi(date);
    CREATE INDEX IF NOT EXISTS idx_ndvi_area_date ON areas_ndvi(area, date);
    
    CREATE INDEX IF NOT EXISTS idx_no2_area ON areas_no2(area);
    CREATE INDEX IF NOT EXISTS idx_no2_date ON areas_no2(date);
    CREATE INDEX IF NOT EXISTS idx_no2_area_date ON areas_no2(area, date);
    """
    
    try:
        # Create tables
        cursor.execute(create_lst_table)
        print("✓ Created/verified areas_lst table")
        
        cursor.execute(create_ndvi_table)
        print("✓ Created/verified areas_ndvi table")
        
        cursor.execute(create_no2_table)
        print("✓ Created/verified areas_no2 table")
        
        # Create indexes
        cursor.execute(create_indexes)
        print("✓ Created/verified indexes for all tables")
        
        conn.commit()
        print("\n✓ All tables created successfully with indexes\n")
        
    except Error as e:
        print(f"✗ Table creation failed: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()


def load_csv_to_table(conn, table_name, csv_file, value_column):
    """Load CSV data into PostgreSQL table"""
    cursor = conn.cursor()
    
    csv_path = os.path.join(os.path.dirname(__file__), csv_file)
    
    if not os.path.exists(csv_path):
        print(f"✗ CSV file not found: {csv_path}")
        return False
    
    try:
        # Read CSV file
        df = pd.read_csv(csv_path)
        
        # Validate required columns
        if not all(col in df.columns for col in [value_column, 'area', 'date']):
            print(f"✗ CSV columns mismatch. Found: {df.columns.tolist()}")
            return False
        
        # Convert date to proper format
        df['date'] = pd.to_datetime(df['date']).dt.date
        
        print(f"\n📊 Loading {csv_file}...")
        print(f"   Records to insert: {len(df):,}")
        
        # Insert data using efficient batch insert
        rows_inserted = 0
        batch_size = 1000
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            
            # Prepare INSERT statement  
            insert_sql = sql.SQL("""
                INSERT INTO {} ({}, area, date)
                VALUES (%s, %s, %s)
                ON CONFLICT (area, date) DO NOTHING
            """).format(
                sql.Identifier(table_name),
                sql.Identifier(value_column.lower())
            )
            
            # Execute batch insert - order: value, area, date
            data_tuples = [tuple(row) for row in batch[[value_column, 'area', 'date']].values]
            
            try:
                cursor.executemany(insert_sql, data_tuples)
                rows_inserted += cursor.rowcount
            except Error as e:
                print(f"✗ Batch insert failed: {e}")
                conn.rollback()
                return False
            
            # Progress indicator
            if (i // batch_size + 1) % 5 == 0:
                print(f"   ... {i + batch_size:,} records processed")
        
        conn.commit()
        print(f"   ✓ {rows_inserted:,} records inserted into {table_name}")
        return True
        
    except Error as e:
        print(f"✗ Data loading failed for {csv_file}: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()


def verify_data(conn):
    """Verify data integrity and display statistics"""
    cursor = conn.cursor()
    
    print("\n📈 Data Verification & Statistics:\n")
    
    tables_info = {
        'areas_lst': ('lst', 'Land Surface Temperature (°C)'),
        'areas_ndvi': ('ndvi', 'Normalized Vegetation Index'),
        'areas_no2': ('no2', 'Nitrogen Dioxide (ppb)')
    }
    
    for table_name, (column_name, description) in tables_info.items():
        try:
            # Get basic stats
            query = sql.SQL("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT area) as unique_areas,
                    COUNT(DISTINCT date) as unique_dates,
                    MIN({}) as min_value,
                    MAX({}) as max_value,
                    ROUND(AVG({})::numeric, 10) as avg_value,
                    ROUND(STDDEV({})::numeric, 10) as std_value
                FROM {}
            """).format(
                sql.Identifier(column_name),
                sql.Identifier(column_name),
                sql.Identifier(column_name),
                sql.Identifier(column_name),
                sql.Identifier(table_name)
            )
            
            cursor.execute(query)
            result = cursor.fetchone()
            
            if result:
                total, areas, dates, min_val, max_val, avg_val, std_val = result
                print(f"📊 {table_name.upper()}: {description}")
                print(f"   Total Records: {total:,}")
                print(f"   Unique Areas: {areas}")
                print(f"   Unique Dates: {dates}")
                print(f"   Range: {min_val} to {max_val}")
                print(f"   Average: {avg_val}")
                print(f"   Std Dev: {std_val}")
                print()
        
        except Error as e:
            print(f"✗ Verification failed for {table_name}: {e}")
    
    cursor.close()


def main():
    """Main execution function"""
    print("=" * 70)
    print("PostgreSQL Data Loader for Ahmedabad Environmental Datasets")
    print("=" * 70)
    print()
    
    conn = None
    try:
        # Connect to database
        conn = create_connection()
        
        # Create tables with schema
        print("\n📋 Creating database tables...\n")
        create_tables(conn)
        
        # Load data from CSV files
        print("📥 Loading data from CSV files...\n")
        load_results = []
        
        for table_name, csv_file in CLEANED_FILES.items():
            value_column = COLUMN_MAPPING[table_name]
            success = load_csv_to_table(conn, table_name, csv_file, value_column)
            load_results.append((csv_file, success))
        
        # Display summary
        print("\n" + "=" * 70)
        print("LOADING SUMMARY:")
        print("=" * 70)
        for csv_file, success in load_results:
            status = "✓ SUCCESS" if success else "✗ FAILED"
            print(f"{status}: {csv_file}")
        
        # Verify data
        verify_data(conn)
        
        print("=" * 70)
        print("✓ Data loading complete!")
        print("=" * 70)
        print("\n💡 Next steps:")
        print("   • Access PostgreSQL via PgAdmin: http://localhost:5050")
        print("   • Run OLAP queries for city planning analysis")
        print("   • Generate municipality reports from cleaned data")
        print()
        
    except Error as e:
        print(f"\n✗ Process failed: {e}")
    
    finally:
        if conn:
            conn.close()
            print("✓ Database connection closed")


if __name__ == "__main__":
    main()
