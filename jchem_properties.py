import requests
import json
import logging
import os
from jchem_rest import getStructInfo
# from jchem_calculator import ChemaxonCalc


# class Pka(ChemaxonCalc):
class Pka(object):
    def __init__(self):
        self.results = ''
        # ChemaxonCalc.__init__(self)
        self.name = 'pKa'
        self.url = '/webservices/rest-v0/util/calculate/pKa'
        self.postData = {
            "pHLower": 0.0,
            "pHUpper": 14.0,
            "pHStep": 0.1,
            "temperature": 298.0,
            "micro": False,
            "considerTautomerization": True,
            "pKaLowerLimit": 0.0,
            "pKaUpperLimit": 14.0,
            "prefix": "DYNAMIC"
        }

    def getMostAcidicPka(self):
        """
		Picks out pKa acidic value(s), returns list
		"""
        pkaValList = []
        if 'mostAcidic' in self.results:
            # logging.info("$ type: {} $".format(self.results['mostAcidic']))
            for pkaVal in self.results['mostAcidic']:
                pkaValList.append(pkaVal)
            return pkaValList
        else:
            logging.warning("key: 'mostAcidic' not in self.results")
            return pkaValList

    def getMostBasicPka(self):
        """
		Picks out pKa Basic value(s), returns list
		"""
        pkaValList = []
        if 'mostBasic' in self.results:
            for pkaVal in self.results['mostBasic']:
                pkaValList.append(pkaVal)
            return pkaValList
        else:
            logging.warning("no key 'mostBasic' in results")
            return pkaValList

    def getParent(self):
        """
		Gets parent image from result and adds structure
		info such as formula, iupac, mass, and smiles.
		Returns dict with keys: image, formula, iupac, mass, and smiles
		"""
        try:
            parentDict = {'image': self.results['result']['image']['image'], 'key': 'parent'}
            parentDict.update(getStructInfo(self.results['result']['structureData']['structure']))
            return parentDict
        except KeyError as ke:
            logging.warning("key error: {}".format(ke))
            return None

    def getMicrospecies(self):
        """
		Gets microspecies from pKa result and appends 
		structure info (i.e., formula, iupac, mass, and smiles)
		Returns list of microspeceies as dicts
		with keys: image, formula, iupac, mass, and smiles
		"""
        if 'microspecies' in self.results:
            try:
                msList = []
                for ms in self.results['microspecies']:
                    msStructDict = {}  # list element in msList
                    msStructDict.update({'image': ms['image']['image'], 'key': ms['key']})
                    structInfo = getStructInfo(ms['structureData']['structure'])
                    msStructDict.update(structInfo)
                    msList.append(msStructDict)
                return msList
            except KeyError as ke:
                logging.info("> key error: {}".format(ke))
                return None
        else:
            logging.info("no microspecies in results")
            return None

    def getChartData(self):
        if 'chartData' in self.results:
            microDistData = {}  # microspecies distribution data
            for ms in self.results['chartData']:
                valuesList = []  # format: [[ph1,con1], [ph2, con2], ...] per ms
                for vals in ms['values']:
                    xy = []  # [ph1, con1]
                    xy.append(vals['pH'])
                    xy.append(100.0 * vals['concentration'])  # convert to %
                    valuesList.append(xy)
                microDistData.update({ms['key']: valuesList})
            return microDistData
        else:
            return None


# class IsoelectricPoint(ChemaxonCalc):
class IsoelectricPoint(object):
    def __init__(self):
        self.results = ''
        # ChemaxonCalc.__init__(self)
        self.name = 'isoelectricPoint'
        self.url = '/webservices/rest-v0/util/calculate/isoelectricPoint'
        self.postData = {
            "pHStep": 0.1,
            "doublePrecision": 2
        }

    def getIsoelectricPoint(self):
        """
		Returns isoelectricPoint value from results
		"""
        try:
            return self.results['isoelectricPoint']
        except KeyError:
            logging.warning("key 'isoelectricPoint' not in results")
            return None

    def getChartData(self):
        """
		Returns isoelectricPoint chart data
		"""
        valsList = []
        try:
            for pt in self.results['chartData']['values']:
                xyPair = []
                for key, value in pt.items():
                    xyPair.append(value)
                valsList.append(xyPair)
        except KeyError as ke:
            logging.warning("key error: {}".format(ke))
            return valsList
        else:
            return valsList


