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
        # TODO better way to destructure?
        name = service['name']
        antialiasing = service['antialiasing']
        
        try:
            service_info = get_service_info(token, args.server, name)
        except Exception as e:
            logging.warning(f"unable to get service info for {name}")
            continue

        service_info['properties']['antialiasingMode'] = antialiasing

        try:
            update_service(token, args.server, name, service_info)
        except Exception as e:
            logging.error(f"failed to update antialiasingMode on service {name}")
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
    logging.info(f'updating antialiasingMode on service {servicename}...')
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
        {"name": "GulfDataAtlas/NMFS_BottomLongline_Stations", "antialiasing": "Fastest"},
        {'name': 'GulfDataAtlas/NMFS_BottomLongline_Stations', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/TradeStatistics_GOM_2005_2012', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/USGS_InvasiveSpecies_Lionfish', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/NGDC_BathymetricContours_General', 'antialiasing': 'Fastest'},
        {'name': 'web_mercator/hazards', 'antialiasing': 'Best'},
        {'name': 'web_mercator/ttt_coastal_locations', 'antialiasing': 'Normal'},
        {'name': 'GulfDataAtlas/FisheriesDependent_Invertebrates_CommercialCatch', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/SEAMAP_ReefFish_Effort_1995_2017', 'antialiasing': 'Normal'},
        {'name': 'GulfDataAtlas/SWOT_NestingSites_FrequencyBySpecies', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/FMAs', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/SEAMAP_FallPlankton_Effort', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/CAGES_NMFS_Bongo_Stations', 'antialiasing': 'Normal'},
        {'name': 'GulfDataAtlas/PredictedHabitat_CC_SAV_MobileBay', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/FisheriesDependent_Fishes_CommercialCatch', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/CriticalHabitats', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/FederalProtectedAreas_US', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/NMFS_Fishes_RelativeAbundance_BottomLongline', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/SEAMAP_Fishes_RelativeAbundance_Trawls_1987_2018', 'antialiasing': 'Normal'},
        {'name': 'GulfDataAtlas/SocialVulnerabilityIndicators_FishingCommunities_GulfCoast', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/Bathymetry_0', 'antialiasing': 'None'},
        {'name': 'GulfDataAtlas/SEAMAP_Trawl_Effort', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/NCDC_SeaWinds', 'antialiasing': 'Fastest'},
        {'name': 'web_mercator/fishmaps', 'antialiasing': 'Best'},
        {'name': 'GulfDataAtlas/ORR_OilSpill_Incidents_2000_2010', 'antialiasing': 'Fastest'},
        {'name': 'web_mercator/seafloor_age', 'antialiasing': 'Fast'},
        {'name': 'GulfDataAtlas/FederalProtectedAreas_Cuba', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/NAWQA_Nitrogen_Phosphorus_GOM', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/ShippingAndNavigation', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/SEAMAP_FallPlankton_NeustonNet_Stations_1986_2016', 'antialiasing': 'Normal'},
        {'name': 'GulfDataAtlas/SWOT_NestingSites_SeaTurtles', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/NODC_DissolvedOxygen', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/TropicalStorms_Hurricanes', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/SEAMAP_Fishes_RelativeAbundance_ReefFish_1995_2017', 'antialiasing': 'Normal'},
        {'name': 'web_mercator/nos_seabed_dynamic', 'antialiasing': 'Best'},
        {'name': 'GulfDataAtlas/EssentialFishHabitats', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/NMFS_Sharks_RelativeAbundance_BottomLongline', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/CAGES_SEAMAP_Trawl_Stations', 'antialiasing': 'Normal'},
        {'name': 'GulfDataAtlas/PredictedHabitat_LCLU_SAV_MobileBay', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/SEAMAP_Hypoxia_2001_2011', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/SEAMAP_Invertebrates_RelativeAbundance_Trawls_1987_2018', 'antialiasing': 'Normal'},
        {'name': 'GulfDataAtlas/SEAMAP_FallPlankton_BongoNet_Effort_1986_2016', 'antialiasing': 'Normal'},
        {'name': 'GulfDataAtlas/NODC_Phosphate', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/CMECS_Chlorophyll', 'antialiasing': 'None'},
        {'name': 'GulfDataAtlas/SEAMAP_Trawl_Stations', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/NMFS_Sharks_RelativeAbundance_BottomLongline_2001_2018', 'antialiasing': 'Normal'},
        {'name': 'GulfDataAtlas/SEAMAP_Sharks_RelativeAbundance_Trawls_1987_2018', 'antialiasing': 'Normal'},
        {'name': 'GulfDataAtlas/Oysters_GOM', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/FederalProtectedAreas_Mexico', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/NCCOS_ToxicBlooms_PMN', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/NODC_SST', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/NOS_DynamicFiveZoneSalinityScheme', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/USACE_NatlWaterWayNetwork', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/SEAMAP_ReefFish_Stations_1995_2017', 'antialiasing': 'Normal'},
        {'name': 'GulfDataAtlas/NMFS_BottomLongline_Effort_2001_2018', 'antialiasing': 'Normal'},
        {'name': 'GulfDataAtlas/SEAMAP_ReefFish_Effort', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/FoodHabits', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/NGDC_BathymetricContours_Detailed', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/SEAMAP_Trawl_Effort_1987_2018', 'antialiasing': 'Normal'},
        {'name': 'GulfDataAtlas/NODC_Silicate', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/usSEABED_LooseSediments', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/SEAMAP_FallPlankton_NeustonNet_Effort_1986_2016', 'antialiasing': 'Normal'},
        {'name': 'GulfDataAtlas/SEAMAP_FallPlankton_Stations', 'antialiasing': 'Fastest'},
        {'name': 'web_mercator/multibeam_dynamic', 'antialiasing': 'Best'},
        {'name': 'GulfDataAtlas/SEAMAP_Invertebrates_RelativeAbundance', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/usSEABED_DominantSediments', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/EssentialFishHabitats_BluefinTuna', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/SEAMAP_Fishes_RelativeAbundance_ReefFish', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/CMECS_Temperature', 'antialiasing': 'None'},
        {'name': 'GulfDataAtlas/SEAMAP_NMFS_Fishes_Occurrence', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/SWOT_PredictedHabitatSuitability_SeaTurtles', 'antialiasing': 'Fastest'},
        {'name': 'EMAG2v3', 'antialiasing': 'Best'},
        {'name': 'SampleWorldCities', 'antialiasing': 'None'},
        {'name': 'GulfDataAtlas/NCCOS_SocialWellBeing_2012', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/NMFS_Fishes_RelativeAbundance_BottomLongline_2001_2018', 'antialiasing': 'Normal'},
        {'name': 'GulfDataAtlas/PERSIANNCDR_1984_2014', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/USGS_InvasiveSpecies_AsianTigerShrimp', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/NODC_Salinity', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/NMFS_BottomLongline_Effort', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/SEAMAP_Fishes_RelativeAbundance_FallPlankton_BongoNeustonNet_1986_2016', 'antialiasing': 'Normal'},
        {'name': 'GulfDataAtlas/SEAMAP_FallPlankton_BongoNet_Stations_1986_2016', 'antialiasing': 'Normal'},
        {'name': 'GulfDataAtlas/GrandBayNERR_Monitoring', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/SEAMAP_NMFS_Fishes_Occurrence_1995_2018', 'antialiasing': 'Normal'},
        {'name': 'GulfDataAtlas/SAV_Gulfwide', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/usSEABED_MudSandGravelRock', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/NODC_WaterTemperature', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/LCLU_MobileBay', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/NMFS_BottomLongline_Stations_2001_2018', 'antialiasing': 'Normal'},
        {'name': 'GulfDataAtlas/SEAMAP_Fishes_RelativeAbundance_FallPlankton', 'antialiasing': 'Fastest'},
        {'name': 'web_mercator/marine_geology_dynamic', 'antialiasing': 'Best'},
        {'name': 'GulfDataAtlas/CMECS_WaterColumnStabilityModifier', 'antialiasing': 'None'},
        {'name': 'GulfDataAtlas/SEAMAP_Trawl_Stations_1987_2018', 'antialiasing': 'Normal'},
        {'name': 'GulfDataAtlas/MarineJurisdictions', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/SEAMAP_ReefFish_Stations', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/Watersheds', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/RecFac_MarinasRamps', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/SEAMAP_Fishes_RelativeAbundance_Trawls', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/EstuarineBathymetry_30m', 'antialiasing': 'None'},
        {'name': 'reference/world_countries_overlay', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/NODC_Nitrates', 'antialiasing': 'Fastest'},
        {'name': 'GulfDataAtlas/NOS_StaticThreeZoneSalinityScheme', 'antialiasing': 'Fastest'},
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
