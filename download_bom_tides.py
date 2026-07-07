#!/usr/bin/env python3
"""
BOM Tide PDF Scraper & Extractor

Downloads tide prediction PDFs from Bureau of Meteorology for all Australian
standard ports and extracts high/low tide data into a CSV file.

Supports: 2026, 2027 (years available from BOM)
"""

import requests
from pathlib import Path
import pandas as pd
import sys
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import PyPDF2
import os
from datetime import datetime

class BOMTideScraper:
    def __init__(self):
        self.base_url = "https://www.bom.gov.au/oceanography/projects/ntc"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.pdfs_dir = Path("tide_pdfs")
        self.pdfs_dir.mkdir(exist_ok=True)
        self.tide_data = []
    
    def find_tide_tables(self):
        """Discover all available BOM tide table PDFs"""
        print("\n🔍 Discovering BOM tide table PDFs...\n")
        
        # BOM states and territories with tide data
        regions = {
            'nsw': ('New South Wales', 'https://www.bom.gov.au/oceanography/projects/ntc/nsw_tide_tables.shtml'),
            'vic': ('Victoria', 'https://www.bom.gov.au/oceanography/projects/ntc/vic_tide_tables.shtml'),
            'qld': ('Queensland', 'https://www.bom.gov.au/oceanography/projects/ntc/qld_tide_tables.shtml'),
            'sa': ('South Australia', 'https://www.bom.gov.au/oceanography/projects/ntc/sa_tide_tables.shtml'),
            'wa': ('Western Australia', 'https://www.bom.gov.au/oceanography/projects/ntc/wa_tide_tables.shtml'),
            'tas': ('Tasmania', 'https://www.bom.gov.au/oceanography/projects/ntc/tas_tide_tables.shtml'),
            'nt': ('Northern Territory', 'https://www.bom.gov.au/oceanography/projects/ntc/nt_tide_tables.shtml'),
        }
        
        pdf_links = {}
        
        for region_code, (region_name, url) in regions.items():
            print(f"📍 Scanning {region_name}...", end=" ", flush=True)
            try:
                response = self.session.get(url, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all PDF links
                pdfs = soup.find_all('a', href=re.compile(r'\.pdf$', re.IGNORECASE))
                
                region_pdfs = []
                for pdf_link in pdfs:
                    href = pdf_link.get('href')
                    text = pdf_link.get_text(strip=True)
                    
                    # Filter for 2026 and 2027 tide table PDFs
                    if ('2026' in href or '2026' in text or '2027' in href or '2027' in text) and \
                       ('tide' in text.lower() or 'tide' in href.lower()):
                        full_url = urljoin(url, href)
                        region_pdfs.append({
                            'name': text,
                            'url': full_url,
                            'region': region_name
                        })
                
                if region_pdfs:
                    pdf_links[region_code] = region_pdfs
                    print(f"✅ Found {len(region_pdfs)}")
                else:
                    print("⚠️  No PDFs found")
            
            except Exception as e:
                print(f"❌ Error: {e}")
        
        return pdf_links
    
    def download_pdfs(self, pdf_links):
        """Download all discovered PDFs"""
        print("\n📥 Downloading PDFs...\n")
        
        total_pdfs = sum(len(pdfs) for pdfs in pdf_links.values())
        downloaded = 0
        
        for region, pdfs in pdf_links.items():
            for pdf_info in pdfs:
                filename = self.pdfs_dir / f"{region}_{pdf_info['name']}"
                
                # Sanitize filename
                filename = filename.name.replace('/', '_').replace('\\', '_')
                filename = self.pdfs_dir / filename
                
                if filename.exists():
                    print(f"  ✓ Already have: {filename.name}")
                    downloaded += 1
                    continue
                
                try:
                    print(f"  Downloading: {pdf_info['name']}...", end=" ", flush=True)
                    response = self.session.get(pdf_info['url'], timeout=30)
                    
                    if response.status_code == 200:
                        with open(filename, 'wb') as f:
                            f.write(response.content)
                        print(f"✅ ({len(response.content) / 1024:.1f}KB)")
                        downloaded += 1
                    else:
                        print(f"❌ HTTP {response.status_code}")
                
                except Exception as e:
                    print(f"❌ Error: {e}")
        
        print(f"\n✅ Downloaded {downloaded}/{total_pdfs} PDFs")
        return list(self.pdfs_dir.glob("*.pdf"))
    
    def extract_tides_from_pdf(self, pdf_path):
        """Extract tide data from a PDF file"""
        tides = []
        
        try:
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text = ""
                
                for page in pdf_reader.pages:
                    text += page.extract_text()
            
            # Parse tide table data (pattern varies by PDF)
            # Looking for patterns like:
            # Date | Time | Height | Type
            # 01   | 0143 | 0.82m  | Low
            
            lines = text.split('\n')
            current_date = None
            port_name = None
            year = None
            
            # Extract year and port from filename or content
            filename = pdf_path.stem
            year_match = re.search(r'(202[0-9])', filename)
            year = int(year_match.group(1)) if year_match else 2026
            
            # Extract port name from filename
            port_name = filename.replace('_', ' ').strip()
            
            for line in lines:
                # Try to match tide data rows
                # Format: DD HH:MM 0.XX m (High/Low)
                tide_match = re.search(
                    r'(\d{1,2})\s+(\d{2}):(\d{2})\s+([\d.]+)\s*m\s*(High|Low|high|low)',
                    line
                )
                
                if tide_match:
                    day, hour, minute, height, tide_type = tide_match.groups()
                    
                    # Build date (we need to infer month/year context)
                    try:
                        date_str = f"{year}-01-{day:0>2}"  # Will need refinement per PDF
                        time_str = f"{hour}:{minute}"
                        
                        tides.append({
                            'date': date_str,
                            'time': time_str,
                            'height': float(height),
                            'type': tide_type.capitalize(),
                            'port': port_name,
                            'year': year
                        })
                    except:
                        pass
            
        except Exception as e:
            print(f"❌ Error extracting from {pdf_path}: {e}")
        
        return tides
    
    def extract_all_tides(self, pdf_files):
        """Extract tide data from all PDFs"""
        print("\n📊 Extracting tide data from PDFs...\n")
        
        total_tides = 0
        
        for pdf_path in pdf_files:
            print(f"  Processing {pdf_path.name}...", end=" ", flush=True)
            
            tides = self.extract_tides_from_pdf(pdf_path)
            self.tide_data.extend(tides)
            total_tides += len(tides)
            
            if tides:
                print(f"✅ ({len(tides)} records)")
            else:
                print("⚠️  No data extracted")
        
        print(f"\n✅ Total tide records extracted: {total_tides}")
        return self.tide_data
    
    def export_to_csv(self, output_file="tides_bom_2026_2027.csv"):
        """Export extracted tide data to CSV"""
        if not self.tide_data:
            print("❌ No tide data to export")
            return False
        
        try:
            df = pd.DataFrame(self.tide_data)
            
            # Sort and clean up
            df = df.sort_values(['port', 'date', 'time']).reset_index(drop=True)
            
            # Remove duplicates
            df = df.drop_duplicates()
            
            df.to_csv(output_file, index=False)
            
            print(f"\n✅ Exported {len(df)} records to {output_file}")
            print(f"📊 Output file: {Path(output_file).absolute()}")
            print(f"\n📈 Summary:")
            print(f"   - Total records: {len(df)}")
            print(f"   - Ports: {df['port'].nunique()}")
            print(f"   - Years: {sorted(df['year'].unique())}")
            print(f"   - Date range: {df['date'].min()} to {df['date'].max()}")
            
            return True
        
        except Exception as e:
            print(f"❌ Error exporting CSV: {e}")
            return False
    
    def run(self):
        """Main execution"""
        print("="*60)
        print("BOM Tide PDF Downloader & Extractor")
        print("="*60)
        
        try:
            # Find PDF links
            pdf_links = self.find_tide_tables()
            
            if not pdf_links:
                print("\n❌ No tide table PDFs found on BOM website")
                return 1
            
            total_pdfs = sum(len(pdfs) for pdfs in pdf_links.values())
            print(f"\n✅ Found {total_pdfs} PDF(s) to download")
            
            # Download PDFs
            pdf_files = self.download_pdfs(pdf_links)
            
            if not pdf_files:
                print("❌ No PDFs downloaded")
                return 1
            
            # Extract tide data
            self.extract_all_tides(pdf_files)
            
            # Export to CSV
            if self.export_to_csv():
                print("\n" + "="*60)
                print("✅ Tide data extraction completed successfully!")
                print("="*60)
                return 0
            else:
                print("\n❌ Failed to export CSV")
                return 1
        
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user")
            return 1
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return 1

def main():
    scraper = BOMTideScraper()
    return scraper.run()

if __name__ == "__main__":
    sys.exit(main())
