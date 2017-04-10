# Generating videos synchronised to pre-existing audio tracks

`ly2video` can synchronize the video of the scrolling music notation
with a previously recorded audio track of the same music, such as a
live performance, even when the audio
uses [*tempo rubato*](https://en.wikipedia.org/wiki/Tempo_rubato) or
is not precisely metronomic.  This is accomplished using *beatmap*
files.

## Beatmap files

A beatmap file is a text file which describes variations in playback
tempo.  The format of the file is simple; it's a list of beats, one
per line, where each line is whitespace delimited with the following
fields:

- label,     e.g. `C5` for the 5th measure of section C
- section,   e.g. `3` for section C
- measure,   e.g. `5` for the 5th measure of the section
- beat,      e.g. `2` for the 2nd beat of the measure
- timestamp, e.g. `0:02:56.280` for just under 3 minutes
- tempo,     e.g. `60` for 60 beats per minute

If such a file is provided to `ly2video` via the `--beatmap` (or `-b`)
command-line option, whilst generating the video it will adjust the
speed of the scrolling to match the tempo variations described by the
beatmap file.

N.B. Currently it is assumed that the file covers every single beat,
and so the only field which is actually used for synchronization is
the tempo field.  The others are only used to prettify the output.
In the future it may be made more intelligent, so that beats could be
skipped if they do not involve a tempo change.

## How to generate beatmap files

As the file format is simple, it is possible to write them manually;
however this is quite tedious.  A quicker option is to import the
audio track into a software program called
[Transcribe!](https://www.seventhstring.com/xscribe/overview.html)
(unfortunately not free, although there is a free 30-day
evaluation period):

- Import the audio file
- Start playback, and tap the `b` key on every beat.
- Save the resulting `.xsc` file
- Generate a beatmap file using [`xsc2beatmap`](../xsc2beatmap), e.g.:

      xsc2beatmap foo.xsc > foo.beatmap

## Implementation details

How it actually works under the hood:

- `ly2video` uses LilyPond to generate a MIDI rendition of the audio
  alongside the graphical rendering of the score.
- If a beatmap is specified, `ly2video`
  uses [`midi-rubato`](../midi-rubato) to insert MIDI tempo change
  events into the generated `.midi` file.
- `ly2video` generates a scrolling video which is synchronised with
  the MIDI events from the `.midi` file.
