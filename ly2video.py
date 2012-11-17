#!/usr/bin/env python
#coding=utf-8
# ------------------------------------------------------------------------------
import os
import sys
from PIL import Image, ImageDraw, ImageFont
from optparse import OptionParser
import optparse
from ly.tokenize import Tokenizer
from pyPdf import PdfFileWriter, PdfFileReader
import midi
import collections
import shutil
import subprocess
from struct import pack
# ------------------------------------------------------------------------------
def lineIndexes(picture, lineLength):
    """
    Takes a picture and returns height indexes of staff lines in pixels.

    Params:
    - picture:      name of picture with staff lines
    - lineLength:   needed length of line to accept it as staff line
    """
    
    fPicture = Image.open(picture)

    # position of the first line on picture
    firstLinePos = (-1, -1)             

    # for every pixel of picture
    for x in range(fPicture.size[0]):   
        for y in range(fPicture.size[1]):
            for length in range(lineLength):
                # testing color of pixels in range (startPos, startPos + lineLength)
                if fPicture.getpixel((x + length, y)) == (255,255,255):
                    # if it's white then it's not a staff line
                    firstLinePos = (-1, -1)
                    break
                else:
                    # else it can be
                    firstLinePos = (x, y)
            # when have a valid position, break out
            if (firstLinePos != (-1, -1)):
                break
        if (firstLinePos != (-1, -1)):
            break

    # adding 3 pixels to avoid line of pixels connectings all staffs together
    firstLinePos = (firstLinePos[0] + 3, firstLinePos[1])

    lines = []
    newLine = True

    # for every pixel in range (height of first line, height of picture)
    for height in range(firstLinePos[1], fPicture.size[1]):
        # if color of that pixel isn't white
        if (fPicture.getpixel((firstLinePos[0], height)) != (255,255,255)):
            # and it can be new staff line
            if newLine:
                # accept it
                newLine = False
                lines.append(height)
        else:
            # it's space between lines
            newLine = True

    del fPicture

    # return staff line indexes
    return lines
# ------------------------------------------------------------------------------
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
    os.mkdir("title")

    sys.stderr.write("TITLE: ly2video will generate cca "
                     + str(fps * titleLength) + " frames.\n")

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
    for frameNum in range(fps * titleLength):
        titleScreen.save("./title/frame" + str(frameNum) + ".png")
        
    sys.stderr.write("TITLE: Generating title screen has ended. ("
                     + str(fps * titleLength) + "/"
                     + str(fps * titleLength) + ")\n")
    return 0
# ------------------------------------------------------------------------------
def writePaperHeader(fFile, resolution, pixelsPerMm, numOfLines):
    """
    Writes own paper block into given file.

    Params:
    - fFile:        given opened file
    - resolution:   wanted resolution of video
    - pixelsPerMm:  how many pixels are in one millimeter
    - numOfLines:   number of staff lines
    """

    fFile.write("\\paper {\n")
    fFile.write("   paper-width = "
                + str(round(10 * resolution[0] * pixelsPerMm)) + "\\mm\n")
    fFile.write("   paper-height = "
                + str(round(resolution[1] * pixelsPerMm)) + "\\mm\n")
    fFile.write("   top-margin = "
                + str(round(resolution[1] * pixelsPerMm / 20)) + "\\mm\n")
    fFile.write("   bottom-margin = "
                + str(round(resolution[1] * pixelsPerMm / 20)) + "\\mm\n")
    fFile.write("   left-margin = "
                + str(round(resolution[0] * pixelsPerMm / 2)) + "\\mm\n")
    fFile.write("   right-margin = "
                + str(round(resolution[0] * pixelsPerMm / 2)) + "\\mm\n")
    fFile.write("   print-page-number = ##f\n")
    fFile.write("}\n")
    fFile.write("#(set-global-staff-size "
                + str(int(round((resolution[1] - 2 * (resolution[1] / 10)) / numOfLines)))
                + ")\n\n")
    
    return 0
