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

__plugin_name__ = "Sound Plugin"
__plugin_version__ = "0.0.3"
__plugin_description__ = "Play a sound localy when receiving a '@' code instead of the usual frequency/duration and suppress sending M300 to printer"


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
			night_volume = 20)
					
	def initialize(self):
		#self._logger.setLevel(logging.DEBUG)
		self.night_volume = self._settings.get_int(["night_volume"])
		self.night_start = self._settings.get_int(["night_start"])
		self.night_end = self._settings.get_int(["night_end"])
		self._logger.info("Initialized with {0}% from {1} to {2}...".format(self.night_volume, self.night_start, self.night_end))
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
		mp3 = os.path.join(self.get_plugin_data_folder(), "%s.mp3"%song)
		if not os.path.isfile(mp3):
			mp3 = os.path.join(self._basefolder, "%s.mp3"%song)
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
				if self.is_mute() and param not in ["@change", "@offset", "@save_offset", "@baby_up", "@baby_down"]:
					comm_instance._log("Mute. (%s)" % param)
					return None,
				sound = param[1:]
				volume = 100
				if self.is_night():
					volume = self.night_volume
				comm_instance._log("Playing '%s'... (%s)" % (self.play(sound, volume), param))
				return None,


def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = SoundPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.comm.protocol.gcode.sending": __plugin_implementation__.suppress_m300
	}
	
