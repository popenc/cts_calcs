import requests
import json
import logging
import os
try:
    from cts_app.cts_calcs.calculator import Calculator
except ImportError as e:
    from cts_calcs.calculator import Calculator

headers = {'Content-Type': 'application/json'}


class TestCalc(Calculator):
    """
	TEST Suite Calculator
	"""

    def __init__(self):

        Calculator.__init__(self)

        self.postData = {"smiles" : ""}
        self.name = "test"
        self.baseUrl = os.environ['CTS_TEST_SERVER']
        self.urlStruct = "/api/TEST/{}/{}" # method, property

        # self.methods = ['hierarchical']
        self.methods = ['FDAMethod', 'HierarchicalMethod']
        # map workflow parameters to test
        self.propMap = {
            'melting_point': {
               'urlKey': 'MeltingPoint'
            },
            'boiling_point': {
               'urlKey': 'BoilingPoint'
            },
            'water_sol': {
               'urlKey': 'WaterSolubility'
            },
            'vapor_press': {
               'urlKey': 'VaporPressure'
            }
            # 'henrys_law_con': ,
            # 'kow_no_ph': 
        }


    def getPostData(self, calc, prop, method=None):
        return {"identifiers": {"SMILES": ""}}


    def makeDataRequest(self, structure, calc, prop, method=None):
        post = self.getPostData(calc, prop)
        post['identifiers']['SMILES'] = structure # set smiles
        test_prop = self.propMap[prop]['urlKey'] # prop name TEST understands
        url = self.baseUrl + self.urlStruct.format('FDAMethod', test_prop)
        try:
            response = requests.post(url, data=json.dumps(post), headers=headers, timeout=60)
        except requests.exceptions.ConnectionError as ce:
            logging.info("connection exception: {}".format(ce))
            # return None
            raise
        except requests.exceptions.Timeout as te:
            logging.info("timeout exception: {}".format(te))
            # return None
            raise

        self.results = response
        return response


    def convertWaterSolubility(self, mass, test_datum):
        """
        Converts water solubility from log(mol/L) => mg/L
        """
        return 1000 * float(mass) * 10**-(test_datum)


    def data_request_handler(self, request_dict):
        

        _filtered_smiles = ''
        _response_dict = {}

        # fill any overlapping keys from request:
        for key in request_dict.keys():
            _response_dict[key] = request_dict.get(key)
        _response_dict.update({'request_post': request_dict, 'method': None})


        # filter smiles before sending to TEST:
        # ++++++++++++++++++++++++ smiles filtering!!! ++++++++++++++++++++
        try:
            _filtered_smiles = parseSmilesByCalculator(request_dict['chemical'], request_dict['calc']) # call smilesfilter
        except Exception as err:
            logging.warning("Error filtering SMILES: {}".format(err))
            _response_dict.update({'data': "Cannot filter SMILES for TEST data"})
            return _response_dict
        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

        logging.info("TEST Filtered SMILES: {}".format(_filtered_smiles))

        try:
            logging.info("Calling TEST for {} data...".format(request_dict['prop']))

            _response = self.makeDataRequest(_filtered_smiles, request_dict['calc'], request_dict['prop'])
            # response_json = json.loads(_response.content)
            # _response_dict.update({'data': _response})

            logging.info("TEST response data for {}: {}".format(request_dict['prop'], response_json))

            # sometimes TEST data successfully returns but with an error:
            if _response.status_code != 200:
                _response_dict['data'] = "TEST could not process chemical"
            else:
                _test_data = response_json['properties'][self.propMap[request_dict['prop']]['urlKey']]
                if _test_data == -9999:
                    _response_dict['data'] = "N/A"
                elif prop == 'water_sol':
                    _response_dict['data'] = self.convertWaterSolubility(request_dict['mass'], _test_data)
                else:
                    _response_dict['data'] = _test_data

            return _response_dict

        except Exception as err:
            logging.warning("Exception occurred getting TEST data: {}".format(err))
            _response_dict.update({'data': "timed out", 'request_post': request.POST})
            logging.info("##### session id: {}".format(sessionid))
            return _response_dict