import argparse
import requests
from requests.exceptions import Timeout
import logging
import os


def main():
    # setup command line arguments
    arg_parser = argparse.ArgumentParser(
        description="""download any new OADS data files"""
    )
    arg_parser.add_argument("--dry-run", help="list files to be downloaded but no action taken", action="store_true")
    args = arg_parser.parse_args()

    if args.dry_run:
        logging.info('dry_run mode: no files will be downloaded')

    try:
        file_list = get_manifest()
    except Exception:
        logging.error("unable to retrieve file manifest")
        return

    download_count = 0
    for url in file_list:
        if file_exists(url):
            logging.debug(f'URL {url} already downloaded, no action taken')
            continue

        logging.debug(f'downloading {url}...')
        if not args.dry_run:
            try:
                download_file(url)
            except Exception:
                logging.error(f"error downloading file {url}")
                continue

        download_count = download_count + 1

    logging.info(f'downloaded {download_count} new files')


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
