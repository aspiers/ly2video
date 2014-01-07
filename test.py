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

import unittest
from video import *
from PIL import Image
        
class VideoFrameWriterTest(unittest.TestCase):

    def setUp(self):
        self.frameWriter = VideoFrameWriter(
                                       width            = 16,
                                       height           = 16,
                                       fps              = 30.0,
                                       cursorLineColor  = (255,0,0),
                                       scrollNotes      = False,
                                       leftMargin       = 50,
                                       rightMargin      = 100,
                                       midiResolution   = 384,
                                       midiTicks        = [0, 384, 768, 1152, 1536],
                                       temposList       = [(0, 60.0)]
        )
        self.image = Image.new("RGB",(16,16),(255,255,255))
        for x in range(16) : self.image.putpixel((x,8),(0,0,0))

        
    def testIsLineBlank (self):
        pixels = self.image.load()
        #pixels = [[(255,255,255),(255,255,255),(255,255,255)],[(255,255,255),(255,255,255),(255,255,255)],[(255,255,255),(255,255,255),(255,255,255)]]
        w, h = self.image.size
        self.assertTrue(self.frameWriter.isLineBlank(pixels, w, 0), "Line should be blank")
        self.assertFalse(self.frameWriter.isLineBlank(pixels, w, 8), "Line should not be blank")
        
    def testIsLineBlank_withLineAlmostBlack (self):
        w, h = self.image.size
        pixels = self.image.load()
        for x in range(15) : self.image.putpixel((x,10),(0,0,0))
        self.assertFalse(self.frameWriter.isLineBlank(pixels, w, 10), "Line should not be blank")

    def testIsLineBlank_withLineAlmostBlank (self):
        w, h = self.image.size
        pixels = self.image.load()
        self.image.putpixel((4,4),(0,0,0))
        self.assertFalse(self.frameWriter.isLineBlank(pixels, w, 4), "Line should not be blank")
        
    def testGetTopAndBottomMarginSizes_withBlackImage (self):
        image = Image.new("RGB",(16,16),(0,0,0))
        topMarginSize, bottomMarginSize = self.frameWriter.getTopAndBottomMarginSizes(image)
        self.assertEqual(topMarginSize, 0, "Bad topMarginSize")
        self.assertEqual(bottomMarginSize, 0, "Bad bottomMarginSize")

    def testGetTopAndBottomMarginSizes_withBlankImage (self):
        image = Image.new("RGB",(16,16),(255,255,255))
        with self.assertRaises(SystemExit) as cm:
            topMarginSize, bottomMarginSize = self.frameWriter.getTopAndBottomMarginSizes(image)
        self.assertEqual(cm.exception.code, 1)

    def testGetTopAndBottomMarginSizes_withHorizontalBlackLine (self):
        image = Image.new("RGB",(16,16),(255,255,255))
        for x in range(16) : image.putpixel((x,8),(0,0,0))
        topMarginSize, bottomMarginSize = self.frameWriter.getTopAndBottomMarginSizes(image)
        self.assertEqual(topMarginSize, 8, "Bad topMarginSize")
        self.assertEqual(bottomMarginSize, 7, "Bad bottomMarginSize")

    def testGetTopAndBottomMarginSizes_withBlackPoint (self):
        image = Image.new("RGB",(16,16),(255,255,255))
        image.putpixel((8,8),(0,0,0))
        topMarginSize, bottomMarginSize = self.frameWriter.getTopAndBottomMarginSizes(image)
        self.assertEqual(topMarginSize, 8, "Bad topMarginSize")
        self.assertEqual(bottomMarginSize, 7, "Bad bottomMarginSize")

    def testGetCropTopAndBottom_withBlackImage(self):
        self.frameWriter.height = 16
        image = Image.new("RGB",(16,16),(0,0,0))
        cropTop, cropBottom = self.frameWriter.getCropTopAndBottom(image)
        self.assertEqual(cropTop, 0, "Bad cropTop!")
        self.assertEqual(cropBottom, 16, "Bad cropBottom!")

    def testGetCropTopAndBottom_withBlackImageTooSmall(self):
        self.frameWriter.height = 17
        image = Image.new("RGB",(16,16),(0,0,0))
        with self.assertRaises(SystemExit) as cm:
            cropTop, cropBottom = self.frameWriter.getCropTopAndBottom(image)
        self.assertEqual(cm.exception.code, 1)

    def testGetCropTopAndBottom_withBlackImageTooBig(self):
        self.frameWriter.height = 15
        image = Image.new("RGB",(16,16),(0,0,0))
        with self.assertRaises(SystemExit) as cm:
            cropTop, cropBottom = self.frameWriter.getCropTopAndBottom(image)
        self.assertEqual(cm.exception.code, 1)

    def testGetCropTopAndBottom_withBlackPoint (self):
        image = Image.new("RGB",(16,16),(255,255,255))
        image.putpixel((8,8),(0,0,0))
        self.frameWriter.height = 9
        cropTop, cropBottom = self.frameWriter.getCropTopAndBottom(image)
        self.assertEqual(cropTop, 4, "Bad cropTop!")
        self.assertEqual(cropBottom, 13, "Bad cropBottom!")

    def testGetCropTopAndBottom_withVideoHeightTooSmall (self):
        self.frameWriter.height = 20
        image = Image.new("RGB",(30,30),(255,255,255))
        image.putpixel((8,4),(0,0,0))
        image.putpixel((8,12),(0,0,0))
        with self.assertRaises(SystemExit) as cm:
            cropTop, cropBottom = self.frameWriter.getCropTopAndBottom(image)
        self.assertEqual(cm.exception.code, 1)

    def testGetCropTopAndBottom_withNonCenteredContent (self):
        image = Image.new("RGB",(16,16),(255,255,255))
        image.putpixel((8,4),(0,0,0))
        image.putpixel((8,12),(0,0,0))
        self.frameWriter.height = 8
        with self.assertRaises(SystemExit) as cm:
            cropTop, cropBottom = self.frameWriter.getCropTopAndBottom(image)
        self.assertEqual(cm.exception.code, 1)
        
    def testTicksToSecs (self):
        for tempo in range (1,300):
            self.frameWriter.tempo = float(tempo)
            secsSinceStartIndex = self.frameWriter.ticksToSecs(0, 0)
            self.assertEqual(secsSinceStartIndex, 0.0, "")
        self.frameWriter.tempo = 60.0
        secsSinceStartIndex = self.frameWriter.ticksToSecs(0, 384)
        self.assertEqual(secsSinceStartIndex, 1.0, "")
        secsSinceStartIndex = self.frameWriter.ticksToSecs(0, 768)
        self.assertEqual(secsSinceStartIndex, 2.0, "")
        self.frameWriter.tempo = 90.0
        secsSinceStartIndex = self.frameWriter.ticksToSecs(0, 1152)
        self.assertEqual(secsSinceStartIndex, 2.0, "")
        secsSinceStartIndex = self.frameWriter.ticksToSecs(0, 3456)
        self.assertEqual(secsSinceStartIndex, 6.0, "")
        
    def testSecsElapsedForTempoChanges (self):
        self.frameWriter.temposList = [(0, 60.0),(1152, 90.0),(3456, 60.0)]
        result = self.frameWriter.secsElapsedForTempoChanges(startTick = 0, endTick = 1152, startIndex = 0, endIndex = 2)
        self.assertEqual(result,3.0,"")
        result = self.frameWriter.secsElapsedForTempoChanges(startTick = 0, endTick = 3456, startIndex = 0, endIndex = 2)
        self.assertEqual(result,6.0,"")
        result = self.frameWriter.secsElapsedForTempoChanges(startTick = 1152, endTick = 3456, startIndex = 0, endIndex = 2)
        self.assertEqual(result,4.0,"")
        result = self.frameWriter.secsElapsedForTempoChanges(startTick = 3456, endTick = 4608, startIndex = 0, endIndex = 2)
        self.assertEqual(result,3.0,"")
        result = self.frameWriter.secsElapsedForTempoChanges(startTick = 0, endTick = 4608, startIndex = 0, endIndex = 2)
        self.assertEqual(result,12.0,"")

    def testFindStaffLinesInImage (self):
        image = Image.new("RGB",(1000,200),(255,255,255))
        for x in range(51) : image.putpixel((x+20,20),(0,0,0))
        staffX, staffYs = findStaffLinesInImage(image, 50)
        self.assertEqual(staffX, 23, "")
        self.assertEqual(staffYs[0], 20, "")
        
    def testCropFrame (self):
        image = Image.new("RGB",(1000,200),(255,255,255))
        ox=20
        for x in range(51) : image.putpixel((x+ox,20),(0,0,0))
        #cropTop, cropBottom = self.getCropTopAndBottom(image)
        self.frameWriter.width=200
        self.frameWriter.leftMargin = 50
        self.frameWriter.rightMargin = 50
        index = 70
        frame, cursorX = self.frameWriter.cropFrame(notesPic = image, index = index, top = 10, bottom = 190)
        w,h = frame.size
        print "cursorX = %d, width = %d, height = %d" % (cursorX,w,h)
        self.assertEqual(w, 200, "")
        self.assertEqual(h, 180, "")
        self.assertEqual(cursorX, self.frameWriter.leftMargin - (ox+3) + index%(self.frameWriter.width-self.frameWriter.rightMargin) , "")
        self.assertEqual(cursorX, 97 , "")
    
    def testCropFrame_withIndexHigherThanWidth (self):
        image = Image.new("RGB",(1000,200),(255,255,255))
        ox=20
        for x in range(51) : image.putpixel((x+ox,20),(0,0,0))
        #cropTop, cropBottom = self.getCropTopAndBottom(image)
        self.frameWriter.width=200
        self.frameWriter.leftMargin = 50
        self.frameWriter.rightMargin = 50
        index = 200
        frame, cursorX = self.frameWriter.cropFrame(notesPic = image, index = index, top = 10, bottom = 190)
        w,h = frame.size
        print "cursorX = %d, width = %d, height = %d" % (cursorX,w,h)
        self.assertEqual(w, 200, "")
        self.assertEqual(h, 180, "")
        self.assertEqual(cursorX, index%(self.frameWriter.width-self.frameWriter.rightMargin) , "")
        self.assertEqual(cursorX, 50 , "")
    
if __name__ == "__main__":
    unittest.main()