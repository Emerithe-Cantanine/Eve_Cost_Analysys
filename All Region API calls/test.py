import requests
import json

region_id = 10000043
page = 1
url = f"https://esi.evetech.net/latest/markets/{region_id}/orders/?datasource=tranquility&order_type=all&page={page}"
response = requests.get(url)

print("Status:", response.status_code)

if response.status_code == 200:
    data = response.json()
    with open(f"{region_id}.txt", "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=2))
        print(f"Data written to {region_id}.txt")
else:
    print("No data found.")
