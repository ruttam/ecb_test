"""
Test suite for European Central Bank API
"""

import datetime
import json
import logging
import math
import pytest
import re
import requests


def get_test_data(name, *params):
    """
    Get test set by name and its parameters in a certain order
    @param name: Name of test data sets
    @param params: Names of test parameters (JSON keys)
    @return: Test parameters - a list of tuples
    """
    with open("test_data/test_source.json", 'r') as file:
        json_obj = json.load(file)
    data = json_obj[name]
    res = []
    for d in data:
        tpl = ()
        for p in params:
            tpl = tpl + (d[p],)
        res.append(tpl)
    return res

def form_key(currencies, denom):
    """
    Create an request key from list of currencies and OR operation
    @param currencies: List of currencies
    @param denom: Denominator
    @return: Key section of URL
    """
    key = "M."
    for crnc in currencies[:-1]:
        key += f"{crnc}+"
    key += f"{currencies[-1]}."
    key += f"{denom}.SP00.A"
    return key

def validate_test_OR_result(data, currencies, denom):
    """
    Validate OR request by checking if all currencies are included in result XML
    @param data: Result data received of response to a request
    @param currencies: Currencies that are in OR statement
    @param denom: Denominator
    @return: Boolean value validating, that response contained only the needed data
    """
    data = data.decode('UTF-8')
    for crnc in currencies:
        validation_str = 'id="CURRENCY" value="'
        assert validation_str + crnc + '"' in data
        assert data.count(validation_str) ==  len(currencies)
    assert data.count(f'id="CURRENCY_DENOM" value="{denom}"') == len(currencies)
    return True

def validate_number_observations(data, number):
    """
    Validate request with a defined number of observations
    @param data: Result data received of response to a request
    @param number: Number of observations expected
    @return: Boolean value validating, that response contained the correct
    number of the most recent observations
    """
    data = data.decode('UTF-8')
    assert data.count("generic:ObsDimension") == number
    obs = re.findall(r"ObsDimension value=\"(.*)\"/>", data)
    now = datetime.datetime.now()
    # taking into account weekends when there are no observations
    # and possibility that present day's observation is not yet uploaded
    expected_num_days = number + 2 * math.ceil(number / 5) + 1
    for o in obs:
        valid = now - datetime.timedelta(days=expected_num_days) <= datetime.datetime.strptime(o, '%Y-%m-%d') <= now
        if not valid:
            return False
    return True

@pytest.mark.parametrize("protocol,url,expected",
                         get_test_data("get_response_data", "protocol", "url", "code"))
def test_get_response(protocol, url, expected):
    """
    Test GET request response code and check http redirection to https
    @param protocol: Request's protocol (e.g. http, https)
    @param url: Address to send GET request to
    @param expected: Expected response code for validation
    """
    url = protocol + "://" + url
    # logger.debug("call url: " + url)
    # logger.debug("expected response code: " + str(expected))
    resp = requests.get(url)
    assert resp.status_code == expected
    if protocol == "http":
        assert "https://" in resp.url

@pytest.mark.parametrize("headers,protocol,url,crnc,denom,expected",
                         get_test_data("OR_data", "headers", "protocol", "url", "crnc", "denom", "code"))
def test_OR(headers, protocol, url, crnc, denom, expected):
    """
    Test OR functionality by providing a list of currencies to fetch their rate
    and validate that only and all of the requested data was received
    @param headers: HTTP header to defined which format of response data
    @param protocol: Request's protocol (e.g. http, https)
    @param url: Address to send GET request to
    @param crnc: Currencies that are in OR statement
    @param denom: Denominator
    @param expected: Expected response code for validation
    """
    if not crnc:
        raise ValueError('Wild cards are not covered in this test case.')
    key = form_key(crnc, denom)
    url = f"{protocol}://{url}{key}"
    resp = requests.get(url, headers=headers)
    assert resp.status_code == expected
    if protocol == "http":
        assert "https://" in resp.url
    assert validate_test_OR_result(resp.content, crnc, denom)

@pytest.mark.parametrize("protocol,url",
                         get_test_data("modified_since_no_change_data", "protocol", "url"))
def test_modified_since_no_change_data(protocol, url):
    """
    Test that providing If-Modified-Since header return No Change when the date
    passed with the request is passed the last modified date
    @param protocol: Request's protocol (e.g. http, https)
    @param url: Address to send GET request to
    """
    url = f"{protocol}://{url}"
    resp = requests.get(url)
    assert resp.status_code == 200
    if protocol == "http":
        assert "https://" in resp.url
    date_time_obj = datetime.datetime.strptime(resp.headers['last-modified'],
                                               '%a, %d %b %Y %H:%M:%S %Z')
    new_time = date_time_obj + datetime.timedelta(minutes=10)
    headers = {'If-Modified-Since': new_time.strftime('%a, %d %b %Y %H:%M:%S %Z')}
    resp = requests.get(url, headers=headers)
    assert resp.status_code == 304

@pytest.mark.parametrize("format,url", get_test_data("supported_format_data", "format", "url"))
def test_supported_format(format, url):
    """
    Test the supported format by adding to HTTP header and receiving correct
    response code (200)
    @param format: Supported format (e.g. application/vnd.sdmx.genericdata+xml;version=2.1)
    @param url: Address to send GET request to
    """
    url = f"https://{url}"
    headers = {"Accept": format}
    resp = requests.get(url, headers=headers)
    assert resp.status_code == 200

@pytest.mark.parametrize("format,url", get_test_data("unsupported_format_data", "format", "url"))
def test_unsupported_format(format, url):
    """
    Test that when adding unsupported format to HTTP request header returns
    correct Invalid format code (406)
    @param format: Supported format (e.g. application/pdf)
    @param url: Address to send GET request to
    """
    url = f"https://{url}"
    headers = {"Accept": format}
    resp = requests.get(url, headers=headers)
    assert resp.status_code == 406

@pytest.mark.parametrize("headers,url,number",
                         get_test_data("number_observations_data", "headers", "url", "number"))
def test_number_observartions(headers, url, number):
    """
    Test that defining number of last observations as parameters in a GET request
    returns correct number of the most recent observations
    @param headers: HTTP header to defined which format of response data
    @param url: Address to send GET request to
    @param number: Number of the last observations
    """
    url = f"https://{url}?lastNObservations={number}"
    resp = requests.get(url, headers=headers)
    assert validate_number_observations(resp.content, number)

@pytest.mark.parametrize("url,expected", get_test_data("get_latency_data", "url", "expected_ms"))
def test_get_latency(url, expected):
    """
    Test the latency of the GET request and validate that it is no higher
    than expected (in milliseconds)
    @param url: Address to send GET request to
    @param expected: Expected MAX latency (in ms)
    """
    url = f"https://{url}"
    resp = requests.get(url)
    assert resp.elapsed.microseconds/1000 <= expected
