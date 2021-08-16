from memory import MemoryRegion, SparseMemory

from memory import MemoryRegion
from areas import Areas
from game_states import GameStates
from frame_count import FrameCount

class Bitmask(object):
  def __init__(self, mask=0):
    self.mask = mask

  def __invert__(self):
    return type(self)(~self.mask)

  def __and__(self, rhs):
    return type(self)(self.mask & rhs.mask)

  def __or__(self, rhs):
    return type(self)(self.mask | rhs.mask)

  def __eq__(self, rhs):
    return self.mask == rhs.mask

  def __ne__(self, rhs):
    return self.mask != rhs.mask

class Items(Bitmask):
  def __iter__(self):
    items = self.mask
    if items & 0x0001: yield 'Varia'
    if items & 0x0002: yield 'SpringBall'
    if items & 0x0004: yield 'Morph'
    if items & 0x0008: yield 'ScrewAttack'
    if items & 0x0020: yield 'Gravity'
    if items & 0x0100: yield 'HiJump'
    if items & 0x0200: yield 'SpaceJump'
    if items & 0x1000: yield 'Bomb'
    if items & 0x2000: yield 'SpeedBooster'
    if items & 0x4000: yield 'Grapple'
    if items & 0x8000: yield 'XRayScope'

class Beams(Bitmask):
  def __iter__(self):
    beams = self.mask
    if beams & 0x1000: yield 'Charge'
    if beams & 0x0001: yield 'Wave'
    if beams & 0x0002: yield 'Ice'
    if beams & 0x0004: yield 'Spazer'
    if beams & 0x0008: yield 'Plasma'

class LocationIDs(Bitmask):
  def __iter__(self):
    locations = self.mask
    loc = 0
    while locations != 0:
      if locations & 1:
        yield loc
      locations >>= 1
      loc += 1

class State(object):
  def __init__(self, **attrs):
    for name in attrs:
      setattr(self, name, attrs[name])

  def __repr__(self):
    return "State(%s)" % ', '.join([ '%s=%s' % (k,repr(v)) for k,v in
      self.__dict__.items() ])

  @staticmethod
  def read_from(sock):
    mem = SparseMemory(
        MemoryRegion.read_from(sock, 0x0790, 0x1f),
        MemoryRegion.read_from(sock, 0x0990, 0xef),
        MemoryRegion.read_from(sock, 0xD800, 0x8f),
        MemoryRegion.read_from(sock, 0x0F80, 0x4f),
        MemoryRegion.read_from(sock, 0x05B0, 0x0f))

    # door_id = mem.short(0x78D)
    room_id = mem.short(0x79B)
    # door = doors.from_id(door_id)
    # room = rooms.from_id(room_id)

    region_id = mem.short(0x79F) 
    area = Areas.get(region_id, hex(region_id))

    game_state_id = mem.short(0x998)
    game_state = GameStates.get(game_state_id, hex(game_state_id))

    collected_items_bitmask = mem.short(0x9A4)
    collected_beams_bitmask = mem.short(0x9A8)

    igt_frames = mem.short(0x9DA)
    igt_seconds = mem[0x9DC]
    igt_minutes = mem[0x9DE]
    igt_hours = mem[0x9E0]
    fps = 60.0 # TODO
    igt = FrameCount(216000 * igt_hours + 3600 * igt_minutes + 60 * igt_seconds + igt_frames)

    # Varia randomizer RTA clock
    rta_frames = mem.short(0x5B8)
    rta_rollovers = mem.short(0x5BA)
    rta = FrameCount(rta_frames + (rta_rollovers << 16))

    # event_flags = mem.short(0xD821)
    locations = mem.bignum(0xD870, 15)

    return State(
        # door=door,
        # room=room,
        room_id=room_id,
        area=area,
        game_state_id=game_state_id,
        game_state=game_state,
        # event_flags=event_flags,
        igt=igt,
        rta=rta,
        fps=fps,
        rta_frames=rta_frames,
        rta_rollovers=rta_rollovers,
        items=Items(collected_items_bitmask),
        beams=Beams(collected_beams_bitmask),
        locations=LocationIDs(locations),
        )
