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

class ScoreImageTest (unittest.TestCase):
    
    def setUp(self):
        image = Image.new("RGB",(1000,200),(255,255,255))
        self.blankImage = ScoreImage(1000,200,image, [], [])
        image = Image.new("RGB",(1000,200),(255,255,255))
        image.putpixel((500,50),(0,0,0))
        image.putpixel((500,149),(0,0,0))
        self.pointsImage = ScoreImage(1000,200,image, [], [])

    # PRIVATE METHODS
    # __isLineBlank
    def test__IsLineBlank (self):
        image = Image.new("RGB",(16,16),(255,255,255))
        for x in range(16) : image.putpixel((x,8),(0,0,0))
        pixels = image.load()
        w, h = image.size
        self.assertTrue(self.blankImage._ScoreImage__isLineBlank(pixels, w, 0), "Line should be blank")
        self.assertFalse(self.blankImage._ScoreImage__isLineBlank(pixels, w, 8), "Line should not be blank")

    def test__IsLineBlank_withLineAlmostBlack (self):
        image = Image.new("RGB",(16,16),(255,255,255))
        for x in range(15) : image.putpixel((x,10),(0,0,0))
        w, h = image.size
        pixels = image.load()
        self.assertFalse(self.blankImage._ScoreImage__isLineBlank(pixels, w, 10), "Line should not be blank")

    def test__IsLineBlank_withLineAlmostBlank (self):
        image = Image.new("RGB",(16,16),(255,255,255))
        image.putpixel((4,4),(0,0,0))
        w, h = image.size
        pixels = image.load()
        self.assertFalse(self.blankImage._ScoreImage__isLineBlank(pixels, w, 4), "Line should not be blank")

    # __setCropTopAndBottom
    def test__setCropTopAndBottom_withBlackImage(self):
        blackImage = ScoreImage(16,16,Image.new("RGB",(16,16),(0,0,0)), [], [])
        blackImage._ScoreImage__setCropTopAndBottom()
        self.assertEqual(blackImage._ScoreImage__cropTop, 0, "Bad cropTop!")
        self.assertEqual(blackImage._ScoreImage__cropBottom, 16, "Bad cropBottom!")

    def test__setCropTopAndBottom_withBlackImageTooSmall(self):
        blackImage = ScoreImage(16,17,Image.new("RGB",(16,16),(0,0,0)), [], [])
        with self.assertRaises(SystemExit) as cm:
            blackImage._ScoreImage__setCropTopAndBottom()
        self.assertEqual(cm.exception.code, 1)

    def test__setCropTopAndBottom_withBlackImageTooBig(self):
        blackImage = ScoreImage(16,17,Image.new("RGB",(16,16),(0,0,0)), [], [])
        with self.assertRaises(SystemExit) as cm:
            blackImage._ScoreImage__setCropTopAndBottom()
        self.assertEqual(cm.exception.code, 1)

    def test__setCropTopAndBottom_withBlackPoint(self):
        image = Image.new("RGB",(16,16),(255,255,255))
        image.putpixel((8,8),(0,0,0))
        blackPointImage = ScoreImage(16,9,image, [], [])
        #blackPointImage.areaHeight = 9
        blackPointImage._ScoreImage__setCropTopAndBottom()
        self.assertEqual(blackPointImage._ScoreImage__cropTop, 4, "Bad cropTop!")
        self.assertEqual(blackPointImage._ScoreImage__cropBottom, 13, "Bad cropBottom!")

    def test__setCropTopAndBottom_withNonCenteredContent(self):
        image = Image.new("RGB",(30,30),(255,255,255))
        image.putpixel((8,4),(0,0,0))
        image.putpixel((8,12),(0,0,0))
        scoreImage = ScoreImage(16,20,Image.new("RGB",(16,16),(0,0,0)), [], [])
        with self.assertRaises(SystemExit) as cm:
            scoreImage._ScoreImage__setCropTopAndBottom()
        self.assertEqual(cm.exception.code, 1)

    def test__setCropTopAndBottom_withVideoHeightTooSmall(self):
        image = Image.new("RGB",(16,16),(255,255,255))
        image.putpixel((8,4),(0,0,0))
        image.putpixel((8,12),(0,0,0))
        scoreImage = ScoreImage(16,8,Image.new("RGB",(16,16),(0,0,0)), [], [])
        with self.assertRaises(SystemExit) as cm:
            scoreImage._ScoreImage__setCropTopAndBottom()
        self.assertEqual(cm.exception.code, 1)

    # __cropFrame
    def test__cropFrame(self):
        image = Image.new("RGB",(1000,200),(255,255,255))
        ox=20
        for x in range(51) : image.putpixel((x+ox,20),(0,0,0))
        scoreImage = ScoreImage(200,40,image, [], [])
        index = 70
        areaFrame, cursorX = scoreImage._ScoreImage__cropFrame(index)
        w,h = areaFrame.size
        self.assertEqual(w, 200, "")
        self.assertEqual(h, 40, "")
        self.assertEqual(cursorX, 97 , "")
        
    def test__cropFrame_withIndexHigherThanWidth (self):
        image = Image.new("RGB",(1000,200),(255,255,255))
        ox=20
        for x in range(51) : image.putpixel((x+ox,20),(0,0,0))
        scoreImage = ScoreImage(200,40,image, [], [])
        index = 200
        areaFrame, cursorX = scoreImage._ScoreImage__cropFrame(index)
        w,h = areaFrame.size
        self.assertEqual(w, 200, "")
        self.assertEqual(h, 40, "")
        self.assertEqual(cursorX, 50 , "")

    # PUBLIC METHODS
    # topCroppable
    def testTopCroppable_withBlackImage (self):
        blackImage = ScoreImage(16,16,Image.new("RGB",(16,16),(0,0,0)), [], [])
        self.assertEqual(blackImage.topCroppable, 0, "Bad topMarginSize")

    def testTopCroppable_withBlankImage (self):
        def testTopCroppable(image):
            return image.topCroppable
        blankImage = ScoreImage(16,16,Image.new("RGB",(16,16),(255,255,255)), [], [])
        self.assertRaises(BlankScoreImageError,testTopCroppable,blankImage)

    def testTopCroppable_withHorizontalBlackLine (self):
        image = Image.new("RGB",(16,16),(255,255,255))
        for x in range(16) : image.putpixel((x,8),(0,0,0))
        blackImage = ScoreImage(16,16,image, [], [])
        self.assertEqual(blackImage.topCroppable, 8, "Bad topMarginSize")

    def testTopCroppable_withBlackPoint (self):
        image = Image.new("RGB",(16,16),(255,255,255))
        image.putpixel((8,8),(0,0,0))
        blackImage = ScoreImage(16,16,image, [], [])
        self.assertEqual(blackImage.topCroppable, 8, "Bad topMarginSize")

    # bottomCroppable
    def testBottomCroppable_withBlackImage (self):
        blackImage = ScoreImage(16, 16, Image.new("RGB",(16,16),(0,0,0)), [], [])
        self.assertEqual(blackImage.bottomCroppable, 0, "Bad bottomMarginSize")

    def testBottomCroppable_withBlankImage (self):
        def testBottomCroppable(image):
            return image.bottomCroppable
        blankImage = ScoreImage(16, 16, Image.new("RGB",(16,16),(255,255,255)), [], [])
        self.assertRaises(BlankScoreImageError,testBottomCroppable,blankImage)

    def testBottomCroppable_withHorizontalBlackLine (self):
        image = Image.new("RGB",(16,16),(255,255,255))
        for x in range(16) : image.putpixel((x,8),(0,0,0))
        blackImage = ScoreImage(16, 16, image, [], [])
        self.assertEqual(blackImage.bottomCroppable, 7, "Bad topMarginSize")

    def testBottomCroppable_withBlackPoint (self):
        image = Image.new("RGB",(16,16),(255,255,255))
        image.putpixel((8,8),(0,0,0))
        blackImage = ScoreImage(16, 16, image, [], [])
        self.assertEqual(blackImage.bottomCroppable, 7, "Bad topMarginSize")
        
    # makeFrame
    def testMakeFrame (self):
        image = Image.new("RGB",(1000,200),(255,255,255))
        ox=20
        for x in range(51) : image.putpixel((x+ox,20),(0,0,0))
        scoreImage = ScoreImage(200, 40, image, [70, 100], [])
        scoreImage.areaWidth = 200
        scoreImage.areaHeight = 40
        areaFrame = scoreImage.makeFrame(numFrame = 10, among = 30)
        w,h = areaFrame.size
        self.assertEqual(w, 200, "")
        self.assertEqual(h, 40, "")
  
