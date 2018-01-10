from gpiozero import LED, Button
from pyownet import protocol
from time import sleep, time
# import datetime
import pyfttt
import rrdtool
#import sys
import logging, logging.handlers
import configparser
import os

flagRun = True
flagWasRunning = True
flagManual = False
flagGarage = True
flagGarageProtect = False
callBedrooms = False
callBathrooms = False
callGarage = False
setpointGarage = None
secStopCallGarage = 0
secStopCallBedrooms = 0
secStartGaragePump = 0
secStopGaragePump = 0
secStartBedroomsPump = 0
secReadTempsLast = 0
secNotifyGarageTempLast = 0
secRRDTempLast = 0
secCheckConfigLast = 0
secConfigFile = 0

LOG_FILE        = '/home/pi/boiler.log'
logger = logging.getLogger('logger')
logger.setLevel(logging.DEBUG)
logformatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
loghandler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=524288, backupCount=5)
loghandler.setFormatter(logformatter)
logger.addHandler(loghandler)

outBoiler = LED(4)
outBedroomsPump = LED(17)
outBedroomsFan = LED(18)
outBathroomsPump = LED(27)
outGaragePump = LED(22)
outGarageFan = LED(23)
outMBaRecirc = LED(24)
#outRelay8 = LED(25)

inCallBedrooms = Button(8, bounce_time=0.02)
inCallBathrooms = Button(7, bounce_time=0.02)

def configRead():
    global flagGarage, flagRun
    global tempBoilerReturnMin, tempBoilerReturnMinGarage, deadbandBoiler
    global setpointGarage, deadbandGarage, tempFreezeProtect
    global secGarageProtectColdOn, secGarageProtectColdOff, secGarageProtectHotOn, secGarageProtectHotOff
    global secPreheatGarage, secPurgeGaragePump, secPurgeGarageFan
    global secPreheatBedrooms, secPurgeBedroomsPump, secPurgeBedroomsFan
    global hrExercise, secUpdate, secRRDTempLoop
    global secConfigCheckLoop, secReadTempsLoop
    global secNotifyGarageTempTimeout
    global IFTTT_KEY, IFTTT_EVENT 
    global ID_PROBE, ID_BOILER_RETURN, ID_BOILER_SUPPLY
    global ID_GARAGE_SUPPLY, ID_GARAGE_RETURN, ID_GARAGE_AIR
    global ID_OUTSIDE_AIR, ID_BATH_SUPPLY   
          
    cfgParser.read('/home/pi/boiler.config')
    cfg=cfgParser['DEFAULT']
    tempBoilerReturnMin = float(cfg['tempboilerreturnmin'])
    deadbandGarage = cfgParser.getfloat('GARAGE','deadbandgarage')
    tempFreezeProtect = cfgParser.getfloat('GARAGE','tempFreezeProtect')
    tempBoilerReturnMinGarage = cfgParser.getfloat('GARAGE','tempboilerreturnmingarage')
    secPreheatGarage = cfgParser.getfloat('GARAGE','secpreheatgarage')
    secPurgeGaragePump = cfgParser.getfloat('GARAGE','secpurgegaragepump')
    secPurgeGarageFan = cfgParser.getfloat('GARAGE','secpurgegaragefan')
    secGarageProtectColdOn = cfgParser.getfloat('GARAGE','secGarageProtectColdOn')
    secGarageProtectColdOff = cfgParser.getfloat('GARAGE','secGarageProtectColdOff')
    secGarageProtectHotOn = cfgParser.getfloat('GARAGE','secGarageProtectHotOn')
    secGarageProtectHotOff = cfgParser.getfloat('GARAGE','secGarageProtectHotOff')
    deadbandBoiler = float(cfg['deadbandboiler'])
    secPreheatBedrooms = float(cfg['secpreheatbedrooms'])
    secPurgeBedroomsPump = float(cfg['secpurgebedroomspump'])
    secPurgeBedroomsFan = float(cfg['secpurgebedroomsfan'])
    hrExercise = float(cfg['hrexercise'])
    secUpdate = float(cfg['secupdate'])
    secReadTempsLoop = float(cfg['secReadTempsLoop'])
    secRRDTempLoop = float(cfg['secrrdtemploop'])
    secConfigCheckLoop = float(cfg['secconfigcheckloop'])
    secNotifyGarageTempTimeout = float(cfg['secNotifyGarageTempTimeout'])
    IFTTT_KEY = cfg['ifttt_key'] #dMU6-1cYu6tDnxg91rl6F5'
    IFTTT_EVENT  = cfg['ifttt_event'] # 'boiler'
    ID_PROBE         = cfg['id_probe'] # '28.F542E1020000'
    ID_BOILER_RETURN = cfg['id_boiler_return'] # '28.13FBCE030000'
    ID_BOILER_SUPPLY = cfg['id_boiler_supply'] # ''
    ID_BATH_SUPPLY = cfg['id_bath_supply'] # ''
    ID_GARAGE_SUPPLY = cfg['id_garage_supply'] # ''
    ID_GARAGE_RETURN = cfg['id_garage_return'] # ''
    ID_GARAGE_AIR    = cfg['id_garage_air'] # '28.00E639040000' 
    ID_OUTSIDE_AIR   = cfg['id_outside_air']
    if flagGarage != cfgParser.getboolean('STATE', 'enable_garage'):
        flagGarage = cfgParser.getboolean('STATE', 'enable_garage')
        logger.info('Config changed: enable_garage {0}'.format(flagGarage))
    if setpointGarage != cfgParser.getfloat('STATE','setpointgarage'):
        setpointGarage = cfgParser.getfloat('STATE','setpointgarage')
        logger.info('Config changed: setpointGarage, now {0}'.format(setpointGarage))
    if flagRun != cfgParser.getboolean('STATE','enable_overall'):
        flagRun = cfgParser.getboolean('STATE','enable_overall')
        logger.info('Config changed: enable_overall {0}'.format(flagRun))

