import urllib.request
import json

def query_cloud_sites():
    token = "sk_connect_5ivdsanPcd96YfdwSgBi1XrkD73akhLj"
    url = "https://api.ntuity.io/v1/sites"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    query_cloud_sites()
