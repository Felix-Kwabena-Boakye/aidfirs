import os
import json
from typing import List, Dict, Any

class ForensicTrainingPipeline:
    """
    Pipeline for extracting and preparing forensic data for AI model training.
    """
    
    def __init__(self, data_registry: str = "storage/training_data"):
        self.data_registry = data_registry
        os.makedirs(data_registry, exist_ok=True)

    def extract_training_samples(self, evidence_id: str, forensic_data: Dict[str, Any], ground_truth: str):
        """
        Converts forensic findings and human corrections into a training sample.
        """
        sample = {
            "instruction": "Classify the following forensic data fragment and identify anomalies.",
            "input": json.dumps(forensic_data),
            "output": ground_truth
        }
        
        sample_path = os.path.join(self.data_registry, f"sample_{evidence_id}_{os.urandom(4).hex()}.json")
        with open(sample_path, 'w') as f:
            json.dump(sample, f, indent=2)
            
        return sample_path

    def prepare_dataset(self) -> str:
        """
        Consolidates individual samples into a single fine-tuning dataset (e.g., JSONL).
        """
        all_samples = []
        for file in os.listdir(self.data_registry):
            if file.endswith(".json"):
                with open(os.path.join(self.data_registry, file), 'r') as f:
                    all_samples.append(json.load(f))
                    
        dataset_path = "storage/datasets/forensic_finetune_latest.jsonl"
        os.makedirs("storage/datasets", exist_ok=True)
        
        with open(dataset_path, 'w') as f:
            for item in all_samples:
                f.write(json.dumps(item) + '\n')
                
        return dataset_path
