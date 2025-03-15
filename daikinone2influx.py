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

    if verbose: 
        for key in data:
            print('{}={}'.format(key,data[key]))

    # maybe make everything int a float?  
    for k in ('ctInverterFinTemp', 'cspSched', 'hspSched', 'tempIndoor', 'sensorRawTemperature'):
        if type(data[k]) != float:
            logging.info(f'forcing {k} {data[k]} to float')
            data[k] = float(data[k])

    # maybe delete soem keys
#    del data['hspSched']
#    for k in ('hspSched'):
#        print('gonna delete data for {} {}'.format(k, data[k]))
#        del data[k]

    # if there is no schedule remove all of the schedule data
    to_delete = []
    if data['schedEnabled'] is False:
        for k in data.keys():
            if k.startswith('sched'):
                to_delete.append(k)
    for k in to_delete:
        del data[k]

    push_data(measurement, data)


def main():
    global ic

    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', dest='verbose',
                        action='store_true', default=0,
                        help='should we be really verbose, huh, should we?')
    parser.add_argument('--push2influx', dest='push2influx',
                        action='store_true', default=True,
                        help='push to influx')
    parser.add_argument('--get_me', dest='get_me',
                        action='store_true', default=False,
                        help='Get/print what Daikin One knows about me')
    parser.add_argument('--get_locations', dest='get_locations',
                        action='store_true', default=False,
                        help='Get/print what Daikin One knows about my location')
    parser.add_argument('--get_devices', dest='get_devices',
                        action='store_true', default=False,
                        help='Get/print what Daikin One knows about my devices')

    args = parser.parse_args()

    log_level = logging.DEBUG

    logging.basicConfig(level=log_level)

    # create influx client, maybe
    if args.push2influx:
        ic = influx.InfluxClient()

    # create thermostat client
    thermo = daikinone.Thermostat()

    if args.get_me:
        r = thermo.get_me()
        pp.pprint(r.json())

    if args.get_locations:
        r = thermo.get_locations()
        pp.pprint(r.json())

    if args.get_devices:
        r = thermo.get_devices()
        pp.pprint(r.json())

    # just do it
    r = thermo.get_thermostat()
    if r.status_code != 200:
        print("failed for some reason")
    else:
        data = r.json()
        send2influx(data)


if __name__ == "__main__":
    main()
