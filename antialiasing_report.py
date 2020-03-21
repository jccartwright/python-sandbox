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


def main():
    # setup command line arguments
    arg_parser = argparse.ArgumentParser(
        description="""Enables the WMS extension on the specified MapServer instance. If a folder name is provided, 
        all map services within that folder will be enabled"""
    )
    arg_parser.add_argument("username", help="user name")
    arg_parser.add_argument("password", help="password")
    arg_parser.add_argument("server", help="fully qualified server name")
    arg_parser.add_argument("-n", "--name", help="folder name or relative path to the map service")
    arg_parser.add_argument("-t", '--target_type', default='service', help="indicates folder or service. defaults to service")
    arg_parser.add_argument("-r", "--report", help="only report on whether WMS is enabled", action="store_true")
    arg_parser.add_argument("-p", "--port", default="6443", help="server port")
    args = arg_parser.parse_args()

    target_type = args.target_type
    if target_type == 'folder' and args.name:
        services = get_service_names(args.server, args.name)
    elif args.name:
        services = [args.name]
    else:
        # no name given, report on all services
        print('reporting on all services')
        services = []
        get_running_services(args.server, services)

    token = get_token(args.username, args.password, args.server)

    server = f"{args.server}:{args.port}"

    for service in services:
        try:
            service_info = get_service_info(token, server, service)
        except Exception as e:
            logging.warning(f"unable to get service info for {service}")
            continue
        # print(json.dumps(service_info, indent=2))
        print(f"{service}: antialiasing set to {service_info['properties']['antialiasingMode']}")


def get_running_services(hostname='gis.ngdc.noaa.gov', services=[], folder=None, type='MapServer'):
    base_url = f"https://{hostname}/arcgis/rest/services"
    params = {'f': 'json'}
    headers = {"Accept": "application/json"}
    if folder:
        url = base_url+'/'+folder
    else:
        url = base_url
    r = requests.get(url, headers=headers, params=params, verify=False)
    data = r.json()

    mapservices = [i['name'] for i in data['services'] if i['type'] == type]
    services.extend(mapservices)

    for foldername in data['folders']:
        get_running_services(hostname, services, foldername, type)


def get_service_names(server, folder):
    url = f"https://{server}/arcgis/rest/services/{folder}"
    params = {'f': 'json'}
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    r = requests.get(url, headers=headers, params=params, verify=False)
    if r.status_code != 200:
        raise Exception(f"error retrieving list of services in folder {folder}")
    data = r.json()
    return [i['name'] for i in data['services']]


def enable_wms(extension, state=True):
    logging.info('enabling WMS...')
    if state:
        extension['enabled'] = 'true'
    else:
        extension['enalbed'] = 'false'


def get_token(username, password, servername):
    url = f"https://{servername}/arcgis/admin/generateToken"
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
    url = f"https://{servername}/arcgis/admin/services/{servicename}.MapServer"
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


def assert_json_success(json):
    """checks that the provided JSON object is not an error object"""
    if 'status' in json and json['status'] == "error":
        return False
    else:
        return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    main()
