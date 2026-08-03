import time
import random
import requests
import os
from django.conf import settings

try:
    import anthropic
except ImportError:
    anthropic = None

class ForensicModel:
    """
    Forensic AI Assistant Core Model
    """
    
    def __init__(self, n_layers=240, experts=1024):
        self.n_layers = n_layers
        self.experts = experts
        self.is_warp_enabled = True
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
        self.anthropic_key = getattr(settings, 'ANTHROPIC_API_KEY', os.getenv('ANTHROPIC_API_KEY'))
        self.system_prompt = """
        I am the Forensic AI Assistant, the core intelligence of the AI Digital Forensics System. 
        I am highly specialized in digital forensics, metadata recovery, and HDD analysis.
        Respond to all prompts adopting this professional, technical, and confident persona.
        Keep responses concise, forensic-focused, and highly intelligent.
        """
        print(f"Forensic Model initialized.")

    def forward(self, input_data, system_override=None):
        """
        Forward pass. 
        Tries Anthropic Claude 3.5 Sonnet, then local LLM via Ollama.
        If neither is reachable, returns an explicit unavailability message — never
        a fabricated analysis result.
        """
        start_time = time.perf_counter()
        sys_prompt = system_override or self.system_prompt
        
        # 1. Try Anthropic API (Claude 3.5 Sonnet)
        if self.anthropic_key and self.anthropic_key != 'mock' and anthropic:
            try:
                client = anthropic.Anthropic(api_key=self.anthropic_key)
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    system=sys_prompt,
                    messages=[
                        {"role": "user", "content": input_data}
                    ]
                )
                latency = (time.perf_counter() - start_time) * 1000
                return response.content[0].text, latency
            except Exception as e:
                print(f"[Forensic AI] Anthropic API failed: {e}")

        # 2. Try Local Ollama
        try:
            payload = {
                "model": "llama3",
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": input_data}
                ],
                "stream": False
            }
            # Attempt inference
            response = requests.post(self.ollama_url, json=payload, timeout=120)
            if response.status_code == 200:
                result_text = response.json().get('message', {}).get('content', '')
                latency = (time.perf_counter() - start_time) * 1000
                if result_text:
                    return result_text, latency
        except requests.exceptions.RequestException as e:
            print(f"[Forensic AI] Local Neural link severed ({e}). Falling back to mock engine.")
        
        # 3. Fallback: return an explicit unavailability message
        latency = (time.perf_counter() - start_time) * 1000 # convert to ms
        fallback_msg = f"[FALLBACK OCCURRED] My multi-layered inference grid intercepted your request:\n'{input_data}'\n\nHowever, my primary local inference core is currently offline. Please ensure Ollama is running or valid Anthropic API key is provided."
        return fallback_msg, latency

def load_forensic_model():
    """
    Loads the Forensic AI Assistant Kernel.
    """
    print("[CRITICAL] Initializing Forensic AI Assistant Engine...")
    model = ForensicModel()
    print("[CRITICAL] Forensic AI Assistant is now initialized.")
    return model

if __name__ == "__main__":
    # Benchmark Forensic AI
    model = load_forensic_model()
    dummy_input = "Global Forensic Stream" * 1000
    _, latency = model.forward(dummy_input)
    print(f"► FORENSIC AI LATENCY: {latency:.8f} ms")


# --------------------------------------------------
# Scikit-Learn Model Loading & Predict Integration
# --------------------------------------------------
_cached_ml_model = None

def _is_model_trusted(model_doc):
    """
    A model is only trusted for verified predictions when it was trained on real
    (or mixed) labelled data with recorded provenance. Models trained purely on
    synthetic data, or legacy models lacking provenance metadata, are untrusted.
    """
    data_source = (model_doc.get("data_source") or "").strip()
    training_method = (model_doc.get("training_method") or "").strip()
    if data_source == "synthetic":
        return False
    if training_method in ("real", "real_with_synthetic_supplement"):
        return True
    return False

def _extract_provenance(model_doc):
    """Read dataset provenance metadata recorded at training time."""
    return {
        "data_source": model_doc.get("data_source"),
        "real_rows": model_doc.get("real_rows"),
        "synthetic_rows": model_doc.get("synthetic_rows"),
        "training_method": model_doc.get("training_method"),
    }

