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

VERSION = '0.3.1'

import collections
import copy
import os
import re
import shutil
import subprocess
import sys
import urllib
from distutils.version import StrictVersion
from optparse import OptionParser
from struct import pack

from PIL import Image, ImageDraw, ImageFont
from ly.tokenize import MusicTokenizer, Tokenizer
import ly.tools
from pyPdf import PdfFileWriter, PdfFileReader
import midi

from pprint import pprint, pformat

DEBUG = False # --debug sets to True

C_MAJOR_SCALE_STEPS = {
    # Maps notes of the C major scale into semi-tones above C.
    # This is needed to map the pitch of ly.tools.Pitch notes
    # into MIDI pitch values within a given octave.
    0 :  0, # c
    1 :  2, # d
    2 :  4, # e
    3 :  5, # f
    4 :  7, # g
    5 :  9, # a
    6 : 11, # b
}

def getLyLines(fileName):
    fLyFile = open(fileName, "r")
    lySrcLines = [ line for line in fLyFile.readlines() ]
    fLyFile.close()
    return lySrcLines

def preprocessLyFile(lyFile):
    version = getLyVersion(lyFile)
    progress("Version in %s: %s" % (lyFile, version if version else "unspecified"))
    if version and version != "2.14.2":
        newLyFile = tmpPath('converted.ly')
        if os.system("convert-ly '%s' > '%s'" % (lyFile, newLyFile)) == 0:
            return newLyFile
        else:
            warn("Convert of input file has failed. " +
                 "This could cause some problems.")

    newLyFile = tmpPath('unconverted.ly')
    shutil.copy(lyFile, newLyFile)
    debug("new ly file is " + newLyFile)
    output_divider_line()

    return newLyFile

def runLilyPond(lyFileName, dpi, *args):
    progress("Generating PDF, PNG and MIDI files ...")
    cmd = [
        "lilypond",
        "-fpdf",
        "--png",
        "-I", runDir,
        "-dpoint-and-click",
        "-dmidi-extension=midi",
        "-dresolution=%d" % dpi
    ] + list(args) + [ lyFileName ]
    output_divider_line()
    os.chdir(tmpPath())
    output = safeRun(cmd, exitcode=9)
    output_divider_line()
    progress("Generated PDF, PNG and MIDI files")
    return output

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

def generateTitle(titleText, width, height, fps, titleLength):
    """
    Generates frames with name of song and its author.

    Params:
    - titleText:    collection of name of song and its author
    - width:        pixel width of frames (and video)
    - height        pixel height of frames (and video)
    - fps:          frame rate (frames per second) of final video
    - titleLength:  length of title screen (seconds)
    """

    # create image of title screen
    titleScreen = Image.new("RGB", (width, height), (255,255,255))
    # it will draw text on titleScreen
    drawer = ImageDraw.Draw(titleScreen)
    # save folder for frames
    if not os.path.exists("title"):
        os.mkdir("title")

    totalFrames = int(round(fps * titleLength))
    progress("TITLE: ly2video will generate approx. %d frames." % totalFrames)

    # font for song's name, args - font type, size
    nameFont = ImageFont.truetype("arial.ttf", height / 15)
    # font for author
    authorFont = ImageFont.truetype("arial.ttf", height / 25)

    # args - position of left upper corner of rectangle (around text), text, font and color (black)
    drawer.text(((width - nameFont.getsize(titleText.name)[0]) / 2,
                 (height - nameFont.getsize(titleText.name)[1]) / 2 - height / 25),
                titleText.name, font=nameFont, fill=(0,0,0))
    # same thing
    drawer.text(((width - authorFont.getsize(titleText.author)[0]) / 2,
                 (height / 2) + height / 25),
                titleText.author, font=authorFont, fill=(0,0,0))

    # generate needed number of frames (= fps * titleLength)
    for frameNum in xrange(totalFrames):
        titleScreen.save(tmpPath("title", "frame%d.png" % frameNum))

    progress("TITLE: Generating title screen has ended. (%d/%d)" %
             (totalFrames, totalFrames))
    return 0

