#!/home/esri/miniconda3/bin/python

import warnings
# hide Pandas deprecation warning
warnings.simplefilter(action='ignore', category=FutureWarning)

import xml.etree.ElementTree as ET
from arcgis.gis import GIS
from arcgis import geometry
import yaml
import sys

with open("update_okeanos_position.yml", 'r') as yaml_file:
    cfg = yaml.safe_load(yaml_file)

BASE_PATH = '/data/OkeanosExplorer/'
#BASE_PATH = 'E:/nobackup/tmp/OkeanosExplorer/'

username = cfg['geoplatform']['username']
password = cfg['geoplatform']['password']
geoplatform = GIS("https://noaa.maps.arcgis.com", username, password)


def get_cruise_list(cruise_list_file):
    # list of dictionaries, one for each cruise. Each dictionary contains attributes for that cruise
    cruises = []

    tree = ET.parse(cruise_list_file).getroot()

    for cruise in tree:
        cruises.append(cruise.attrib)

    return cruises


def get_current_marker(cruise):
    # cruise is just a dictionary of the attributes on the XML <cruise> element
    markers = []

    cruise_pts_file = BASE_PATH + cruise['hourly_path']
    tree = ET.parse(cruise_pts_file).getroot()

    for marker in tree:
        markers.append(marker.attrib)

    # assume markers listed in reverse chronological order
    return markers[0]

def write_csv_file(marker, csv_file):
    f = open(csv_file, 'w')

    f.write(','.join(marker.keys()) + '\n')
    f.write(','.join(marker.values()) + '\n')

    f.close()


def update_gis_item(marker, in_port=False):
    # marker is just a dictionary of the attributes on the XML <marker> element

    # this feature layer has a single layer with a single feature
    gis_item = geoplatform.content.get('4bcb226ce9c446fc802cc7f5c29bcc5c')
    point = gis_item.layers[0].query().features[0]

    point.attributes['IN_PORT'] = in_port

    # extract the lat, lon from dictionary and create geometry
    #lon = marker.pop('lon')
    #lat = marker.pop('lat')

    geom = geographic_to_web_mercator(marker['lon'], marker['lat'])
    point.geometry = geom

    # leave the lon, lat values as attributes for convenience
    marker['lon'] = round(float(marker['lon']), 5)
    marker['lat'] = round(float(marker['lat']), 5)

    if in_port:
        marker['cruiseID'] = 'In Port'
        for key in marker:
            if key not in ['cruiseID', 'lon', 'lat', 'dateTime']:
                #If in port, set all attributes to null except cruiseID, lon, lat, and dateTime
                marker[key] = None

    # previous_position = web_mercator_to_geographic(point.geometry['x'], point.geometry['y'])
    # print(f"Okeanos Explorer previously at {previous_position[0]['x']}, {previous_position[0]['y']}")
    # print(f"Okeanos Explorer currently at {lon}, {lat}")

    # copy the remaining attributes from the XML <marker> element to the Feature
    for key in marker:
        value = marker[key]
        # print(f"{key} = {value}")
        if value:
            point.attributes[key] = marker[key]
        else:
            point.attributes[key] = None

    result = gis_item.layers[0].edit_features(updates=[point])

    # should be exactly one updated Feature
    if not result['updateResults'][0]['success']:
        raise Exception("error updating current position")


def geographic_to_web_mercator(lon, lat):
    input_geometry = {'y': float(lat),
                      'x': float(lon)}
    output_geometry = geometry.project(geometries=[input_geometry],
                                       in_sr=4326,
                                       out_sr=3857,
                                       gis=geoplatform)
    return output_geometry[0]


def web_mercator_to_geographic(x, y):
    input_geometry = {'y': float(y),
                      'x': float(x)}
    output_geometry = geometry.project(geometries=[input_geometry],
                                       in_sr=3857,
                                       out_sr=4326,
                                       gis=geoplatform)
    return output_geometry[0]


def main():
    in_port = False

    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <cruise list filename> <csv filename>")
        sys.exit(1)

    cruise_list_file = sys.argv[1]
    csv_file = sys.argv[2]

    cruise_list = get_cruise_list(cruise_list_file)
    if cruise_list[0]['id'] != 'NO CURRENT CRUISE':
        current_cruise = cruise_list[0]
    else:
        current_cruise = cruise_list[1]
        in_port = True
        # print('WARNING: the ship is in port')

    # assume current cruise is first in list and first Marker element is most recent
    marker = get_current_marker(current_cruise)

    # temporarily write out CSV file
    write_csv_file(marker, csv_file)

    # update the hosted Feature from the XML element
    update_gis_item(marker, in_port)


if __name__ == "__main__":
    main()
