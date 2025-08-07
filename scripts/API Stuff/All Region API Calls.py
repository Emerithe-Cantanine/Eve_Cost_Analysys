import requests
import time
import json

BASE_URL = "https://esi.evetech.net/latest/markets/{}/orders/?datasource=tranquility&order_type=all&page={}"
REGION_START = 10000001
REGION_END = 10000070
SLEEP_TIME = 0.2  # Adjust as needed to avoid hitting rate limits

def fetch_region_data(region_id):
    page = 1
    with open(f"{region_id}.txt", "w", encoding="utf-8") as f:
        while True:
            url = BASE_URL.format(region_id, page)
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    f.write(json.dumps(data) + "\n")
                    # print(f"Region {region_id} - Page {page} downloaded.")
                    page += 1
                    time.sleep(SLEEP_TIME)
                elif response.status_code == 404 and "Requested page does not exist!" in response.text:
                    print(f"Region {region_id} complete at page {page - 1}.")
                    break
                else:
                    print(f"Unexpected error for region {region_id} page {page}: {response.status_code}")
                    break
            except Exception as e:
                print(f"Exception on region {region_id} page {page}: {e}")
                break

def main():
    for region_id in range(REGION_START, REGION_END + 1):
        if region_id == 24 or region_id == 26: continue
        print(f"Fetching data for region {region_id}...")
        fetch_region_data(region_id)

if __name__ == "__main__":
    main()
