import math
import sys
from datetime import *

import scipy.stats as sc
from scipy.optimize import fmin

#from dbfpy import dbf
import sqlite3

#currently there are at least three groundwater level modelling software models, so the files containing parameters are different
#the first is called a4metqm and it needs to calibrate 20 parameters
#the second is called metul0204 with 22 parameters (two additional parameters (DPERC, BETA) correcting groundwater percolation)
#the third is not implemented here yet - called metulInsol with 23 parameters (additional parameter (AMELTCOR) correcting snowmelt)

class pyMetul:

    def __init__(self, name):
        self.name=name
	self.meteoDate=[]
        self.params=[]  #liste, 1D masiivs, satur visus metul parametrus
        self.state=[]   #liste, 1D masiivs, satur saakuma veertiibas modeleeshanai
        self.paramFName=""   #strings, parametru faila nosaukums
        self.stateFName=""   #strings, state faila nosaukums
        self.meteoFName=""   #strings, metoe faila nosaukums
        self.temperature=[]     #liste, 1D masiivs, satur visus nolasiitos temperatuuras no self.meteoFName
        self.precipitation=[]   #liste, 1D masiivs, satur visus nolasiitos nokrisnus no self.meteoFName
        self.humidityDef=[]     #liste, 1D masiivs, satur visus nolasiitos mitruma deficiitus no self.meteoFName
        self.humidity=[]
	self.gwLevel=[]        #liste, 2D masiivs, satur apreekjinaatos gruntsuudens liimenju rezultaatus
        self.ObservationFName="" #strings, obs.faila nosaukums
        self.modType=int()
        self.paramValuesForOptimisation=[] #liste, 1D masiivs, satur parametru veertiibas, kas jaainterpolee
        self.paramKeysForOptimisation=[]        #liste, 1D masiivs, satur 
        self.startDate = ""
	self.xCoord=int()
	self.yCoord=int()
	self.zCoord=int()
	self.observations=[]

    ########################################
    #
    # metode, 1 arguments - parametru faila atrashanaas vieta
    # 1 arguments - parametru faila atrashanaas vieta. sagatavo 22 inicializacijas parametrus masiivaa
    # self.params
    # atgriezh TRUE/FALSE, ja ir/nav veiksmiigi izdevies nolasiit failu,
    #
    ########################################
    def readParamFile(self, paramFName):
        try:
            self.paramFName=paramFName
            f=open(paramFName)
            f.readlines
            for line in f:      
                self.params.append(float(line))
            return True
        except ioError:
            print "Unable to read parameter file", paramFName
            return False
    
    
    ####################
    #
    #metode, 1 arguments - state faila atrashanaas vieta
    #1 arguments - state faila atrashanaas vieta. sagatavo triis inicializacijas parametrus
    #self.sn
    #self.sm
    #self.gw
    #atgriezh TRUE/FALSE, ja ir/nav veiksmiigi izdevies nolasiit failu,
    #
    ####################
    def readStateFile(self,stateFName):

        self.stateFName=stateFName
        try:   
            f=open(stateFName)
            f.readlines
            for line in f:
                self.state.append(float(line))
            self.state=self.state[6:]
            return True
        except IOError:
            print "Unable to read state file", stateFName
            return False
    
          
    #########################
    #
    #metode
    #1 arguments - meteofaila atrashanaas vieta. sagatavo triis listes
    #self.temperature
    #self.precipitation
    #self.humidityDef
    #atgriezh TRUE/FALSE, ja ir/nav veiksmiigi izdevies nolasiit failu,
    #
    #########################
    def readMeteoFile(self, meteoFName):      
        try:
            f=open(meteoFName)        
            f.readlines
            for line in f:
                self.temperature.append(float(line[9:17]))
                self.precipitation.append(float(line[17:25]))
                self.humidityDef.append(float(line[25:len(line)]))
            return True
        except IOError:
            print "Unable to read meteo file"
            return False


    ############################
    #
    # Nolasa no ekselja noveerojumus.
    # Uzlabojams, parametrus jaapievieno - no kurienes, sheeta utt.
    #
    ############################
    def readObservations(self,xlsFName):
        print
        print "=-=-=-=READING OBSERVATIONS FROM EXCEL=-=-="
        print
        fails=open(xlsFName, 'rb')
        self.observations=fails.readlines()
        for i in range(len(self.observations)):
            self.observations[i]=self.observations[i].replace(",",".")
            self.observations[i]=self.observations[i].rstrip()            
        self.observations=map(float,self.observations)

        


    def readParamsFromXLS(self,xlsFName,sheetName,headRowCount,paramCol):
        #Iespeeja importeet 22 parametrus no Excel faila. Kaa ievades parametri -
        #excel faila nosaukums/atrasanaas vieta
        #excel sheet nosaukums
        #header rindu skaits. ja headera nav, tad 0, ja ir, tad veertiiba tik liela, cik daudz rindas.
        #paramCol - parametru kolonna
        
        print
        print "=-=-=-=READING PARAMETERS FROM EXCEL=-=-=-="
        print
        try:
            import xlrd           
            print "opening:", xlsFName
            wb=xlrd.open_workbook(xlsFName)
            print xlsFName, "successfully opened for reading parameters"
            print "searching for sheet:", sheetName        
            sh=wb.sheet_by_name(sheetName)
            print "sheet found"
            print "gathering parameters from column:", paramCol        
            parameterList= sh.col_values(paramCol)
            self.params=parameterList[headRowCount:22+headRowCount]
            print "params successfully gathered"
        except ImportError:
            print "you dont have associated module xlrd installed. please download and install it from http://www.lexicon.net/sjmachin/xlrd.htm", self.readDataFromXLS
        except IOError:
            print "unable to import from excel file", self.readDataFromXLS
        except:
            print "impossible to work with current excel file", self.readDataFromXLS
        print
        print "=-=-=-==-=-=-==-=-=-="
        print
        


    ###########################
    #
    # Iespeeja importeet meteodatus no excel dokumenta. Kaa ievades parametri -
    # excel faila nosaukums/atrasanaas vieta
    # excel sheet nosaukums
    # header rindu skaits. ja headera nav, tad 0, ja ir, tad veertiiba tik liela, cik daudz rindas.
    # tempCol - temperatuuras kolonna
    # precipCol - nokrisnu kolonna
    # humidDefCol - mitruma deficiita kolonna
    # saakuma datums
    #
    ###########################
    def readDataFromXLS(self,xlsFName,sheetName,headRowCount,tempCol,precipCol,humidDefCol):

        print
        print "=-=-=-=READING METEODATA FROM EXCEL=-=-=-="
        print
        try:
            import xlrd
	    import datetime
            print "opening:", xlsFName
            wb=xlrd.open_workbook(xlsFName)
            print xlsFName, "successfully opened for reading meteo data"
            print "searching for sheet:", sheetName
            sh=wb.sheet_by_name(sheetName)
            print "sheet found"
            print "gathering information from columns:", tempCol, precipCol, humidDefCol
            temperatureList= sh.col_values(tempCol)
            precipitationList=sh.col_values(precipCol)
            humidDefList=sh.col_values(humidDefCol)
            
            datums=sh.cell(rowx=headRowCount,colx=0).value

            year, month, day, hour, minute, second = xlrd.xldate_as_tuple(datums,wb.datemode)
            py_date = datetime.datetime(year, month, day, hour, minute, 0)
            self.startDate=py_date
            
            self.humidityDef=humidDefList[headRowCount:]
            self.temperature=temperatureList[headRowCount:]
            self.precipitation=precipitationList[headRowCount:]
            
            print "temp count-", len(humidDefList), ", precip count-", len(precipitationList), " humid def count-", len(humidDefList)

        except ImportError:
            print "you dont have associated module xlrd installed. please download and install it from http://www.lexicon.net/sjmachin/xlrd.htm", self.readDataFromXLS
        except IOError:
            print "unable to import from excel file", self.readDataFromXLS
        #except:
        #    print "impossible to work with current excel file", self.readDataFromXLS
        print
        print "=-=-=-==-=-=-==-=-=-="
        print
    
    def readStateFromXLS(self,xlsFName,sheetName,headRowCount,stateCol):
        #Iespeeja importeet state inicializaacijas datus no excel dokumenta. Kaa ievades parametri -
        #excel faila nosaukums/atrasanaas vieta
        #excel sheet nosaukums
        #header rindu skaits. ja headera nav, tad 0, ja ir, tad veertiiba tik liela, cik daudz rindas.
        #iniCol - temperatuuras kolonna
        print
        print "=-=-=-=READING STATE FROM EXCEL=-=-=-="
        print
        try:
            import xlrd
            print "opening:", xlsFName
            wb=xlrd.open_workbook(xlsFName)
            print xlsFName, "successfully opened for reading initialisation data"
            print "searching for sheet:", sheetName
            sh=wb.sheet_by_name(sheetName)
            print "sheet found"
            print "gathering information from column:", stateCol
            iniValList= sh.col_values(stateCol)
            
            


            self.state=iniValList[headRowCount:]
            
        except ImportError:
            print "you dont have associated module xlrd installed. please download and install it from http://www.lexicon.net/sjmachin/xlrd.htm", self.readDataFromXLS
        except IOError:
            print "unable to import from excel file", self.readDataFromXLS
        except:
            print "impossible to work with current excel file", self.readDataFromXLS
        print
        print "=-=-=-==-=-=-==-=-=-="
        print
    
    def printParams(self):
        #metode - izdrukaa uz ekraana parametrus
        for parametrs in self.params:
            print parametrs
            
    def printGWLevel(self):
        #metode - izdrukaa uz ekraana apreekinaatos GUL
        for level in self.gwLevel:
            print level
    
    def printState(self):
        #metode - izdrukaa uz ekraana saakuma veertiibas
        for state in self.state:
            print state

    def loadDefaultState(self):
	self.state=[0,0,100]
    
    
    def GCWZ_metul0204(self, PZ, GWB, GWE, RCH, CAP, Q1, Q2, Q3, WZB, WZE, ALFA, A2, A3, DZ, WZEP, Q1SUM, Q2SUM, Q3SUM, QSUM, BETA, DPERC):
        #PZ,GWB,GWE,RCH,CAP,Q1,Q2,Q3,WZB,WZE,ALFA,A2,A3, DZ,WZEP,Q1SUM,Q2SUM,Q3SUM,QSUM
        
        WZE = WZB
       
        for i in range(0, 15):
            if  ( WZB > 0 ) :
                GWB = 10 * ALFA * WZB
            DWZEDZ = WZE - DZ
            if  ( DWZEDZ > 0 ) :
                Q2 = 0
            else:
                
                Q2 = A2 *  (( DZ - WZE )  ** 2)
                
            Q3 = A3 *  ( PZ - WZE )
            GWE = GWB - RCH + Q2 + Q3 + CAP
            WZEP = GWE /  ( 10 * ALFA )
            WZE = ( WZE + WZEP )  / 2
            
        
        #print WZE, WZB, GWE, GWB, DPERC
            
        WZE1 = ( WZE + WZB )  / 2

        Q2 = A2 *  (( DZ - WZE1 )  ** 2)
        ST = DZ - WZE1       
        if  ( ST < 0 ) :
            Q2 = 0
        Q2SUM = Q2SUM + Q2
        Q3 = A3 *  ( PZ - WZE1 )
        Q3SUM = Q3SUM + Q3
        GWE = GWB - RCH + Q2 + Q3 + CAP
                      
        if  (GWE < 0 ) :
            Q1 = Q1 - GWE 
            GWE = GWB - RCH + CAP + Q1 + Q2 + Q3
        Q1SUM = Q1SUM + Q1
        GWE = GWE + DPERC
        QSUM = Q1SUM + Q2SUM + Q3SUM
        WZE = GWE /  ( 10 * ALFA )
        
        
        #PZ, GWB, GWE, RCH, CAP, Q1, Q2, Q3, WZB, WZE, ALFA, A2, A3, DZ, WZEP, Q1SUM, Q2SUM, Q3SUM, QSUM
        D = dict(PZ=PZ, GWB=GWB, GWE=GWE, RCH=RCH, CAP=CAP, Q1=Q1, Q2=Q2, Q3=Q3, WZB=WZB, WZE=WZE, ALFA=ALFA, A2=A2, A3=A3, DZ=DZ, WZEP=WZEP, Q1SUM=Q1SUM, Q2SUM=Q2SUM, Q3SUM=Q3SUM, QSUM=QSUM)
        return D
    
    def GCWZ_A4Metqm(self, PZ, GWB, GWE, RCH, CAP, Q1, Q2, Q3, WZB, WZE, ALFA, A2, A3, DZ, WZEP, Q1SUM, Q2SUM, Q3SUM, QSUM):
        #PZ,GWB,GWE,RCH,CAP,Q1,Q2,Q3,WZB,WZE,ALFA,A2,A3, DZ,WZEP,Q1SUM,Q2SUM,Q3SUM,QSUM
        
        WZE = WZB
       
        for i in range(0, 15):
            if  ( WZB > 0 ) :
                GWB = 10 * ALFA * WZB
            DWZEDZ = WZE - DZ
            if  ( DWZEDZ > 0 ) :
                Q2 = 0
            else:
                Q2 = A2 *  (( DZ - WZE )  ** 2)
                
            Q3 = A3 *  ( PZ - WZE )
            GWE = GWB - RCH + Q2 + Q3 + CAP
            WZEP = GWE /  ( 10 * ALFA )
            WZE = ( WZE + WZEP )  / 2
            
        WZE1 = ( WZE + WZB )  / 2
        Q2 = A2 *  (( DZ - WZE1 )  ** 2)
        ST = DZ - WZE1
        if  ( ST < 0 ) :
            Q2 = 0
        Q2SUM = Q2SUM + Q2
        Q3 = A3 *  ( PZ - WZE1 )
        Q3SUM = Q3SUM + Q3
        GWE = GWB - RCH + Q2 + Q3 + CAP
        Q1 = Q1
        if  ( GWE < 0 ) :
            Q1 = - GWE + Q1
            GWE = GWB - RCH + CAP + Q1 + Q2 + Q3
        Q1SUM = Q1SUM + Q1
        QSUM = Q1SUM + Q2SUM + Q3SUM
        
        
        #PZ, GWB, GWE, RCH, CAP, Q1, Q2, Q3, WZB, WZE, ALFA, A2, A3, DZ, WZEP, Q1SUM, Q2SUM, Q3SUM, QSUM
        D = dict(PZ=PZ, GWB=GWB, GWE=GWE, RCH=RCH, CAP=CAP, Q1=Q1, Q2=Q2, Q3=Q3, WZB=WZB, WZE=WZE, ALFA=ALFA, A2=A2, A3=A3, DZ=DZ, WZEP=WZEP, Q1SUM=Q1SUM, Q2SUM=Q2SUM, Q3SUM=Q3SUM, QSUM=QSUM)
        return D
       
    def ASZ(self, EA, RS, ES, WZB, SMSB, SMSE, RCH, CAP, DEF, WMAX, KU, KL, ZCAP, Q1, ESUM):
        #EA,RS,ES,WZB,SMSB,SMSE,RCH,CAP,DEF,WMAX,KU,KL,ZCAP,Q1,ESUM
        Q1 = 0
        if  ( ES > 0 ) :
            EA = 0
            #DEBUG.PRINT RS
        else:
            DSMSBWMAX = SMSB - WMAX
            if  ( DSMSBWMAX >= 0 ) :
                EA = KU * DEF
            else:
                if  ( SMSB == 0 and WZB >= ZCAP ) :
                    EA = KL * DEF
                DWZBZCAP = WZB - ZCAP
                if  ( DWZBZCAP > 0 ) :
                    EA = DEF *  ( KU -  ( KU - KL )  *  ( 1 - SMSB / WMAX ) )
                else:
                    EA = DEF *  ( KU - WZB *  ( KU - KL )  *  ( 1 - SMSB / WMAX )  / ZCAP )
        CAP = 0
        RCH = 0
        SMSE = SMSB + RS - RCH - EA + CAP
        if  ( SMSE < 0 ) :
            CAP = - SMSE
        SMSE = SMSB + RS - EA - RCH + CAP
        DSMSEWMAX = SMSE - WMAX
        if  ( DSMSEWMAX <= 0 ) :
            ESUM = ESUM + EA
        else:
            RCH = SMSE - WMAX
            Q1 = 0.02 * RCH
            RCH = 0.98 * RCH
            SMSE = SMSB + RS - EA - RCH - Q1 + CAP
            ESUM = ESUM + EA        
        D=dict(EA=EA,RS=RS,ES=ES,WZB=WZB,SMSB=SMSB,SMSE=SMSE,RCH=RCH,CAP=CAP,DEF=DEF,WMAX=WMAX,KU=KU,KL=KL,ZCAP=ZCAP,Q1=Q1,ESUM=ESUM)
        return D
    
    def SNOW(self, SSBC, SSBSK, SSEC, SSESK, RS, ES, P, T, DEF, CMELT, KS, T1, T2, WMELT, WRFR, WHC, WHT, CFR, ESUM, KOP, IZTV, SSBC1):
        if  ( SSBC > 0.001 or T <= T2 ) :
            ES = KS * DEF
            ESUM = ESUM + ES
            SSBSK = SSBSK - ES
            IZTV = 0
            SSBC = SSBC + P
            if  ( SSBSK < 0 ) :
                IZTV = SSBSK
                SSBC = SSBC + IZTV
                IZTV = 0
                SSBSK = 0
            if  ( SSBC < 0 ) :
                ESUM = ESUM + SSBC
                ES = 0.0001
                IZTV = 0
                SSBC = 0
            DT2 = T - T2
            if  ( DT2 <= 0 ) :
                WMELT = 0
                SSEC = SSBC
                WHT = SSEC * WHC
                if  ( SSBSK > 0 ) :
                    if  ( SSBSK > 0 ) :
                        WRFR = CMELT *  ( T2 - T )  * CFR
                    if  ( SSBSK < WRFR ) :
                        WRFR = SSBSK
                        SSESK = 0
                        SSBC = SSBC + WRFR
                    else:
                        SSESK = SSBSK - WRFR
                        if  ( SSESK > WHT ) :
                            RS = SSBSK - WHT
                        else:
                            RS = 0
                            SSEC = SSBC + WRFR
                            if  ( SSEC <= 0 ) :
                                if  ( ES <= 0 ) :
                                    ES = 0.0001
                            D=dict(SSBC=SSBC, SSBSK=SSBSK, SSEC=SSEC, SSESK=SSESK, RS=RS, ES=ES, KS=KS, WMELT=WMELT, WRFR=WRFR, WHC=WHC, WHT=WHT, CFR=CFR, ESUM=ESUM, KOP=KOP, IZTV=IZTV, SSBC1=SSBC1)
                            return D
                        if  ( RS >= 0 ) :
                            SSESK = WHT
                            SSEC = SSBC + WRFR
                            if  ( SSEC <= 0 ) :
                                if  ( ES <= 0 ) :
                                    ES = 0.0001
                        else:
                            RS = 0
                            SSESK = WHT + RS
                            SSEC = SSBC + WRFR
                            if  ( SSEC <= 0 ) :
                                if  ( ES <= 0 ) :
                                    ES = 0.0001
                SSESK = 0
                RS = 0
                SSEC = SSBC
                if  ( SSEC <= 0 ) :
                    if  ( ES <= 0 ) :
                        ES = 0.0001
            else:
                DT1 = T - T1
                if  ( DT1 < 0 ) :
                    if  ( T >= T2 and P > 0 ) :
                        WMELT = 0
                        SSEC = SSBC
                        WHT = SSEC * WHC
                        if  ( SSBSK > WHT ) :
                            RS = SSBSK - WHT
                        else:
                            RS = 0
                            SSESK = SSBSK
                            if  ( SSEC <= 0 ) :
                                if  ( ES <= 0 ) :
                                    ES = 0.0001
                            D=dict(SSBC=SSBC, SSBSK=SSBSK, SSEC=SSEC, SSESK=SSESK, RS=RS, ES=ES, KS=KS, WMELT=WMELT, WRFR=WRFR, WHC=WHC, WHT=WHT, CFR=CFR, ESUM=ESUM, KOP=KOP, IZTV=IZTV, SSBC1=SSBC1)
                            return D
                        if  ( RS >= 0 ) :
                            SSESK = WHT
                            if  ( SSEC <= 0 ) :
                                if  ( ES <= 0 ) :
                                    ES = 0.0001
                        else:
                            RS = 0
                            SSESK = WHT + RS
                            if  ( SSEC <= 0 ) :
                                if  ( ES <= 0 ) :
                                    ES = 0.0001
                    else:
                        if  ( T >= T2 and P == 0 ) :
                            WMELT = CMELT *  ( T - T2 )
                WMELT = CMELT *  ( T - T2 )
                SSBC1 = SSBC - P
                if  ( WMELT > SSBC1 ) :
                    WMELT = SSBC - P
                if  ( WMELT < 0 ) :
                    WMELT = 0
                SSEC = SSBC - WMELT - P
                if  ( SSEC <= 0 ) :
                    SSEC = 0
                WHT = SSEC * WHC
                KOP = SSBSK + WMELT + P
                if  ( SSBSK > WHT ) :
                    SSESK = WHT
                    RS = WMELT + P -  ( WHT - SSBSK )
                    if  ( RS <= 0 ) :
                        RS = 0
                else:
                    if  ( KOP > WHT ) :
                        SSESK = WHT
                        RS = WMELT + P -  ( WHT - SSBSK )
                    else:
                        SSESK = SSBSK + WMELT + P
                        RS = 0
        else:
            WRFR = 0
            WHT = 0
            KOP = 0
            IZTV = 0
            SSBC1 = 0
            SSEC = 0
            SSBC = 0
            SSBSK = 0
            SSESK = 0
            ES = 0
            RS = P
            WMELT = 0
        D=dict(SSBC=SSBC, SSBSK=SSBSK, SSEC=SSEC, SSESK=SSESK, RS=RS, ES=ES, KS=KS, WMELT=WMELT, WRFR=WRFR, WHC=WHC, WHT=WHT, CFR=CFR, ESUM=ESUM, KOP=KOP, IZTV=IZTV, SSBC1=SSBC1)
        return D
               
    def runMetul0204(self):
