
import db
import netlib

from SQL import *

class Order(SQLWithAttrBase):
	tablename = "tp.order"
	fieldname = "order"
	
	def realid(oid, slot):
		result = db.query("""SELECT id FROM tp.order WHERE oid=%(oid)s and slot=%(slot)s""", oid=oid, slot=slot)
		if len(result) != 1:
			return -1
		else:
			return result[0]['id']
	realid = staticmethod(realid)

	def number(oid):
		return db.query("""SELECT count(id) FROM tp.order WHERE oid=%(oid)s""", oid=oid)[0]['count(id)']
	number = staticmethod(number)

	def __init__(self, id=None, slot=None, packet=None):
		SQLWithAttrBase.__init__(self)

		if id != None and slot != None:
			self.load(id, slot)
		if packet != None:
			self.from_packet(packet)

	def load(self, oid, slot):
		id = self.realid(oid, slot)
		if id == -1:
			raise NoSuch("Order %s %s does not exists" % (oid, slot))
			
		SQLWithAttrBase.load(self, id)

	def insert(self):
		number = self.number(self.oid)
		if self.slot == -1:
			self.slot = number
		elif self.slot < number:
			# Need to move all the other orders down
			db.query("""UPDATE tp.order SET slot=slot+1 WHERE slot>=%(slot)s AND oid=%(oid)s""" % self.todict())
		else:
			raise NoSuch("Cannot insert to that slot number.")
		
		self.save()

	def save(self):
		if not hasattr(self, 'id'):
			id = self.realid(self.oid, self.slot)
			if id != -1:
				self.id = id
			
		SQLWithAttrBase.save(self)

	def remove(self):
		# Move the other orders down
		db.query("""UPDATE tp.order SET slot=slot-1 WHERE slot>=%(slot)s AND oid=%(oid)s""", self.todict())

		SQLWithAttrBase.remove(self)

	def to_packet(self, sequence):
		# Preset arguments
		args = [sequence, self.oid, self.slot, self.type, 0, []]

		for attribute in self.attributes():
			value = getattr(self, attribute['name'])
			args.append(value)

		return netlib.objects.Order(*args)

	def from_packet(self, packet):
		self.__dict__.update(packet.__dict__)
		self.oid = self.id
		del self.id

	def __str__(self):
		return "<Order type=%s id=%s oid=%s slot=%s>" % (self.type, self.id, self.oid, self.slot)

	__repr__ = __str__


