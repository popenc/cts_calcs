__author__ = "np"

import requests
import logging
import json
from .calculator import Calculator
from .calculator_metabolizer import MetabolizerCalc
from .jchem_properties import Tautomerization



class Molecule(object):
	"""
	Basic molecule object for CTS
	"""
	def __init__(self):

		# cts keys:
		self.chemical = ''  # initial structure from user (any chemaxon format)
		self.orig_smiles = ''  # before filtering, converted to smiles

		# chemaxon/jchem keys:
		self.smiles = ''  # post filtered smiles 
		self.formula = ''
		self.iupac = ''
		self.cas = ''
		self.mass = ''
		self.structureData = ''
		self.exactMass = ''

	def createMolecule(self, chemical, orig_smiles, chem_details_response, get_structure_data=None):
		"""
		Gets Molecule attributes from Calculator's getChemDetails response
		"""
		# set attrs from jchem data:
		for key in self.__dict__.keys():
			if key != 'orig_smiles' and key != 'chemical':
				try:
					if key == 'structureData' and get_structure_data == None:
						pass
					elif key == 'cas':
						# check if object with 'error' key instead of string of CAS#..
						if isinstance(chem_details_response['data'][0][key], dict):
							self.__setattr__(key, "N/A")
						else:
							self.__setattr__(key, chem_details_response['data'][0][key])	
					else:
						self.__setattr__(key, chem_details_response['data'][0][key])
				except KeyError as err:
					raise err
		# set cts attrs:
		self.__setattr__('chemical', chemical)
		self.__setattr__('orig_smiles', orig_smiles)

		return self.__dict__




class ChemInfo(object):
	"""
	Suggested class for organizing chemical info in CTS.
	Captures the objects and key:vals used for obtaining
	chemical data.
	"""
	def __init__(self, chemical=None):
		self.chem_obj = {
			'chemical': chemical,  # user-entered molecule of any chemaxon format
			'orig_smiles': "",  # 'chemical' converted to smiles (pre-filtering)
			'smiles': "",  # result of orig_smiles after cts filtering (standardized smiles)
			'preferredName': "",
			'iupac': "",
			'formula': "",
			'cas': "",
			'dtxsid': "",
			'mass': "",
			'exactMass': ""
		}


	def get_cheminfo(self, request_post):
		"""
		Makes call to Calculator for chemaxon
		data. Converts incoming structure to smiles,
		then filters smiles, and then retrieves data
		:param request:
		:return: chemical details response json

		Note: Due to marvin sketch image data (<cml> image) being
		so large, a bool, "structureData", is used to determine
		whether or not to grab it. It's only needed in chem edit tab.
		"""
		# Updated cheminfo workflow with actorws:
		###########################################################################################
		# 1. Determine if user's chemical is smiles, cas, or drawn
		# 		a. If smiles, get gsid from actorws chemicalIdentifier endpoint
		#		b. If cas, get chem data from actorws dsstox endpoint
		#		c. If drawn, get smiles from chemaxon, then gsid like in a.
		# 2. Check if request from 1. "matched" (exist?)
		#		a. If 1b returns cas result, get cheminfo from dsstox results
		#		b. If 1a or 1c, use gsid from chemicalIdentifier and perform step 1b for dsstox cheminfo
		# 3. Use dsstox results: curated CAS#, SMILES, preferredName, iupac, and dtxsid
		#		a. Display in chemical editor.
		#############################################################################################

		chemical = request_post.get('chemical')
		get_sd = request_post.get('get_structure_data')  # bool for getting <cml> format image for marvin sketch
		is_node = request_post.get('is_node')  # bool for tree node or not

		actorws = ACTORWS()
		calc = Calculator()

		# 1. Determine chemical type from user (e.g., smiles, cas, name, etc.):
		chem_type = calc.get_chemical_type(chemical)

		logging.info("Incoming chemical to CTS standardizer: {}".format(chemical))
		logging.info("Chemical type: {}".format(chem_type))

		_gsid = None
		_smiles_from_mrv = False
		_name_or_smiles = chem_type['type'] in ['name', 'common', 'smiles']  # bool for chemical in name/common or smiles format
		_actor_results = {}  # final key:vals from actorws: smiles, iupac, preferredName, dsstoxSubstanceId, casrn

		# Checking type for next step:
		if chem_type['type'] == 'mrv':
			logging.info("Getting SMILES from jchem web services..")
			response = calc.convertToSMILES({'chemical': chemical})
			chemical = response['structure']
			logging.info("SMILES of drawn chemical: {}".format(chemical))
			_smiles_from_mrv = True

		if _name_or_smiles or _smiles_from_mrv:
			logging.info("Getting gsid from actorws chemicalIdentifier..")
			chemid_results = actorws.get_chemid_results(chemical)  # obj w/ keys calc, prop, data
			_gsid = chemid_results.get('data', {}).get('gsid')
			logging.info("gsid from actorws chemid: {}".format(_gsid))

		# Should be CAS# or have gsid from chemid by this point..
		if _gsid or chem_type['type'] == 'CAS#':
			id_type = 'CAS#'
			if _gsid:
				chem_id = _gsid  # use gsid for ACTORWS request
				id_type = 'gsid'
			else:
				chem_id = chemical  # use CAS# for ACTORWS request
			logging.info("Getting results from actorws dsstox..")
			dsstox_results = actorws.get_dsstox_results(chem_id, id_type)  # keys: smiles, iupac, preferredName, dsstoxSubstanceId, casrn 
			_actor_results.update(dsstox_results)

		# If user enters something other than SMILES, use actorws smiles for orig_smiles
		orig_smiles = ""
		if chem_type['type'] == 'smiles':
			orig_smiles = chemical  # use user-entered smiles as orig_siles
		elif 'smiles' in _actor_results.get('data', {}):
			orig_smiles = _actor_results['data']['smiles']  # use actorws smiles as orig_smiles
			logging.info("Using actorws smiles as original smiles..")
		else:
			logging.info("smiles not in user request or actorws results, getting from jchem ws..")
			orig_smiles = calc.convertToSMILES({'chemical': chemical}).get('structure')

		filtered_smiles = SMILESFilter().filterSMILES(orig_smiles)

		logging.info("Original smiles before cts filtering: {}".format(orig_smiles))
		logging.info("Filtered SMILES: {}".format(filtered_smiles))

		jchem_response = calc.getChemDetails({'chemical': filtered_smiles})  # get chemical details

		molecule_obj = Molecule().createMolecule(chemical, orig_smiles, jchem_response, get_sd)

		# Loop _actor_results, replace certain keys in molecule_obj with actorws vals:
		for key, val in _actor_results.get('data', {}).items():
			if key != 'iupac' and key != 'smiles':
				# using chemaxon 'iupac' instead of actorws
				molecule_obj[key] = val  # replace or add any values from chemaxon deat

		for key in actorws.dsstox_result_keys:
			if key not in molecule_obj:
				molecule_obj.update({key: "N/A"})  # fill in any missed data from actorws with "N/A"

		if is_node:
			molecule_obj.update({'node_image': calc.nodeWrapper(filtered_smiles, MetabolizerCalc().tree_image_height, MetabolizerCalc().tree_image_width, MetabolizerCalc().image_scale, MetabolizerCalc().metID,'svg', True)})
			molecule_obj.update({
				'popup_image': Calculator().popupBuilder(
					{"smiles": filtered_smiles}, 
					MetabolizerCalc().metabolite_keys, 
					"{}".format(request_post.get('id')),
					"Metabolite Information")
			})

		wrapped_post = {
			'status': True,  # 'metadata': '',
			'data': molecule_obj,
			'request_post': request_post
		}
		return wrapped_post