#metode, darbina gcwz, asz un snow.
#vajadzeetu atgriezt listi ar gruntsuudens liimeniem (WZE - Water zone endOfDay)
        
        #snow
        __SSBC = float()
        __SSBSK = float()
        __SSEC = float()
        __SSESK = float()
        __RS = float()
        __ES = float()
        __P = float()
        __T = float()
        __DEF = float()
        __CMELT = float()
        __KS = float()
        __T1 = float()
        __T2 = float()
        __WMELT = float()
        __WRFR = float()
        __WHC = float()
        __WHT = float()
        __CFR = float()
        __ESUM = float()
        __KOP = float()
        __IZTV = float()
        __SSBC1 = float()
        
        
        #ASZ
        __EA = float()
        __WZB = float()
        __SMSB = float()
        __SMSE = float()
        __RCH = float()
        __CAP = float()
        __WMAX = float()
        __KU = float()
        __KL = float()
        __ZCAP = float()
        __Q1 = float()
        
        
        
        #GCWZ
        __PZ = float()
        __GWB = float()
        __GWE = float()
        __Q2 = float()
        __Q3 = float()
        __WZE = float()
        __ALFA = float()
        __A2 = float()
        __A3 = float()
        __DZ = float()
        __WZEP = float()
        __Q1SUM = float()
        __Q2SUM = float()
        __Q3SUM = float()
        __QSUM = float()
        
        
        
        SSER = 0
        SMSER = 0
        WZER = 100
        
        SSBC = SSER
        SMSB = SMSER
        WZB = WZER
        SSEC = SSER
        SMSE = SMSER
        WZE = WZER
        
        PSUM = 0
        DSUM = 0
        TSUM=0
        Q1SUM = 0
        Q2SUM = 0
        Q3SUM = 0
        QSUM = 0
        NDIEN = 0
        SSBSK = 0
        SSESK = 0
        
        RS=0
        ES=0
        WMELT=0
        WRFR=0
        WHT=0
        ESUM=0
        KOP=0
        IZTV=0
        SSBC1=0
		
        EA=0
        RCH=0
        CAP=0
        Q1=0
        GWB=0
        GWE=0
        Q2=0
        Q3=0
        WZEP=0
        
       
        WMAX=float(self.params[0])
        ALFA=float(self.params[1])
        ZCAP=float(self.params[2])
        A2=float(self.params[3])
        A3=float(self.params[4])
        KU=float(self.params[5])
        KL=float(self.params[6])
        CMELT=float(self.params[7])
        T1=float(self.params[8])
        T2=float(self.params[9])
        KS=float(self.params[10])
        DZ=float(self.params[11])
        PZ=float(self.params[12])
        RCHROB=float(self.params[13])
        RCHROBZ =float(self.params[14])
        RCHROB2 = float(self.params[15])
        RCHROB2Z = float(self.params[16])
        ROBK = float(self.params[17])       
        WHC = float(self.params[18])
        CFR=float(self.params[19])
        BETA=float(self.params[20])
        DPERC=float(self.params[21])

        
        
        
        for T, P, DEF, DATE in map(None,self.temperature,self.precipitation,self.humidityDef, self.meteoDate):
            
            
            PSUM=PSUM+P
            DSUM=DSUM+DEF
            TSUM=TSUM+T
            
            D_SNOW = self.SNOW(SSBC,SSBSK,SSEC,SSESK,RS,ES,P,T,DEF,CMELT,KS,T1,T2,WMELT,WRFR,WHC,WHT,CFR,ESUM,KOP,IZTV,SSBC1)           
            
            SSBC=D_SNOW['SSBC']
            SSBSK=D_SNOW['SSBSK']
            SSEC=D_SNOW['SSEC']
            SSESK=D_SNOW['SSESK']
            RS=D_SNOW['RS']
            ES=D_SNOW['ES']
            
            WMELT=D_SNOW['WMELT']
            WRFR=D_SNOW['WRFR']
            WHC=D_SNOW['WHC']
            WHT=D_SNOW['WHT']
            ESUM=D_SNOW['ESUM']
            KOP=D_SNOW['KOP']
            IZTV=D_SNOW['IZTV']
            SSBC1=D_SNOW['SSBC1']
            
                  
            D_ASZ=self.ASZ(EA, RS, ES, WZB, SMSB, SMSE, RCH, CAP, DEF, WMAX, KU, KL, ZCAP, Q1, ESUM)
            
            EA=D_ASZ['EA']
            RS=D_ASZ['RS']
            ES=D_ASZ['ES']
            WZB=D_ASZ['WZB']
            SMSB=D_ASZ['SMSB']
            SMSE=D_ASZ['SMSE']
            RCH=D_ASZ['RCH']
            CAP=D_ASZ['CAP']
            Q1=D_ASZ['Q1']
            ESUM=D_ASZ['ESUM']
            
            
            
            if  ( SSEC <= 0 ) :
                if  ( RCH < RCHROB ) :
                    Q1 = Q1
                else:
                    QRCH = RCHROB2 * math.tanh(( RCH - RCHROB )  / RCHROB2 / ROBK) + RCHROB
                    QV = RCH - QRCH
                    if  ( QV <= 0 ) :
                        Q1 = Q1
                    if  ( QV > 0 ) :
                        Q1 = Q1 + QV
                    RCH = RCH - QV
            else:
                if  ( RCH < RCHROBZ ) :
                    Q1 = Q1
                else:
                    QRCH = RCHROB2Z * math.tanh(( RCH - RCHROBZ )  / RCHROB2Z / ROBK) + RCHROBZ
                    QV = RCH - QRCH
                    if  ( QV <= 0 ) :
                        Q1 = Q1
                    if  ( QV > 0 ) :
                        Q1 = Q1 + QV
                    RCH = RCH - QV
                    
           
           
