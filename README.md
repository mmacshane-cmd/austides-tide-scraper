# AusTides Tide Data Scraper

Extracts high and low tide predictions for all standard Australian ports (including PNG and Solomon Islands) from the AusTides application database and generates a comprehensive CSV file.

## Features

- **Extracts data directly from AusTides database** (no scraping, guaranteed accuracy)
- **Covers all standard ports** across Australia, Papua New Guinea, and Solomon Islands
- **Generates predictions for 2026, 2027, and 2028**
- **Single CSV output** with high/low tide times and heights for each day
- **Auto-detects AusTides installation** on macOS
- **BoM-level accuracy** (reads directly from official source)

## Requirements

- macOS 10.15+
- Python 3.8+
- AusTides application installed locally
- `pandas` library

## Installation

1. Clone this repository:
```bash
git clone https://github.com/mmacshane-cmd/austides-tide-scraper.git
cd austides-tide-scraper
