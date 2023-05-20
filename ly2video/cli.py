#!/usr/bin/env python3
# coding=utf-8

# ly2video - generate performances video from LilyPond source files
# Copyright (C) 2012 Jiri "FireTight" Szabo
# Copyright (C) 2012 Adam Spiers
# Copyright (C) 2014 Emmanuel Leguy
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# For more information about this program, please visit
# <https://github.com/aspiers/ly2video/>.

# Used to determine --version output for released versions, not
# when running from a git check-out:

import itertools
import os
import pipes
import re
import shutil
import subprocess
import sys
import traceback

from collections import namedtuple
from distutils.version import StrictVersion
from argparse import ArgumentParser
from struct import pack
from fractions import Fraction
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
import mido
from ly2video.utils import *
from ly2video.video import *

from pprint import pprint, pformat

from pexpect.popen_spawn import PopenSpawn
from pexpect import EOF

VERSION = '0.4.2'

GLOBAL_STAFF_SIZE = 20

C_MAJOR_SCALE_STEPS = [
    # Maps notes of the C major scale into semi-tones above C.
    # This is needed to map the pitch of ly2video.ly.tools.Pitch notes
    # into MIDI pitch values within a given octave.
    0,   # c
    2,   # d
    4,   # e
    5,   # f
    7,   # g
    9,   # a
    11,  # b
]

NOTE_NAMES = [
    "C", "C#/Db", "D", "D#/Eb", "E", "F", "F#/Gb",
    "G", "G#/Ab", "A", "A#/Bb", "B"
]

NOTE_ALTERATIONS = [
    'eses', 'eseh', 'es', 'eh', '', 'ih', 'is', 'isih', 'isis'
]


class LySrcLocation(object):
    """
    Represents a location within a .ly file.  Note that line numbers
    count from 0, but are displayed counting from 1, since that
    matches what editors such as emacs and vim show.

    Addtional pitch info is stored.

    - octave: int, 0 is c', 1 is c'', -1 is c, and so on
    - notename: int, 0,1,2,3,4,5,6 for c,d,e,f,g,a,b
    - alteration: Fraction, 0: no alteration, 1/2: SHARP, -1/2: FLAT, and so on

    """
    __slots__ = ['filename', 'lineNum', 'columnNum', 'octave', 'notename', 'alteration']

    def __init__(self, filename, lineNum, columnNum, octave, notename, alteration):
        self.filename  = filename
        self.lineNum   = lineNum
        self.columnNum = columnNum
        self.octave  = octave
        self.notename  = notename
        self.alteration  = alteration

    def __str__(self):
        return "%s:%d:%d" % (self.filename, self.lineNum + 1, self.columnNum)

    def coords(self):
        return (self.lineNum, self.columnNum)

    def getAbsolutePitch(self):
        accidentalSemitoneSteps = 2 * self.alteration

        pitch = (self.octave + 5) * 12 + \
            C_MAJOR_SCALE_STEPS[self.notename] + \
            accidentalSemitoneSteps

        token = noteToken(self.octave, self.notename, self.alteration)

        return pitch, token


def preprocessLyFile(lyFile, lilypondVersion):
    version = getLyVersion(lyFile)
    progress("Version in %s: %s" %
             (lyFile, version if version else "unspecified"))
    if version and version != lilypondVersion:
        progress("Will convert to: %s" % lilypondVersion)
        newLyFile = tmpPath('converted.ly')
        if os.system("convert-ly '%s' >> '%s'" % (lyFile, newLyFile)) == 0:
            return newLyFile
        else:
            warn("Convert of input file has failed. " +
                 "This could cause some problems.")

    newLyFile = tmpPath('unconverted.ly')

    with open(newLyFile, 'w', encoding='utf-8') as new:
        with open(lyFile, encoding='utf-8') as old:
            new.write(''.join(old.readlines()))

    debug("new ly file is " + newLyFile)
    output_divider_line()

    return newLyFile


def runLilyPond(lyFileName, dpi, *args):
    progress("Generating PNG and MIDI files ...")
    cmd = [
        "lilypond",
        "--png",
        "-I", runDir,
        "-dmidi-extension=midi",  # default on Windows is .mid
        "-dresolution=%d" % dpi
    ] + list(args) + [lyFileName]
    output_divider_line()
    os.chdir(tmpPath())
    # the "*** Warning..." part may be inserted INSIDE UTF-8 character sequence,
    # so we add a preprocessor to remove it before decode the output to text string
    output = safeRun(
        cmd, exitcode=9,
        preprocessor=lambda s: re.sub(
            b"\n\*\*\* Warning: GenericResourceDir doesn't point to a valid resource directory\.\s*\n"
            b"\s*the .+ option can be used to set this.\n\n",
            b"", s)
    )
    output_divider_line()
    progress("Generated PNG and MIDI files")
    return output


def getLeftmostGrobsByMoment(output, dpi, leftPaperMarginPx):
    """
    Parse the ly2video data output by LilyPond, and return a
    sorted list of (moment, xcoord) tuples where each X co-ordinate
    corresponds to the left-most grob at that moment.
    """

    lines = output.split('\n')

    leftmostGrobs = {}
    currentLySrcFile = None

    prefix = '^ly2video:\\s+'
    for line in lines:
        if not line.startswith('ly2video: '):
            continue

        # Allow ly2video to embed comments in output for debugging
        # purposes.
        if re.match(prefix + '#', line):
            continue

        m = re.match(prefix +
                     # X-extents
                     '\\(\\s*(-?\\d+\\.\\d+),\\s*(-?\\d+\\.\\d+)\\s*\\)'
                     # pitch (octave/notename/alteration)
                     '\\s+pitch\\s+(-?\\d+):(\\d+):(-?\\d+(?:/\\d+)?)'
                     # delimiter
                     '\\s+@\\s+'
                     # moment
                     '(-?\\d+\\.\\d+)'
                     # delimiter
                     '\\s+from\\s+'
                     # file:line:char
                     '(.+): *(\d+):(\d+)'
                     '\\r?$', line)
        if not m:
            bug("Failed to parse ly2video line:\n%s" % line)
        left, right, octave, notename, alteration, moment, filename, line, column = m.groups()

        if currentLySrcFile is None or currentLySrcFile != filename:
            currentLySrcFile = filename
            debug("Current .ly source file: %s" % currentLySrcFile)

        left   = float(left)
        right  = float(right)
        octave = int(octave)
        notename = int(notename)
        alteration = Fraction(alteration)
        centre = (left + right) / 2
        moment = float(moment)
        line   = int(line) - 1  # LilyPond counts from 1
        column = int(column)
        x = int(round(staffSpacesToPixels(centre, dpi))) + leftPaperMarginPx

        if moment not in leftmostGrobs or x < leftmostGrobs[moment][0]:
            location = LySrcLocation(
                filename, line, column, octave, notename, alteration)
            leftmostGrobs[moment] = [x, location]
            debug("leftmost grob (%2d, %s) for moment %9f is now x =%5d @ %3d:%d"
                  % (location.getAbsolutePitch()[0], location.getAbsolutePitch()[1],
                     moment, x, line + 1, column))

    groblist = [tuple([moment] + leftmostGrobs[moment])
                for moment in sorted(leftmostGrobs.keys())]

    if not groblist:
        bug("Didn't find any notes; something must have gone wrong "
            "with the use of dump-spacetime-info.")

    return groblist


