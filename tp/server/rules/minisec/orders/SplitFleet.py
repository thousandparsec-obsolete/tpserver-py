
import copy
import netlib

from sbases.Object import Object
from sbases.Order import Order
from sbases.Message import Message

from sobjects.Fleet import Fleet

class SplitFleet(Order):
	"""\
Split some ships into a new fleet.
"""

	attributes = {\
		'call': Order.Attribute("call", "", 'protected', type=netlib.objects.Constants.ARG_STRING, 
				desc="What to call the new fleet."),
		'ships': Order.Attribute("ships", {}, 'protected', type=netlib.objects.Constants.ARG_LIST, 
				desc="Ships to move into new fleet.")
	}
	
	def do(self):
		# We need the original fleet
		fleet1 = Object(self.oid)
		
		# Create the new fleet
		fleet2 = copy.deepcopy(fleet1)
		fleet2.name = self.call

		# Add the ships to the new fleet
		for type, number in self.ships:
			if fleet1.ships[type] - number > 0:
				fleet1.ships[type] -= number
				fleet2.ships[type] = number
			else:
				fleet2.ships[type] = fleet1.ships[type]
				fleet1.ships[type] = 0
		self.remove()

	def simulate(self):
		pass

	def turns(self, turns=0):
		return self.turns+1

	def resources(self):
		return []

	def fn_call(self, value=None):
		if value == None:
			return [0, self.call]
		else:
			self.call = value[0]

	def fn_ships(self, value=None):
		max = self.object.ships
		if value == None:
			returns = []
			for type, number in max.items():
				returns.append((type, Fleet.ship_types[type], number))
			print returns, self.ships.items()
			return returns, self.ships.items()
		else:
			ships = {}

			try:
				for type, number in value[1]:
					if not type in Fleet.ships.keys():
						raise ValueError("Invalid type selected")
					if number > max[type]:
						raise ValueError("Number to big")
					ships[type] = number
			except:
				pass

			self.ships = ships

SplitFleet.typeno = 3
Order.types[SplitFleet.typeno] = SplitFleet