#            print PZ,GWB,GWE,RCH,CAP,Q1,Q2,Q3,WZB,WZE,ALFA,A2,A3,DZ,WZEP,BETA,DPERC,Q1SUM,Q2SUM,Q3SUM,QSUM
            D_GCWZ=self.GCWZ_metul0204(PZ, GWB, GWE, RCH, CAP, Q1, Q2, Q3, WZB, WZE, ALFA, A2, A3, DZ, WZEP, Q1SUM, Q2SUM, Q3SUM, QSUM, BETA, DPERC)
            

            GWB=D_GCWZ['GWB']
            GWE=D_GCWZ['GWE']   
            RCH=D_GCWZ['RCH']
            CAP=D_GCWZ['CAP']
            Q1=D_GCWZ['Q1']
            Q2=D_GCWZ['Q2']
            Q3=D_GCWZ['Q3']
            WZB=D_GCWZ['WZB']
            WZE=D_GCWZ['WZE']
            WZEP=D_GCWZ['WZEP']
            Q1SUM=D_GCWZ['Q1SUM']
            Q2SUM=D_GCWZ['Q2SUM']
            Q3SUM=D_GCWZ['Q3SUM']
            QSUM=D_GCWZ['QSUM']
	    
            self.gwLevel[0].append(DATE)
            self.gwLevel[1].append(WZE)
	    
            
            SSBC = SSEC     #sniega sega
            SSBSK = SSESK   #sniega sega
            SMSB = SMSE     #aktiivaa zona
            WZB = WZE       #piesaatinaataa zona
            
        print "done"

    def runA4Metqm(self):
        self.resetResults()
        #metode, darbina gcwz, asz un snow.
        #vajadzeetu atgriezt listi ar gruntsuudens liimeniem (WZE - Water zone endOfDay)
        
        #snow
        __SSBC = float()
        __SSBSK = float()
        __SSEC = float()
        __SSESK = float()
        __RS = float()
        __ES = float()
        __P = float()
        __T = float()
        __DEF = float()
        __CMELT = float()
        __KS = float()
        __T1 = float()
        __T2 = float()
        __WMELT = float()
        __WRFR = float()
        __WHC = float()
        __WHT = float()
        __CFR = float()
        __ESUM = float()
        __KOP = float()
        __IZTV = float()
        __SSBC1 = float()
        
        
        #ASZ
        __EA = float()
        __WZB = float()
        __SMSB = float()
        __SMSE = float()
        __RCH = float()
        __CAP = float()
        __WMAX = float()
        __KU = float()
        __KL = float()
        __ZCAP = float()
        __Q1 = float()
        
        
        
        #GCWZ
        __PZ = float()
        __GWB = float()
        __GWE = float()
        __Q2 = float()
        __Q3 = float()
        __WZE = float()
        __ALFA = float()
        __A2 = float()
        __A3 = float()
        __DZ = float()
        __WZEP = float()
        __Q1SUM = float()
        __Q2SUM = float()
        __Q3SUM = float()
        __QSUM = float()
        
        
        
        SSER = 0
        SMSER = 0
        WZER = 100
        
        SSBC = SSER
        SMSB = SMSER
        WZB = WZER
        SSEC = SSER
        SMSE = SMSER
        WZE = WZER
        
        PSUM = 0
        DSUM = 0
        TSUM=0
        Q1SUM = 0
        Q2SUM = 0
        Q3SUM = 0
        QSUM = 0
        NDIEN = 0
        SSBSK = 0
        SSESK = 0
        
        RS=0
        ES=0
        WMELT=0
        WRFR=0
        WHT=0
        ESUM=0
        KOP=0
        IZTV=0
        SSBC1=0
        EA=0
        RCH=0
        CAP=0
        Q1=0
        GWB=0
        GWE=0
        Q2=0
        Q3=0
        WZEP=0
        
       
        WMAX=float(self.params[0])
        ALFA=float(self.params[1])
        ZCAP=float(self.params[2])
        A2=float(self.params[3])
        A3=float(self.params[4])
        KU=float(self.params[5])
        KL=float(self.params[6])
        CMELT=float(self.params[7])
        T1=float(self.params[8])
        T2=float(self.params[9])
        KS=float(self.params[10])
        DZ=float(self.params[11])
        PZ=float(self.params[12])
        RCHROB=float(self.params[13])
        RCHROBZ =float(self.params[14])
        RCHROB2 = float(self.params[15])
        RCHROB2Z = float(self.params[16])
        ROBK = float(self.params[17])       
        WHC = float(self.params[18])
        CFR=float(self.params[19])


        for T, P, DEF, DATE in map(None,self.temperature,self.precipitation,self.humidityDef, self.meteoDate):
            
            
            PSUM=PSUM+P
            DSUM=DSUM+DEF
            TSUM=TSUM+T
            
            D_SNOW = self.SNOW(SSBC,SSBSK,SSEC,SSESK,RS,ES,P,T,DEF,CMELT,KS,T1,T2,WMELT,WRFR,WHC,WHT,CFR,ESUM,KOP,IZTV,SSBC1)           
            
            SSBC=D_SNOW['SSBC']
            SSBSK=D_SNOW['SSBSK']
            SSEC=D_SNOW['SSEC']
            SSESK=D_SNOW['SSESK']
            RS=D_SNOW['RS']
            ES=D_SNOW['ES']
            
            WMELT=D_SNOW['WMELT']
            WRFR=D_SNOW['WRFR']
            WHC=D_SNOW['WHC']
            WHT=D_SNOW['WHT']
            ESUM=D_SNOW['ESUM']
            KOP=D_SNOW['KOP']
            IZTV=D_SNOW['IZTV']
            SSBC1=D_SNOW['SSBC1']
            
                  
            D_ASZ=self.ASZ(EA, RS, ES, WZB, SMSB, SMSE, RCH, CAP, DEF, WMAX, KU, KL, ZCAP, Q1, ESUM)
            
            EA=D_ASZ['EA']
            RS=D_ASZ['RS']
            ES=D_ASZ['ES']
            WZB=D_ASZ['WZB']
            SMSB=D_ASZ['SMSB']
            SMSE=D_ASZ['SMSE']
            RCH=D_ASZ['RCH']
            CAP=D_ASZ['CAP']
            Q1=D_ASZ['Q1']
            ESUM=D_ASZ['ESUM']
            
            
            
            if  ( SSEC <= 0 ) :
                if  ( RCH < RCHROB ) :
                    Q1 = Q1
                else:
                    QRCH = RCHROB2 * math.tanh(( RCH - RCHROB )  / RCHROB2 / ROBK) + RCHROB
                    QV = RCH - QRCH
                    if  ( QV <= 0 ) :
                        Q1 = Q1
                    if  ( QV > 0 ) :
                        Q1 = Q1 + QV
                    RCH = RCH - QV
            else:
                if  ( RCH < RCHROBZ ) :
                    Q1 = Q1
                else:
                    QRCH = RCHROB2Z * math.tanh(( RCH - RCHROBZ )  / RCHROB2Z / ROBK) + RCHROBZ
                    QV = RCH - QRCH
                    if  ( QV <= 0 ) :
                        Q1 = Q1
                    if  ( QV > 0 ) :
                        Q1 = Q1 + QV
                    RCH = RCH - QV
                    
           
            