def getMeasuresIndices(output, dpi, leftPaperMarginPx):
    ret = []
    ret.append(leftPaperMarginPx)
    lines = output.split('\n')

    for line in lines:
        if not line.startswith('ly2videoBar: '):
            continue

        m = re.match('^ly2videoBar:\\s+'
                     # X-extents
                     '\\(\\s*(-?\\d+\\.\\d+),\\s*(-?\\d+\\.\\d+)\\s*\\)'
                     # delimiter
                     '\\s+@\\s+'
                     # moment
                     '(-?\\d+\\.\\d+)'
                     '$', line)
        if not m:
            bug("Failed to parse ly2videoBar line:\n%s" % line)
        left, right, moment = m.groups()

        left   = float(left)
        right  = float(right)
        centre = (left + right) / 2
        moment = float(moment)
        x = int(round(staffSpacesToPixels(centre, dpi))) + leftPaperMarginPx

        if x not in ret:
            ret.append(x)

    ret.sort()
    return ret


def findStaffLines(imageFile, lineLength):
    """
    Takes a image and returns y co-ordinates of staff lines in pixels.

    Params:
      - imageFile:    filename of image containing staff lines
      - lineLength:   required length of line for acceptance as staff line

    Returns a list of y co-ordinates of staff lines.
    """
    progress("Looking for staff lines in %s" % imageFile)
    image = Image.open(imageFile)

    x, ys = findStaffLinesInImage(image, lineLength)
    return ys


def generateTitleFrame(titleText, width, height, ttfFile):
    """
    Generates frame with name of song and its author.

    Params:
    - titleText:    collection of name of song and its author
    - width:        pixel width of frames (and video)
    - height:       pixel height of frames (and video)
    - ttfFile:      path to TTF file to use for title text
    """

    # create image of title screen
    titleScreen = Image.new("RGB", (width, height), (255, 255, 255))
    # it will draw text on titleScreen
    drawer = ImageDraw.Draw(titleScreen)

    # font for song's name, args - font type, size
    nameFont = ImageFont.truetype(ttfFile, int(height / 15))
    # font for author
    authorFont = ImageFont.truetype(ttfFile, int(height / 25))

    # args - position of left upper corner of rectangle (around text),
    # text, font and color (black)
    drawer.text(((width - nameFont.getsize(titleText.name)[0]) / 2,
                 (height - nameFont.getsize(titleText.name)[1]) / 2 -
                 height / 25),
                titleText.name, font=nameFont, fill=(0, 0, 0))
    # same thing
    drawer.text(((width - authorFont.getsize(titleText.author)[0]) / 2,
                 (height / 2) + height / 25),
                titleText.author, font=authorFont, fill=(0, 0, 0))

    return titleScreen


def staffSpacesToPixels(ss, dpi):
    staffSpacePoints = GLOBAL_STAFF_SIZE / 4
    points = ss * staffSpacePoints
    pointsPerInch = 72.27  # Donald Knuth's TeX points
    inches = points / pointsPerInch
    return inches * dpi


def mmToPixel(mm, dpi):
    pixelsPerMm = dpi / 25.4
    return mm * pixelsPerMm


def pixelsToMm(pixels, dpi):
    inchesPerPixel = 1.0 / dpi
    mmPerPixel = inchesPerPixel * 25.4
    return pixels * mmPerPixel


def writePaperHeader(fFile, width, height, dpi, numOfLines, lilypondVersion):
    """
    Writes own paper block into given file.

    Params:
    - fFile:        given opened file
    - width:        pixel width of final video
    - height:       pixel height of final video
    - dpi:          resolution in DPI
    - numOfLines:   number of staff lines
    - lilypondVersion: version of LilyPond
    """
    fFile.write("\\paper {\n")
    fFile.write("   page-breaking = #ly:one-line-breaking\n")

    # make sure we have enough margin to be cropped
    topPixels    = height / 2
    bottomPixels = height / 2
    leftPixels   = 200
    rightPixels  = 200

    topMm    = round(pixelsToMm(topPixels,    dpi))
    bottomMm = round(pixelsToMm(bottomPixels, dpi))
    leftMm   = round(pixelsToMm(leftPixels,   dpi))
    rightMm  = round(pixelsToMm(rightPixels,  dpi))

    fFile.write("   top-margin    = %d\\mm  %% %d pixels\n" % (topMm, topPixels))
    fFile.write("   bottom-margin = %d\\mm  %% %d pixels\n" % (bottomMm, bottomPixels))
    fFile.write("   left-margin   = %d\\mm  %% %d pixels\n" % (leftMm, leftPixels))
    fFile.write("   right-margin  = %d\\mm  %% %d pixels\n" % (rightMm, rightPixels))

    fFile.write("   oddFooterMarkup = \\markup \\null\n")
    fFile.write("   evenFooterMarkup = \\markup \\null\n")
    fFile.write("}\n")

    fFile.write("#(set-global-staff-size %d)\n" % GLOBAL_STAFF_SIZE)

    progress("Margins in mm: left=%d top=%d right=%d bottom=%d"
             % (leftMm, topMm, rightMm, bottomMm))
    progress("Margins in px: left=%d top=%d right=%d bottom=%d"
             % (leftPixels, topPixels, rightPixels, bottomPixels))

    return leftPixels


def getTemposList(midiFile):
    """
    Returns a list of tempo changes in midiFile.  Each tempo change is
    represented as a (tick, tempoValue) tuple.
    """
    midiHeader = midiFile.tracks[0]

    temposList = []
    for event in midiHeader:
        # if it's SetTempoEvent
        if event.type == 'set_tempo':
            bpm = mido.tempo2bpm(event.tempo)
            debug("tick %6d: tempo change to %.3f bpm" %
                  (event.time, bpm))
            temposList.append((event.time, bpm))

    return temposList