def writePaperHeader(fFile, width, height, dpi, numOfLines, lilypondVersion):
    """
    Writes own paper block into given file.

    Params:
    - fFile:        given opened file
    - width:        pixel width of frames (and video)
    - height        pixel height of frames (and video)
    - numOfLines:   number of staff lines
    """
    inchesPerPixel = 1.0 / dpi
    mmPerPixel = inchesPerPixel * 25.4

    fFile.write("\\paper {\n")

    # one-line-breaking is available as of 2.15.41:
    #   https://code.google.com/p/lilypond/issues/detail?id=2570
    #   https://codereview.appspot.com/6248056/
    #   http://article.gmane.org/gmane.comp.gnu.lilypond.general/72373/
    oneLineBreaking = False
    if StrictVersion(lilypondVersion) >= StrictVersion('2.15.41'):
        oneLineBreaking = True
    else:
        warn("""You have LilyPond %s which does not support
infinitely long lines.  Upgrade to >= 2.15.41 to avoid
sudden jumps in your video.
""" % lilypondVersion)

    if oneLineBreaking:
        fFile.write("   page-breaking = #ly:one-line-breaking\n")
    else:
        fFile.write("   paper-width   = %d\\mm\n" % round(10 * width * mmPerPixel))
        fFile.write("   paper-height  = %d\\mm\n" % round(height * mmPerPixel))

    fFile.write("   top-margin    = %d\\mm\n" % round(height * mmPerPixel / 5))
    fFile.write("   bottom-margin = %d\\mm\n" % round(height * mmPerPixel / 5))
    fFile.write("   left-margin   = %d\\mm\n" % round(width * mmPerPixel / 2))
    fFile.write("   right-margin  = %d\\mm\n" % round(width * mmPerPixel / 2))

    if not oneLineBreaking:
        fFile.write("   print-page-number = ##f\n")

    fFile.write("}\n")

    return 0

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
            debug("tick %d: tempo change to %.3f bpm" % (event.tick, event.bpm))
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
                    fatal("found orphaned pitch bend in tick %d" %
                          pendingPitchBend.tick)
                if not isinstance(event, midi.NoteOnEvent):
                    fatal("pitch bend was not followed by NoteOn in tick %d" %
                          tick)
                if event.get_velocity() == 0:
                    fatal("pitch bend was followed by NoteOff")

            if isinstance(event, midi.PitchWheelEvent):
                bend = event.get_pitch()
                debug("    tick %d: read %s(%d)" %
                      (tick, eventClass, bend))
                if bend != 0:
                    pendingPitchBend = event
                continue
            elif isinstance(event, midi.NoteOnEvent):
                if event.get_velocity() == 0:
                    # velocity is zero (that's basically "NoteOffEvent")
                    debug("    tick %d: read NoteOffEvent(%d)" %
                          (tick, event.get_pitch()))
                    continue
                else:
                    if pendingPitchBend:
                        pitchBends[event] = pendingPitchBend
                        pendingPitchBend = None
                    debug("    tick %d: read %s(%d)" %
                          (tick, eventClass, event.get_pitch()))
            else:
                debug("    tick %d: read %s - skipping" %
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

def getNotePositions(pdfFileName, lySrcFileName, lySrcLines):
    """
    For every link annotation in the PDF file which is a link to the
    sanitised .ly file we generated, store the coordinates of the
    annotated rectangle and also the line and column number it points
    to in the .ly file.

    Parameters:
      - pdfFileName
      - lySrcLines: loaded *.ly file in memory (list)

    Returns:
      - notesAndTies: a sorted list of (lineNum, charNum) tuples
        containing the locations of notes and ties in the .ly file
      - notePositionsByPage: a list with each top-level item
        representing a page, where each page is a sorted list of
        ((lineNum, charNum), coords) tuples.  coords is (x1,y1,x2,y2)
        representing opposite corners of the rectangle.
      - tokens: a dict mapping every (lineNum, charNum) tuple to the
        token found at that point in the .ly source.  This will be used
        to compare notes in the source with notes in the MIDI
      - parser: the MusicTokenizer() object which can be reused for
        pitch calculations
      - pageWidth: the width of the first PDF page in PDF units (all
        pages are assumed to have the same width)
    """

    # open PDF file with external library and gets width of page (in PDF measures)
    fPdf = file(pdfFileName, "rb")
    pdfFile = PdfFileReader(fPdf)
    numPages = pdfFile.getNumPages()
    progress("PDF file %s has %d page(s)" % (pdfFileName, numPages))
    pageWidth = pdfFile.getPage(0).getObject()['/MediaBox'][2]
    progress("Width of first PDF page is %f" % pageWidth)

    notesAndTies = set()
    notePositionsByPage = []
    tokens = {}

    # ly parser (from Frescobaldi)
    lySrc = ''.join(lySrcLines)
    parser = MusicTokenizer()
    language, keyPitch = ly.tools.languageAndKey(lySrc)
    progress('Detected language in %s as %s' % (lySrcFileName, language))
    parser.language = language
    absolutePitches = ly.tools.relativeToAbsolute(lySrc)

    output_divider_line()

    progress(("Extracting annotation positions from:\n    %s\n" +
              "and corresponding source positions in:\n    %s") %
             (pdfFileName, lySrcFileName))

    escapedLySrcFileName = urllib.quote(lySrcFileName)

    for pageNumber in xrange(numPages):
        # get informations about page
        page = pdfFile.getPage(pageNumber)
        info = page.getObject()

        if not info.has_key('/Annots'):
            continue

        links = info['/Annots']

        # stores wanted positions on single page
        notePositionsInPage = []

        for link in links:
            # Get (x1, y1, x2, y2) coordinates of opposite corners
            # of the annotated rectangle
            coords = link.getObject()['/Rect']
            # if it's not link into .ly, then ignore it
            uri = link.getObject()['/A']['/URI']
            if uri.find(escapedLySrcFileName) == -1:
                continue
            # otherwise get coordinates into .ly file
            lineNum, charNum, columnNum = uri.split(":")[-3:]
            lineNum   = int(lineNum)   # counting from 1
            charNum   = int(charNum)   # the start of the text,
                                       # counting from 0
            columnNum = int(columnNum) # the end of the text?
            srcLine = lySrcLines[lineNum - 1]

            # get name of note
            token = parser.tokens(srcLine[charNum:]).next()
            debug("PDF links to token '%s' at %d:%d" % (token, lineNum, charNum))

            # Is the note immediately followed by \rest?  If so,
            # it's actually a rest not a note:
            # http://lilypond.org/doc/v2.14/Documentation/notation/writing-rests
            # We default to assuming it's a note, in case there
            # isn't any other note to the right of it.
            isNote = True

            restOfLine = srcLine[charNum + len(token):]
            for rightToken in parser.tokens(restOfLine):
                # if there is another note (or rest etc.) to the
                # right of it, it's a real note
                if isinstance(rightToken, MusicTokenizer.Pitch):
                    break
                # if \rest appears after it and before the next
                # note, it's a rest not a note, so we ignore it
                elif isinstance(rightToken, Tokenizer.Command) and \
                     rightToken == '\\rest':
                    isNote = False
                    break

            # If the note is not followed by \rest, and it's a
            # note rather than an "r"-style rest or it's a tie, we
            # keep track of it.  In the next phase,
            # getFilteredIndices() will filter out notes to the
            # right of ties.
            if isNote:
                isNote = isinstance(token, MusicTokenizer.Pitch) and \
                         str(token) not in "rR"
                # Note "a-2~b" will rest in two Unparsed tokens: "-2~"
                # and "~", but we don't want to count both.  Also, a
                # tie token could contain other artifacts, e.g. "~["
                # or "~]".  So we have to be careful about how we do
                # the comparison.
                if isNote or token[0] == '~':
                    # add it
                    sourceCoords = (lineNum, charNum)
                    # We make the first value in the tuple the
                    # coordinate of the left side of the box, in order
                    # that the tuples notePositionsInPage will be
                    # sorted primarily left to right in the order they
                    # appear in the PDF, and secondarily by the order
                    # they appear in the source file.  This fixes the
                    # case where tokens in the source file are linked
                    # multiple times from the PDF, which can happen if
                    # they are contained by a
                    #
                    #     myMusic = { ... }
                    #
                    # declaration which is then invoked multiple # times:
                    #
                    #     \myMusic
                    #     ...
                    #     \myMusic
                    notePositionsInPage.append((coords[0], sourceCoords, coords))
                    notesAndTies.add(sourceCoords)
                    tokens[sourceCoords] = \
                        absolutePitch(absolutePitches, token,
                                      lineNum, charNum, parser)
                    debug("    added token '%s' @ %d:%d" % (token, lineNum, charNum))
                elif not isNote:
                    debug("    ! isNote, class %s" % token.__class__)

        if not notePositionsInPage:
            fatal("Didn't find any notes on page; aborting! "
                  "Maybe you got hit by https://github.com/aspiers/ly2video/issues/31 ?")

        # sort wanted positions on that page and add it into whole wanted positions
        notePositionsInPage.sort()
        notePositionsByPage.append(notePositionsInPage)

    # close PDF file
    fPdf.close()

    # create list of notes and ties and sort it
    notesAndTies = list(notesAndTies)
    notesAndTies.sort()
    return notePositionsByPage, notesAndTies, tokens, parser, pageWidth

def absolutePitch(absolutePitches, token, lineNum, charNum, parser):
    absolutePitchText = \
        absolutePitches.newTextForLineColumn(lineNum - 1, charNum)
    if absolutePitchText:
        absolutePitchToken = parser.tokens(absolutePitchText).next()
        debug("    absolute pitch: %s" % absolutePitchToken)
        return absolutePitchToken
    return token

def getFilteredIndices(notePositionsByPage, notesAndTies, lySrcLines, imageWidth, pageWidth):
    """
    Goes through notePositionsByPage, filtering out anything that
    won't generate a MIDI NoteOn event, converting each note's
    coordinate into an index (i.e. the x-coordinate of the center of
    the note in the PNG file which contains it), and merging indices
    which are within +/- 10 pixels of each other.

    Parameters
      - notePositionsByPage: a list with each top-level item
        representing a page, where each page is a sorted list of
        ((lineNum, charNum), coords) tuples.  coords is (x1,y1,x2,y2)
        representing opposite corners of the rectangle.
      - notesAndTies: a sorted list of (lineNum, charNum) tuples
        containing the locations of notes and ties in the .ly file
      - lySrcLines: loaded *.ly file in memory (list)
      - imageWidth: width of PNG file(s)
      - pageWidth: the width of the first PDF page in PDF units (all
        pages are assumed to have the same width)

    Returns:
      - indexNoteSourcesByPage:
            a list of dicts, one per page, mapping each index to a
            list of (lineNum, colNum) tuples in the .ly source file
            corresponding to the notes and/or ties at that index, e.g.
                [
                    # page 1
                    {
                        ...
                        123 : [    # index
                            (37, 2), # note at index 123, line 37 col 2
                            (37, 5), # note at index 123, line 37 col 5
                        ],
                        128 :
                        ...
                    }

                    # page 2
                    {
                        ...
                    }
                ]
      - noteIndicesByPage:
            a list of sorted lists, one per page, containing
            all the indices on that page in order, e.g.
                [
                    # page 1
                    [ 123, 137, 178 ... ],
                    # page 2
                    [ ... ],
                ]
    """
    indexNoteSourcesByPage = []
    noteIndicesByPage = []

    progress("Calculating indices and removing silent notes ...")

    for pageNum, notePositionsInPage in enumerate(notePositionsByPage):
        parser = Tokenizer()
        # co-ordinates in the .ly source of notes, grouped by index
        # (within one page)
        indexNoteSourcesInPage = {}

        # Notes that are preceded by tie and will not generate
        # a MIDI NoteOn event
        silentNotes = []

        for (left, linkLy, coords) in notePositionsInPage: # this is already sorted
            lineNum, charNum = linkLy
            # get that token
            token = parser.tokens(lySrcLines[lineNum - 1][charNum:]).next()
            debug("PDF box (%d, %d, %d, %d) linked to token '%s' @ %d:%d" %
                  tuple(list(coords) + [token, lineNum, charNum]))

            if isinstance(token, MusicTokenizer.PitchWord):
                # It's a note; if it's silent, remove it and ignore it
                if linkLy in silentNotes:
                    silentNotes.remove(linkLy)
                    debug("    removed silent note %s" % token)
                    continue
                # otherwise get its index in pixels
                xcenter = (coords[0] + coords[2]) / 2
                noteIndex = int(round(xcenter * imageWidth / pageWidth))
                # add that index into indices
                if noteIndex not in indexNoteSourcesInPage:
                    indexNoteSourcesInPage[noteIndex] = []
                indexNoteSourcesInPage[noteIndex].append(linkLy)
                debug("    added index %d" % noteIndex)
            # The comments in getNotePositions() about the "~" string
            # comparison apply here too:
            elif token[0] == "~":
                # It's a tie.
                # If next note isn't in silent notes, add it
                nextNoteCoords = notesAndTies[notesAndTies.index(linkLy) + 1]
                if nextNoteCoords not in silentNotes:
                    silentNotes.append(nextNoteCoords)
                    debug("    marked note @ %d:%d as silent" % nextNoteCoords)
                # otherwise add next one (after the last silent one (if it's tie of harmony))
                else:
                    lastSilentSrcIndex = notesAndTies.index(silentNotes[-1])
                    srcIndexAfterLastSilent = lastSilentSrcIndex + 1
                    coordsAfterLastSilent = notesAndTies[srcIndexAfterLastSilent]
                    silentNotes.append(coordsAfterLastSilent)
                    debug("    marked note @ %d:%d after last silent one as silent" %
                          coordsAfterLastSilent)
            else:
                fatal("didn't know what to do with %s" % repr(token))

        noteIndicesInPage = mergeNearbyIndices(indexNoteSourcesInPage)

        # stores info about this page
        indexNoteSourcesByPage.append(indexNoteSourcesInPage)
        noteIndicesByPage.append(noteIndicesInPage)

        progress("PDF: Page %d/%d has been completed." %
                 (pageNum + 1, len(notePositionsByPage)))

    return indexNoteSourcesByPage, noteIndicesByPage

def mergeNearbyIndices(indexNoteSourcesInPage):
    """
    Merges nearby note indices in the given page.  Any within +/- 10
    pixels of each other get merged into a single index.

    Parameters:
      - indexNoteSourcesInPage:
            a dict mapping each index to a list of (lineNum, colNum)
            tuples in the .ly source corresponding to the notes at
            that index within the page, e.g.

                {
                    123 : [    # index
                        (37, 2), # note at index 123, line 37 col 2
                        (37, 5), # note at index 123, line 37 col 5
                    ],
                    ...
                }

    Returns:
      - a sorted list of all indices in the page, post merge

    indexNoteSourcesInPage is also adjusted according to the merging,
    as a side-effect.
    """
    # gets all indices on one page and sort it
    noteIndicesInPage = indexNoteSourcesInPage.keys()
    noteIndicesInPage.sort()

    # merges indices within +/- 10 pixels of each other
    skipNext = False
    for index in noteIndicesInPage[:-1]:
        if skipNext:
            skipNext = False
            continue
        # gets next index
        nextIndex = noteIndicesInPage[noteIndicesInPage.index(index) + 1]
        if index in xrange(nextIndex - 10, nextIndex + 10):
            debug("merging index %d with %d" % (index, nextIndex))
            indexNoteSourcesInPage[index].extend(indexNoteSourcesInPage[nextIndex])
            del indexNoteSourcesInPage[nextIndex]
            noteIndicesInPage.remove(nextIndex)
            skipNext = True

    return noteIndicesInPage

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

def alignIndicesWithTicks(indexNoteSourcesByPage, noteIndicesByPage,
                          tokens, parser,
                          midiTicks, notesInTicks, pitchBends):
    """
    Build a list of note indices (grouped by page) which align with
    the ticks in midiTicks, by sequentially comparing the notes at
    each index in the images with the notes at each tick in the MIDI
    stream.

    If none of the MIDI events are found to have corresponding
    notation (e.g. notes hidden via \hideNotes, and non-root notes
    within a chord), they are skipped and the containing tick is
    removed from midiTicks.

    If only *some* of the MIDI events are found to have corresponding
    notation, a warning is output, but the containing tick is kept.

    If notes are found in the index with no corresponding MIDI event,
    then currently we flag an error.  If this turns out to be a valid
    use case then we can possibly change this behaviour, although I'm
    not sure how the synchronization algorithm could be modified to
    support that, because then if you encountered a tick and index
    with no notes in common between them, which one would you skip?
    Skipping both would probably be too lossy to be acceptable.

    There is probably a bug which will be triggered when a chord
    appears on a beat containing no notated notes, and the next note
    index contains one or more notes in the chord.  In this case, I
    would expect the latter to match the MIDI tick containing the
    chord, which would throw synchronization off.  But chords
    generated by LilyPond in MIDI don't generally sound good due to
    the naive voicing, and so should be turned off:

      https://github.com/aspiers/ly2video/issues/16
      http://article.gmane.org/gmane.comp.gnu.lilypond.general/61500

    Parameters:
      - indexNoteSourcesByPage: as returned by getFilteredIndices()
      - noteIndicesByPage:      as returned by getFilteredIndices()
      - tokens:                 as returned by getNotePositions()
      - parser:                 as returned by getNotePositions()
      - midiTicks: a sorted list of which ticks contain NoteOn events.
                   The last tick corresponds to the earliest
                   EndOfTrackEvent found across all MIDI channels.
      - notesInTicks:           as returned by getNotesInTicks()
      - pitchBends:             as returned by getNotesInTicks()

    Returns:
      - alignedNoteIndicesByPage:
          a list of sorted lists, one per page, containing all the
          indices on that page aligned in order with the MIDI ticks

    Side-effect:
      - entries may be removed from midiTicks (see above)
    """

    alignedNoteIndicesByPage = []

    # index into list of MIDI ticks
    midiIndex = 0

    # Keep track of how many times we've consecutively skipped a MIDI
    # tick, so that we can place a threshold on it in order to catch
    # a total loss of synchronization between ticks and note indices.
    consecutiveTicksSkipped = 0

    for pageNum, noteIndicesInPage in enumerate(noteIndicesByPage):
        # final indices of notes on one page
        alignedNoteIndicesInPage = []

        indexNoteSourcesInPage = indexNoteSourcesByPage[pageNum]

        # index into list of note indices
        i = 0

        while i < len(noteIndicesInPage):
            if midiIndex == len(midiTicks):
                fatal("Ran out of MIDI indices after %d. Current PDF index: %d" %
                      (midiIndex, index))

            index = noteIndicesInPage[i]
            indexNoteSources = indexNoteSourcesInPage[index]

            tick = midiTicks[midiIndex]
            debug("index %d, tick %d" % (index, tick))

            if not tick in notesInTicks:
                # This should mean that we reached the tick
                # corresponding to the final EndOfTrackEvent
                # (see getMidiEvents()).
                midiIndex += 1
                if midiIndex < len(midiTicks):
                    fatal("    BUG: no notes in tick but more ticks still to go?!")
                debug("    no notes in final tick %d" % tick)
                continue

            events = notesInTicks[tick]

            # Build dicts tracking which pitches (modulo the octave)
            # are present in the current tick and index.  Pitches will
            # be removed from these as they match.
            midiPitches = { }
            for event in events:
                pitch = event.get_pitch()
                if event in pitchBends:
                    pitch += float(pitchBends[event].get_pitch()) / 4096
                midiPitches[pitch] = event

            indexPitches = { }
            for indexNoteSource in indexNoteSources:
                token = tokens[indexNoteSource]
                lineNum, colNum = indexNoteSource
                notePitch = pitchValue(token, parser)
                indexPitches[float(notePitch)] = (token, lineNum, colNum)

            debug("    midiPitches:  %s" % repr(midiPitches))
            debug("    indexPitches: %s" % repr(indexPitches))

            # Check every note from the source is in the MIDI tick.
            # If only some are, abort with an error.  If none are, we
            # skip this MIDI tick, assuming it corresponds to a
            # transparent note caused by \hideNotes or similar, or a
            # chord.
            matchCount = 0
            for indexPitch in indexPitches.keys():
                token, lineNum, colNum = indexPitches[indexPitch]
                if indexPitch in midiPitches:
                    matchCount += 1
                    del midiPitches[indexPitch]
                    del indexPitches[indexPitch]
                    debug("        matched '%s' @ %d:%d to MIDI pitch %d" %
                          (token, lineNum, colNum, indexPitch))

            if matchCount == 0:
                # No pitches in this index matched this MIDI tick -
                # maybe it was a note hidden by \hideNotes, or notes
                # from a chord.  So let's skip the tick.
                consecutiveTicksSkipped += 1
                midiTicks.pop(midiIndex)
                msg = "    WARNING: skipping MIDI tick %d; contents:" % tick
                for event in events:
                    msg += ("\n        pitch %d length %d" %
                            (event.get_pitch(), event.length))
                stderr(msg)
                if consecutiveTicksSkipped >= 5:
                    fatal("Wanted to skip 5 consecutive MIDI ticks "
                          "which suggests a catastrophic loss of "
                          "synchronization; aborting.")
                continue

            # If we get this far, regardless of what we found, we're
            # going to keep this tick and move onto the next one now.
            midiIndex += 1

            if midiPitches:
                debug("    WARNING: only matched %d/%d MIDI notes "
                      "at index %d tick %d" %
                      (matchCount, len(events), index, tick))
                for event in midiPitches.values():
                    debug("        pitch %d length %d" %
                          (event.get_pitch(), event.length))
                if not indexPitches:
                    continue

            if indexPitches:
                err = ("only matched %d/%d notes at index %d with tick %d" %
                       (matchCount, len(indexNoteSources), index, tick))
                for indexPitch in indexPitches:
                    token, lineNum, colNum = indexPitches[indexPitch]
                    err += ("\n        pitch %d for '%s' @ %d:%d" %
                            (indexPitch, token, lineNum, colNum))
                fatal(err)

            debug("    all pitches matched in this MIDI tick!")
            alignedNoteIndicesInPage.append(index)
            consecutiveTicksSkipped = 0
            i += 1

        # add indices on one page into final noteIndicesByPage
        alignedNoteIndicesByPage.append(alignedNoteIndicesInPage)

    if midiIndex < len(midiTicks) - 1:
        warn("ran out of notes in PDF at MIDI tick %d (%d/%d ticks)" % \
                 (midiTicks[midiIndex], midiIndex + 1, len(midiTicks)))

    return alignedNoteIndicesByPage

def getNoteIndices(pdfFileName, imageWidth, lySrcFileName, lySrcLines,
                   midiTicks, notesInTicks, pitchBends):
    """
    Returns indices of notes in generated PNG images (through PDF
    file).  A note's index is the x-coordinate of its center in the
    PNG image containing it.  This relies on the fact that the PDF
    file was generated with -dpoint-and-click.

    It iterates through PDF pages:

    - first pass: finds the position in the PDF file and in the *.ly
      code of every note or tie

    - second pass: goes through notePositionsByPage separating notes and
      ties and merging near indices (e.g. 834, 835, 833, ...)

    Then it sequentially compares the indices of the images with
    indices in the MIDI: the first position in the MIDI with the first
    position on the image.  If it's equal, then it's OK.  If not, then
    it skips to the next position on image (see getMidiEvents() and
    notesInTicks).  Then it compares the next image index with MIDI
    index, and so on.

    Params:
    - pdfFileName:      name of generated PDF file (string)
    - imageWidth:       width of PNG file(s)
    - lySrcFileName:    name of .ly file
    - lySrcLines:       loaded *.ly file in memory (list)
    - midiTicks:        all ticks with notes in MIDI file
    - notesInTicks:     how many notes starts in each tick
    - pitchBends:       as returned by getNotesInTicks()

    Returns a list of note indices in the PNG image, grouped by page.
    """

    notePositionsByPage, notesAndTies, tokens, parser, pageWidth = \
        getNotePositions(pdfFileName, lySrcFileName, lySrcLines)

    output_divider_line()

    indexNoteSourcesByPage, noteIndicesByPage = \
        getFilteredIndices(notePositionsByPage, notesAndTies,
                           lySrcLines, imageWidth, pageWidth)

    return alignIndicesWithTicks(indexNoteSourcesByPage,
                                 noteIndicesByPage, tokens, parser,
                                 midiTicks, notesInTicks, pitchBends)

class VideoFrameWriter(object):
    """
    Generates frames for the final video, synchronized with audio.
    Each frame is written to disk as a PNG file.

    Counts time between starts of two notes, gets their positions on
    image and generates needed amount of frames. The index of last
    note on every page is "doubled", so it waits at the end of page.
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

    def write(self, noteIndicesByPage, notesImages):
        """
        Params:
          - noteIndicesByPage: indices of notes in pictures
          - notesImages:       names of that images (list of strings)
        """
        # folder to store frames for video
        if not os.path.exists("notes"):
            os.mkdir("notes")

        firstTempoTick, self.tempo = self.temposList[self.tempoIndex]
        debug("first tempo is %.3f bpm" % self.tempo)
        debug("final MIDI tick is %d" % self.midiTicks[-1])
        approxBeats = float(self.midiTicks[-1]) / self.midiResolution
        debug("approx %.2f MIDI beats" % approxBeats)
        beatsPerSec = 60.0 / self.tempo
        approxDuration = approxBeats * beatsPerSec
        debug("approx duration: %.2f seconds" % approxDuration)
        estimatedFrames = approxDuration * self.fps
        progress("SYNC: ly2video will generate approx. %d frames at %.3f frames/sec." %
                 (estimatedFrames, self.fps))
        if not DEBUG:
            progress("A dot is displayed for every 10 frames generated.")

        for pageNum, indices in enumerate(noteIndicesByPage):
            self.writePage(pageNum, indices, notesImages[pageNum])

    def writePage(self, pageNum, indices, notesImage):
        """
        Params:
          - pageNum:           number of page to write
          - indices:           indices of notes in page
          - notesImageFile:    name of that images (list of strings)
        """
        progress("Writing frames for page %d ..." % pageNum)

        notesPic = Image.open(notesImage)
        cropTop, cropBottom = self.getCropTopAndBottom(notesPic)

        # duplicate last index
        indices.append(indices[-1])

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
                self.measureTempoChanges(startTick, endTick,
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

        progress("SYNC: Generated %d frames for page %d/%d" %
                 (self.frameNum, pageNum + 1, len(indices)))

    def getCropTopAndBottom(self, image):
        """
        Returns a tuple containing the y-coordinates of the top and
        bottom edges of the cropping rectangle, relative to the given
        (non-cropped) image.
        """
        width, height = image.size
        progress("      Image height: %5d pixels" % height)

        topMarginSize, bottomMarginSize = self.getTopAndBottomMarginSizes(image)
        bottomY = height - bottomMarginSize
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

        if cropTop < 0:
            fatal("Would have to crop %d pixels above top of image! "
                  "Try increasing the resolution DPI "
                  "(which would increase the size of the PNG to be cropped), "
                  "or reducing the video height" % -cropTop)
            cropTop = 0

        if cropBottom > height:
            fatal("Would have to crop %d pixels below bottom of image! "
                  "Try increasing the resolution DPI "
                  "(which would increase the size of the PNG to be cropped), "
                  "or reducing the video height" % (cropBottom - height))
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

        topMargin = 0
        for y in xrange(height):
            if self.isLineBlank(pixels, width, y):
                topMargin += 1
            else:
                break

        bottomMargin = 0
        for y in xrange(height - 1, -1, -1):
            if self.isLineBlank(pixels, width, y):
                bottomMargin += 1
            else:
                break

        bottomY = height - bottomMargin
        if topMargin >= bottomY:
            fatal("Image was entirely white?  "
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

    def measureTempoChanges(self, startTick, endTick,
                            startIndex, endIndex):
        """
        Returns the time elapsed in between startTick and endTick,
        where the only MIDI events in between (if any) are tempo
        change events.
        """
        secsSinceIndex = 0.0
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
            secsSinceIndex += self.ticksToSecs(lastTick, tempoTick)
            debug("        secs since index %d: %f" %
                  (startIndex, secsSinceIndex))
            lastTick = tempoTick

        # Add on the time elapsed between the final tempo change
        # and endTick:
        secsSinceIndex += self.ticksToSecs(lastTick, endTick)

        debug("    secs between indices %d and %d: %f" %
              (startIndex, endIndex, secsSinceIndex))
        return secsSinceIndex

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
        fatal("TiMidity++ failed to generate %s ?!" % wavExpected)
    return wavExpected

def generateSilence(length):
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
    Subchunk2Size = length * sample * channels * bps/8
    ChunkSize = 4 + (8 + Subchunk1Size) + (8 + Subchunk2Size)

    fSilence = open("silence.wav", "w")

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
    return "silence.wav"

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
    stderr("ERROR: " + text)
    sys.exit(status)

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
                           '(1 is best, 31 is worst) [30]',
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
    parser.add_option("--title-at-start", dest="titleAtStart",
                      help='adds title screen at the start of video '
                           '(with name of song and its author)',
                      action="store_true", default=False)
    parser.add_option("--title-delay", dest="titleDelay",
                      help='time to display the title screen [3]',
                      type="int", metavar="SECONDS", default=3)
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
        print """ly2video %s

Copyright (C) 2012 Jiri "FireTight" Szabo, Adam Spiers
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.""" % VERSION
        sys.exit(0)

    if options.debug:
        global DEBUG
        DEBUG = True

    return options, args

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

def safeRun(cmd, errormsg=None, exitcode=None, shell=False):
    quotedCmd = []
    for arg in cmd:
        if arg.find(' ') != -1 or arg.find('"') != -1:
            quotedCmd.append('"' + arg.replace('"', '\"') + '"')
        else:
            quotedCmd.append(arg)
    quotedCmdStr = " ".join(quotedCmd)

    debug("Running: %s" % quotedCmdStr)

    try:
        stdout = subprocess.check_output(cmd, shell=shell)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        excmsg = "%s: %s" % (exc_type.__name__, exc_value)
        if errormsg is None:
            errormsg = "Failed to run command: %s: %s" % \
                (quotedCmdStr, excmsg)
        fatal(errormsg, exitcode)

    return stdout

def findExecutableDependencies(options):
    stdout = safeRun(["lilypond", "-v"], "LilyPond was not found.", 1)
    progress("LilyPond was found.")
    m = re.search('\AGNU LilyPond (\d[\d.]+\d)', stdout)
    if not m:
        fatal("Couldn't determine LilyPond version via lilypond -v")
    version = m.group(1)

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
        safeRun(cmd, exitcode=13)
    else:
        # generate silent title video
        silentAudio = generateSilence(titleLength)
        titlePath   = tmpPath("title.mpg")
        cmd = [
            ffmpeg,
            "-f", "image2",
            "-r", fps,
            "-i", framePath,
            "-i", silentAudio,
            "-same_quant",
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
            "-same_quant",
            "-q:v", str(options.quality),
            notesPath
        ]
        safeRun(cmd, exitcode=15)

        # join the files
        joinedPath = tmpPath('joined.mpg')
        if sys.platform.startswith("linux"):
            safeRun("cat '%s' '%s' > %s" % (titlePath, notesPath, joinedPath), shell=True)
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

def getNoteImages():
    """
    Returns a sorted list of the generated PNG files.
    """
    notesImages = []
    for fileName in os.listdir(tmpPath()):
        m = re.search('(?:.*/)?sanitised(?:-page(\d+))?\.png$', fileName)
        if m:
            progress("Found generated image: %s" % fileName)
            if m.group(1):
                i = int(m.group(1))
            else:
                i = 1
            newFileName = "sanitised-page%04d.png" % i
            newPath = tmpPath(newFileName)

            if newFileName != fileName:
                os.rename(fileName, newPath)
                progress("  renamed -> %s" % newFileName)
            notesImages.append(newPath)
    notesImages.sort()
    return notesImages

def getImageWidth(notesImages):
    """
    Get width of first image in pixels (we assume they all have the
    same width).  This will allow us to convert PDF coordinates into
    dimensions measured in pixels.
    """
    tmpImage = Image.open(notesImages[0])
    picWidth = tmpImage.size[0]
    progress("Width of %s is %d pixels" % (notesImages[0], picWidth))
    del tmpImage
    return picWidth

def getNumStaffLines(lyFileName, dpi):
    # generate preview of notes
    runLilyPond(
        lyFileName, dpi,
        "-dpreview",
        "-dprint-pages=#f",
    )

    # move generated files into temporary directory
    dirname, filename = os.path.split(lyFileName)
    if dirname != tmpPath():
        basename, suffix = os.path.splitext(filename)
        for ext in ('png', 'eps', 'pdf'):
            generated = basename + '.' + ext
            src = os.path.join(dirname, generated)
            dst = tmpPath(generated)
            os.rename(src, dst)
            progress("Moved %s to %s" % (src, dst))

    # find preview image and get num of staff lines
    previewPic = ""
    previewFilesTmp = os.listdir(".")
    previewFiles = []
    for fileName in previewFilesTmp:
        if "preview" in fileName:
            previewFiles.append(fileName)
            if fileName.split(".")[-1] == "png":
                previewPic = fileName

    staffYs = findStaffLines(previewPic, 50)
    numStaffLines = len(staffYs)

    progress("Found %d staff lines" % numStaffLines)
    return numStaffLines

def sanitiseLy(lyFile, width, height, dpi, numStaffLines,
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

    line = fLyFile.readline()
    while line != "":
        # if the line is done
        done = False

        if line.find("\\partial") != -1:
            warn('Ly2video has found "\\partial" command ' +
                 "in your lyFile.  This could cause problems.")

        # ignore these commands
        if re.search('\\\\include\\s+\\"articulate.ly\\"', line) or \
            line.find("\\pointAndClickOff") != -1                or \
            line.find("#(set-global-staff-size") != -1           or \
            line.find("\\bookOutputName") != -1:
            line = fLyFile.readline()

        # if I find version, write own paper block right behind it
        if line.find("\\version") != -1:
            done = True
            fSanitisedLyFile.write(line)
            writePaperHeader(fSanitisedLyFile, width, height, dpi,
                             numStaffLines, lilypondVersion)
            paperBlock = True

        # get needed info from header block and ignore it
        if (line.find("\\header") != -1 or headerPart) and not done:
            if line.find("\\header") != -1:
                fSanitisedLyFile.write("\\header {\n   tagline = ##f composer = ##f\n}\n")
                headerPart = True

            done = True

            if re.search("title\\s*=", line):
                titleText.name = line.split("=")[-1].strip()[1:-1]
            if re.search("composer\\s*=", line):
                titleText.author = line.split("=")[-1].strip()[1:-1]

            for znak in line:
                if znak == "{":
                    bracketsHeader += 1
                elif znak == "}":
                    bracketsHeader -= 1
            if bracketsHeader == 0:
                headerPart = False

        # ignore paper block
        if (line.find("\\paper") != -1 or paperPart) and not done:
            if line.find("\\paper") != -1:
                paperPart = True

            done = True

            for znak in line:
                if znak == "{":
                    bracketsPaper += 1
                elif znak == "}":
                    bracketsPaper -= 1
            if bracketsPaper == 0:
                paperPart = False

        # add unfoldRepeats right after start of score block
        if re.search("\\\\score\\s*\\{", line) and not done:
            done = True
            fSanitisedLyFile.write(line + " \\unfoldRepeats\n")

        # parse other lines, ignore page breaking commands and articulate
        if not headerPart and not paperPart and not done:
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
            elif line.find("\\articulate") != -1:
                finalLine = (line[:line.find("\\articulate")]
                             + line[line.find("\\articulate") + len("\\articulate"):])
            else:
                finalLine = line

            fSanitisedLyFile.write(finalLine)

        line = fLyFile.readline()

    fLyFile.close()

    # if I didn't find \version, write own paper block
    if not paperBlock:
        writePaperHeader(fSanitisedLyFile, width, height, numStaffLines)

    fSanitisedLyFile.close()
    progress("Wrote sanitised version of %s into %s" % (lyFile, sanitisedLyFileName))

    return sanitisedLyFileName

def main():
    """
    Main function of ly2video script.

    It performs the following steps:

    - use Lilypond to generate PNG images, PDF, and MIDI files of the
      music

    - find the spacial and temporal position of each note in the PDF
      and MIDI files respectively

    - combine the positions together to generate the required number
      of video frames

    - create a video file from the individual frames
    """
    (options, args) = parseOptions()

    lilypondVersion, ffmpeg, timidity = findExecutableDependencies(options)

    # title and all about it
    if options.titleAtStart:
        titleLength = options.titleDelay
    else:
        titleLength = 0
    titleText = collections.namedtuple("titleText", "name author")
    titleText.name = "<name of song>"
    titleText.author = "<author>"

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

    # if it's not 2.14.2, try to convert it
    lyFile = preprocessLyFile(lyFile)

    numStaffLines = getNumStaffLines(lyFile, options.dpi)

    sanitisedLyFileName = \
        sanitiseLy(lyFile,
                   options.width, options.height, options.dpi,
                   numStaffLines, titleText, lilypondVersion)

    lySrcLines = getLyLines(sanitisedLyFileName)

    runLilyPond(sanitisedLyFileName, options.dpi)

    notesImages = getNoteImages()
    picWidth = getImageWidth(notesImages)

    midiPath = tmpPath("sanitised.midi")
    if options.beatmap:
        output_divider_line()
        newMidiPath = tmpPath("sanitised-adjusted.midi")
        applyBeatmap(midiPath, newMidiPath,
                     absPathFromRunDir(options.beatmap))
        midiPath = newMidiPath

    output_divider_line()

    # find needed data in MIDI
    try:
        midiResolution, temposList, midiTicks, notesInTicks, pitchBends = \
            getMidiEvents(midiPath)
    except Exception as err:
        fatal("MIDI: %s " % err, 10)

    output_divider_line()

    # find notes indices
    noteIndicesByPage = getNoteIndices(tmpPath("sanitised.pdf"),
                                       picWidth,
                                       sanitisedLyFileName, lySrcLines,
                                       midiTicks, notesInTicks, pitchBends)
    output_divider_line()

    # frame rate of output video
    fps = options.fps

    # generate title screen
    if options.titleAtStart:
        generateTitle(titleText, width, height, fps, titleLength)
        output_divider_line()

    # generate notes
    leftMargin, rightMargin = options.cursorMargins.split(",")
    frameWriter = VideoFrameWriter(
        options.width, options.height, fps, getCursorLineColor(options),
        options.scrollNotes, int(leftMargin), int(rightMargin),
        midiResolution, midiTicks, temposList)
    frameWriter.write(noteIndicesByPage, notesImages)

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
