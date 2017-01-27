from gpiozero import LED, Button
from pyownet import protocol
from time import sleep, time
# import datetime
from Adafruit_IO import MQTTClient, Client
import pyfttt
import rrdtool
#import sys
import logging, logging.handlers
import configparser
import os

flagRun = True
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
secPublishTempLast = 0
secPublishStatusLast = 0
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

def pubAIO(feed,message):
    try:
        aio.publish(feed,message)
    except:
        logger.warning('failure to publish {0}'.format(AIO_FEED_STATUS))

def configRead():
    global flagGarage, flagRun
    global tempBoilerReturnMin, tempBoilerReturnMinGarage, deadbandBoiler
    global setpointGarage, deadbandGarage, tempFreezeProtect
    global secGarageProtectColdOn, secGarageProtectColdOff, secGarageProtectHotOn, secGarageProtectHotOff
    global secPreheatGarage, secPurgeGaragePump, secPurgeGarageFan
    global secPreheatBedrooms, secPurgeBedroomsPump, secPurgeBedroomsFan
    global hrExercise, secUpdate, secPublishTempLoop, secRRDTempLoop
    global secPublishStatusLoop, secConfigCheckLoop, secReadTempsLoop
    global IFTTT_KEY, IFTTT_EVENT 
    global ID_PROBE, ID_BOILER_RETURN, ID_BOILER_SUPPLY
    global ID_GARAGE_SUPPLY, ID_GARAGE_RETURN, ID_GARAGE_AIR
    global ID_OUTSIDE_AIR   
    global AIO_KEY, AIO_USERNAME        
    global AIO_FEED_TEMP_BS, AIO_FEED_TEMP_BR    
    global AIO_FEED_TEMP_GA, AIO_FEED_TEMP_GS, AIO_FEED_TEMP_GR    
    global AIO_FEED_STATE, AIO_FEED_SP_G       
    global AIO_FEED_ENABLE_G, AIO_FEED_STATUS      
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
    secPublishTempLoop = float(cfg['secpublishtemploop'])
    secPublishStatusLoop = float(cfg['secpublishstatusloop'])
    secConfigCheckLoop = float(cfg['secconfigcheckloop'])
    IFTTT_KEY = cfg['ifttt_key'] #dMU6-1cYu6tDnxg91rl6F5'
    IFTTT_EVENT  = cfg['ifttt_event'] # 'boiler'
    ID_PROBE         = cfg['id_probe'] # '28.F542E1020000'
    ID_BOILER_RETURN = cfg['id_boiler_return'] # '28.13FBCE030000'
    ID_BOILER_SUPPLY = cfg['id_boiler_supply'] # ''
    ID_GARAGE_SUPPLY = cfg['id_garage_supply'] # ''
    ID_GARAGE_RETURN = cfg['id_garage_return'] # ''
    ID_GARAGE_AIR    = cfg['id_garage_air'] # '28.00E639040000' 
    ID_OUTSIDE_AIR   = cfg['id_outside_air']
    AIO_KEY              = cfg['aio_key'] # '462a14a808df4619840d228fcf49e7a8'
    AIO_USERNAME         = cfg['aio_username'] # 'jwmelvin'
    AIO_FEED_TEMP_BS     = cfg['aio_feed_temp_bs'] # 'temp-boilersupply'
    AIO_FEED_TEMP_BR     = cfg['aio_feed_temp_br'] # 'temp-boilerreturn'
    AIO_FEED_TEMP_GA     = cfg['aio_feed_temp_ga'] # 'temp-garageair'
    AIO_FEED_TEMP_GS     = cfg['aio_feed_temp_gs'] # 'temp-garagesupply'
    AIO_FEED_TEMP_GR     = cfg['aio_feed_temp_gr'] # 'temp-garagereturn'
    AIO_FEED_STATE       = cfg['aio_feed_state'] # 'state-boilercontroller'
    AIO_FEED_SP_G        = cfg['aio_feed_sp_g'] # 'setpoint-garage'
    AIO_FEED_ENABLE_G    = cfg['aio_feed_enable_g'] # 'enable-garage'
    AIO_FEED_STATUS      = cfg['aio_feed_status'] # 'status-report'
    if flagRun != cfgParser.getboolean('STATE', 'enable_overall'):
        flagRun = cfgParser.getboolean('STATE', 'enable_overall')
        logger.info('Config changed: enable_overall {0}'.format(flagRun))
        pubAIO(AIO_FEED_STATUS,'config file: Overall enable = '.format(flagRun))
        if flagRun:
            pubAIO(AIO_FEED_STATE,'ON')
        else:
            pubAIO(AIO_FEED_STATE,'OFF')
    if flagGarage != cfgParser.getboolean('STATE', 'enable_garage'):
        flagGarage = cfgParser.getboolean('STATE', 'enable_garage')
        logger.info('Config changed: enable_garage {0}'.format(flagGarage))
        pubAIO(AIO_FEED_STATUS,'config file: Garage enable = '.format(flagGarage))
        if flagGarage:
            pubAIO(AIO_FEED_ENABLE_G,'ON')
        else:
            pubAIO(AIO_FEED_ENABLE_G,'OFF')
    if setpointGarage != cfgParser.getfloat('STATE','setpointgarage'):
        setpointGarage = cfgParser.getfloat('STATE','setpointgarage')
        logger.info('Config changed: setpointGarage, now {0}'.format(setpointGarage))
        pubAIO(AIO_FEED_SP_G, setpointGarage)
        pubAIO(AIO_FEED_STATUS,'config file: Garage setpoint = '.format(setpointGarage))

