# -*- coding: utf-8 -*-

import sqlite3
from SmsCat import SmsCat
from datetime import datetime
import time
from threading import Thread

class SmsDaemon(Thread):
  def __init__(self, port, sn, db = 'db.sqlite'):
    Thread.__init__(self, name = sn)
    self.db= db
    self.cat = SmsCat(port)
    self.sn = sn

  def initDB(self):
    conn = sqlite3.connect(self.db)
    cursor = conn.cursor()

    cursor.executescript("""
      DROP TABLE IF EXISTS SMS;
      CREATE TABLE IF NOT EXISTS SMS(
        Id INTEGER PRIMARY KEY,
        Send_On DATETIME NOT NULL, 
        Source TEXT NOT NULL,
        Destination TEXT NOT NULL,
        Content TEXT NOT NULL,
        Label TEXT,
        Pos Integer NOT NULL,
        Len Integer
      );
    """)
    conn.commit()
    cursor.close()
    conn.close()

  def run(self):
    while True:
      l =  self.cat.read_sms_list()
      if l:
        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        cursor.executemany("""
          INSERT INTO SMS (
                      Send_On, 
                      Source, 
                      Destination,
                      Content,
                      label,
                      Pos,
                      Len)
          VALUES (:send_on, :source, %s, :content, :label, :pos, :len)
        """ % self.sn, l)
        conn.commit()
        cursor.close()
        conn.commit()
      else:
        time.sleep(10)

if __name__ == '__main__':
  sd = SmsDaemon('/dev/ttyS0', '18805900896')
  sd.initDB()
  sd.start()
