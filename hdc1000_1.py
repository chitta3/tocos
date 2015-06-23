#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Read temperature and humidity data via HDC1000 senser for munin
#
__author__ = 'yo'
import wiringpi2
import os
import struct
from time import sleep

wiringpi2.wiringPiSetup()
i2c = wiringpi2.I2C()
dev = i2c.setup(0x40)
i2c.writeReg16(dev,0x02,0x10)   # Temp + Hidi 32-bit transfer mode, LSB-MSB inverted, why?
i2c.writeReg8(dev,0x00,0x00)    # start conversion.
sleep((6350.0 + 6500.0 +  500.0)/1000000.0) # wait for conversion.
# LSB-MSB inverted, again...
temp = ((struct.unpack('4B', os.read(dev,4)))[0] << 8 | (struct.unpack('4B', os.read(dev,4)))[1])
hudi = ((struct.unpack('4B', os.read(dev,4)))[2] << 8 | (struct.unpack('4B', os.read(dev,4)))[3])
os.close(dev) #Don't leave the door open.
print "Humidity %.2f" % (( hudi / 65535.0 ) * 100)
print "Temperature %.2f" % (( temp  / 65535.0) * 165 - 40 )