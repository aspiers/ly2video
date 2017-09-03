# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008, 2009, 2010 by Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.

from __future__ import unicode_literals

""" LilyPond information and logic concerning durations """

import ly.rx


durations = ['\\maxima', '\\longa', '\\breve',
    '1', '2', '4', '8', '16', '32', '64', '128', '256', '512', '1024', '2048']

def editRhythm(func):
    """
    Decorator to handle functions that are the callback for the regexp.
    """
    def decorator(text):
        def repl(m):
            return m.group('duration') and func(m) or m.group()
        return ly.rx.chord_rest.sub(repl, text)
    return decorator

@editRhythm
def doubleDurations(m):
    chord, dur, dots, scale = m.group('chord', 'dur', 'dots', 'scale')
    if dur in durations:
        i = durations.index(dur)
        if i > 0:
            dur = durations[i - 1]
    return ''.join(i or '' for i in (chord, dur, dots, scale))

@editRhythm
def halveDurations(m):
    chord, dur, dots, scale = m.group('chord', 'dur', 'dots', 'scale')
    if dur in durations:
        i = durations.index(dur)
        if i < len(durations) - 1:
            dur = durations[i + 1]
    return ''.join(i or '' for i in (chord, dur, dots, scale))

@editRhythm
def dotDurations(m):
    chord, dur, dots, scale = m.group('chord', 'dur', 'dots', 'scale')
    dots = (dots or '') + '.'
    return ''.join(i or '' for i in (chord, dur, dots, scale))

@editRhythm
def undotDurations(m):
    chord, dur, dots, scale = m.group('chord', 'dur', 'dots', 'scale')
    if dots:
        dots = dots[1:]
    return ''.join(i or '' for i in (chord, dur, dots, scale))

@editRhythm
def removeScaling(m):
    return ''.join(i or '' for i in m.group('chord', 'dur', 'dots'))

@editRhythm
def removeDurations(m):
    return m.group('chord')

def makeImplicit(text):
    old = ['']
    def repl(m):
        chord, duration = m.group('chord', 'duration')
        if chord:
            if not duration or duration == old[0]:
                return chord
            else:
                old[0] = duration
                return chord + duration
        return m.group()
    return ly.rx.chord_rest.sub(repl, text)

def makeImplicitPerLine(text):
    return '\n'.join(makeImplicit(t) for t in makeExplicit(text).split('\n'))
    
def makeExplicit(text):
    old = ['']
    def repl(m):
        chord, duration = m.group('chord', 'duration')
        if chord:
            if not duration:
                return chord + old[0]
            else:
                old[0] = duration
                return chord + duration
        return m.group()
    return ly.rx.chord_rest.sub(repl, text)

def applyRhythm(text, rhythm):
    """ Adds the entered rhythm to the selected music."""
    durs = [m.group() for m in ly.rx.finddurs.finditer(rhythm)]
    if not durs:
        return text
    def durgen():
        old = ''
        while True:
            for i in durs:
                yield i != old and i or ''
                old = i
    durations = durgen()
    def repl(m):
        if m.group('chord'):
            return m.group('chord') + next(durations)
        return m.group()
    return ly.rx.chord_rest.sub(repl, text)

def extractRhythm(text):
    """ Iterate over a rhythm from text, returning only the durations """
    duration = ''
    for m in ly.rx.chord_rest.finditer(text):
        if m.group('chord'):
            if m.group('duration'):
                duration = m.group('duration')
            yield duration