# class MajorMicrospecies(ChemaxonCalc):
class MajorMicrospecies(object):
    def __init__(self):
        self.results = ''
        # ChemaxonCalc.__init__(self)
        self.name = 'majorMicrospecies'
        self.url = '/webservices/rest-v0/util/calculate/majorMicrospecies'
        self.postData = {
            "pH": 7.0,
            "takeMajorTautomericForm": False
        }

    def getMajorMicrospecies(self):
        majorMsDict = {}
        try:
            majorMsDict.update({'image': self.results['result']['image']['image'], 'key': 'majorMS'})
            structInfo = getStructInfo(self.results['result']['structureData']['structure'])
            majorMsDict.update(structInfo)  # add smiles, iupac, mass, formula key:values
            return majorMsDict
        except KeyError as ke:
            logging.warning("key error: {}".format(ke))
            return None


# class Tautomerization(ChemaxonCalc):
class Tautomerization(object):
    def __init__(self):
        self.results = ''
        # ChemaxonCalc.__init__(self)
        self.name = 'tautomerization'
        self.url = '/webservices/rest-v0/util/calculate/tautomerization'
        self.postData = {
            "calculationType": "DOMINANT",
            # "calculationType": "MAJOR",
            "maxStructureCount": 1000,
            "considerPH": False,
            "enableMaxPathLength": True,
            "maxPathLength": 4,
            "rationalTautomerGenerationMode": False,
            "singleFragmentMode": True,
            "protectAromaticity": True,
            "protectCharge": True,
            "excludeAntiAromaticCompounds": True,
            "protectDoubleBondStereo": False,
            "protectAllTetrahedralStereoCenters": False,
            "protectLabeledTetrahedralStereoCenters": False,
            "protectEsterGroups": True,
            "ringChainTautomerizationAllowed": False
        }

    def getTautomers(self):
        """
        returns dict w/ key 'tautStructs' and
        value is a list of tautomer images
        """
        tautDict = {'tautStructs': [None]}
        tautImageList = []
        try:
            # expecting list of result objects:
            # for taut in self.results['result']:
            # taut = self.results['result']  # single result object

            tauts = self.results['result']  # for DOMINANT tautomers

            # logging.warning("taut instance: {}".format(isinstance(taut, list)))

            # if isinstance(taut, list):
            #     taut = taut[0]
                
            # tautStructDict = {'image': taut['image']['image'], 'key': 'taut'}
            
            # structInfo = getStructInfo(taut['structureData']['structure'])
            # tautStructDict.update(structInfo)
            # # tautStructDict.update({'dist': 100 * round(taut['dominantTautomerDistribution'], 4)})
            # tautImageList.append(tautStructDict)


            # 10-19-16 request by Eric
            for taut in tauts:
                tautStructDict = {'image': taut['image']['image'], 'key': 'taut'}
                structInfo = getStructInfo(taut['structureData']['structure'])
                tautStructDict.update(structInfo)
                tautStructDict.update({'dist': 100 * round(taut['dominantTautomerDistribution'], 4)})
                tautImageList.append(tautStructDict)

            tautDict.update({'tautStructs': tautImageList})
            return tautImageList
        except KeyError as ke:
            logging.warning("key error: {}".format(ke))
            return None


# class Stereoisomer(ChemaxonCalc):
class Stereoisomer(object):
    def __init__(self):
        self.results = ''
        # ChemaxonCalc.__init__(self)
        self.name = 'stereoisomer'
        self.url = '/webservices/rest-v0/util/calculate/stereoisomer'
        self.postData = {
            "stereoisomerismType"
            # "stereobjecte": "TETRAHEDRAL",
            "maxStructureCount": 100,
            "protectDoubleBondStereo": False,
            "protectTetrahedralStereo": False,
            "filterInvalid3DStructures": False
        }

    def getStereoisomers(self):
        stereoList = []
        try:
            for stereo in self.results['result']:
                stereoDict = {'image': stereo['image']['image'], 'key': 'stereo'}
                structInfo = getStructInfo(stereo['structureData']['structure'])
                stereoDict.update(structInfo)
                stereoList.append(stereoDict)
            return stereoList
        except KeyError as ke:
            logging.warning("key error: {} @ jchem rest".format(ke))
            return None


