#!/usr/bin/env python3

from retroarch.network_command_socket import NetworkCommandSocket

from state import State

from PIL import Image, ImageOps

import argparse
import time
import os.path
import base64

layout = [
  [ 'charge', 'ice', 'wave', 'spazer', 'plasma' ],
  [ 'morph', 'varia', 'springball', 'hj', 'spacejump' ],
  [ 'bombs', 'gravity', 'ridley', 'speed', 'screw' ],
  [ 'croc', 'kraid', 'phantoon', 'draygon', 'shaktool' ],
]

import sys
from base64 import standard_b64encode

def serialize_gr_command(**cmd):
  payload = cmd.pop('payload', None)
  cmd = ','.join('{}={}'.format(k, v) for k, v in cmd.items())
  ans = []
  w = ans.append
  w(b'\033_G'), w(cmd.encode('ascii'))
  if payload:
    w(b';')
    w(payload)
  w(b'\033\\')
  return b''.join(ans)


def write_chunked(**cmd):
  data = standard_b64encode(cmd.pop('data'))
  while data:
    chunk, data = data[:4096], data[4096:]
    m = 1 if data else 0
    sys.stdout.buffer.write(serialize_gr_command(payload=chunk, m=m,
                                                **cmd))
    sys.stdout.flush()
    cmd.clear()

class Icon(object):
  def __init__(self, name):
    self.name = name
    self.filename = 'images/%s.png' % name
    if os.path.exists(self.filename):
      self.image = Image.open(self.filename).convert('RGBA')
      self.nimage = self.image.convert('LA').convert('RGBA')
    else:
      print('%s does not exist' % self.filename)
      self.image = Image.new('RGBA', (32,32), (0, 0, 0, 0))
      self.nimage = Image.new('RGBA', (32,32), (0, 0, 0, 0))

class Grid(object):
  def __init__(self, layout):
    self.rows = [ ]
    for row in layout:
      self.rows.append([ Icon(name) for name in row ])

  def draw(self, stuff):
    image = Image.new('RGBA', (32*5, 32*4))
    for rowidx, row in enumerate(self.rows):
      for idx, icon in enumerate(row):
        x = idx * 32
        y = rowidx * 32
        image.paste(icon.image if icon.name in stuff else icon.nimage, (x, y))

    w, h = image.size
    write_chunked(a='T', f=32, s=w, v=h, data=image.tobytes())

def need_redraw(last_state, state):
  # TODO: bosses
  return last_state is None or \
         last_state.items != state.items or \
         last_state.beams != state.beams

def translate(name):
  name = name.lower()
  if name == 'screwattack':
    return 'screw'
  elif name == 'speedbooster':
    return 'speed'
  elif name == 'hijump':
   return 'hj'
  elif name == 'gravity':
    return 'grav'
  else:
    return name

def redraw(grid, state):
  stuff = [ ]
  stuff += [ translate(item) for item in state.items ]
  stuff += [ translate(beam) for beam in state.beams ]
  grid.draw(stuff)

def run(sock, grid):
  last_state = None
  while True:
    state = State.read_from(sock)
    if need_redraw(last_state, state):
      redraw(grid, state)
    last_state = state
    time.sleep(1)

if __name__ == '__main__':
  write_chunked(a='A', data=b'')
  parser = argparse.ArgumentParser(description='SM Terminal Tracker')
  args = parser.parse_args()

  sock = NetworkCommandSocket()
  grid = Grid(layout)

  run(sock, grid)
