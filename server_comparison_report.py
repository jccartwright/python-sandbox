import argparse
from requests.exceptions import Timeout
from urllib.parse import urlencode
import sys
import os
import json
import logging
import requests
import urllib3

# ignore warning about NGDC-signed certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main(args):
    # augment each server name with port number. all servers must use same port.
    # servers = [f"{i}:{args.port}" for i in args.target_server]
    servers = []
    for i in range(0,2):
        name = args.server[i]
        password = args.password[i]
        username = args.username[i]
        uri = f"{name}:{args.port}"
        token = get_token(username, password, uri)
        mapservice_list = []
        get_service_names(uri, mapservice_list)
        imageservice_list = []
        get_service_names(uri, imageservice_list, None, 'ImageServer')

        servers.append({'name': name, 'username': username, 'password': password, 'port': args.port, 'token': token,
                        'mapservices': mapservice_list, 'imageservices': imageservice_list})

    # build a list of unique service names across all servers
    all_mapservices = []
    for server in servers:
        all_mapservices.extend(server['mapservices'])

    # convert to a list of unique service names
    mapservices = sorted(list(set(all_mapservices)))

    all_imageservices = []
    for server in servers:
        all_imageservices.extend(server['imageservices'])

    # convert to a list of unique service names
    imageservices = sorted(list(set(all_imageservices)))

    # report services not found on both servers
    print('Map Services')
    print(f"name\t{servers[0]['name']}\t{servers[1]['name']}")
    for service in mapservices:
        if service not in servers[0]['mapservices'] or service not in servers[1]['mapservices']:
            print(f"{service}\t{service in servers[0]['mapservices']}\t{service in servers[1]['mapservices']}")

    print('\n')
    print('Image Services')
    print(f"name\t{servers[0]['name']}\t{servers[1]['name']}")
    for service in imageservices:
        if service not in servers[0]['imageservices'] or service not in servers[1]['imageservices']:
            print(f"{service}\t{service in servers[0]['imageservices']}\t{service in servers[1]['imageservices']}")

    # for service in services:
    #     try:
    #         service_info = get_service_info(token, server, service)
    #     except Exception as e:
    #         logging.warning(f"unable to get service info for {service}")
    #         continue
    #     # print(json.dumps(service_info, indent=2))
    #     print(f"{service}: antialiasing set to {service_info['properties']['antialiasingMode']}")


def get_service_names(hostname, services=[], folder=None, type='MapServer'):
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
        get_service_names(hostname, services, foldername, type)


def get_token(username, password, servername):
    url = f"https://{servername}/arcgis/admin/generateToken"
    params = urlencode({'username': username, 'password': password, 'client': 'requestip', 'f': 'json'})
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    r = requests.post(url, headers=headers, data=params, verify=False)
    if r.status_code != 200:
        raise Exception("Error while fetching tokens from admin URL. Please check the URL and try again.")
    data = r.json()
    print(data)

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
    logging.basicConfig(level=logging.WARN)

    # setup command line arguments
    arg_parser = argparse.ArgumentParser(
        description="""report on the differences in map/image services on the specified server(s)"""
    )
    arg_parser.add_argument("--username", action="append", required=True, help="user name")
    arg_parser.add_argument("--password", action="append", required=True, help="password")
    arg_parser.add_argument("--port", default="6443", help="server port")
    arg_parser.add_argument('--server', action='append', required=True,
                            help="fully-qualified target server name. specify once for each server")
    arg_parser.add_argument("--diff", help="report only differences between servers", action="store_true")
    args = arg_parser.parse_args()

    main(args)
