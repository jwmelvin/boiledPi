
#from time import sleep, time
import pyfttt
#import sys
import configparser
import logging, logging.handlers
#import os

LOG_FILE        = '/home/pi/boiler.log'
logger = logging.getLogger('logger')
logger.setLevel(logging.DEBUG)
logformatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
loghandler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=524288, backupCount=5)
loghandler.setFormatter(logformatter)
logger.addHandler(loghandler)

def configRead():
    global IFTTT_KEY, IFTTT_EVENT 
    cfgParser.read('/home/pi/boiler.config')
    IFTTT_KEY = cfgParser.get('DEFAULT','ifttt_key') #dMU6-1cYu6tDnxg91rl6F5'
    IFTTT_EVENT  = cfgParser.get('DEFAULT','ifttt_event') # 'boiler'

if __name__ == '__main__':
    cfgParser=configparser.ConfigParser()
    configRead()
    
    try:
        pyfttt.send_event(IFTTT_KEY,IFTTT_EVENT,'Boiler service exited')
    except:
        logger.error('error sending IFTTT failure message')
