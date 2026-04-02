import requests

def test_ai_assistant():
    print("Testing ForensicAIAssistant...")
    try:
        from backend.analysis.assistant import ForensicAIAssistant
        assistant = ForensicAIAssistant()
        res = assistant.chat("Test case context", "Test forensic data", "What do you see?")
        print("Success:", res["success"])
        if res["success"]:
            print("Response:", res["response"][:100] + "...")
        else:
            print("Error:", res.get("error"))
    except Exception as e:
        print("Test failed with exception:", str(e))

if __name__ == "__main__":
    test_ai_assistant()
