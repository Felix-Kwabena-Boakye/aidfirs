from mongo_connection import get_db, MONGO_AVAILABLE
from bson import ObjectId
import json
import os
import uuid
import hashlib
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEVICES_FILE = os.path.join(BASE_DIR, 'devices.json')


class Device:
    """
    MongoDB-based Device model for tracking connected forensic devices.
    Stores full forensic metadata per device including vendor, bus type,
    device path, and cryptographic fingerprints.
    """
    def __init__(self, device_name, serial_number, model, filesystem, size_gb,
                 drive_letter, connected_at=None, source="AIDFIRS Agent",
                 # Extended forensic fields
                 vendor=None, manufacturer=None, bus_type=None, device_path=None,
                 volume_label=None, mount_point=None, capacity_bytes=None,
                 hash_sha256=None, hash_md5=None, drive_type=None,
                 _id=None):
        self._id = _id
        self.device_name = device_name
        self.serial_number = serial_number
        self.model = model
        self.filesystem = filesystem
        self.size_gb = float(size_gb) if size_gb is not None else 0.0
        self.drive_letter = drive_letter
        self.connected_at = connected_at or datetime.now(timezone.utc)
        self.source = source
        # Extended fields
        self.vendor = vendor or ''
        self.manufacturer = manufacturer or ''
        self.bus_type = bus_type or ''
        self.device_path = device_path or drive_letter or ''
        self.volume_label = volume_label or device_name or ''
        self.mount_point = mount_point or drive_letter or ''
        self.capacity_bytes = int(capacity_bytes) if capacity_bytes else int(self.size_gb * 1024 ** 3)
        self.drive_type = drive_type or 'USB Drive'
        # Compute fingerprints if not provided
        if serial_number and (not hash_sha256 or not hash_md5):
            fingerprint_src = f"{serial_number}:{model}".encode('utf-8')
            self.hash_sha256 = hash_sha256 or hashlib.sha256(fingerprint_src).hexdigest()
            self.hash_md5 = hash_md5 or hashlib.md5(fingerprint_src).hexdigest()
        else:
            self.hash_sha256 = hash_sha256 or ''
            self.hash_md5 = hash_md5 or ''

    @staticmethod
    def get_collection():
        db = get_db()
        if db is not None:
            return db['devices']
        return None

    @staticmethod
    def create(device_name, serial_number, model, filesystem, size_gb, drive_letter,
               connected_at=None, source="AIDFIRS Agent", **kwargs):
        col = Device.get_collection()
        connected_at = connected_at or datetime.now(timezone.utc)
        if isinstance(connected_at, str):
            try:
                connected_at = datetime.fromisoformat(connected_at.replace('Z', '+00:00'))
            except:
                connected_at = datetime.now(timezone.utc)

        # Compute fingerprints
        fingerprint_src = f"{serial_number}:{model}".encode('utf-8')
        hash_sha256 = kwargs.get('hash_sha256') or hashlib.sha256(fingerprint_src).hexdigest()
        hash_md5 = kwargs.get('hash_md5') or hashlib.md5(fingerprint_src).hexdigest()

        doc = {
            "device_name": device_name,
            "serial_number": serial_number,
            "model": model,
            "filesystem": filesystem,
            "size_gb": float(size_gb) if size_gb is not None else 0.0,
            "drive_letter": drive_letter,
            "connected_at": connected_at,
            "source": source,
            # Extended forensic fields
            "vendor": kwargs.get('vendor', ''),
            "manufacturer": kwargs.get('manufacturer', ''),
            "bus_type": kwargs.get('bus_type', ''),
            "device_path": kwargs.get('device_path', drive_letter or ''),
            "volume_label": kwargs.get('volume_label', device_name or ''),
            "mount_point": kwargs.get('mount_point', drive_letter or ''),
            "capacity_bytes": int(kwargs.get('capacity_bytes', int((float(size_gb) if size_gb else 0) * 1024 ** 3))),
            "drive_type": kwargs.get('drive_type', 'USB Drive'),
            "hash_sha256": hash_sha256,
            "hash_md5": hash_md5,
        }

        if col is not None:
            if serial_number:
                # Upsert by serial number to avoid duplicates
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
            # Fallback to local JSON file
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
        # Try string match fallback
        if col is not None:
            try:
                doc = col.find_one({"_id": device_id})
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
    def delete_by_id(device_id):
        col = Device.get_collection()
        if col is not None:
            try:
                col.delete_one({"_id": ObjectId(device_id)})
                return True
            except Exception:
                pass
        if os.path.exists(DEVICES_FILE):
            try:
                with open(DEVICES_FILE, 'r') as f:
                    devices_data = json.load(f)
                devices_data = [d for d in devices_data if str(d.get('_id')) != str(device_id)]
                with open(DEVICES_FILE, 'w') as f:
                    json.dump(devices_data, f, indent=2, default=str)
                return True
            except Exception:
                pass
        return False

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
            device_name=data.get('device_name', ''),
            serial_number=data.get('serial_number', ''),
            model=data.get('model', ''),
            filesystem=data.get('filesystem', ''),
            size_gb=data.get('size_gb', 0.0),
            drive_letter=data.get('drive_letter', ''),
            connected_at=connected_at,
            source=data.get('source', 'AIDFIRS Agent'),
            vendor=data.get('vendor', ''),
            manufacturer=data.get('manufacturer', ''),
            bus_type=data.get('bus_type', ''),
            device_path=data.get('device_path', ''),
            volume_label=data.get('volume_label', ''),
            mount_point=data.get('mount_point', ''),
            capacity_bytes=data.get('capacity_bytes', 0),
            drive_type=data.get('drive_type', 'USB Drive'),
            hash_sha256=data.get('hash_sha256', ''),
            hash_md5=data.get('hash_md5', ''),
        )

    def to_dict(self):
        return {
            "id": str(self._id) if self._id else None,
            "_id": str(self._id) if self._id else None,
            "device_name": self.device_name,
            "drive_letter": self.drive_letter,
            "volume_name": self.volume_label or self.device_name,
            "volume_label": self.volume_label,
            "mount_point": self.mount_point,
            "device_path": self.device_path,
            "drive_type": self.drive_type,
            "size_gb": self.size_gb,
            "capacity_bytes": self.capacity_bytes,
            "serial_number": self.serial_number,
            "vendor": self.vendor,
            "manufacturer": self.manufacturer,
            "bus_type": self.bus_type,
            "interface": self.bus_type or "USB",
            "is_external": True,
            "filesystem": self.filesystem,
            "model": self.model,
            "hash_sha256": self.hash_sha256,
            "hash_md5": self.hash_md5,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "source": self.source,
        }
