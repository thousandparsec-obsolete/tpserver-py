"""\
Classes for dealing with games hosted on the machine.
"""
# Module imports
import weakref
import os, socket
from sqlalchemy import *

import hashlib

# Local imports
from tp.server.db import *
from tp.server.db.enum import Enum

from tp.server.bases.SQL  import SQLBase, NoSuch

from tp.netlib import objects
from tp.netlib.discover.game import Game as DiscoverGame

# FIXME: There should be some way to store the ruleset parameters...

class Lock(SQLBase):
	"""
	Each server can add different types of locks to each game.

	The following lock types are supported:
		Serving    - This program is serving the database.
		Processing - This program is processing a turn.
	"""
	types = ['serving', 'processing']

	table = Table('lock', metadata,
		Column('game',	    Integer,     nullable=False, index=True, primary_key=True), # Game this lock is for
		Column('id',	    Integer,     nullable=False, index=True, primary_key=True),
		Column('locktype',  Enum(types), nullable=False, index=True),       # Locktype
		Column('host',      String(255), nullable=False, index=True),       # Hostname of the process is running on
		Column('pid',       Integer,     nullable=False, index=True), 		# PID of the process with the lock
		Column('time',	    DateTime,    nullable=False, index=True, 		# Last time the lock was updated
			onupdate=func.current_timestamp(), default=func.current_timestamp()),

		ForeignKeyConstraint(['game'], ['game.id']),
	)

	@classmethod
	def new(cls, type):
		"""
		Create a new lock of the given type.

		When a lock goes out of scope it will remove itself from the database.
		"""
		self = cls()
		self.local = True

		if not type in Lock.types:
			raise TypeError('Lock type can only be one of %s' % Lock.types)

		self.locktype = unicode(type)
		self.pid      = os.getpid()
		self.host     = socket.gethostname()
		self.save()
		print "Creating lock", self, hasattr(self, 'local') and self.local
		return self

	def __del__(self):
		if hasattr(self, 'id'):
			if hasattr(self, 'local') and self.local:
				dbconn.use(self.game)
				print "Removing lock", self, hasattr(self, 'local') and self.local
				self.remove()

	def __str__(self):
		if not hasattr(self, 'id'):
			id = '(new)'
		else:
			id = self.id
		return "<Lock-%s,%s %s by %s-%s>" % (id, self.game, self.locktype, self.host, self.pid) 

	@staticmethod
	def locked(type, game=None):
		t = Lock.table
		if game is None:
			return len(dbconn.execute(select([t.c.id], t.c.locktype==type)).fetchall()) > 0
		else:
			return len(dbconn.execute(select([t.c.id], (t.c.locktype==type)&(t.c.game==game.id))).fetchall()) > 0

	@staticmethod
	def cleanup():
		t = Lock.table
		dbconn.execute(delete(t, t.c.host==socket.gethostname()))
#		locallocks = dbconn.execute(select([t.c.game, t.c.id, t.c.pid, t.c.locktype], t.c.host==socket.gethostname())).fetchall()
#		for gid, id, pid, locktype in locallocks:
#			print "%s-%s" % (gid, id), pid, locktype

