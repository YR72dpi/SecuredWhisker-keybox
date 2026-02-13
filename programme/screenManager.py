import os
fontdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'font')
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pics')
from PIL import Image, ImageDraw, ImageFont
import logging
import time

def printText(epd, text, x, y):
    logging.info("Affiche du texte sans clignotement pour les mises à jour")
    """Affiche du texte sans clignotement pour les mises à jour"""

    clearNoFlash(epd)
    time.sleep(1)

    image = Image.new('1', (epd.height, epd.width), 255)  # 255: blanc, 0: noir
    draw = ImageDraw.Draw(image)
    font15 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 15)
    draw.text((x, y), text, font=font15, fill=0)  # fill=0 pour noir
    
    buffer = epd.getbuffer(image)
    # Envoyer directement sans reset
    epd.send_command(0x24)  # WRITE_RAM
    epd.send_data2(buffer)
    epd.TurnOnDisplayPart()  # Mise à jour rapide

def clearNoFlash(epd):
    logging.info("Efface l'écran sans aucun clignotement")
    """Efface l'écran sans aucun clignotement"""
    image = Image.new('1', (epd.height, epd.width), 255)  # 255: blanc
    buffer = epd.getbuffer(image)
    
    # Envoyer directement les données sans reset
    epd.send_command(0x24)  # WRITE_RAM
    epd.send_data2(buffer)
    epd.TurnOnDisplayPart()  # Mise à jour rapide sans attente

def clearAndSleep(epd):
    """Applique une image blanche neutre puis éteint l'écran"""
    image = Image.open(os.path.join(picdir, "logo.bmp"))  # 255: blanc
    buffer = epd.getbuffer(image)
    # Effacer sans clignotement avant de dormir
    epd.send_command(0x24)  # WRITE_RAM
    epd.send_data2(buffer)
    epd.TurnOnDisplayPart()
    epd.sleep()

def showImage (epd, fileName):
    image = Image.open(os.path.join(picdir, fileName))
    epd.displayPartBaseImage(epd.getbuffer(image))
    DrawImage = ImageDraw.Draw(image)
    epd.init(epd.PART_UPDATE)