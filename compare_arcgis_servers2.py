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


def get_running_services(hostname='gis.ngdc.noaa.gov', services=[], folder=None, type='MapServer'):
    base_url = f"https://{hostname}:6443/arcgis/rest/services"
    params = {'f': 'json'}
    headers = {"Accept": "application/json"}
    if folder:
        url = base_url+'/'+folder
    else:
        url = base_url

    if localhost.startswith('lynx'):
        # SOCKS proxy not needed
        r = requests.get(url, params=params, headers=headers, verify=False)
    else:
        r = requests.get(url, params=params, headers=headers, proxies=dict(https='socks5://localhost:5001'),
                         verify=False)
    data = r.json()

    mapservices = [i['name'] for i in data['services'] if i['type'] == type]
    services.extend(mapservices)

    for foldername in data['folders']:
        get_running_services(hostname, services, foldername, type)


# TODO does not currently report on WMS endpoints for ImageServices
def get_OGC_services(hostname='gis.ngdc.noaa.gov', services=[], type='WMS'):
    """given a list of mapservices, return the subset for which there are active OGC endpoints"""
    ogc_services = []

    base_url = f"https://{hostname}:6443/arcgis/services"
    if type == 'WMS':
        params = {'request': 'GetCapabilities', 'service': type}
        service_type = 'MapServer/WMSServer'
    elif type == 'WCS':
        params = {'request': 'GetCapabilities', 'service': type}
        service_type = 'ImageServer/WCSServer'

    for service in services:
        url = f'{base_url}/{service}/{service_type}'

        if localhost.startswith('lynx'):
            # SOCKS proxy not needed
            r = requests.get(url, params=params, verify=False)
        else:
            r = requests.get(url, params=params, proxies=dict(https='socks5://localhost:5001'),
                             verify=False)
        # print(f'{url} on {hostname}: {r.status_code}')
        if r.status_code == 200:
            ogc_services.append(service)

    return ogc_services


def main():
    """
    compare the services hosted on two ArcGIS Server instances
    Note:
        this only compares the service name and type. It does not take in account any other service properties.
    """
    host1 = 'wildcat.ngdc.noaa.gov'
    host2 = 'snowleopard.ngdc.noaa.gov'

    mapservices1 = []
    get_running_services(hostname=host1, services=mapservices1)
    wms_services1 = get_OGC_services(hostname=host1, services=mapservices1)

    imageservices1 = []
    get_running_services(hostname=host1, services=imageservices1, type='ImageServer')
    wcs_services1 = get_OGC_services(hostname=host1, services=imageservices1, type='WCS')

    mapservices2 = []
    get_running_services(hostname=host2, services=mapservices2)
    wms_services2 = get_OGC_services(hostname=host2, services=mapservices2)

    imageservices2 = []
    get_running_services(hostname=host2, services=imageservices2, type='ImageServer')
    wcs_services2 = get_OGC_services(hostname=host2, services=imageservices2, type='WCS')

    print(f"\n\nmap services on {host1} but not on {host2}:")
    for i in mapservices1:
        if i not in mapservices2:
            print(i)

    print(f"\n\nWMS services on {host1} but not on {host2}:")
    for i in wms_services1:
        if i not in wms_services2:
            print(i)

    print(f"\n\nmap services on {host2} but not on {host1}:")
    for i in mapservices2:
        if i not in mapservices1:
            print(i)

    print(f"\n\nWMS services on {host2} but not on {host1}:")
    for i in wms_services2:
        if i not in wms_services1:
            print(i)

    print(f"\n\nimage services on {host1} but not on {host2}:")
    for i in imageservices1:
        if i not in imageservices2:
            print(i)

    print(f"\n\nWCS services on {host1} but not on {host2}:")
    for i in wcs_services1:
        if i not in wcs_services2:
            print(i)

    print(f"\n\nimage services on {host2} but not on {host1}:")
    for i in imageservices2:
        if i not in imageservices1:
            print(i)

    print(f"\n\nWCS services on {host2} but not on {host1}:")
    for i in wcs_services2:
        if i not in wcs_services1:
            print(i)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARN)
    main()
