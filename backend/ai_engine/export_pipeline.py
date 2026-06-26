import os
import sys
import pandas as pd
from pymongo import MongoClient

# Ensure backend directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mongo_connection import get_db, MONGO_AVAILABLE

# Compute backend root so the CSV path is always absolute and correct.
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def export_dataset(output_path=None):
    if output_path is None:
        output_path = os.path.join(_BACKEND_ROOT, "forensics_training_data.csv")
    print("Initializing Forensic Dataset Export Pipeline...")
    
    db = get_db()
    if db is None:
        print("MongoDB is not available. Simulating dataset export with synthesized forensic features...")
        dataset = synthesize_forensic_data(100)
    else:
        try:
            evidence = list(db.evidence.find())
            analysis = list(db.analysis_results.find())
            
            print(f"Retrieved {len(evidence)} evidence documents and {len(analysis)} analysis results.")
            
            if len(evidence) == 0 or len(analysis) == 0:
                print("Insufficient documents in database. Merging and synthesizing complete dataset...")
                dataset = synthesize_forensic_data(100)
            else:
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
                
                clean_data = []
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
                        
                    # ai_prediction / recoverable target
                    ai_pred = row.get("ai_prediction")
                    if ai_pred is None or pd.isna(ai_pred):
                        # check in findings
                        findings = row.get("findings")
                        if isinstance(findings, dict):
                            ai_pred = findings.get("ai_prediction")
                            
                    if ai_pred is None or pd.isna(ai_pred):
                        # Guess based on entropy (lower entropy = more recoverable)
                        ai_pred = 1 if float(entropy) < 6.0 else 0
                        
                    clean_data.append({
                        "size_bytes": int(size),
                        "file_type": str(ftype),
                        "entropy": float(entropy),
                        "partition": str(partition),
                        "ai_prediction": int(ai_pred)
                    })
                    
                dataset = pd.DataFrame(clean_data)
                
                # If the dataset is too small, supplement with synthesized data
                if len(dataset) < 20:
                    print(f"Dataset has only {len(dataset)} merged rows. Supplementing with synthesized forensic samples...")
                    synth_df = synthesize_forensic_data(100 - len(dataset))
                    dataset = pd.concat([dataset, synth_df], ignore_index=True)
        except Exception as e:
            print(f"Error querying MongoDB: {e}. Falling back to synthesized dataset.")
            dataset = synthesize_forensic_data(100)
            
    # Process target columns
    final_cols = ["size_bytes", "file_type", "entropy", "partition", "ai_prediction"]
    
    # Save CSV
    dataset[final_cols].to_csv(output_path, index=False)
    print(f"Successfully exported {len(dataset)} samples to {output_path}")
    return output_path

def synthesize_forensic_data(num_samples=100):
    """
    Synthesize realistic forensic evidence metadata for training classical ML models.
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