# ------------------------------------------------------------------------------
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

    # how many notes start in one tick
    notesInTick = dict()

    # for every channel in MIDI (except the first one)
    for eventsList in midiFile[1:]:
        # for every event
        for event in eventsList:
            # if it's NoteOnEvent
            if isinstance(event, midi.NoteOnEvent):
                # and velocity is not zero (that's basically "NoteOffEvent")
                if (event.data[1] != 0):
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
            if (endOfTrack < eventsList[-1].tick):
                endOfTrack = eventsList[-1].tick
    midiTicks.append(endOfTrack)
    
    sys.stderr.write("MIDI: Parsing MIDI file has ended.\n")
    
    return (midiResolution, temposList, notesInTick, midiTicks)
# ------------------------------------------------------------------------------
def getNotesIndexes(pdf, imageWidth, loadedProject, midiTicks, notesInTick):
    """
    Returns indexes of notes in generated PNG pictures (through PDF file).

    Params:
    - pdf:              name of generated PDF file (string)
    - imageWidth:       width of PNG file(s) 
    - loadedProject:    loaded *.ly file in memory (list)
    - midiTicks:        all ticks with notes in MIDI file
    - notesInTick:      how many notes starts in one tick
    """

    # open PDf file with external library and gets width of page (in PDF measures)
    fPdf = file(pdf, "rb")
    pdfFile = PdfFileReader(fPdf) 
    pageWidth = pdfFile.getPage(0).getObject()['/MediaBox'][2]

    # stores positions of notes and ligatures in LY file
    notesAndLigatures = set()
    # stores wanted positions (notes and ligatures) in LY and PDF file
    wantedPos = []
    
    for pageNumber in range(pdfFile.getNumPages()):
        # get informations about page
        page = pdfFile.getPage(pageNumber)
        info = page.getObject()

        # ly parser (from Frescobaldi)
        parser = Tokenizer()

        if info.has_key('/Annots'):
            links = info['/Annots']

            # stores wanted positions on single page
            wantedPosPage = []
            
            for link in links:
                # get coordinates of that link
                coords = link.getObject()['/Rect']
                # if it's not link into ly2videoConvert.ly, then ignore it
                if link.getObject()['/A']['/URI'].find("ly2videoConvert.ly") == -1:
                    continue
                # otherwise get coordinates into LY file
                linkLy = link.getObject()['/A']['/URI'].split(":")[-3:]
                
                try:
                    # get name of that note
                    note = parser.tokens(loadedProject[int(linkLy[0]) - 1][int(linkLy[1]):]).next()

                    # is that note ok?
                    noteOk = True
                    for token in parser.tokens(loadedProject[int(linkLy[0]) - 1][int(linkLy[1])
                                                                                 + len(note):]):
                        # if there is another note right next to it (or rest, etc.), it's ok 
                        if token.__class__.__name__ == "PitchWord":
                            break
                        # if its "note with \rest", it's NOT ok and ignore it
                        elif (token.__class__.__name__ == "Command"
                              and repr(token) == "u'\\\\rest'"):
                            noteOk = False
                            break
                    # if the note is ok and it's not rest or it's ligature
                    if noteOk:
                        if ((note.__class__.__name__ == "PitchWord" and str(note) not in "rR")
                            or (note.find("~") != -1)):
                            # add it
                            wantedPosPage.append(((int(linkLy[0]), int(linkLy[1])), coords))
                            notesAndLigatures.add((int(linkLy[0]), int(linkLy[1])))
                #if there is some error, write that statement and exit
                except Exception as err:
                    sys.stderr.write("ERROR:\n")
                    sys.stderr.write("> PDF: There has been some error, "
                                     + " ly2video is trying to work with this: \""
                                     + loadedProject[int(linkLy[0]) - 1][int(linkLy[1]):][:-1]
                                     + "\", coords in LY (" + str((int(linkLy[0]), int(linkLy[1])))
                                     + ").\n")
                    sys.stderr.write("> Statement: " + str(err))
                    sys.exit()
                    
            # sort wanted positions on that page and add it into whole wanted positions
            wantedPosPage.sort()
            wantedPos.append(wantedPosPage)
            
    # create list of notes and ligatures and sort it        
    notesAndLigatures = list(notesAndLigatures)
    notesAndLigatures.sort()    

    # how many notes are in one position
    notesInIndex = []
    # indexes of all notes
    allNotesIndexes = []

    for page in wantedPos: 
        parser = Tokenizer()
        # how many notes are in one position (on one page)
        notesInIndexPage = dict()

        # notes in ligature        
        silentNotes = []
        for (linkLy, coords) in page:
            # get that token
            token = parser.tokens(loadedProject[linkLy[0] - 1][linkLy[1]:]).next()                     

            # if it's note
            if (token.__class__.__name__ == "PitchWord"):
                # if it's silent note, then remove it and ignore it
                if linkLy in silentNotes:
                    silentNotes.remove(linkLy)
                    continue
                # otherwise get its index in pixels
                noteIndex = int(round((float((coords[0] / pageWidth * imageWidth)
                                             + (coords[2] / pageWidth * imageWidth))) / 2))
                # add that index into indexes
                if notesInIndexPage.get(noteIndex) == None:
                    notesInIndexPage[noteIndex] = 1
                else:
                    notesInIndexPage[noteIndex] += 1
            # if it's ligature
            elif token.find("~") != -1:
                    # if next note isn't in silent notes, add it
                    if silentNotes.count(notesAndLigatures[notesAndLigatures.index(linkLy) + 1]) == 0:
                        silentNotes.append(notesAndLigatures[notesAndLigatures.index(linkLy) + 1])
                    # otherwise add next one (after the last silent one (if it's ligature of harmony))
                    else:
                        silentNotes.append(notesAndLigatures[notesAndLigatures.index(silentNotes[-1]) + 1]) 

        # gets all indexes on one page and sort it
        notesIndexesPage = notesInIndexPage.keys()
        notesIndexesPage.sort()

        # merges near indexes
        skip = False
        for index in notesIndexesPage[:-1]:
            if skip:
                skip = False
                continue
            # gets next index
            tmp = notesIndexesPage[notesIndexesPage.index(index) + 1]
            # if this index is in its range +/- 10 pixels
            if index in range(tmp - 10, tmp + 10):
                # merges them and remove next index
                notesInIndexPage[index] += notesInIndexPage.get(tmp)
                notesInIndexPage.pop(tmp)
                notesIndexesPage.remove(tmp)
                skip = True

        # stores info about this page        
        notesInIndex.append(notesInIndexPage)
        allNotesIndexes.append(notesIndexesPage)
        
        sys.stderr.write("PDF: Page " + str(wantedPos.index(page) + 1) + "/"
                         + str(len(wantedPos)) + " has been completed.\n")

    # notesIndexes = final indexes of notes
    notesIndexes = []
    # index into list of MIDI ticks
    midiIndex = 0

    for page in allNotesIndexes:
        # final indexes of notes on one page
        notesIndexesPage = []
        # skips next index (if needed)
        skip = False
        
        for index in page:
            # if runs out of midi indexes, then exit
            if midiIndex == len(midiTicks):
                sys.stderr.write("ERROR: ly2video don't have enough MIDI indexes. "
                                 + "Current PDF index: " + str(index) +".\n")
                sys.exit()
                
            # skip next index
            if skip:
                skip = False
                continue
            
            # if number of notes in one tick (MIDI) <= number of notes in one index (PNG)
            if (notesInTick.get(midiTicks[midiIndex])
                <= notesInIndex[allNotesIndexes.index(page)].get(index)):
                # add that index
                notesIndexesPage.append(index)
            else:
                # if there is next index on my right
                if index != page[-1]:
                    # get number of notes in right index
                    rightIndex = notesInIndex[allNotesIndexes.index(page)].get(page[page.index(index) + 1])
                    # compare them and get add that with more notes
                    if notesInIndex[allNotesIndexes.index(page)].get(index) >= rightIndex:
                        notesIndexesPage.append(index)
                    else:
                        notesIndexesPage.append(page[page.index(index) + 1])
                # otherwise just add that index (it's last index on that page)
                else:
                    notesIndexesPage.append(index)
                # and of course skip next index
                skip = True
            # go to next MIDI index
            midiIndex += 1
        # add indexes on one page into finel notesIndexes
        notesIndexes.append(notesIndexesPage)
        
    # close PDF file
    fPdf.close()
    
    return notesIndexes
