#!/usr/bin/env python3

from retroarch.network_command_socket import NetworkCommandSocket

from state import State
from image_writers import KittyImageWriter
from toilet import Toilet

from PIL import Image, ImageOps

import argparse
import time
import os.path
import sys

layout = [
  [ 'charge', 'ice', 'wave', 'spazer', 'plasma' ],
  [ 'morph', 'varia', 'springball', 'hj', 'spacejump' ],
  [ 'bombs', 'gravity', 'ridley', 'speed', 'screw' ],
  [ 'croc', 'kraid', 'phantoon', 'draygon', 'shaktool' ],
]

class Timer(object):
  def __init__(self):
    pass

  def render_timer(self, toilet, time, colors, prefix):
    lines = toilet.render(time)
    for idx, line in enumerate(lines):
      # color = text_colors[idx] or gradient_colors[-1]
      # color_pair = Curses.color_pair(color)
      # window.attron(color_pair) {
      #   window << prefix << line
      # }
      # window.clrtoeol()
      # window << "\n"
      print(line)

  def s_time(self, secs):
    h = '%d' % (secs // 3600)
    mm = '%02d' % ((secs // 1 % 3600) // 60)
    ss = '%02d' % (secs // 1 % 60)
    ff = '%02d' % ((secs * 100) // 1 % 100)
    return '%s:%s:%s.%s' % (h, mm, ss, ff)

  def draw(self, state, toilet):
    colors = None # TODO
    self.render_timer(toilet, " IGT: " + self.s_time(state.igt.to_seconds()), colors, "  ")
    self.render_timer(toilet, " RTA: " + self.s_time(state.rta.to_seconds()), colors, "")

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

  def draw(self, stuff, image_writer):
    image = Image.new('RGBA', (32*5, 32*4))
    for rowidx, row in enumerate(self.rows):
      for idx, icon in enumerate(row):
        x = idx * 32
        y = rowidx * 32
        image.paste(icon.image if icon.name in stuff else icon.nimage, (x, y))

    image_writer.write(image, file=sys.stdout)
    sys.stdout.flush()

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

def redraw(timer, grid, state, toilet, image_writer):
  stuff = [ ]
  stuff += [ translate(item) for item in state.items ]
  stuff += [ translate(beam) for beam in state.beams ]

  timer.draw(state, toilet)
  grid.draw(stuff, image_writer)

def run(sock, timer, grid, toilet, image_writer):
  last_state = None
  while True:
    state = State.read_from(sock)
    if need_redraw(last_state, state):
      redraw(timer, grid, state, toilet, image_writer)
    last_state = state
    time.sleep(1)

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='SM Terminal Tracker')
  args = parser.parse_args()

  sock = NetworkCommandSocket()
  grid = Grid(layout)
  timer = Timer()
  toilet = Toilet(format='utf8', font='future')
  image_writer = KittyImageWriter()

  run(sock, timer, grid, toilet, image_writer)
