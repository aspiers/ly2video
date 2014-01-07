#!/usr/bin/env python
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

from utils import *
import os
from PIL import Image

# Image manipulation functions

def writeCursorLine(image, X, color):
    """Draws a line on the image"""
    for pixel in xrange(image.size[1]):
        image.putpixel((X    , pixel), color)
        image.putpixel((X + 1, pixel), color)

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
        
        self.runDir = None
        
        self.__scoreImage = None

    def estimateFrames(self):
        approxBeats = float(self.midiTicks[-1]) / self.midiResolution
        debug("approx %.2f MIDI beats" % approxBeats)
        beatsPerSec = 60.0 / self.tempo
        approxDuration = approxBeats * beatsPerSec
        debug("approx duration: %.2f seconds" % approxDuration)
        estimatedFrames = approxDuration * self.fps
        progress("SYNC: ly2video will generate approx. %d frames at %.3f frames/sec." %
                 (estimatedFrames, self.fps))

    @property
    def scoreImage (self):
        return self.__scoreImage
        
    @scoreImage.setter
    def scoreImage (self, scoreImage):
        self.__scoreImage = scoreImage
        self.__scoreImage.areaWidth = self.width
        self.__scoreImage.areaHeight = self.height
        self.__scoreImage.cursorLineColor = self.cursorLineColor

    def write(self):
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
                self.secsElapsedForTempoChanges(0, initialTick)

        # generate all frames in between each pair of adjacent indices
        while self.midiIndex < len(self.midiTicks) - 1:
#            debug("\nwall-clock secs: %f" % self.secs)
#            debug("index: %d -> %d (indexTravel %d)" %
#                  (startIndex, endIndex, indexTravel))

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
                self.secsElapsedForTempoChanges(startTick, endTick)

            # This is the exact time we are *aiming* for the frameset
            # to finish at (i.e. the start time of the first frame
            # generated after the writeVideoFrames() invocation below
            # has written all the frames for the current frameset).
            # However, since we have less than an infinite number of
            # frames per second, there will typically be a rounding
            # error and we'll miss our target by a small amount.
            targetSecs = self.secs + secsSinceIndex

#            debug("    secs at new index %d: %f" %
#                  (endIndex, targetSecs))

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
                self.writeVideoFrames(neededFrames)

            # Update time in the *ideal* (i.e. not real) world - this
            # is totally independent of fps.
            self.secs = targetSecs
            self.__scoreImage.moveToNextNote()
        print

        progress("SYNC: Generated %d frames" % self.frameNum)

    def secsElapsedForTempoChanges(self, startTick, endTick):
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
            debug("        secs : %f" %
                  (secsSinceStartIndex))
            lastTick = tempoTick

        # Add on the time elapsed between the final tempo change
        # and endTick:
        secsSinceStartIndex += self.ticksToSecs(lastTick, endTick)

#        debug("    secs between indices %d and %d: %f" %
#              (startIndex, endIndex, secsSinceStartIndex))
        return secsSinceStartIndex

    def writeVideoFrames(self, neededFrames):
        """
        Writes the required number of frames to travel indexTravel
        pixels from startIndex, incrementing frameNum for each frame
        written.
        """
        for i in xrange(neededFrames):
            debug("        writing frame %d" % (self.frameNum))

            scoreFrame = self.__scoreImage.makeFrame(numFrame = i, among = neededFrames)
            w, h =  scoreFrame.size
            frame = Image.new("RGB", (w,h), "white")
            frame.paste(scoreFrame,(0,0,w,h))
                
            # Save the frame.  ffmpeg doesn't work if the numbers in these
            # filenames are zero-padded.
            frame.save(tmpPath("notes", "frame%d.png" % self.frameNum))
            self.frameNum += 1
            if not DEBUG and self.frameNum % 10 == 0:
                sys.stdout.write(".")
                sys.stdout.flush()   

    def ticksToSecs(self, startTick, endTick):
        beatsSinceTick = float(endTick - startTick) / self.midiResolution
        debug("        beats from tick %d -> %d: %f (%d ticks per beat)" %
              (startTick, endTick, beatsSinceTick, self.midiResolution))

        secsSinceTick = beatsSinceTick * 60.0 / self.tempo
        debug("        secs  from tick %d -> %d: %f (%.3f bpm)" %
              (startTick, endTick, secsSinceTick, self.tempo))

        return secsSinceTick
  
class BlankScoreImageError (Exception):
    pass

class Media (object):
    
    def __init__ (self, width = 1280, height = 720):
        self.__width = width
        self.__height = height
        
    @property
    def width (self):
        return self.__width
    
    @property
    def height (self):
        return self.__height

