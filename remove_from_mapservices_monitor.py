import sys
import os
import codecs
import json
import logging
import requests
import socket
import urllib3

localhost = socket.gethostname()

# ignore warning about NGDC-signed certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_running_services(services=[], folder=None, type='MapServer'):
    """ returns a list of all the map service names (including folder) on the target host """

    logging.debug(f"inside get_running_services with {target_host}")
    base_url = f"https://{target_host}/arcgis/rest/services"
    params = {'f': 'json'}
    headers = {"Accept": "application/json"}
    if folder:
        url = base_url+'/'+folder
    else:
        url = base_url
    # r = requests.get(url, headers=headers, params=params)
    if localhost.startswith('lynx'):
        # SOCKS proxy not needed
        r = requests.get(url, params=params, headers=headers)
    else:
        r = requests.get(url, params=params, headers=headers, proxies=dict(https='socks5://localhost:5001'),
                         verify=False)
    data = r.json()

    mapservices = [i['name'] for i in data['services'] if i['type'] == type]
    services.extend(mapservices)

    for foldername in data['folders']:
        get_running_services(services, foldername, type)


def get_existing_checks():
    """ returns a list of the URLs used by currently defined checks"""

    url = f"https://gisdev.ngdc.noaa.gov/mapservices-monitor/healthChecks"
    headers = {"Accept": "application/json"}
    params = {}
    if localhost.startswith('lynx'):
        # SOCKS proxy not needed
        r = requests.get(url, params=params, headers=headers)
    else:
        r = requests.get(url, params=params, headers=headers, proxies=dict(https='socks5://localhost:5001'),
                         verify=False)

    if r.status_code is not 200:
        raise Exception("unable to query API")

    response = r.json()

    if len(response) == 0:
        return False

    return [i['url'] for i in response]


def check_existing_record(servicename=None, service_type='MapServer'):
    """ returns True if any previously defined health check has a URL referencing the provided service name"""

    if not servicename:
        raise Exception("a servicename must be provided")

    # url = f"https://gisdev.ngdc.noaa.gov/mapservices-monitor/healthChecks"
    # headers = {"Accept": "application/json"}
    # params = {}
    # if localhost.startswith('lynx'):
    #     # SOCKS proxy not needed
    #     r = requests.get(url, params=params, headers=headers)
    # else:
    #     r = requests.get(url, params=params, headers=headers, proxies=dict(https='socks5://localhost:5001'),
    #                      verify=False)
    #
    # if r.status_code is not 200:
    #     raise Exception("unable to query API")
    #
    # response = r.json()
    #
    # if len(response) == 0:
    #     return False
    #
    # service_urls = [i['url'] for i in response]

    for i in existing_check_urls:
        # if i.startswith(f"https://{target_host}/arcgis/rest/services/{servicename}/{service_type}"):
        if i.startswith(f"http://wildcat.ngdc.noaa.gov:6080/arcgis/rest/services/{servicename}/{service_type}"):
            return True

    return False


def insert_record(servicename=None, service_type='MapServer', tags=None):
    logging.info(f"inserting record for {servicename}")
    url = "https://gisdev.ngdc.noaa.gov/mapservices-monitor/healthChecks"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    # define the health check parameters
    #         "url": f"https://{target_host}/arcgis/rest/services/{servicename}/{service_type}/export?dpi=96&transparent=true&format=png8&bbox=-84,34,-81,37&bboxSR=4269&size=250,250&f=image",
    data = json.dumps({
        "url": f"http://wildcat.ngdc.noaa.gov:6080/arcgis/rest/services/{servicename}/{service_type}/export?dpi=96&transparent=true&format=png8&bbox=-170,-85,170,85&bboxSR=4269&size=500,250&f=image",
        "checkInterval": "HOURLY",
        "tags": tags
    })

    if localhost.startswith('lynx'):
        # SOCKS proxy not needed
        r = requests.post(url, data=data, headers=headers, auth=(api_user, api_password))
    else:
        r = requests.post(url, data=data, headers=headers, auth=(api_user, api_password),
                          proxies=dict(https='socks5://localhost:5001'), verify=False)
    if r.status_code == 201:
        return True
    else:
        return False

def main():
    """
    read each map and image service from specified ArcGIS Server and add entry into mapservice-monitor if none already
    exists
    """

    mapservices = []
    get_running_services(services=mapservices)

    imageservices = []
    get_running_services(services=imageservices, type='ImageServer')

    for servicename in mapservices:
        if not check_existing_record(servicename=servicename):
            insert_record(servicename=servicename, tags=service_tags)
            pass
        else:
            logging.debug(f"found existing record for {servicename}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # globals
    target_host = 'wildcat.ngdc.noaa.gov:6443'
    api_user = 'admin'
    api_password = 'mypassword'
    service_tags = ["dynamic", "arcgis", "boulder", "wildcat"]

    existing_check_urls = get_existing_checks()

    main()
