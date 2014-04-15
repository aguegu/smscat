# -*- coding: utf-8 -*-

import sqlite3
from SmsCat import SmsCat
from datetime import datetime
import time
from threading import Thread
import json
import requests

url = 'http://localhost:5000/api/inbox'
headers = {'content-type': 'application/json'}

class SmsDaemon(Thread):
  def __init__(self, port, sn, run_once = False, delete = True, db = 'db.sqlite'):
    Thread.__init__(self, name = sn)
    self.db= db
    self.cat = SmsCat(port)
    self.sn = sn
    self.run_once = run_once
    self.delete = delete

  def initDB(self):
    conn = sqlite3.connect(self.db)
    cursor = conn.cursor()

    cursor.executescript("""
      DROP TABLE IF EXISTS INBOX;
      CREATE TABLE IF NOT EXISTS INBOX(
        Id INTEGER PRIMARY KEY,
        Source TEXT NOT NULL,
        Destination TEXT NOT NULL,
        Content TEXT NOT NULL,
        Mark TEXT,
        SegmentPos Integer NOT NULL,
        SegmentCount Integer NOT NULL,
        SendOn Datetime NOT NULL,
        ReceiveOn Datetime NOT NULL
      );
    """)
    conn.commit()
    cursor.close()
    conn.close()

  def run(self):
    while True:
      ll =  self.cat.read_sms_list()
      if ll:
        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        cursor.executemany("""
          INSERT INTO INBOX (
                      Source,
                      Destination,
                      Content,
                      Mark,
                      SegmentPos,
                      SegmentCount,
                      SendOn,
                      ReceiveOn)
          VALUES (:source, %s, :content, :mark, :segment_pos, :segment_count, :send_on, :receive_on)
        """ % self.sn, ll)
        conn.commit()
        cursor.close()
        conn.commit()

        for l in ll:
          l['send_on'] = l['send_on'].isoformat()
          l['receive_on'] = l['receive_on'].strftime("%Y-%m-%dT%H:%M:%S")
          l['destination'] = self.sn
          i = l['index']
          del(l['index'])
          r = requests.post(url, data=json.dumps(l), headers=headers)
          if self.delete and r.status_code == 200:
            self.cat.delete_sms(i)
      if self.run_once:
        break
      time.sleep(10)

if __name__ == '__main__':
  sd = SmsDaemon('/dev/ttyS0', '18805900896', False, True)
  sd.initDB()
  sd.start()
