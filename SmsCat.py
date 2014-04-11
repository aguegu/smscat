# -*- coding: utf-8 -*-

import serial
import time
import re
import logging
from datetime import datetime
import json

logging.basicConfig(level=logging.WARNING)

class SmsCat:
  def __init__(self, port):
    self.sp = serial.Serial()
    self.sp.port = port
    self.sp.baudrate = 115200
    self.sp.parity = serial.PARITY_NONE
    self.sp.stopbit = serial.STOPBITS_ONE
    self.sp.bytesize = serial.EIGHTBITS
    self.sp.timeout = 2

    assert not self.sp.isOpen()
    
    self.sp.open()
    while True:
      r = self.transmit('AT')
      if len(r) == 1 and r[0] == 'OK':
        break
   
    r = self.transmit('AT+CMGF?')
    self.cmgf = int(r[0][-1])

  # 0: PDU; 1: TEXT
  def set_cmgf(self, cmgf):
    assert cmgf in (0, 1)
    if cmgf != self.cmgf:
      sms.transmit('AT+CMGF=%d' % cmgf)
      self.cmgf = cmgf

  def getResponse(self):
    recv = []
    while True:
      s = self.sp.readline().strip()
      if s:
        logging.info('< %s' % s)
        recv.append(s)
        if s == 'OK' or s == 'ERROR':
          break

    return recv
  
  def transmit(self, content):
    logging.info('> %s' % content)
    self.sp.write(content + '\r')
    self.sp.flush()
    return self.getResponse()

  def send_sms_text(self, phone_number, text):
    self.set_cmgf(1)
    self.sp.write("AT+CMGS=%s\r" % phone_number)
    self.sp.flush()
    self.sp.read(4)
    self.sp.write(text)
    self.sp.write('%c' % 0x1a)
    self.sp.flush()
    return self.getResponse()

  def close(self):
    self.sp.close()

  @staticmethod
  def ucs2(s):
    return ''.join(sum(zip(s[1::2], s[::2]),()))

  @classmethod
  def ucs2_phone(cls, s):
    if len(s) % 2:
      s += 'F'
    s = '86' + s
    return cls.ucs2(s)
  
  @staticmethod
  def msg(s):
    assert type(s) is unicode
    s = ''.join('{:04X}'.format(ord(c)) for c in s)
    return '{:02x}'.format(len(s) / 2) + s 

  def send_sms_pdu(self, phone_number, text):
    self.set_cmgf(0)
#    header = "00"      # use the on sim sms center 
    header = '0891{0}'.format(SmsCat.ucs2_phone('13800591500'))
#    header = '07A1{0}'.format(SmsCat.ucs2('13800591500F'))
    pdu = "11000D91{0}000800{1}".format(SmsCat.ucs2_phone(phone_number), SmsCat.msg(text))
    logging.info('%d %s' % (len(pdu) / 2, header + pdu))
    self.sp.write("AT+CMGS=%02d\r" % (len(pdu) / 2))
    self.sp.flush()
    self.sp.readline()
    self.sp.write(header + pdu)
    self.sp.write('%c' % 0x1a)
    self.sp.flush()
    return self.getResponse()

  def decode_pdu(self, pdu):
    if pdu[:6] == '050003':
      group = pdu[6:][:2]
      total = int(pdu[8:][:2], 16)
      index = int(pdu[10:][:2], 16)
    
      pdu = pdu[12:]

      s = ''.join(unichr(int(c, 16)) for c in re.findall(r'....', pdu))
      content = "[%d/%d] <%s>: %s" % (index, total, group, s)
    elif pdu[:6] == '060504':
      content = '(MMS)'
    else:
      content = ''.join(unichr(int(c, 16)) for c in re.findall(r'....', pdu))

    return content
 
  def read_sms_text(self, index):
    self.set_cmgf(1)
    recv = self.transmit("AT+CMGR=%d" % index)
    if len(recv) and recv[0].find('"') != -1:
      d = dict(zip(['source', 'send_on'], re.findall(r'\"([^\"]+)\"', recv[0])[1:]))
      if d['source'][:3] == '+86':
        d['source'] = d['source'][3:]
      if d['source'][-1] == 'F':
        d['source'] = d['source'][:-1]
      
      d['id'] = index
      d['send_on'] = datetime.strptime(d['send_on'][:-3], '%y/%m/%d,%H:%M:%S')
      d['content'] = self.decode_pdu(recv[1])
      return d

  def decode_pdu_full(self, pdu):
    d = {}
    center_length = int(pdu[:2], 16) * 2
#    d['center'] = SmsCat.ucs2(pdu[4:(center_length + 2)])[:-1]
    source_length =(int(pdu[center_length + 4:][:2], 16) + 1) / 2 * 2
    d['source'] = SmsCat.ucs2(pdu[center_length + 8:][:source_length])
    if d['source'][:2] == '86':
      d['source'] = d['source'][2:]
    
    encoding = pdu[center_length + 10 + source_length:][:2]
    d['send_on'] = datetime.strptime(SmsCat.ucs2(pdu[center_length + source_length + 12:][:12]), '%y%m%d%H%M%S')

    content = pdu[-int(pdu[center_length + source_length + 26:][:2], 16) * 2:]
    
    if encoding == '08':
      d['content'] = self.decode_pdu(content)
    elif encoding == '00':
      content = pdu[-int(pdu[center_length + source_length + 26:][:2], 16) / 8 * 7 * 2:]
      s = ''.join((re.findall(r'..', content)[::-1]))
      r = ''
      n = int(s, 16)
      while n:
        c = chr(n & 0x7f)
        n >>= 7
        r += c
      d['content'] = unicode(r)
    elif encoding == '04':
      d['content'] = u'(MMS)'

    return d

  def read_sms_pdu(self, index):
    self.set_cmgf(0)

    recv = self.transmit("AT+CMGR=%d" % index)
    if len(recv) != 3:
      return

    d = self.decode_pdu_full(recv[1])
    d['id'] = index
    return d

  def read_sms_list(self):
    self.set_cmgf(0)
    l = self.transmit('AT+CMGL=4')
    if len(l) % 2 == 1 and l[-1] == 'OK':
      l = zip(l[::2], l[1::2])
      ll = []
      for m in l:
        d = self.decode_pdu_full(m[1])
        d['index'] = int(re.findall(r': (\d+),', m[0])[0])
        ll.append(d)
    return ll  

if __name__ == '__main__':
  sms = SmsCat('/dev/ttyS0')
#  sms.send_sms_text('13665036099', 'hello, world, again.')
#  sms.send_sms_pdu("13665036099", u'使用8字节国内短信中心发送到8位国际号码')
#  sms.transmit('AT+IPR')
  
  print json.dumps(sms.read_sms_list())

  sms.close()
