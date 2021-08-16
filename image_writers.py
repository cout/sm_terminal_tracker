import sys
from base64 import standard_b64encode

# Based on examples at https://sw.kovidgoyal.net/kitty/graphics-protocol/
class KittyImageWriter(object):
  @staticmethod
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


  @staticmethod
  def write_chunked(file=sys.stdout, **cmd):
    data = standard_b64encode(cmd.pop('data'))
    while data:
      chunk, data = data[:4096], data[4096:]
      m = 1 if data else 0
      file.buffer.write(KittyImageWriter.serialize_gr_command(payload=chunk, m=m, **cmd))
      file.flush()
      cmd.clear()

  def write(self, image, file):
    w, h = image.size

    if image.mode == 'RGB':
      f = 24
    elif image.mode == 'RGBA':
      f = 32
    else:
      raise ValueError("Image must be RGB or RGBA")

    self.write_chunked(a='T', f=f, s=w, v=h, data=image.tobytes(), file=file)
