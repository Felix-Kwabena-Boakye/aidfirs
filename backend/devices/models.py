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
                 device_fingerprint=None, identity_digest=None, drive_type=None,
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
        # Identity fingerprints derived deterministically from serial:model.
        # These are NOT evidence content hashes — they identify the device and
        # must never be presented as SHA-256/MD5 hashes of an acquired image.
        if serial_number and (not device_fingerprint or not identity_digest):
            fingerprint_src = f"{serial_number}:{model}".encode('utf-8')
            self.device_fingerprint = device_fingerprint or hashlib.sha256(fingerprint_src).hexdigest()
            self.identity_digest = identity_digest or hashlib.md5(fingerprint_src).hexdigest()
        else:
            self.device_fingerprint = device_fingerprint or ''
            self.identity_digest = identity_digest or ''

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

        # Compute identity fingerprints (deterministic serial:model digest — NOT content hashes)
        fingerprint_src = f"{serial_number}:{model}".encode('utf-8')
        device_fingerprint = kwargs.get('device_fingerprint') or hashlib.sha256(fingerprint_src).hexdigest()
        identity_digest = kwargs.get('identity_digest') or hashlib.md5(fingerprint_src).hexdigest()

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
            "device_fingerprint": device_fingerprint,
            "identity_digest": identity_digest,
        }

        if col is not None:
            query = {}
            if drive_letter:
                query["drive_letter"] = drive_letter
            elif serial_number and serial_number != "UNKNOWN":
                query["serial_number"] = serial_number

            if query:
                res = col.update_one(query, {"$set": doc}, upsert=True)
                if res.upserted_id:
                    doc["_id"] = res.upserted_id
                else:
                    existing = col.find_one(query)
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
            for i, d in enumerate(devices):
                if (drive_letter and d.get("drive_letter") == drive_letter) or \
                   (serial_number and serial_number != "UNKNOWN" and d.get("serial_number") == serial_number):
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
    def sync_active_devices(raw_devices):
        """
        Synchronizes MongoDB devices collection with current live scan results.
        Upserts active devices and purges stale disconnected devices.
        Returns list of active Device objects.
        """
        col = Device.get_collection()
        active_serials = set()
        active_letters = set()
        active_devices = []

        for raw in raw_devices:
            serial = raw.get("serial_number", "")
            letter = raw.get("drive_letter", "")
            if serial and serial != "UNKNOWN":
                active_serials.add(serial)
            if letter:
                active_letters.add(letter)

            dev = Device.create(
                device_name=raw.get("volume_name") or raw.get("device_name") or raw.get("model") or "Storage Device",
                serial_number=serial,
                model=raw.get("model", ""),
                filesystem=raw.get("filesystem", ""),
                size_gb=float(raw.get("size_gb") or raw.get("capacity") or 0.0),
                drive_letter=letter,
                source=raw.get("source", "AIDFIRS Agent"),
                vendor=raw.get("vendor", ""),
                manufacturer=raw.get("manufacturer", ""),
                bus_type=raw.get("bus_type", ""),
                device_path=raw.get("device_path", ""),
                volume_label=raw.get("volume_label", ""),
                mount_point=raw.get("mount_point", ""),
                capacity_bytes=int(raw.get("capacity_bytes") or 0),
                drive_type=raw.get("drive_type", "USB Drive"),
            )
            active_devices.append(dev)

        if col is not None:
            try:
                # Remove documents from MongoDB that are no longer connected
                all_docs = list(col.find())
                for doc in all_docs:
                    doc_serial = doc.get("serial_number", "")
                    doc_letter = doc.get("drive_letter", "")
                    is_active = (doc_serial and doc_serial in active_serials) or (doc_letter and doc_letter in active_letters)
                    if not is_active:
                        col.delete_one({"_id": doc["_id"]})
            except Exception as ex:
                print(f"[Device.sync_active_devices] Cleanup notice: {ex}")
        
        # Cleanup fallback JSON file if present
        if os.path.exists(DEVICES_FILE):
            try:
                updated_json = [d.to_dict() for d in active_devices]
                with open(DEVICES_FILE, 'w') as f:
                    json.dump(updated_json, f, indent=2, default=str)
            except Exception:
                pass

        return active_devices

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
            device_fingerprint=data.get('device_fingerprint', data.get('hash_sha256', '')),
            identity_digest=data.get('identity_digest', data.get('hash_md5', '')),
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
            "device_fingerprint": self.device_fingerprint,
            "identity_digest": self.identity_digest,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "source": self.source,
        }