# ------------------------------------------------------------------------------
def sync(midiResolution, temposList, midiTicks, resolution, fps, notesIndexes,
         notesPictures, color):
    """
    Generates frames for video, synchronized with audio.

    Params:
    - midiResolution:   resolution of MIDI file
    - temposList:       list of possible tempos in MIDI
    - midiTicks:        list of ticks with NoteOnEvent
    - resolution:       resolution of generated frames (and video)
    - fps:              frame rate of video
    - notesIndexes:     indexes of notes in picutres
    - notesPictures:    names of that pictures (list of strings)
    - color:            color of middle line
    """

    midiIndex = 0
    tempoIndex = 0
    frameNum = 0

    # folder to store frames for video
    os.mkdir("notes")

    totalFrames = int(round(((temposList[tempoIndex][1] * 1.0)
                        / midiResolution * (midiTicks[-1]) / 1000000 * fps)))
    sys.stderr.write("SYNC: ly2video will generate cca "
                     + str(totalFrames) + " frames.\n")

    dropFrame = 0.0
    
    for indexes in notesIndexes:
        # open picture of staff
        notesPic = Image.open(notesPictures[notesIndexes.index(indexes)]) 

        # add index for the last note
        indexes.append(indexes[-1])

        for index in indexes[:-1]:
            # get two indexes of notes (pixels)
            startIndex = index
            endIndex = indexes[indexes.index(index) + 1]

            # get two indexes of MIDI events (ticks)
            startMidi = midiTicks[midiIndex]
            midiIndex += 1
            endMidi = midiTicks[midiIndex]

            # if there's gonna be change in tempo, change it
            if (tempoIndex != (len(temposList) - 1)):
                if (startMidi == temposList[tempoIndex + 1][0]):
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
                if (dropFrame >= 1.0):
                    dropFrame -= 1.0
                    continue
                else:
                    # get frame from picture of staff, args - (("left upper corner", "right lower corner"))
                    leftUpper = int(startIndex + round(posun * shift)
                                    - (resolution[0] / 2))
                    rightUpper = int(startIndex + round(posun * shift)
                                     + (resolution[0] / 2))
                    frame = notesPic.copy().crop((leftUpper, 0, rightUpper, resolution[1]))
                    # add middle line
                    for pixel in range(resolution[1]):
                        frame.putpixel((resolution[0] / 2, pixel), color)
                        frame.putpixel(((resolution[0] / 2) + 1, pixel), color)

                    # save that frame
                    frame.save("./notes/frame" + str(frameNum) + ".png")
                    frameNum += 1

        sys.stderr.write("SYNC: Generating frames for page "
                         + str(notesIndexes.index(indexes) + 1) + "/"
                         + str(len(notesIndexes)) + " has beeen completed. ("
                         + str(frameNum) + "/" + str(totalFrames) + ")\n")
