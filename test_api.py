import asyncio
import aiohttp
import json
import os

async def main():
    cloud_token = "sk_connect_5ivdsanPcd96YfdwSgBi1XrkD73akhLj"
    beaam_key = "sk_beaam_GFw7vnDGnYzDrXvtSWvevba1yoHcSQT4"
    beaam_ip = "192.168.20.159"

    async with aiohttp.ClientSession() as session:
        # 1. Test Cloud API - Get Sites
        print("--- CLOUD API: SITES ---")
        try:
            async with session.get("https://api.ntuity.io/v1/sites", headers={"Authorization": f"Bearer {cloud_token}"}) as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    sites = await resp.json()
                    print(json.dumps(sites, indent=2))
                    if isinstance(sites, list) and len(sites) > 0:
                        site_id = sites[0].get("id") or sites[0].get("siteId")
                    elif isinstance(sites, dict) and "items" in sites and len(sites["items"]) > 0:
                        site_id = sites["items"][0].get("id") or sites["items"][0].get("siteId")
                    elif isinstance(sites, dict) and "data" in sites and len(sites["data"]) > 0:
                        site_id = sites["data"][0].get("id") or sites["data"][0].get("siteId")
                    else:
                        site_id = None
                        
                    if site_id:
                        print(f"\n--- CLOUD API: SITE DETAILS ({site_id}) ---")
                        async with session.get(f"https://api.ntuity.io/v1/sites/{site_id}", headers={"Authorization": f"Bearer {cloud_token}"}) as r_site:
                            print(json.dumps(await r_site.json(), indent=2))
                            
                        print(f"\n--- CLOUD API: ENERGY FLOW LATEST ({site_id}) ---")
                        async with session.get(f"https://api.ntuity.io/v1/sites/{site_id}/energy-flow/latest", headers={"Authorization": f"Bearer {cloud_token}"}) as r_flow:
                            print(json.dumps(await r_flow.json(), indent=2))
                else:
                    print(await resp.text())
        except Exception as e:
            print(f"Error fetching cloud API: {e}")

        # 2. Test Local BEAAM API - Get Configuration
        print("\n--- LOCAL API: CONFIGURATION ---")
        try:
            async with session.get(f"http://{beaam_ip}/api/v1/site/configuration", headers={"Authorization": f"Bearer {beaam_key}"}, timeout=10) as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    config = await resp.json()
                    # We just want to extract Heat Pumps or Generic Devices to find the keys
                    things = config.get("things", {})
                    for t_id, t_data in things.items():
                        if "HEAT" in t_data.get("type", "").upper() or "GENERIC" in t_data.get("type", "").upper():
                            print(f"\nFound Thing: {t_id} (Type: {t_data.get('type')})")
                            print("DataPoints:")
                            for dp_id, dp_data in t_data.get("dataPoints", {}).items():
                                print(f"  - Key: {dp_data.get('key')}, Controllable: {dp_data.get('controllable')}, Type: {dp_data.get('dataType')}")
                else:
                    print(await resp.text())
        except Exception as e:
            print(f"Error fetching local API: {e}")

if __name__ == "__main__":
    asyncio.run(main())
