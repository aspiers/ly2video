#!/usr/bin/env python
# coding=utf-8

# ly2video - generate performances video from LilyPond source files
# Copyright (C) 2012 Jiri "FireTight" Szabo
# Copyright (C) 2012 Adam Spiers
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
VERSION = '0.4.2'

import collections
import copy
import os
import re
import shutil
import subprocess
import sys
import urllib
import pipes
from collections import namedtuple
from distutils.version import StrictVersion
from optparse import OptionParser
from struct import pack

from PIL import Image, ImageDraw, ImageFont
from ly.tokenize import MusicTokenizer, Tokenizer
import ly.tools
import midi

from pprint import pprint, pformat

DEBUG = False # --debug sets to True

GLOBAL_STAFF_SIZE = 20

C_MAJOR_SCALE_STEPS = [
    # Maps notes of the C major scale into semi-tones above C.
    # This is needed to map the pitch of ly.tools.Pitch notes
    # into MIDI pitch values within a given octave.
     0, # c
     2, # d
     4, # e
     5, # f
     7, # g
     9, # a
    11, # b
]

NOTE_NAMES = [ "C", "C#/Db", "D", "D#/Eb", "E", "F", "F#/Gb",
               "G", "G#/Ab", "A", "A#/Bb", "B" ]

class LySrc(object):
    """
    Provides access to the contents of .ly files, which on first read
    are cached in memory along with the changelist from converting
    relative note pitches to absolute pitches.
    """
    cache = { }

    __slots__ = [ 'filename', 'lines', 'parser', 'absolutePitches' ]

    @classmethod
    def get(cls, filename):
        if filename not in cls.cache:
            cls.cache[filename] = LySrc(filename)
        return cls.cache[filename]

    def __init__(self, filename):
        self.filename = filename
        self.readLines()
        document = ''.join(self.lines)
        self.initParser(document)
        self.getAbsolutePitches(document)

    def readLines(self):
        with open(self.filename) as f:
            self.lines = [ line for line in f.readlines() ]

    def initParser(self, document):
        language, keyPitch = ly.tools.languageAndKey(document)
        progress('Detected language as %s' % language)
        self.parser = MusicTokenizer()
        self.parser.language = language

    def getAbsolutePitches(self, document):
        if document.find('\\relative') == -1:
            self.absolutePitches = { }
            return

        # N.B. line numbers in this are numbered starting from 0
        changelist = ly.tools.relativeToAbsolute(document)
        self.absolutePitches = changelist.token_changes_by_coords
        debug("absolutePitches: %s" % repr(self.absolutePitches))
        if not self.absolutePitches:
            warn("Conversion of .ly relative pitches to absolute failed. "
                 "Synchronization will probably fail.")

    def getAbsolutePitch(self, lySrcLocation):
        coords = lySrcLocation.coords()
        if coords in self.absolutePitches:
            grobPitchText = self.absolutePitches[coords]
        else:
            # text representations of absolute and relative pitch are the same
            # (absolutePitches contains a changelist, i.e. only differences)
            grobPitchText = self.lines[lySrcLocation.lineNum][lySrcLocation.columnNum:]

        try:
            grobPitchToken = self.parser.tokens(grobPitchText).next()
        except StopIteration:
            bug("Didn't find a note at:\n"
                "    %s\n" % lySrcLocation)

        if grobPitchToken == 'q':
            # 'q' means a repeated chord in LilyPond
            return None, grobPitchToken

        if not isinstance(grobPitchToken, ly.tokenize.MusicTokenizer.Pitch):
            bug("Expected pitch token during conversion from relative to absolute\n"
                "pitch, but found %s instance @ %s:\n\n    %s" %
                (grobPitchToken.__class__, lySrcLocation, grobPitchToken), 33, 37)

        grobPitchValue = pitchValue(grobPitchToken, self.parser)
        return grobPitchValue, grobPitchToken

class LySrcLocation(object):
    """
    Represents a location within a .ly file.  Note that line numbers
    count from 0, but are displayed counting from 1, since that
    matches what editors such as emacs and vim show.
    """
    __slots__ = [ 'filename', 'lineNum', 'columnNum' ]

    def __init__(self, filename, lineNum, columnNum):
        self.filename  = filename
        self.lineNum   = lineNum
        self.columnNum = columnNum

    def __str__(self):
        return "%s:%d:%d" % (self.filename, self.lineNum + 1, self.columnNum)

    def coords(self):
        return (self.lineNum, self.columnNum)

    def getAbsolutePitch(self):
        return LySrc.get(self.filename).getAbsolutePitch(self)

def preprocessLyFile(lyFile, lilypondVersion, dumper):
    version = getLyVersion(lyFile)
    progress("Version in %s: %s" % (lyFile, version if version else "unspecified"))
    if version and version != lilypondVersion:
        progress("Will convert to: %s" % lilypondVersion)
        newLyFile = tmpPath('converted.ly')
        with open(newLyFile, 'w') as f:
            f.write(dumper)
        if os.system("convert-ly '%s' >> '%s'" % (lyFile, newLyFile)) == 0:
            return newLyFile
        else:
            warn("Convert of input file has failed. " +
                 "This could cause some problems.")

    newLyFile = tmpPath('unconverted.ly')

    with open(newLyFile, 'w') as new:
        new.write(dumper)
        with open(lyFile) as old:
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
        "-dmidi-extension=midi", # default on Windows is .mid
        "-dresolution=%d" % dpi
    ] + list(args) + [ lyFileName ]
    output_divider_line()
    os.chdir(tmpPath())
    output = safeRun(cmd, exitcode=9)
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

    leftmostGrobs = { }
    currentLySrcFile = None

    for line in lines:
        if not line.startswith('ly2video: '):
            continue

        m = re.match('^ly2video:\\s+'
                     # X-extents
                     '\\(\\s*(-?\\d+\\.\\d+),\\s*(-?\\d+\\.\\d+)\\s*\\)'
                     # delimiter
                     '\\s+@\\s+'
                     # moment
                     '(-?\\d+\\.\\d+)'
                     # delimiter
                     '\\s+from\\s+'
                     # file:line:char
                     '([^:]+): *(\d+):(\d+)'
                     '$', line)
        if not m:
            bug("Failed to parse ly2video line:\n%s" % line)
        left, right, moment, filename, line, column = m.groups()

        if currentLySrcFile is None or currentLySrcFile != filename:
            currentLySrcFile = filename
            debug("Current .ly source file: %s" % currentLySrcFile)

        left   = float(left)
        right  = float(right)
        centre = (left + right) / 2
        moment = float(moment)
        line   = int(line) - 1 # LilyPond counts from 1
        column = int(column)
        x = int(round(staffSpacesToPixels(centre, dpi))) + leftPaperMarginPx

        if moment not in leftmostGrobs or x < leftmostGrobs[moment][0]:
            location = LySrcLocation(filename, line, column)
            leftmostGrobs[moment] = [x, location]
            debug("leftmost grob for moment %9f is now x =%5d @ %3d:%d"
                  % (moment, x, line + 1, column))

    groblist = [ tuple([moment] + leftmostGrobs[moment])
                 for moment in sorted(leftmostGrobs.keys()) ]

    if not groblist:
        bug("Didn't find any notes; something must have gone wrong "
            "with the use of dump-spacetime-info.")

    return groblist

