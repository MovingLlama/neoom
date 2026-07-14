import urllib.request
import json

def query_site_state():
    ip = "192.168.20.159"
    key = "sk_beaam_GFw7vnDGnYzDrXvtSWvevba1yoHcSQT4"
    url = f"http://{ip}/api/v1/site/state"
    
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {key}")
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    query_site_state()
