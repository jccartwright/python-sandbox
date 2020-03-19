import argparse
import requests
from requests.exceptions import Timeout
import logging
import os
import sys
from urllib.parse import urlencode
import json


def main():
    # setup command line arguments
    arg_parser = argparse.ArgumentParser(
        description="""Enables the WMS extension on the specified MapServer instance. If a folder name is provided, 
        all map services within that folder will be enabled"""
    )
    arg_parser.add_argument("username", help="user name")
    arg_parser.add_argument("password", help="password")
    arg_parser.add_argument("server", help="fully qualified server name")
    arg_parser.add_argument("name", help="folder name or relative path to the map service")
    arg_parser.add_argument("-t", '--target_type', default='service', help="indicates folder or service. defaults to service")
    arg_parser.add_argument("-r", "--report", help="only report on whether WMS is enabled", action="store_true")
    args = arg_parser.parse_args()

    target_type = args.target_type
    if target_type == 'folder':
        services = get_service_names(args.server, args.name)
    elif target_type == 'service':
        services = [args.name]
    else:
        print('target_type must either be "service" or "folder"')
        sys.exit(1)

    token = get_token(args.username, args.password, args.server)

    for service in services:
        try:
            service_info = get_service_info(token, args.server, service)
        except Exception as e:
            logging.warning(f"unable to get service info for {service}")
            continue

        wms_extension = get_wms_extension(service_info)

        # report and take no further action
        if args.report:
            print(wms_extension['enabled'])
            continue

        if wms_extension['enabled'] == 'true':
            logging.info(f"WMS is already enabled on {args.servicename}")
            continue

        # warning: mutates the object which is passed in
        enable_wms(wms_extension)

        try:
            update_service(token, args.servername, args.servicename, service_info)
        except Exception:
            logging.error(f"failed to enable WMS on service {service}")
            continue


def get_service_names(server, folder):
    url = f"https://{server}/arcgis/rest/services/{folder}"
    params = {'f': 'json'}
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    r = requests.get(url, headers=headers, params=params)
    if r.status_code != 200:
        raise Exception(f"error retrieving list of services in folder {folder}")
    data = r.json()
    return [i['name'] for i in data['services']]


def get_wms_extension(service_info):
    for i in service_info['extensions']:
        if i['typeName'] == 'WMSServer':
            return i


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
    r = requests.post(url, headers=headers, data=params)
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

    r = requests.post(url, headers=headers, data=params)
    if r.status_code != 200:
        raise Exception("Error while fetching tokens from admin URL. Please check the URL and try again.")
    data = r.json()

    if not assert_json_success(data):
        # logging.warning(data)
        raise Exception("Error: response object represents an error.")

    return data


def update_service(token, servername, servicename, serviceinfo):
    # print(serviceinfo)
    url = f"https://{servername}/arcgis/admin/services/{servicename}.MapServer/edit"
    params = urlencode({'token': token, 'f': 'json', 'service': json.dumps(serviceinfo)})
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "application/json"}

    r = requests.post(url, headers=headers, data=params)
    if r.status_code != 200:
        raise Exception(f"Error while updating service properties for {servicename}")
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