def getNotesInTicks(midiFile):
    """
    Returns a tuple of the following items:
      - a dict mapping ticks to a list of NoteOn events in that tick
      - a dict mapping NoteOn events to their corresponding pitch bends
    """
    notesInTicks = {}
    pitchBends   = {}

    # for every channel in MIDI (except the first one)
    for i in range(1, len(midiFile.tracks)):
        debug("Reading MIDI track %d" % i)
        track = midiFile.tracks[i]
        pendingPitchBend = None
        for event in track:
            tick = event.time
            eventClass = event.type

            if pendingPitchBend:
                if pendingPitchBend.tick != tick:
                    bug("Found orphaned pitch bend in tick %d" %
                        pendingPitchBend.tick)
                if not eventClass == 'note_on':
                    bug("Pitch bend was not followed by NoteOn in tick %d" %
                        tick)
                if event.velocity == 0:
                    bug("Pitch bend was followed by NoteOff")

            if eventClass == 'pitchwheel':
                bend = event.pitch
                debug("    tick %6d: %s(%d)" %
                      (tick, eventClass, bend))
                if bend != 0:
                    pendingPitchBend = event
                continue
            elif eventClass == 'note_on':
                if event.velocity == 0:
                    # velocity is zero (that's basically "NoteOffEvent")
                    debug("    tick %6d:     NoteOffEvent(%d)" %
                          (tick, event.note))
                    continue
                else:
                    if pendingPitchBend:
                        pitchBends[event] = pendingPitchBend
                        pendingPitchBend = None
                    debug("    tick %6d: %s(%d)" %
                          (tick, eventClass, event.note))
            else:
                debug("    tick %6d:     %s - skipping" %
                      (tick, eventClass))
                continue

            # add it into notesInTicks
            if tick not in notesInTicks:
                notesInTicks[tick] = []
            notesInTicks[tick].append(event)

    return notesInTicks, pitchBends

def make_time_abs(midiFile):
    """
    Changes the time of all messages to absolute time in ticks
    """
    for track in midiFile.tracks:
        time = 0
        for event in track:
            time += event.time
            event.time = time

def getMidiEvents(midiFileName):
    """
    Extracts useful information from a given MIDI file and returns it.

    Params:
      - midiFileName: name of MIDI file (string)

    Returns a tuple of the following items:
      - midiResolution: the resolution of the MIDI file
      - temposList: as returned by getTemposList()
      - midiTicks: a sorted list of which ticks contain NoteOn events.
                   The last tick corresponds to the earliest
                   EndOfTrackEvent found across all MIDI channels.
      - notesInTicks: as returned by getNotesInTicks()
      - pitchBends: as returned by getNotesInTicks()
    """

    # open MIDI with external library
    midiFile = mido.MidiFile(midiFileName)
    # and make ticks absolute
    make_time_abs(midiFile)

    # get MIDI resolution and header
    midiResolution = midiFile.ticks_per_beat
    progress("MIDI resolution (ticks per beat) is %d" % midiResolution)

    temposList = getTemposList(midiFile)

    output_divider_line()

    notesInTicks, pitchBends = getNotesInTicks(midiFile)

    # get all ticks with notes and sorts it
    midiTicks = sorted(notesInTicks.keys())

    # find the tick corresponding to the earliest EndOfTrackEvent
    # across all MIDI channels, and append it
    endOfTrack = -1
    for eventsList in midiFile.tracks[1:]:
        if eventsList[-1].type == 'end_of_track':
            if endOfTrack < eventsList[-1].time:
                endOfTrack = eventsList[-1].time
    midiTicks.append(endOfTrack)

    progress("MIDI: Parsing MIDI file has ended.")

    return (midiResolution, temposList, midiTicks, notesInTicks, pitchBends)


