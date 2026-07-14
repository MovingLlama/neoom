import urllib.request
import json

def query_cloud():
    token = "sk_connect_5ivdsanPcd96YfdwSgBi1XrkD73akhLj"
    site_id = "b60bf800-c509-4c10-9a7e-bc05b90824a1"
    
    # 1. Query Site
    url_site = f"https://api.ntuity.io/v1/sites/{site_id}"
    req_site = urllib.request.Request(url_site)
    req_site.add_header("Authorization", f"Bearer {token}")
    
    try:
        with urllib.request.urlopen(req_site) as response:
            data = json.loads(response.read().decode())
            print("--- CLOUD SITE DETAILS ---")
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error querying site: {e}")
        
    # 2. Query Flow
    url_flow = f"https://api.ntuity.io/v1/sites/{site_id}/energy-flow/latest"
    req_flow = urllib.request.Request(url_flow)
    req_flow.add_header("Authorization", f"Bearer {token}")
    
    try:
        with urllib.request.urlopen(req_flow) as response:
            data = json.loads(response.read().decode())
            print("\n--- CLOUD ENERGY FLOW LATEST ---")
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error querying flow: {e}")

if __name__ == "__main__":
    query_cloud()