def findTopStaffLine(image, lineLength):
    """
    Returns the coordinates of the left-most pixel in the top line of
    the first staff in the image.

    FIXME: The code assumes that the first staff is not indented
    further right than subsequent staffs.

    Params:
    - image:        image with staff lines
    - lineLength:   needed length of line to accept it as staff line
    """
    # position of the first line on image
    firstLinePos = (-1, -1)

    width, height = image.size

    # Start searching at the hard left but allow for a left margin.
    for x in xrange(width):
        for y in xrange(height):
            for length in xrange(lineLength):
                # testing color of pixels in range (startPos, startPos + lineLength)
                if image.getpixel((x + length, y)) == (255,255,255):
                    # if it's white then it's not a staff line
                    firstLinePos = (-1, -1)
                    break
                else:
                    # else it can be
                    firstLinePos = (x, y)
            # when have a valid position, break out
            if firstLinePos != (-1, -1):
                break
        if firstLinePos != (-1, -1):
            break

    progress("First staff line found at (%d, %d)" % firstLinePos)
    return firstLinePos

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

def findStaffLinesInImage(image, lineLength):
    """
    Takes a image and returns co-ordinates of staff lines in pixels.

    Params:
      - image:        image object containing staff lines
      - lineLength:   required length of line for acceptance as staff line

    Returns a tuple of the following items:
      - x:   x co-ordinate of left end of staff lines
      - ys:  list of y co-ordinates of staff lines
    """
    firstLineX, firstLineY = findTopStaffLine(image, lineLength)
    # move 3 pixels to the right, to avoid line of pixels connectings
    # all staffs together
    firstLineX += 3

    lines = []
    newLine = True

    width, height = image.size

    for y in xrange(firstLineY, height):
        # if color of that pixel isn't white
        if image.getpixel((firstLineX, y)) != (255,255,255):
            # and it can be new staff line
            if newLine:
                # accept it
                newLine = False
                lines.append(y)
        else:
            # it's space between lines
            newLine = True

    del image

    # return staff line indices
    return firstLineX, lines

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
    titleScreen = Image.new("RGB", (width, height), (255,255,255))
    # it will draw text on titleScreen
    drawer = ImageDraw.Draw(titleScreen)

    # font for song's name, args - font type, size
    nameFont = ImageFont.truetype(ttfFile, height / 15)
    # font for author
    authorFont = ImageFont.truetype(ttfFile, height / 25)

    # args - position of left upper corner of rectangle (around text), text, font and color (black)
    drawer.text(((width - nameFont.getsize(titleText.name)[0]) / 2,
                 (height - nameFont.getsize(titleText.name)[1]) / 2 - height / 25),
                titleText.name, font=nameFont, fill=(0,0,0))
    # same thing
    drawer.text(((width - authorFont.getsize(titleText.author)[0]) / 2,
                 (height / 2) + height / 25),
                titleText.author, font=authorFont, fill=(0,0,0))

    titleScreen.save(tmpPath("title.png"))
    generateStaticVideoFrames('title', int(round(fps * titleLength)))

def staffSpacesToPixels(ss, dpi):
    staffSpacePoints = GLOBAL_STAFF_SIZE / 4
    points = ss * staffSpacePoints
    pointsPerInch = 72.27 # Donald Knuth's TeX points
    inches = points / pointsPerInch
    return inches * dpi

def mmToPixel(mm, dpi):
    pixelsPerMm = dpi / 25.4
    return mm * pixelsPerMm

def pixelsToMm(pixels, dpi):
    inchesPerPixel = 1.0 / dpi
    mmPerPixel = inchesPerPixel * 25.4
    return pixels * mmPerPixel

