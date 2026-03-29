"""@bruin
name: main.load_to_manticore
depends:
  - main.ingest_eva
@bruin"""

import pandas as pd
import requests
import json
import os
import time

def materialize():
    print("Loading extracted TSV data into Manticore Search DWH...")
    tsv_path = '/data/variantes_poblaciones.tsv'
    
    if not os.path.exists(tsv_path):
        raise FileNotFoundError(f"Missing {tsv_path}. Did the ingestion step run?")
        
    df = pd.read_csv(tsv_path, sep='\t')
    
    # Missing values should be converted to 0.0 or handled
    df = df.replace("NULL", 0.0)
    df = df.fillna(0.0)
    
    # Mapping ALFA project columns to expected db schema:
    # SAMN10492695 -> afr_freq
    # SAMN10492698 -> eur_freq
    # SAMN10492696 -> amr_freq
    
    MANTICORE_URL = os.getenv("MANTICORE_URL", "http://search-engine:9308")
    
    bulk_data = []
    # Drop rows without an ID or where ID is .
    df = df[df['variant_id'] != '.']
    
    # reset index for Manticore IDs
    df = df.reset_index(drop=True)
    
    for i, row in df.iterrows():
        # Using NDJSON format for Manticore Bulk API
        req_line = {
            "replace": {
                "index": "eva_variants",
                "id": i + 1,
                "doc": {
                    "variant_id": str(row["variant_id"]),
                    "pos": int(row["pos"]),
                    "ref": str(row["ref"]),
                    "alt": str(row["alt"]),
                    "eur_freq": float(row.get("SAMN10492698", 0.0)),
                    "afr_freq": float(row.get("SAMN10492695", 0.0)),
                    "amr_freq": float(row.get("SAMN10492696", 0.0))
                }
            }
        }
        bulk_data.append(json.dumps(req_line))
        
    # Chunking to avoid memory bombs / timeouts with Manticore HTTP
    chunk_size = 5000
    max_retries = 3
    
    headers = {'Content-Type': 'application/x-ndjson'}
    
    for chunk_start in range(0, len(bulk_data), chunk_size):
        chunk = bulk_data[chunk_start:chunk_start+chunk_size]
        body = '\n'.join(chunk) + '\n'
        
        for attempt in range(max_retries):
            try:
                resp = requests.post(f"{MANTICORE_URL}/bulk", data=body, headers=headers)
                if resp.status_code == 200:
                    print(f"Successfully bulk-loaded variants [{chunk_start}:{chunk_start+len(chunk)}] into Manticore.")
                    break
                else:
                    print(f"Error {resp.status_code} from Manticore: {resp.text}")
                    if attempt == max_retries - 1:
                        raise RuntimeError("Manticore bulk insert failed.")
            except requests.exceptions.ConnectionError:
                print(f"Connection failed (Attempt {attempt+1}/{max_retries}). Retrying in 2s...")
                time.sleep(2)
                if attempt == max_retries - 1:
                    raise
            
    print("Loading Task Complete.")
    return pd.DataFrame([{"status": "load_complete"}])