class ACTORWS(object):
	"""
	Uses actor web services to obtain curated
	CAS#, SMILES, preferred name, iupac, and DTXSID.
	Location: https://actorws.epa.gov/actorws/
	"""
	def __init__(self):
		self.base_url = "https://actorws.epa.gov/actorws"
		self.chemid_url = "https://actorws.epa.gov/actorws/chemIdentifier/v01/resolve.json"  # ?identifier=[chemical name or SMILES]
		self.dsstox_url = "https://actorws.epa.gov/actorws/dsstox/v02/casTable.json"  # ?identifier=[casrn or gsid]
		self.calc = "actorws"
		self.props = ['dsstox', 'chemid']
		self.chemid_result_keys = ['synGsid']  # chemidentifier result key of interest
		self.dsstox_result_keys = ['casrn', 'dsstoxSubstanceId', 'preferredName', 'smiles', 'iupac']
		self.result_obj = {
			'calc': "actorws",
			'prop': "",
			'data': {},
		}

	def make_request(self, url, payload):
		_response = requests.get(url, params=payload, timeout=10)
		if _response.status_code != 200:
			return {'success': False, 'error': "error connecting to actorws", 'data': None} 
		return json.loads(_response.content)


	##### "PUBLIC" METHODS BELOW #####
	def get_dsstox_results(self, chemical, id_type):
		"""
		Makes request to actowws dsstox for the following
		result keys: casrn, dsstoxSubstanceId, preferredName, smiles, and iupac
		Input: cas number or gsid obtained from actorws chemicalIdentifier endpoint
		Output: Dictionary of above result key:vals
		"""
		_payload = {}
		if id_type == 'gsid':
			_payload = {'gsid': chemical}
		elif id_type == 'CAS#':
			_payload = {'casrn': chemical}

		_dsstox_results = self.make_request(self.dsstox_url, _payload)

		logging.warning("DSSTOX RESULTS: {}".format(_dsstox_results))

		try:
			_dsstox_results = _dsstox_results['DataList']['list'][0]
		except Exception as e:
			logging.warning("Error getting dsstox results key:vals: {}".format(e))
			logging.warning("Using only Jchem WS results instead..")
			# raise e  # raise it for now

		_results = self.result_obj
		_results['prop'] = "dsstox"
		for _key, _val in _dsstox_results.items():
			if _key in self.dsstox_result_keys:
				_results['data'][_key] = _val

		return _results

	def get_chemid_results(self, chemical):
		"""
		Makes request to actorws chemicalIdentifier endpoint for
		'synGsid' to be used for dsstox if cas isn't provided by user.

		Inputs: chemical - either a chemical name or smiles
		Output: Dictionary with results_obj keys and synGsid
		"""
		_chemid_results = self.make_request(self.chemid_url, {'identifier': chemical})

		logging.warning("CHEMID RESULTS: {}".format(_chemid_results))

		try:
			_chemid_results = _chemid_results['DataRow']
		except KeyError as e:
			logging.warning("'DataRow' key not found in chemid results.. Returning None..")
			return None

		# what key:vals should be with results??

		_results = self.result_obj
		_results['prop'] = "chemid"
		_result_key = self.chemid_result_keys[0]  # only one key needed for now
		
		if _result_key in _chemid_results:
			_results['data'].update({'gsid': _chemid_results.get(_result_key)})  # getting synGsid key:val

		# todo: add more error handling, waiting to start new cheminfo workflow w/ actorws first..

		return _results




