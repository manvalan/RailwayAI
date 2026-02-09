#!/usr/bin/env python3
"""
Download European Railway GTFS Data

Downloads real timetable data from major European operators:
- Trenitalia (Italy)
- SNCF (France)
- DB (Germany)
- Renfe (Spain)
- NS (Netherlands)
"""

import requests
import zipfile
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GTFSDownloader:
    """Download and extract GTFS feeds"""
    
    FEEDS = {
        "trenitalia": {
            "url": "https://github.com/transitland/gtfs-archives-not-hosted-elsewhere/raw/master/trenitalia.zip",
            "name": "Trenitalia (Italy)"
        },
        "sncf": {
            "url": "https://eu.ftp.opendatasoft.com/sncf/gtfs/export-ter-gtfs-last.zip",
            "name": "SNCF TER (France)"
        },
        "renfe": {
            "url": "https://data.renfe.com/dataset/horarios-de-alta-velocidad-larga-distancia-y-media-distancia",
            "name": "Renfe (Spain)"
        }
    }
    
    def __init__(self, output_dir: str = "data/gtfs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def download_feed(self, feed_id: str) -> bool:
        """Download a single GTFS feed"""
        if feed_id not in self.FEEDS:
            logger.error(f"Unknown feed: {feed_id}")
            return False
        
        feed = self.FEEDS[feed_id]
        logger.info(f"📥 Downloading {feed['name']}...")
        
        try:
            # Download
            response = requests.get(feed["url"], timeout=300, stream=True)
            response.raise_for_status()
            
            # Save zip
            zip_path = self.output_dir / f"{feed_id}.zip"
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Extract
            extract_dir = self.output_dir / feed_id
            extract_dir.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Clean up zip
            zip_path.unlink()
            
            logger.info(f"✅ {feed['name']} downloaded to {extract_dir}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to download {feed['name']}: {e}")
            return False
    
    def download_all(self):
        """Download all available feeds"""
        logger.info(f"🌍 Downloading {len(self.FEEDS)} European GTFS feeds...")
        
        success = 0
        for feed_id in self.FEEDS:
            if self.download_feed(feed_id):
                success += 1
        
        logger.info(f"\n✅ Downloaded {success}/{len(self.FEEDS)} feeds")
        logger.info(f"📁 Data location: {self.output_dir}")
        
        return success > 0

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--feed", type=str, help="Specific feed to download (trenitalia, sncf, renfe)")
    parser.add_argument("--output", type=str, default="data/gtfs", help="Output directory")
    args = parser.parse_args()
    
    downloader = GTFSDownloader(output_dir=args.output)
    
    if args.feed:
        downloader.download_feed(args.feed)
    else:
        downloader.download_all()