def checkConfig():
    global secConfigFile
    if os.path.getmtime('/home/pi/boiler.config') != secConfigFile:
        secConfigFile = os.path.getmtime('/home/pi/boiler.config')
        configRead()
        logger.info('updated parameters from config file')
        pubAIO(AIO_FEED_STATUS,'updated parameters from config file')

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
                pubAIO(AIO_FEED_STATUS,'call Garage')
        elif tempGarageAir > setpointGarage + deadbandGarage/2:
            if callGarage:
                secStopCallGarage = time()
                logger.debug('uncall Garage')
                pubAIO(AIO_FEED_STATUS,'uncall Garage')
            callGarage = False
    else:
        if callGarage:
            secStopCallGarage = time()
            logger.debug('disabling Garage')
            pubAIO(AIO_FEED_STATUS,'disabling Garage')
        callGarage = False


def bathroomsCheck():
    global callBathrooms
    if inCallBathrooms.is_pressed:
        if not callBathrooms:
            logger.debug('call Bathrooms')
            pubAIO(AIO_FEED_STATUS,'call Bathrooms')
        callBathrooms = True
    else:
        if callBathrooms:
            logger.debug('uncall Bathrooms')
            pubAIO(AIO_FEED_STATUS,'uncall Bathrooms')
        callBathrooms = False

def bedroomsCheck():
    global callBedrooms, secStopCallBedrooms
    if inCallBedrooms.is_pressed:
        if not callBedrooms:
            logger.debug('call Bedrooms')
            pubAIO(AIO_FEED_STATUS,'call Bedrooms')
        callBedrooms = True
    else:
        if callBedrooms:
            secStopCallBedrooms = time()
            logger.debug('uncall Bedrooms')
            pubAIO(AIO_FEED_STATUS,'uncall Bedrooms')
        callBedrooms = False

def publish_status():
    try:
        aio.publish(AIO_FEED_STATUS,'spG: {0}, runG: {1}'.format(setpointGarage,flagGarage))
    except:
        logger.warning('failure to publish {0}'.format(AIO_FEED_STATUS))
    
