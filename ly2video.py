#!/usr/bin/env python
# coding=utf-8

import collections
import os
import re
import shutil
import subprocess
import sys
from   optparse import OptionParser
from   struct import pack

from PIL import Image, ImageDraw, ImageFont
from ly.tokenize import Tokenizer
from pyPdf import PdfFileWriter, PdfFileReader
import midi


SANITISED_LY = "ly2videoConvert.ly"
KEEP_TMP_FILES = False

def lineIndices(image, lineLength):
    """
    Takes a image and returns height indices of staff lines in pixels.

    Params:
    - image:        name of image with staff lines
    - lineLength:   needed length of line to accept it as staff line
    """
    
    fImage = Image.open(image)

    # position of the first line on image
    firstLinePos = (-1, -1)             

    # for every pixel of image
    for x in range(fImage.size[0]):   
        for y in range(fImage.size[1]):
            for length in range(lineLength):
                # testing color of pixels in range (startPos, startPos + lineLength)
                if fImage.getpixel((x + length, y)) == (255,255,255):
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

    # adding 3 pixels to avoid line of pixels connectings all staffs together
    firstLinePos = (firstLinePos[0] + 3, firstLinePos[1])

    lines = []
    newLine = True

    # for every pixel in range (height of first line, height of image)
    for height in range(firstLinePos[1], fImage.size[1]):
        # if color of that pixel isn't white
        if fImage.getpixel((firstLinePos[0], height)) != (255,255,255):
            # and it can be new staff line
            if newLine:
                # accept it
                newLine = False
                lines.append(height)
        else:
            # it's space between lines
            newLine = True

    del fImage

    # return staff line indices
    return lines

def generateTitle(titleText, resolution, fps, titleLength):
    """
    Generates frames with name of song and its author.

    Params:
    - titleText:    collection of name of song and its author
    - resolution:   wanted resolution of frames (and video)
    - fps:          frame rate (frames per second) of final video
    - titleLength:  length of title screen (seconds)
    """

    # create image of title screen
    titleScreen = Image.new("RGB", resolution, (255,255,255))
    # it will draw text on titleScreen
    drawer = ImageDraw.Draw(titleScreen)    
    # save folder for frames
    if not os.path.exists("title"):
        os.mkdir("title")

    totalFrames = fps * titleLength
    progress("TITLE: ly2video will generate cca %d frames." % totalFrames)

    # font for song's name, args - font type, size
    nameFont = ImageFont.truetype("arial.ttf", resolution[1] / 15)
    # font for author
    authorFont = ImageFont.truetype("arial.ttf", resolution[1] / 25)

    # args - position of left upper corner of rectangle (around text), text, font and color (black)
    drawer.text(((resolution[0] - nameFont.getsize(titleText.name)[0]) / 2,
                 (resolution[1] - nameFont.getsize(titleText.name)[1]) / 2 - resolution[1] / 25),
                titleText.name, font=nameFont, fill=(0,0,0))
    # same thing
    drawer.text(((resolution[0] - authorFont.getsize(titleText.author)[0]) / 2,
                 (resolution[1] / 2) + resolution[1] / 25),
                titleText.author, font=authorFont, fill=(0,0,0))

    # generate needed number of frames (= fps * titleLength)
    for frameNum in range(totalFrames):
        titleScreen.save("./title/frame%d.png" % frameNum)

    progress("TITLE: Generating title screen has ended. (%d/%d)" %
             (totalFrames, totalFrames))
    return 0

def writePaperHeader(fFile, resolution, numOfLines):
    """
    Writes own paper block into given file.

    Params:
    - fFile:        given opened file
    - resolution:   wanted resolution of video
    - numOfLines:   number of staff lines
    """

    pixelsPerMm = 181.0 / 720 # 1 px = 0.251375 mm

    fFile.write("\\paper {\n")
    fFile.write("   paper-width   = %d\\mm\n" % round(10 * resolution[0] * pixelsPerMm))
    fFile.write("   paper-height  = %d\\mm\n" % round(resolution[1] * pixelsPerMm))
    fFile.write("   top-margin    = %d\\mm\n" % round(resolution[1] * pixelsPerMm / 20))
    fFile.write("   bottom-margin = %d\\mm\n" % round(resolution[1] * pixelsPerMm / 20))
    fFile.write("   left-margin   = %d\\mm\n" % round(resolution[0] * pixelsPerMm / 2))
    fFile.write("   right-margin  = %d\\mm\n" % round(resolution[0] * pixelsPerMm / 2))
    fFile.write("   print-page-number = ##f\n")
    fFile.write("}\n")
    fFile.write("#(set-global-staff-size %d)\n\n" %
                int(round((resolution[1] - 2 * (resolution[1] / 10)) / numOfLines)))
    
    return 0

