import os
fontdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'font')
from PIL import Image, ImageDraw, ImageFont


def printText(epd, text, x, y):
    image = Image.new('1', (epd.height, epd.width), 255)  # 255: blanc, 0: noir
    draw = ImageDraw.Draw(image)
    font15 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 15)
    # font24 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 24)    
    draw.text((x, y), text, font=font15, fill=0)  # fill=0 pour noir
    epd.display(epd.getbuffer(image))

def clearAndSleep(epd):
    """Applique une image blanche neutre puis éteint l'écran"""
    image = Image.new('1', (epd.height, epd.width), 255)  # 255: blanc
    epd.display(epd.getbuffer(image))    
    epd.sleep()