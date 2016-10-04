Octoprint plugin to replace printer sounds `M300 S2093 P120` with mp3 sound played by RPi

1. add mp3 files to `.octoprint/data/sound/` to overwrite or to add new keywords
2. add settings to `config.yaml`

```
plugins:
  sound:
    night_start: 20
    night_end: 6
    night_volume: 60
    nomute:
    - change
    - offset
    - save_offset
    - baby_up
    - baby_down
	
```
- `nomute` contains a list of sounds played even if the plugin is muted (via the ["switch" plugin](https://github.com/MoonshineSG/OctoPrint-Switch))

3. call `M300 @keyword` (for example) in your GCODE... 
Any keyword is allowed, and it would be matched against a list of MP3 files in the `.octoprint/data/sound/` or plugin folder (e.g. `keyword.mp3`). 
If none is found, the default, `.octoprint/plugins/sound/default.mp3`, would be played.
 
The sound will be played at reduced volume `night_volume`% at noght (between `night_start` and `night_end`)

It can be muted via the ["switch" plugin](https://github.com/MoonshineSG/OctoPrint-Switch)