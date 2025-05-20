
import os
import logging
import sys

# Import isn't used here, but it needs to happen before zeroc-ice
# is ever imported, otherwise we get segfaults on https requests.
# (Still unsolved as to why - may need to open a ticket with zeroc-ice)
import requests  # nopep8

from src.mumble import mumble_connect  # nopep8


def main():
    debug = os.environ.get('DEBUG', '0') != '0'
    if os.environ.get('ICE_HOST') is None:
        raise KeyError('Missing required ICE_HOST envvar')

    log_level = logging.DEBUG if debug else logging.INFO

    # Configure application logging
    file_formatter = logging.Formatter(
        "%(asctime)s | %(pathname)s:%(lineno)d | %(funcName)s | %(levelname)s | %(message)s ")
    file_handler = logging.FileHandler('output.log')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)

    stdout_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.setFormatter(stdout_formatter)

    # Open an Ice channel to Mumble
    logger = logging.getLogger('Mumble')
    logger.setLevel(log_level)
    logger.addHandler(file_handler)
    logger.addHandler(stdout_handler)

    conn = mumble_connect(logger)
    conn.waitForShutdown()


if __name__ == '__main__':
    main()