class Event(SQLBase):
	"""
	Sometimes 'Events' occur. This table stores them.

	When a server starts up it reads the latest event id from the table. 
	It then checks periodicly that no id greater then the current on has been
	added to the table.

	Events can be the following types,
		Shutdown      - Shutdown of a given game is requested (normally before deletion or upgrade).
		End of Turn   - An end of turn has occurred.

		Game Added    - A new game is added.
		Game Removed  - A game is removed.
		Game Updated  - Information about a game is updated.
	"""
	types = ['shutdown', 'endofturn', 'gameadded', 'gameremoved', 'gameupdated']

	table = Table('event', metadata,
		Column('id',	    Integer,     nullable=False, index=True, primary_key=True),
		Column('game',	    Integer,     nullable=True,  index=True),
		Column('eventtype', Enum(types), nullable=False, index=True),

		ForeignKeyConstraint(['game'], ['game.id']),
	)

	@classmethod
	def new(cls, eventtype, game=None):
		if not eventtype in Event.types:
			raise TypeError("Event type must be %r not %s" % (cls.types, eventtype))

		# Create a new event object
		if game != None and not isinstance(game, (Game, int, long)):
			raise TypeError("Second argument must be an ID or a game object not %r!" % game)

		e = Event()
		e.eventtype = eventtype
		e.game = game
		if game != None and isinstance(game, Game):
			e.game = game.id

		old = dbconn.use(None)
		e.insert()
		dbconn.use(old)

		return e

	@classmethod
	def latest(cls):
		"""\
		Get the lates Event id.
		"""
		old = dbconn.use(None)
		try:
			c = cls.table.c
			try:
				return select([c.id], order_by=[desc(c.id)], limit=1).execute().fetchall()[0][0]
			except IndexError:
				return -1
		finally:
			dbconn.use(old)

	@classmethod
	def since(cls, id):
		"""
		Get all events since a given id.
		"""
		old = dbconn.use(None)
		try:
			dbconn.use(None)
			c = cls.table.c
			return [Event(id=x['id']) for x in select([c.id], c.id>id, order_by=[asc(c.id)]).execute()]
		finally:
			dbconn.use(old)

	def __str__(self):
		if not hasattr(self, 'id'):
			id = '(new)'
		else:
			id = self.id
		return "<Event-%s (Game - %s) %s>" % (id, self.game, self.eventtype) 
	__repr__ = __str__

class Connection(SQLBase):
	"""\
	Events regarding connections get recorded in this table.

	The following event types are supported:
		connect    - A connection is made from an IP address.
		login      - A person logs in on the connection.
		disconnect - A connection is terminated.
	"""
	types = ['connect', 'login', 'disconnect']

	table = Table('connection', metadata,
		Column('id',	    Integer,     nullable=False, index=True, primary_key=True),
		Column('ip',        String(255), nullable=False, index=True),
		Column('eventtype', Enum(types), nullable=False, index=True),
		Column('time',	    DateTime,    nullable=False, index=True,
			onupdate=func.current_timestamp(), default=func.current_timestamp()),

		UniqueConstraint('id'),
	)


