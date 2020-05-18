import argparse
import requests
from requests.exceptions import Timeout
import logging
import os
import sys
from urllib.parse import urlencode
import json
import urllib3

# ignore warning about NGDC-signed certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main(args):
    token = get_token(args.username, args.password, args.server)

    for service in target_services:
        try:
            service_info = get_service_info(token, args.server, service['name'])
        except Exception as e:
            logging.warning(f"unable to get service info for {service['name']}")
            continue

        service_info['properties']['antialiasingMode'] = service['antialiasing']

        try:
            update_service(token, args.server, service, service_info)
        except Exception as e:
            logging.error(f"failed to enable WMS on service {service}")
            continue


def get_token(username, password, servername):
    url = f"https://{servername}:6443/arcgis/admin/generateToken"
    params = urlencode({'username': username, 'password': password, 'client': 'requestip', 'f': 'json'})
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    r = requests.post(url, headers=headers, data=params, verify=False)
    if r.status_code != 200:
        raise Exception("Error while fetching tokens from admin URL. Please check the URL and try again.")
    data = r.json()

    if not assert_json_success(data):
        # logging.warning(data)
        raise Exception("Error: response object represents an error.")

    return data['token']


def get_service_info(token, servername, servicename):
    url = f"https://{servername}:6443/arcgis/admin/services/{servicename}.MapServer"
    params = urlencode({'token': token, 'f': 'json'})
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "application/json"}

    r = requests.post(url, headers=headers, data=params, verify=False)
    if r.status_code != 200:
        raise Exception("Error while fetching tokens from admin URL. Please check the URL and try again.")
    data = r.json()

    if not assert_json_success(data):
        # logging.warning(data)
        raise Exception("Error: response object represents an error.")

    return data


def update_service(token, servername, servicename, serviceinfo):
    logging.info(f'enabling WMS on service {servicename}...')
    # print(serviceinfo)
    url = f"https://{servername}:6443/arcgis/admin/services/{servicename}.MapServer/edit"
    params = urlencode({'token': token, 'f': 'json', 'service': json.dumps(serviceinfo)})
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "application/json"}

    r = requests.post(url, headers=headers, params=params, verify=False)
    if r.status_code != 200:
        raise Exception(f"Error while updating service properties for {servicename}")
    data = r.json()
    if not assert_json_success(data):
        # logging.warning(data)
        raise Exception("Error: response object represents an error.")


def assert_json_success(json):
    """checks that the provided JSON object is not an error object"""
    if 'status' in json and json['status'] == "error":
        return False
    else:
        return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    target_services = [
        {"name": "GulfDataAtlas/NMFS_BottomLongline_Stations", "antialiasing": "Fastest"}
    ]

    # setup command line arguments
    arg_parser = argparse.ArgumentParser(
        description="""Sets the antialiasingMode on the specified list of services."""
    )

    arg_parser.add_argument("username", help="user name")
    arg_parser.add_argument("password", help="password")
    arg_parser.add_argument("server", help="fully qualified server name")
    args = arg_parser.parse_args()

    main(args)
