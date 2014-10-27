class Player:
	"""Programmitcally define a player."""

	def set_position(self, position):
		self.position = position
	
	def __init__(self, id, position=None):
		self.id = id

		if position is not None:
			self.position = position