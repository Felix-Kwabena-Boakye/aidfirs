import os
import sys
import json
import pandas as pd
from pymongo import MongoClient

# Ensure backend directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mongo_connection import get_db, MONGO_AVAILABLE

# Compute backend root so the CSV path is always absolute and correct.
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_FINAL_COLS = ["size_bytes", "file_type", "entropy", "partition", "ai_prediction"]

def export_dataset(output_path=None):
    """
    Export a training dataset and return its provenance.

    Provenance fields returned: data_source ('real' | 'mixed' | 'synthetic'),
    total_rows, real_rows, synthetic_rows.

    Rules for truthfulness:
    - Real rows are only included when they carry a genuine ai_prediction label.
      Labels are never guessed from entropy.
    - If no real labelled rows exist, the dataset is synthetic-only and training
      must be refused by the caller (train_and_save_model).
    - Provenance is also written to a sidecar JSON so training always knows the
      dataset source, even when invoked standalone.
    """
    if output_path is None:
        output_path = os.path.join(_BACKEND_ROOT, "forensics_training_data.csv")
    print("Initializing Forensic Dataset Export Pipeline...")

    real_rows = 0
    synthetic_rows = 0
    data_source = None

    db = get_db()
    if db is None:
        print("MongoDB is not available. Exporting synthesized forensic features (training will refuse this)...")
        dataset = synthesize_forensic_data(100)
        synthetic_rows = len(dataset)
        data_source = "synthetic"
    else:
        try:
            evidence = list(db.evidence.find())
            analysis = list(db.analysis_results.find())
            
            print(f"Retrieved {len(evidence)} evidence documents and {len(analysis)} analysis results.")
            
            clean_data = []
            if len(evidence) > 0 and len(analysis) > 0:
                evidence_df = pd.DataFrame(evidence)
                analysis_df = pd.DataFrame(analysis)
                
                # Align key names: right_on can be file_id or evidence_id
                left_on = "_id"
                right_on = "evidence_id" if "evidence_id" in analysis_df.columns else "file_id"
                
                # Make sure the IDs are strings consistently
                evidence_df["_id"] = evidence_df["_id"].apply(str)
                if right_on in analysis_df.columns:
                    analysis_df[right_on] = analysis_df[right_on].apply(str)
                else:
                    analysis_df[right_on] = "" # fallback empty
                    
                merged_df = evidence_df.merge(analysis_df, left_on=left_on, right_on=right_on)
                
                for _, row in merged_df.iterrows():
                    # size_bytes
                    size = row.get("file_size", row.get("size_bytes", 1024))
                    if pd.isna(size) or size is None:
                        size = 1024
                        
                    # file_type
                    ftype = row.get("evidence_type", row.get("file_type", "file"))
                    if pd.isna(ftype) or ftype is None:
                        ftype = "file"
                        
                    # entropy
                    entropy = None
                    if "metadata" in row and isinstance(row["metadata"], dict):
                        entropy = row["metadata"].get("entropy")
                    if entropy is None or pd.isna(entropy):
                        entropy = 4.5
                        
                    # partition
                    partition = None
                    if "metadata" in row and isinstance(row["metadata"], dict):
                        partition = row["metadata"].get("partition")
                    if partition is None or pd.isna(partition):
                        partition = "NTFS"
                        
                    # ai_prediction / recoverable target — only a genuine label counts.
                    ai_pred = row.get("ai_prediction")
                    if ai_pred is None or pd.isna(ai_pred):
                        findings = row.get("findings")
                        if isinstance(findings, dict):
                            ai_pred = findings.get("ai_prediction")
                            
                    if ai_pred is None or pd.isna(ai_pred):
                        # No genuine recoverability label: skip the row rather than
                        # fabricate a target from entropy.
                        continue
                        
                    clean_data.append({
                        "size_bytes": int(size),
                        "file_type": str(ftype),
                        "entropy": float(entropy),
                        "partition": str(partition),
                        "ai_prediction": int(ai_pred)
                    })
                real_rows = len(clean_data)
                dataset = pd.DataFrame(clean_data)
            else:
                dataset = pd.DataFrame(columns=_FINAL_COLS)

            if len(dataset) == 0:
                print("No real labelled evidence rows found. Exporting synthesized dataset (training will refuse this)...")
                dataset = synthesize_forensic_data(100)
                synthetic_rows = len(dataset)
                data_source = "synthetic"
            elif len(dataset) < 20:
                print(f"Dataset has only {len(dataset)} real labelled rows. Supplementing with synthesized forensic samples...")
                synth_df = synthesize_forensic_data(100 - len(dataset))
                synthetic_rows = len(synth_df)
                dataset = pd.concat([dataset, synth_df], ignore_index=True)
                data_source = "mixed"
            else:
                data_source = "real"
        except Exception as e:
            print(f"Error querying MongoDB: {e}. Exporting synthesized dataset (training will refuse this).")
            dataset = synthesize_forensic_data(100)
            synthetic_rows = len(dataset)
            data_source = "synthetic"
    
    dataset[_FINAL_COLS].to_csv(output_path, index=False)
    total_rows = len(dataset)
    print(f"Successfully exported {total_rows} samples to {output_path} (source: {data_source})")

    provenance = {
        "path": output_path,
        "total_rows": int(total_rows),
        "real_rows": int(real_rows),
        "synthetic_rows": int(synthetic_rows),
        "data_source": data_source,
    }

    # Write a sidecar provenance file so training always knows the dataset source.
    try:
        sidecar = f"{output_path}.provenance.json"
        with open(sidecar, "w") as f:
            json.dump(provenance, f, indent=2)
    except Exception:
        pass

    return provenance

def synthesize_forensic_data(num_samples=100):
    """
    Synthesize forensic evidence metadata for exploration/load testing only.
    Rows produced here are explicitly synthetic and are NEVER used to train a
    model that the system serves as verified.
    """
    import random
    
    file_types = ["file", "disk_image", "memory_dump", "network_capture", "log_file", "registry", "email"]
    partitions = ["NTFS", "FAT32", "EXT4", "APFS", "exFAT"]
    
    data = []
    for _ in range(num_samples):
        f_type = random.choice(file_types)
        partition = random.choice(partitions)
        
        # Correlate features
        if f_type == "memory_dump":
            size = random.randint(1024**3, 16 * 1024**3)
            entropy = random.uniform(6.5, 7.9)
        elif f_type == "log_file":
            size = random.randint(1024, 10 * 1024**2)
            entropy = random.uniform(3.0, 5.0)
        elif f_type == "disk_image":
            size = random.randint(4 * 1024**3, 64 * 1024**3)
            entropy = random.uniform(5.5, 7.8)
        else:
            size = random.randint(512, 50 * 1024**2)
            entropy = random.uniform(1.0, 7.5)
            
        if entropy > 7.1:
            ai_pred = 0
        elif f_type in ["log_file", "registry", "email"] and entropy < 5.5:
            ai_pred = 1
        else:
            ai_pred = 1 if random.random() > 0.3 else 0
            
        data.append({
            "size_bytes": size,
            "file_type": f_type,
            "entropy": round(entropy, 4),
            "partition": partition,
            "ai_prediction": ai_pred
        })
        
    return pd.DataFrame(data)

if __name__ == "__main__":
    export_dataset()
