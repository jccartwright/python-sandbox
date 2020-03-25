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

    # counters
    file_count = 0
    total_point_count = 0
    for file in new_files:
        try:
            point_count = load_points(file)
        except Exception as e:
            print(e)
            logging.error(f"failed to load points from file {file}")
            continue
        logging.info(f"loaded {point_count} points from file {file}")
        total_point_count += point_count
        file_count += 1

    logging.info(f"loaded {total_point_count} points from {file_count} files")


def read_large_file(file_handler):
    for line in file_handler:
        yield line.strip()


def load_points(filename):
    count = 0
    bad_points = 0
    duplicate_points = 0

    prev_coords = None
    batch = []

    accession_id = get_accession_id_from_filename(filename)

    with open(filename, 'r') as reader:
        for cnt, line in enumerate(read_large_file(reader), start=1):
            try:
                coords = get_coordinates(cnt, line)
            except Exception as error:
                logging.error(error)
                bad_points += 1
                continue

            if point_within_tolerance(prev_coords, coords):
                duplicate_points += 1
                continue

            prev_coords = coords
            coords.append(accession_id)
            batch.append(coords)

            # TODO batch size may be inconsistent if duplicate or bad points encountered. Replace row number with
            #  independent counter that accounts for skipped rows in batch size test
            if (cnt % 5000) == 0:
                # print(f"row number: {cnt}, batch size: {len(batch)}")
                insert_rows(batch)
                count += len(batch)
                batch = []

        # add the last (partial) batch
        insert_rows(batch)
        count += len(batch)

        logging.info(f"bad points: {bad_points}, duplicate points: {duplicate_points}, loaded points: {count}")

    return count


def point_within_tolerance(previous, current):
    # first row doesn't have a previous
    if previous is None:
        return False

    tolerance = 0.0001  # ~11m at equator
    # skip subsequent point if both longitude and latitude values w/in tolerance. assumes both pairs in same accession
    if abs(previous[0] - current[0]) < tolerance and abs(previous[1] - current[1]) < tolerance:
        return True
    else:
        return False


# TODO
def insert_rows(batch):
    # print(batch)
    pass


def get_coordinates(line_number, line):
    elements = line.split()
    try:
        # 4 decimal places precision allows ~11m at equator
        lon = round(float(elements[0].strip()), 3)
        lat = round(float(elements[1].strip()), 3)
    except ValueError:
        raise Exception(f"line number {line_number}: Longitude or Latitude value is not a number")
    if lon < -180.0 or lon > 180.0:
        raise Exception(f"line_number {line_number}: Bad longitude: {lon}")

    if lat < -90.0 or lat > 90.0:
        raise Exception(f"line_number {line_number}: Bad Latitude: {lat}")

    return [lon, lat]


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


if __name__ == "__main__":
    # global vars
    logging.basicConfig(level=logging.INFO)
    DATA_DIR = './oads/'

    main()