def load_ml_model():
    """
    Load the active Scikit-Learn ML model from MongoDB Atlas or local storage.
    Caches the model in memory.
    """
    global _cached_ml_model
    if _cached_ml_model is not None:
        return _cached_ml_model

    print("[CRITICAL] Loading active Forensic Scikit-Learn Model...")
    import pickle
    from mongo_connection import get_ai_models_collection
    
    # Try loading from MongoDB Atlas first
    ai_models_col = get_ai_models_collection()
    if ai_models_col is not None:
        try:
            model_doc = ai_models_col.find_one({"model_name": "random_forest_recoverability", "status": "active"})
            if model_doc:
                model_bytes = bytes(model_doc["model_bytes"])
                model = pickle.loads(model_bytes)
                _cached_ml_model = {
                    "model": model,
                    "mappings": model_doc.get("mappings", {}),
                    "accuracy": model_doc.get("accuracy", 0.0),
                    "trained_at": model_doc.get("trained_at"),
                    "features": model_doc.get("features", []),
                    "provenance": _extract_provenance(model_doc),
                    "trusted": _is_model_trusted(model_doc),
                }
                print(f"[CRITICAL] Loaded model from MongoDB Atlas (Accuracy: {model_doc.get('accuracy'):.4f}, Trained: {model_doc.get('trained_at')}, Trusted: {_cached_ml_model['trusted']})")
                return _cached_ml_model
        except Exception as e:
            print(f"Error loading model from MongoDB Atlas: {e}")
            
    # Try loading from local file fallback
    local_path = "storage/models/active_model.pkl"
    if os.path.exists(local_path):
        try:
            with open(local_path, "rb") as f:
                model_doc = pickle.load(f)
            model_bytes = bytes(model_doc["model_bytes"])
            model = pickle.loads(model_bytes)
            _cached_ml_model = {
                "model": model,
                "mappings": model_doc.get("mappings", {}),
                "accuracy": model_doc.get("accuracy", 0.0),
                "trained_at": model_doc.get("trained_at"),
                "features": model_doc.get("features", []),
                "provenance": _extract_provenance(model_doc),
                "trusted": _is_model_trusted(model_doc),
            }
            print(f"[CRITICAL] Loaded model from local storage fallback (Accuracy: {model_doc.get('accuracy'):.4f}, Trusted: {_cached_ml_model['trusted']})")
            return _cached_ml_model
        except Exception as e:
            print(f"Error loading local model: {e}")
            
    print("[WARNING] No active ML model found in MongoDB or local storage. Predictions will not be served.")
    _cached_ml_model = {
        "model": None,
        "mappings": {},
        "accuracy": 0.0,
        "trained_at": None,
        "features": [],
        "provenance": None,
        "trusted": False,
    }
    return _cached_ml_model


def predict_recoverability(size_bytes, file_type, entropy, partition):
    """
    Predict recoverability and return (prediction, confidence_score, anomaly_detected).

    Only returns a prediction when a trusted, provenance-verified ML model is loaded.
    When no trusted model exists it returns (None, None, []) so callers can surface an
    honest {"status": "heuristic", "confidence": null, "verified": false} result instead
    of fabricating a confidence score from entropy heuristics.
    """
    import numpy as np
    
    ml_info = load_ml_model()
    model = ml_info.get("model")
    trusted = ml_info.get("trusted", False)
    
    # 1. No trusted model available: never fabricate a prediction or confidence score.
    if model is None or not trusted:
        return None, None, []
        
    # 2. Scikit-learn prediction
    try:
        mappings = ml_info.get("mappings", {})
        file_type_map = mappings.get("file_type", {})
        partition_map = mappings.get("partition", {})
        
        # Map string inputs to integers
        ft_idx = file_type_map.get(str(file_type).lower(), file_type_map.get("other", 7))
        part_idx = partition_map.get(str(partition), partition_map.get("other", 5))
        
        # Format feature array
        features = [[
            int(size_bytes),
            int(ft_idx),
            float(entropy),
            int(part_idx)
        ]]
        
        # Run prediction
        pred = int(model.predict(features)[0])
        # Get probability
        probs = model.predict_proba(features)[0]
        conf = float(probs[pred])
        
        # Descriptive, measured anomaly flags (no fabricated conclusions)
        anomalies = []
        if float(entropy) > 7.5:
            anomalies.append("High byte entropy (value above 7.5): possible compression or encryption; manual inspection required.")
        if float(entropy) < 1.0 and int(size_bytes) > 1024 * 1024:
            anomalies.append("Low byte entropy on a file larger than 1 MiB: possible sector wiping or padding; manual inspection required.")
            
        return pred, conf, anomalies
    except Exception as e:
        print(f"Error during Scikit-Learn prediction: {e}.")
        return None, None, []