def writePaperHeader(fFile, dpi, numOfLines, lilypondVersion):
    """
    Writes own paper block into given file.

    Params:
    - fFile:        given opened file
    - numOfLines:   number of staff lines
    """
    fFile.write("\\paper {\n")
    fFile.write("   page-breaking = #ly:one-line-breaking\n")

    topPixels    = 200
    bottomPixels = 200
    leftPixels   = 200
    rightPixels  = 200

    topMm    = round(pixelsToMm(topPixels,    dpi))
    bottomMm = round(pixelsToMm(bottomPixels, dpi))
    leftMm   = round(pixelsToMm(leftPixels,   dpi))
    rightMm  = round(pixelsToMm(rightPixels,  dpi))

    fFile.write("   top-margin    = %d\\mm\n" % topMm)
    fFile.write("   bottom-margin = %d\\mm\n" % bottomMm)
    fFile.write("   left-margin   = %d\\mm\n" % leftMm)
    fFile.write("   right-margin  = %d\\mm\n" % rightMm)

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
    midiHeader = midiFile[0]

    temposList = []
    for event in midiHeader:
        # if it's SetTempoEvent
        if isinstance(event, midi.SetTempoEvent):
            debug("tick %6d: tempo change to %.3f bpm" % (event.tick, event.bpm))
            temposList.append((event.tick, event.bpm))

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
    for i in xrange(1, len(midiFile)):
        debug("Reading MIDI track %d" % i)
        track = midiFile[i]
        pendingPitchBend = None
        for event in track:
            tick = event.tick
            eventClass = event.__class__.__name__

            if pendingPitchBend:
                if pendingPitchBend.tick != tick:
                    bug("Found orphaned pitch bend in tick %d" %
                        pendingPitchBend.tick)
                if not isinstance(event, midi.NoteOnEvent):
                    bug("Pitch bend was not followed by NoteOn in tick %d" %
                        tick)
                if event.get_velocity() == 0:
                    bug("Pitch bend was followed by NoteOff")

            if isinstance(event, midi.PitchWheelEvent):
                bend = event.get_pitch()
                debug("    tick %6d: %s(%d)" %
                      (tick, eventClass, bend))
                if bend != 0:
                    pendingPitchBend = event
                continue
            elif isinstance(event, midi.NoteOnEvent):
                if event.get_velocity() == 0:
                    # velocity is zero (that's basically "NoteOffEvent")
                    debug("    tick %6d:     NoteOffEvent(%d)" %
                          (tick, event.get_pitch()))
                    continue
                else:
                    if pendingPitchBend:
                        pitchBends[event] = pendingPitchBend
                        pendingPitchBend = None
                    debug("    tick %6d: %s(%d)" %
                          (tick, eventClass, event.get_pitch()))
            else:
                debug("    tick %6d:     %s - skipping" %
                      (tick, eventClass))
                continue

            # add it into notesInTicks
            if tick not in notesInTicks:
                notesInTicks[tick] = []
            notesInTicks[tick].append(event)

    return notesInTicks, pitchBends

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
    midiFile = midi.read_midifile(midiFileName)
    # and make ticks absolute
    midiFile.make_ticks_abs()

    # get MIDI resolution and header
    midiResolution = midiFile.resolution
    progress("MIDI resolution (ticks per beat) is %d" % midiResolution)

    temposList = getTemposList(midiFile)

    output_divider_line()

    notesInTicks, pitchBends = getNotesInTicks(midiFile)

    # get all ticks with notes and sorts it
    midiTicks = notesInTicks.keys()
    midiTicks.sort()

    # find the tick corresponding to the earliest EndOfTrackEvent
    # across all MIDI channels, and append it
    endOfTrack = -1
    for eventsList in midiFile[1:]:
        if isinstance(eventsList[-1], midi.EndOfTrackEvent):
            if endOfTrack < eventsList[-1].tick:
                endOfTrack = eventsList[-1].tick
    midiTicks.append(endOfTrack)

    progress("MIDI: Parsing MIDI file has ended.")

    return (midiResolution, temposList, midiTicks, notesInTicks, pitchBends)

def pitchValue(token, parser):
    """
    Returns the numerical pitch of the token representing a note,
    where the token is treated as an absolute pitch, and each
    increment of 1 is equivalent to going up a semi-tone (half-step).
    This facilitates comparison to MIDI NoteOn events.
    """
    p = ly.tools.Pitch.fromToken(token, parser)

    accidentalSemitoneSteps = 2 * p.alter

    pitch = (p.octave + 4) * 12 + \
            C_MAJOR_SCALE_STEPS[p.note] + \
            accidentalSemitoneSteps

    return pitch

def getMidiPitches(events, pitchBends):
    """
    Build dicts tracking which pitches (modulo the octave)
    are present in the current tick and index.
    """
    midiPitches = { }
    for event in events:
        pitch = event.get_pitch()
        if event in pitchBends:
            pitch += float(pitchBends[event].get_pitch()) / 4096
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
    lastChord = [ ]

    # final indices of notes
    alignedNoteIndices = []

    # index into list of note indices
    i = 0

    currentLySrcFile = None

    while i < len(leftmostGrobsByMoment):
        if midiIndex == len(midiTicks):
            warn("Ran out of MIDI indices after %d. Current index: %d" %
                  (midiIndex, index))
            break

        moment, index, lySrcLocation = leftmostGrobsByMoment[i]
        if currentLySrcFile is None or currentLySrcFile != lySrcLocation.filename:
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

        debug("%-3s @ %3d:%3d | grob(time=%.4f, x=%5d, tick=%5d) | MIDI(tick=%5d)" %
              (grobPitchToken, lySrcLocation.lineNum + 1, lySrcLocation.columnNum,
               moment, index, grobTick, midiTick))

        if not midiTick in notesInTicks:
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
            msg = "    WARNING: skipping MIDI tick %d since no grob matched; contents:" % midiTick
            for event in events:
                msg += ("\n        pitch %d length %d" %
                        (event.get_pitch(), event.length))
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
            debug("    grob's pitch %d not found in midiPitches; "
                  "probably a tie/ChordName" % grobPitchValue)
            midiPitches = [ str(event.get_pitch()) for event in events ]
            debug("    midiPitches: %s" %
                  " ".join([ "%s (%s)" % (pitch, NOTE_NAMES[int(pitch) % 12])
                             for pitch in sorted(midiPitches) ]))
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
            lastChord = [ ]

    if midiIndex < len(midiTicks) - 1:
        # Could happen if last note is a dangling tie?
        warn("ran out of notes at MIDI tick %d (%d/%d ticks)" % \
                 (midiTicks[midiIndex], midiIndex + 1, len(midiTicks)))

    progress("sync points found: %5d\n"
             "             from: %5d original indices\n"
             "              and: %5d original ticks\n"
             "   last tick used: %5d\n"
             "    ticks skipped: %5d"   %
             (len(alignedNoteIndices), len(leftmostGrobsByMoment), originalTickCount,
              midiIndex, ticksSkipped))

    if len(alignedNoteIndices) < 2:
        bug("Not enough synchronization points found!  Aborting.")

    return alignedNoteIndices

