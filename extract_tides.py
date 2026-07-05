#!/usr/bin/env python3
"""
AusTides Tide Data Extractor

Extracts high and low tide predictions for all standard Australian ports
from the AusTides application database and generates a CSV file.
"""

import sqlite3
from pathlib import Path
import pandas as pd
import sys

class AusTidesExtractor:
    def __init__(self):
        self.db_path = None
        self.conn = None
        self.cursor = None
    
    def find_database(self):
        print("\n🔍 Searching for AusTides database...")
        possible_paths = [
            Path.home() / "Library" / "Application Support" / "AusTides",
            Path.home() / "Library" / "Application Support" / "au.gov.hydro.AusTides",
            Path("/Applications/AusTides.app/Contents/Resources"),
            Path("/Applications/AusTides.app/Contents/MacOS"),
        ]
        
        db_files = []
        for base_path in possible_paths:
            if base_path.exists():
                for pattern in ["*.db", "*.sqlite", "*.sqlite3"]:
                    db_files.extend(base_path.glob(pattern))
                try:
                    for subdir in base_path.iterdir():
                        if subdir.is_dir():
                            for pattern in ["*.db", "*.sqlite", "*.sqlite3"]:
                                db_files.extend(subdir.glob(pattern))
                except:
                    pass
        
        if db_files:
            print(f"✅ Found {len(db_files)} potential database file(s):")
            for i, db_file in enumerate(db_files, 1):
                print(f"   {i}. {db_file}")
            
            if len(db_files) == 1:
                self.db_path = db_files[0]
                print(f"\n📦 Using database: {self.db_path}")
                return True
            else:
                choice = input(f"\nEnter the number of the database to use (1-{len(db_files)}): ")
                try:
                    self.db_path = db_files[int(choice) - 1]
                    print(f"\n📦 Using database: {self.db_path}")
                    return True
                except (ValueError, IndexError):
                    print("Invalid choice.")
        else:
            print("❌ No AusTides database found in standard locations.")
        
        manual_path = input("\nEnter the full path to your AusTides database file: ").strip()
        if Path(manual_path).exists():
            self.db_path = Path(manual_path)
            print(f"📦 Using database: {self.db_path}")
            return True
        else:
            print(f"❌ File not found: {manual_path}")
            return False
    
    def connect(self):
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            self.cursor = self.conn.cursor()
            print("✅ Connected to AusTides database")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            return False
    
    def get_table_names(self):
        try:
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            tables = [row[0] for row in self.cursor.fetchall()]
            return tables
        except Exception as e:
            print(f"❌ Error reading tables: {e}")
            return []
    
    def inspect_database(self):
        print("\n📋 Database Structure:")
        tables = self.get_table_names()
        print(f"Tables found: {', '.join(tables)}")
        
        for table in tables:
            try:
                self.cursor.execute(f"PRAGMA table_info({table})")
                columns = self.cursor.fetchall()
                print(f"\n  {table}:")
                for col in columns:
                    print(f"    - {col[1]} ({col[2]})")
            except Exception as e:
                print(f"    Error: {e}")
    
    def get_ports(self):
        try:
            queries = [
                "SELECT id, name FROM stations WHERE type = 'Standard'",
                "SELECT id, name FROM ports WHERE type = 'Standard'",
                "SELECT id, name FROM tideStations WHERE standard = 1",
                "SELECT id, name FROM stations",
                "SELECT id, name FROM ports",
                "SELECT * FROM stations LIMIT 1",
            ]
            
            for query in queries:
                try:
                    self.cursor.execute(query)
                    results = self.cursor.fetchall()
                    if results and len(results[0]) >= 2:
                        print(f"✅ Found ports using query: {query}")
                        return results
                except:
                    continue
            
            print("❌ Could not find ports in database")
            return []
        except Exception as e:
            print(f"❌ Error fetching ports: {e}")
            return []
    
    def get_tide_predictions(self, port_id, start_date, end_date):
        try:
            queries = [
                f"""SELECT date, time, height FROM predictions 
                   WHERE port_id = {port_id} 
                   AND date BETWEEN '{start_date}' AND '{end_date}'
                   ORDER BY date, time""",
                f"""SELECT date, time, height FROM tides 
                   WHERE station_id = {port_id} 
                   AND date BETWEEN '{start_date}' AND '{end_date}'
                   ORDER BY date, time""",
                f"""SELECT date, time, height FROM predictions 
                   WHERE id = {port_id} 
                   AND date BETWEEN '{start_date}' AND '{end_date}'
                   ORDER BY date, time""",
            ]
            
            for query in queries:
                try:
                    self.cursor.execute(query)
                    results = self.cursor.fetchall()
                    if results:
                        return results
                except:
                    continue
            
            return []
        except Exception as e:
            print(f"Error fetching tide predictions for port {port_id}: {e}")
            return []
    
    def extract_and_export(self, output_file="tides_2026_2027_2028.csv"):
        print("\n🌊 Starting tide data extraction...\n")
        
        self.inspect_database()
        
        print("\n🔍 Fetching ports...")
        ports = self.get_ports()
        
        if not ports:
            print("❌ No ports found in database. Please check database structure.")
            return False
        
        print(f"✅ Found {len(ports)} ports")
        
        start_date = "2026-01-01"
        end_date = "2028-12-31"
        
        tide_data = []
        
        for port_id, port_name in ports:
            print(f"  Processing {port_name}...", end="", flush=True)
            
            predictions = self.get_tide_predictions(port_id, start_date, end_date)
            
            date_tides = {}
            for date, time, height in predictions:
                if date not in date_tides:
                    date_tides[date] = []
                date_tides[date].append((time, height))
            
            for date in sorted(date_tides.keys()):
                tides = sorted(date_tides[date], key=lambda x: x[0])
                
                row = {
                    'port_name': port_name,
                    'port_id': port_id,
                    'date': date,
                }
                
                for i, (time, height) in enumerate(tides):
                    if i < 4:
                        tide_type = 'high' if i % 2 == 0 else 'low'
                        tide_num = (i // 2) + 1
                        row[f'{tide_type}_time_{tide_num}'] = time
                        row[f'{tide_type}_height_{tide_num}'] = height
                
                tide_data.append(row)
            
            print(" ✅")
        
        if tide_data:
            df = pd.DataFrame(tide_data)
            df = df.sort_values(['port_name', 'date']).reset_index(drop=True)
            df.to_csv(output_file, index=False)
            print(f"\n✅ Exported {len(df)} rows to {output_file}")
            print(f"\n📊 Output file: {Path(output_file).absolute()}")
            return True
        else:
            print("❌ No tide data extracted")
            return False
    
    def close(self):
        if self.conn:
            self.conn.close()
            print("\n🔐 Database connection closed")

def main():
    print("="*60)
    print("AusTides Tide Data Extractor")
    print("="*60)
    
    extractor = AusTidesExtractor()
    
    try:
        if not extractor.find_database():
            print("❌ Failed to locate database")
            return 1
        
        if not extractor.connect():
            print("❌ Failed to connect to database")
            return 1
        
        if extractor.extract_and_export():
            print("\n" + "="*60)
            print("✅ Tide data extraction completed successfully!")
            print("="*60)
            return 0
        else:
            print("\n❌ Tide data extraction failed")
            return 1
    
    except KeyboardInterrupt:
        print("\n⚠️  Extraction interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        extractor.close()

if __name__ == "__main__":
    sys.exit(main())
