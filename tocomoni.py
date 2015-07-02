#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# TOCOS TWE-lite DIP monitor
#


import sqlite3
# import string
import serial
import time
import datetime
# import locale
import syslog
# import signal
# import sys
import os
from daemon import daemon
from daemon.pidlockfile import PIDLockFile

dc = DaemonContext(
    pidfile=PIDLockFile('/var/run/tocomoni.pid'),
    stderr=open('/var/log/tocomoni_err_console.txt’, 'w+')
)

def conv_temp1(val):
    return (int(val) / 100.0)

def conv_temp2(val):
    return ((int(val) - 600) / 10.0) + 10.0

def conv_temp3(val):
    return ((int(val) - 600) / 10.0) + 2.0

def conv_pass(val):
    return int(val) * 1.0


ADDR = 5
BATT = 6
MAIN = 7
ADC1 = 9
ADC2 = 10
PKID = 11
TIME = 12

TAG1 = 0
func1 = 1
TAG2 = 2
func2 = 3
TAG3 = 4
func3 = 5

Nodes = {
    '100366b': ['OuterTemp', conv_temp1, 'NONE', conv_pass, 'OMsystmp', conv_temp2],     # node1
    '100f095': ['OMairTemp', conv_temp1, 'Outer2tmp', conv_temp2, 'NONE', conv_pass],    # node2
    '10039fc': ['AtomPress', conv_pass, 'Watertmp', conv_temp3, 'NONE', conv_pass]       # node3
}

DBNAME = "/var/log/tocos/data.db"

SERIALPORT = "/dev/ttyUSB0"
BAUDRATE = 115200

global ser # serial i/o handle
global con # sqlite db connection handle

def init_serial():
    try:
        ser = serial.Serial(SERIALPORT, BAUDRATE)

        ser.bytesize = serial.EIGHTBITS # number of bits per bytes
        ser.parity = serial.PARITY_NONE # set parity check: no parity
        ser.stopbits = serial.STOPBITS_ONE # number of stop bits

        # ser.timeout = None          # block read
        # ser.timeout = 0             # non-block read
        ser.timeout = 2              # timeout block read
        ser.xonxoff = False     # disable software flow control
        ser.rtscts = False     # disable hardware (RTS/CTS) flow control
        ser.dsrdtr = False       # disable hardware (DSR/DTR) flow control
        ser.writeTimeout = 0     # timeout for write

        ser.open()
        ser.flushInput()    # flush input buffer, discarding all its contents
        ser.flushOutput()   # flush output buffer, aborting current output
        return

    except Exception, e:
        print("error open serial port: " + str(e))
        exit()

def write_senser(line):
    key = line[ADDR]
    print key
    print line[MAIN]
    print Nodes[key]
    print Nodes[key][func1]
    line[MAIN] = "{0:.2f}".format(Nodes[key][func1](line[MAIN]))
    line[ADC1] = "{0:.2f}".format(Nodes[key][func2](line[ADC1]))
    line[ADC2] = "{0:.2f}".format(Nodes[key][func3](line[ADC2]))

    vlist = [(TAG1, MAIN), (TAG2, ADC1), (TAG3, ADC2)]
    for tag, val in vlist:
        if Nodes[key][tag] != 'NONE':
            write_db(Nodes[key][tag], line[val], line[BATT], line[TIME], line[ADDR])

def write_db(tagname, value, batt, stump, addr):
    con = sqlite3.connect(DBNAME, isolation_level=None)

    c = con.execute("""SELECT * FROM data WHERE id = '{0}';""".format(tagname))

    r = c.fetchall()
    if len(r) > 0:
        c = con.execute("""UPDATE data
            SET value='{0}', batt='{1}', timestump='{2}', address='{3}'
            WHERE id = '{4}';""".format(value, batt, stump, addr, tagname))
    else:
        c = con.execute("""INSERT INTO data(id, value, batt, timestump, address)
            VALUES('{0}', '{1}', '{2}', '{3}', '{4}');""".format(tagname, value, batt, stump, addr))
    con.close()
    return

def main():
    try:
        syslog.openlog("tocos", syslog.LOG_PID, syslog.LOG_LOCAL0)
        init_serial()
        if not ser.isOpen():
            print "cannot open serial port "
            return

        while True:
            response = ser.readline()
            line = response.split(";")
            if len(line) > 3:
                d = datetime.datetime.now()
                line.pop()
                line = line + [d.strftime("%Y%m%d%H%M%S")]	# TimeStump
                syslog.syslog("{0[TIME]};{0[PKID]};{0[ADDR]};{0[MAIN]};{0[ADC1]};{0[ADC2]};{0[BATT]}".format(line))
                print line
                write_senser(line)
                print line
            time.sleep(5)

    except Exception, e:
        print "error communicating...: " + str(e)
        exit()

    except KeyboardInterrupt, e:
        print "\nInterrupt: " + str(e)

    finally:
        ser.close()
        syslog.closelog()
        con.close()

#   def savepid():
#       f = open('/var/run/tocomoni.pid', 'w')
#       f.write(str(os.getpid())+'\n')
#       f.close()

if __name__ == "__main__":
#
#    savepid()
#   ser = serial.Serial(SERIALPORT, BAUDRATE)
    with dc:
        main()

# ;1001;00000000;159;003;1007bbd;2970;2680;6696;1116;0858;L;
# ;*1  ;*2      ;*3 ;*4 ;*5     ;*6  ;*7  ;*8  ;*9  ;*10 ;*11;
# *1: 親機起動後のタイムスタンプ[s]
# *2: 未使用
# *3: LQI
# *4: 続き番号
# *5: 子機のID(MACアドレスの下7桁)
# *6: 子機の電源電圧
# *7: 温度(℃)×100
# *8: 未使用
# *9: ADC1(mV)
# *10: ADC2(mV)
# *11* パケット識別子
# パケット識別子(*11)がL　LM61BIZ 温度センサ（アナログ)
#
# ;1001;00000000;144;005;1007bbd;3330;1051;0000;1526;0214;M;
# ;*1  ;*2      ;*3 ;*4 ;*5     ;*6  ;*7  ;*8  ;*9  ;*10 ;*11;
# *1: 親機起動後のタイムスタンプ[s]
# *2: 未使用
# *3: LQI
# *4: 続き番号
# *5: 子機のID(MACアドレスの下7桁)
# *6: 子機の電源電圧
# *7: 気圧(hPa)
# *8: 未使用
# *9: ADC1(mV)
# *10: ADC2(mV)
# *11* パケット識別子
# パケット識別子(*11)がM　MPL115A2 気圧センサ
#
# ;1001;00000000;144;005;1007bbd;3330;2710;0000;1526;0214;D;
# ;*1  ;*2      ;*3 ;*4 ;*5     ;*6  ;*7  ;*8  ;*9  ;*10 ;*11;
# *1: 親機起動後のタイムスタンプ[s]
# *2: 未使用
# *3: LQI
# *4: 続き番号
# *5: 子機のID(MACアドレスの下7桁)
# *6: 子機の電源電圧
# *7: 温度(℃)×100
# *8: 未使用
# *9: ADC1(mV)
# *10: ADC2(mV)
# *11* パケット識別子
# パケット識別子(*11)がD　ADT7410 温度センサ（I2C)