class VideoFrameWriter(object):
    """
    Generates frames for the final video, synchronized with audio.
    Each frame is written to disk as a PNG file.

    Counts time between starts of two notes, gets their positions on
    image and generates needed amount of frames. The index of the last
    note is repeated, so that every index can be the left one in a pair.
    The required number of frames for every pair is computed as a real
    number and because a fractional number of frames can't be
    generated, they are stored in dropFrame and if that is > 1, it
    skips generating one frame.
    """

    def __init__(self, width, height, fps, cursorLineColor,
                 scrollNotes, leftMargin, rightMargin,
                 midiResolution, midiTicks, temposList):
        """
        Params:
          - width:             pixel width of frames (and video)
          - height:            pixel height of frames (and video)
          - fps:               frame rate of video
          - cursorLineColor:   color of middle line
          - scrollNotes:       False selects cursor scrolling mode,
                               True selects note scrolling mode
          - leftMargin:        left margin for cursor when
                               cursor scrolling mode is enabled
          - rightMargin:       right margin for cursor when
                               cursor scrolling mode is enabled
          - midiResolution:    resolution of MIDI file
          - midiTicks:         list of ticks with NoteOnEvent
          - temposList:        list of possible tempos in MIDI
          - leftMargin:        width of left margin for cursor
          - rightMargin:       width of right margin for cursor
        """
        self.midiIndex   = 0
        self.tempoIndex  = 0
        self.frameNum    = 0

        # Keep track of wall clock time to ensure that rounding errors
        # when aligning indices to frames don't accumulate over time.
        self.secs = 0.0

        self.scrollNotes = scrollNotes

        # In cursor scrolling mode, this is the x-coordinate in the
        # original image of the left edge of the frame (i.e. the
        # left edge of the cropping rectangle).
        self.leftEdge = None

        self.width = width
        self.height = height
        self.fps = fps
        self.cursorLineColor = cursorLineColor
        self.midiResolution = midiResolution
        self.midiTicks = midiTicks
        self.temposList = temposList
        self.leftMargin = leftMargin
        self.rightMargin = rightMargin

    def estimateFrames(self):
        approxBeats = float(self.midiTicks[-1]) / self.midiResolution
        debug("approx %.2f MIDI beats" % approxBeats)
        beatsPerSec = 60.0 / self.tempo
        approxDuration = approxBeats * beatsPerSec
        debug("approx duration: %.2f seconds" % approxDuration)
        estimatedFrames = approxDuration * self.fps
        progress("SYNC: ly2video will generate approx. %d frames at %.3f frames/sec." %
                 (estimatedFrames, self.fps))

    def write(self, indices, notesImage):
        """
        Params:
          - indices:     indices of notes in pictures
          - notesImage:  filename of the image
        """
        # folder to store frames for video
        if not os.path.exists("notes"):
            os.mkdir("notes")

        firstTempoTick, self.tempo = self.temposList[self.tempoIndex]
        debug("first tempo is %.3f bpm" % self.tempo)
        debug("final MIDI tick is %d" % self.midiTicks[-1])

        notesPic = Image.open(notesImage)
        cropTop, cropBottom = self.getCropTopAndBottom(notesPic)

        # duplicate last index
        indices.append(indices[-1])

        self.estimateFrames()
        progress("Writing frames ...")
        if not DEBUG:
            progress("A dot is displayed for every 10 frames generated.")

        initialTick = self.midiTicks[self.midiIndex]
        if initialTick > 0:
            debug("\ncalculating wall-clock start for first audible MIDI event")
            # This duration isn't used, but it's necessary to
            # calculate it like this in order to ensure tempoIndex is
            # correct before we start writing frames.
            silentPreludeDuration = \
                self.secsElapsedForTempoChanges(0, initialTick,
                                                0, indices[0])

        # generate all frames in between each pair of adjacent indices
        for i in xrange(len(indices) - 1):
            # get two indices of notes (pixels)
            startIndex  = indices[i]
            endIndex    = indices[i + 1]
            indexTravel = endIndex - startIndex

            debug("\nwall-clock secs: %f" % self.secs)
            debug("index: %d -> %d (indexTravel %d)" %
                  (startIndex, endIndex, indexTravel))

            # get two indices of MIDI events (ticks)
            startTick = self.midiTicks[self.midiIndex]
            self.midiIndex += 1
            endTick = self.midiTicks[self.midiIndex]
            ticks = endTick - startTick
            debug("ticks: %d -> %d (%d)" % (startTick, endTick, ticks))

            # If we have 1+ tempo changes in between adjacent indices,
            # we need to keep track of how many seconds elapsed since
            # the last one, since this will allow us to calculate how
            # many frames we need in between the current pair of
            # indices.
            secsSinceIndex = \
                self.secsElapsedForTempoChanges(startTick, endTick,
                                                startIndex, endIndex)

            # This is the exact time we are *aiming* for the frameset
            # to finish at (i.e. the start time of the first frame
            # generated after the writeVideoFrames() invocation below
            # has written all the frames for the current frameset).
            # However, since we have less than an infinite number of
            # frames per second, there will typically be a rounding
            # error and we'll miss our target by a small amount.
            targetSecs = self.secs + secsSinceIndex

            debug("    secs at new index %d: %f" %
                  (endIndex, targetSecs))

            # The ideal duration of the current frameset is the target
            # end time minus the *actual* start time, not the ideal
            # start time.  This is crucially important to avoid
            # rounding errors from accumulating over the course of the
            # video.
            neededFrameSetSecs = targetSecs - float(self.frameNum)/self.fps
            debug("    need next frameset to last %f secs" %
                  neededFrameSetSecs)

            debug("    need %f frames @ %.3f fps" %
                  (neededFrameSetSecs * self.fps, self.fps))
            neededFrames = int(round(neededFrameSetSecs * self.fps))

            if neededFrames > 0:
                self.writeVideoFrames(
                    neededFrames, startIndex, indexTravel,
                    notesPic, cropTop, cropBottom)

            # Update time in the *ideal* (i.e. not real) world - this
            # is totally independent of fps.
            self.secs = targetSecs

        print

        progress("SYNC: Generated %d frames" % self.frameNum)

    def getCropTopAndBottom(self, image):
        """
        Returns a tuple containing the y-coordinates of the top and
        bottom edges of the cropping rectangle, relative to the given
        (non-cropped) image.
        """
        width, height = image.size

        topMarginSize, bottomMarginSize = self.getTopAndBottomMarginSizes(image)
        bottomY = height - bottomMarginSize
        progress("      Image height: %5d pixels" % height)
        progress("   Top margin size: %5d pixels" % topMarginSize)
        progress("Bottom margin size: %5d pixels (y=%d)" %
                 (bottomMarginSize, bottomY))

        nonWhiteRows = height - topMarginSize - bottomMarginSize
        progress("Visible content is formed of %d non-white rows of pixels" %
                 nonWhiteRows)

        # y-coordinate of centre of the visible content, relative to
        # the original non-cropped image
        nonWhiteCentre = topMarginSize + int(round(nonWhiteRows/2))
        progress("Centre of visible content is %d pixels from top" %
                 nonWhiteCentre)

        # Now choose top/bottom cropping coordinates which center
        # the content in the video frame.
        cropTop    = nonWhiteCentre - int(round(self.height / 2))
        cropBottom = cropTop + self.height

        # Figure out the maximum height allowed which keeps the
        # cropping rectangle within the source image.
        maxTopHalf    =    topMarginSize + nonWhiteRows / 2
        maxBottomHalf = bottomMarginSize + nonWhiteRows / 2
        maxHeight = min(maxTopHalf, maxBottomHalf) * 2

        if cropTop < 0:
            fatal("Would have to crop %d pixels above top of image! "
                  "Try increasing the resolution DPI "
                  "(which would increase the size of the PNG to be cropped), "
                  "or reducing the video height to at most %d" %
                  (-cropTop, maxHeight))
            cropTop = 0

        if cropBottom > height:
            fatal("Would have to crop %d pixels below bottom of image! "
                  "Try increasing the resolution DPI "
                  "(which would increase the size of the PNG to be cropped), "
                  "or reducing the video height to at most %d" %
                  (cropBottom - height, maxHeight))
            cropBottom = height

        if cropTop > topMarginSize:
            fatal("Would have to crop %d pixels below top of visible content! "
                  "Try increasing the video height to at least %d, "
                  "or decreasing the resolution DPI."
                  % (cropTop - topMarginSize, nonWhiteRows))
            cropTop = topMarginSize

        if cropBottom < bottomY:
            fatal("Would have to crop %d pixels above bottom of visible content! "
                  "Try increasing the video height to at least %d, "
                  "or decreasing the resolution DPI."
                  % (bottomY - cropBottom, nonWhiteRows))
            cropBottom = bottomY

        progress("Will crop from y=%d to y=%d" % (cropTop, cropBottom))

        return cropTop, cropBottom

    def getTopAndBottomMarginSizes(self, image):
        """
        Counts the number of white-only rows of pixels at the top and
        bottom of the given image.
        """

        width, height = image.size

        # This is way faster than width*height invocations of getPixel()
        pixels = image.load()

        progress("Auto-detecting top margin; this may take a while ...")
        topMargin = 0
        for y in xrange(height):
            if self.isLineBlank(pixels, width, y):
                topMargin += 1
                if topMargin % 10 == 0:
                    sys.stdout.write(".")
                    sys.stdout.flush()
            else:
                break
        if topMargin >= 10:
            print

        progress("Auto-detecting bottom margin; this may take a while ...")
        bottomMargin = 0
        for y in xrange(height - 1, -1, -1):
            if self.isLineBlank(pixels, width, y):
                bottomMargin += 1
                if bottomMargin % 10 == 0:
                    sys.stdout.write(".")
                    sys.stdout.flush()
            else:
                break
        if bottomMargin >= 10:
            print

        bottomY = height - bottomMargin
        if topMargin >= bottomY:
            bug("Image was entirely white!\n"
                "Top margin %d, bottom margin %d (y=%d), height %d" %
                (topMargin, bottomMargin, bottomY, height))

        return topMargin, bottomMargin

    def isLineBlank(self, pixels, width, y):
        """
        Returns True iff the line with the given y coordinate
        is entirely white.
        """
        for x in xrange(width):
            if pixels[x, y] != (255, 255, 255):
                return False
        return True

    def secsElapsedForTempoChanges(self, startTick, endTick,
                                   startIndex, endIndex):
        """
        Returns the time elapsed in between startTick and endTick,
        where the only MIDI events in between (if any) are tempo
        change events.
        """
        secsSinceStartIndex = 0.0
        lastTick = startTick
        while self.tempoIndex < len(self.temposList):
            tempoTick, tempo = self.temposList[self.tempoIndex]
            debug("    checking tempo #%d @ tick %d: %.3f bpm" %
                  (self.tempoIndex, tempoTick, tempo))
            if tempoTick >= endTick:
                break

            self.tempoIndex += 1
            self.tempo = tempo

            if tempoTick == startTick:
                continue

            # startTick < tempoTick < endTick
            secsSinceStartIndex += self.ticksToSecs(lastTick, tempoTick)
            debug("        last %d tempo %d" % (lastTick, tempoTick))
            debug("        secs since index %d: %f" %
                  (startIndex, secsSinceStartIndex))
            lastTick = tempoTick

        # Add on the time elapsed between the final tempo change
        # and endTick:
        secsSinceStartIndex += self.ticksToSecs(lastTick, endTick)

        debug("    secs between indices %d and %d: %f" %
              (startIndex, endIndex, secsSinceStartIndex))
        return secsSinceStartIndex

    def writeVideoFrames(self, neededFrames, startIndex, indexTravel,
                         notesPic, cropTop, cropBottom):
        """
        Writes the required number of frames to travel indexTravel
        pixels from startIndex, incrementing frameNum for each frame
        written.
        """
        travelPerFrame = float(indexTravel) / neededFrames
        debug("    travel per frame: %f pixels" % travelPerFrame)
        debug("    generating %d frames: %d -> %d" %
              (neededFrames, self.frameNum, self.frameNum + neededFrames - 1))

        for i in xrange(neededFrames):
            index = startIndex + int(round(i * travelPerFrame))
            debug("        writing frame %d index %d" %
                  (self.frameNum, index))

            frame, cursorX = self.cropFrame(notesPic, index,
                                            cropTop, cropBottom)
            self.writeCursorLine(frame, cursorX)

            # Save the frame.  ffmpeg doesn't work if the numbers in these
            # filenames are zero-padded.
            frame.save(tmpPath("notes", "frame%d.png" % self.frameNum))
            self.frameNum += 1
            if not DEBUG and self.frameNum % 10 == 0:
                sys.stdout.write(".")
                sys.stdout.flush()

    def cropFrame(self, notesPic, index, top, bottom):
        if self.scrollNotes:
            # Get frame from image of staff
            centre = self.width / 2
            left  = int(index - centre)
            right = int(index + centre)
            frame = notesPic.copy().crop((left, top, right, bottom))
            cursorX = centre
        else:
            if self.leftEdge is None:
                # first frame
                staffX, staffYs = findStaffLinesInImage(notesPic, 50)
                self.leftEdge = staffX - self.leftMargin

            cursorX = index - self.leftEdge
            debug("        left edge at %d, cursor at %d" %
                  (self.leftEdge, cursorX))
            if cursorX > self.width - self.rightMargin:
                self.leftEdge = index - self.leftMargin
                cursorX = index - self.leftEdge
                debug("        <<< left edge at %d, cursor at %d" %
                      (self.leftEdge, cursorX))

            rightEdge = self.leftEdge + self.width
            frame = notesPic.copy().crop((self.leftEdge, top,
                                          rightEdge, bottom))
        return frame, cursorX

    def writeCursorLine(self, frame, x):
        for pixel in xrange(self.height):
            frame.putpixel((x    , pixel), self.cursorLineColor)
            frame.putpixel((x + 1, pixel), self.cursorLineColor)

    def ticksToSecs(self, startTick, endTick):
        beatsSinceTick = float(endTick - startTick) / self.midiResolution
        debug("        beats from tick %d -> %d: %f (%d ticks per beat)" %
              (startTick, endTick, beatsSinceTick, self.midiResolution))

        secsSinceTick = beatsSinceTick * 60.0 / self.tempo
        debug("        secs  from tick %d -> %d: %f (%.3f bpm)" %
              (startTick, endTick, secsSinceTick, self.tempo))

        return secsSinceTick

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
    Subchunk2Size = int(length * sample * channels * bps/8)
    ChunkSize = 4 + (8 + Subchunk1Size) + (8 + Subchunk2Size)

    outdir = tmpPath("silence")
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    out = os.path.join(outdir, name + '.wav')

    fSilence = open(out, "w")

    fSilence.write("".join([
        'RIFF',                                # ChunkID (magic)      # 0x00
        pack('<I', ChunkSize),                 # ChunkSize            # 0x04
        'WAVE',                                # Format               # 0x08
        'fmt ',                                # Subchunk1ID          # 0x0c
        pack('<I', Subchunk1Size),             # Subchunk1Size        # 0x10
        pack('<H', 1),                         # AudioFormat (1=PCM)  # 0x14
        pack('<H', channels),                  # NumChannels          # 0x16
        pack('<I', sample),                    # SampleRate           # 0x18
        pack('<I', bps/8 * channels * sample), # ByteRate             # 0x1c
        pack('<H', bps/8 * channels),          # BlockAlign           # 0x20
        pack('<H', bps),                       # BitsPerSample        # 0x22
        pack('<H', ExtraParamSize),            # ExtraParamSize       # 0x22
        'data',                                # Subchunk2ID          # 0x24
        pack('<I', Subchunk2Size),             # Subchunk2Size        # 0x28
        '\0'*Subchunk2Size
    ]))
    fSilence.close()
    return out

