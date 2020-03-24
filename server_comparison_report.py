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
    if args.diff and len(args.server) != 2:
        logging.error("--diff can only be used with 2 servers")
        sys.exit(1)

    # initialize server list with command line values
    servers = []
    for i in zip(args.server, args.username, args.password):
        name = i[0]
        username = i[1]
        password = i[2]
        uri = f"{name}:{args.port}"
        token = get_token(username, password, uri)

        # get a list of all services
        service_list = []
        get_service_names(uri, service_list, None, args.service_type)

        # dictionary of each service's relevant properties
        capabilities = {}
        for service in service_list:
            capabilities[service] = get_capabilities(uri, service, token, args.service_type)

        servers.append({'name': name, 'username': username, 'password': password, 'port': args.port, 'token': token,
                        'services': capabilities})

    if args.diff:
        # services not on both servers
        server0_services = set(servers[0]['services'].keys())
        server1_services = set(servers[1]['services'].keys())
        # expect to be sorted
        if server0_services == server1_services:
            print(f"{servers[0]['name']} and {servers[1]['name']} have the same services")
        else:
            diff0 = server0_services.difference(server1_services)
            diff1 = server1_services.difference(server0_services)
            if len(diff0):
                print(f"services missing from {servers[1]['name']}: {diff0}")
            if len(diff1):
                print(f"services missing from {servers[0]['name']}: {diff1}")

        print("difference in service properties")
        print("service\tserver\ttype\twms\twcs\tantialiasing")
        common_services = server0_services.intersection(server1_services)
        for svc in common_services:
            if servers[0]['services'][svc] != servers[1]['services'][svc]:
                print(f"{svc}\t{servers[0]['name']}\t{servers[0]['services'][svc]['type']}\t{servers[0]['services'][svc]['wms']}\t{servers[0]['services'][svc]['wcs']}\t{servers[0]['services'][svc]['antialiasing']}")
                print(f"{svc}\t{servers[1]['name']}\t{servers[1]['services'][svc]['type']}\t{servers[1]['services'][svc]['wms']}\t{servers[1]['services'][svc]['wcs']}\t{servers[1]['services'][svc]['antialiasing']}")
    else:
        # print all services
        print("server\tservice\ttype\twms\twcs\tantialiasing")
        for server in servers:
            server_name = server['name']
            capabilities = server['services']
            for service in capabilities:
                print(f"{server_name}\t{service}\t{capabilities[service]['type']}\t{capabilities[service]['wms']}\t{capabilities[service]['wcs']}\t{capabilities[service]['antialiasing']}")


def get_capabilities(server, service, token, service_type):
    service_info = get_service_info(token, server, service, service_type)
    wms = extension_enabled(service_info, 'WMSServer')
    wcs = extension_enabled(service_info, 'WCSServer')
    # some services, e.g. built-in SampleWorldCities don't have antialiasingMode property
    try:
        antialiasing = service_info['properties']['antialiasingMode']
    except:
        antialiasing = None
    return {'type': service_info['type'], 'wms': wms, 'wcs': wcs, 'antialiasing': antialiasing}


def extension_enabled(service_info, extension='WMSServer'):
    """find the specified extension section in the service_info and return whether it is enabled"""
    for i in service_info['extensions']:
        if i['typeName'] == extension:
            if i['enabled'] == 'true':
                return True
            else:
                return False


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

    if not assert_json_success(data):
        # logging.warning(data)
        raise Exception("Error: response object represents an error.")

    return data['token']


def get_service_info(token, servername, servicename, service_type):
    url = f"https://{servername}/arcgis/admin/services/{servicename}.{service_type}"
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
        description="""report on the properties of map/image services on the specified server(s)"""
    )
    arg_parser.add_argument("--username", action="append", required=True, help="user name")
    arg_parser.add_argument("--password", action="append", required=True, help="password")
    arg_parser.add_argument("--port", default="6443", help="server port")
    arg_parser.add_argument('--server', action='append', required=True,
                            help="fully-qualified target server name. specify once for each server")
    arg_parser.add_argument('--service_type', default='MapServer', choices=['MapServer', 'ImageServer'],
                            help="report on MapServer or ImageServer instances")
    arg_parser.add_argument("--diff", help="report only differences between servers", action="store_true")
    args = arg_parser.parse_args()

    main(args)
