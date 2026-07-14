import urllib.request
import json

def query_states():
    ip = "192.168.20.159"
    key = "sk_beaam_GFw7vnDGnYzDrXvtSWvevba1yoHcSQT4"
    thing_id = "0b2c0779-f3d8-416e-94d3-fbad9fee70ce"
    url = f"http://{ip}/api/v1/things/{thing_id}/states"
    
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {key}")
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    query_states()
