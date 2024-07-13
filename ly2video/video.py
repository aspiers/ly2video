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

from ly2video.synchro import *
from ly2video.utils import *
import os
from PIL import Image


# for compatible with python3, if xrange doesn't exists, use range instead
try:
    xrange
except NameError:
    xrange = range


# Image manipulation functions

def writeCursorLine(image, X, color):
    """Draws a line on the image"""
    for pixel in range(image.size[1]):
        image.putpixel((X    , pixel), color)
        image.putpixel((X + 1, pixel), color)

def writeMeasureCursor(image, start, end, color, cursor_height=10):
    """Draws a box at the bottom of the image"""
    w, h = image.size
    if start > w :
        raise Exception()
    for dx in range(end-start) :
        for y in range(cursor_height):
            if start + dx < w and start + dx > 0 :
                image.putpixel((start + dx, h-y-1), color)

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
    for x in range(width):
        for y in range(height):
            for length in range(lineLength):
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

    for y in range(firstLineY, height):
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

    The VideoFrameWriter can manage severals medias. So the push method
    can be used to stack medias one above the other.
    """

    def __init__(self, fps, cursorLineColor,
                 midiResolution, midiTicks, temposList):
        """
        Params:
          - fps:               frame rate of video
          - cursorLineColor:   color of middle line
          - midiResolution:    resolution of MIDI file
          - midiTicks:         list of ticks with NoteOnEvent
          - temposList:        list of possible tempos in MIDI
        """
        self.frameNum    = 0

        # In cursor scrolling mode, this is the x-coordinate in the
        # original image of the left edge of the frame (i.e. the
        # left edge of the cropping rectangle).
        self.leftEdge = None

        self.width = None
        self.height = None
        self.fps = fps
        self.cursorLineColor = cursorLineColor

        self.runDir = None

        self.__scoreImage = None
        self.__medias = []
        self.__timecode = TimeCode (midiTicks,temposList,midiResolution,fps)

        self.firstFrame = None
        self.lastFrame = None

    def push (self, media):
        self.height += media.height
        self.__medias.append(media)
        self.__timecode.registerObserver(media)

    @property
    def scoreImage (self):
        return self.__scoreImage

    @scoreImage.setter
    def scoreImage (self, scoreImage):
        self.width = scoreImage.width
        self.height = scoreImage.height
        self.__scoreImage = scoreImage
        self.__scoreImage.cursorLineColor = self.cursorLineColor
        self.__timecode.registerObserver(scoreImage)

    @property
    def frames (self):
        while not self.__timecode.atEnd() :
            neededFrames = self.__timecode.nbFramesToNextNote()
            for i in range(neededFrames):
                frame = self.__makeFrame(i, neededFrames)
                if not self.firstFrame:
                    self.firstFrame = frame

                self.frameNum += 1
                yield frame
            else:
                self.lastFrame = frame

            self.__timecode.goToNextNote()

    def write (self):
        # folder to store frames for video
        if not os.path.exists("notes"):
            os.mkdir("notes")

        for videoFrame in self.frames:
            # Save the frame.  ffmpeg doesn't work if the numbers in these
            # filenames are zero-padded.
            videoFrame.save(tmpPath("notes", "frame%d.png" % self.frameNum))
            if not DEBUG and self.frameNum % 10 == 0:
                sys.stdout.write(".")
                sys.stdout.flush()

    def __makeFrame (self, numFrame, among):
        debug("        writing frame %d" % (self.frameNum))

        videoFrame = Image.new("RGB", (self.width,self.height), "white")
        scoreFrame = self.__scoreImage.makeFrame(numFrame, among)
        w, h =  scoreFrame.size
        videoFrame.paste(scoreFrame,(0,self.height-h,w,self.height))
        for media in self.__medias :
            mediaFrame = media.makeFrame(numFrame, among)
            wm, hm =  mediaFrame.size
            w = max(w,wm)
            h += hm
            videoFrame.paste(mediaFrame, (0,self.height-h,wm,self.height-h+hm))
        return videoFrame


class BlankScoreImageError (Exception):
    pass

class Media (object):

    """
    Abstract class which is handled by the VideoFrameWriter. ScoreImage
    and SlideShow classes inherit from it.
    """

    def __init__ (self, width = 1280, height = 720):
        self.__width = width
        self.__height = height

    @property
    def width (self):
        return self.__width

    @property
    def height (self):
        return self.__height

    def makeFrame (self, numframe, among):
        pass

    def update (self, timecode):
        pass

class ScoreImage (Media):

    """
    This class manages:
        - the image following: currentXposition(), travelToNextNote(),
          moveToNextNote(), notesXpositions methods
        - the frame drawing: the makeFrame() method.
    This class handles the 'measure cursor', a new type of cursor.
    """

    def __init__ (self, width, height, picture, notesXpostions, measuresXpositions, leftMargin = 50, rightMargin = 50, scrollNotes = None, noteCursor = True):
        """
        Params:
          - width:             pixel width of frames (and video)
          - height:            pixel height of frames (and video)
          - picture:           the long width picture
          - notesXpostions:    positions in pixel of notes
          - measuresXpositions:positions in pixel of measures bars
          - leftMargin:        left margin for cursor when
                               cursor scrolling mode is enabled
          - rightMargin:       right margin for cursor when
                               cursor scrolling mode is enabled
          - scrollNotes:       False selects cursor scrolling mode,
                               True selects note scrolling mode
        """
        Media.__init__(self, width, height)
        self.__picture = picture
        self.__notesXpositions = notesXpostions
        if len(self.__notesXpositions) > 0 :
            self.__notesXpositions.append(self.__notesXpositions[-1])
        self.__measuresXpositions = measuresXpositions
        #self.__measuresXpositions.append(self.__measuresXpositions[-1])
        self.__currentMeasureIndex = 0
        self.__currentNotesIndex = 0
        self.__topCroppable = None
        self.__bottomCroppable = None
        self.leftMargin = leftMargin
        self.rightMargin = rightMargin
        self.__leftEdge = None
        self.__cropTop = None
        self.__cropBottom = None
        self.__noteCursor = noteCursor
        self.scrollNotes = scrollNotes
        self.cursorLineColor = (255,0,0)

    @property
    def currentXposition (self):
        return self.__notesXpositions[self.__currentNotesIndex]

    @property
    def travelToNextNote (self):
        return self.__notesXpositions[self.__currentNotesIndex+1] - self.__notesXpositions[self.__currentNotesIndex]

    def moveToNextNote (self):
        self.__currentNotesIndex += 1
        if self.__measuresXpositions:
            if self.currentXposition > self.__measuresXpositions[self.__currentMeasureIndex+1] :
                self.__currentMeasureIndex += 1

    @property
    def notesXpostions (self):
        return self.__notesXpositions

    @property
    def picture (self):
        return self.__picture

    def __setCropTopAndBottom(self):
        """
        set the y-coordinates of the top and
        bottom edges of the cropping rectangle, relative to the given
        (non-cropped) image.
        """
        if self.__cropTop is not None and self.__cropBottom is not None: return
        picture_width, picture_height = self.__picture.size

        bottomY = picture_height - self.bottomCroppable
        progress("      Video height: %5d pixels" % self.height)
        progress("      Image height: %5d pixels" % picture_height)
        progress("   Top margin size: %5d pixels" % self.topCroppable)
        progress("Bottom margin size: %5d pixels (y=%d)" %
                 (self.bottomCroppable, bottomY))

        nonWhiteRows = picture_height - self.topCroppable - self.bottomCroppable
        progress("Visible content is formed of %d non-white rows of pixels" %
                 nonWhiteRows)

        # y-coordinate of centre of the visible content, relative to
        # the original non-cropped image
        nonWhiteCentre = self.topCroppable + int(round(nonWhiteRows/2))
        progress("Centre of visible content is %d pixels from top" %
                 nonWhiteCentre)

        # Now choose top/bottom cropping coordinates which center
        # the content in the video frame.
        self.__cropTop    = nonWhiteCentre - int(round(self.height / 2))
        self.__cropBottom = self.__cropTop + self.height

        # Figure out the maximum height allowed which keeps the
        # cropping rectangle within the source image.
        maxTopHalf    =    self.topCroppable + nonWhiteRows / 2
        maxBottomHalf = self.bottomCroppable + nonWhiteRows / 2
        maxHeight = min(maxTopHalf, maxBottomHalf) * 2

        if self.__cropTop < 0:
            fatal("Would have to crop %d pixels above top of image! "
                  "Try increasing the resolution DPI (option -r)"
                  "(which would increase the size of the PNG to be cropped), "
                  "or reducing the video height to at most %d (option -y)." %
                  (-self.__cropTop, maxHeight))
            self.__cropTop = 0

        if self.__cropBottom > picture_height:
            fatal("Would have to crop %d pixels below bottom of image! "
                  "Try increasing the resolution DPI (option -r)"
                  "(which would increase the size of the PNG to be cropped), "
                  "or reducing the video height to at most %d (option -y)." %
                  (self.__cropBottom - picture_height, maxHeight))
            self.__cropBottom = picture_height

        if self.__cropTop > self.topCroppable:
            fatal("Would have to crop %d pixels below top of visible content! "
                  "Try increasing the video height to at least %d (option -y), "
                  "or decreasing the resolution DPI (option -r)."
                  % (self.__cropTop - self.topCroppable, nonWhiteRows))
            self.__cropTop = self.topCroppable

        if self.__cropBottom < bottomY:
            fatal("Would have to crop %d pixels above bottom of visible content! "
                  "Try increasing the video height to at least %d (option -y), "
                  "or decreasing the resolution DPI (option -r)."
                  % (bottomY - self.__cropBottom, nonWhiteRows))
            self.__cropBottom = bottomY

        progress("Will crop from y=%d to y=%d" % (self.__cropTop, self.__cropBottom))

    def __cropFrame(self,index):
        self.__setCropTopAndBottom()
        picture_width, picture_height = self.__picture.size

        if self.scrollNotes:
            # Get frame from image of staff
            cursorX = int(self.width * self.scrollNotes)
            left  = int(index - cursorX)
            right = int(index - cursorX + self.width)
            cropped = self.picture.crop((max(left, 0), self.__cropTop,
                                         min(picture_width, right), self.__cropBottom))

            if left < 0 or right > picture_width:
                # Paste the cropped frame onto white background
                frame = Image.new('RGB', (self.width, self.height), (255, 255, 255))
                frame.paste(cropped, (max(-left, 0), 0))
            else:
                frame = cropped
        else:
            if self.__leftEdge is None:
                # first frame
                staffX, staffYs = findStaffLinesInImage(self.picture, 50)
                self.__leftEdge = staffX - self.leftMargin

            cursorX = index - self.__leftEdge
            debug("        left edge at %d, cursor at %d" %
                  (self.__leftEdge, cursorX))
            if cursorX > self.width - self.rightMargin:
                self.__leftEdge = index - self.leftMargin
                cursorX = index - self.__leftEdge
                debug("        <<< left edge at %d, cursor at %d" %
                      (self.__leftEdge, cursorX))
            if picture_width - self.__leftEdge < self.width :
                self.__leftEdge = picture_width - self.width
                # the cursor has to finish its travel in the last picture cropping
                self.rightMargin = 0
            rightEdge = self.__leftEdge + self.width
            frame = self.picture.crop((self.__leftEdge, self.__cropTop,
                                          rightEdge, self.__cropBottom))
        return (frame,cursorX)

    def makeFrame (self, numFrame, among):
        startIndex  = self.currentXposition
        indexTravel = self.travelToNextNote
        travelPerFrame = float(indexTravel) / among
        index = startIndex + int(round(numFrame * travelPerFrame))

        scoreFrame, cursorX = self.__cropFrame(index)

        # Cursors
        if self.__measuresXpositions :
            origin = index - cursorX
            start = self.__measuresXpositions[self.__currentMeasureIndex] - origin
            end = self.__measuresXpositions[self.__currentMeasureIndex + 1] - origin
            writeMeasureCursor(scoreFrame, start, end, self.cursorLineColor)
        elif self.__noteCursor:
            writeCursorLine(scoreFrame, cursorX, self.cursorLineColor)

        return scoreFrame

    def __isLineBlank(self, pixels, width, y):
        """
        Returns True if the line with the given y coordinate
        is entirely white.
        """
        for x in range(width):
            if pixels[x, y] != (255, 255, 255):
                return False
        return True

    def __setTopCroppable (self):
        # This is way faster than width*height invocations of getPixel()
        picture_width, picture_height = self.__picture.size
        pixels = self.__picture.load()
        progress("Auto-detecting top margin; this may take a while ...")
        self.__topCroppable = 0
        for y in range(picture_height):
            if y == picture_height - 1:
                raise BlankScoreImageError
            if self.__isLineBlank(pixels, picture_width, y):
                self.__topCroppable += 1
            else:
                break

    def __setBottomCroppable (self):
        # This is way faster than width*height invocations of getPixel()
        picture_width, picture_height = self.__picture.size
        pixels = self.__picture.load()
        progress("Auto-detecting top margin; this may take a while ...")
        self.__bottomCroppable = 0
        for y in range(picture_height - 1, -1, -1):
            if y == 0:
                raise BlankScoreImageError
            if self.__isLineBlank(pixels, picture_width, y):
                self.__bottomCroppable += 1
            else:
                break

    @property
    def topCroppable (self): # raises BlankScoreImageError
        if self.__topCroppable is None:
            self.__setTopCroppable()
        return self.__topCroppable

    @property
    def bottomCroppable (self):
        if self.__bottomCroppable is None:
            self.__setBottomCroppable()
        return self.__bottomCroppable

    def update (self, timecode):
        self.moveToNextNote()

class SlideShow (Media):

    """
    This class is needed to run show composed of several pictures as
    the music is playing. A horizontal line cursor can be added if needed.
    """

    def __init__(self, fileNamePrefix, cursorPos = None, lastOffset = None):
        self.__fileNamePrefix = fileNamePrefix
        self.__fileName = "%s%09.4f.png" % (self.__fileNamePrefix,0.0)
        self.__slide = Image.open(self.__fileName)
        Media.__init__(self,self.__slide.size[0], self.__slide.size[1])
        self.cursorLineColor = (255,0,0)

        # get cursor travelling data
        if cursorPos and lastOffset:
            self.__cursorStart = float(cursorPos[0])
            self.__cursorEnd = float(cursorPos[1])
            self.__lastOffset = lastOffset
            self.__scale = (self.__cursorEnd - self.__cursorStart)/self.__lastOffset
        else:
            self.__cursorStart = None


        self.startOffset = 0.0
        self.endOffset = 0.0

    def makeFrame (self, numFrame, among):
        # We check if the slide must change
        start = self.startOffset * self.__scale
        end = self.endOffset * self.__scale
        travelPerFrame = float(end - start) / among
        index = start + int(round(numFrame * travelPerFrame)) + self.__cursorStart

        newFileName = "%s%09.4f.png" % (self.__fileNamePrefix,self.startOffset)
        if newFileName != self.__fileName:
            self.__fileName = newFileName
            if os.path.exists(self.__fileName):
                self.__slide = Image.open(self.__fileName)
                debug ("Add slide from file " + self.__fileName)
        tmpSlide = self.__slide.copy()
        writeCursorLine(tmpSlide, int(index), self.cursorLineColor)
        return tmpSlide

    def update(self, timecode):
        self.startOffset = timecode.currentOffset
        self.endOffset = timecode.nextOffset
