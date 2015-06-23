#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Print TOCOS TWE-lite DIP senser battery data for munin
#

import sqlite3
import sys

DBNAME = "/var/log/tocos/data.db"

def read_db(con):
    c = con.execute("""SELECT DISTINCT address, batt FROM data
                          ORDER BY address ASC;""")
    r = c.fetchall()
    return r

def main(args):
    try:
        con = sqlite3.connect(DBNAME, isolation_level=None)
        value = read_db(con)
        for i in value:
            print('{0}.value {1}'.format(args[value.index(i) + 1], i[1]))

    finally:
        con.close()

if __name__ == "__main__":
    main(sys.argv)
