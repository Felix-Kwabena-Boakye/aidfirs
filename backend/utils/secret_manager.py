import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables on module import
load_dotenv()

class SecretManager:
    """
    Utility class to manage application secrets, configurations, and API keys.
    Supports reading from environment variables, local .env files, and provides
    graceful fallbacks.
    """

    @staticmethod
    def get_secret(key: str, default: str = None) -> str:
        """
        Retrieve a secret or configuration value by key.
        Looks in environment variables first.
        """
        val = os.getenv(key)
        if val is not None:
            return val
        return default

    @staticmethod
    def get_bool(key: str, default: bool = False) -> bool:
        """
        Retrieve a configuration value as a boolean.
        """
        val = SecretManager.get_secret(key)
        if val is None:
            return default
        return val.lower() in ("true", "1", "yes", "on")

    @staticmethod
    def get_int(key: str, default: int = 0) -> int:
        """
        Retrieve a configuration value as an integer.
        """
        val = SecretManager.get_secret(key)
        if val is None:
            return default
        try:
            return int(val)
        except ValueError:
            return default

    @property
    def anthropic_api_key(self) -> str:
        return self.get_secret("ANTHROPIC_API_KEY")

    @property
    def secret_key(self) -> str:
        return self.get_secret("SECRET_KEY")

    @property
    def mongo_uri(self) -> str:
        return self.get_secret("MONGO_URI", "mongodb://localhost:27017")

    @property
    def mongo_db_name(self) -> str:
        return self.get_secret("MONGO_DB_NAME", "ai_digital_forensics")

secret_manager = SecretManager()
