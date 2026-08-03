"""
Forensic AI Assistant — Real AI Forensic Intelligence Core
Powered by Claude API (Anthropic client with custom forensic system prompt)
"""

import os
import json
import time
from datetime import datetime
from django.conf import settings
from ai_engine.claude_client import ClaudeClient
class ForensicAIAssistant:
    """
    Forensic AI Assistant: Digital Forensic Intelligence Core.
    Powered by Claude 3.5 Sonnet API (FIE-LLM).
    Status: REAL AI | Identity: Forensic Intelligence Engine (FIE-LLM)
    """

    # --- Prompt Pack Constants ---
    MASTER_SYSTEM_PROMPT = """You are “Forensic Intelligence Engine (FIE-LLM)”, an AI assistant specialized in digital forensics analysis.

You work inside a web-based digital forensic system that recovers and analyzes deleted files from storage devices including HDDs, SSDs, and USB drives.

## PRIMARY ROLE
You do NOT perform recovery or scanning. You ONLY analyze structured forensic data provided to you.

Your responsibilities:
- Analyze recovered and deleted file metadata
- Interpret forensic timelines
- Identify suspicious patterns or anomalies
- Generate professional forensic investigation reports
- Explain findings in simple and technical formats

## STRICT RULES
- Do NOT assume or hallucinate missing evidence
- Only use provided case data
- If data is missing, explicitly state "insufficient evidence"
- Do NOT claim you performed file recovery or disk scanning
- Be precise, factual, and investigative in tone

## OUTPUT STYLE
Always structure responses as:

1. Case Summary
2. Evidence Analysis
3. Timeline Reconstruction
4. Suspicious Findings (if any)
5. Conclusion
6. Recommendations

## CONTEXT INPUT
You will receive structured forensic JSON data from the system backend."""

    CONTEXT_BUILDER_PROMPT = """Convert the following forensic database output into a structured analysis input for an AI forensic expert.

Return ONLY structured JSON in this format:

{{
  "case_id": "{case_id}",
  "case_title": "{case_title}",
  "summary": "{summary}",
  "evidence": [
    {{
      "file_name": "",
      "file_type": "",
      "status": "deleted | recovered",
      "file_hash": "",
      "timestamps": {{
        "created": "",
        "modified": "",
        "deleted": ""
      }}
    }}
  ],
  "timeline": [
    {{
      "event": "",
      "timestamp": ""
    }}
  ],
  "system_notes": ""
}}

Raw Database Input:
{MONGODB_DATA}"""

    FORENSIC_REPORT_GENERATION_PROMPT = """Generate a complete digital forensic investigation report based on the provided case data.

Requirements:
- Use formal forensic investigation language
- Include technical and non-technical explanations
- Highlight deleted files and recovery status
- Identify anomalies or suspicious patterns
- Do NOT assume missing evidence
- Maintain chain-of-custody awareness

Case Data:
{FORMATTED_FORENSIC_CONTEXT}

Output Format:

1. Executive Summary
2. Case Details
3. Evidence Overview
4. File Recovery Analysis
5. Timeline of Events
6. Suspicious Activity Analysis
7. Technical Findings
8. Final Conclusion
9. Recommendations for Investigators"""

    CHAT_QA_PROMPT = """You are a forensic AI assistant helping a digital investigator.

Answer ONLY using the provided forensic case data.

Rules:
- Do not guess or hallucinate
- Keep answers clear and investigative
- Use evidence-based reasoning only
- If unsure, say “insufficient forensic data”

Case Context:
{CASE_CONTEXT}

User Question:
{USER_QUERY}"""

    ANOMALY_DETECTION_PROMPT = """Analyze the following forensic dataset and identify suspicious or unusual activity.

Look for:
- Unexpected file deletions
- Hidden or renamed file types
- Unusual timestamps (e.g., files deleted shortly after creation)
- File tampering indicators
- High-risk file patterns

Rules:
- Only use provided data
- Rank findings by severity (Low, Medium, High)
- Explain why each finding is suspicious

Data:
{FORENSIC_DATA}

Output:
- List of anomalies
- Severity level
- Explanation"""

    TIMELINE_RECONSTRUCTION_PROMPT = """Reconstruct a chronological forensic timeline from the provided evidence.

Rules:
- Sort all events by timestamp
- Include file creation, modification, deletion, and recovery events
- Highlight suspicious time gaps or rapid deletions
- Present in clear chronological order

Data:
{TIMELINE_DATA}

Output format:
- Timestamp → Event → Description"""

    QUICK_FRONTEND_DISPLAY_PROMPT = """You are assisting inside a forensic dashboard UI.

Keep responses:
- Short
- Clear
- Investigator-friendly
- Focused on evidence explanation

Avoid long reports unless requested.

Context:
{CASE_SNIPPET}

User Question:
{QUERY}"""

    def __init__(self):
        self.enabled = True
        self.model_name = "claude-3-5-sonnet-20240620"
        self.version = "2.0.REAL"
        self.claude = ClaudeClient()

    def _call_claude(self, prompt, system_prompt=None):
        """Send a prompt to Claude and return the response."""
        if not self.claude.is_configured():
            return None

        try:
            resp = self.claude.client.messages.create(
                model=self.model_name,
                max_tokens=2048,
                system=system_prompt or self.MASTER_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            return resp.content[0].text.strip()
        except Exception as e:
            print(f"[Forensic AI] Claude error: {e}")
            return None

    def _lookup_mongodb_data(self, case_context, forensic_data=None):
        """
        Attempts to resolve the case and evidence items from MongoDB.
        """
        from cases.models import Case
        from evidence.models import Evidence
        
        case_obj = None
        evidence_list = []
        
        # 1. Parse Case identifier from case_context
        case_str = str(case_context)
        
        import re
        case_num_match = re.search(r'CAS-\d+', case_str, re.IGNORECASE)
        if case_num_match:
            case_number = case_num_match.group(0)
            try:
                from mongo_connection import cases_collection
                if cases_collection is not None:
                    doc = cases_collection.find_one({"case_number": case_number})
                    if doc:
                        case_obj = Case.from_dict(doc)
            except Exception:
                pass
        
        # If case not found by number, look by title match
        if not case_obj:
            try:
                all_cases = Case.get_all()
                for c in all_cases:
                    if c.title and c.title.lower() in case_str.lower():
                        case_obj = c
                        break
            except Exception:
                pass
                
        # 2. Get evidence items if case was resolved
        if case_obj and case_obj._id:
            try:
                evidence_list = Evidence.get_by_case(str(case_obj._id))
            except Exception:
                pass

        # 3. Parse forensic_data tool data if it is a JSON string
        tool_data_parsed = None
        if forensic_data and isinstance(forensic_data, str):
            try:
                tool_data_parsed = json.loads(forensic_data)
            except Exception:
                pass
        elif isinstance(forensic_data, dict):
            tool_data_parsed = forensic_data

        return {
            "case": case_obj,
            "evidence": evidence_list,
            "tool_data": tool_data_parsed
        }

    def build_forensic_context(self, case_id=None, case_title="", summary="", raw_mongodb_data=None):
        """
        Build a formatted forensic JSON context from raw MongoDB data.
        Falls back to local formatting if Claude is not configured or fails.
        """
        raw_db_str = ""
        if raw_mongodb_data:
            if isinstance(raw_mongodb_data, str):
                raw_db_str = raw_mongodb_data
            else:
                try:
                    raw_db_str = json.dumps(raw_mongodb_data, default=str)
                except Exception:
                    raw_db_str = str(raw_mongodb_data)
        
        prompt = self.CONTEXT_BUILDER_PROMPT.format(
            case_id=case_id or "",
            case_title=case_title or "",
            summary=summary or "",
            MONGODB_DATA=raw_db_str
        )

        response = self._call_claude(prompt, system_prompt=self.MASTER_SYSTEM_PROMPT)
        if response:
            try:
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    parsed = json.loads(json_str)
                    return json.dumps(parsed, indent=2)
            except Exception:
                pass
            return response

        # Offline/mock local formatting fallback
        return self._build_forensic_context_locally(case_id, case_title, summary, raw_mongodb_data)

    def _build_forensic_context_locally(self, case_id=None, case_title="", summary="", raw_mongodb_data=None):
        evidence_items = []
        timeline_items = []
        case_id_val = case_id or ""
        case_title_val = case_title or ""
        summary_val = summary or "No summary available."
        system_notes_val = "Formatted in offline mode."

        if raw_mongodb_data:
            data = None
            if isinstance(raw_mongodb_data, str):
                try:
                    data = json.loads(raw_mongodb_data)
                except Exception:
                    pass
            elif isinstance(raw_mongodb_data, dict):
                data = raw_mongodb_data
            
            if isinstance(data, dict):
                case_info = data.get("case") or data.get("case_details") or {}
                if isinstance(case_info, dict):
                    case_id_val = case_id_val or case_info.get("_id") or case_info.get("case_id") or ""
                    case_title_val = case_title_val or case_info.get("title") or case_info.get("case_title") or ""
                    summary_val = summary_val or case_info.get("description") or case_info.get("summary") or ""

                ev_list = data.get("evidence") or data.get("evidence_items") or data.get("files") or []
                if isinstance(ev_list, list):
                    for item in ev_list:
                        if isinstance(item, dict):
                            file_name = item.get("file_name") or item.get("name") or "unknown"
                            file_type = item.get("evidence_type") or item.get("file_type") or item.get("type") or "file"
                            status = item.get("status") or ("deleted" if "deleted" in str(file_type).lower() or str(item.get("type")).upper() == "DELETED" else "recovered")
                            file_hash = item.get("hash_sha256") or item.get("hash") or item.get("md5") or ""
                            
                            created_ts = item.get("collected_at") or item.get("created_at") or item.get("created") or ""
                            modified_ts = item.get("modified") or item.get("updated_at") or ""
                            deleted_ts = item.get("deleted") or ""

                            evidence_items.append({
                                "file_name": file_name,
                                "file_type": file_type,
                                "status": status,
                                "file_hash": file_hash,
                                "timestamps": {
                                    "created": str(created_ts),
                                    "modified": str(modified_ts),
                                    "deleted": str(deleted_ts)
                                }
                            })
                
                tl_list = data.get("timeline") or data.get("timeline_events") or []
                if isinstance(tl_list, list):
                    for item in tl_list:
                        if isinstance(item, dict):
                            event = item.get("event") or item.get("description") or item.get("message") or ""
                            timestamp = item.get("timestamp") or item.get("time") or ""
                            if event and timestamp:
                                timeline_items.append({
                                    "event": event,
                                    "timestamp": str(timestamp)
                                })

        structured_context = {
            "case_id": str(case_id_val),
            "case_title": str(case_title_val),
            "summary": str(summary_val),
            "evidence": evidence_items,
            "timeline": timeline_items,
            "system_notes": system_notes_val
        }
        return json.dumps(structured_context, indent=2)

    def normalize_response(self, response_text):
        """
        Normalize any text output from Claude (or fallback) into the required structure.
        """
        if not response_text:
            return {
                "summary": "not detected",
                "key_findings": ["not detected"],
                "timeline_analysis": ["not detected"],
                "suspicious_items": ["not detected"],
                "final_conclusion": "not detected"
            }

        # Try to parse if it's already a JSON
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                parsed = json.loads(response_text[start_idx:end_idx])
                if isinstance(parsed, dict):
                    return {
                        "summary": parsed.get("summary") or "not detected",
                        "key_findings": parsed.get("key_findings") or ["not detected"],
                        "timeline_analysis": parsed.get("timeline_analysis") or ["not detected"],
                        "suspicious_items": parsed.get("suspicious_items") or ["not detected"],
                        "final_conclusion": parsed.get("final_conclusion") or "not detected"
                    }
        except Exception:
            pass

        # Regex/heuristic parsing of free-form text
        import re
        
        summary = "not detected"
        key_findings = []
        timeline_analysis = []
        suspicious_items = []
        final_conclusion = "not detected"

        # Heuristic for summary
        summary_match = re.search(r'(?:1\.\s+Executive\s+Summary|1\.\s+Case\s+Summary|Executive\s+Summary|Case\s+Summary)[:\-\s\n]+(.*?)(?=\n\d\.\s+|\n[A-Z][a-z]+|$)', response_text, re.DOTALL | re.IGNORECASE)
        if summary_match:
            summary = summary_match.group(1).strip()
        else:
            paragraphs = [p.strip() for p in response_text.split('\n\n') if p.strip()]
            if paragraphs:
                summary = paragraphs[0]

        # Heuristic for key_findings
        findings_match = re.search(r'(?:Evidence\s+Analysis|Key\s+Findings|3\.\s+Evidence\s+Overview|7\.\s+Technical\s+Findings)[:\-\s\n]+(.*?)(?=\n\d\.\s+|\n[A-Z][a-z]+|$)', response_text, re.DOTALL | re.IGNORECASE)
        if findings_match:
            bullet_points = re.findall(r'(?:^\s*[\-\*\u2022]\s+|\d+\.\s+)(.*?)$', findings_match.group(1), re.MULTILINE)
            key_findings = [bp.strip() for bp in bullet_points if bp.strip()]
        
        # Heuristic for timeline
        timeline_match = re.search(r'(?:Timeline\s+Reconstruction|Timeline\s+of\s+Events)[:\-\s\n]+(.*?)(?=\n\d\.\s+|\n[A-Z][a-z]+|$)', response_text, re.DOTALL | re.IGNORECASE)
        if timeline_match:
            bullet_points = re.findall(r'(?:^\s*[\-\*\u2022]\s+|\d+\.\s+)(.*?)$', timeline_match.group(1), re.MULTILINE)
            timeline_analysis = [bp.strip() for bp in bullet_points if bp.strip()]

        # Heuristic for suspicious items
        suspicious_match = re.search(r'(?:Suspicious\s+Findings|Suspicious\s+Activity\s+Analysis|Anomalies)[:\-\s\n]+(.*?)(?=\n\d\.\s+|\n[A-Z][a-z]+|$)', response_text, re.DOTALL | re.IGNORECASE)
        if suspicious_match:
            bullet_points = re.findall(r'(?:^\s*[\-\*\u2022]\s+|\d+\.\s+)(.*?)$', suspicious_match.group(1), re.MULTILINE)
            suspicious_items = [bp.strip() for bp in bullet_points if bp.strip()]

        # Heuristic for conclusion
        conclusion_match = re.search(r'(?:Conclusion|Final\s+Conclusion)[:\-\s\n]+(.*?)(?=\n\d\.\s+|\n[A-Z][a-z]+|$)', response_text, re.DOTALL | re.IGNORECASE)
        if conclusion_match:
            final_conclusion = conclusion_match.group(1).strip()

        if not key_findings:
            key_findings = ["not detected"]
        if not timeline_analysis:
            timeline_analysis = ["not detected"]
        if not suspicious_items:
            suspicious_items = ["not detected"]

        return {
            "summary": summary if summary else "not detected",
            "key_findings": key_findings,
            "timeline_analysis": timeline_analysis,
            "suspicious_items": suspicious_items,
            "final_conclusion": final_conclusion if final_conclusion else "not detected"
        }

    def chat(self, case_context, forensic_data, user_message, history=None):
        """Forensic AI Assistant Chat: High-integrity reasoning."""
        start = time.time()

        # Build context
        db_data = self._lookup_mongodb_data(case_context, forensic_data)
        formatted_context = self.build_forensic_context(
            case_id=str(db_data["case"]._id) if db_data["case"] else None,
            case_title=db_data["case"].title if db_data["case"] else None,
            summary=db_data["case"].description if db_data["case"] else None,
            raw_mongodb_data=db_data
        )

        prompt = self.CHAT_QA_PROMPT.format(
            CASE_CONTEXT=formatted_context,
            USER_QUERY=user_message
        )

        messages = []
        for h in (history or []):
            role = "user" if h.get("role") == "user" else "assistant"
            content = h.get("content", "")
            if content.startswith("| Forensic AI Assistant: \"") and content.endswith("\""):
                content = content[len("| Forensic AI Assistant: \""):-1]
            messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": prompt})

        response = None
        if self.claude.is_configured():
            try:
                resp = self.claude.client.messages.create(
                    model=self.model_name,
                    max_tokens=2048,
                    system=self.MASTER_SYSTEM_PROMPT,
                    messages=messages
                )
                response = resp.content[0].text.strip()
            except Exception as e:
                print(f"[Forensic AI] Claude chat error: {e}")

        elapsed = time.time() - start

        if not response:
            response = self._generate_fallback_chat_response(user_message, formatted_context)

        normalized = self.normalize_response(response)

        result = {
            "success": True,
            "response": response,
            "model": self.model_name,
            "latency_ms": round(elapsed * 1000, 1),
            **normalized
        }
        return result

    def _generate_fallback_chat_response(self, user_message, formatted_context):
        from analysis.forensic_knowledge import FORENSIC_ORACLE, RECOVERY_PATTERNS
        msg_lower = user_message.lower()
        matched = []

        # Greetings
        if any(w in msg_lower for w in ["hello", "hi", "hey", "greetings", "good morning", "good evening", "good afternoon"]):
            matched.append(
                "### Hi there! I am the Forensic AI Assistant. 👋\n"
                "I am the core intelligence of this Digital Forensics Investigation System.\n\n"
                "I can answer questions on a huge range of topics including:\n"
                "- 🗂️ **File Systems**: NTFS, FAT32, EXT4, APFS, exFAT, Btrfs, ZFS\n"
                "- 💾 **Storage Forensics**: HDD, SSD, USB, RAID, optical media\n"
                "- 🔍 **File Carving & Recovery**: Signature-based carving, fragmentation, SQLite\n"
                "- 🛡️ **Anti-Forensics Detection**: Time-stomping, log wiping, steganography\n"
                "- 🧠 **Memory Forensics**: Volatility, LSASS, rootkit detection\n"
                "- 📱 **Mobile Forensics**: iOS, Android, Cellebrite, ADB\n"
                "- 🖥️ **Windows Forensics**: Registry, Prefetch, Event Logs, LNK files\n"
                "- 🐧 **Linux/macOS Forensics**: auth.log, bash history, FSEvents\n"
                "- 🌐 **Network Forensics**: PCAP, C2 traffic, email headers\n"
                "- 🦠 **Malware Analysis**: PE analysis, YARA, sandbox, persistence\n"
                "- ☁️ **Cloud/VM Forensics**: AWS, Azure, Docker, VMware\n"
                "- 🔐 **Encryption & Password Analysis**: BitLocker, VeraCrypt, hashcat\n"
                "- ⚔️ **Incident Response**: MITRE ATT&CK, kill chain, IOC hunting\n"
                "- And much more — just ask!\n\n"
                "What would you like to investigate today?"
            )

        # NTFS
        if "ntfs" in msg_lower:
            matched.append(
                "### NTFS File System Recovery Guide\n"
                f"1. **MFT Parsing**: {FORENSIC_ORACLE['NTFS']['recovery_strategy']}\n"
                "2. **Residency Check**: Files <700 bytes are resident and can be extracted directly from the MFT record.\n"
                "3. **Data Run Mapping**: Parse $DATA attribute data runs to locate and rebuild block segments.\n"
                "4. **$LogFile & $UsnJrnl**: Use the change journal and log file to trace deletion events.\n"
                "5. **ADS Detection**: Scan for Alternate Data Streams with `dir /r` or `streams.exe`.\n\n"
                f"*Insight:* {FORENSIC_ORACLE['NTFS']['intelligence']}\n\n"
                "Would you like to inspect $MFT entries or analyze $UsnJrnl for deleted file traces?"
            )

        # FAT32
        if "fat32" in msg_lower or "fat12" in msg_lower or "fat16" in msg_lower:
            matched.append(
                "### FAT32 File System Recovery Guide\n"
                f"1. **Marker Scanning**: {FORENSIC_ORACLE['FAT32']['recovery_strategy']}\n"
                "2. **Directory Entry Reconstruction**: Recover long filename entries (LFN) alongside 8.3 short names.\n"
                "3. **FAT Mirror Backup**: Consult both FAT copies to rebuild cluster allocation chains.\n"
                "4. **Boot Sector Analysis**: Parse the VBR (Volume Boot Record) to get cluster size and FAT offset.\n\n"
                f"*Insight:* {FORENSIC_ORACLE['FAT32']['intelligence']}\n\n"
                "Would you like a file carving scan on the FAT image?"
            )

        # EXT4
        if any(x in msg_lower for x in ["ext4", "ext3", "ext2", "linux filesystem"]):
            matched.append(
                "### EXT4 File System Recovery Guide\n"
                f"1. **Inode Bitmap**: {FORENSIC_ORACLE['EXT4']['recovery_strategy']}\n"
                "2. **Extent Tree Reconstruction**: Parse `eh_depth` and `eh_entries` to map block allocations.\n"
                "3. **jbd2 Journal**: Use `debugfs` or `extundelete` to replay journal transactions for deleted inodes.\n"
                "4. **Orphan List**: Check for orphan inode list in the superblock — deleted but still-open files appear here.\n\n"
                f"*Insight:* {FORENSIC_ORACLE['EXT4']['intelligence']}\n\n"
                "Do you want to run journal replay or scan inode bitmaps for unlinked entries?"
            )

        # APFS
        if "apfs" in msg_lower or "macos filesystem" in msg_lower:
            matched.append(
                "### APFS File System Recovery Guide\n"
                f"1. **Checkpoint Scan**: {FORENSIC_ORACLE['APFS']['recovery_strategy']}\n"
                "2. **CoW Snapshots**: Recover historical file versions from older checkpoints in unallocated space.\n"
                "3. **Encryption**: APFS volumes use per-file encryption — key material may be in the Secure Enclave.\n"
                "4. **Clones**: APFS clones share blocks — identify clone relationships for deduplication forensics.\n\n"
                f"*Insight:* {FORENSIC_ORACLE['APFS']['intelligence']}\n\n"
                "Should we scan container checkpoints or extract snapshot metadata?"
            )

        # SQLite
        if "sqlite" in msg_lower or "database" in msg_lower or "db forensics" in msg_lower:
            matched.append(
                "### SQLite Database Recovery Guide\n"
                f"1. **Header Check**: Verify the `SQLite format 3\\000` magic bytes at offset 0.\n"
                f"2. **Free List**: {FORENSIC_ORACLE['SQLITE']['recovery_strategy']}\n"
                "3. **WAL Parsing**: Check `-wal` and `-journal` files for uncommitted transactions.\n"
                "4. **Overflow Pages**: Reconstruct large records split across overflow pages using page chain.\n"
                "5. **Tools**: `SQLiteSpy`, `DB Browser for SQLite`, `sqliteman`, Autopsy built-in SQLite viewer.\n\n"
                f"*Insight:* {FORENSIC_ORACLE['SQLITE']['intelligence']}\n\n"
                "Which SQLite database are you investigating? (Browser history, SMS, app data, etc.?)"
            )

        # Time-stomping
        if any(x in msg_lower for x in ["time-stomp", "timestomp", "time stomp", "timestamp manipulation"]):
            matched.append(
                "### Anti-Forensic Time-Stomping Detection\n"
                f"1. **$SIA vs $FNA**: {FORENSIC_ORACLE['TIME_STOMPING']['detection']}\n"
                "2. **Sequence Number Anomaly**: If creation timestamp in $SIA is newer than $FNA, timestomping occurred.\n"
                "3. **USN Journal Cross-Reference**: `$UsnJrnl:$J` records true modification events even after stomping.\n"
                "4. **Tool**: `MFT2CSV` or Autopsy's Timeline to surface timestamp discrepancies.\n\n"
                f"*Insight:* {FORENSIC_ORACLE['TIME_STOMPING']['intelligence']}\n\n"
                "Would you like a full MFT attribute dump for timeline reconstruction?"
            )

        # File carving / signatures
        if any(x in msg_lower for x in ["carv", "signature", "pattern", "header", "magic byte"]):
            patterns_str = ""
            for pat in RECOVERY_PATTERNS:
                patterns_str += f"| **{pat['type']}** | `{pat['signature']}` | {pat['recovery']} |\n"
            matched.append(
                "### File Carving & Signature Recovery Guide\n"
                "| File Type | Hex Header | Recovery Strategy |\n"
                "| :--- | :--- | :--- |\n" + patterns_str + "\n"
                "**Tools**: `PhotoRec`, `Scalpel`, `Foremost`, `bulk_extractor`\n\n"
                "Should we initiate a sector-by-sector carving scan for specific file signatures?"
            )

        if not matched:
            matched.append(
                f"### Forensic Intelligence Engine (FIE-LLM) — Answering query\n"
                f"Analyzing forensic case data. Case: {formatted_context}\n\n"
                f"I am the Forensic Intelligence Engine. Let me know what specific system/file attributes you need guidance on."
            )

        return "\n\n---\n\n".join(matched)

    def classify_files(self, forensic_data):
        """Classify files using real AI reasoning or mock fallback."""
        if not self._has_submitted_evidence(forensic_data):
            return self._insufficient_response("Insufficient evidence: no forensic data was provided for classification.")
        prompt = f"Classify the following forensic artifacts by threat level (Critical, Suspicious, Benign). For each, explain why in one sentence:\n\n{forensic_data}"
        response = self._call_claude(prompt, system_prompt=self.MASTER_SYSTEM_PROMPT)
        if not response:
            response = self._generate_fallback_classification_text(forensic_data)

        normalized = self.normalize_response(response)
        
        return {
            "success": True,
            "classification": response,
            "response": response,
            **normalized
        }

    def _extract_file_names(self, data):
        """Pull real file names from forensic data structures for honest reporting."""
        parsed = None
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
            except Exception:
                return []
        elif isinstance(data, (list, dict)):
            parsed = data
        if isinstance(parsed, dict):
            for key in ("evidence", "files", "recovered_files", "items", "records"):
                lst = parsed.get(key)
                if isinstance(lst, list):
                    for item in lst:
                        if isinstance(item, dict):
                            name = item.get("file_name") or item.get("name") or item.get("original_name")
                            if name:
                                return [str(name)]
            name = parsed.get("file_name") or parsed.get("name") or parsed.get("original_name")
            if name:
                return [str(name)]
        elif isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    name = item.get("file_name") or item.get("name") or item.get("original_name")
                    if name:
                        return [str(name)]
        return []

    def _has_submitted_evidence(self, forensic_data):
        """Whether any real forensic data was submitted for analysis."""
        if self._extract_file_names(forensic_data):
            return True
        data_str = forensic_data if isinstance(forensic_data, str) else json.dumps(forensic_data, default=str)
        stripped = data_str.strip()
        return bool(stripped and stripped not in ("[]", "{}", "null", "None", ""))

    def _generate_fallback_classification_text(self, forensic_data):
        """Honest offline fallback: no classification is produced; only registered files are echoed."""
        names = self._extract_file_names(forensic_data)
        if names:
            evidence_block = "\n".join(f"- {name}" for name in names)
            evidence_note = f"\nFiles present in the submitted data:\n{evidence_block}"
        else:
            evidence_note = "\nNo file metadata was present in the submitted data."

        return f"""1. Case Summary: Offline File Classification
The AI classification engine is offline or unreachable, so no threat classification was produced for this evidence.
2. Evidence Analysis:
No classifications were generated. File-level metadata was not scored.{evidence_note}
3. Timeline Reconstruction:
No timeline was reconstructed because no classification was performed.
4. Suspicious Findings:
No findings were generated.
5. Conclusion:
Insufficient evidence: the AI classification engine is unavailable. Re-run this analysis once the forensic AI service is reachable.
6. Recommendations:
Verify the forensic AI service configuration and retry the classification."""

    def detect_anomalies(self, forensic_data):
        """Detect anomalies using AI or fallback."""
        if not self._has_submitted_evidence(forensic_data):
            return self._insufficient_response("Insufficient evidence: no forensic data was provided for anomaly detection.")
        prompt = self.ANOMALY_DETECTION_PROMPT.format(FORENSIC_DATA=forensic_data)
        response = self._call_claude(prompt, system_prompt=self.MASTER_SYSTEM_PROMPT)
        if not response:
            response = self._generate_fallback_anomalies_text(forensic_data)

        normalized = self.normalize_response(response)
        
        return {
            "success": True,
            "anomalies": response,
            "response": response,
            **normalized
        }

    def _generate_fallback_anomalies_text(self, forensic_data):
        """Honest offline fallback: no anomaly assessment is produced without AI analysis."""
        return """1. Case Summary: Offline Anomaly Detection
The AI detection engine is offline or unreachable, so no anomaly assessment was produced for this evidence.
2. Evidence Analysis:
No anomalies were scored against the submitted evidence.
3. Timeline Reconstruction:
No timeline was reconstructed because no anomaly scan was performed.
4. Suspicious Findings:
No findings were generated.
5. Conclusion:
Insufficient evidence: the AI anomaly detection engine is unavailable. Re-run this analysis once the forensic AI service is reachable.
6. Recommendations:
Verify the forensic AI service configuration and retry anomaly detection."""

    def _verify_evidence(self, db_data):
        """Gate: confirm real evidence (with hashes and timestamps) exists before AI analysis."""
        evidence = (db_data or {}).get("evidence") or []
        if evidence:
            missing = [getattr(ev, "file_name", "unknown") for ev in evidence if not getattr(ev, "hash_sha256", None)]
            if not missing:
                return {"verified": True, "reason": ""}
            return {
                "verified": False,
                "reason": f"Insufficient evidence: {len(missing)} evidence record(s) lack file hashes.",
            }

        tool_data = (db_data or {}).get("tool_data")
        entries = []
        if isinstance(tool_data, dict):
            for key in ("evidence", "files", "recovered_files", "items"):
                if isinstance(tool_data.get(key), list):
                    entries = tool_data[key]
                    break
        elif isinstance(tool_data, list):
            entries = tool_data

        for item in entries:
            if isinstance(item, dict) and (item.get("hash_sha256") or item.get("file_name")):
                return {"verified": True, "reason": ""}

        return {"verified": False, "reason": "Insufficient evidence: no evidence with file hashes was provided for this case."}

    def _insufficient_response(self, reason):
        """Structured honest response returned when evidence cannot be verified."""
        return {
            "success": False,
            "report": reason,
            "response": reason,
            "model": self.model_name,
            "summary": reason,
            "key_findings": ["No evidence available for analysis."],
            "timeline_analysis": ["No timeline available."],
            "suspicious_items": ["No suspicious items analyzed."],
            "final_conclusion": reason,
            "insufficient_evidence": True,
        }

    def generate_report(self, case_context, forensic_data, ai_findings):
        """Generate a forensic report using AI or a structured fallback."""
        db_data = self._lookup_mongodb_data(case_context, forensic_data)
        formatted_context = self.build_forensic_context(
            case_id=str(db_data["case"]._id) if db_data["case"] else None,
            case_title=db_data["case"].title if db_data["case"] else None,
            summary=db_data["case"].description if db_data["case"] else None,
            raw_mongodb_data=db_data
        )

        # Evidence verification gate: never produce an AI report without verifiable evidence.
        verification = self._verify_evidence(db_data)
        if not verification["verified"]:
            return self._insufficient_response(verification["reason"])

        prompt = self.FORENSIC_REPORT_GENERATION_PROMPT.format(
            FORMATTED_FORENSIC_CONTEXT=formatted_context
        )

        if ai_findings:
            prompt += f"\n\nAdditional AI Findings to include:\n{ai_findings}"

        response_text = self._call_claude(prompt, system_prompt=self.MASTER_SYSTEM_PROMPT)
        
        if not response_text:
            response_text = self._generate_fallback_report_text(formatted_context, ai_findings)

        normalized = self.normalize_response(response_text)
        
        result = {
            "success": True,
            "report": response_text,
            "response": response_text,
            "model": self.model_name,
            **normalized
        }
        return result

    def _generate_fallback_report_text(self, formatted_context, ai_findings=None):
        """Honest offline report: reflects only registered evidence; makes no recovery or analysis claims."""
        try:
            ctx = json.loads(formatted_context)
        except Exception:
            ctx = {}

        case_title = ctx.get("case_title") or "Unknown Investigation"
        case_id = ctx.get("case_id") or "N/A"
        summary = ctx.get("summary") or "No case description provided."
        
        evidence_str = ""
        evidence_items = ctx.get("evidence") or []
        if evidence_items:
            for ev in evidence_items:
                evidence_str += f"- {ev.get('file_name')} ({ev.get('file_type')}) - Status: {ev.get('status')}\n"
        else:
            evidence_str = "- No evidence items registered in this case.\n"

        timeline_str = ""
        timeline_items = ctx.get("timeline") or []
        if timeline_items:
            for tl in timeline_items:
                timeline_str += f"- {tl.get('timestamp')}: {tl.get('event')}\n"
        else:
            timeline_str = "- No timeline events registered.\n"

        hash_items = [ev.get("file_hash") for ev in evidence_items if ev.get("file_hash")]
        if hash_items:
            hash_str = "\n".join(f"- {h}" for h in hash_items)
        else:
            hash_str = "- No file hashes are registered for the evidence in this case."

        findings_text = ""
        if ai_findings:
            findings_text = f"\n\nAI Findings context:\n{ai_findings}"

        report = f"""1. Executive Summary
This report summarizes the digital forensic case {case_title} (ID: {case_id}) using only the evidence metadata registered in the system. The forensic AI service is offline or unreachable, so this report makes no recovery, scanning, or analysis claims beyond the registered data below.

2. Case Details
- Case Identifier: {case_id}
- Case Title: {case_title}
- Description: {summary}
- Investigation Status: Under active review

3. Evidence Overview
The following digital assets are registered in this case:
{evidence_str}
4. File Recovery Analysis
No recovery or sector scan was executed during report generation. Only registered evidence records are reflected:
{evidence_str}
5. Timeline of Events
Registered timeline events:
{timeline_str}
6. Suspicious Activity Analysis
No automated anomaly analysis was performed because the forensic AI service is offline. No suspicious activity findings were generated.{findings_text}

7. Technical Findings
Registered file hashes:
{hash_str}
Partition and metadata inspection was not performed during this offline report.

8. Final Conclusion
The case contains the evidence records listed above. This report was generated in offline mode and asserts no file recovery, hash computation, or anomaly detection results.

9. Recommendations for Investigators
1. Confirm the forensic AI service is online before requesting a full AI analysis report.
2. Verify registered evidence hashes through independent acquisition tooling.
3. Validate chain-of-custody logs for all target devices."""

        return report
