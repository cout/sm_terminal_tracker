#!/usr/bin/env python3

from retroarch.network_command_socket import NetworkCommandSocket

from state import State
from image_writers import KittyImageWriter
from toilet import Toilet

from PIL import Image, ImageOps, ImageEnhance

import argparse
import time
import os.path
import sys
import curses

layout = [
  [ 'charge', 'ice', 'wave', 'spazer', 'plasma' ],
  [ 'morph', 'varia', 'springball', 'hj', 'spacejump' ],
  [ 'bombs', 'gravity', 'ridley', 'speed', 'screw' ],
  [ 'croc', 'kraid', 'phantoon', 'draygon', 'shaktool' ],
]

colors = {
  'timer': [ [ 40, -1, ], [ 41, -1 ], [ 42, -1 ] ],
}

class ColorPairs(object):
  def __init__(self):
    self.next = 1
    self.colors = { }
    self.gradients = { }

  def define(self, name, fg, bg):
    curses.init_pair(self.next, fg, bg)
    self.colors[name] = self.next
    self.next += 1

  def define_gradient(self, name, *pairs):
    names = [ ]
    for idx, pair in enumerate(pairs):
      n = name if idx == 0 else '%s-%s' % (name, idx)
      self.define(n, *pair)
      names.append(n)
    self.gradients[name] = names

  def __getitem__(self, name):
    return self.colors[name]

  def gradient(self, name):
    gradient = self.gradients[name]
    return [ self[name] for name in gradient ]

class Timer(object):
  def __init__(self):
    pass

  def render_timer(self, window, toilet, time, color_pairs, prefix):
    lines = toilet.render(time)
    colors = color_pairs.gradient('timer')
    for idx, line in enumerate(lines):
      color = colors[min(idx, len(colors)-1)]
      color_pair = curses.color_pair(color)
      window.addstr(prefix, color_pair)
      window.addstr(line, color_pair)
      window.clrtoeol()
      window.addstr("\n")

  def s_time(self, secs):
    h = '%d' % (secs // 3600)
    mm = '%02d' % ((secs // 1 % 3600) // 60)
    ss = '%02d' % (secs // 1 % 60)
    ff = '%02d' % ((secs * 100) // 1 % 100)
    return '%s:%s:%s.%s' % (h, mm, ss, ff)

  def draw(self, state, window, color_pairs, toilet):
    self.render_timer(window, toilet, " IGT: " + self.s_time(state.igt.to_seconds()), color_pairs, "  ")
    self.render_timer(window, toilet, " RTA: " + self.s_time(state.rta.to_seconds()), color_pairs, "")

class Icon(object):
  def __init__(self, name):
    self.name = name
    self.filename = 'images/%s.png' % name
    if os.path.exists(self.filename):
      self.image = Image.open(self.filename).convert('RGBA')
      self.nimage = ImageEnhance.Brightness(self.image.convert('LA').convert('RGBA')).enhance(0.5)
    else:
      self.image = Image.new('RGBA', (32,32), (0, 0, 0, 0))
      self.nimage = Image.new('RGBA', (32,32), (0, 0, 0, 0))

class Grid(object):
  def __init__(self, layout):
    self.last_state = None
    self.image = None
    self.rows = [ ]
    for row in layout:
      self.rows.append([ Icon(name) for name in row ])

  @staticmethod
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

  def render_image(self, state):
    stuff = [ ]
    stuff += [ self.translate(item) for item in state.items ]
    stuff += [ self.translate(beam) for beam in state.beams ]
    stuff += [ self.translate(boss) for boss in state.bosses ]

    image = Image.new('RGBA', (36*5, 36*4))
    for rowidx, row in enumerate(self.rows):
      for idx, icon in enumerate(row):
        x = idx * 36
        y = rowidx * 36
        image.paste(icon.image if icon.name in stuff else icon.nimage, (x, y))

    return image

  def need_render(self, state):
    # TODO: bosses
    return self.last_state is None or \
           self.last_state.items != state.items or \
           self.last_state.beams != state.beams

  def draw(self, state, image_writer):
    if self.need_render(state):
      self.image = self.render_image(state)
      self.last_state = state

    image_writer.write(self.image, file=sys.stdout)
    sys.stdout.flush()

class UI(object):
  def __init__(self, screen, layout, colors):
    self.screen = screen
    self.layout = layout
    self.colors = colors

    self.sock = NetworkCommandSocket()
    self.grid = Grid(layout)
    self.timer = Timer()
    self.toilet = Toilet(format='utf8', font='future')
    self.image_writer = KittyImageWriter()
    sys.stdout.write("\033[2J")
    sys.stdout.flush()

    self.window = curses.newwin(0, 0, 1, 2)
    self.window.clear()

    self.color_pairs = ColorPairs()
    for name, pairs in colors.items():
      if type(pairs) == list:
        self.color_pairs.define_gradient(name, *pairs)
      else:
        self.color_pairs.define(name, *pairs)

  @staticmethod
  def run(*args, **kwargs):
    screen = curses.initscr()

    try:
      curses.start_color()
      curses.use_default_colors()
      curses.curs_set(0)
      curses.noecho()

      ui = UI(*args, screen=screen, **kwargs)
      ui._run()

    finally:
      curses.endwin()

  def _run(self):
    self.done = False
    last_state = None
    while not self.done:
      state = State.read_from(self.sock)
      self.redraw(state)
      last_state = state
      self.process_input()

  def process_input(self):
    self.window.timeout(25)
    ch = self.window.getch()
    if ch >= 32 and ch < 128:
      s = chr(ch)
    else:
      s = ch
    self.handle_input(s)

  def handle_input(self, s):
    if s == 'q':
      self.done = True

  def redraw(self, state):
    # TODO: Calling clear() like this can IME introduce flicker, but
    # it's the only way I know of to clear images off the screen in
    # the version of kitty I am running (the documented escape sequence
    # for deleting images causes the terminal to hang).
    self.window.clear()

    self.window.move(0, 0)

    self.timer.draw(state, self.window, self.color_pairs, self.toilet)

    self.window.addstr("\n")

    # self.window.noutrefresh()
    # curses.doupdate()
    self.window.refresh()

    self.grid.draw(state, self.image_writer)

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='SM Terminal Tracker')
  args = parser.parse_args()

  UI.run(layout=layout, colors=colors)
