#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# TOCOS TWE-lite DIP monitor
#
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


import sqlite3
import string
import serial
import time
import datetime
#import locale
import syslog
#import signal
#import sys
import os

DBNAME = "/var/log/tocos/data1.db"

SERIALPORT = "/dev/ttyUSB0"
BAUDRATE = 115200

global con
global ser

def init_serial():
    try:
#       ser = serial.Serial(port, rate)
        ser.bytesize = serial.EIGHTBITS #number of bits per bytes
        ser.parity = serial.PARITY_NONE #set parity check: no parity
        ser.stopbits = serial.STOPBITS_ONE #number of stop bits

        #ser.timeout = None          #block read
        #ser.timeout = 0             #non-block read
        ser.timeout = 2              #timeout block read
        ser.xonxoff = False     #disable software flow control
        ser.rtscts = False     #disable hardware (RTS/CTS) flow control
        ser.dsrdtr = False       #disable hardware (DSR/DTR) flow control
        ser.writeTimeout = 0     #timeout for write

        ser.open()
        ser.flushInput() #flush input buffer, discarding all its contents
        ser.flushOutput()#flush output buffer, aborting current output
        return

    except Exception, e:
        print("error open serial port: " + str(e))
        exit()

#def sigint_handler(signal, frame):
    #syslog.closelog()
    #ser.close()
    #con.close()
    #print("\nInterrupted")
    #sys.exit(0)

def conv_temp1(val):
    return (int(val) / 100.0)

def conv_temp2(val):
    return ((int(val) - 600) / 10.0) + 10.0

def conv_temp3(val):
    return ((int(val) - 600) / 10.0) + 2.0

def conv_pass(val):
    return int(val) * 1.0

Nodes = {
    '100366b': ['OuterTemp', conv_temp1, 'NONE', conv_pass, 'OMsystmp', conv_temp2],     # node1
    '100f095': ['OMairTemp', conv_temp1, 'Outer2tmp', conv_temp2, 'NONE', conv_pass],    # node2
    '10039fc': ['AtomPress', conv_pass, 'Watertmp', conv_temp3, 'NONE', conv_pass]       # node3
}

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

def write_senser(line, con):
    key = line[ADDR]
    print key
    print line[MAIN]
    print Nodes[key]
    print Nodes[key][func1]
    line[MAIN] = "{0:.2f}".format(Nodes[key][func1](line[MAIN]))
    line[ADC1] = "{0:.2f}".format(Nodes[key][func2](line[ADC1]))
    line[ADC2] = "{0:.2f}".format(Nodes[key][func3](line[ADC2]))

    list = [(TAG1, MAIN), (TAG2, ADC1), (TAG3, ADC2)]
    for tag, val in list:
        if Nodes[key][tag] != 'NONE':
            write_db(con, Nodes[key][tag], line[val], line[BATT], line[TIME], line[ADDR])

def temp_senser(line, con):
    line[7] = "{0:.2f}".format(int(line[7]) / 100.0 + 2)	#Temperrature
    line[9] = "{0:.2f}".format((int(line[9]) -600) / 10.0 + 10)	#ADC1 (mV)
    line[10] = "{0:.2f}".format((int(line[10]) -600) / 10.0 + 10)	#ADC2 (mV)

    write_db(con, 'OuterTemp', line[7], line[6], line[12], line[5])
    write_db(con, 'OMsysTemp', line[10], line[6], line[12], line[5])

    return line

def adt7410_temp_senser(line, con):
    line[7] = "{0:.2f}".format(int(line[7]) / 100.0 + 2)	#Temperrature
    line[9] = "{0:.2f}".format((int(line[9]) -600) / 10.0 + 10)	#ADC1 (mV)
    line[10] = "{0:.2f}".format((int(line[10]) -600) / 10.0 + 10)	#ADC2 (mV)

    write_db(con, 'OMairTemp', line[7], line[6], line[12], line[5])
    write_db(con, 'Outer2Temp', line[10], line[6], line[12], line[5])

    return line
def atom_senser(line, con):
    # line[7]  Atmospheric Pressure (hPa)
    line[9] = "{0:.2f}".format((int(line[9]) -600) / 10.0 +2)	#ADC1 (mV)
    line[10] = "{0:.2f}".format((int(line[10]) -600) / 10.0 +2)	#ADC2 (mV)

    write_db(con, 'AtomPress', line[7], line[6], line[12], line[5])
    write_db(con, 'WaterTemp', line[9], line[6], line[12], line[5])

    return line

def write_db(con, type, value, batt, stump, addr):
    c = con.execute("""SELECT * FROM data WHERE id = '{0}';""".format(type))

    r = c.fetchall()
    if len(r) > 0:
        print("""UPDATE data
            SET value='{0}', batt='{1}', timestump='{2}', address='{3}'
            WHERE id = '{4}';""".format(value, batt, stump, addr, type))
        c = con.execute("""UPDATE data
            SET value='{0}', batt='{1}', timestump='{2}', address='{3}'
            WHERE id = '{4}';""".format(value, batt, stump, addr, type))
    else:
        c = con.execute("""INSERT INTO data(id, value, batt, timestump, address)
            VALUES('{0}', '{1}', '{2}', '{3}', '{4}');""".format(type, value, batt, stump, addr))

    return

def main():
    try:
        syslog.openlog("tocos", syslog.LOG_PID, syslog.LOG_LOCAL0)
        init_serial()
        if not ser.isOpen():
            print "cannot open serial port "
            return

        con = sqlite3.connect(DBNAME, isolation_level=None)

        while True:
            response = ser.readline()
            line = response.split(";")
            if len(line) > 3:
                d = datetime.datetime.now()
                line.pop()
                line = line + [d.strftime("%Y%m%d%H%M%S")]	# TimeStump
                syslog.syslog("{0[TIME]};{0[PKID]};{0[ADDR]};{0[MAIN]};{0[ADC1]};{0[ADC2]};{0[BATT]}".format(line))
                print line
                write_senser(line, con)
                print line
#               if line[11] == 'L':	                 # アナログ温度センサ
#                   line = temp_senser(line, con)
#               elif line[11] == 'D':               # ADT7410 温度センサ
#                   line = adt7410_temp_senser(line, con)
#               elif line[11] == 'M':               # 気圧センサ
#                   line = atom_senser(line, con)
#               print line
#               print("{0[12]};{0[11]};{0[5]};{0[7]};{0[9]};{0[10]};{0[6]}".format(line))
#               syslog.syslog("{0[12]};{0[11]};{0[5]};{0[7]};{0[9]};{0[10]};{0[6]}".format(line))
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

def savepid():
    f = open('/var/run/tocomoni.pid', 'w')
    f.write(str(os.getpid())+'\n')
    f.close()

if __name__ == "__main__":
#    savepid()
    ser = serial.Serial(SERIALPORT, BAUDRATE)
    main()
