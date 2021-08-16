import pty
import os
from subprocess import Popen, PIPE

class Toilet(object):
  def __init__(self, font=None, filters=[], filter=None, format=None, width=None):
    filters = [ 'crop', *filters ]
    if filter:
      filters.append(filter)

    cmd = [ 'toilet' ]
    if font: cmd.extend(('-f', font))
    if filters: cmd.extend(('-F', *filters))
    if format: cmd.extend(('-E', format))
    if width: cmd.extend(('-w', width))

    p = Popen(cmd + [ 'FOO' ], stdout=PIPE)
    output = p.communicate()[0]
    self.height = len(output.splitlines())

    pid, fd = pty.fork()
    if pid == 0:
      os.execvp(cmd[0], cmd)

    self.pid = pid
    self.fd = fd
    self.r = os.fdopen(self.fd, 'r')
    self.w = os.fdopen(self.fd, 'w')

  def render(self, text):
    print(text, file=self.w)
    self.r.readline() # read echo
    s = [ ]
    for i in range(0, self.height):
      s.append(self.r.readline().rstrip("\n"))

    while len(s) > 0 and s[-1].strip() == '': s.pop()
    while len(s) > 0 and s[0].strip() == '': s.pop(0)

    return s