def output_divider_line():
    progress(60 * "-")

def debug(text):
    if DEBUG:
        print text

def progress(text):
    print text

def stderr(text):
    sys.stderr.write(text + "\n")

def warn(text):
    stderr("WARNING: " + text)

def fatal(text, status=1):
    output_divider_line()
    stderr("ERROR: " + text)
    sys.exit(status)

def bug(text, *issues):
    if len(issues) == 0:
        msg = """
Sorry, ly2video has encountered a fatal bug as described above,
which it could not attribute to any known cause :-( 

Please consider searching:
        """
    else:
        msg = """
Sorry, ly2video has encountered a fatal bug as described above :-(
It might be due to the following known issue(s):

"""
        for issue in issues:
            msg += "    https://github.com/aspiers/ly2video/issues/%d\n" % issue

        msg += """
If you suspect this is not the case, please visit:
"""

    msg += """
    https://github.com/aspiers/ly2video/issues

and if the problem is not listed there, please file a new
entry so we can get it fixed.  Thanks!

Aborted execution.\
"""
    fatal(text + "\n" + msg)

def tmpPath(*dirs):
    segments = [ 'ly2video.tmp' ]
    segments.extend(dirs)
    return os.path.join(runDir, *segments)

def parseOptions():
    parser = OptionParser("usage: %prog [options]")

    parser.add_option("-i", "--input", dest="input",
                      help="input LilyPond file", metavar="INPUT-FILE")
    parser.add_option("-o", "--output", dest="output",
                      help='name of output video (e.g. "myNotes.avi") '
                           '[INPUT-FILE.avi]',
                      metavar="OUTPUT-FILE")
    parser.add_option("-b", "--beatmap", dest="beatmap",
                      help='name of beatmap file for adjusting MIDI tempo',
                      metavar="FILE")
    parser.add_option("-c", "--color", dest="color",
                      help='name of color of middle bar [red]',
                      metavar="COLOR", default="red")
    parser.add_option("-f", "--fps", dest="fps",
                      help='frame rate of final video [30]',
                      type="float", metavar="FPS", default=30.0)
    parser.add_option("-q", "--quality", dest="quality",
                      help="video encoding quality as used by ffmpeg's -q option "
                           '(1 is best, 31 is worst) [10]',
                      type="int", metavar="N", default=10)
    parser.add_option("-r", "--resolution", dest="dpi",
                      help='resolution in DPI [110]',
                      metavar="DPI", type="int", default=110)
    parser.add_option("-x", "--width", dest="width",
                      help='pixel width of final video [1280]',
                      metavar="WIDTH", type="int", default=1280)
    parser.add_option("-y", "--height", dest="height",
                      help='pixel height of final video [720]',
                      metavar="HEIGHT", type="int", default=720)
    parser.add_option("-m", "--cursor-margins", dest="cursorMargins",
                      help='width of left/right margins for scrolling '
                           'in pixels [50,100]',
                      metavar="WIDTH,WIDTH", type="string", default='50,100')
    parser.add_option("-s", "--scroll-notes", dest="scrollNotes",
                      help='rather than scrolling the cursor from left to right, '
                           'scroll the notation from right to left and keep the '
                           'cursor in the centre',
                      action="store_true", default=False)
    parser.add_option("-t", "--title-at-start", dest="titleAtStart",
                      help='adds title screen at the start of video '
                           '(with name of song and its author)',
                      action="store_true", default=False)
    parser.add_option("--title-duration", dest="titleDuration",
                      help='time to display the title screen [3]',
                      type="int", metavar="SECONDS", default=3)
    parser.add_option("--ttf", "--title-ttf", dest="titleTtfFile",
                      help='path to TTF font file to use in title',
                      type="string", metavar="FONT-FILE")
    parser.add_option("--windows-ffmpeg", dest="winFfmpeg",
                      help='(for Windows users) folder with ffpeg.exe '
                           '(e.g. "C:\\ffmpeg\\bin\\")',
                      metavar="PATH", default="")
    parser.add_option("--windows-timidity", dest="winTimidity",
                      help='(for Windows users) folder with '
                           'timidity.exe (e.g. "C:\\timidity\\")',
                      metavar="PATH", default="")
    parser.add_option("-d", "--debug", dest="debug",
                      help="enable debugging mode",
                      action="store_true", default=False)
    parser.add_option("-k", "--keep", dest="keepTempFiles",
                      help="don't remove temporary working files",
                      action="store_true", default=False)
    parser.add_option("-v", "--version", dest="showVersion",
                      help="show program version",
                      action="store_true", default=False)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    options, args = parser.parse_args()

    if options.showVersion:
        showVersion()

    if options.titleAtStart and options.titleTtfFile is None:
        fatal("Must specify --title-ttf=FONT-FILE with --title-at-start.")

    if options.debug:
        global DEBUG
        DEBUG = True

    return options, args

