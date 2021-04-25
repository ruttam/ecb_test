import datetime
import json
import logging
import math
import pytest
import re
import requests


logger = logging.getLogger('Logger')

def get_test_data(name, *params):
    with open("../test_data/test_source.json", 'r') as file:
        json_obj = json.load(file)
    data = json_obj[name]
    res = []
    for d in data:
        tpl = ()
        for p in params:
            tpl = tpl + (d[p],)
        res.append(tpl)
    return res

def form_key(currencies_lh, denom):
    key = "M."
    for crnc in currencies_lh[:-1]:
        key += f"{crnc}+"
    key += f"{currencies_lh[-1]}."
    key += f"{denom}.SP00.A"
    return key

def validate_test_OR_result(data, crnc_lh, denom):
    data = data.decode('UTF-8')
    for crnc in crnc_lh:
        assert 'id="CURRENCY" value="' + crnc + '"' in data
    assert data.count(f'id="CURRENCY_DENOM" value="{denom}"') == len(crnc_lh)
    return True

def validate_number_observations(data, number):
    data = data.decode('UTF-8')
    assert data.count("generic:ObsDimension") == number
    obs = re.findall(r"ObsDimension value=\"(.*)\"/>", data)
    now = datetime.datetime.now()
    # taking into account weekends when there are no observations
    expected_num_days = number + 2 * math.ceil(number / 5)
    for o in obs:
        valid = now - datetime.timedelta(days=expected_num_days) <= datetime.datetime.strptime(o, '%Y-%m-%d') <= now
        if not valid:
            return False
    return True

@pytest.mark.parametrize("protocol,url,expected",
                         get_test_data("get_response_data", "protocol", "url", "code"))
def test_get_response(protocol, url, expected):
    url = protocol + "://" + url
    # logger.debug("call url: " + url)
    # logger.debug("expected response code: " + str(expected))
    resp = requests.get(url)
    assert resp.status_code == expected
    if protocol == "http":
        assert "https://" in resp.url

@pytest.mark.parametrize("headers,protocol,url,crnc_lh,denom,expected",
                         get_test_data("OR_data", "headers", "protocol", "url", "crnc_lh", "denom", "code"))
def test_OR(headers, protocol, url, crnc_lh, denom, expected):
    if not crnc_lh:
        raise ValueError('Wild cards are not covered in this test case.')
    key = form_key(crnc_lh, denom)
    url = f"{protocol}://{url}{key}"
    resp = requests.get(url, headers=headers)
    assert resp.status_code == expected
    if protocol == "http":
        assert "https://" in resp.url
    assert validate_test_OR_result(resp.content, crnc_lh, denom)

@pytest.mark.parametrize("protocol,url",
                         get_test_data("modified_since_no_change_data", "protocol", "url"))
def test_modified_since_no_change_data(protocol, url):
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
    url = f"https://{url}"
    headers = {"Accept": format}
    resp = requests.get(url, headers=headers)
    assert resp.status_code == 200

@pytest.mark.parametrize("format,url", get_test_data("unsupported_format_data", "format", "url"))
def test_unsupported_format(format, url):
    url = f"https://{url}"
    headers = {"Accept": format}
    resp = requests.get(url, headers=headers)
    assert resp.status_code == 406

@pytest.mark.parametrize("headers,url,number",
                         get_test_data("number_observations_data", "headers", "url", "number"))
def test_number_observartions(headers, url, number):
    url = f"https://{url}?lastNObservations={number}"
    resp = requests.get(url, headers=headers)
    assert validate_number_observations(resp.content, number)

@pytest.mark.parametrize("url,expected", get_test_data("get_latency_data", "url", "expected_ms"))
def test_get_latency(url, expected):
    url = f"https://{url}"
    resp = requests.get(url)
    assert resp.elapsed.microseconds/1000 <= expected