def checkConfig():
    global secConfigFile
    if os.path.getmtime('/home/pi/boiler.config') != secConfigFile:
        secConfigFile = os.path.getmtime('/home/pi/boiler.config')
        configRead()
        logger.info('updated parameters from config file')

def readTemp(target):
    try:
        return float(ow.read('/{0}/temperature'.format(target)))
    except protocol.OwnetError:
        logger.error('OwnetError, sensor {0} not present?'.format(target))
    except:
        pass
        logger.error('unknown error reading sensor: {0}'.format(target))
    
def startCallBedrooms():
    logger.debug('startCallBedrooms')
    global callBedrooms 
    callBedrooms = True

def stopCallBedrooms():
    logger.debug('stopCallBedrooms')
    global callBedrooms
    callBedrooms = False
    global secStopCallBedrooms 
    secStopCallBedrooms = time()

def startCallBathrooms():
    logger.debug('startCallBathrooms')
    global callBathrooms
    callBathrooms = True
    
def stopCallBathrooms():
    logger.debug('stopCallBathrooms')
    global callBathrooms 
    callBathrooms = False

def garageCheck():
    global secStopCallGarage
    global callGarage
    if flagGarage and isinstance(tempGarageAir, float):
        if tempGarageAir < setpointGarage - deadbandGarage/2:
            if not callGarage:
                logger.debug('call Garage')
                callGarage = True
        elif tempGarageAir > setpointGarage + deadbandGarage/2:
            if callGarage:
                secStopCallGarage = time()
                logger.debug('uncall Garage')
            callGarage = False
    else:
        if callGarage:
            secStopCallGarage = time()
            logger.debug('disabling Garage')
        callGarage = False


def bathroomsCheck():
    global callBathrooms
    if inCallBathrooms.is_pressed:
        if not callBathrooms:
            logger.debug('call Bathrooms')
        callBathrooms = True
    else:
        if callBathrooms:
            logger.debug('uncall Bathrooms')
        callBathrooms = False

def bedroomsCheck():
    global callBedrooms, secStopCallBedrooms
    if inCallBedrooms.is_pressed:
        if not callBedrooms:
            logger.debug('call Bedrooms')
        callBedrooms = True
    else:
        if callBedrooms:
            secStopCallBedrooms = time()
            logger.debug('uncall Bedrooms')
        callBedrooms = False