def getMidiEvents(nameOfMidi):
    """
    Goes through given MIDI file and returns list of tempos, resolution,
    dictionary of MIDI events and when MIDI events happen (ticks).

    Params:
    - nameOfMidi: name of MIDI file (string)
    """

    # open MIDI with external library
    midiFile = midi.read_midifile(nameOfMidi)
    # and make ticks absolute
    midiFile.make_ticks_abs()

    # get MIDI resolution and header
    midiResolution = midiFile.resolution
    midiHeader = midiFile[0]

    temposList = []
    for event in midiHeader:
        # if it's SetTempoEvent
        if isinstance(event, midi.SetTempoEvent):
            # convert value from hexadecimal into decimal
            base = 0
            tempoValue = 0
            data = event.data
            data.reverse()
            for value in data:
                tempoValue += value * (256 ** base)
                base += 1
            # and add that new tempo with its start into temposList
            temposList.append((event.tick, tempoValue))

    # Count how many notes start in each tick.  Each key is a tick and
    # the corresponding value is the count.  This is needed for
    # deleting some notes' positions obtained from the images,
    # e.g. when two or more notes within a major second of each other
    # occur in the same chord and share a note stem - in that case you
    # get some note heads to the left of the stem and some to the
    # right.
    notesInTick = dict()

    # for every channel in MIDI (except the first one)
    for eventsList in midiFile[1:]:
        # for every event
        for event in eventsList:
            # if it's NoteOnEvent
            if isinstance(event, midi.NoteOnEvent):
                # and velocity is not zero (that's basically "NoteOffEvent")
                if event.data[1] != 0:
                    # add it into notesInTick
                    if notesInTick.get(event.tick) == None:
                        notesInTick[event.tick] = 1
                    else:
                        notesInTick[event.tick] += 1

    # get all ticks with notes and sorts it
    midiTicks = notesInTick.keys()
    midiTicks.sort()

    # add last possible tick (end of song)
    endOfTrack = -1
    # through ever channel
    for eventsList in midiFile[1:]:
        if isinstance(eventsList[-1], midi.EndOfTrackEvent):
            if endOfTrack < eventsList[-1].tick:
                endOfTrack = eventsList[-1].tick
    midiTicks.append(endOfTrack)
    
    progress("MIDI: Parsing MIDI file has ended.")
    
    return (midiResolution, temposList, notesInTick, midiTicks)