class ScoreImage (Media):
    
    def __init__ (self, picture, notesXpostions, leftMargin = 50, rightMargin = 50, scrollNotes = False):
        Media.__init__(self,picture.size[0], picture.size[1])
        self.__picture = picture
        self.__notesXpositions = notesXpostions
        if len(self.__notesXpositions) > 0 :
            self.__notesXpositions.append(self.__notesXpositions[-1])
        self.__currentNotesIndex = 0
        self.__topCroppable = None
        self.__bottomCroppable = None
        self.leftMargin = leftMargin
        self.rightMargin = rightMargin
        self.areaWidth = 1920
        self.areaHeight = 1080
        self.__leftEdge = None
        self.__cropTop = None
        self.__cropBottom = None
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

        bottomY = self.height - self.bottomCroppable
        progress("      Image height: %5d pixels" % self.height)
        progress("   Top margin size: %5d pixels" % self.topCroppable)
        progress("Bottom margin size: %5d pixels (y=%d)" %
                 (self.bottomCroppable, bottomY))

        nonWhiteRows = self.height - self.topCroppable - self.bottomCroppable
        progress("Visible content is formed of %d non-white rows of pixels" %
                 nonWhiteRows)

        # y-coordinate of centre of the visible content, relative to
        # the original non-cropped image
        nonWhiteCentre = self.topCroppable + int(round(nonWhiteRows/2))
        progress("Centre of visible content is %d pixels from top" %
                 nonWhiteCentre)

        # Now choose top/bottom cropping coordinates which center
        # the content in the video frame.
        self.__cropTop    = nonWhiteCentre - int(round(self.areaHeight / 2))
        self.__cropBottom = self.__cropTop + self.areaHeight

        # Figure out the maximum height allowed which keeps the
        # cropping rectangle within the source image.
        maxTopHalf    =    self.topCroppable + nonWhiteRows / 2
        maxBottomHalf = self.bottomCroppable + nonWhiteRows / 2
        maxHeight = min(maxTopHalf, maxBottomHalf) * 2

        if self.__cropTop < 0:
            fatal("Would have to crop %d pixels above top of image! "
                  "Try increasing the resolution DPI "
                  "(which would increase the size of the PNG to be cropped), "
                  "or reducing the video height to at most %d" %
                  (-self.__cropTop, maxHeight))
            self.__cropTop = 0

        if self.__cropBottom > self.height:
            fatal("Would have to crop %d pixels below bottom of image! "
                  "Try increasing the resolution DPI "
                  "(which would increase the size of the PNG to be cropped), "
                  "or reducing the video height to at most %d" %
                  (self.__cropBottom - self.height, maxHeight))
            self.__cropBottom = self.height

        if self.__cropTop > self.topCroppable:
            fatal("Would have to crop %d pixels below top of visible content! "
                  "Try increasing the video height to at least %d, "
                  "or decreasing the resolution DPI."
                  % (self.__cropTop - self.topCroppable, nonWhiteRows))
            self.__cropTop = self.topCroppable

        if self.__cropBottom < bottomY:
            fatal("Would have to crop %d pixels above bottom of visible content! "
                  "Try increasing the video height to at least %d, "
                  "or decreasing the resolution DPI."
                  % (bottomY - self.__cropBottom, nonWhiteRows))
            self.__cropBottom = bottomY

        progress("Will crop from y=%d to y=%d" % (self.__cropTop, self.__cropBottom))

    def __cropFrame(self,index):
        self.__setCropTopAndBottom()
        if self.scrollNotes:
            # Get frame from image of staff
            centre = self.width / 2
            left  = int(index - centre)
            right = int(index + centre)
            frame = self.picture.copy().crop((left, self.__cropTop, right, self.__cropBottom))
            cursorX = centre
        else:
            if self.__leftEdge is None:
                # first frame
                staffX, staffYs = findStaffLinesInImage(self.picture, 50)
                self.__leftEdge = staffX - self.leftMargin

            cursorX = index - self.__leftEdge
            debug("        left edge at %d, cursor at %d" %
                  (self.__leftEdge, cursorX))
            if cursorX > self.areaWidth - self.rightMargin:
                self.__leftEdge = index - self.leftMargin
                cursorX = index - self.__leftEdge
                debug("        <<< left edge at %d, cursor at %d" %
                      (self.__leftEdge, cursorX))

            rightEdge = self.__leftEdge + self.areaWidth
            frame = self.picture.copy().crop((self.__leftEdge, self.__cropTop,
                                          rightEdge, self.__cropBottom))
        return (frame,cursorX)

    def makeFrame (self, numFrame, among):
        startIndex  = self.currentXposition
        indexTravel = self.travelToNextNote
        travelPerFrame = float(indexTravel) / among
        index = startIndex + int(round(numFrame * travelPerFrame))

        scoreFrame, cursorX = self.__cropFrame(index)

        # Cursor
        writeCursorLine(scoreFrame, cursorX, self.cursorLineColor)

        return scoreFrame

    def __isLineBlank(self, pixels, width, y):
        """
        Returns True if the line with the given y coordinate
        is entirely white.
        """
        for x in xrange(width):
            if pixels[x, y] != (255, 255, 255):
                return False
        return True
            
    def __setTopCroppable (self):
        # This is way faster than width*height invocations of getPixel()
        pixels = self.__picture.load()
        progress("Auto-detecting top margin; this may take a while ...")
        self.__topCroppable = 0
        for y in xrange(self.height):
            if y == self.height - 1:
                raise BlankScoreImageError
            if self.__isLineBlank(pixels, self.width, y):
                self.__topCroppable += 1
            else:
                break

    def __setBottomCroppable (self):
        # This is way faster than width*height invocations of getPixel()
        pixels = self.__picture.load()
        progress("Auto-detecting top margin; this may take a while ...")
        self.__bottomCroppable = 0
        for y in xrange(self.height - 1, -1, -1):
            if y == 0:
                raise BlankScoreImageError
            if self.__isLineBlank(pixels, self.width, y):
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
    
