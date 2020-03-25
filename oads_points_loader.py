import argparse
import requests
from requests.exceptions import Timeout
import logging
import os
import glob


def main():
    # setup command line arguments
    arg_parser = argparse.ArgumentParser(
        description="""insert into Oracle table points from any file not currently represented in the database"""
    )
    arg_parser.add_argument("--dry-run", help="list files to be loaded but no action taken", action="store_true")
    args = arg_parser.parse_args()

    if args.dry_run:
        logging.info('dry_run mode: no files will be loaded')

    try:
        current_accessions = get_accession_ids()
    except Exception:
        logging.error("unable to retrieve existing accession IDs")
        return

    # files on disk w/o corresponding accession ID in database
    new_files = get_new_files(current_accessions)

    file_count = 0
    total_point_count = 0
    for file in new_files:
        try:
            point_count = load_points(file)
        except Exception:
            logging.error(f"failed to load points from file {file}")
            continue
        logging.info(f"loaded {point_count} points from file {file}")
        total_point_count += point_count
        file_count += 1

    logging.info(f"loaded {total_point_count} points from {file_count} files")


# TODO
def load_points(filename):
    count = 0
    with open(filename, 'r') as reader:
        for line in reader:
            count += 1

    return count


def get_new_files(current_accessions):
    """return a list of filenames which don't have a corresponding accession ID in the given list"""
    new_files = []
    for filename in glob.glob(DATA_DIR + "*.txt"):
        accession_id = get_accession_id_from_filename(filename)
        if accession_id not in current_accessions:
            new_files.append(filename)

    return new_files


# depends on file name convention like "NNNNNNN_lonlat.txt" where "NNNNNNN" represents accession ID.
def get_accession_id_from_filename(filename):
    name = filename.split('/')[-1]
    return name.split('_')[0]


# TODO
def get_accession_ids():
    return ['0000183', '0000071']


def file_exists(file_url):
    filename = file_url.split('/')[-1]
    if os.path.exists(DATA_DIR + filename):
        return True
    else:
        return False


def download_file(file_url):
    r = requests.get(file_url)
    if r.status_code != 200:
        raise Exception(f"error downloading file {file_url}")

    filename = file_url.split('/')[-1]
    with open(DATA_DIR + filename, 'wb') as writer:
        writer.write(r.content)


def get_manifest():
    """returns a list of data file URLs"""
    r = requests.get(MANIFEST_URL)

    if r.status_code != 200:
        raise Exception("unable to retrieve file manifest")

    return r.text.splitlines()


if __name__ == "__main__":
    # global vars
    logging.basicConfig(level=logging.INFO)
    MANIFEST_URL = 'https://data.nodc.noaa.gov/ncei/ocaa/ocaa_lonlat.url'
    DATA_DIR = './oads/'

    main()
