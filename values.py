#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Print TOCOS TWE-lite DIP senser data for munin
#

import sqlite3
import string
import os

DBNAME = "/var/log/tocos/data.db"

def read_db(con):
    c = con.execute("""SELECT * FROM data;""")
    r = c.fetchall()
    return r

def main():
    try:
        con = sqlite3.connect(DBNAME, isolation_level=None)
        value = read_db(con)
        for i in value:
            print('{0}.value {1}'.format(i[0], i[1]))

    finally:
        con.close()

if __name__ == "__main__":
    main()
