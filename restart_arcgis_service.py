import argparse
import requests
import time
from requests.exceptions import Timeout
import logging
import sys
from urllib.parse import urlencode
import urllib3

# ignore warning about NGDC-signed certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main(args):

    server = f"{args.server}:{args.port}"

    token = get_token(args.username, args.password, server)

    stop_service(token, server, args.service, args.service_type)
    time.sleep(30)
    start_service(token, server, args.service, args.service_type)


def stop_service(token, servername, servicename, service_type):
    url = f"https://{servername}/arcgis/admin/services/{servicename}.{service_type}/stop"
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


def start_service(token, servername, servicename, service_type):
    url = f"https://{servername}/arcgis/admin/services/{servicename}.{service_type}/start"
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


def assert_json_success(json):
    """checks that the provided JSON object is not an error object"""
    if 'status' in json and json['status'] == "error":
        return False
    else:
        return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # setup command line arguments
    arg_parser = argparse.ArgumentParser(
        description="""restart the specified service"""
    )
    arg_parser.add_argument("--username", required=True, help="user name")
    arg_parser.add_argument("--password", required=True, help="password")
    arg_parser.add_argument("--port", default="6443", help="server port")
    arg_parser.add_argument('--server', required=True, help="fully-qualified target server name.")
    arg_parser.add_argument('--service', required=True, help="service name including folder")
    arg_parser.add_argument('--service_type', default='MapServer', choices=['MapServer', 'ImageServer'],
                            help="type of service, default is MapServer")
    args = arg_parser.parse_args()

    main(args)
