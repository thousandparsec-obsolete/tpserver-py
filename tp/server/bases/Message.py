
import db
import netlib

from SQL import *

class Message(SQLBase):
	tablename = "tp.message"

	def realid(bid, slot):
		result = db.query("""SELECT id FROM tp.message WHERE bid=%(bid)s and slot=%(slot)s""", bid=bid, slot=slot)
		if len(result) != 1:
			return -1
		else:
			return result[0]['id']
	realid = staticmethod(realid)

	def number(bid):
		return db.query("""SELECT count(id) FROM tp.message WHERE bid=%(bid)s""", bid=bid)[0]['count(id)']
	number = staticmethod(number)

	def __init__(self, id=None, slot=None, packet=None):
		SQLBase.__init__(self)

		if id != None and slot != None:
			self.load(id, slot)
		if packet != None:
			self.from_packet(packet)

	def load(self, bid, slot):
		id = self.realid(bid, slot)
		if id == -1:
			raise NoSuch("Order %s %s does not exists" % (bid, slot))
			
		SQLBase.load(self, id)

	def insert(self):
		number = self.number(self.bid)
		if self.slot == -1:
			self.slot = number
		elif self.slot <= number:
			# Need to move all the other orders down
			db.query("""UPDATE tp.message SET slot=slot+1 WHERE slot>=%(slot)s AND bid=%(bid)s""" % self.todict())
		else:
			raise NoSuch("Cannot insert to that slot number.")
		
		self.save()

	def save(self):
		if not hasattr(self, 'id'):
			id = self.realid(self.bid, self.slot)
			if id != -1:
				self.id = id
			
		SQLBase.save(self)

	def remove(self):
		# Move the other orders down
		db.query("""UPDATE tp.message SET slot=slot-1 WHERE slot>=%(slot)s AND bid=%(bid)s""", self.todict())

		SQLBase.remove(self)

	def to_packet(self, sequence):
		# Preset arguments
		return netlib.objects.Message(sequence, self.bid, self.slot, [], self.subject, self.body)

	def from_packet(self, packet):
		self.__dict__.update(packet.__dict__)
		self.bid = self.id
		del self.id

	def __str__(self):
		return "<Message id=%s bid=%s slot=%s>" % (self.id, self.bid, self.slot)

	__repr__ = __str__