# class Solubility(ChemaxonCalc):
class Solubility(object):
    def __init__(self):
        self.results = ''
        # ChemaxonCalc.__init__(self)
        self.name = 'solubility'
        self.url = '/webservices/rest-v0/util/calculate/solubility'
        self.postData = {
            "pHLower": 0.0,
            "pHUpper": 14.0,
            "pHStep": 0.1,
            "unit": "MGPERML"
        }

    def getIntrinsicSolubility(self):
        """
		Gets water solubility for chemaxon
		"""
        try:
            # logging.info("getting solubility from: {}".format(self.results))
            return 1000.0 * self.results['intrinsicSolubility']
        except KeyError as ke:
            logging.warning("key error: {}".format(ke))
            return None

    def getPHDependentSolubility(self, ph=7.0):
        """
        Gets ph-dependent water solubility
        """
        try:
            # logging.info("getting solubility from: {}".format(self.results))
            ws_list = self.results['pHDependentSolubility']['values']
            ph = float(ph)
            for item in ws_list:
                item_ph = item['pH']
                item_ws = item['solubility']
                # logging.info("ph: {}, ws: {}".format(item_ph, item_ws))
                # logging.info("types for ph: {}, ws: {}".format(type(item_ph), type(item_ws)))
                if item_ph == ph:
                    # logging.info("getting solubility: {} at ph: {}".format(item_ws, item_ph))
                    return item_ws
            return "N/A"
            # return 1000.0 * self.results['intrinsicSolubility']
        except KeyError as ke:
            logging.warning("key error: {}".format(ke))
            return None

    def convertLogToMGPERL(self, log_val, mass):
        """
        Converts WS values of Log into mg/L.
        Units of mass in mol/g
        """
        logging.info("MASS FOR CONVERSION: {}".format(mass))
        logging.info("LOG VAL FOR CONVERSION: {}".format(log_val))
        return 1000 * float(mass) * 10**(log_val)



# class LogP(ChemaxonCalc):
class LogP(object):
    def __init__(self):
        self.results = ''
        # ChemaxonCalc.__init__(self)
        self.name = 'logP'
        self.url = '/webservices/rest-v0/util/calculate/logP'
        self.methods = ['KLOP', 'VG', 'PHYS']
        # logging.info("METHOD: {}".format(method))
        # if not method:
        #     logging.info("using WEIGHTED method for logP..")
        #     method = self.methods[3]
        # if not (method in self.methods): 
        #     key_err = "method {} not recognized as a method for logP ({}).."
        #     logging.warning(key_err.format(method, self.methods))
        #     raise KeyError(key_err.format(method, self.methods))
        self.postData = {
            "wVG": 1.0,
            "wKLOP": 1.0,
            "wPHYS": 1.0,
            "Cl": 0.1,
            "NaK": 0.1,
            "considerTautomerization": False
        }

    def getLogP(self):
        """
		Gets pH-independent kow
		"""
        try:
            return self.results['logpnonionic']
        except KeyError as ke:
            logging.warning("ker error: {}".format(ke))
            return None


# class LogD(ChemaxonCalc):
class LogD(object):
    def __init__(self):
        self.results = ''
        # ChemaxonCalc.__init__(self)
        self.name = 'logD'
        self.url = '/webservices/rest-v0/util/calculate/logD'
        self.methods = ['KLOP', 'VG', 'PHYS']
        self.postData = {
            "pHLower": 0.0,
            "pHUpper": 14.0,
            "pHStep": 0.1,
            "wVG": 1.0,
            "wKLOP": 1.0,
            "wPHYS": 1.0,
            "Cl": 0.1,
            "NaK": 0.1,
            "considerTautomerization": False
        }

    def getLogD(self, ph):
        """
		Gets pH-dependent kow
		"""
        try:
            ph = float(ph)
            chartDataList = self.results['chartData']['values']
            for xyPair in chartDataList:
                if xyPair['pH'] == round(ph, 1):
                    value = xyPair['logD']
                    break
            return value
        except KeyError as ke:
            logging.warning("key error: {}".format(ke))
            return None