def publish_temps():
    if len(ID_BOILER_SUPPLY)>0 and isinstance(tempBoilerSupply,float):
        try:
            aio.publish(AIO_FEED_TEMP_BS,tempBoilerSupply)
        except:
            logger.warning('failure to publish {0}'.format(AIO_FEED_TEMP_BS))
            pass
    if len(ID_BOILER_RETURN)>0 and isinstance(tempBoilerReturn,float):
        try:
            aio.publish(AIO_FEED_TEMP_BR,tempBoilerReturn)
        except:
            logger.warning('Warning: failure to publish {0}'.format(AIO_FEED_TEMP_BR))
            pass
    if len(ID_GARAGE_AIR)>0 and isinstance(tempGarageAir,float):
        try:
            aio.publish(AIO_FEED_TEMP_GA,tempGarageAir)
        except:
            logger.warning('Warning: failure to publish {0}'.format(AIO_FEED_TEMP_GA))
            pass
    if len(ID_GARAGE_SUPPLY)>0 and isinstance(tempGarageSupply,float):
        try:
            aio.publish(AIO_FEED_TEMP_GS,tempGarageSupply)
        except:
            logger.warning('Warning: failure to publish {0}'.format(AIO_FEED_TEMP_GS))
            pass
    if len(ID_GARAGE_RETURN)>0 and isinstance(tempGarageReturn,float):
        try:
            aio.publish(AIO_FEED_TEMP_GR,tempGarageReturn)
        except:
            logger.warning('Warning: failure to publish {0}'.format(AIO_FEED_TEMP_GR))
            pass
    
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
            rrdtool.update('--daemon','192.168.1.75','temp_GR.rrd','N:%s' %(tempOutsideAir))
        except:
            logger.warning('Warning: failure to update rrd tempGarageReturn')    
        

def read_temps():
    global tempBoilerSupply, tempBoilerReturn 
    global tempGarageAir, tempGarageSupply, tempGarageReturn
    global tempOutsideAir
    if len(ID_BOILER_SUPPLY)>0:
        tempBoilerSupply = readTemp(ID_BOILER_SUPPLY)
    if len(ID_BOILER_RETURN)>0:
        tempBoilerReturn = readTemp(ID_BOILER_RETURN)
    if len(ID_GARAGE_AIR)>0:
        tempGarageAir = readTemp(ID_GARAGE_AIR)
    if len(ID_GARAGE_SUPPLY)>0:
        tempGarageSupply = readTemp(ID_GARAGE_SUPPLY)
    if len(ID_GARAGE_RETURN)>0:
        tempGarageReturn = readTemp(ID_GARAGE_RETURN)
    if len(ID_OUTSIDE_AIR)>0:
        tempOutsideAir = readTemp(ID_OUTSIDE_AIR)

def aio_connected(client):
    # called when the client is connected to Adafruit IO.
    # This is a good place to subscribe to feed changes.  The client parameter
    # passed to this function is the Adafruit IO MQTT client so you can make
    # calls against it easily.
    logger.info('Connected to Adafruit IO!  Listening...')
    # Subscribe to changes on desired feeds
    try:
        client.subscribe(AIO_FEED_STATE)
    except:
        logger.error('subscribing to {0}'.format(AIO_FEED_STATE))
    try:
        client.subscribe(AIO_FEED_SP_G)
    except:
        logger.error('subscribing to {0}'.format(AIO_FEED_SP_G))
    try:
        client.subscribe(AIO_FEED_ENABLE_G)
    except:
        logger.error('subscribing to {0}'.format(AIO_FEED_ENABLE_G))    

def aio_disconnected(client):
    # Disconnected function will be called when the client disconnects.
    logger.error('Disconnected from Adafruit IO!')
    #sys.exit(1)