def getNotePositions(pdf, loadedProject):
    """
    For every link annotation in the PDF file which is a link to the
    SANITISED_LY file we generated, store the coordinates of the
    annotated rectangle and also the line and column number it points
    to in the SANITISED_LY file.

    Returns:
    - notesAndTies: a list of (lineNum, charNum) tuples sorted by
      line number in SANITISED_LY
    - notePositionsByPage: a list with each top-level item representing a page,
      where each page is a list of ((lineNum, charNum), coords) tuples.
      coords is (x1, y1, x2, y2) representing opposite corners of
      the rectangle.
    - pageWidth: the width of the first page (all pages are
      assumed to have the same width)
    """

    # open PDF file with external library and gets width of page (in PDF measures)
    fPdf = file(pdf, "rb")
    pdfFile = PdfFileReader(fPdf) 
    pageWidth = pdfFile.getPage(0).getObject()['/MediaBox'][2]
    print "width of first PDF page is %f" % pageWidth

    notesAndTies = set()
    notePositionsByPage = []
    
    for pageNumber in range(pdfFile.getNumPages()):
        # get informations about page
        page = pdfFile.getPage(pageNumber)
        info = page.getObject()

        # ly parser (from Frescobaldi)
        parser = Tokenizer()

        if info.has_key('/Annots'):
            links = info['/Annots']

            # stores wanted positions on single page
            notePositionsInPage = []
            
            for link in links:
                # Get (x1, y1, x2, y2) coordinates of opposite corners
                # of the annotated rectangle
                coords = link.getObject()['/Rect']

                # if it's not link into ly2videoConvert.ly, then ignore it
                if link.getObject()['/A']['/URI'].find(SANITISED_LY) == -1:
                    continue
                # otherwise get coordinates into LY file
                uri = link.getObject()['/A']['/URI']
                lineNum, charNum, columnNum = uri.split(":")[-3:]
                if charNum != columnNum:
                    print "got char %s col %s on line %s" % (charNum, columnNum, lineNum)
                lineNum = int(lineNum)
                charNum = int(charNum)
                
                try:
                    # get name of that note
                    note = parser.tokens(loadedProject[lineNum - 1][charNum:]).next()

                    # is that note ok?
                    noteOk = True
                    for token in parser.tokens(loadedProject[lineNum - 1][charNum + len(note):]):
                        # if there is another note right next to it (or rest, etc.), it's ok 
                        if token.__class__.__name__ == "PitchWord":
                            break
                        # if its "note with \rest", it's NOT ok and ignore it
                        elif (token.__class__.__name__ == "Command"
                              and repr(token) == "u'\\\\rest'"):
                            noteOk = False
                            break
                    # if the note is ok and it's not rest or it's tie
                    if noteOk:
                        if ((note.__class__.__name__ == "PitchWord" and str(note) not in "rR")
                            or (note.find("~") != -1)):
                            # add it
                            notePositionsInPage.append(((lineNum, charNum), coords))
                            notesAndTies.add((lineNum, charNum))
                #if there is some error, write that statement and exit
                except Exception as err:
                    fatal(("PDF: %s\n"
                           + "ly2video was trying to work with this: "
                           + "\"%s\", coords in LY (line %d char %d).") %
                          (err, loadedProject[lineNum - 1][charNum:][:-1],
                           lineNum, charNum))

            # sort wanted positions on that page and add it into whole wanted positions
            notePositionsInPage.sort()
            notePositionsByPage.append(notePositionsInPage)

    # close PDF file
    fPdf.close()

    # create list of notes and ties and sort it        
    notesAndTies = list(notesAndTies)
    notesAndTies.sort()    
    return notePositionsByPage, notesAndTies, pageWidth

def getFilteredIndices(notePositionsByPage, notesAndTies, loadedProject, imageWidth, pageWidth):
    """
    Goes through notePositionsByPage, filtering out anything that
    won't generate a MIDI NoteOn event, converting each note's
    coordinate into an index (i.e. the x-coordinate of the center of
    the note in the PNG file which contains it), and merging indices
    which are within +/- 10 pixels of each other.

    Returns:
    - notesInIndex: a list of hashes, one per page, mapping each index
                    to how many notes are at that index
    - allNotesIndices: a list of sorted lists, one per page, containing
                       all the indices on that page in order
    """
    notesInIndex = []
    allNotesIndices = []

    for pageNum, notePositionsInPage in enumerate(notePositionsByPage):
        parser = Tokenizer()
        # how many notes are in one position (on one page)
        notesInIndexPage = dict()

        # notes that are connected by tie and will not generate
        # a MIDI NoteOn event
        silentNotes = []

        for (linkLy, coords) in notePositionsInPage:
            lineNum, charNum = linkLy
            # get that token
            token = parser.tokens(loadedProject[lineNum - 1][charNum:]).next()

            # if it's note
            if token.__class__.__name__ == "PitchWord":
                # if it's silent note, then remove it and ignore it
                if linkLy in silentNotes:
                    silentNotes.remove(linkLy)
                    continue
                # otherwise get its index in pixels
                xcenter = (coords[0] + coords[2]) / 2
                noteIndex = int(round(xcenter * imageWidth / pageWidth))
                # add that index into indices
                if notesInIndexPage.get(noteIndex) == None:
                    notesInIndexPage[noteIndex] = 1
                else:
                    notesInIndexPage[noteIndex] += 1
            # if it's tie
            elif token.find("~") != -1:
                # if next note isn't in silent notes, add it
                if silentNotes.count(notesAndTies[notesAndTies.index(linkLy) + 1]) == 0:
                    silentNotes.append(notesAndTies[notesAndTies.index(linkLy) + 1])
                # otherwise add next one (after the last silent one (if it's tie of harmony))
                else:
                    silentNotes.append(notesAndTies[notesAndTies.index(silentNotes[-1]) + 1]) 

        # gets all indices on one page and sort it
        noteIndicesInPage = notesInIndexPage.keys()
        noteIndicesInPage.sort()

        # merges indices within +/- 10 pixels of each other
        skipNext = False
        for index in noteIndicesInPage[:-1]:
            if skipNext:
                skipNext = False
                continue
            # gets next index
            nextIndex = noteIndicesInPage[noteIndicesInPage.index(index) + 1]
            if index in range(nextIndex - 10, nextIndex + 10):
                # merges them and remove next index
                notesInIndexPage[index] += notesInIndexPage.get(nextIndex)
                notesInIndexPage.pop(nextIndex)
                noteIndicesInPage.remove(nextIndex)
                skipNext = True

        # stores info about this page        
        notesInIndex.append(notesInIndexPage)
        allNotesIndices.append(noteIndicesInPage)
        
        progress("PDF: Page %d/%d has been completed." %
                 (pageNum + 1, len(notePositionsByPage)))

    return notesInIndex, allNotesIndices

