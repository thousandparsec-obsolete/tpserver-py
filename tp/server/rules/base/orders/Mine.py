
from tp import netlib

from tp.server.bases.Order import Order

class Mine(Order):
	"""\
Turn a mineable resource into a surface resource.
"""
	typeno = 6

	attributes = {\
		'resource': Order.Attribute("resource", 0, 'public', type=netlib.objects.constants.ARG_RANGE, 
				desc="Which resource to dig up."),
		'amount': Order.Attribute("amount", 0, 'public', type=netlib.objects.constants.ARG_RANGE, 
				desc="How much to dig up.")
	}
	
	def do(self):
		pass

	def turns(self, turns=0):
		return turns

	def resources(self):
		return []

