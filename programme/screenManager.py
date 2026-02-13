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


def printLines(epd, lines, x=5, y=5, fontSize=15, lineSpacing=3, clearBefore=True, sleepAfterClear=1):
    """Affiche plusieurs lignes de texte sur un seul écran.

    Args:
        epd: Instance du driver e-paper.
        lines: Tableau (list/tuple) de lignes (str) à afficher.
        x, y: Position du coin haut-gauche du bloc texte.
        fontSize: Taille de la police.
        lineSpacing: Espacement (en pixels) entre les lignes.
        clearBefore: Si True, efface l'écran sans clignotement avant d'écrire.
        sleepAfterClear: Pause (secondes) après effacement, pour stabiliser l'affichage.
    """
    logging.info("Affiche plusieurs lignes de texte (mise à jour partielle)")


    if lines is None:
        lines = []

    if clearBefore:
        clearNoFlash(epd)
        if sleepAfterClear > 0:
            time.sleep(sleepAfterClear)

    image = Image.new('1', (epd.height, epd.width), 255)  # 255: blanc, 0: noir
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), int(fontSize))

    try:
        bbox = font.getbbox("Ay")
        logging.info(bbox)
        lineHeight = (bbox[3] - bbox[1])
    except Exception:
        lineHeight = font.getsize("Ay")[1]

    cursorY = int(y)
    for line in lines:
        if line is None:
            line = ""
        line = str(line)
        if cursorY >= epd.width:
            break
        draw.text((int(x), cursorY), line, font=font, fill=0)
        cursorY += lineHeight + int(lineSpacing)

    buffer = epd.getbuffer(image)
    epd.send_command(0x24)  # WRITE_RAM
    epd.send_data2(buffer)
    epd.TurnOnDisplayPart()

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