def pitchToken(pitch):
    pitch = int(pitch)
    token = NOTE_NAMES[pitch % 12].lower()

    if pitch < 4 * 12:
        token +=  "," * (4 - pitch // 12)
    else:
        token +=  "'" * (pitch // 12 - 4)

    return token


def noteToken(octave, notename, alteration):
    token = NOTE_NAMES[C_MAJOR_SCALE_STEPS[notename]].lower()
    token += NOTE_ALTERATIONS[4 + int(alteration * 4)]

    if octave < -1:
        token +=  "," * (-octave - 1)
    else:
        token +=  "'" * (octave + 1)

    return token


def getMidiPitches(events, pitchBends):
    """
    Build dicts tracking which pitches (modulo the octave)
    are present in the current tick and index.
    """
    midiPitches = {}
    for event in events:
        pitch = event.note
        if pitch in pitchBends:
            pitch += float(pitchBends[pitch].pitch) / 4096 # TODO:
        midiPitches[pitch] = event
    return midiPitches


def getNoteIndices(leftmostGrobsByMoment,
                   midiResolution, midiTicks, notesInTicks, pitchBends):
    """
    Build a list of note indices which align with the ticks in
    midiTicks, by aligning the moments in the space-time data from
    LilyPond with the MIDI ticks.  As a side-effect, any MIDI ticks
    which do not match notes in these indices are removed from
    midiTicks.

    If the (leftmost) grob at a given moment is found to have no
    corresponding MIDI event (e.g. when the grob is on the right-hand
    side of a tie), it is skipped.

    If none of the MIDI events at a given moment are found to have a
    corresponding grob (e.g. when notes are hidden via \hideNotes, or
    generated via a ChordName), they are skipped and the containing
    tick is removed from midiTicks.

    Parameters:
      - leftmostGrobsByMoment:
          A sorted list mapping each moment to a (x, line, column) tuple
          for the left-most grob at that moment
      - midiResolution
      - midiTicks:
          A sorted list of which ticks contain NoteOn events.  The
          last tick corresponds to the earliest EndOfTrackEvent found
          across all MIDI channels.
      - notesInTicks:           as returned by getNotesInTicks()
      - pitchBends:             as returned by getNotesInTicks()

    Returns:
      - alignedNoteIndices:
          a sorted list containing all the
          indices aligned in order with the MIDI ticks

    Side-effect:
      - midiTicks is potentially trimmed down
    """

    # index into list of MIDI ticks
    midiIndex = 0

    originalTickCount = len(midiTicks)
    ticksSkipped  = 0
    lastChord = []

    # final indices of notes
    alignedNoteIndices = []

    # index into list of note indices
    i = 0

    currentLySrcFile = None

    index = None
    while i < len(leftmostGrobsByMoment):
        if midiIndex == len(midiTicks):
            warn("Ran out of MIDI indices after %d. Current index: %d" %
                 (midiIndex, index))
            break

        moment, index, lySrcLocation = leftmostGrobsByMoment[i]
        if currentLySrcFile is None or \
           currentLySrcFile != lySrcLocation.filename:
            currentLySrcFile = lySrcLocation.filename
            debug("Current .ly source file: %s" % currentLySrcFile)

        midiTick = midiTicks[midiIndex]
        grobTick = int(round(moment * midiResolution * 4))

        grobPitchValue, grobPitchToken = lySrcLocation.getAbsolutePitch()
        if grobPitchToken == 'q':
            if len(lastChord) < 2:
                bug("Encountered a 'q' repeated chord token at %s "
                    "but didn't have a last chord saved." % lySrcLocation)
            grobPitchValue = lastChord[0]

        debug("%-3s @ %3d:%3d | grob(time=%3.4f, x=%5d, tick=%5d) | "
              "MIDI(tick=%5d)" %
              (grobPitchToken, lySrcLocation.lineNum + 1,
               lySrcLocation.columnNum,
               moment, index, grobTick, midiTick))

        if midiTick not in notesInTicks:
            # This should mean that we reached the tick corresponding
            # to the final EndOfTrackEvent (see getMidiEvents()).
            midiIndex += 1
            if midiIndex < len(midiTicks):
                bug("No notes in tick %d (%d/%d)" %
                    (midiTick, midiIndex, len(midiTicks)))
            debug("    no notes in final tick %d" % midiTick)
            continue

        events = notesInTicks[midiTick]
        midiPitches = getMidiPitches(events, pitchBends)

        if midiTick < grobTick:
            # No grobs matched this MIDI tick - maybe it was a note
            # hidden by \hideNotes, or notes from a chord.  So let's
            # skip the tick.
            ticksSkipped += 1
            midiTicks.pop(midiIndex)
            msg = "    WARNING: skipping MIDI tick %d since " \
                  "no grob matched; contents:" % midiTick
            for event in events:
                msg += ("\n        pitch %d time %d" %
                        (event.note, event.time))
            progress(msg)
            continue

        i += 1

        if grobTick < midiTick:
            # No MIDI events found for this grob.  This is probably
            # due to a tied note, or a ChordName for which the
            # corresponding chord was excluded from the MIDI output.
            # FIXME: make sure.
            debug("    No MIDI events for this grob; "
                  "probably a tie/ChordName - skipping grob.")
            continue

        # We're looking at the same point in time in the notated
        # music and the MIDI file.

        # FIXME: it would be better to compare the pitch of *every*
        # grob, not just the leftmost one.  This might result in more
        # synchronization failures, but over time that could expose
        # more edge cases which are not correctly handled right now.
        #
        # The pitch matching can also fail here if the grob is a
        # ChordName, since its pitch might be in a different octave to
        # the NoteOn event for the root of the chord.
        if grobPitchValue not in midiPitches:
            debug("    grob's pitch %d (%s) not found in midiPitches; "
                  "probably a tie/ChordName" % (grobPitchValue, pitchToken(grobPitchValue)))
            midiPitches = [str(event.note) for event in events]
            debug("    midiPitches: %s" %
                  " ".join(["%s (%s)" % (pitch, pitchToken(pitch))
                            for pitch in sorted(midiPitches)]))
            if midiIndex == 0:
                # This is the first MIDI event - we can't skip it,
                # because then the audio and video would start in
                # different places.
                progress("    Starting by hovering over the first grob")
            else:
                progress("    Skipping grob and tick")
                ticksSkipped += 1
                midiTicks.pop(midiIndex)
                continue

        midiIndex += 1
        alignedNoteIndices.append(index)

        if len(midiPitches) > 1:
            # technically it would be more correct to save the grob
            # pitches not MIDI pitches,
            lastChord = midiPitches
        else:
            lastChord = []

    if midiIndex < len(midiTicks) - 1:
        # Could happen if last note is a dangling tie?
        warn("ran out of notes at MIDI tick %d (%d/%d ticks)" %
             (midiTicks[midiIndex], midiIndex + 1, len(midiTicks)))

    progress("sync points found: %5d\n"
             "             from: %5d original indices\n"
             "              and: %5d original ticks\n"
             "   last tick used: %5d\n"
             "    ticks skipped: %5d"   %
             (len(alignedNoteIndices),
              len(leftmostGrobsByMoment),
              originalTickCount,
              midiIndex, ticksSkipped))

    if len(alignedNoteIndices) < 2:
        bug("Not enough synchronization points found!  Aborting.")

    return alignedNoteIndices


def genWavFile(timidity, midiPath):
    """
    Call TiMidity++ to convert MIDI to .wav.
    It has a weird problem where it converts any '.' into '_'
    in the input path, so we run it on the file's relative path
    not the absolute path.
    """
    progress("Running TiMidity++ on %s to generate .wav audio ..." % midiPath)
    dirname, midiFile = os.path.split(midiPath)
    os.chdir(dirname)
    cmd = [timidity, midiFile, "-Ow"]
    progress(safeRun(cmd, exitcode=11))
    wavExpected = midiPath.replace('.midi', '.wav')
    if not os.path.exists(wavExpected):
        bug("TiMidity++ failed to generate %s" % wavExpected)
    return wavExpected


def generateSilence(name, length):
    """
    Generates silent audio for the title screen.

    author: Mister Muffin,
    http://blog.mister-muffin.de/2011/06/04/generate-silent-wav/

    Params:
    - length: length of that silence
    """

    #
    channels = 2    # number of channels
    bps = 16        # bits per sample
    sample = 44100  # sample rate
    ExtraParamSize = 0
    Subchunk1Size = 16 + 2 + ExtraParamSize
    Subchunk2Size = int(length * sample * channels * bps / 8)
    ChunkSize = 4 + (8 + Subchunk1Size) + (8 + Subchunk2Size)

    outdir = tmpPath("silence")
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    out = os.path.join(outdir, name + '.wav')

    with open(out, 'wb') as fSilence:
        for b in  (
                'RIFF'.encode('utf-8'),                   # ChunkID (magic)      # 0x00
                pack('<I', ChunkSize),                    # ChunkSize            # 0x04
                'WAVE'.encode('utf-8'),                   # Format               # 0x08
                'fmt '.encode('utf-8'),                   # Subchunk1ID          # 0x0c
                pack('<I', Subchunk1Size),                # Subchunk1Size        # 0x10
                pack('<H', 1),                            # AudioFormat (1=PCM)  # 0x14
                pack('<H', channels),                     # NumChannels          # 0x16
                pack('<I', sample),                       # SampleRate           # 0x18
                pack('<I', bps // 8 * channels * sample),  # ByteRate             # 0x1c
                pack('<H', bps // 8 * channels),           # BlockAlign           # 0x20
                pack('<H', bps),                          # BitsPerSample        # 0x22
                pack('<H', ExtraParamSize),               # ExtraParamSize       # 0x22
                'data'.encode('utf-8'),                   # Subchunk2ID          # 0x24
                pack('<I', Subchunk2Size),                # Subchunk2Size        # 0x28
                ('\0' * Subchunk2Size).encode('utf-8')):
            fSilence.write(b)

    return out


def parseOptions():
    parser = ArgumentParser(prog=os.path.basename(sys.argv[0]))

    group_inout = parser.add_argument_group(title='Input/output files')

    group_inout.add_argument(
        "-i", "--input", required=True,
        help="input LilyPond file", metavar="INPUT-FILE")
    group_inout.add_argument(
        "-b", "--beatmap",
        help='name of beatmap file for adjusting MIDI tempo',
        metavar="BEATMAP-FILE")
    group_inout.add_argument(
        "--slide-show", dest="slideShow",
        help="input file prefix to generate a slide show "
        "(see doc/slideshow.txt)",
        metavar="SLIDESHOW-PREFIX")
    group_inout.add_argument(
        "-o", "--output",
        help='name of output video (e.g. "myNotes.avi") '
        '[INPUT-FILE.avi]',
        metavar="OUTPUT-FILE")

    group_scroll = parser.add_argument_group(title='Scrolling')

    group_scroll.add_argument(
        "-m", "--cursor-margins", dest="cursorMargins",
        help='width of left/right margins for scrolling '
        'in pixels [%(default)s]',
        metavar="WIDTH,WIDTH", default='50,100')
    group_scroll.add_argument(
        "-s", "--scroll-notes", dest="scrollNotes",
        help='rather than scrolling the cursor from left to right, '
        'scroll the notation from right to left and keep the '
        'cursor in the centre',
        action="store_true", default=False)

    group_video = parser.add_argument_group(title='Video output')

    group_video.add_argument(
        "-f", "--fps", dest="fps",
        help='frame rate of final video [%(default)s]',
        type=float, metavar="FPS", default=30.0)
    group_video.add_argument(
        "-q", "--quality",
        help="video encoding quality as used by ffmpeg's -q option "
        '(1 is best, 31 is worst) [%(default)s]',
        type=int, metavar="N", default=10)
    group_video.add_argument(
        "-r", "--resolution", dest="dpi",
        help='resolution in DPI [%(default)s]',
        metavar="DPI", type=int, default=110)
    group_video.add_argument(
        "-x", "--width",
        help='pixel width of final video [%(default)s]',
        metavar="WIDTH", type=int, default=1280)
    group_video.add_argument(
        "-y", "--height",
        help='pixel height of final video [%(default)s]',
        metavar="HEIGHT", type=int, default=720)

    group_cursors = parser.add_argument_group(title='Cursors')

    group_cursors.add_argument(
        "-c", "--color",
        help='name of the cursor color [%(default)s]',
        metavar="COLOR", default="red")
    group_cursors.add_argument(
        "--no-cursor", dest="noteCursor",
        help='do not generate a cursor',
        action="store_false", default=True)
    group_cursors.add_argument(
        "--note-cursor", dest="noteCursor",
        help='generate a cursor following the score note by note (default)',
        action="store_true", default=True)
    group_cursors.add_argument(
        "--measure-cursor", dest="measureCursor",
        help='generate a cursor following the score measure by measure',
        action="store_true", default=False)
    group_cursors.add_argument(
        "--slide-show-cursor", dest="slideShowCursor", type=float,
        help="start and end positions on the cursor in the slide show",
        nargs=2, metavar=("START", "END"))

    group_startend = parser.add_argument_group(
        title='Start and end of the video')

    group_startend.add_argument(
        "-t", "--title-at-start", dest="titleAtStart",
        help='adds title screen at the start of video '
        '(with name of song and its author)',
        action="store_true", default=False)
    group_startend.add_argument(
        "--title-duration", dest="titleDuration",
        help='time to display the title screen [%(default)s]',
        type=int, metavar="SECONDS", default=3)
    group_startend.add_argument(
        "--ttf", "--title-ttf", dest="titleTtfFile",
        help='path to TTF font file to use in title',
        metavar="FONT-FILE")
    group_startend.add_argument(
        "-p", "--padding",
        help='time to pause on initial and final frames [%(default)s]',
        metavar="SECS,SECS", default='1,1')

    group_os = parser.add_argument_group(title='External programs')

    group_os.add_argument(
        "--windows-ffmpeg", dest="winFfmpeg",
        help='(for Windows users) folder with ffpeg.exe '
        '(e.g. "C:\\ffmpeg\\bin\\")',
        metavar="PATH", default="")
    group_os.add_argument(
        "--windows-timidity", dest="winTimidity",
        help='(for Windows users) folder with '
        'timidity.exe (e.g. "C:\\timidity\\")',
        metavar="PATH", default="")

    group_debug = parser.add_argument_group(title='Debug')

    group_debug.add_argument(
        "-d", "--debug",
        help="enable debugging mode",
        action="store_true", default=False)
    group_debug.add_argument(
        "-k", "--keep", dest="keepTempFiles",
        help="don't remove temporary working files",
        action="store_true", default=False)
    group_debug.add_argument(
        "-v", "--version", dest="showVersion",
        help="show program version",
        action="store_true", default=False)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    options = parser.parse_args()

    if options.showVersion:
        showVersion()

    if options.titleAtStart and options.titleTtfFile is None:
        fatal("Must specify --title-ttf=FONT-FILE with --title-at-start.")

    if options.debug:
        setDebug()

    return options


def getVersion():
    try:
        stdout = subprocess.check_output(["git", "describe", "--tags"],
                                         cwd=os.path.dirname(__file__))
        m = re.match('^(v\d\S+)', stdout)
        if m:
            return m.group(1)
    except:
        #exc_type, exc_value, exc_traceback = sys.exc_info()
        #print("%s: %s" % (exc_type.__name__, exc_value))
        pass

    return VERSION


def showVersion():
    print("""ly2video %s

Copyright (C) 2012-2014 Jiri "FireTight" Szabo, Adam Spiers, Emmanuel Leguy
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.""" % getVersion())
    sys.exit(0)


def portableDevNull():
    if sys.platform.startswith("linux"):
        return "/dev/null"
    elif sys.platform.startswith("win"):
        return "NUL"


def applyBeatmap(src, dst, beatmap):
    prog = "midi-rubato"
    cmd = [prog, src, beatmap, dst]
    progress("Applying beatmap via '%s'" % " ".join(cmd))
    debug(safeRun(cmd))


def safeRun(cmd, errormsg=None, exitcode=None, shell=False, issues=[], preprocessor=None):
    if shell:
        quotedCmd = cmd
    else:
        quotedCmd = [cmd[0]]
        for arg in cmd[1:]:
            quotedCmd.append(pipes.quote(arg))
        quotedCmd = " ".join(quotedCmd)

    debug("Running: %s\n" % quotedCmd)

    try:
        stdout = subprocess.check_output(cmd, shell=shell)
    except KeyboardInterrupt:
        fatal("Interrupted via keyboard; aborting.")
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        excmsg = "%s: %s" % (exc_type.__name__, exc_value)
        if errormsg is None:
            errormsg = "Failed to run command: %s:\n%s" % \
                (quotedCmd, excmsg)
        if issues:
            bug(errormsg, *issues)
        else:
            fatal(errormsg, exitcode)

    if preprocessor:
        stdout = preprocessor(stdout)

    return stdout.decode("utf-8")


def safeRunInput(cmd, inputs, errormsg=None, exitcode=None, issues=[], preprocessor=None):
    quotedCmd = [cmd[0]]
    for arg in cmd[1:]:
        quotedCmd.append(pipes.quote(arg))
    quotedCmd = " ".join(quotedCmd)

    debug("Running: %s\n" % quotedCmd)

    outputs = []

    try:
        process = PopenSpawn(cmd, timeout=None)

        if inputs:
            count = 0
            for input in inputs:
                process.send(input)
                count += 1

                if count % 10 == 0:
                    sys.stdout.write(".")
                    sys.stdout.flush()

        process.sendeof()
        process.expect(EOF)
        output = process.before
    except KeyboardInterrupt:
        fatal("Interrupted via keyboard; aborting.")
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        excmsg = "%s: %s" % (exc_type.__name__, exc_value)
        if errormsg is None:
            errormsg = "Failed to run command: %s:\n%s" % \
                (quotedCmd, excmsg)
        if issues:
            bug(errormsg, *issues)
        else:
            fatal(errormsg, exitcode)

    retcode = process.wait()
    if retcode:
        raise subprocess.CalledProcessError(retcode, cmd, output=output)

    if preprocessor:
        output = preprocessor(output)

    return output.decode("utf-8")


def findExecutableDependencies(options):
    stdout = safeRun(["lilypond", "-v"], "LilyPond was not found.", 1)
    progress("LilyPond was found.")
    m = re.search('\AGNU LilyPond (\d[\d.]+\d)', stdout)
    if not m:
        bug("Couldn't determine LilyPond version via lilypond -v")
    version = m.group(1)

    # one-line-breaking is available as of 2.15.41:
    #   https://code.google.com/p/lilypond/issues/detail?id=2570
    #   https://codereview.appspot.com/6248056/
    #   http://article.gmane.org/gmane.comp.gnu.lilypond.general/72373/
    if StrictVersion(version) < StrictVersion('2.15.41'):
        fatal("You have LilyPond %s which does not support\n"
              "infinitely long lines.  Please upgrade to >= 2.15.41." %
              version)

    redirectToNull = " >%s" % portableDevNull()

    ffmpeg = options.winFfmpeg + "ffmpeg"
    if os.system(ffmpeg + " -version" + redirectToNull) != 0:
        fatal("FFmpeg was not found (maybe use --windows-ffmpeg?).", 2)
    progress("FFmpeg was found.")

    timidity = options.winTimidity + "timidity"
    if os.system(timidity + " -v" + redirectToNull) != 0:
        fatal("TiMidity++ was not found (maybe use --windows-timidity?).", 3)
    progress("TiMidity++ was found.")

    output_divider_line()

    return version, ffmpeg, timidity


def getCursorLineColor(options):
    options.color = options.color.lower()
    if options.color == "black":
        return (0, 0, 0)
    elif options.color == "yellow":
        return (255, 255, 0)
    elif options.color == "red":
        return (255, 0, 0)
    elif options.color == "green":
        return (0, 128, 0)
    elif options.color == "blue":
        return (0, 0, 255)
    elif options.color == "brown":
        return (165, 42, 42)
    else:
        warn("Color was not found, ly2video will use default one ('red').")
        return (255, 0, 0)


def absPathFromRunDir(path):
    if os.path.isabs(path):
        return path
    return os.path.join(runDir, path)


def getOutputFile(options):
    outputFile = options.output
    if outputFile is None:
        basename, ext = os.path.splitext(options.input)
        outputFile = basename + '.avi'
    return absPathFromRunDir(outputFile)


def imageToBytes(image):
    f = BytesIO()
    image.save(f, format="BMP")
    return f.getvalue()


def generateNotesVideo(ffmpeg, fps, quality, frames, wavPath):
    progress("Generating video with animated notation\n")
    notesPath = tmpPath("notes.mpg")
    cmd = [
        ffmpeg,
        "-nostdin",
        "-f", "image2pipe",
        "-r", str(fps),
        "-i", "-",
        "-i", wavPath,
        "-q:v", quality,
        "-f", "avi",
        notesPath
    ]
    safeRunInput(cmd, inputs=(imageToBytes(frame) for frame in frames), exitcode=15)
    output_divider_line()
    return notesPath


def generateSilentVideo(ffmpeg, fps, quality, desiredDuration, name, srcFrame):
    out         = tmpPath('%s.mpg' % name)
    frames = int(desiredDuration * fps)
    trueDuration = float(frames) / fps
    progress("Generating silent video %s, duration %fs\n" %
             (out, trueDuration))
    silentAudio = generateSilence(name, trueDuration)
    cmd = [
        ffmpeg,
        "-nostdin",
        "-f", "image2pipe",
        "-r", str(fps),
        "-i", "-",
        "-i", silentAudio,
        "-q:v", quality,
        "-f", "avi",
        out
    ]
    safeRunInput(cmd, inputs=itertools.repeat(imageToBytes(srcFrame), frames), exitcode=14)
    output_divider_line()
    return out


def generateVideo(ffmpeg, options, wavPath, titleText, frameWriter, outputFile):
    fps = float(options.fps)
    quality = str(options.quality)

    videos = [generateNotesVideo(ffmpeg, fps, quality, frameWriter.frames, wavPath)]

    initialPadding, finalPadding = options.padding.split(",")

    if float(initialPadding) > 0:
        video = generateSilentVideo(ffmpeg, fps, quality,
                                    float(initialPadding), 'initial-padding',
                                    frameWriter.firstFrame)
        videos.insert(0, video)

    if float(finalPadding) > 0:
        video = generateSilentVideo(ffmpeg, fps, quality,
                                    float(finalPadding), 'final-padding',
                                    frameWriter.lastFrame)
        videos.append(video)

    if options.titleAtStart:
        titleFrame = generateTitleFrame(titleText, options.width,
                                        options.height,
                                        options.titleTtfFile)
        output_divider_line()

        video = generateSilentVideo(ffmpeg, fps, quality,
                                    float(options.titleDuration),
                                    'title', titleFrame)
        videos.insert(0, video)

    if len(videos) == 1:
        os.rename(videos[0], outputFile)
    else:
        progress("Joining videos:\n%s" %
                 "".join(["  %s\n" % video for video in videos]))

        # Do this with ffmpeg:
        #
        #   ffmpeg -i concat:"title.mpg|notes.mpg" -codec copy out.mpg
        #
        # See: http://stackoverflow.com/questions/7333232/concatenate-two-mp4-files-using-ffmpeg
        cmd = [
            ffmpeg,
            "-nostdin",
            "-i", "concat:%s" % "|".join(videos),
            "-codec", "copy",
            "-y",
            "-f", "avi",
            outputFile,
        ]
        safeRun(cmd, exitcode=16)


def getLyVersion(fileName):
    # if I don't have input file, end
    if fileName is None:
        fatal("LilyPond input file was not specified.", 4)
    else:
        # otherwise try to open fileName
        try:
            with open(fileName, 'r', encoding='utf-8') as fLyFile:
                # find version of LilyPond in .ly input file
                for line in fLyFile.readlines():
                    m = re.search(r'\\version\s+"([^"]+)"', line)
                    if m:
                        return m.group(1)
        except Exception as e:
            traceback.print_exception(e)

            fatal("Couldn't read %s" % fileName, 5)


def getNumStaffLines(lyFileName, dpi):
    # generate preview of notes
    output = runLilyPond(
        lyFileName, dpi,
        "-dpreview",
        "-dprint-pages=#f",
    )

    # move generated files into temporary directory
    dirname, filename = os.path.split(lyFileName)
    if dirname != tmpPath():
        basename, suffix = os.path.splitext(filename)
        for ext in ('png', 'eps'):
            generated = basename + '.' + ext
            src = os.path.join(dirname, generated)
            dst = tmpPath(generated)
            os.rename(src, dst)
            progress("Moved %s to %s" % (src, dst))

    # find preview image and get num of staff lines
    previewPic = None
    for fileName in os.listdir("."):
        if "preview" in fileName:
            if fileName.split(".")[-1] == "png":
                previewPic = fileName

    if previewPic is None:
        error = "Failed to generate a .png preview file from %s" % lyFileName
        msg = error

        if re.search('\S', output):
            msg = "%s\nlilypond output: [%s]\n\n%s; please check lilypond output immediately above." % \
                (error, output, msg)

        fatal("%s\n\n"
              "Maybe your input .ly file was missing a \\layout { } "
              "command?  See:\n\n"
              "  http://www.lilypond.org/doc/v2.16/Documentation/learning/introduction-to-the-lilypond-file-structure\n\n"
              "for more information." % msg)

    staffYs = findStaffLines(previewPic, 50)
    numStaffLines = len(staffYs)

    progress("Found %d staff lines" % numStaffLines)
    return numStaffLines


def writeSpaceTimeDumper():
    filename = 'dump-spacetime-info.ly'
    f = open(tmpPath(filename), 'w', encoding='utf-8')
    f.write('''
% Huge thanks to Jan Nieuwenhuizen for helping me with this!

#(define (grob-get-ancestor-with-interface grob interface axis)
  (let ((parent (ly:grob-parent grob axis)))
   (if (null? parent)
    #f
    (if (grob::has-interface parent interface)
     parent
     (grob-get-ancestor-with-interface parent interface axis)))))

#(define (grob-get-paper-column grob)
  (grob-get-ancestor-with-interface grob 'paper-column-interface X))

#(define (dump-spacetime-info grob)
  (let* ((extent       (ly:grob-extent grob grob X))
         (system       (ly:grob-system grob))
         (x-extent     (ly:grob-extent grob system X))
         (left         (car x-extent))
         (right        (cdr x-extent))
         (paper-column (grob-get-paper-column grob))
         (time         (ly:grob-property paper-column 'when 0))
         (cause        (ly:grob-property grob 'cause))
         (origin       (ly:event-property cause 'origin))
         (location     (ly:input-file-line-char-column origin))
         (file         (list-ref location 0))
         (line         (list-ref location 1))
         (char         (list-ref location 2))
         (column       (list-ref location 3))
         (drum-type    (ly:event-property cause 'drum-type))
         (pitch        (if (null? drum-type)
                           (ly:event-property cause 'pitch)
                          (ly:assoc-get drum-type midiDrumPitches)))
         (midi-pitch   (if (ly:pitch? pitch) (+ 0.0 (ly:pitch-tones pitch)) "no pitch")))
   (if #f (format #t "\\nly2video: # pitch ~a drum-type ~a ~a" pitch drum-type (null? drum-type)))
   (if (not (equal? (ly:grob-property grob 'transparent) #t))
    (format #t "\\nly2video: (~23,16f, ~23,16f) pitch ~d:~a:~a @ ~23,16f from ~a:~3d:~d"
                left right
                (if (ly:pitch? pitch) (ly:pitch-octave pitch) 0)
                (if (ly:pitch? pitch) (ly:pitch-notename pitch) "?")
                (if (ly:pitch? pitch) (ly:pitch-alteration pitch) "?")
                (+ 0.0 (ly:moment-main time) (* (ly:moment-grace time) (/ 9 40)))
                file line char))))

#(define (dump-spacetime-info-barline grob)
  (let* ((extent       (ly:grob-extent grob grob X))
         (system       (ly:grob-system grob))
         (x-extent     (ly:grob-extent grob system X))
         (left         (car x-extent))
         (right        (cdr x-extent))
         (paper-column (grob-get-paper-column grob))
         (time         (ly:grob-property paper-column 'when 0))
         (cause        (ly:grob-property grob 'cause)))
   (if (not (equal? (ly:grob-property grob 'transparent) #t))
    (format #t "\\nly2videoBar: (~23,16f, ~23,16f) @ ~23,16f"
                left right
                (+ 0.0 (ly:moment-main time) (* (ly:moment-grace time) (/ 9 40)))
                ))))

\layout {
  \context {
    \DrumVoice
    \override NoteHead.after-line-breaking = #dump-spacetime-info
  }
  \context {
    \DrumStaff
    \override BarLine.after-line-breaking = #dump-spacetime-info-barline
  }
  \context {
    \Voice
    \override NoteHead.after-line-breaking = #dump-spacetime-info
  }
  \context {
    \Staff
    \override BarLine.after-line-breaking = #dump-spacetime-info-barline
  }
  \context {
    \ChordNames
    \override ChordName.after-line-breaking = #dump-spacetime-info
  }
}
''')
    f.close()
    return '\\include "%s"\n' % filename


def sanitiseLy(lyFile, dumper, width, height, dpi, numStaffLines,
               titleText, lilypondVersion):
    fLyFile = open(lyFile, 'r', encoding='utf-8')

    sanitisedLyFileName = tmpPath("sanitised.ly")

    # create own ly lyFile
    fSanitisedLyFile = open(sanitisedLyFileName, 'w', encoding='utf-8')

    # if I add own paper block
    paperBlock = False

    # stores info about header and paper block (and brackets in them)
    headerPart = False
    bracketsHeader = 0
    paperPart = False
    bracketsPaper = 0

    fSanitisedLyFile.write(dumper)

    line = fLyFile.readline()
    while line != "":
        # ignore these commands
        if line.find("#(set-global-staff-size") != -1 or \
           line.find("\\bookOutputName") != -1:
            pass

        # if I find version, write own paper block right behind it
        elif line.find("\\version") != -1:
            fSanitisedLyFile.write(line)
            leftPaperMarginPx = writePaperHeader(
                fSanitisedLyFile, width, height, dpi, numStaffLines, lilypondVersion)
            paperBlock = True

        # get needed info from header block and ignore it
        elif (line.find("\\header") != -1 or headerPart):
            if line.find("\\header") != -1:
                fSanitisedLyFile.write(
                    "\\header {\n   tagline = ##f composer = ##f\n}\n")
                headerPart = True

            if re.search("\\btitle\\s*=", line):
                titleText.name = line.split("=")[-1].strip()[1:-1]
            if re.search("composer\\s*=", line):
                titleText.author = line.split("=")[-1].strip()[1:-1]

            for char in line:
                if char == "{":
                    bracketsHeader += 1
                elif char == "}":
                    bracketsHeader -= 1
            if bracketsHeader == 0:
                headerPart = False

        # ignore paper block
        elif (line.find("\\paper") != -1 or paperPart):
            debug("paperPart: %s" % line.rstrip())
            if line.find("\\paper") != -1:
                paperPart = True
                debug(">> in paperPart")

            for char in line:
                if char == "{":
                    bracketsPaper += 1
                    debug("  bracketsPaper += 1")
                elif char == "}":
                    bracketsPaper -= 1
                    debug("  bracketsPaper -= 1")
            if bracketsPaper == 0:
                paperPart = False
                debug("<< leaving paperPart")

        # add unfoldRepeats right after start of score block
        elif re.search("\\\\score\\s*\\{", line):
            fSanitisedLyFile.write(line + " \\unfoldRepeats\n")

        # parse other lines, ignore page breaking commands and articulate
        elif not headerPart and not paperPart:
            finalLine = ""

            if line.find("\\break") != -1:
                finalLine = (line[:line.find("\\break")]
                             + line[line.find("\\break") + len("\\break"):])
            elif line.find("\\noBreak") != -1:
                finalLine = (line[:line.find("\\noBreak")]
                             + line[line.find("\\noBreak") + len("\\noBreak"):])
            elif line.find("\\pageBreak") != -1:
                finalLine = (line[:line.find("\\pageBreak")] +
                             line[line.find("\\pageBreak") +
                             len("\\pageBreak"):])
            else:
                finalLine = line

            fSanitisedLyFile.write(finalLine)

        line = fLyFile.readline()

    fLyFile.close()

    # if I didn't find \version, write own paper block
    if not paperBlock:
        leftPaperMarginPx = writePaperHeader(fSanitisedLyFile, width, height, dpi,
                                             numStaffLines, lilypondVersion)

    fSanitisedLyFile.close()
    progress("Wrote sanitised version of %s into %s" %
             (lyFile, sanitisedLyFileName))

    return sanitisedLyFileName, leftPaperMarginPx


def main():
    """
    Main function of ly2video script.

    It performs the following steps:

    - use Lilypond to generate PNG images, and MIDI files of the
      music

    - find the spatial and temporal position of each note in the PNG
      and MIDI files

    - combine the positions together to generate the required number
      of video frames

    - create a video file from the individual frames
    """
    options = parseOptions()

    lilypondVersion, ffmpeg, timidity = findExecutableDependencies(options)

    # FIXME.  Ugh, eventually this will be an instance method, and
    # we'll have somewhere nice to save state.
    global runDir
    runDir = os.getcwd()
    setRunDir(runDir)

    # Delete old temporary files.
    if os.path.isdir(tmpPath()):
        shutil.rmtree(tmpPath())
    os.mkdir(tmpPath())

    # .ly input file from user (string)
    lyFile = options.input

    # If the input .ly doesn't match the currently installed LilyPond
    # version, try to convert it
    lyFile = preprocessLyFile(lyFile, lilypondVersion)

    # https://pillow.readthedocs.io/en/5.1.x/releasenotes/5.0.0.html#decompression-bombs-now-raise-exceptions
    Image.MAX_IMAGE_PIXELS = None

    numStaffLines = getNumStaffLines(lyFile, options.dpi)

    titleText = namedtuple("titleText", "name author")
    titleText.name = "<name of song>"
    titleText.author = "<author>"

    dumper = writeSpaceTimeDumper()
    sanitisedLyFileName, leftPaperMargin = \
        sanitiseLy(lyFile, dumper,
                   options.width, options.height, options.dpi,
                   numStaffLines, titleText, lilypondVersion)

    output = runLilyPond(sanitisedLyFileName, options.dpi,)
    with open(tmpPath('sanitised.ly.out'), 'w', encoding='utf-8') as out:
        out.write(output)

    leftmostGrobsByMoment = getLeftmostGrobsByMoment(output, options.dpi,
                                                     leftPaperMargin)

    measuresXpositions = None
    if options.measureCursor:
        measuresXpositions = getMeasuresIndices(output, options.dpi,
                                                leftPaperMargin)

    notesImage = tmpPath("sanitised.png")

    midiPath = tmpPath("sanitised.midi")
    if not os.path.exists(midiPath):
        fatal("Failed to generate MIDI file from %s\n"
              "Please ensure that your input file contains a \\midi "
              "command and successfully outputs a MIDI file when "
              "run through LilyPond." % sanitisedLyFileName)

    if options.beatmap:
        output_divider_line()
        newMidiPath = tmpPath("sanitised-adjusted.midi")
        applyBeatmap(midiPath, newMidiPath,
                     absPathFromRunDir(options.beatmap))
        midiPath = newMidiPath

    output_divider_line()

    # find needed data in MIDI
    midiResolution, temposList, midiTicks, notesInTicks, pitchBends = \
        getMidiEvents(midiPath)

    output_divider_line()

    noteIndices = getNoteIndices(leftmostGrobsByMoment,
                                 midiResolution, midiTicks, notesInTicks,
                                 pitchBends)
    output_divider_line()

    # frame rate of output video
    fps = options.fps

    # generate notes
    frameWriter = VideoFrameWriter(
        fps, getCursorLineColor(options),
        midiResolution, midiTicks, temposList)
    leftMargin, rightMargin = options.cursorMargins.split(",")
    frameWriter.scoreImage = ScoreImage(
        options.width, options.height,
        Image.open(notesImage), noteIndices, measuresXpositions,
        int(leftMargin), int(rightMargin),
        options.scrollNotes, options.noteCursor)
    if options.slideShow:
        lastOffset = midiTicks[-1] / midiResolution
        frameWriter.push(
            SlideShow(options.slideShow, options.slideShowCursor, lastOffset))
    #  frameWriter.write()
    output_divider_line()

    wavPath = genWavFile(timidity, midiPath)

    output_divider_line()

    outputFile = getOutputFile(options)
    #  finalFrame = "notes/frame%d.png" % (frameWriter.frameNum - 1)
    generateVideo(ffmpeg, options, wavPath, titleText, frameWriter, outputFile)

    output_divider_line()

    if options.keepTempFiles:
        progress("Left temporary files in %s" % tmpPath())
    else:
        shutil.rmtree(tmpPath())

    # end
    progress("Ly2video has ended. Your generated file: " + outputFile + ".")
    return 0

if __name__ == '__main__':
    status = main()
    sys.exit(status)
