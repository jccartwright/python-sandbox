import sys
import os
import codecs
import json
import logging
import requests


def get_running_services(hostname='gis.ngdc.noaa.gov', services=[], folder=None, type='MapServer'):
    base_url = f"https://{hostname}/arcgis/rest/services"
    params = {'f': 'json'}
    headers = {"Accept": "application/json"}
    if folder:
        url = base_url+'/'+folder
    else:
        url = base_url
    r = requests.get(url, headers=headers, params=params)
    data = r.json()

    mapservices = [i['name'] for i in data['services'] if i['type'] == type]
    services.extend(mapservices)

    for foldername in data['folders']:
        get_running_services(hostname, services, foldername, type)


def main():
    """
    compare the services hosted on two ArcGIS Server instances

    Note:
        this only compares the service name and type. It does not take in account any other service properties.
    """
    host1 = 'gis.ngdc.noaa.gov'
    host2 = 'gis.ncdc.noaa.gov'

    mapservices1 = []
    get_running_services(hostname=host1, services=mapservices1)

    imageservices1 = []
    get_running_services(hostname=host1, services=imageservices1, type='ImageServer')

    mapservices2 = []
    get_running_services(hostname=host2, services=mapservices2)

    imageservices2 = []
    get_running_services(hostname=host2, services=imageservices2, type='ImageServer')

    print(f"\n\nservices in {host1} but not in {host2}:")
    for i in mapservices1:
        if i not in mapservices2:
            print(i)

    print(f"\n\nservices in {host2} but not in {host1}:")
    for i in mapservices2:
        if i not in mapservices1:
            print(i)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARN)
    main()
