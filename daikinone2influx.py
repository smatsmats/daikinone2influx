#!/usr/bin/python3

import argparse
import datetime
import pprint
from enum import Enum

import sys

import logging
import logging.config

# local stuff
import influx
import daikinone
import myconfig
import mylogger

pp = pprint.PrettyPrinter(indent=4)

verbose = 0
directory_base = "."


def push_data(measurement, data, tags=None):
    json_body = [
        {
            "measurement": measurement,
            "tags": tags,
            # we really should use the time from the call, but whatever
            # "time": datetime.utcfromtimestamp(int(data['ts'])).isoformat(),
            "time": datetime.datetime.now(datetime.UTC).isoformat(),
            "fields": data,
        }
    ]
    mylogger.logger.debug(pp.pformat(json_body))
    mylogger.logger.debug("Point Json:")
    ic.write_points(json_body)


def assign(key, value, data2push=None):
    #    print(f"AAAAAAAAAAAAAAAAAAAA key: {key} value: {value}")

    if data2push is None:
        data2push = {}

    if type(value) is dict:
        for k in value:
            building_k = key + '_' + k
            assign(building_k, value[k], data2push)
    elif type(value) is list:
        k = 1
        for v in value:
            building_k = key + '_' + str(k)
            assign(building_k, v, data2push)
            k = k + 1
    else:
        # test for and handle None value
        if value is None:
            pass
        else:
            data2push[key] = value

    return data2push


def send2influx(data):

    try:
        measurement = '{}-{}'.format(data['statBrand'], data['statModel'])
    except KeyError:
        print("missing keys for brand and model, can't go on")
        return

    if verbose: 
        print(measurement)

    args = []
    spas = []

    if verbose: 
        for key in data:
            print('{}={}'.format(key,data[key]))

    push_data(measurement, data)


def main():
    global ic

    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', dest='verbose',
                        action='store_true', default=0,
                        help='should we be really verbose, huh, should we?')
    parser.add_argument(dest='push2influx',
                        action='store_true', default=True,
                        help='push to influx')

    args = parser.parse_args()

    log_level = logging.DEBUG

    logging.basicConfig(level=log_level)

    # create influx client, maybe
    if args.push2influx:
        ic = influx.InfluxClient()

    # create thermostat client
    thermo = daikinone.Thermostat()

    # just do it
    r = thermo.get_thermostat()
    if r.status_code != 200:
        print("failed for some reason")
    else:
        data = r.json()
        send2influx(data)


if __name__ == "__main__":
    main()
