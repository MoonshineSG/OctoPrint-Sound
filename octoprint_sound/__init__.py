# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import logging
import logging.handlers

import os
from datetime import datetime, time
from threading import Thread
import pygame
from Queue import Queue


class SoundThread (Thread):

	def __init__(self, logger, song, volume, callback = None):
		Thread.__init__(self)
		self._logger = logger
		self._song = song
		self._volume = volume
		self._callback = callback

	def run(self):
		if not pygame.mixer.get_init():
			self._logger.debug("pygame.mixer mixer initialized.")
			pygame.mixer.init(48000, -16, 1, 1024)
		self._logger.debug("pygame.mixer %s (volume %s)"%(self._song, self._volume) )
		pygame.mixer.music.set_volume(float(self._volume) / 100)
		pygame.mixer.music.load(self._song)
		pygame.mixer.music.play()
		while pygame.mixer.music.get_busy():
			continue
		pygame.mixer.quit()
		self._logger.debug("pygame.mixer off")
		if self._callback:
			self._callback()

class SoundPlugin(octoprint.plugin.SettingsPlugin):
	
	def get_settings_defaults(self):
		return dict(
			night_start = 20,
			night_end = 8,
			night_volume = 20,
			nomute = []
			)
					
	def initialize(self):
		#self._logger.setLevel(logging.DEBUG)
		self.night_volume = self._settings.get_int(["night_volume"])
		self.night_start = self._settings.get_int(["night_start"])
		self.night_end = self._settings.get_int(["night_end"])		
		self.nomute = map(( lambda x: '@' + x), self._settings.get(["nomute"]))
		self._logger.info("Initialized with {0}% from {1} to {2}...".format(self.night_volume, self.night_start, self.night_end))
		self._logger.info("Sounds not muted: {0}".format(self.nomute))
		self.default_sound = os.path.join(self._basefolder,"default.mp3")
		self.q = Queue()
		self.playing = False
		
	def play_next(self):
		if self.q.empty():
			self.playing = False
		else:
			self.q.get().start()
			
	def play_pygame(self, song, volume):
		st = SoundThread(self._logger, song, volume, self.play_next)
		if self.playing:
			self.q.put(st) 
		else:
			self.playing = True
			st.start()	
		
	def play(self, song, volume = 100):
		mp3 = os.path.join(self.get_plugin_data_folder() ,"%s.mp3"%song)
		if not os.path.isfile(mp3):
			mp3 = os.path.join(self._basefolder, "default", "%s.mp3"%song)
		if not os.path.isfile(mp3):
			mp3 = self.default_sound
		self.play_pygame(mp3, volume)
		return os.path.basename(mp3)

	def remove_prefix(self, text, prefix):
		if text.startswith(prefix):
			return text[len(prefix):].strip()
		return "@alert"
		
	def in_between(self, now, start, end):
		if start <= end:
			return start <= now < end
		else: 
			return start <= now or now < end

	def is_mute(self):
		return os.path.isfile( "/home/pi/.octoprint/data/switch/mute" )
		
	def is_night(self):
		return True if self.in_between(datetime.now().time(), time(self.night_start), time(self.night_end)) else False

	def suppress_m300(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
		if gcode and gcode == "M300":
			param = self.remove_prefix(cmd, "M300")
			if param and param[0] == "@":
				if self.is_mute() and param not in self.nomute:
					comm_instance._log("Mute. (%s)" % param)
					return None,
				sound = param[1:]
				volume = 100
				if self.is_night():
					volume = self.night_volume
					
				if param in self.nomute:
					volume = self.night_volume
					
				comm_instance._log("Playing '%s'... (%s)" % (self.play(sound, volume), param))
				return None,

	def get_version(self):
		return self._plugin_version

	def get_update_information(self):
		return dict(
			octoprint_sound=dict(
				displayName="Sound",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="MoonshineSG",
				repo="OctoPrint-Sound",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/MoonshineSG/OctoPrint-Sound/archive/{target_version}.zip"
			)
		)

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = SoundPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.comm.protocol.gcode.sending": __plugin_implementation__.suppress_m300,
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}
	
	