class CursorsTest (unittest.TestCase):
    
    def testWriteCursorLine (self):
        frame = Image.new("RGB",(16,16),(255,255,255))
        writeCursorLine(frame, 10, (255,0,0))
        for i in range (16):
            self.assertEqual(frame.getpixel((10,i)), (255,0,0), "")

    def testWriteCursorLineOut (self):
        frame = Image.new("RGB",(16,16),(255,255,255))
        self.assertRaises(Exception, writeCursorLine, frame, 20)
   
    def testWriteMeasureCursor (self):
        frame = Image.new("RGB",(16,16),(255,255,255))
        writeMeasureCursor(frame, 5, 10, (255,0,0))
        for i in range (5):
            self.assertEqual(frame.getpixel((5+i,14)), (255,0,0), "")

    def testWriteMeasureCursorOut (self):
        frame = Image.new("RGB",(16,16),(255,255,255))
        self.assertRaises(Exception, writeMeasureCursor, frame, 20, 30, (255,0,0))
    
class VideoFrameWriterTest(unittest.TestCase):

    def setUp(self):
        self.frameWriter = VideoFrameWriter(
                                       fps              = 30.0,
                                       cursorLineColor  = (255,0,0),
                                       midiResolution   = 384,
                                       midiTicks        = [0, 384, 768, 1152, 1536],
                                       temposList       = [(0, 60.0)]
        )
        self.image = Image.new("RGB",(16,16),(255,255,255))
        for x in range(16) : self.image.putpixel((x,8),(0,0,0))

        
    def testPush (self):
        frameWriter = VideoFrameWriter(30.0,(255,0,0),0,[],[])
        frameWriter.scoreImage = Media(1000,200)
        frameWriter.push(Media(100, 100))
        self.assertEqual(frameWriter.height, 300)
    
    def testScoreImageSetter (self):
        frameWriter = VideoFrameWriter(30.0,(255,0,0),0,[],[])
        frameWriter.scoreImage = ScoreImage(1000,200,Image.new("RGB",(1000,200),(255,255,255)), [], [])
        self.assertEqual(frameWriter.width, 1000)
        self.assertEqual(frameWriter.height, 200)
    
    def testWrite (self):
        pass
    
    def testWriteVideoFrames (self):
        pass
        
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
        result = self.frameWriter.secsElapsedForTempoChanges(startTick = 0, endTick = 1152)
        self.assertEqual(result,3.0,"")
        result = self.frameWriter.secsElapsedForTempoChanges(startTick = 0, endTick = 3456)
        self.assertEqual(result,6.0,"")
        result = self.frameWriter.secsElapsedForTempoChanges(startTick = 1152, endTick = 3456)
        self.assertEqual(result,4.0,"")
        result = self.frameWriter.secsElapsedForTempoChanges(startTick = 3456, endTick = 4608)
        self.assertEqual(result,3.0,"")
        result = self.frameWriter.secsElapsedForTempoChanges(startTick = 0, endTick = 4608)
        self.assertEqual(result,12.0,"")

    def testFindStaffLinesInImage (self):
        image = Image.new("RGB",(1000,200),(255,255,255))
        for x in range(51) : image.putpixel((x+20,20),(0,0,0))
        staffX, staffYs = findStaffLinesInImage(image, 50)
        self.assertEqual(staffX, 23, "")
        self.assertEqual(staffYs[0], 20, "")
        
    
if __name__ == "__main__":
    unittest.main()