class Game(SQLBase):
	"""
	This class represents the various "Games" which exist on the server. 

	It is a "singlton" class, meaning that only one instance exists for each game.
	"""

	table = Table('game', metadata,
		Column('id',	    Integer,     nullable=False, index=True, primary_key=True),
		Column('rulesetname', String(255), nullable=False, index=True),       # Ruleset this game uses
		Column('shortname', String(255), nullable=False, index=True),       # Computer name
		Column('longname',  Binary,      nullable=False, default=""), 		# Human readable name
		Column('admin',     String(255), nullable=False, index=True), 		# Admin's email address
		Column('comment',   Binary,      nullable=False, default=""), 		# A generic comment
		Column('turn',	    Integer,     nullable=False), 					# The current turn of the game
		Column('commandline', Binary,    nullable=False), 					# The command line used to create the game
		Column('time',	    DateTime,    nullable=False, index=True,
			onupdate=func.current_timestamp(), default=func.current_timestamp()),

		UniqueConstraint('shortname'),
	)

	__cache = weakref.WeakValueDictionary()
	def __new__(cls, id=None, shortname=None, longname=None):
		# Try and return the object from the cache instead...
		if not id is None:
			try:
				return cls.__cache[id]
			except KeyError:
				pass

		if not longname is None:
			shortname = cls.munge(longname)

		if not shortname is None:
			try:
				return cls.__cache[shortname]
			except KeyError:
				pass
		
		# Call the __init__ method of the super class
		self = SQLBase.__new__(cls)
		if not id is None:
			SQLBase.__init__(self, id=id)
		if not (shortname is None):
			SQLBase.__init__(self, id=self.gameid(shortname))
		if not (longname is None):
			SQLBase.__init__(self, id=self.gameid(self.munge(longname)))

		if (id, shortname, longname) == (None, None, None):
			return self
		else:
			# Short the object in the cache
			cls.__cache[self.id]        = self
			cls.__cache[self.shortname] = self

			return self

	def __init__(self, *args, **kw):
		pass

	@staticmethod
	def munge(game):
		"""\
		Convert a longname into some sort of suitable short name.
		"""
		return game.replace(' ', '').strip().lower()

	@staticmethod
	def gameid(game):
		"""\
		Get the id of a game from a short name.
		"""
		try:
			return Game.__cache[game].id
		except KeyError:
			pass

		dbconn.use()
		t = Game.table
		try:
			return dbconn.execute(select([t.c.id], t.c.shortname==game)).fetchall()[0][0]
		except (KeyError, IndexError), e:
			raise NoSuch("No such game named %s exists!" % game)

	def ruleset_get(self):
		"""\
		Return the Ruleset (object) this game uses.
		""" 
		try:
			return self.__ruleset
		except AttributeError:
			exec("from tp.server.rules.%s import Ruleset" % self.rulesetname)
			self.__ruleset = Ruleset(self)
			return self.__ruleset

	def ruleset_set(self, value):
		if hasattr(self, 'rulesetname'):
			raise TypeError('A ruleset can only be set once!')
		try:
			exec("from tp.server.rules.%s import Ruleset" % value)
		except ImportError, e:	
			print e
			raise ImportError("This game references a ruleset which doesn't exist anymore! Please reinstall the ruleset.")
		self.rulesetname = value

	ruleset = property(ruleset_get, ruleset_set)

	def __str__(self):
		if hasattr(self, 'id'):
			return "<Game-%i %s (%s) turn-%i>" % (self.id, self.shortname, self.longname, self.turn)
		else:
			return "<Game-(new) %s (%s) turn-%i>" % (self.shortname, self.longname, self.turn)

	def key(self):
		# FIXME: This probably isn't very secure...
		key = hashlib.md5("%s-%s" % (self.longname, self.time))
		return key.hexdigest()
	key = property(key)

	def players(self):
		dbconn.use(self)
		from tp.server.bases.User import User
		return User.amount()
	players = property(players)

	def objects(self):
		dbconn.use(self)
		from tp.server.bases.Object import Object
		return Object.amount()
	objects = property(objects)

	def to_packet(self, sequence):
		from tp.server.server  import servers, servername, serverip
		from tp.server.version import version
		server_ver = "%s.%s.%s" % version[0:3]

		locations = []
		for server in servers.values():
			for port in server.ports:
				locations.append(('tp',       servername, serverip, port))
				locations.append(('tp+http',  servername, serverip, port))
			for port in server.sslports:
				locations.append(('tps',      servername, serverip, port))
				locations.append(('tp+https', servername, serverip, port))

		# Build the optional parameters
		optional = []
		# FIXME: Magic Numbers!
		# Number of players
		optional.append((1, '', self.players))
		# Number of objects
		optional.append((3, '', self.objects))
		# Admin email address
		optional.append((4, self.admin, -1))
		# Comment
		optional.append((5, self.comment, -1))
		# Turn
		#optional.append((6, '', self.turn))

		return objects.Game(sequence, self.longname, '', #self.key, 
								["0.3", "0.3+"], 
								server_ver, "tpserver-py", 
								self.ruleset.name, self.ruleset.version,
								locations, optional)

	def to_discover(self):
		g = DiscoverGame(self.longname)

		from tp.server.server  import servers, servername, serverip
		from tp.server.version import version

		required = {}
		required['key']     = self.key
		required['tp']      = "0.3,0.3+"
		required['server']  = "%s.%s.%s" % version[0:3]
		required['sertype'] = "tpserver-py"
		required['rule']    = self.ruleset.name
		required['rulever'] = self.ruleset.version
		g.updateRequired(required)

		for server in servers.values():
			for port in server.ports:
				g.addLocation('tp',       (servername, serverip, port))
				g.addLocation('tp+http',  (servername, serverip, port))
			for port in server.sslports:
				g.addLocation('tps',      (servername, serverip, port))
				g.addLocation('tp+https', (servername, serverip, port))

		# Build the optional parameters
		optional = {}
		# FIXME: Magic Numbers!
		# Number of players
		optional['plys']  = self.players
		# Number of objects
		optional['objs']  = self.objects
		# Admin email address
		optional['admin'] = self.admin
		# Comment
		optional['cmt']   = self.comment
		# Turn
		#optional.append((6, '', self.turn))

		g.updateOptional(optional)
		return g