def getVersion():
    try:
        stdout = subprocess.check_output([ "git", "describe", "--tags" ],
                                         cwd=os.path.dirname(__file__))
        m = re.match('^(v\d\S+)', stdout)
        if m:
            return m.group(1)
    except:
        #exc_type, exc_value, exc_traceback = sys.exc_info()
        #print "%s: %s" % (exc_type.__name__, exc_value)
        pass

    return VERSION

def showVersion():
    print """ly2video %s

Copyright (C) 2012 Jiri "FireTight" Szabo, Adam Spiers
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.""" % getVersion()
    sys.exit(0)

def portableDevNull():
    if sys.platform.startswith("linux"):
        return "/dev/null"
    elif sys.platform.startswith("win"):
        return "NUL"

def applyBeatmap(src, dst, beatmap):
    prog = "midi-rubato"
    cmd = [prog, src, dst, beatmap]
    progress("Applying beatmap via '%s'" % " ".join(cmd))
    debug(safeRun(cmd))

def safeRun(cmd, errormsg=None, exitcode=None, shell=False, issues=[]):
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

    return stdout

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
              "infinitely long lines.  Please upgrade to >= 2.15.41." % version)

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
        return (0,0,0)
    elif options.color == "yellow":
        return (255,255,0)
    elif options.color == "red":
        return (255,0,0)
    elif options.color == "green":
        return (0,128,0)
    elif options.color == "blue":
        return (0,0,255)
    elif options.color == "brown":
        return (165,42,42)
    else:
        warn("Color was not found, ly2video will use default one ('red').")
        return (255,0,0)

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

