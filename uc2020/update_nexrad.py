import argparse
import logging
import cx_Oracle
from arcgis.gis import GIS
from arcgis import geometry
from arcgis.features import Feature
from arcgis import geometry
import sys
import datetime
# import warnings
# warnings.simplefilter(action='ignore', category=FutureWarning)

def get_data_from_oracle(connect_string):
#    connection = cx_Oracle.connect('gis/VkYi9i8p6m6F@10.254.8.119/NCEIDEV')
    connection = cx_Oracle.connect(connect_string)
    cursor = connection.cursor()
    #cursor.execute("select * from  GIS.NEXRAD_ODA")
    stmt = """SELECT
       'NEXRAD:' || icaoid station_id,
        short_stn_name station_name,
        stateprov state,
        to_date(begindate,'YYYYMMDD') begin_date,
        to_date(enddate,'YYYYMMDD') end_date,
        county,
        countryname country,
        lat latitude,
        lon longitude,
        el_ground elevation,
        rownum objectid
    FROM homrselect.rpt_mshr_legacy
    WHERE STNTYPE in ('NEXRAD','TDWR') AND icaoid != 'KCRI'"""
    cursor.execute(stmt)
    return cursor.fetchall()


def project_all_geometries(nexrad_data):
    geometries = [{'y': i[7], 'x': i[8]} for i in nexrad_data]

    # ArcGIS Online seems to be expecting coordinates in WebMercator
    projected_geometries = geometry.project(geometries=geometries, in_sr=4326, out_sr=3857, gis=geoplatform)
    return projected_geometries


def delete_from_featurelayer(featurelayer):
    """delete all existing Features from FeatureLayer"""

    # TODO why is where clause required to delete all Features?
    result = featurelayer.delete_features(where="OBJECTID is not null")
    deleted_count = len(result['deleteResults'])
    logging.info(f"deleted {deleted_count} stations from FeatureLayer")
    if len(featurelayer.query().features) != 0:
        raise RuntimeError("Expected the FeatureLayer to be empty")


def add_features_to_featurelayer(featurelayer, nexrad_data):
    """add each record retrieved from the database as a new Feature"""
    # much faster to project all points at once
    geometries = project_all_geometries(nexrad_data)

    new_features = []
    for station, geom in zip(nexrad_data, geometries):
        logging.info(f"adding station {station[1]}...")

        new_features.append(
            Feature(geometry=geom, attributes={
                "STATION_ID": station[0],
                "STATION_NAME": station[1],
                "STATE": station[2],
                "BEGIN_DATE": station[3],
                "END_DATE": station[4],
                "COUNTY": station[5],
                "COUNTRY": station[6],
                "LATITUDE": station[7],
                "LONGITUDE": station[8],
                "ELEVATION": station[9],
                "OBJECTID": station[10]
            })
        )

    # commit changes to the hosted FeatureLayer
    result = featurelayer.edit_features(adds=new_features)
    added_count = len(result['addResults'])
    logging.info(f"added {added_count} stations")
    if added_count != len(nexrad_data):
        raise RuntimeError("Number of records added to FeatureLayer does not equal the record count from database")


def main(args):
    if args.dry_run:
        logging.info('dry_run mode: no changes will be made')

    oracle_connect_string = f"{args.db_username}/{args.db_password}@{args.db_host}/{args.db_name}"
    nexrad_data = get_data_from_oracle(oracle_connect_string)
    logging.info(f"retrieved {len(nexrad_data)} stations from database")

    # this FeatureLayerCollection has a single FeatureLayer
    gis_item = geoplatform.content.get('b9c527e0cb6d4c7fac39981f966fdd65')
    layer = gis_item.layers[0]

    if args.dry_run:
        logging.info("dry_run: skipping delete from FeatureLayer")
    else:
        delete_from_featurelayer(layer)

    if args.dry_run:
        logging.info("dry_run: skipping add stations to FeatureLayer")
    else:
        add_features_to_featurelayer(layer, nexrad_data)


if __name__ == "__main__":
    # setup command line arguments
    arg_parser = argparse.ArgumentParser(
        description="""update the Nexrad hosted FeatureLayer from a Oracle database query"""
    )
    arg_parser.add_argument("--gp_username", default="ncei_noaa", help="username to connect to the NOAA GeoPlatform")
    arg_parser.add_argument("--gp_password", required=True, help="password to connect to the NOAA GeoPlatform")
    arg_parser.add_argument("--db_username", default="gisselect", help="username to connect to the database")
    arg_parser.add_argument("--db_password", required=True, help="password to connect to the database")
    arg_parser.add_argument("--db_host", default="10.254.8.119", help="DB hostname or IP")
    arg_parser.add_argument("--db_name", default="NCEIDEV", help="Oracle instance name")
    arg_parser.add_argument("--dry_run", help="query database but no changes made to FeatureLayer", action="store_true")
    args = arg_parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    # setup ArcGIS Online connection as a global
    try:
        geoplatform = GIS("https://noaa.maps.arcgis.com", args.gp_username, args.gp_password)
    except RuntimeError:
        raise RuntimeError(f"failed to connect to the NOAA GeoPlatform as user {args.gp_username}")

    main(args)

