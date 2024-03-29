"""
By: Thomas Ackerly

This file strives to initalize our local wibl-manager with metadata (not data) so it is
populated for local testing.
"""

import os, unittest
import random
import requests
import uuid
import time, datetime, json

#assume that we call this somewhere in the docker compose, and the file is already up?
#do the post then put?



def current_milli_time():
    return round(time.time() * 1000)

"""
What do we want to randomize:
filename
Logger name
ship name/platform - logger and ship should correlate to one another?
# of observations
# of soundings
start time - must be in specified format
end time - must be in specified format, and must come after end time
"""

#should include some with an unknown ship?
shipNames = ["USS Alabama", "USS Alaska", "USS Albany", "USS Alexandria", "USS Arlington",
          "USS Maine", "USS Maryland", "USS Constitution", "USS Green Bay", "USS Hawaii"]

loggerNames = []
for i in range(10):
    loggerNames.append('UNHJHC-wibl-' + str(i))

manager_endpoint = os.getenv('MANAGEMENT_URL', 'http://172.17.0.1:5000')

"""
def load_from_file(filename: str):
    
    return 0
"""

def main():
    
    """
    Need to check a couple things:
        1 - need to verify if the database is already initialized: Try this with a special 
        metadata entry that is not randomly generated. If it's present, don't initialize?
        2 - if we do not find the special metadata entry, we should check for a file that 
        we can use to initialize the database. Written in json?
        3 - initialize randomly
    """

    #1: Not the best solution tbh
    response = requests.get(manager_endpoint + '/wibl/special-boy')
    print(response.status_code)
    if response is not None and response.status_code == 200:
        print("Found special entry, data should be loaded")
        exit(1)

    #2: Check to see if there is a data file that we can use to load the server
    """
    check_file = os.path.isfile('metadata.json')
    if check_file:
        print('Existing json file, loading manager from that.')
        load_from_file('metadata.json')
        exit(1)
    """
        
    #3:
    #first, place special metadata file

    print("starting from scratch")
    #equests.delete(manager_endpoint + '/wibl/all')

    manual_uuid = "special-boy" #uuid in manager is simply a string
    response = requests.post(manager_endpoint + '/wibl/' + manual_uuid, json={'size': 10.4})
    json_object = {
        'url' : manager_endpoint + '/wibl/' + manual_uuid,
        'size' : 10.4,
        'logger': 'UNHJHC-wibl-11', 'platform': 'USCGC Healy',
        'observations': 100232, 'soundings': 8023,
        'startTime': '2023-01-23T12:34:45.142',
        'endTime': '2023-01-24T01:45:23.012',
        'status': 1
    }

    json_array = []
    json_array.append(json_object)

    for i in range(10):
        file_name = 'wibl_' + str(i)
        fileid = str(uuid.uuid4())

        logger = loggerNames[int(i/100)]
        platform = shipNames[int(i/100)]
        observations = random.randint(75000, 125000)
        soundings = random.randint(8000, 12000)

        #end date would be something like 12 to 24 hrs in advance?
        #24*60*60*1000?
        iso_startdate: int = time.time() - (86400 * i)
        iso_enddate = random.randint(12*60*60, 24*60*60) + iso_startdate
        iso_startdate = datetime.datetime.fromtimestamp(iso_startdate).isoformat()
        iso_enddate = datetime.datetime.fromtimestamp(iso_enddate).isoformat()

        status = 1

        json_object = {
            'url' : (manager_endpoint + '/wibl/' + fileid),
            'size' : (observations/10000.0),
            'logger' : logger, 'platform' : platform,
            'observations' : observations, 'soundings' : soundings,
            'startTime' : iso_startdate, 'endTime' : iso_enddate,
            'status' : status
        }
        print(json_object)
        json_array.append(json_object)

        response = requests.post(manager_endpoint + '/wibl/' + fileid, json={'size': observations/10000.0})
        
        if response is None:
            print('Response from manager for post to' + manager_endpoint + '/wibl/' + fileid
                  + ' was None. Aborting.')
            exit(1)
        if response.status_code != 201:
            print('Response from manager for put to ' + manager_endpoint + '/wibl/' + fileid
                  + ' returned an unexpected value ' + response.status_code + ', expecting 201. Aborting.')
            exit(1)

        response = requests.put(manager_endpoint + '/wibl/' + fileid,
                                    json=json_object)
        if response is None:
            exit(1)
        if response.status_code != 201:
            print('Response from manager for put to ' + manager_endpoint + '/wibl/' + fileid
                  + ' returned an unexpected value ' + response.status_code + ', expecting 201. Aborting.')
            exit(1)

    """
    json_string = json.dumps([ob.__dict__ for ob in json_array])
    with open('metadata.json', 'w') as file:
        file.write(json_string)
    """

    return 0
    
if __name__ == "__main__":
    main()