#            print PZ,GWB,GWE,RCH,CAP,Q1,Q2,Q3,WZB,WZE,ALFA,A2,A3,DZ,WZEP,BETA,DPERC,Q1SUM,Q2SUM,Q3SUM,QSUM
            D_GCWZ=self.GCWZ_A4Metqm(PZ, GWB, GWE, RCH, CAP, Q1, Q2, Q3, WZB, WZE, ALFA, A2, A3, DZ, WZEP, Q1SUM, Q2SUM, Q3SUM, QSUM)
            

            GWB=D_GCWZ['GWB']
            GWE=D_GCWZ['GWE']   
            RCH=D_GCWZ['RCH']
            CAP=D_GCWZ['CAP']
            Q1=D_GCWZ['Q1']
            Q2=D_GCWZ['Q2']
            Q3=D_GCWZ['Q3']
            WZB=D_GCWZ['WZB']
            WZE=D_GCWZ['WZE']
            WZEP=D_GCWZ['WZEP']
            Q1SUM=D_GCWZ['Q1SUM']
            Q2SUM=D_GCWZ['Q2SUM']
            Q3SUM=D_GCWZ['Q3SUM']
            QSUM=D_GCWZ['QSUM']
	    
            self.gwLevel.append([DATE,WZE])

            
            SSBC = SSEC     #sniega sega
            SSBSK = SSESK   #sniega sega
            SMSB = SMSE     #aktiivaa zona
            WZB = WZE       #piesaatinaataa zona
        #print "modelling with a4metqm successful"

    def resetResults(self):
        self.gwLevel=[]





    #########################
    #
    # funkcija, kas veic apreekjinu un atgriezh piirsona R veertiibu. jo tuvaak nullei, jo labaaka sakritiiba
    # 1)paarkopee parametrus
    # 2)palaizh attieciigo apreekinu
    # 3)korigee apreekinu attieciibaa pret noveerojumiem
    # 4)apreekina piirsona R
    #
    #########################    
    def objectiveFunction(self, parameterValuesForOptimisation):
        
        self.paramValuesForOptimisation=parameterValuesForOptimisation[:]       #nokopee parametrus, ko atgrieziis autokalibraacija ieksh objekta iipashiibas
        self.blendOptimisedParameters()                            		#iekljauj optimizeetos parametrus kopeejaa parametru masiivaa

        if (self.modType==0):
            self.runA4Metqm()
        else:
            self.runMetul0204()

        self.correctData(self.gwLevel,self.observations)
        result=self.corelation()
        return 1-result




    #############
    #
    # metode - veikt optimizaaciju. atrastie parametri peec metodes buus objektaa (laikam)
    # abos (.params un .paramValuesForOptimisation) masiivos
    #
    #############
    def optimisation(self):
        optimisedParams=fmin(self.objectiveFunction,self.paramValuesForOptimisation,xtol=0.0000000000001)




    ###########
    #
    # ieksheeja metode, iekljauj optimizeetos parametrus peec to atsleegas kopeejaa parametru masiivaa.
    # pirms tam jaabuut izdariitam .setParamKeysForOptimisation
    #
    ###########    
    def blendOptimisedParameters(self):
        i=0
        for atsleega in self.paramKeysForOptimisation:             #katrai atziimeetajai atsleegai ieksh atsleegu masiiva
            #print m.params[atsleega]
            self.params[atsleega]=self.paramValuesForOptimisation[i]  #kopeejaa parametru masiivaa pieshkirt veertiibu no atziimeeto parametru masiiva
            #print m.paramValuesForOptimisation[i]
            i+=1



    ##################
    #
    # funkcija, kura
    # definee optimizeejamos parametrus (opt atsleegas masiivs) un
    # pieshkir tiem saakuma veertiibu (opt veertiibu masiivs).
    #
    # jaaizdara vienreiz, pirms optimizeeshanas.
    #
    ##################
    def setParamKeysForOptimisation(self,masiivs):
        self.paramKeysForOptimisation=masiivs[:]                   # kuri no parametriem jaaoptimizee (atsleegas masiivs)
        for value in self.paramKeysForOptimisation:                #kaadas ir sho parametru veertiibas (no parametru masiiva peec atsleegas masiiva)
            self.paramValuesForOptimisation.append(self.params[value])#  
        
        #m.paramValuesForOptimisation=map()


    def loadDefaultParameters(self):
	self.params=[80,0.046,320,0.05,0.0064,0.55,0.2,2,0.5,-1,0.2,122,269,8,1,12,6,1.5,0.1,1.2,2,10]

    
    def saveParamsInMYSQLite(self, fname):
	con = sqlite3.connect(fname)
	
	sqlValues=self.params[:]
	sqlValues.reverse()
	sqlValues.append(self.zCoord)
	sqlValues.append(self.yCoord)
	sqlValues.append(self.xCoord)
	sqlValues.append(self.name)
	sqlValues.reverse()
	
	with con:    
	    cur = con.cursor()    
	    cur.execute('''
	    CREATE TABLE IF NOT EXISTS objekts
	    (
	    Name TEXT,
	    xCoord REAL,
	    yCoord REAL,
	    zCoord REAL,
	    WMAX REAL,
	    ALFA REAL,
	    ZCAP REAL,
	    A2 REAL,
	    A3 REAL,
	    KU REAL,
	    KL REAL,
	    CMELT REAL,
	    T1 REAL,
	    T2 REAL,
	    KS REAL,
	    DZ REAL,
	    PZ REAL,
	    RCHROB REAL,
	    RCHROBZ REAL,
	    RCHROB2 REAL,
	    RCHROB2Z REAL,
	    ROBK REAL,
	    WHC REAL,
	    CFR REAL,
	    BETA REAL,
	    DPERC REAL
	    )
	    ''')
	
	    cur.execute("INSERT INTO objekts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",sqlValues)
	
	con.commit()

        
    
    def readMeteoFromSQLite(self,stationName="",startDate=None,endDate=None,meteoDbName=None,borrowHum=None):
        
        if meteoDbName==None:
            con = sqlite3.connect('meteo.db')
        else:
            con = sqlite3.connect(meteoDbName)

	
	
        with con:
            cur = con.cursor()
            if (startDate==None) and (endDate==None):				#------var padot bez datumiem
                if borrowHum!=None:
		    cur.execute("Select * from "+stationName+" where T!='' and P!=''")
		    rows=cur.fetchall()
		    cur.execute("Select Date, Hum from "+borrowHum+" where Hum!=''")
		    rows2=cur.fetchall()
		    rows=self.changeHum(rows,rows2)
		    
		else:    
		    cur.execute("Select * from "+stationName+" where Hum!='' and T!='' and P!=''")
		    rows=cur.fetchall()
            else:
                startDate=datetime.strptime(startDate, '%Y.%m.%d')              #------ja ir padoti abi datumi
                endDate=datetime.strptime(endDate, '%Y.%m.%d')
                if borrowHum!=None:
		    cur.execute("SELECT * from "+stationName+" where Date>'"+str(startDate)+"' and Date<'"+str(endDate)+"' and T!='' and P!=''")
		    rows = cur.fetchall()
		    cur.execute("SELECT * from "+borrowHum+" where Date>'"+str(startDate)+"' and Date<'"+str(endDate)+"' and Hum!=''")
		    rows2 = cur.fetchall()
		    rows=self.changeHum(rows,rows2)
		    
		else:
		    cur.execute("SELECT * from "+stationName+" where Date>'"+str(startDate)+"' and Date<'"+str(endDate)+"' and Hum!='' and T!='' and P!=''")
		    rows = cur.fetchall()
        
        #print "wtf" #kur ir mans wtf :D
        for row in rows:
            self.meteoDate.append(row[0])
            self.temperature.append(row[1])
            self.precipitation.append(row[2])
            self.humidity.append(row[3])


    def changeHum(self, array1, array2):
	""" Paliigfunkcija, kas aizvieto relatiivo mitrumu no citas meteostacijas"""

	tmpDateArray=[]
	tmpHumArray=[]
	tmpResArray=[]
	
	for each in array2:			#sadala 2D masiivu pa 1D masiiviem - vienaa datumi, otraa veertiibas
	    tmpDateArray.append(each[0])
	    tmpHumArray.append(each[1])

	for each in array1:
	    if (each[0] in tmpDateArray) and (each[3]==""): #izprintee tos 2.masiiva hum, kad 1.masiivam hum nav, bet datumi atbilst
		tmpResArray.append([each[0],each[1],each[2],tmpHumArray[ tmpDateArray.index(each[0])]])
		#print each[0], each[1],each[2], tmpHumArray[tmpDateArray.index(each[0])]
	    elif (each[3]!=""):
		tmpResArray.append([each[0], each[1], each[2], each[3]])
		#print each[0], each[1], each[2], each[3]
	
	return tmpResArray	
	

    def relMitrumsToDeficits(self):
        #print "=(EXP((17,3*temperatura)/(temperatura+237,3))*6,11)*(1-(relatMitrums/100))"      
        self.humidityDef=[]
        for t, h,date in zip(self.temperature, self.humidity,self.meteoDate):
		#print t,h,date #seit
		self.humidityDef.append((math.exp((17.3*t)/(t+237.3))*6.11)*(1-(h/100)))



    def get_date(self, record):
        return datetime.strptime(record, '%Y-%m-%d %H:%M:%S')



    def isDecimal(self, str):
        try:
            Decimal(str)
            return True
        except Exception as x:
            return False


    def correctData(self, mas, mas2):

        dataArray = []
        saraksts = list()
        garaisMasivs=mas2[:]                        #============korekta masiivu kopeeshana ir izmantojot [:]
        isaisMasivs=mas[:]
        xi=0                                        #==========iisaa masiiva counteris
        yi=0                                        #==========garaa masiiva counteris
        yc=0                                        #==========garaa masiiva countera counteris :D
        garaMasivaGarums=len(garaisMasivs)-1        #======miinus viens, jo masiivaa pirmais ir nultais elements
        isaMasivaGarums=len(isaisMasivs)-1

	
        tmpGarais=[]
        tmpIsais=[]
        tmpArray=[[]*3 for x in xrange(3)]          #========definee 2d masiivu
        while xi<=isaMasivaGarums:                  #========divi while cikli viens ieksh otra. flowcontrols taads, ka tikai vienu reizi iziet cauri
                                                    #========masiivam atrodot vai nu elements ir "agraak", "veelaak", vai sakriit.
                    yi=yc
                    while yi<=garaMasivaGarums:     #==========cikls, kursh skataas, vai visi garaa masiiva elementi apskatiiti; to  pasaka yi (gara masiiva) counteris
                                    if self.get_date(isaisMasivs[xi][0])<self.get_date(garaisMasivs[yi][0]):
                                                    yi=len(garaisMasivs) #======break aizstaajeejs, ja ir lielaaks, tad pa taisno iet no garaa masiiva cikla aaraa                                               
                                    elif self.get_date(isaisMasivs[xi][0])>self.get_date(garaisMasivs[yi][0]):
                                                    yi+=1           #=========naakoshais garaa masiiva elements svariigs.
                                                    yc=yi           #=========NO kura elementa turpinaat iisajaa masiivaaa!
                                                    
                                    else:
                                                    tmpGarais.append(garaisMasivs[yi][1])
                                                    tmpIsais.append(isaisMasivs[xi][1])
                                                    tmpArray[0].append(garaisMasivs[yi][1])
                                                    tmpArray[1].append(isaisMasivs[xi][1])
						    tmpArray[2].append(isaisMasivs[xi][0])	#===pievieno dienu kaa tresho 
                                                    break
    
                    xi=xi+1
        self.valuesForCorrelation=tmpArray[:]
	return "valuesForCorrelation OK"


    def corelation(self):
        return sc.pearsonr(self.valuesForCorrelation[0], self.valuesForCorrelation[1])[0]


    def saveGWInFile(self, name):
        f=open(name, 'w')
        for item in self.gwLevel:
            f.write(str(str(item[0])+"\t"+str(item[1])+"\n"))

    def saveObsInFile(self, name):
        f=open(name, 'w')
        for item in self.observations:
            f.write(str(str(item[0])+"\t"+str(item[1])+"\n"))
            
    def saveBothInFile(self,name):
        import os
	
	fullPath= os.getcwd()+"\\both\\"
	if not(os.path.exists(fullPath)):os.makedirs(fullPath)
	
	f=open(fullPath+name,'w')    
	for a,b,c in zip(self.valuesForCorrelation[2],self.valuesForCorrelation[0],self.valuesForCorrelation[1]):
	    f.write(str(str(a)+"\t"+str(b)+"\t"+str(c)+"\n"))
    
    def longTermMonthlyAverage(self):
    #This function creates a monthly average from list with
    #such structure (["%Y-%m-%d %H:%M:%S", float],["%Y-%m-%d %H:%M:%S", float]..)
    
	tmpMonthArray=[[]*12 for x in xrange(12)]
	resultArray=[]
	for eachPair in self.gwLevel:
	    #print eachPair[0]
	    dateObjekts=datetime.strptime(eachPair[0],"%Y-%m-%d %H:%M:%S")
	    menesis=dateObjekts.month
	    tmpMonthArray[menesis-1].append(eachPair[1])
	i=1
	for each in tmpMonthArray:
	    resultArray.append([i,sum(each)/len(each)])
	    i+=1    
	return resultArray


    def loadFutureMeteoData(self,stationName,startDate,endDate,climScenId):
	
	#print stationName,startDate,endDate,climScenId
	con = sqlite3.connect('futureMeteo.db')
	startDate=datetime.strptime(startDate, '%Y-%m-%d')		#------ja ir padoti abi datumi
        endDate=datetime.strptime(endDate, '%Y-%m-%d')
	
	
        with con:
	    cur = con.cursor()
	    #Select * from Dagda join klimScenNames where klimScenID=id and datums>'2035-01-01 00:00:00' and datums<'2045-01-01 00:00:00' and name='pirmais'
            #cur.execute("Select * from "+str(stationName)+" where datums>"+str(startData)+" and datums<"+str(endData)+" and klimScenID="+str(climScenId))
	    #cur.execute("Select * from "+str(stationName)+" where datums>'"+str(startDate)+"' and datums<'"+str(endDate)+"' and klimScenID="+str(climScenId))
	    cur.execute("Select datums, T, P, Hum from "+str(stationName)+"\
	    join klimScenIDs where\
	    klimScenID=id\
	    and T!=''\
	    and P!=''\
	    and Hum!=''\
	    and datums>'"+str(startDate)+"'\
	    and datums<'"+str(endDate)+"'\
	    and klmScenName='"+str(climScenId)+"'") #paarbaudi peec tam vai pareizi ir tie - T, P un Hum uzrakstiiti ;)
	    rows=cur.fetchall()
	
	self.meteoDate=[]
	self.temperature=[]
	self.precipitation=[]
	self.humidity=[]
	for row in rows:
	    self.meteoDate.append(row[0])
            self.temperature.append(row[1])
            self.precipitation.append(row[2])
            self.humidity.append(row[3])
