# -*- coding: utf-8 -*-

import sqlite3
from SmsCat import SmsCat
from datetime import datetime

cat = SmsCat('/dev/ttyS0')
l =  cat.read_sms_list()
print l


conn = sqlite3.connect('db.sqlite')
cursor = conn.cursor()

cursor.executescript("""

  DROP TABLE IF EXISTS SMS;

  CREATE TABLE IF NOT EXISTS SMS(
    Id INTEGER PRIMARY KEY,
    Send_On DATETIME NOT NULL, 
    Source TEXT NOT NULL,
    Content TEXT NOT NULL,
    Label TEXT,
    Pos Integer NOT NULL,
    Len Integer
  );

""")


  
conn.commit()
if l:
  cursor.executemany("""
    INSERT INTO SMS (
                Send_On, 
                Source, 
                Content,
                label,
                Pos,
                Len)
    VALUES (:send_on, :source, :content, :label, :pos, :len)
  """, l)

conn.commit()
cursor.close()
conn.close()
