class Team:
	"""Programmatically defines a team."""

	def set_name(self, name):
		self.name = name

	def add_player(self, player):
		self.players.append(player)

	def __init__(self, id, name=None):
		self.id = id
		self.players = []

		if name is not None:
			self.name = name