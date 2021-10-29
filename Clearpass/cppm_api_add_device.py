import requests
import json
import pprint
import csv

cppm_base = "https://clearpasspm.jsd.ad:443/api"


def gen_cp_token():

    # GENERATE TOKEN
    authURL = cppm_base + "/oauth"
    clientID = "cppmAPI"
    clientSecret = "SECRET"
    user = "test"
    pwd = "test123"
    authBody = {"grant_type": "client_credentials",
                "client_id": clientID,
                "client_secret": clientSecret,
                "username": user,
                "password": pwd}
    rAuth = requests.post(authURL, data=authBody, verify=False)
    rAuthJson = rAuth.json()
    token = rAuthJson[u'access_token']
    tokenType = rAuthJson[u'token_type']
    headToken = tokenType + ' ' + token
    return headToken
    # END GENERATE TOKEN


def add_cp_device(mac_addr, site, token):

    url = cppm_base + "/device?change_of_authorization=true"
    headers = {'Authorization': token, 'Content-Type': 'application/json'}
    device = {"enabled": True,
              "expire_time": 0,
              "mac": mac_addr,
              "notes": "",
              "role_id": 2,
              "visitor_name": mac_addr,
              "airgroup_enable": "1",
              "airgroup_shared": "1",
              "airgroup_shared_location": "AP-Group=" + site}
    devicejson = json.dumps(device)
    pprint.pprint(devicejson)
    makedevice = requests.post(url, headers=headers, data=devicejson, verify=False)
    pprint.pprint(makedevice.json())

# "Login" to clearpass
key = gen_cp_token()

with open('apgroup_device.csv', 'rb') as csvfile:
    csv_reader = csv.reader(csvfile)
    for row in csv_reader:
        # Where the first entry in the row is MAC and second entry is site number
        add_cp_device(row[0], row[1], key)