def compareIndices(notesInIndex, allNotesIndices, midiTicks, notesInTick):
    """
    Sequentially compares the indices of notes in the images with
    indices in the MIDI: the first position in the MIDI with the first
    position on the image.  If it's equal, then it's OK.  If not, then
    it skips to the next position on image (see getMidiEvents(), part
    notesInTick).  Then it compares the next image index with MIDI
    index, and so on.
    """

    newNoteIndicesByPage = []

    # index into list of MIDI ticks
    midiIndex = 0

    for page in allNotesIndices:
        # final indices of notes on one page
        noteIndicesInPage = []
        # skips next index (if needed)
        skip = False
        
        for index in page:
            # if runs out of midi indices, then exit
            if midiIndex == len(midiTicks):
                fatal("ly2video don't have enough MIDI indices. "
                      + "Current PDF index: %d" % index)
                
            # skip next index
            if skip:
                skip = False
                continue
            
            # if number of notes in one tick (MIDI) <= number of notes in one index (PNG)
            if (notesInTick.get(midiTicks[midiIndex])
                <= notesInIndex[allNotesIndices.index(page)].get(index)):
                # add that index
                noteIndicesInPage.append(index)
            else:
                # if there is next index on my right
                if index != page[-1]:
                    # get number of notes in right index
                    rightIndex = notesInIndex[allNotesIndices.index(page)].get(page[page.index(index) + 1])
                    # compare them and get add that with more notes
                    if notesInIndex[allNotesIndices.index(page)].get(index) >= rightIndex:
                        noteIndicesInPage.append(index)
                    else:
                        noteIndicesInPage.append(page[page.index(index) + 1])
                # otherwise just add that index (it's last index on that page)
                else:
                    noteIndicesInPage.append(index)
                # and of course skip next index
                skip = True
            # go to next MIDI index
            midiIndex += 1
        # add indices on one page into final noteIndicesByPage
        newNoteIndicesByPage.append(noteIndicesInPage)

    return newNoteIndicesByPage

