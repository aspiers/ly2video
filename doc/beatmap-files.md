# Beatmap files

A beatmap file is a text file which describes variations in playback
tempo.

## Usage

Beatmap files can be used by `ly2video` to [synchronise generated video
with a pre-existing audio track](how-to-audio-sync.md).

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

- If your beats do not correspond to quarter notes (crotchets) then
  manually adjust the beat value fields (see below).

## File format

The format of the file is simple; it's a list of beats, one per line,
where each line is whitespace delimited with the following fields:

- label,     e.g. `C5` for the 5th measure of section C
- section,   e.g. `3` for section C
- measure,   e.g. `5` for the 5th measure of the section
- beat,      e.g. `2` for the 2nd beat of the measure
- timestamp, e.g. `0:02:56.280` for just under 3 minutes
- beat value numerator (see Beat value below)
- beat value denominator (see Beat value below)
- tempo,     e.g. `60` for 60 beats per minute

The last tempo field is omitted on the final beat, since without
a following beat, there is no way to determine the tempo.

### Beat value

The beat value is obtained by dividing the numerator value by the
denominator value, and represents the ratio between the length of a
beat and quarter-notes (crotchets).  So if beats are quarter-notes
then the beat value numerator and denominator would typically both be
"1", although it doesn't matter as long as they are both the same
integer.

In compound time signatures such as 6/8, 9/8, 12/18 etc., then a beat
typically represents a dotted quarter-note (crotchet), so the
numerator would be "3" and the denominator "2", representing a beat
value of 1.5 times a quarter-note.  In 4/2 time signature the beat
value would typically be 2 representing a half-note (minim), in which
case the numerator could be "2" and the denominator "1" (or "4" and
"2" respectively).  In 3/8, the beat would typically be an eighth-note
(quaver) which is half the length of a quarter-note, so they would be
"1" and "2" respectively.

This beat value is required because MIDI measures deltas between
events in fractions of a quarter note, not fractions of a beat.
