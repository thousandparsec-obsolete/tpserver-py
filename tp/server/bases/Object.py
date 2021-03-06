"""\
The basis for all objects that exist.
"""
# Module imports
from sqlalchemy import *

# Local imports
from tp.server.db import *
from tp import netlib
from SQL import SQLBase, SQLTypedBase, SQLTypedTable, quickimport
from Order import Order

class Object(SQLTypedBase):
	table = Table('object', metadata,
		Column('game',	    Integer,     nullable=False, index=True, primary_key=True),
		Column('id',	    Integer,     nullable=False, index=True, primary_key=True),
		Column('type',	    String(255), nullable=False, index=True),
		Column('name',      Binary,      nullable=False),
		Column('size',      Integer(64), nullable=False),
		Column('posx',      Integer(64), nullable=False, default=0),
		Column('posy',      Integer(64), nullable=False, default=0),
		Column('posz',      Integer(64), nullable=False, default=0),
		Column('velx',      Integer(64), nullable=False, default=0),
		Column('vely',      Integer(64), nullable=False, default=0),
		Column('velz',      Integer(64), nullable=False, default=0),
		Column('parent',    Integer,     nullable=True),
		Column('time',	    DateTime,    nullable=False, index=True,
			onupdate=func.current_timestamp(), default=func.current_timestamp()),

		UniqueConstraint('id', 'game'),
		ForeignKeyConstraint(['parent'], ['object.id']),
		ForeignKeyConstraint(['game'],   ['game.id']),
	)
	Index('idx_object_position', table.c.posx, table.c.posy, table.c.posz)

	table_extra = SQLTypedTable('object')

	types = {}
	orderclasses = {}

	bypos_size = [asc(table.c.size)]

	@classmethod
	def bypos(cls, pos, size=0, limit=-1, orderby=None):
		"""\
		Object.bypos([x, y, z], size) -> [Object, ...]

		Return all objects which are centered inside a sphere centerd on
		size and radius of size.
		"""
		pos = long(pos[0]), long(pos[1]), long(pos[2])

		c = cls.table.c

		bp_x = bindparam('x')
		bp_y = bindparam('y')
		bp_z = bindparam('z')
		bp_s = bindparam('size')
		where = ((c.size+bp_s) >= \
					func.abs((c.posx-bp_x)) + \
					func.abs((c.posy-bp_y)) + \
					func.abs((c.posz-bp_z)))
#		where = (((c.size+bp_s)*(c.size+bp_s)) >= \
#					((c.posx-bp_x) * (c.posx-bp_x)) + \
#					((c.posy-bp_y) * (c.posy-bp_y)) + \
#					((c.posz-bp_z) * (c.posz-bp_z)))
		if orderby is None:
			orderby = [asc(c.time), desc(c.size)]

		s = select([c.id, c.time], where, order_by=orderby)
		if limit != -1:
			s.limit = limit

		results = s.execute(x=pos[0], y=pos[1], z=pos[2], size=size).fetchall()
		return [(x['id'], x['time']) for x in results]

	@classmethod
	def byparent(cls, id):
		"""\
		byparent(id)

		Returns the objects which have a parent of this id.
		"""
		t = cls.table

		# FIXME: Need to figure out what is going on here..
		bp_id = bindparam('id')
		results = select([t.c.id, t.c.time], (t.c.parent==bp_id) & (t.c.id != bp_id)).execute(id=id).fetchall()
		return [(x['id'], x['time']) for x in results]

	@classmethod
	def bytype(cls, type):
		"""\
		bytype(id)

		Returns the objects which have a certain type.
		"""
		t = cls.table

		# FIXME: Need to figure out what is going on here..
		results = select([t.c.id, t.c.time], (t.c.type==bindparam('type'))).execute(type=type).fetchall()
		return [(x['id'], x['time']) for x in results]

	def __init__(self, id=None, type=None):
		self.name = "Unknown object"
		self.size = 0
		self.posx = 0
		self.posy = 0
		self.posz = 0
		self.velx = 0
		self.vely = 0
		self.velz = 0
		self.parent = 0

		SQLTypedBase.__init__(self, id, type)

	def protect(self, user):
		o = SQLBase.protect(self, user)
		if hasattr(self, "owner") and self.owner != user.id:
			print self.owner
			def empty():
				return 0
			o.orders = empty
			
			def empty():
				return []
			o.ordertypes = empty
		return o

	def remove(self):
		# FIXME: Need to remove associated orders in a better way
		#delete(Order.table).execute(oid=self.id)
		# Remove any parenting on this object.
		t = Object.table
		update(t, t.c.parent==self.id, {t.c.parent: 0}).execute()
		SQLTypedBase.remove(self)
	
	def orders(self):
		"""\
		orders()

		Returns the number of orders this object has.
		"""
		return Order.number(self.id)

	def ordertypes(self):
		"""\
		ordertypes()

		Returns the valid order types for this object.
		"""
		# FIXME: This probably isn't good
		if not hasattr(self, "_ordertypes"):
			self._ordertypes = []
			for type in self.orderclasses:
				self._ordertypes.append(quickimport(type).typeno)
		
		return self._ordertypes

	def contains(self):
		"""
		contains()

		Returns the objects which this object contains.
		"""
		ids = self.byparent(self.id)
		if len(ids) > 0:
			return zip(*ids)[0]
		else:
			return tuple()

	def to_packet(self, user, sequence):
		# Preset arguments
		self, args = SQLTypedBase.to_packet(self, user, sequence)
		return netlib.objects.Object(sequence, self.id, self.typeno, self.name, 
				self.size, 
				self.posx, self.posy, self.posz, 
				self.velx, self.vely, self.velz, 
				self.contains(), self.ordertypes(), self.orders(), 
				self.time, 
				*args)

	@classmethod
	def id_packet(cls):
		return netlib.objects.Object_IDSequence

	def __str__(self):
		return "<Object %s id=%s>" % (".".join(self.type.split('.')[3:]), self.id)

	def ghost(self):
		"""\
		Returns true if this object should be removed.
		"""
		if hasattr(self, "owner"):
			return self.owner == 0
		else:
			return False
