# Generating videos synchronised to pre-existing audio tracks

`ly2video` can synchronize the video of the scrolling music notation
with a previously recorded audio track of the same music, such as a
live performance, even when the audio
uses [*tempo rubato*](https://en.wikipedia.org/wiki/Tempo_rubato) or
is not precisely metronomic.  This is accomplished
using [*beatmap* files](beatmap-files.md).  If such a file is provided
to `ly2video` via the `--beatmap` (or `-b`) command-line option,
whilst generating the video it will adjust the speed of the scrolling
to match the tempo variations described by the beatmap file.  However
the generated video will still use a MIDI-rendered audio track, so as
a final step you will need to use a video editor if you want to
replace this audio track with the original one on which the beatmap
file was based.

N.B. Currently it is assumed that the beatmap file covers every single
beat, and so the only fields which are actually used for
synchronization are the tempo and beat value fields.  The others are
only used to prettify the output.  In the future it may be made more
intelligent, so that beats could be skipped if they do not involve a
tempo change.

## Implementation details

How it actually works under the hood:

- `ly2video` uses LilyPond to generate a MIDI rendition of the audio
  alongside the graphical rendering of the score.
- If a beatmap is specified, `ly2video`
  uses [`midi-rubato`](../scripts/midi-rubato) to insert MIDI tempo change
  events into the generated `.midi` file.
- `ly2video` generates a scrolling video which is synchronised with
  the MIDI events from the `.midi` file.
