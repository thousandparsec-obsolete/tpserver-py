
from config import db, netlib, admin

from SQL import *

class Order(SQLTypedBase):
	tablename = "`order`"
	tablename_extra = "`order_extra`"
	types = {}

	def realid(cls, oid, slot):
		"""\
		Order.realid(objectid, slot) -> id
		
		Returns the database id for the order found on object at slot.
		"""
		result = db.query("""SELECT id FROM %(tablename)s WHERE oid=%(oid)s and slot=%(slot)s""", tablename=cls.tablename, oid=oid, slot=slot)
		if len(result) != 1:
			return -1
		else:
			return result[0]['id']
	realid = classmethod(realid)

	def number(cls, oid):
		"""\
		Order.number(objectid) -> number

		Returns the number of orders on an object.
		"""
		return db.query("""SELECT count(id) FROM %(tablename)s WHERE oid=%(oid)s""", tablename=cls.tablename, oid=oid)[0]['count(id)']
	number = classmethod(number)

	def desc_packet(cls, sequence, typeno):
		"""\
		Order.desc_packet(sequence, typeno)

		Builds an order description packet for the specified order type.
		"""
		# Pull out the arguments
		if not cls.types.has_key(typeno):
			raise NoSuch("No such order type.")

		order = cls(typeno=typeno)
		
		arguments = []
		for attribute in order.attributes.values():
			if attribute.level != 'private':
				arguments.append((attribute.name, attribute.type, attribute.desc))

		# FIXME: This should send a correct last modified time
		return netlib.objects.OrderDesc(sequence, typeno, order.__class__.__name__, order.__class__.__doc__, arguments, 0)
	desc_packet = classmethod(desc_packet)
	
	def load_all(cls):
		"""\
		Order.load_all()

		Loads all the possible order types from the database.
		"""
		for id in cls.types.keys():
			cls.desc_packet(0, id).register()
	load_all = classmethod(load_all)

	def __init__(self, oid=None, slot=None, packet=None, type=None, typeno=None, id=None):
		if oid != None and slot != None:
			id = self.realid(oid, slot)
		else:
			id = None
			
		SQLTypedBase.__init__(self, id, packet, type, typeno)

	def allowed(self, user):
		# FIXME: This is a hack.
		return (user.id in admin) or (hasattr(self.object, "owner") and self.object.owner == user.id)

	def object(self):
		if not hasattr(self, "_object"):
			from Object import Object
			self._object = Object(self.oid)
		return self._object
	object = property(object)

	def insert(self):
		try:
			db.query("BEGIN")
		
			number = self.number(self.oid)
			if self.slot == -1:
				self.slot = number
			elif self.slot <= number:
				# Need to move all the other orders down
				print self.todict()
				db.query("""UPDATE %(tablename)s SET slot=slot+1 WHERE slot>=%(slot)s AND oid=%(oid)s""", self.todict())
			else:
				raise NoSuch("Cannot insert to that slot number.")
			
			self.save()

		except Exception, e:
			db.rollback()
			raise
		else:
			db.commit()

	def save(self):
		try:
			db.begin()
			
			self.object.save()	
			if not hasattr(self, 'id'):
				id = self.realid(self.oid, self.slot)
				if id != -1:
					self.id = id
			SQLTypedBase.save(self)
		except Exception, e:
			db.rollback()
			raise
		else:
			db.commit()

	def remove(self):
		try:
			db.begin()
			
			# Move the other orders down
			db.query("""UPDATE %(tablename)s SET slot=slot-1 WHERE slot>=%(slot)s AND oid=%(oid)s""", self.todict())
			
			self.object.save()
			SQLTypedBase.remove(self)

		except Exception, e:
			db.rollback()
			raise
		else:
			db.commit()

	def to_packet(self, sequence):
		# Preset arguments
		args = [sequence, self.oid, self.slot, self.typeno, self.turns(), self.resources()]
		SQLTypedBase.to_packet(self, sequence, args)
		return netlib.objects.Order(*args)

	def from_packet(self, packet):
		self.worked = 0

		self.oid = packet.id
		self.slot = packet.slot
		SQLTypedBase.from_packet(self, packet)

		del self.id

	def __str__(self):
		if hasattr(self, 'id'):
			return "<Order type=%s id=%s oid=%s slot=%s>" % (self.typeno, self.id, self.oid, self.slot)
		else:
			return "<Order type=%s id=XX oid=%s slot=%s>" % (self.typeno, self.oid, self.slot)

	def turns(self, turns=0):
		"""\
		Number of turns this order will take to complete.
		"""
		return turns + 0
	
	def resources(self):
		"""\
		The resources this order will consume/use. (Negative for producing).
		"""
		return []
		
