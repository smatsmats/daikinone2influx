#!/usr/bin/python3

import requests
import pprint
import time
import json
import math
import sys
from requests.exceptions import HTTPError
from datetime import datetime, timedelta, date

import myconfig
import mylogger

pp = pprint.PrettyPrinter(indent=4)
bogus_date = datetime(1900, 1, 1)
date_format = "%Y-%m-%dT%H:%M:%SZ"

session = requests.Session()
verbose = False
calls = 0

access_token = ''
refresh_token = ''


def flatten_json(nested_json):
    out = {}

    def flatten(x, name=""):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + ".")
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + ".")
                i += 1
        else:
            out[name[:-1]] = x

    flatten(nested_json)
    return out


class Request:
    def __init__(self, account="test", dry_run=True, allow_404=False):
        self.account = account
        self.dry_run = dry_run
        self.allow_404 = allow_404
        self.token = None
        self.token_expire = bogus_date
        self.refresh_token = None
        self.session = requests.Session()
        self.calls = 0

    def get_calls(self):
        return (self.calls)

    def make_request(self, method, url, payload=None,
                     header=None, is_get_token=False):

        headers = {'content-type': 'application/json',
                   'Accept': 'application/json'}
        # add any headers needed
        if header is not None:
            headers.update(header)

        response = None
        c = 0
        max = 10
        while response is None and c < max:

            if not is_get_token:
                if self.token_expire < datetime.now():
                    self.token = None

                if self.token is None:
                    self.token = self.get_token()

                token_string = "Bearer " + self.token
                headers.update({'authorization': token_string})

            if verbose:
                print("method", method, "url", url,
                      "headers", headers, "payload", payload)

            try:
                response = self.session.request(method=method,
                                                url=url,
                                                headers=headers,
                                                data=json.dumps(payload),
                                                timeout=myconfig.config['requests_timeout'])
                self.calls = self.calls + 1

                # If the response was successful, no Exception will be raised
                response.raise_for_status()
            except HTTPError as http_err:
                print('HTTP error occurred: {}'.format(http_err))

                if response.status_code == 401:
                    print('got a 401, maybe try again')
                    self.token = None
                elif response.status_code == 404 and self.allow_404:
                    print('got a 404, but that it is ok')
                elif response.status_code == 502:
                    print('got a 502, but ok, lets wait a tick and try again')
                    response = None
                elif response.status_code == 520:
                    print('got a 520, is this ok?, lets wait a tick and try again')
                    response = None
                else:
                    sys.exit(1)
            except Timeout as err:
                print('Timeout ({}), maybe try again: {}'.
                      format(myconfig.config['requests_timeout'], err))
            except Exception as err:
                print('Other error occurred: {}'.format(err))
            else:
                if verbose:
                    print('Success!')

            if response is None:
                c = c + 1
                wait = c * 20
                print("timed out, going to wait {} second and try again".
                      format(wait))
                time.sleep(wait)

        return response

    def get_token(self):
        email = myconfig.config['daikinone']['email']
        password = myconfig.config['daikinone']['password']

        payload = {'email': email, "password": password}

        url = 'https://api.daikinskyport.com/users/auth/login'

        response = self.make_request(
            "post", url, payload=payload, is_get_token=True)

        if response.status_code != 200:
            print('bummer, couldn\'t get token, non-200')
            sys.exit(1)

        response_dict = response.json()

        if verbose:
            pp.pprint(response_dict)

        try:
            response_dict['accessToken']
        except KeyError:
            if not response_dict['status']:
                print('bummer, couldn\'t get token, error message: {}'.
                      format(response_dict['errorMessage']))
                sys.exit(1)

        self.token = response_dict['accessToken']
        self.refresh_token = response_dict['refreshToken']
        self.accessTokenExpiresIn = response_dict['accessTokenExpiresIn']
        self.token_expire = datetime.now() + timedelta(seconds=self.accessTokenExpiresIn)
        if verbose:
            print("new token expire time: {}".
                  format(datetime.strftime(self.token_expire,
                         date_format)))
        return (self.token)


def make_request(method, url, payload=None):
    global dry_run
    global session
    global calls

    if accessToken == '':
        make_request
    token_string = "Bearer " + myconfig.config["span"]["auth"]["token"]
    headers = {
        "authorization": token_string,
        "accept": "application/json",
        "content-type": "application/json",
    }

    #    mylogger.logger.debug("payload {}".format(json.dumps(payload)))
    if verbose:
        pp.pprint("method", method, "url", url,
                  "headers", headers, "payload", payload)

    response = None
    c = 0
    max = 10
    while response is None and c < max:
        try:
            response = session.request(
                method=method, url=url, headers=headers, data=json.dumps(
                    payload)
            )
            calls = calls + 1

            # If the response was successful, no Exception will be raised
            response.raise_for_status()
        except HTTPError as http_err:
            # print(f'HTTP error occurred: {http_err}')
            # print(f'text: {response.text}')
            if response.status_code == 401:
                sys.exit()
        except Exception as err:
            print(f"Other error occurred: {err}")
        else:
            if verbose:
                print("Success!")
        if response is None:
            c = c + 1
            wait = c * 20
            print("timed out, going to wait %d second and try again" % (wait))
            time.sleep(wait)

    # did we get anything?
    if response is None:
        print("No response")
        sys.exit()

    return response


class Thermostat:
    def __init__(self):
        # maybe check if we can actually talk to the panel before
        # going any further
        self.rqt = Request(dry_run=False)
        self.api_base = myconfig.config['daikinone']['api_url_base']

    def get_me(self):
        method = 'get'
        path = 'users/me'
        url = '{}{}'.format(self.api_base, path)
        r = self.rqt.make_request(method, url)
        if r.status_code != 200:
            return (None)

        if verbose:
            pp.pprint(r.json())

        return (r)

    def get_locations(self):
        method = 'get'
        path = 'locations'
        url = '{}{}'.format(self.api_base, path)
        r = self.rqt.make_request(method, url)
        if r.status_code != 200:
            return (None)

        if verbose:
            pp.pprint(r.json())

        return (r)

    def get_devices(self):
        method = 'get'
        path = 'devices'
        url = '{}{}'.format(self.api_base, path)
        r = self.rqt.make_request(method, url)
        if r.status_code != 200:
            return (None)

        if verbose:
            pp.pprint(r.json())

        return (r)

    def get_thermostat(self):
        method = 'get'
        path = 'deviceData'
        device_id = myconfig.config['daikinone']['thermostat_id']
        url = '{}{}/{}'.format(self.api_base, path, device_id)
        r = self.rqt.make_request(method, url)
        if r.status_code != 200:
            return (None)

        if verbose:
            pp.pprint(r.json())

        return (r)


def main():
    verbose = True
    thermo = Thermostat()
    thermo.get_me()
    thermo.get_locations()
    thermo.get_devices()
    thermo.get_thermostat()

    exit(0)


if __name__ == "__main__":
    main()
