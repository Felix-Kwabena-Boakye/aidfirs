import os
import sys
import pickle
import pandas as pd
from datetime import datetime, timezone
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from bson.binary import Binary

# Ensure backend directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mongo_connection import get_ai_models_collection, MONGO_AVAILABLE

# Compute backend root so the CSV path is always absolute and correct.
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def train_and_save_model(csv_path=None):
    if csv_path is None:
        csv_path = os.path.join(_BACKEND_ROOT, "forensics_training_data.csv")
    print(f"Loading dataset from {csv_path}...")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset CSV not found at {csv_path}. Please run export_pipeline.py first.")
        
    df = pd.read_csv(csv_path)
    
    # Mappings for categorical variables
    file_type_map = {
        "file": 0, "disk_image": 1, "memory_dump": 2, 
        "network_capture": 3, "log_file": 4, "registry": 5, 
        "email": 6, "other": 7
    }
    
    partition_map = {
        "NTFS": 0, "FAT32": 1, "EXT4": 2, 
        "APFS": 3, "exFAT": 4, "other": 5
    }
    
    print("Pre-processing dataset features...")
    # Map file_type
    df["file_type"] = df["file_type"].astype(str).str.lower().map(file_type_map).fillna(file_type_map["other"])
    
    # Map partition
    df["partition"] = df["partition"].astype(str).map(partition_map).fillna(partition_map["other"])
    
    # Split features and target
    X = df[["size_bytes", "file_type", "entropy", "partition"]]
    y = df["ai_prediction"]
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print("Training RandomForestClassifier model...")
    model = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate model
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    
    print("Model Evaluation Metrics:")
    print(f"  Accuracy:  {accuracy:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1 Score:  {f1:.4f}")
    
    # Serialize model
    serialized_model = pickle.dumps(model)
    
    # Prepare database document
    model_doc = {
        "model_name": "random_forest_recoverability",
        "trained_at": datetime.now(timezone.utc),
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "features": ["size_bytes", "file_type", "entropy", "partition"],
        "mappings": {
            "file_type": file_type_map,
            "partition": partition_map
        },
        "model_bytes": Binary(serialized_model),
        "status": "active"
    }
    
    # Save to MongoDB
    ai_models_col = get_ai_models_collection()
    if ai_models_col is not None:
        try:
            print("Saving trained model weights to MongoDB Atlas...")
            # Set all older models with the same name to inactive status
            ai_models_col.update_many(
                {"model_name": "random_forest_recoverability", "status": "active"},
                {"$set": {"status": "inactive"}}
            )
            # Insert the new model
            result = ai_models_col.insert_one(model_doc)
            print(f"Model saved successfully to MongoDB Atlas with ID: {result.inserted_id}")
        except Exception as e:
            print(f"Failed to save model to MongoDB Atlas: {e}. Saving locally instead.")
            save_model_locally(model_doc)
    else:
        print("MongoDB is not available. Saving trained model locally...")
        save_model_locally(model_doc)

def save_model_locally(model_doc):
    """
    Saves the model metadata and serialized weights to a local file in storage/models.
    """
    model_dir = "storage/models"
    os.makedirs(model_dir, exist_ok=True)
    local_path = os.path.join(model_dir, "active_model.pkl")
    
    # Convert Binary BSON back to standard bytes for local pickle storage
    if isinstance(model_doc["model_bytes"], Binary):
        model_doc["model_bytes"] = bytes(model_doc["model_bytes"])
        
    with open(local_path, "wb") as f:
        pickle.dump(model_doc, f)
    print(f"Model successfully saved locally at {local_path}")

if __name__ == "__main__":
    train_and_save_model()
