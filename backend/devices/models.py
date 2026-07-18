from mongo_connection import get_db, MONGO_AVAILABLE
from bson import ObjectId
import json
import os
import uuid
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEVICES_FILE = os.path.join(BASE_DIR, 'devices.json')

class Device:
    """
    MongoDB-based Device model for tracking connected devices.
    """
    def __init__(self, device_name, serial_number, model, filesystem, size_gb, drive_letter, connected_at=None, source="AIDFIRS Agent", _id=None):
        self._id = _id
        self.device_name = device_name
        self.serial_number = serial_number
        self.model = model
        self.filesystem = filesystem
        self.size_gb = float(size_gb) if size_gb is not None else 0.0
        self.drive_letter = drive_letter
        self.connected_at = connected_at or datetime.now(timezone.utc)
        self.source = source

    @staticmethod
    def get_collection():
        db = get_db()
        if db is not None:
            return db['devices']
        return None

    @staticmethod
    def create(device_name, serial_number, model, filesystem, size_gb, drive_letter, connected_at=None, source="AIDFIRS Agent"):
        col = Device.get_collection()
        connected_at = connected_at or datetime.now(timezone.utc)
        if isinstance(connected_at, str):
            try:
                connected_at = datetime.fromisoformat(connected_at.replace('Z', '+00:00'))
            except:
                connected_at = datetime.now(timezone.utc)

        doc = {
            "device_name": device_name,
            "serial_number": serial_number,
            "model": model,
            "filesystem": filesystem,
            "size_gb": float(size_gb) if size_gb is not None else 0.0,
            "drive_letter": drive_letter,
            "connected_at": connected_at,
            "source": source
        }

        if col is not None:
            if serial_number:
                # Upsert by serial number to keep it clean
                res = col.update_one({"serial_number": serial_number}, {"$set": doc}, upsert=True)
                if res.upserted_id:
                    doc["_id"] = res.upserted_id
                else:
                    existing = col.find_one({"serial_number": serial_number})
                    doc["_id"] = existing["_id"] if existing else None
            else:
                res = col.insert_one(doc)
                doc["_id"] = res.inserted_id
        else:
            # Fallback to local devices.json file
            doc["_id"] = str(uuid.uuid4())
            devices = []
            if os.path.exists(DEVICES_FILE):
                try:
                    with open(DEVICES_FILE, 'r') as f:
                        devices = json.load(f)
                except:
                    pass
            updated = False
            if serial_number:
                for i, d in enumerate(devices):
                    if d.get("serial_number") == serial_number:
                        doc["_id"] = d.get("_id")
                        devices[i] = doc
                        updated = True
                        break
            if not updated:
                devices.append(doc)
            with open(DEVICES_FILE, 'w') as f:
                json.dump(devices, f, indent=2, default=str)

        return Device.from_dict(doc)

    @staticmethod
    def get_all():
        col = Device.get_collection()
        if col is not None:
            try:
                cursor = col.find().sort("connected_at", -1)
                return [Device.from_dict(d) for d in cursor]
            except Exception:
                pass
        
        if os.path.exists(DEVICES_FILE):
            try:
                with open(DEVICES_FILE, 'r') as f:
                    devices_data = json.load(f)
                devices_data.sort(key=lambda x: x.get('connected_at', ''), reverse=True)
                return [Device.from_dict(d) for d in devices_data]
            except Exception:
                pass
        return []

    @staticmethod
    def get_by_id(device_id):
        col = Device.get_collection()
        if col is not None:
            try:
                doc = col.find_one({"_id": ObjectId(device_id)})
                if doc:
                    return Device.from_dict(doc)
            except Exception:
                pass
        if os.path.exists(DEVICES_FILE):
            try:
                with open(DEVICES_FILE, 'r') as f:
                    devices_data = json.load(f)
                for d in devices_data:
                    if str(d.get('_id')) == str(device_id):
                        return Device.from_dict(d)
            except Exception:
                pass
        return None

    @staticmethod
    def from_dict(data):
        connected_at = data.get('connected_at')
        if isinstance(connected_at, str):
            try:
                connected_at = datetime.fromisoformat(connected_at.replace('Z', '+00:00'))
            except:
                pass
        return Device(
            _id=data.get('_id'),
            device_name=data.get('device_name'),
            serial_number=data.get('serial_number'),
            model=data.get('model'),
            filesystem=data.get('filesystem'),
            size_gb=data.get('size_gb', 0.0),
            drive_letter=data.get('drive_letter'),
            connected_at=connected_at,
            source=data.get('source', 'AIDFIRS Agent')
        )

    def to_dict(self):
        return {
            "id": str(self._id) if self._id else None,
            "_id": str(self._id) if self._id else None,
            "drive_letter": self.drive_letter,
            "volume_name": self.device_name,
            "drive_type": "USB Drive" if "usb" in (self.model or "").lower() or "usb" in (self.device_name or "").lower() else "HDD",
            "size_gb": self.size_gb,
            "serial_number": self.serial_number,
            "interface": "USB",
            "is_external": True,
            "filesystem": self.filesystem,
            "model": self.model,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "source": self.source
        }