def rrd_temps():
    if len(ID_BOILER_SUPPLY)>0 and isinstance(tempBoilerSupply,float):
        try:
            rrdtool.update('--daemon','192.168.1.75','temp_BS.rrd','N:%s' %(tempBoilerSupply))
        except:
            logger.warning('failure to update rrd tempBoilerSupply')
    if len(ID_BOILER_RETURN)>0 and isinstance(tempBoilerReturn,float):
        try:
            rrdtool.update('--daemon','192.168.1.75','temp_BR.rrd','N:%s' %(tempBoilerReturn))
        except:
            logger.warning('Warning: failure to update rrd tempBoilerReturn')
    if len(ID_BATH_SUPPLY)>0 and isinstance(tempBathSupply,float):
        try:
            rrdtool.update('--daemon','192.168.1.75','temp_BaS.rrd','N:%s' %(tempBathSupply))
        except:
            logger.warning('failure to update rrd tempBathSupply')
    if len(ID_GARAGE_AIR)>0 and isinstance(tempGarageAir,float):
        try:
            rrdtool.update('--daemon','192.168.1.75','temp_GA.rrd','N:%s' %(tempGarageAir))
        except:
            logger.warning('Warning: failure to update rrd tempGarageAir')
    if len(ID_GARAGE_SUPPLY)>0 and isinstance(tempGarageSupply,float):
        try:
            rrdtool.update('--daemon','192.168.1.75','temp_GS.rrd','N:%s' %(tempGarageSupply))
        except:
            logger.warning('Warning: failure to update rrd tempGarageSupply')
    if len(ID_GARAGE_RETURN)>0 and isinstance(tempGarageReturn,float):
        try:
            rrdtool.update('--daemon','192.168.1.75','temp_GR.rrd','N:%s' %(tempGarageReturn))
        except:
            logger.warning('Warning: failure to update rrd tempGarageReturn')
    if len(ID_OUTSIDE_AIR)>0 and isinstance(tempOutsideAir,float):
        try:
            rrdtool.update('--daemon','192.168.1.75','temp_OA.rrd','N:%s' %(tempOutsideAir))
        except:
            logger.warning('Warning: failure to update rrd tempOutsideAir')

def read_temps():
    global tempBoilerSupply, tempBoilerReturn 
    global tempGarageAir, tempGarageSupply, tempGarageReturn
    global tempOutsideAir, tempBathSupply
    if len(ID_BOILER_SUPPLY)>0:
        tempBoilerSupply = readTemp(ID_BOILER_SUPPLY)
    if len(ID_BOILER_RETURN)>0:
        tempBoilerReturn = readTemp(ID_BOILER_RETURN)
    if len(ID_BATH_SUPPLY)>0:
        tempBathSupply = readTemp(ID_BATH_SUPPLY)
    if len(ID_GARAGE_AIR)>0:
        tempGarageAir = readTemp(ID_GARAGE_AIR)
    if len(ID_GARAGE_SUPPLY)>0:
        tempGarageSupply = readTemp(ID_GARAGE_SUPPLY)
    if len(ID_GARAGE_RETURN)>0:
        tempGarageReturn = readTemp(ID_GARAGE_RETURN)
    if len(ID_OUTSIDE_AIR)>0:
        tempOutsideAir = readTemp(ID_OUTSIDE_AIR)

def manualOps():
        global flagManual
        if not flagManual:
            try:
                pyfttt.send_event(IFTTT_KEY,IFTTT_EVENT,'Entered manual operation')
            except:
                logger.error('error sending IFTTT message')
            flagManual = True
        if callBedrooms or callBathrooms:
            outBoiler.on()
        else:
            outBoiler.off()
        if callBedrooms:
            outBedroomsPump.on()
            outBedroomsFan.on()
        else:
            outBedroomsPump.off()
            outBedroomsFan.off()

        if callBathrooms:
            outBathroomsPump.on()
        else:
            outBathroomsPump.off()
        outGaragePump.blink(secGarageProtectHotOn, secGarageProtectHotOff)
        outGarageFan.off()

def stopAll():
    global flagWasRunning
    flagWasRunning = False
    logger.info('stopped all outputs')
    outBoiler.off()
    outBedroomsPump.off()
    outBedroomsFan.off()
    outBathroomsPump.off()
    outGaragePump.off()
    outGarageFan.off()

