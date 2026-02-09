#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic/2in13')
fontdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'font')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)
    
from TP_lib import gt1151
from TP_lib import epd2in13_V4
import time
import logging
from PIL import Image, ImageDraw, ImageFont
import traceback
import threading

logging.basicConfig(level=logging.DEBUG)
flag_t = 1

def pthread_irq():
    print("pthread running")
    while flag_t == 1:
        if(gt.digital_read(gt.INT) == 0):
            GT_Dev.Touch = 1
        else:
            GT_Dev.Touch = 0
    print("thread:exit")

try:
    logging.info("epd2in13_V4 Touch Demo")
    
    epd = epd2in13_V4.EPD()
    gt = gt1151.GT1151()
    GT_Dev = gt1151.GT_Development()
    GT_Old = gt1151.GT_Development()
    
    logging.info("init and Clear")
    
    epd.init(epd.FULL_UPDATE)
    gt.GT_Init()
    epd.Clear(0x00)
    
    t = threading.Thread(target=pthread_irq)
    t.setDaemon(True)
    t.start()

    time.sleep(1)
    
    # Créer une image
    image = Image.new('1', (epd.height, epd.width), 255)  # 255: blanc, 0: noir
    draw = ImageDraw.Draw(image)
    
    # Charger les polices
    font15 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 15)
    font24 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 24)
    
    # Dessiner le texte
    draw.text((8, 12), 'Secured Whisker Key Box', font=font15, fill=0)  # fill=0 pour noir
    
    # Afficher l'image sur l'écran
    epd.display(epd.getbuffer(image))
    
    # Mettre en veille
    epd.sleep()

    # Garder le programme actif
    while True:
        time.sleep(1)
    
except IOError as e:
    logging.info(e)
    
except KeyboardInterrupt:    
    logging.info("ctrl + c:")
    epd.Clear(0x00)
    flag_t = 0
    epd.sleep()
    time.sleep(2)
    t.join()
    epd.Dev_exit()
    exit()