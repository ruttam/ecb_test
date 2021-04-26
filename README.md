# ECB test project

In this project I test some of the functionality of the European Central Bank API. I chose to use Pytest testing framework.

## Approach
I have implemented data driven testing approach, where various data sets are stored separately from test scripts. A single test case can be executed for different data combinations. It is advantageous with regards to maintainability, avoiding test case repetition and during the regression testing.

In this project I store test data in the JSON format in `test_data/` directory. Data driven testing is enabled through pytest parametrization.

Testing plan:

* Smoke and sanity checks: testing if API responds to different requests with a correct code and returns right data.
* Functionality/interaction testing with correct and incorrect data.
* Metrics testing (e.g., response time to a request or load testing).

### Smoke testing

Testing plan starts with checking basic API functionality. E.g., checking if the API responds with the correct response code.

Test case `test_get_response(protocol, url, code)`.
Sends GET requests with different URL addresses and checks that the response code received is as expected. Additionally a check is added to make sure, that calls to http protocol are redirected to https.

```
def test_get_response(protocol, url, expected):
    """
    Test GET request response code and check http redirection to https
    @param protocol: Request's protocol (e.g. http, https)
    @param url: Address to send GET request to
    @param expected: Expected response code for validation
    """
```

### API functionality testing



Test case `test_OR(headers, protocol, url, crnc, denom, expected)`
Sends HTTP request with an OR operation in the key. The validation method analyses response data in XML format by ensuring, that only the currencies provided in the key are returned.

```
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
```

Test case `def test_modified_since_no_change_data(protocol, url)`
Firstly checks the last modified date by sending a GET request. Then adds 10 minutes to this timestamp and sends a new GET request with this time in If-Modified-Since header. The response is expected to return code 304 - No Change.

```
def test_modified_since_no_change_data(protocol, url):
    """
    Test that providing If-Modified-Since header return No Change when the date
    passed with the request is passed the last modified date
    @param protocol: Request's protocol (e.g. http, https)
    @param url: Address to send GET request to
    """
```

Test case `def test_supported_format(format, url)`
Checks that response to the request with a supported format defined in the headers returns a code OK (200).

```
def test_supported_format(format, url):
    """
    Test the supported format by adding to HTTP header and receiving correct
    response code (200)
    @param format: Supported format (e.g. application/vnd.sdmx.genericdata+xml;version=2.1)
    @param url: Address to send GET request to
    """
```

Test case `def test_unsupported_format(format, url)`
Checks that response to the request with an un supported format defined in the headers returns an Invalid format (406) code.

```
def test_unsupported_format(format, url):
    """
    Test that when adding unsupported format to HTTP request header returns
    Invalid format response code (406)
    @param format: Supported format (e.g. application/pdf)
    @param url: Address to send GET request to
    """
    url = f"https://{url}"
    headers = {"Accept": format}
    resp = requests.get(url, headers=headers)
    assert resp.status_code == 406
```

 Test case `def test_number_observartions(headers, url, number)`
 Checks that when sending a request with a parameter *lastNObservations*, the reponse data contains correct number of the most recent observations. It is validated by analyzing response content, finding exactly the right number of observations and validating, that they are from correct period (in days).

```
def test_number_observartions(headers, url, number):
    """
    Test that defining number of last observations as parameters in a GET request
    returns correct number of the most recent observations
    @param headers: HTTP header to defined which format of response data
    @param url: Address to send GET request to
    @param number: Number of the last observations
    """
```

Test case `def test_get_latency(url, expected)`
Checks that the latency of a request to a certain url is no higher then max latency expected, which is provided in the test data set.

```
def test_get_latency(url, expected):
    """
    Test the latency of the GET request and validate that it is no higher
    than expected (in milliseconds)
    @param url: Address to send GET request to
    @param expected: Expected MAX latency (in ms)
    """
```

## Running locally

To execute tests locally, clone the git repository: `git clone https://github.com/ruttam/ecb_test.git`
In the project root directory run `setup_and_run.bat` (on Windows). This script will setup python environment with the required packages and run the test suite. **Note:** python must be installed in the machine.
The following Python packages and their versions are necessary:
* pytest (6.2.3)
* requests (2.25.1)

The package requirements have strict version numbers to be sure of the environment tests are running in and avoiding unexpected issues when packages get updated.

## Automation

Having test data and test cases under version control in the cloud facilitates continuous integration and delivery. I chose CircleCi CI/CD tool to automatically execute testing on changes of tests or test data in the repository.

### Integration with circleCI
On every push to repository, the pipeline on circleCI (https://app.circleci.com/pipelines/github/ruttam/ecb_test?invite=true) initiates build and execution of the test cases.

The circleCI configuration yml file can be found in: `.circleci/config.yml`. It starts with creating a clean testing environment (starts up a docker container) with the requirements for python version and installs packages defined in `requirements.txt` file. Finally, it runs the tests.

## Final notes

During testing with *If-Modified-Since* header I have observed that ECB API does not comply to the requirements. When defining time past last modified timestamp, it keeps returning response code 200 (OK) instead of expected no change code 304.

Due to CircleCi being hosted outside of Europe, the response time of GET requests is quite long.

### Future work

Some possible improvements:
* Group the test cases so that only the relevant tests would be re-run on changes in their data or their code.
* Initiate testing of certain API functionality when Last modified date returned by HTTP response is updated.
* Use Sphinx to generate Python documentation automatically.
* Use Docker containerization for testing locally to isolate the environment and avoid making changes to the local machine.
* Generate test reports (e.g. using pytest-html package) and store them in a database for traceability.