# ------------------------------------------------------------------------------
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
# ------------------------------------------------------------------------------
def output_divider_line():
    sys.stderr.write(60 * "-" + "\n")
# ------------------------------------------------------------------------------

# MAIN ----------------------------------------------------------------------------------------------
def main():
    """
    Main function of ly2video script.
    """
    
    # create parser and add options
    parser = OptionParser("usage: %prog [options]")

    parser.add_option("-i", "--input", dest="input",
                  help="input LilyPond project", metavar="FILE")
    parser.add_option("-o", "--output", dest="output",
                  help="name of output video (e.g. \"myNotes.avi\", default is input + .avi)",
                      metavar="FILE")
    parser.add_option("-c", "--color", dest="color",
                  help="name of color of middle bar (default is \"red\")", metavar="COLOR",
                      default="red")
    parser.add_option("-f", "--fps", dest="fps",
                  help="frame rate of final video (default is \"30\")", type="int", metavar="FPS",
                      default=30)
    parser.add_option("-r", "--resolution", dest="resolution",
                  help="resolution of final video (options: 360, 720, 1080, default is \"720\")",
                      metavar="HEIGHT", type="int", default=720)
    parser.add_option("--title-at-start", dest="titleAtStart",
                  help="adds title screen at the start of video (with name of song and its author)",
                      action="store_true", default=False)
    parser.add_option("--title-delay", dest="titleDelay",
                  help="time to display the title screen (default is \"3\" seconds)", type="int",
                      metavar="SECONDS", default=3)
    parser.add_option("--windows-ffmpeg", dest="winFfmpeg",
                  help="(for Windows users) folder with ffpeg.exe (e.g. \"C:\\ffmpeg\\bin\\\")",
                      metavar="PATH", default="")
    parser.add_option("--windows-timidity", dest="winTimidity",
                  help="(for Windows users) folder with timidity.exe (e.g. \"C:\\timidity\\\")",
                      metavar="PATH", default="")

    # if there is only one arg, then show help and exit
    if(len(sys.argv) == 1):
        parser.print_help()
        return 0
    # and parse input
    (options, args) = parser.parse_args()

    # test needed programs
    redirect = ""
    if sys.platform.startswith("linux"):
        redirect = "/dev/null"
    elif sys.platform.startswith("win"):
        redirect = "NUL"
    
    if (os.system("lilypond -v > " + redirect) != 0):
        sys.stderr.write("ERROR: LilyPond was not found.\n")
        return 1
    else:
        sys.stderr.write("LilyPond was found.\n")

    winFfmpeg = options.winFfmpeg
    winTimidity = options.winTimidity
    if (os.system(winFfmpeg + "ffmpeg -version > " + redirect) != 0):
        sys.stderr.write("ERROR: FFmpeg was not found (maybe use --windows-ffmpeg?).\n")
        return 2
    else:
        sys.stderr.write("FFmpeg was found.\n")
        
    if (os.system(winTimidity + "timidity -v > " + redirect) != 0):
        sys.stderr.write("ERROR: TiMidity++ was not found (maybe use --windows-timidity?).\n")
        return 3
    else:
        sys.stderr.write("TiMidity++ was found.\n")
    output_divider_line()

    # input project from user (string)
    project = options.input
    # opened project from user (pointer)
    fProject = None
    # output file
    output = options.output

    # color of middle line
    color = (255,0,0)
    options.color = options.color.lower()
    if (options.color == "black"):
        color = (0,0,0)
    elif (options.color == "yellow"):
        color = (255,255,0)
    elif (options.color == "red"):
        color = (255,0,0)
    elif (options.color == "green"):
        color = (0,128,0)
    elif (options.color == "blue"):
        color = (0,0,255)
    elif (options.color == "brown"):
        color = (165,42,42)
    else:
        sys.stderr.write("ERROR: Color was not found, " +
                         "ly2video will use default one (\"red\").\n")

    # frame rate of output video
    fps = options.fps
    
    # resolution of output video
    resolution = (1280, 720)
    if (options.resolution == 360):
        resolution = (640, 360)
    elif (options.resolution == 720):
        resolution = (1280, 720)
    elif (options.resolution == 1080):
        resolution = (1920, 1080)
    else:
        sys.stderr.write("ERROR: Resolution was not found, " + 
                         "ly2video will use default one (\"720\" => 1280x720).\n")
    # title and all about it
    useTitle = options.titleAtStart
    if (useTitle):
        titleLength = options.titleDelay
    else:
        titleLength = 0
    titleText = collections.namedtuple("titleText", "name author")
    titleText.name = "<name of song>"
    titleText.author = "<author>"

    # if I don't have input file, end  
    if (project == None):
        sys.stderr.write("ERROR: Input project was not found.\n")
        return 4
    else:
        # otherwise try to open project
        try:
            fProject = open(project, "r") 
        except (IOError):
            sys.stderr.write("ERROR: Input project doesn't exist.\n")
            return 5

    # try to chech output name
    if (output == None or len(output.split(".")) < 2):
        output = project[:-2] + "avi"
        
    # delete old created folders
    for folder in ["notes", "title"]:   
        try:
            shutil.rmtree(folder)
        except os.error:
            continue
    # delete old created files   
    for fileName in os.listdir("."):
        if "ly2videoConvert" in fileName:
            try:
                os.remove(fileName)
            except Exception as err:
                sys.stderr.write("ERROR:\n")
                sys.stderr.write("> Ly2video can't delete old files.\n")
                sys.stderr.write("> Statement: " + str(err) + "\n")
                return 6
       
    # 1 px = 0.251375 mm
    pixelsInMm = 181.0 / 720
    
    # prepinac set-global-staff-size
    sirka = int(round(resolution[0] * pixelsInMm)) # základní šířka

    # find version of LilyPond in input project
    version = ""
    for line in fProject.readlines():
        if (line.find("\\version") != -1):
            parser = Tokenizer()
            for token in parser.tokens(line):
                if token.__class__.__name__ == "StringQuoted":
                    version = str(token)[1:-1]
                    break
            if version != "":
                break
    fProject.close()
    
    # if it's not 2.14.2, try to convert it
    if version != "2.14.2":
        if os.system("convert-ly " + project + " > newProject.ly") == 0:
            project = "newProject.ly"
        else:
            sys.stderr.write("WARNING: Convert of input file has failed, " +
                             "there can be some errors.\n")
            output_divider_line()
    fProject = open(project, "r")

    # generate preview of notes
    if (os.system("lilypond -dmidi-extension=midi -dpreview -dprint-pages=#f "
                  + project + " 2> " + redirect) != 0):
        sys.stderr.write("ERROR: Generating preview has failed.\n")
        return 7

    # find preview picture and get num of staff lines
    previewPic = ""
    previewFilesTmp = os.listdir(".")
    previewFiles = []
    for soubor in previewFilesTmp:
        if "preview" in soubor:
            previewFiles.append(soubor)
            if soubor.split(".")[-1] == "png":
                previewPic = soubor
    numStaffLines = len(lineIndexes(previewPic, 50))

    # then delete generated preview files
    try:
        for soubor in previewFiles:    
            os.remove(soubor)
        os.remove(project[:-2] + "midi")
    except Exception as err:
        sys.stderr.write("ERROR:\n")
        sys.stderr.write("> Ly2video can't delete preview files.\n")
        sys.stderr.write("> Statement: " + str(err) + "\n")
        return 8

    # create own ly project
    fMyProject = open("ly2videoConvert.ly", "w")

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

        if (line.find("\\partial") != -1):
            sys.stderr.write("WARNING: Ly2video has found \"\\partial\" command " +
                             "in your project. There can be some errors.\n")

        # ignore these commands
        if (line.find("\\include \"articulate.ly\"") != -1
            or line.find("\\pointAndClickOff") != -1
            or line.find("#(set-global-staff-size") != -1
            or line.find("\\bookOutputName") != -1):
            line = fProject.readline()

        # if I find version, write own paper block right behind it
        if (line.find("\\version") != -1):
            done = True
            fMyProject.write(line)
            writePaperHeader(fMyProject, resolution, pixelsInMm, numStaffLines)
            paperBlock = True

        # get needed info from header block and ignore it
        if (line.find("\\header") != -1 or headerPart) and not done:
            if line.find("\\header") != -1:
                fMyProject.write("\\header {\n   tagline = ##f composer = ##f\n}\n")
                headerPart = True
                
            done = True
            
            if (line.find("title = ") != -1):
                titleText.name = line.split("=")[-1].strip()[1:-1]
            if (line.find("composer = ") != -1):
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
        if (not headerPart and not paperPart and not done):
            finalLine = ""
            
            if (line.find("\\break") != -1):
                finalLine = (line[:line.find("\\break")]
                             + line[line.find("\\break") + len("\\break"):])
            elif (line.find("\\noBreak") != -1):
                finalLine = (line[:line.find("\\noBreak")]
                             + line[line.find("\\noBreak") + len("\\noBreak"):])
            elif (line.find("\\pageBreak") != -1):
                finalLine = (line[:line.find("\\pageBreak")]
                             + line[line.find("\\pageBreak") + len("\\pageBreak"):])
            elif (line.find("\\articulate") != -1):
                finalLine = (line[:line.find("\\articulate")]
                             + line[line.find("\\articulate") + len("\\articulate"):])
            else:
                finalLine = line
                
            fMyProject.write(finalLine)
            
        line = fProject.readline()

    fProject.close()

    # if I didn't find \version, write own paper block
    if not paperBlock:
        writePaperHeader(fMyProject, resolution, pixelsInMm, numStaffLines)
    fMyProject.close()

    # load own project into memory
    fMyProject = open("ly2videoConvert.ly", "r")
    loadedProject = []
    for line in fMyProject.readlines():
        loadedProject.append(line)
    fMyProject.close()
    
    # generate PDF, PNG and MIDI file
    if (os.system("lilypond -fpdf --png -dpoint-and-click "
                  + "-dmidi-extension=midi ly2videoConvert.ly") != 0):
        sys.stderr.write("ERROR: Calling LilyPond has failed.\n")
        return 9
    output_divider_line()

    # delete created project
    os.remove("ly2videoConvert.ly")
    # and try to delete converted project
    if version != "2.14.2":
        try:
            os.remove("newProjekt.ly")
        except:
            pass

    # find generated pictures
    folderContent = os.listdir(".")
    notesPictures = []
    for fileName in folderContent:
        if (fileName.split(".")[-1] == "png" and "ly2videoConvert" in fileName):
            sys.stderr.write("found generated picture: %s\n" % fileName)
            notesPictures.append(fileName)
    output_divider_line()

    # and get width of picture        
    tmpPicuture = Image.open(notesPictures[0])
    picWidth = tmpPicuture.size[0]
    del tmpPicuture

    # find needed data in MIDI
    try:
        midiResolution, temposList, notesInTick, midiTicks = getMidiEvents("ly2videoConvert.midi")
    except Exception as err:
        sys.stderr.write("ERROR:\n")
        sys.stderr.write("> MIDI: There has been some error.\n")
        sys.stderr.write("> Statement: " + str(err) + "\n")
        return 10
        
    output_divider_line()

    # find notes indexes
    notesIndexes = getNotesIndexes("ly2videoConvert.pdf",
                                   picWidth, loadedProject, midiTicks, notesInTick)
    output_divider_line()
    
    # generate title screen
    if (useTitle):
        generateTitle(titleText, resolution, fps, titleLength)
    output_divider_line()

    # generate notes
    sync(midiResolution, temposList, midiTicks, resolution,
         fps, notesIndexes, notesPictures, color)
    output_divider_line()

    # call TiMidity++ to convert MIDI (ly2videoConvert.wav)
    try:
        subprocess.check_call([winTimidity + "timidity", "ly2videoConvert.midi", "-Ow"])
    except subprocess.CalledProcessError as err:
        sys.stderr.write("ERROR:\n")
        sys.stderr.write("> TiMidity++: There has been some error.\n")
        sys.stderr.write("> Statement: " + str(err) + "\n")
        return 11
    output_divider_line()

    # delete old files
    try:
        for picture in notesPictures:
            os.remove(picture)
        os.remove("ly2videoConvert.pdf")
        os.remove("ly2videoConvert.midi")
    except Exception as err:
        sys.stderr.write("ERROR:\n")
        sys.stderr.write("> Ly2video can't delete some files.\n")
        sys.stderr.write("> Statement: " + str(err) + "\n")
        return 12

    # call FFmpeg (without title)
    if not useTitle:
        if os.system(winFfmpeg + "ffmpeg -f image2 -r " + str(fps)
                     + " -i ./notes/frame%d.png -i ly2videoConvert.wav "
                     + output) != 0:
            sys.stderr.write("ERROR: Calling FFmpeg has failed.\n")
            return 13
    # call FFmpeg (with title)
    else:
        # create video with title
        silentAudio = generateSilence(titleLength)
        if os.system(winFfmpeg + "ffmpeg -f image2 -r " + str(fps)
                     + " -i ./title/frame%d.png -i "
                     + silentAudio + " -same_quant title.mpg") != 0:
            sys.stderr.write("ERROR: Calling FFmpeg has failed.\n")
            return 14
        # generate video with notes
        if os.system(winFfmpeg + "ffmpeg -f image2 -r " + str(fps)
                     + " -i ./notes/frame%d.png -i ly2videoConvert.wav "
                     + "-same_quant notes.mpg") != 0:
            sys.stderr.write("ERROR: Calling FFmpeg has failed.\n")
            return 15
        # join the files
        if sys.platform.startswith("linux"):
            os.system("cat title.mpg notes.mpg > video.mpg")
        elif sys.platform.startswith("win"):
            os.system("copy title.mpg /B + notes.mpg /B video.mpg /B")

        # create output file
        if os.system(winFfmpeg + "ffmpeg -i video.mpg " + output) != 0:
            sys.stderr.write("ERROR: Calling FFmpeg has failed.\n")
            return 16

        # delete created videos, silent audio and folder with title frames
        os.remove("title.mpg")
        os.remove("notes.mpg")
        os.remove("video.mpg")
        os.remove(silentAudio)
        shutil.rmtree("title")
    output_divider_line()
        
    # delete wav file and folder with notes frames
    os.remove("ly2videoConvert.wav")
    shutil.rmtree("notes")

    # end
    print("Ly2video has ended. Your generated file: " + output + ".")
    return 0  
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
