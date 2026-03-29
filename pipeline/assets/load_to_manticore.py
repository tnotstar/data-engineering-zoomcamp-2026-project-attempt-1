"""@bruin
name: load_to_manticore
depends:
  - ingest_eva
image: python:3.11-slim
materialization:
  type: none
@bruin"""

import pandas as pd
import requests
import json
import os
import time

def materialize():
    print("Loading extracted CSV data into Manticore Search DWH...")
    csv_path = '/data/eva_filtered.csv'
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Missing {csv_path}. Did the ingestion step run?")
        
    df = pd.read_csv(csv_path)
    
    MANTICORE_URL = os.getenv("MANTICORE_URL", "http://manticore:9308")
    
    bulk_data = []
    for i, row in df.iterrows():
        # Using NDJSON format for Manticore Bulk API
        req_line = {
            "insert": {
                "index": "eva_variants",
                "id": i + 1,
                "doc": {
                    "variant_id": row["variant_id"],
                    "pos": int(row["pos"]),
                    "ref": row["ref"],
                    "alt": row["alt"],
                    "eur_freq": float(row["eur_freq"]),
                    "afr_freq": float(row["afr_freq"]),
                    "amr_freq": float(row["amr_freq"])
                }
            }
        }
        bulk_data.append(json.dumps(req_line))
        
    body = '\n'.join(bulk_data) + '\n'
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            headers = {'Content-Type': 'application/x-ndjson'}
            resp = requests.post(f"{MANTICORE_URL}/bulk", data=body, headers=headers)
            if resp.status_code == 200:
                print(f"Successfully bulk-loaded {len(df)} records into Manticore index 'eva_variants'.")
                break
            else:
                print(f"Error {resp.status_code} from Manticore: {resp.text}")
        except requests.exceptions.ConnectionError:
            print(f"Connection failed (Attempt {attempt+1}/{max_retries}). Manticore unreachable at {MANTICORE_URL}. Retrying...")
            time.sleep(2)
            
    print("Loading Task Complete.")