if __name__ == '__main__':
    ow = protocol.proxy()
    cfgParser=configparser.ConfigParser()
    configRead()
    
    try:
        pyfttt.send_event(IFTTT_KEY,IFTTT_EVENT,'Boiler service started')
    except:
        logger.error('error sending IFTTT startup message')

    while True:
        secStartLoop = time()
        if time() - secReadTempsLast  > secReadTempsLoop:
            read_temps()
            if not isinstance(tempGarageAir, float):
                logger.error('unknown Garage temperature')
                if time() - secNotifyGarageTempLast > secNotifyGarageTempTimeout:
                    try:
                        pyfttt.send_event(IFTTT_KEY,IFTTT_EVENT,'unknown Garage temperature')
                    except:
                        logger.error('error sending IFTTT message')
                    secNotifyGarageTempLast = time()
            secReadTempsLast = time()
        garageCheck()
        bathroomsCheck()
        bedroomsCheck()
        if flagRun and isinstance(tempBoilerReturn, float):
            if flagManual:
                try:
                    pyfttt.send_event(IFTTT_KEY,IFTTT_EVENT,'Reentered automatic mode')
                except:
                    logger.error('error sending IFTTT message')
                flagManual = False

            if callBedrooms or callBathrooms or callGarage:
                outBoiler.on()
            else:
                outBoiler.off()

            if tempBoilerReturn < tempBoilerReturnMin - deadbandBoiler/2:
                outBedroomsPump.off()
                outBedroomsFan.off()
                outBathroomsPump.off()
                if not flagGarageProtect:
                    outGaragePump.off()
                outGarageFan.off()
            else:
                if callBedrooms:
                    if tempBoilerReturn > tempBoilerReturnMin + deadbandBoiler/2:
                        if not outBedroomsPump.is_active:
                            secStartBedroomsPump = time()
                        outBedroomsPump.on()

                    if time() - secStartBedroomsPump > secPreheatBedrooms:
                        outBedroomsFan.on()
                else:
                    if time() - secStopCallBedrooms > secPurgeBedroomsPump:
                        outBedroomsPump.off()
                    if time() - secStopCallBedrooms > secPurgeBedroomsFan:
                        outBedroomsFan.off()

                if callBathrooms:
                    if tempBoilerReturn > tempBoilerReturnMin + deadbandBoiler/2:
                        outBathroomsPump.on()
                else:
                    outBathroomsPump.off()

                if callGarage:
                    if (not callBedrooms) and \
                        (tempBoilerReturn > tempBoilerReturnMin + deadbandBoiler/2):
                        if not outGaragePump.is_active:
                            secStartGaragePump = time()
                        outGaragePump.on()
                    elif tempBoilerReturn > tempBoilerReturnMinGarage + deadbandBoiler/2:
                        if not outGaragePump.is_active:
                            secStartGaragePump = time()
                        outGaragePump.on()
                    if time() - secStartGaragePump > secPreheatGarage:
                        outGarageFan.on()
                else:
                    if time() - secStopCallGarage > secPurgeGaragePump and not flagGarageProtect:
                        outGaragePump.off()
                    if time() - secStopCallGarage > secPurgeGarageFan and outGarageFan.is_active:
                        outGarageFan.off()
            if isinstance(tempGarageAir, float):
                if tempGarageAir < tempFreezeProtect:
                    if not flagGarageProtect:
                        flagGarageProtect = True
                        logger.info('Garage freeze protect started')
                    if tempBoilerReturn < tempBoilerReturnMin or not outBoiler.is_active:
                        secOn = secGarageProtectColdOn
                        secOff = secGarageProtectColdOff
                    else:
                        secOn = secGarageProtectHotOn
                        secOff = secGarageProtectHotOff
                    if outGaragePump.is_active:
                        if time() - secStartGaragePump > secOn:
                            outGaragePump.off()
                            logger.debug('freezeProtect stop')
                            secStopGaragePump = time()
                    else:
                        if time() - secStopGaragePump > secOff:
                            outGaragePump.on()
                            secStartGaragePump = time()
                            logger.debug('freezeProtect run')
                elif tempGarageAir > tempFreezeProtect + 2:
                    if flagGarageProtect:
                        flagGarageProtect = False
                        logger.info('Garage freeze protect ended')
        elif flagRun:
            manualOps()
        elif flagWasRunning:
            stopAll()
        if time () - secRRDTempLast > secRRDTempLoop:
            rrd_temps() 
            secRRDTempLast = time()
        if time() - secCheckConfigLast > secConfigCheckLoop: 
            checkConfig()
            secCheckConfigLast = time()
        while time() - secStartLoop < secUpdate:
            sleep(0.1)
        