def aio_message(client, feed_id, payload):
    global flagRun, setpointGarage, flagGarage
    # Message function will be called when a subscribed feed has a new value.
    # The feed_id parameter identifies the feed, and the payload parameter has
    # the new value.
    logger.info('Feed {0} received new value: {1}'.format(feed_id, payload))
    if feed_id == 'state-boildercontroller':
        if payload == 'ON':
            flagRun = True
            pubAIO(AIO_FEED_STATUS,'controller ON')
        elif payload == 'OFF':
            flagRun = False
            pubAIO(AIO_FEED_STATUS,'controller OFF')
    if feed_id == 'setpoint-garage':
        setpointGarage = float(payload)
        pubAIO(AIO_FEED_STATUS,'garage setpoint now {0}'.format(setpointGarage))
    if feed_id == 'enable-garage':
        if payload == 'ON':
            flagGarage = True
            pubAIO(AIO_FEED_STATUS,'garage heat ON')
        elif payload == 'OFF':
            flagGarage = False
            pubAIO(AIO_FEED_STATUS,'garage heat OFF')

def manualOps():
        global flagManual
        if not flagManual:
            try:
                pyfttt.send_event(IFTTT_KEY,IFTTT_EVENT,'Entered manual operation')
            except:
                logger.error('error sending IFTTT message')
            flagManual = True
            pubAIO(AIO_FEED_STATUS,'entered Manual mode')
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
#         outGaragePump.off()

if __name__ == '__main__':
    ow = protocol.proxy()
    
    cfgParser=configparser.ConfigParser()
    configRead()
    
    aio = MQTTClient(AIO_USERNAME, AIO_KEY)
    #aioREST = Client(AIO_KEY)
    aio.on_connect    = aio_connected
    aio.on_disconnect = aio_disconnected
    aio.on_message    = aio_message
    aio.connect()
    aio.loop_background()
    
    while True:
        secStartLoop = time()
        if time() - secReadTempsLast  > secReadTempsLoop:
            read_temps()
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
                pubAIO(AIO_FEED_STATUS,'entered Automatic mode')
                
            if callBedrooms or callBathrooms or callGarage:
                outBoiler.on()
            else:
                outBoiler.off()
            
            if tempBoilerReturn < tempBoilerReturnMin - deadbandBoiler/2:
                outBedroomsPump.off()
                outBedroomsFan.off()
                outBathroomsPump.off()
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
                elif isinstance(tempGarageAir, float): 
                    if tempGarageAir < tempFreezeProtect:
                        if not flagGarageProtect:
                            flagGarageProtect = True
                            pubAIO(AIO_FEED_STATUS,'Garage freeze protect started')
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
                                secStopGaragePump = time()
                        else:
                            if time() - secStopGaragePump > secOff:
                                outGaragePump.on()
                                secStartGaragePump = time()
                    else:
                        if flagGarageProtect:
                            flagGarageProtect = False
                            pubAIO(AIO_FEED_STATUS,'Garage freeze protect ended')
                            logger.info('Garage freeze protect ended')
                        if time() - secStopCallGarage > secPurgeGaragePump:
                            outGaragePump.off()
                        if time() - secStopCallGarage > secPurgeGarageFan:
                            outGarageFan.off()
                else:
                    logger.error('unknown Garage temperature')
                    pubAIO(AIO_FEED_STATUS,'unknown Garage temperature')
                    try:
                        pyfttt.send_event(IFTTT_KEY,IFTTT_EVENT,'unknown Garage temperature')
                    except:
                        logger.error('error sending IFTTT message')
                        
        elif flagRun:
            manualOps()
        if time() - secPublishTempLast  > secPublishTempLoop:
            publish_temps()
            secPublishTempLast = time()
        if secPublishStatusLoop > 0 and time() - secPublishStatusLast  > secPublishStatusLoop:
            publish_status()
            secPublishStatusLast = time()
        if time () - secRRDTempLast > secRRDTempLoop:
            rrd_temps() 
            secRRDTempLast = time()
        if time() - secCheckConfigLast > secConfigCheckLoop: 
            checkConfig()
            secCheckConfigLast = time()
        while time() - secStartLoop < secUpdate:
            sleep(0.1)
        