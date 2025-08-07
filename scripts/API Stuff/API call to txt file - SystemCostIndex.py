import requests
import json

# API endpoint
url = "https://esi.evetech.net/latest/industry/systems/?datasource=tranquility"

# Call the API
try:
    response = requests.get(url)
    response.raise_for_status()  # Raise exception for HTTP errors
    data = response.json()

    # Save the JSON data to a text file
    with open("SystemCostIndexes.txt", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    print("Data saved to SystemCostIndexes.txt")

except requests.RequestException as e:
    print(f"API request failed: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
