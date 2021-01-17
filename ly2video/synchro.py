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

from ly2video.utils import *

class TimeCode (Observable):

    """
    The sychro.Timecode class handles the synchronisation data: atEnd(),
    gotToNextNote(), nbFramesToNextNote() methods.
    The 'Observer' design pattern to produce frames. The timecode object is a
    kind of 'conductor' of the process
    """

    def __init__(self, miditicks, temposList, midiResolution, fps):
        """
        Params:
          - midiTicks:         list of ticks with NoteOnEvent
          - temposList:        list of possible tempos in MIDI
          - midiResolution:    resolution of MIDI file
          - fps:               frame per sec. Needed to get the
                               needed frames between 2 notes
        """
        Observable.__init__(self)
        self.fps = fps
        self.__miditicks = miditicks
        self.__currentTickIndex = 0
        self.tempoIndex  = 0
        self.temposList = temposList
        self.midiResolution = midiResolution

        # Keep track of wall clock time to ensure that rounding errors
        # when aligning indices to frames don't accumulate over time.
        self.secs = 0.0

        self.__wroteFrames = 0

        firstTempoTick, self.tempo = self.temposList[self.tempoIndex]
        debug("first tempo is %.3f bpm" % self.tempo)
        debug("final MIDI tick is %d" % self.__miditicks[-1])

        self.estimateFrames()
        progress("Writing frames ...")
        if not DEBUG:
            progress("A dot is displayed for every 10 frames generated.")

        initialTick = self.__miditicks[self.__currentTickIndex]
        if initialTick > 0:
            #self.__miditicks = [0] + self.__miditicks
            debug("\ncalculating wall-clock start for first audible MIDI event")
            # This duration isn't used, but it's necessary to
            # calculate it like this in order to ensure tempoIndex is
            # correct before we start writing frames.
            silentPreludeDuration = \
                self.secsElapsedForTempoChanges(0, initialTick)

        self.__currentTick = self.__miditicks[self.__currentTickIndex]
        self.__nextTick = self.__miditicks[self.__currentTickIndex + 1]
        self.currentOffset = float(self.__currentTick)/self.midiResolution
        self.nextOffset = float(self.__nextTick)/self.midiResolution


    def atEnd(self):
        return self.__currentTickIndex + 2 >= len(self.__miditicks)

    def goToNextNote (self):
        self.__currentTickIndex += 1
        self.__currentTick = self.__miditicks[self.__currentTickIndex]
        self.__nextTick = self.__miditicks[self.__currentTickIndex+1]
        self.currentOffset = float(self.__currentTick)/self.midiResolution
        self.nextOffset = float(self.__nextTick)/self.midiResolution
        ticks = self.__nextTick - self.__currentTick
        debug("ticks: %d -> %d (%d)" % (self.__currentTick, self.__nextTick, ticks))

        self.notifyObservers()

    def nbFramesToNextNote(self):
        # If we have 1+ tempo changes in between adjacent indices,
        # we need to keep track of how many seconds elapsed since
        # the last one, since this will allow us to calculate how
        # many frames we need in between the current pair of
        # indices.
        secsSinceIndex = self.secsElapsedForTempoChanges(self.__currentTick, self.__nextTick)

        # This is the exact time we are *aiming* for the frameset
        # to finish at (i.e. the start time of the first frame
        # generated after the writeVideoFrames() invocation below
        # has written all the frames for the current frameset).
        # However, since we have less than an infinite number of
        # frames per second, there will typically be a rounding
        # error and we'll miss our target by a small amount.
        targetSecs = self.secs + secsSinceIndex
        debug("    secs at new tick %d: %f" % (self.__nextTick, targetSecs))

        # The ideal duration of the current frameset is the target
        # end time minus the *actual* start time, not the ideal
        # start time.  This is crucially important to avoid
        # rounding errors from accumulating over the course of the
        # video.
        neededFrameSetSecs = targetSecs - float(self.__wroteFrames)/self.fps
        debug("    need next frameset to last %f secs" % neededFrameSetSecs)

        debug("    need %f frames @ %.3f fps" % (neededFrameSetSecs * self.fps, self.fps))
        neededFrames = int(round(neededFrameSetSecs * self.fps))
        self.__wroteFrames += neededFrames
        # Update time in the *ideal* (i.e. not real) world - this
        # is totally independent of fps.
        self.secs = targetSecs

        return neededFrames

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

    def ticksToSecs(self, startTick, endTick):
        beatsSinceTick = float(endTick - startTick) / self.midiResolution
        debug("        beats from tick %d -> %d: %f (%d ticks per beat)" %
              (startTick, endTick, beatsSinceTick, self.midiResolution))

        secsSinceTick = beatsSinceTick * 60.0 / self.tempo
        debug("        secs  from tick %d -> %d: %f (%.3f bpm)" %
              (startTick, endTick, secsSinceTick, self.tempo))

        return secsSinceTick

    def estimateFrames(self):
        approxBeats = float(self.__miditicks[-1]) / self.midiResolution
        debug("approx %.2f MIDI beats" % approxBeats)
        beatsPerSec = 60.0 / self.tempo
        approxDuration = approxBeats * beatsPerSec
        debug("approx duration: %.2f seconds" % approxDuration)
        estimatedFrames = approxDuration * self.fps
        progress("SYNC: ly2video will generate approx. %d frames at %.3f frames/sec." %
                 (estimatedFrames, self.fps))
