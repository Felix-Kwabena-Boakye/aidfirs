import sys
import os

def test_ai_assistant():
    print("Testing ForensicAIAssistant...")
    # Add current directory to path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    try:
        from analysis.assistant import ForensicAIAssistant
        assistant = ForensicAIAssistant()
        
        # Test default greeting response
        res = assistant.chat("Test case context", "Test forensic data", "Hello!")
        assert res["success"] is True
        assert "Forensic AI Assistant" in res["response"]
        assert "FAT32" in res["response"]
        
        # Test NTFS keyword
        res_ntfs = assistant.chat("Test case context", "Test forensic data", "Tell me about NTFS recovery")
        assert "NTFS File System Recovery Guide" in res_ntfs["response"]
        
        # Test FAT32 keyword
        res_fat = assistant.chat("Test case context", "Test forensic data", "How to scan FAT32?")
        assert "FAT32 File System Recovery Guide" in res_fat["response"]
        
        # Test EXT4 keyword
        res_ext = assistant.chat("Test case context", "Test forensic data", "Show EXT4 recovery strategy")
        assert "EXT4 File System Recovery Guide" in res_ext["response"]
        
        # Test APFS keyword
        res_apfs = assistant.chat("Test case context", "Test forensic data", "APFS volume recovery")
        assert "APFS File System Recovery Guide" in res_apfs["response"]
        
        # Test SQLite keyword
        res_sqlite = assistant.chat("Test case context", "Test forensic data", "Can you read deleted SQLite records?")
        assert "SQLite Database Recovery Guide" in res_sqlite["response"]
        
        # Test time-stomping keyword
        res_ts = assistant.chat("Test case context", "Test forensic data", "Check for time-stomping anomaly")
        assert "Anti-Forensic Time-Stomping Detection" in res_ts["response"]
        
        # Test carve signature keyword
        res_carve = assistant.chat("Test case context", "Test forensic data", "Carve files from raw partition")
        assert "File Carving & Signature Recovery Guide" in res_carve["response"]
        
        print("All test assertions passed successfully!")
    except Exception as e:
        print("Test failed with exception:", str(e))
        sys.exit(1)

if __name__ == "__main__":
    test_ai_assistant()
