import os
import random
import requests
import uuid
import time
import datetime

# Function to calculate current time in milliseconds
def current_milli_time():
    return round(time.time() * 1000)

# List of ship names
shipNames = ["USS Alabama", "USS Alaska", "USS Albany", "USS Alexandria", "USS Arlington",
          "USS Maine", "USS Maryland", "USS Constitution", "USS Green Bay", "USS Hawaii"]

# List of logger names
loggerNames = ['UNHJHC-wibl-' + str(i) for i in range(10)]

# Endpoint for the manager
manager_endpoint = os.getenv('MANAGEMENT_URL', 'http://host.docker.internal:5000')

# Function to initialize metadata
def main():
    print("Starting from scratch")

    json_array = []

    # Loop to create random metadata entries
    for i in range(1000):
        fileid = str(uuid.uuid4())
        fileid_wibl = fileid + '.wibl'

        logger = loggerNames[int(i / 100)]
        platform = shipNames[int(i / 100)]
        observations = random.randint(75000, 125000)
        soundings = random.randint(8000, 12000)

        iso_startdate = time.time() - (86400 * i)
        iso_enddate = random.randint(12 * 60 * 60, 24 * 60 * 60) + iso_startdate
        iso_startdate = datetime.datetime.fromtimestamp(iso_startdate).isoformat()
        iso_enddate = datetime.datetime.fromtimestamp(iso_enddate).isoformat()

        status = 1

        json_object = {
            'url': (manager_endpoint + '/wibl/' + fileid_wibl),
            'size': (observations / 10000.0),
            'logger': logger,
            'platform': platform,
            'observations': observations,
            'soundings': soundings,
            'startTime': iso_startdate,
            'endTime': iso_enddate,
            'status': status,
            'messages': '',
        }
        json_array.append(json_object)

        # Sending requests to create metadata entries
        try:
            response = requests.post(manager_endpoint + '/wibl/' + fileid_wibl, json={'size': observations / 10000.0})
            response.raise_for_status()
            response = requests.put(manager_endpoint + '/wibl/' + fileid_wibl, json=json_object)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}. Skipping this entry...")
            continue

        # Creating JSON object for geojson entry
        fileid_geojson = fileid + '.geojson'
        json_object_geojson = {
            'url': (manager_endpoint + '/geojson/' + fileid_geojson),
            'size': (observations / 10000.0),
            'logger': logger,
            'observations': observations,
            'soundings': soundings,
            'status': status,
            'messages': ''
        }

        try:
            response = requests.post(manager_endpoint + '/geojson/' + fileid_geojson,
                                     json={'size': observations / 10000.0})
            response.raise_for_status()
            response = requests.put(manager_endpoint + '/geojson/' + fileid_geojson, json=json_object_geojson)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}. Skipping this entry...")

    print("Initialization complete.")

if __name__ == "__main__":
    main()