class SMILESFilter(object):
	"""
	This is the smilesfilter.py module as a class and
	clumped in with other classes related to chem info.
	"""

	def __init__(self):
		self.max_weight = 1500  # max weight [g/mol] for epi, test, and sparc
		self.excludestring = {".","[Ag]","[Al]","[Au]","[As]","[As+","[B]","[B-]","[Br-]","[Ca]",
						"[Ca+","[Cl-]","[Co]","[Co+","[Fe]","[Fe+","[Hg]","[K]","[K+","[Li]",
						"[Li+","[Mg]","[Mg+","[Na]","[Na+","[Pb]","[Pb2+]","[Pb+","[Pt]",
						"[Sc]","[Si]","[Si+","[SiH]","[Sn]","[W]"}
		self.return_val = {
			"valid" : False,
			"smiles": "",
			"processedsmiles" : ""
		}

	def is_valid_smiles(self, smiles):

		_return_val = self.return_val
		_return_val['smiles'] = smiles

		if any(x in smiles for x in self.excludestring):
			return _return_val  # metal in smiles, invalid!

		try:
			processed_smiles = self.filterSMILES(smiles)
		except Exception as e:
			logging.warning("!!! Error in smilesfilter {} !!!".format(e))
			raise "smiles filter exception, possibly invalid smiles..."
				
		_return_val["valid"] = True
		_return_val["processedsmiles"] = processed_smiles

		return _return_val


	def singleFilter(self, request_obj):
		"""
		Calls single EFS Standardizer filter
		for filtering SMILES
		"""
		try:
			smiles = request_obj.get('smiles')
			action = request_obj.get('action')
		except Exception as e:
			logging.info("Exception retrieving mass from jchem: {}".format(e))
			raise
		post_data = {
			"structure": smiles,
			"actions": [
				action
			]
		}
		url = Calculator().efs_server_url + Calculator().efs_standardizer_endpoint
		return Calculator().web_call(url, post_data)


	def filterSMILES(self, smiles):
		"""
		cts ws call to jchem to perform various
		smiles processing before being sent to
		p-chem calculators
		"""

		logging.info("{} is being processed by cts SMILES filter..".format(smiles))

		# Updated approach (todo: more efficient to have CTSWS use major taut instead of canonical)
		# 1. CTSWS actions "removeExplicitH" and "transform".
		url = Calculator().efs_server_url + Calculator().efs_standardizer_endpoint
		post_data = {
			'structure': smiles,
			'actions': [
				"removeExplicitH",
				"transform"
			]
		}
		response = Calculator().web_call(url, post_data)

		logging.info("1. Removing explicit H, then transforming..")
		logging.info("request to jchem: {}".format(post_data))
		logging.info("response from jchem: {}".format(response))

		filtered_smiles = response['results'][-1] # picks last item, format: [filter1 smiles, filter1 + filter2 smiles]

		logging.info("filtered smiles so far: {}".format(filtered_smiles))
		
		# 2. Get major tautomer from jchem:
		taut_obj = Tautomerization()
		taut_obj.postData.update({'calculationType': 'MAJOR'})
		taut_obj.make_data_request(filtered_smiles, taut_obj)

		logging.info("2. Obtaining major tautomer from {}".format(filtered_smiles))
		logging.info("request to jchem: {}".format(taut_obj.postData))
		logging.info("response from jchem: {}".format(taut_obj.results))

		# todo: verify this is major taut result smiles, not original smiles for major taut request...
		major_taut_smiles = None
		try:
			major_taut_smiles = taut_obj.results['result']['structureData']['structure']
		except KeyError as e:
			logging.warning("Jchem error requesting major tautomer from {}..".format(filtered_smiles))
			logging.warning("Exception: {}".format(e))
			logging.warning("Using smiles {} for next step..".format(filtered_smiles))

		if major_taut_smiles:
			logging.info("Major tautomer found: {}.. Using as filtered smiles..".format(major_taut_smiles))
			filtered_smiles = major_taut_smiles

		# 3. Using major taut smiles for final "neutralize" filter:
		post_data = {
			'structure': filtered_smiles, 
			'actions': [
				"neutralize"
			]
		}
		response = Calculator().web_call(url, post_data)

		logging.info("3. Neutralizing smiles {}".format(filtered_smiles))
		logging.info("request to jchem: {}".format(post_data))
		logging.info("response from jchem: {}".format(response))

		final_smiles = response['results'][-1]
		logging.info("smiles results after cts filtering: {}".format(response.get('results')))
		logging.warning("FINAL FITERED SMILES: {}".format(final_smiles))

		return final_smiles


	def checkMass(self, chemical):
		"""
		returns true if chemical mass is less
		than 1500 g/mol
		"""
		logging.info("checking mass..")
		try:
			json_obj = Calculator().getMass({'chemical': chemical}) # get mass from jchem ws
		except Exception as e:
			logging.warning("!!! Error in checkMass() {} !!!".format(e))
			raise e
		logging.info("mass response data: {}".format(json_obj))
		struct_mass = json_obj['data'][0]['mass']
		logging.info("structure's mass: {}".format(struct_mass))

		if struct_mass < 1500  and struct_mass > 0:
			return True
		else:
			return False


	def clearStereos(self, smiles):
		"""
		clears stereoisomers from smiles
		"""
		try:
			response = self.singleFilter({'smiles':smiles, 'action': "clearStereo"})
			filtered_smiles = response['results'] # get stereoless structure
		except Exception as e:
			logging.warning("!!! Error in clearStereos() {} !!!".format(e))
			raise e
		return filtered_smiles


	def transformSMILES(self, smiles):
		"""
		N(=O)=O >> [N+](=O)[O-]
		"""
		try:
			response = self.singleFilter({'smiles':smiles, 'action': "transform"})
			filtered_smiles = response['results'] # get stereoless structure
		except Exception as e:
			logging.warning("!!! Error in transformSMILES() {} !!!".format(e))
			raise e
		return filtered_smiles


	def untransformSMILES(self, smiles):
		"""
		[N+](=O)[O-] >> N(=O)=O
		"""
		try:
			response = self.singleFilter({'smiles':smiles, 'action': "untransform"})
			filtered_smiles = response['results'] # get stereoless structure
		except Exception as e:
			logging.warning("!!! Error in untransformSMILES() {} !!!".format(e))
			raise e
		return filtered_smiles


	def parseSmilesByCalculator(self, structure, calculator):
		"""
		Calculator-dependent SMILES filtering!
		"""
		logging.info("Parsing SMILES by calculator..")
		filtered_smiles = structure

		#1. check structure mass..
		if calculator != 'chemaxon':
			logging.info("checking mass for: {}...".format(structure))
			if not self.checkMass(structure):
				logging.info("Structure too large, must be < 1500 g/mol..")
				raise "Structure too large, must be < 1500 g/mol.."

		#2-3. clear stereos from structure, untransform [N+](=O)[O-] >> N(=O)=O..
		if calculator == 'epi' or calculator == 'sparc' or calculator == 'measured':
			try:
				# clear stereoisomers:
				filtered_smiles = self.clearStereos(structure)
				logging.info("stereos cleared: {}".format(filtered_smiles))

				# transform structure:
				filtered_smiles = str(filtered_smiles[-1])
				filtered_smiles = str(self.untransformSMILES(filtered_smiles)[-1])
				logging.info("structure transformed..")
			except Exception as e:
				logging.warning("!!! Error in parseSmilesByCalculator() {} !!!".format(e))
				raise e

		# 4. Check for metals and stuff (square brackets):
		if calculator == 'epi' or calculator == 'measured':
			if '[' in filtered_smiles or ']' in filtered_smiles:
				# bubble up to calc for handling error
				raise Exception("{} cannot process metals...".format(calculator))

		return filtered_smiles