# -*- coding: utf-8 -*-

import sqlite3
from SmsCat import SmsCat, logging
from datetime import datetime
import time
from threading import Thread
import json
import requests
from datetime import datetime

inbox_url = 'http://localhost:5000/api/inbox'
outbox_url = 'http://localhost:5000/api/outbox'

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
      CREATE  TABLE IF NOT EXISTS INBOX(
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
    spans = [0, 2, 4, 8, 16]
    span_index = 0
    size = self.cat.getSimSize()
    while True:
      logging.info(datetime.now().isoformat())
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
          try:
            r = requests.post(inbox_url, data=json.dumps(l), headers=headers)
            print l
            if self.delete and r.status_code == 200:
              self.cat.delete_sms(i)
          except requests.ConnectionError:
            logging.error("could not access server.")
            exit(1)

      r = requests.put(outbox_url + '?source=%s&action=assign' % self.sn) 
      if r.status_code == 200:
        d = r.json()
        self.cat.send_sms(d['destination'], d['content'])
        r = requests.put(outbox_url + '?id=%d&action=send' % d["id"])
        assert r.status_code == 200

      if len(ll) > size * 3 / 4 and span_index in range(1, len(spans)):
        span_index -= 1
      elif len(ll) < size / 4 and span_index in range(0, len(spans) - 1):
        span_index += 1
    
      if self.run_once:
        break

      time.sleep(spans[span_index])

if __name__ == '__main__':
  sd = SmsDaemon('/dev/ttyS0', '18805900896', False, True)
  sd.initDB()
  sd.start()
