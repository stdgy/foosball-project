from datetime import datetime

class Game:
	"""
	Programmatically defines a game."""

	def set_start_time(self, start_time=None):
		if start_time is not None and type(start_time) is str:
			self.start_time = datetime.fromtimestamp(float(start_time))

	def set_end_time(self, end_time=None):
		if end_time is not None and type(end_time) is str:
			self.end_time = datetime.fromtimestamp(float(end_time))

	def add_team(self, team=None):
		if team is not None:
			self.teams.append(team)

	def get_json(self):
		game = {}
		game['id'] = self.id 
		if self.start_time is not None:
			game['start_time'] = str(self.start_time) 

		if self.end_time is not None:
			game['end_time'] = str(self.end_time)
			
		game['teams'] = self.teams 

		return game

	def __init__(self, id=None, start_time=None, end_time=None):
		self.id = id

		if start_time is not None and type(start_time) is str:
			self.start_time = datetime.fromtimestamp(float(start_time))

		if end_time is not None and type(end_time) is str:
			self.end_time = datetime.fromtimestamp(float(end_time))

		# Setup teams
		self.teams = []