def generateStaticVideoFrames(name, frames):
    outdir = tmpPath(name)
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    srcFrame = tmpPath("%s.png" % name)

    for i in xrange(frames):
        os.symlink(srcFrame, os.path.join(outdir, "frame%d.png" % i))

    progress("Generated %d frames in %s/ from %s" % (frames, outdir, srcFrame))

def callFfmpeg(ffmpeg, options, wavPath, outputFile):
    fps = str(options.fps)
    framePath = tmpPath('notes', 'frame%d.png')

    if not options.titleAtStart:
        cmd = [
            ffmpeg,
            "-f", "image2",
            "-r", fps,
            "-i", framePath,
            "-i", wavPath,
            "-q:v", str(options.quality),
            outputFile
        ]
        safeRun(cmd, exitcode=13, issues=[32])
    else:
        # generate silent title video
        silentAudio    = generateSilence('title', options.titleDuration)
        titleFramePath = tmpPath('title', 'frame%d.png')
        titlePath      = tmpPath('title.mpg')
        cmd = [
            ffmpeg,
            "-f", "image2",
            "-r", fps,
            "-i", titleFramePath,
            "-i", silentAudio,
            "-q:v", str(options.quality),
            titlePath
        ]
        safeRun(cmd, exitcode=14)

        # generate video with notes
        notesPath = tmpPath("notes.mpg")
        cmd = [
            ffmpeg,
            "-f", "image2",
            "-r", fps,
            "-i", framePath,
            "-i", wavPath,
            "-q:v", str(options.quality),
            notesPath
        ]
        safeRun(cmd, exitcode=15)

        # join the files
        joinedPath = tmpPath('joined.mpg')
        if sys.platform.startswith("linux"):
            safeRun("cat '%s' '%s' > '%s'" % (titlePath, notesPath, joinedPath), shell=True)
        elif sys.platform.startswith("win"):
            os.system('copy "%s" /B + "%s" /B "%s" /B' % (titlePath, notesPath, joinedPath))

        # create output file
        cmd = [
            ffmpeg,
            "-i", joinedPath,
            "-q:v", str(options.quality),
            outputFile
        ]
        safeRun(cmd, exitcode=16)