def getNoteIndices(pdf, imageWidth, loadedProject, midiTicks, notesInTick):
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
    it skips to the next position on image (see getMidiEvents(), part
    notesInTick).  Then it compares the next image index with MIDI
    index, and so on.

    Returns a list of note indices in the PNG image, grouped by page.

    Params:
    - pdf:              name of generated PDF file (string)
    - imageWidth:       width of PNG file(s)
    - loadedProject:    loaded *.ly file in memory (list)
    - midiTicks:        all ticks with notes in MIDI file
    - notesInTick:      how many notes starts in each tick
    """

    notePositionsByPage, notesAndTies, pageWidth = \
        getNotePositions(pdf, loadedProject)

    notesInIndex, allNotesIndices = \
        getFilteredIndices(notePositionsByPage, notesAndTies, loadedProject, imageWidth, pageWidth)

    return compareIndices(notesInIndex, allNotesIndices, midiTicks, notesInTick)

def sync(midiResolution, temposList, midiTicks, resolution, fps, noteIndicesByPage,
         notesImages, cursorLineColor):
    """
    Generates frames for the final video, synchronized with audio.

    Counts time between starts of two notes, gets their positions on
    image and generates needed amount of frames. The index of last
    note on every page is "doubled", so it waits at the end of page.
    The required number of frames for every pair is computed as a real
    number and because a fractional number of frames can't be
    generated, they are stored in dropFrame and if that is > 1, it
    skips generating one frame.

    Params:
    - midiResolution:    resolution of MIDI file
    - temposList:        list of possible tempos in MIDI
    - midiTicks:         list of ticks with NoteOnEvent
    - resolution:        resolution of generated frames (and video)
    - fps:               frame rate of video
    - noteIndicesByPage: indices of notes in pictures
    - notesImages:       names of that images (list of strings)
    - cursorLineColor:   color of middle line
    """

    midiIndex = 0
    tempoIndex = 0
    frameNum = 0

    # folder to store frames for video
    if not os.path.exists("notes"):
        os.mkdir("notes")

    totalFrames = int(round(((temposList[tempoIndex][1] * 1.0)
                        / midiResolution * (midiTicks[-1]) / 1000000 * fps)))
    progress("SYNC: ly2video will generate cca %d frames." % totalFrames)

    dropFrame = 0.0
    
    for pageNum, indices in enumerate(noteIndicesByPage):
        # open image of staff
        notesPic = Image.open(notesImages[pageNum])

        # add index for the last note
        indices.append(indices[-1])

        for index in indices[:-1]:
            # get two indices of notes (pixels)
            startIndex = index
            endIndex = indices[indices.index(index) + 1]

            # get two indices of MIDI events (ticks)
            startMidi = midiTicks[midiIndex]
            midiIndex += 1
            endMidi = midiTicks[midiIndex]

            # if there's gonna be change in tempo, change it
            if tempoIndex != (len(temposList) - 1):
                if startMidi == temposList[tempoIndex + 1][0]:
                    tempoIndex += 1


            # how many frames do I need?
            neededFrames = ((temposList[tempoIndex][1] * 1.0) / midiResolution
                            * (endMidi - startMidi) / 1000000 * fps)
            # how mane frames can be generated?
            realFrames = int(round(neededFrames))
            # add that difference between needed and real value into dropFrame
            dropFrame += (realFrames - neededFrames)
            # pixel shift for one frame
            shift = (endIndex - startIndex) * 1.0 / neededFrames

            
            for posun in range(realFrames):
                # if I need drop more than "1.0" frames, drop one
                if dropFrame >= 1.0:
                    dropFrame -= 1.0
                    continue
                else:
                    # get frame from image of staff, args - (("left upper corner", "right lower corner"))
                    leftUpper = int(startIndex + round(posun * shift)
                                    - (resolution[0] / 2))
                    rightUpper = int(startIndex + round(posun * shift)
                                     + (resolution[0] / 2))
                    frame = notesPic.copy().crop((leftUpper, 0, rightUpper, resolution[1]))
                    # add middle line
                    for pixel in range(resolution[1]):
                        frame.putpixel((resolution[0] / 2, pixel), cursorLineColor)
                        frame.putpixel(((resolution[0] / 2) + 1, pixel), cursorLineColor)

                    # save that frame
                    frame.save("./notes/frame%d.png" % frameNum)
                    frameNum += 1
                    if frameNum % 10 == 0:
                        sys.stdout.write(".")
                        sys.stdout.flush()
        print

        progress("SYNC: Generating frames for page %d/%d has been completed. (%d/%d)" %
                 (pageNum + 1, len(noteIndicesByPage), frameNum, totalFrames))

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

def progress(text):
    sys.stderr.write(text + "\n")

def output_divider_line():
    progress(60 * "-")

def fatal(text, status=1):
    progress("ERROR: " + text)
    sys.exit(status)

def delete_tmp_files(paths):
    return True
    errors = 0
    for path in paths:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            try:
                os.remove(path)
            except Exception as err:
                sys.stderr.write("WARNING: ly2video can't delete %s: %s\n" %
                                 (path, err))
                errors += 1
    return (errors == 0)

def parseOptions():
    # create parser and add options
    parser = OptionParser("usage: %prog [options]")

    parser.add_option("-i", "--input", dest="input",
                  help="input LilyPond project", metavar="FILE")
    parser.add_option("-o", "--output", dest="output",
                  help='name of output video (e.g. "myNotes.avi", default is input + .avi)',
                      metavar="FILE")
    parser.add_option("-c", "--color", dest="color",
                  help='name of color of middle bar (default is "red")', metavar="COLOR",
                      default="red")
    parser.add_option("-f", "--fps", dest="fps",
                  help='frame rate of final video (default is "30")', type="int", metavar="FPS",
                      default=30)
    parser.add_option("-r", "--resolution", dest="resolution",
                  help='resolution of final video (options: 360, 720, 1080, default is "720")',
                      metavar="HEIGHT", type="int", default=720)
    parser.add_option("--title-at-start", dest="titleAtStart",
                  help='adds title screen at the start of video (with name of song and its author)',
                      action="store_true", default=False)
    parser.add_option("--title-delay", dest="titleDelay",
                  help='time to display the title screen (default is "3" seconds)', type="int",
                      metavar="SECONDS", default=3)
    parser.add_option("--windows-ffmpeg", dest="winFfmpeg",
                  help='(for Windows users) folder with ffpeg.exe (e.g. "C:\\ffmpeg\\bin\\")',
                      metavar="PATH", default="")
    parser.add_option("--windows-timidity", dest="winTimidity",
                  help='(for Windows users) folder with timidity.exe (e.g. "C:\\timidity\\")',
                      metavar="PATH", default="")
    parser.add_option("-k", "--keep", dest="keepTempFiles",
                  help="don't remove temporary working files",
                      action="store_true", default=False)

    # if there is only one arg, then show help and exit
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    # and parse input
    return parser.parse_args()

def portableDevNull():
    if sys.platform.startswith("linux"):
        return "/dev/null"
    elif sys.platform.startswith("win"):
        return "NUL"

def findExecutableDependencies(options):
    redirectToNull = " >%s" % portableDevNull()

    if os.system("lilypond -v" + redirectToNull) != 0:
        fatal("LilyPond was not found.", 1)
    else:
        progress("LilyPond was found.")

    ffmpeg = options.winFfmpeg + "ffmpeg"
    if os.system(ffmpeg + " -version" + redirectToNull) != 0:
        fatal("FFmpeg was not found (maybe use --windows-ffmpeg?).", 2)
    else:
        progress("FFmpeg was found.")

    timidity = options.winTimidity + "timidity"
    if os.system(timidity + " -v" + redirectToNull) != 0:
        fatal("TiMidity++ was not found (maybe use --windows-timidity?).", 3)
    else:
        progress("TiMidity++ was found.")

    output_divider_line()

    return ffmpeg, timidity

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
        progress("WARNING: Color was not found, " +
                 'ly2video will use default one ("red").')
        return (255,0,0)

def getResolution(options):
    if options.resolution == 360:
        return (640, 360)
    elif options.resolution == 720:
        return (1280, 720)
    elif options.resolution == 1080:
        return (1920, 1080)
    else:
        progress("WARNING: Resolution was not found, " +
                 'ly2video will use default one ("720" => 1280x720).')
        return (1280, 720)

def getOutputFile(options):
    output = options.output
    if output == None or len(output.split(".")) < 2:
        return project[:-2] + "avi"
    return output

def callFfmpeg(ffmpeg, options, output):
    fps = str(options.fps)
    # call FFmpeg (without title)
    if not options.titleAtStart:
        if os.system(ffmpeg + " -f image2 -r " + fps
                     + " -i ./notes/frame%d.png -i ly2videoConvert.wav "
                     + output) != 0:
            fatal("Calling FFmpeg has failed.", 13)
    # call FFmpeg (with title)
    else:
        # create video with title
        silentAudio = generateSilence(titleLength)
        if os.system(ffmpeg + " -f image2 -r " + fps
                     + " -i ./title/frame%d.png -i "
                     + silentAudio + " -same_quant title.mpg") != 0:
            fatal("Calling FFmpeg has failed.", 14)
        # generate video with notes
        if os.system(ffmpeg + " -f image2 -r " + fps
                     + " -i ./notes/frame%d.png -i ly2videoConvert.wav "
                     + "-same_quant notes.mpg") != 0:
            fatal("Calling FFmpeg has failed.", 15)
        # join the files
        if sys.platform.startswith("linux"):
            os.system("cat title.mpg notes.mpg > video.mpg")
        elif sys.platform.startswith("win"):
            os.system("copy title.mpg /B + notes.mpg /B video.mpg /B")

        # create output file
        if os.system(ffmpeg + " -i video.mpg " + output) != 0:
            fatal("Calling FFmpeg has failed.", 16)

        # delete created videos, silent audio and folder with title frames
        delete_tmp_files([ "title.mpg", "notes.mpg", "video.mpg", silentAudio, "title" ])

def getLyVersion(fileName):
    # if I don't have input file, end  
    if fileName == None:
        fatal("LilyPond input file was not specified.", 4)
    else:
        # otherwise try to open fileName
        try:
            fProject = open(fileName, "r") 
        except IOError:
            fatal("Couldn't read %s" % fileName, 5)

    # find version of LilyPond in input project
    version = ""
    for line in fProject.readlines():
        if line.find("\\version") != -1:
            parser = Tokenizer()
            for token in parser.tokens(line):
                if token.__class__.__name__ == "StringQuoted":
                    version = str(token)[1:-1]
                    break
            if version != "":
                break
    fProject.close()

    return version

def getNoteImages(fileName):
    """
    Returns a sorted list of the generated PNG files.
    """
    notesImages = []
    for fileName in os.listdir("."):
        m = re.match('ly2videoConvert(?:-page(\d+))?\.png', fileName)
        if m:
            progress("Found generated image: %s" % fileName)
            if m.group(1):
                i = int(m.group(1))
            else:
                i = 1
            newFileName = "ly2videoConvert-page%04d.png" % i

            if newFileName != fileName:
                os.rename(fileName, newFileName)
                progress("  renamed -> %s" % newFileName)
            notesImages.append(newFileName)
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
    print "width of %s is %d pixels" % (notesImages[0], picWidth)
    del tmpImage
    return picWidth

def getNumStaffLines(project):
    # generate preview of notes
    if (os.system("lilypond -dmidi-extension=midi -dpreview -dprint-pages=#f "
                  + project + " 2>" + portableDevNull()) != 0):
        fatal("Generating preview has failed.", 7)

    # find preview image and get num of staff lines
    previewPic = ""
    previewFilesTmp = os.listdir(".")
    previewFiles = []
    for fileName in previewFilesTmp:
        if "preview" in fileName:
            previewFiles.append(fileName)
            if fileName.split(".")[-1] == "png":
                previewPic = fileName
    numStaffLines = len(lineIndices(previewPic, 50))

    # then delete generated preview files
    if not delete_tmp_files(previewFiles):
        sys.exit(8)
    if not delete_tmp_files(project[:-2] + "midi"):
        sys.exit(8)

    return numStaffLines

def sanitiseLy(project, resolution, numStaffLines, titleText):
    fProject = open(project, "r")

    # create own ly project
    fMyProject = open(SANITISED_LY, "w")

    # if I add own paper block
    paperBlock = False

    # stores info about header and paper block (and brackets in them)
    headerPart = False
    bracketsHeader = 0
    paperPart = False
    bracketsPaper = 0
    
    line = fProject.readline()
    while line != "":
        # if the line is done
        done = False

        if line.find("\\partial") != -1:
            progress('WARNING: Ly2video has found "\\partial" command ' +
                     "in your project. There can be some errors.")

        # ignore these commands
        if (line.find("\\include \"articulate.ly\"") != -1
            or line.find("\\pointAndClickOff") != -1
            or line.find("#(set-global-staff-size") != -1
            or line.find("\\bookOutputName") != -1):
            line = fProject.readline()

        # if I find version, write own paper block right behind it
        if line.find("\\version") != -1:
            done = True
            fMyProject.write(line)
            writePaperHeader(fMyProject, resolution, numStaffLines)
            paperBlock = True

        # get needed info from header block and ignore it
        if (line.find("\\header") != -1 or headerPart) and not done:
            if line.find("\\header") != -1:
                fMyProject.write("\\header {\n   tagline = ##f composer = ##f\n}\n")
                headerPart = True
                
            done = True
            
            if line.find("title = ") != -1:
                titleText.name = line.split("=")[-1].strip()[1:-1]
            if line.find("composer = ") != -1:
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
        if (line.find("\\score {") != -1) and not done:
            done = True
            fMyProject.write(line + " \\unfoldRepeats\n")

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
                
            fMyProject.write(finalLine)
            
        line = fProject.readline()

    fProject.close()

    # if I didn't find \version, write own paper block
    if not paperBlock:
        writePaperHeader(fMyProject, resolution, numStaffLines)
    fMyProject.close()

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

    if options.keepTempFiles:
        KEEP_TMP_FILES = True

    ffmpeg, timidity = findExecutableDependencies(options)

    # resolution of output video
    resolution = getResolution(options)

    # title and all about it
    if options.titleAtStart:
        titleLength = options.titleDelay
    else:
        titleLength = 0
    titleText = collections.namedtuple("titleText", "name author")
    titleText.name = "<name of song>"
    titleText.author = "<author>"

    # delete old created folders
    delete_tmp_files(["notes", "title"])
    for fileName in os.listdir("."):
        if "ly2videoConvert" in fileName:
            if not delete_tmp_files(fileName):
                return 6
       
    # input project from user (string)
    project = options.input

    # if it's not 2.14.2, try to convert it
    versionConversion = False
    if getLyVersion(project) != "2.14.2":
        if os.system("convert-ly " + project + " > newProject.ly") == 0:
            project = "newProject.ly"
            versionConversion = True
        else:
            progress("WARNING: Convert of input file has failed, " +
                     "there can be some errors.")
            output_divider_line()

    numStaffLines = getNumStaffLines(project)

    sanitiseLy(project, resolution, numStaffLines, titleText)

    # load own project into memory
    fMyProject = open(SANITISED_LY, "r")
    loadedProject = []
    for line in fMyProject.readlines():
        loadedProject.append(line)
    fMyProject.close()
    
    # generate PDF, PNG and MIDI file
    if (os.system("lilypond -fpdf --png -dpoint-and-click "
                  + "-dmidi-extension=midi ly2videoConvert.ly") != 0):
        fatal("Calling LilyPond has failed.", 9)
    output_divider_line()

    # delete created project
    delete_tmp_files(SANITISED_LY)

    # and try to delete converted project
    if versionConversion:
        delete_tmp_files(project)

    # find generated images
    notesImages = getNoteImages(fileName)
    output_divider_line()
    picWidth = getImageWidth(notesImages)

    # find needed data in MIDI
    try:
        midiResolution, temposList, notesInTick, midiTicks = getMidiEvents("ly2videoConvert.midi")
    except Exception as err:
        fatal("MIDI: %s " % err, 10)
        
    output_divider_line()

    # find notes indices
    noteIndicesByPage = getNoteIndices("ly2videoConvert.pdf", picWidth,
                                       loadedProject, midiTicks, notesInTick)
    output_divider_line()
    
    # frame rate of output video
    fps = options.fps
    
    # generate title screen
    if options.titleAtStart:
        generateTitle(titleText, resolution, fps, titleLength)
    output_divider_line()

    # generate notes
    sync(midiResolution, temposList, midiTicks, resolution,
         fps, noteIndicesByPage, notesImages, getCursorLineColor(options))
    output_divider_line()

    # call TiMidity++ to convert MIDI (ly2videoConvert.wav)
    try:
        subprocess.check_call([timidity, "ly2videoConvert.midi", "-Ow"])
    except (subprocess.CalledProcessError, OSError) as err:
        fatal("TiMidity++: %s" % err, 11)
    output_divider_line()

    # delete old files
    delete_tmp_files(notesImages)
    delete_tmp_files("ly2videoConvert.pdf")
    delete_tmp_files("ly2videoConvert.midi")

    output = getOutputFile(options)
    callFfmpeg(ffmpeg, options, output)

    output_divider_line()
        
    # delete wav file and folder with notes frames
    delete_tmp_files([ "ly2videoConvert.wav", "notes" ])

    # end
    print("Ly2video has ended. Your generated file: " + output + ".")
    return 0  

if __name__ == '__main__':
    status = main()
    sys.exit(status)
