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

import sys
import os

DEBUG = False # --debug sets to True
RUNDIR = ""

def setDebug():
    global DEBUG
    DEBUG = True

def debug(text):
    if DEBUG:
        print(text)

def progress(text):
    print(text)

def stderr(text):
    sys.stderr.write(text + "\n")

def warn(text):
    stderr("WARNING: " + text)

def output_divider_line():
    progress(60 * "-")

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

def setRunDir (runDir):
    global RUNDIR
    RUNDIR = runDir

def tmpPath(*dirs):
    segments = [ 'ly2video.tmp' ]
    segments.extend(dirs)
    return os.path.join(RUNDIR, *segments)


class Observable:

    def __init__(self):
        self.__observers = []

    def registerObserver(self, observer):
        self.__observers.append(observer)

    def notifyObservers (self):
        for observer in self.__observers :
            observer.update(self)

class Observer:

    def update (self, observable):
        pass
