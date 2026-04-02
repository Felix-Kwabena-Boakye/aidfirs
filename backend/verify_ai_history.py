import requests
import json

BASE_URL = 'http://127.0.0.1:8000/api'

def test_ai_history():
    print("=== Testing AI Assistant History ===")
    
    # 1. Login to get token
    login_url = f"{BASE_URL}/accounts/login/"
    login_data = {"username": "admin", "password": "admin"}
    
    try:
        response = requests.post(login_url, json=login_data)
        response.raise_for_status()
        token = response.json()['access']
        print("Logged in successfully.")
    except Exception as e:
        print(f"Login failed: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    # Try with and without trailing slash
    urls_to_try = [
        f"{BASE_URL}/analysis/chat/",
        f"{BASE_URL}/analysis/chat"
    ]
    
    for chat_url in urls_to_try:
        print(f"\nTrying URL: {chat_url}")
        history = []
        data = {
            "case_context": "Test Case",
            "forensic_data": "None",
            "message": "My name is Antigravity.",
            "history": history
        }
        
        try:
            response = requests.post(chat_url, json=data, headers=headers)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                bot_response = response.json()['response']
                print(f"Assistant: {bot_response}")
                
                # Test History
                history.append({"role": "user", "content": "My name is Antigravity."})
                history.append({"role": "assistant", "content": bot_response})
                
                print("\nSending second message: 'What is my name?'")
                data["message"] = "What is my name?"
                data["history"] = history
                
                response2 = requests.post(chat_url, json=data, headers=headers)
                print(f"Status Code 2: {response2.status_code}")
                if response2.status_code == 200:
                    bot_response2 = response2.json()['response']
                    print(f"Assistant 2: {bot_response2}")
                    if "Antigravity" in bot_response2:
                        print("\nSUCCESS: AI remembered the name!")
                    else:
                        print("\nFAILURE: AI forgot the name.")
                    return
            else:
                print(f"Headers: {response.headers}")
                print(f"Body: {response.text}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    test_ai_history()