def getLyVersion(fileName):
    # if I don't have input file, end
    if fileName == None:
        fatal("LilyPond input file was not specified.", 4)
    else:
        # otherwise try to open fileName
        try:
            fLyFile = open(fileName, "r")
        except IOError:
            fatal("Couldn't read %s" % fileName, 5)

    # find version of LilyPond in .ly input file
    version = ""
    for line in fLyFile.readlines():
        if line.find("\\version") != -1:
            parser = Tokenizer()
            for token in parser.tokens(line):
                if token.__class__.__name__ == "StringQuoted":
                    version = str(token)[1:-1]
                    break
            if version != "":
                break
    fLyFile.close()

    return version

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
    f = open(tmpPath(filename), 'w')
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
         (pitch        (ly:event-property cause 'pitch))
         (midi-pitch   (if (ly:pitch? pitch) (+ 0.0 (ly:pitch-tones pitch)) "no pitch")))
   (if (not (equal? (ly:grob-property grob 'transparent) #t))
    (format #t "\\nly2video: (~23,16f, ~23,16f) @ ~23,16f from ~a:~3d:~d"
                left right
                (+ 0.0 (ly:moment-main time) (* (ly:moment-grace time) (/ 9 40)))
                file line char))))

\layout {
  \context {
    \Voice
    \override NoteHead  #'after-line-breaking = #dump-spacetime-info
  }
  \context {
    \ChordNames
    \override ChordName #'after-line-breaking = #dump-spacetime-info
  }
}
''')
    f.close()
    return '\\include "%s"\n' % filename

def sanitiseLy(lyFile, dumper, width, height, dpi, numStaffLines,
               titleText, lilypondVersion):
    fLyFile = open(lyFile, "r")

    sanitisedLyFileName = tmpPath("sanitised.ly")

    # create own ly lyFile
    fSanitisedLyFile = open(sanitisedLyFileName, "w")

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
            leftPaperMarginPx = writePaperHeader(fSanitisedLyFile, dpi,
                                                 numStaffLines, lilypondVersion)
            paperBlock = True

        # get needed info from header block and ignore it
        elif (line.find("\\header") != -1 or headerPart):
            if line.find("\\header") != -1:
                fSanitisedLyFile.write("\\header {\n   tagline = ##f composer = ##f\n}\n")
                headerPart = True

            if re.search("title\\s*=", line):
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
                finalLine = (line[:line.find("\\pageBreak")]
                             + line[line.find("\\pageBreak") + len("\\pageBreak"):])
            else:
                finalLine = line

            fSanitisedLyFile.write(finalLine)

        line = fLyFile.readline()

    fLyFile.close()

    # if I didn't find \version, write own paper block
    if not paperBlock:
        leftPaperMarginPx = writePaperHeader(fSanitisedLyFile,
                                             numStaffLines, lilypondVersion)

    fSanitisedLyFile.close()
    progress("Wrote sanitised version of %s into %s" % (lyFile, sanitisedLyFileName))

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
    (options, args) = parseOptions()

    lilypondVersion, ffmpeg, timidity = findExecutableDependencies(options)

    # FIXME.  Ugh, eventually this will be an instance method, and
    # we'll have somewhere nice to save state.
    global runDir
    runDir = os.getcwd()

    # Delete old temporary files.
    if os.path.isdir(tmpPath()):
        shutil.rmtree(tmpPath())
    os.mkdir(tmpPath())

    # .ly input file from user (string)
    lyFile = options.input

    dumper = writeSpaceTimeDumper()

    # If the input .ly doesn't match the currently installed LilyPond
    # version, try to convert it
    lyFile = preprocessLyFile(lyFile, lilypondVersion, dumper)

    numStaffLines = getNumStaffLines(lyFile, options.dpi)

    titleText = collections.namedtuple("titleText", "name author")
    titleText.name = "<name of song>"
    titleText.author = "<author>"

    sanitisedLyFileName, leftPaperMargin = \
        sanitiseLy(lyFile, dumper,
                   options.width, options.height, options.dpi,
                   numStaffLines, titleText, lilypondVersion)

    output = runLilyPond(sanitisedLyFileName, options.dpi)
    leftmostGrobsByMoment = getLeftmostGrobsByMoment(output, options.dpi,
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

    # generate title screen
    if options.titleAtStart:
        generateTitle(titleText, options.width, options.height,
                      options.titleTtfFile, fps, options.titleDuration)
        output_divider_line()

    # generate notes
    leftMargin, rightMargin = options.cursorMargins.split(",")
    frameWriter = VideoFrameWriter(
        options.width, options.height, fps, getCursorLineColor(options),
        options.scrollNotes, int(leftMargin), int(rightMargin),
        midiResolution, midiTicks, temposList)
    frameWriter.write(noteIndices, notesImage)

    output_divider_line()

    wavPath = genWavFile(timidity, midiPath)

    output_divider_line()

    outputFile = getOutputFile(options)
    callFfmpeg(ffmpeg, options, wavPath, outputFile)

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
