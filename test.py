# -*- coding: utf-8 -*-

import serial
import time
import re

class SmsCat:
  def __init__(self, port, sms_center = ''):
    self.sp = serial.Serial()
    self.sp.port = port
    self.sp.baudrate = 115200
    self.sp.parity = serial.PARITY_NONE
    self.sp.stopbit = serial.STOPBITS_ONE
    self.sp.bytesize = serial.EIGHTBITS
    self.sp.timeout = 2
    self.sms_center = SmsCat.ucs2_phone(sms_center)
   
  def open(self):
    self.sp.open()
   
  def transmit(self, content):
    print '>', content
    self.sp.write(content + '\r')
    self.sp.flush()
    recv = []
    while True:
      s = self.sp.readline().strip()
      if s:
        print '<', s

        if s == 'OK' or s == 'ERROR':
          break
        else:
          recv.append(s)

    return recv

  def send_sms_text(self, phone_number, text):
    self.sp.write("AT+CMGS=%s\r" % phone_number)
    self.sp.flush()
    self.sp.read(4)
    self.sp.write(text)
    self.sp.write('%c' % 0x1a)
    self.sp.flush()
    while True:
      s = self.sp.readline().strip()
      if s:
        print '<', s
      if s == 'OK' or s == 'ERROR':
        break

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
#    pdu = "0891{0}".format(self.sms_center)
    pdu = "00"
    s = "11000D91{0}000800{1}".format(SmsCat.ucs2_phone(phone_number), SmsCat.msg(text))
    print len(s) / 2, pdu + s
    self.sp.write("AT+CMGS=%02d\r" % (len(s) / 2))
    self.sp.flush()
    self.sp.readline()
    self.sp.write(pdu + s)
    self.sp.write('%c' % 0x1a)
    self.sp.flush()
    while True:
      s = self.sp.readline().strip()
      if s:
        print '<', s
      if s == 'OK':
        break

  def read_sms_text(self, index):
    recv = self.transmit("AT+CMGR=%d" % index)
    if len(recv) and recv[0].find('"') != -1:
      d = dict(zip(['status', 'source', 'sent_on'], re.findall(r'\"([^\"]+)\"', recv[0])))
      d['pdu'] = recv[1]

      index = int(d['pdu'][:2], 16)
      
      if index == 5 or index == 6:
        print re.findall('..', d['pdu'][:index * 2 + 2])
        d['pdu'] = d['pdu'][index * 2 + 2:]

      d['content'] = ''.join(unichr(int(c, 16)) for c in re.findall('....', d['pdu']))

      print d['content']

  def read_sms_pdu(self, index):
    center = '683108501905F0'
    center = ''.join(sum(zip(center[1::2], center[::2]),()))        
    if center[-1] == 'F':
      center = center[:-1]
    
    print center
    
    s = '39DCCD56A3CD6431580E77B3D56833590C96C3DD6C35DA4C1683E570375B8D3693C56039DCCD56A3CD6431580E77B3D56833590C96C3DD6C35DA4C1683E570375B8D3693C56039DCCD56A3CD6431580E77B3D56833590C96C3DD6C35DA4C1683E570375B8D3693C56039DCCD56A3CD6431580E77B3D56833590C96C3DD6C35DA4C1683E570375B8D3693C560'
    s = ''.join((re.findall(r'..', s)[::-1]))
    
    r = ''
    
    d = int(s, 16)
    while d:
      c = chr(d & 0x7f)
      d >>= 7
      r += c

    print r
    
  

   
if __name__ == '__main__':
  sms = SmsCat('/dev/ttyS0', '13800591500')
  sms.open()
#  sms.transmit('AT+CSCA?')
#  sms.transmit('AT')
  sms.transmit('AT+CMGF=0')
  sms.transmit('AT+CMGF?')
#  sms.send_sms_text('13665036099', 'hello, world, again.')
#  sms.send_sms_text('13665036099', '9876543210' * 16)
#  sms.send_gsm_text('15959159137', 'hello, world, again and again, too.')
#  sms.transmit('AT+CGMR')
#  sms.transmit('AT+IPR')
#  sms.close()
#  print SmsCat.ucs2("13800591500")
#  print SmsCat.msg(u'你好')
#  print SmsCat.msg(u'你好000')
  sms.send_sms_pdu("13665036099", u'你好啊！')
#  sms.send_pdu_text("13605945341", u'341341341234才文，来帮我接亲啊~ weihong.guan@gmail.com, 13665036099')
  
#  for i in range(1, 40):
#    sms.read_sms(i)
  sms.read_sms_pdu(0)


