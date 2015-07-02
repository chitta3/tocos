#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# TOCOS TWE-lite DIP sensor
#

import sqlite3
import serial
import time
import datetime
import syslog
import os
from daemon import daemon
from daemon.pidlockfile import PIDLockFile

dc = DaemonContext(
    pidfile=PIDLockFile('/var/run/tocomoni.pid'),
    stderr=open('/var/log/tocomoni_err_console.txt’, 'w+')
)

DBNAME = '/var/log/tocos/data.db'

SERIALPORT = '/dev/ttyUSB0'
BAUDRATE = 115200

ADDR = 5
BATT = 6
MAIN = 7
ADC1 = 9
ADC2 = 10
PKID = 11
TIME = 12

class Port:
    def __init__(self, port, rate):
        self.port = port
        self.rate = rate
        return
    def __del__(self):
        self.ser.close()

    def open(self):
        try:
            self.ser = serial.Serial(self.port, self.rate)

            self.ser.bytesize = serial.EIGHTBITS # number of bits per bytes
            self.ser.parity = serial.PARITY_NONE # set parity check: no parity
            self.ser.stopbits = serial.STOPBITS_ONE # number of stop bits

            # self.ser.timeout = None          # block read
            # self.ser.timeout = 0             # non-block read
            self.ser.timeout = 2              # timeout block read
            self.ser.xonxoff = False     # disable software flow control
            self.ser.rtscts = False     # disable hardware (RTS/CTS) flow control
            self.ser.dsrdtr = False       # disable hardware (DSR/DTR) flow control
            self.ser.writeTimeout = 0     # timeout for write

            self.ser.open()
            self.ser.flushInput()    # flush input buffer, discarding all its contents
            self.ser.flushOutput()   # flush output buffer, aborting current output
            return self.ser

        except Exception, e:
            print("error open serial port: " + str(e))
            return None

    def readline(self):
        return self.ser.readline()

class Sensor:
    ADDR = 5
    BATT = 6
    MAIN = 7
    ADC1 = 9
    ADC2 = 10
    PKID = 11
    TIME = 12

    def __init__(self, id, name, pos, func):
        self.address = id
        self.tagname = name
        self.position = pos
        self.function = func

    def read_tagname(self):
        return self.tagname

    def read_value(self, line):
        return self.function(line[self.position])

    def read_battery(self, line):
        return line[BATT]

    def read_timestump(self, line):
        return line[TIME]

    def read_address(self):
        return self.address

class Rdb:
    def __init__(self, dbname):
        self.dbname = dbname
        self.connect = None
        return

    def __del__(self):
        self.connect.close()

    def open(self):
        try:
            self.connect = sqlite3.connect(dbname, isolation_level=None)
            return self.connect
        except Exception, e:
            print "sqlite can't open database...: " + str(e)
            return None

    def write(self, tagname, value, batt, stump, addr):
        try:
            c = self.connect.execute("""SELECT * FROM data WHERE id = '{0}';""".format(tagname))
            r = c.fetchall()
            if len(r) > 0:
                c = self.connect.execute("""UPDATE data
                    SET value='{0}', batt='{1}', timestump='{2}', address='{3}'
                    WHERE id = '{4}';""".format(value, batt, stump, addr, tagname))
            else:
                c = self.connect.execute("""INSERT INTO data(id, value, batt, timestump, address)
                    VALUES('{0}', '{1}', '{2}', '{3}', '{4}');""".format(tagname, value, batt, stump, addr))
            return
        except Exception, e:
            print "sqlite error...: " + str(e)
            return None

    def close(self):
        self.connect.close()

def conv_temp1(val):
    return (int(val) / 100.0)
def conv_temp2(val):
    return ((int(val) - 600) / 10.0) + 10.0
def conv_temp3(val):
    return ((int(val) - 600) / 10.0) + 2.0
def conv_pass(val):
    return int(val) * 1.0

def run():
    try:
        syslog.openlog("tocos", syslog.LOG_PID, syslog.LOG_LOCAL0)
        ser = Port(SERIALPORT, BAUDRATE)
        ser._open()
        con = Rdb(DBNAME)
        con.open()

# initialize sensor
        sensor = []
        sensor += Sensor('100366b', OuterTemp, MAIN, conv_temp1)
        sensor += Sensor('100366b', OMsystmp, ADC2, conv_temp2)
        sensor += Sensor('100f095', OMairTemp, MAIN, conv_temp1)
        sensor += Sensor('100f095', Outer2tmp, ADC1, conv_temp2)
        sensor += Sensor('10039fc', AtomPress, MAIN, conv_pass)
        sensor += Sensor('10039fc', Watertmp, ADC1, conv_temp3)

        while True:
            response = ser.readline()
            line = response.split(";")
            if len(line) > 3:
                d = datetime.datetime.now()
                line.pop()
                line = line + [d.strftime("%Y%m%d%H%M%S")]	# TimeStump
                syslog.syslog("{0[TIME]};{0[PKID]};{0[ADDR]};{0[MAIN]};{0[ADC1]};{0[ADC2]};{0[BATT]}".format(line))
                for s in sensor:
                    if s.read_address() == line[ADDR]:
                        write_db(s.read_tagname(), s.read_value(line), s.read_battery(line), s.read_timestump(line), s.read_address())
            time.sleep(5)

    except Exception, e:
        print "error communicating...: " + str(e)
        exit()

    except KeyboardInterrupt, e:
        print "\nInterrupt: " + str(e)

    finally:
        syslog.closelog()

if __name__ == "__main__":
    with dc:
        run()
