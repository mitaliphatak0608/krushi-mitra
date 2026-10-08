import requests

def test_simulator():
    url = "http://localhost:8000/sms/simulator"
    
    # Send START
    res = requests.post(url, json={"from": "+91-DEMO-USER", "message": "START"})
    print("START response:", res.status_code, res.text)
    
test_simulator()
