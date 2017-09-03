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

"""
Code dealing with Key signatures
"""

##
# The dicts key2num and num2key translate a key signature name to
# the number of accidentals. (0 = C, 1 = G, -1 = F, etc.)

key2num = {
    'ne': {
        'fes':-8, 'ces':-7, 'ges':-6, 'des':-5, 'as':-4,
        'aes':-4, 'es':-3, 'ees':-3, 'bes':-2, 'f':-1,
        'c':0, 'g':1, 'd':2, 'a':3, 'e':4, 'b':5, 'fis':6, 'cis':7,
        'gis':8, 'dis':9, 'ais':10, 'eis':11, 'bis':12
    },
    'en-short': {
        'ff':-8, 'cf':-7, 'gf':-6, 'df':-5,
        'af':-4, 'ef':-3, 'bf':-2, 'f':-1,
        'c':0, 'g':1, 'd':2, 'a':3, 'e':4, 'b':5, 'fs':6, 'cs':7,
        'gs':8, 'ds':9, 'as':10, 'es':11, 'bs':12
    },
    'en': {
        'fflat':-8, 'cflat':-7, 'gflat':-6, 'dflat':-5,
        'aflat':-4, 'eflat':-3, 'bflat':-2, 'f':-1,
        'c':0, 'g':1, 'd':2, 'a':3, 'e':4, 'b':5, 'fsharp':6, 'csharp':7,
        'gsharp':8, 'dsharp':9, 'asharp':10, 'esharp':11, 'bsharp':12
    },
    'de': {
        'fes':-8, 'ces':-7, 'ges':-6, 'des':-5, 'as':-4,
        'aes':-4, 'es':-3, 'ees':-3, 'b':-2, 'f':-1,
        'c':0, 'g':1, 'd':2, 'a':3, 'e':4, 'h':5, 'fis':6, 'cis':7,
        'gis':8, 'dis':9, 'ais':10, 'eis':11, 'his':12
    },
    'sv': {
        'fess':-8, 'cess':-7, 'gess':-6, 'dess':-5, 'ass':-4,
        'aess':-4, 'ess':-3, 'eess':-3, 'b':-2, 'f':-1,
        'c':0, 'g':1, 'd':2, 'a':3, 'e':4, 'h':5, 'fiss':6, 'ciss':7,
        'giss':8, 'diss':9, 'aiss':10, 'eiss':11, 'hiss':12
    },
    # no = (de|sv), su = de
    'it': {
        'fab':-8, 'dob':-7, 'solb':-6, 'reb':-5, 'lab':-4,
        'mib':-3, 'sib':-2, 'fa':-1,
        'do':0, 'sol':1, 're':2, 'la':3, 'mi':4, 'si':5, 'fad':6, 'dod':7,
        'sold':8, 'red':9, 'lad':10, 'mid':11, 'sid':12
    },
    'es': {
        'fab':-8, 'dob':-7, 'solb':-6, 'reb':-5, 'lab':-4,
        'mib':-3, 'sib':-2, 'fa':-1,
        'do':0, 'sol':1, 're':2, 'la':3, 'mi':4, 'si':5, 'fas':6, 'dos':7,
        'sols':8, 'res':9, 'las':10, 'mis':11, 'sis':12
    },
    # ca = (it|es), po = es
    'vl': {
        'fab':-8, 'dob':-7, 'solb':-6, 'reb':-5, 'lab':-4,
        'mib':-3, 'sib':-2, 'fa':-1,
        'do':0, 'sol':1, 're':2, 'la':3, 'mi':4, 'si':5, 'fak':6, 'dok':7,
        'solk':8, 'rek':9, 'lak':10, 'mik':11, 'sik':12
    },
}

def rdict(d):
    """ reverse a dict """
    return dict((v,k) for k,v in d.iteritems())

num2key = dict((lang, rdict(p)) for lang, p in key2num.iteritems())

##
# How many accidentals to add/substract for different modi.
modes = {
    'major': 0,
    'minor': -2,    # should be -3, but we want a sharp below the fifth
    'ionian': 0,
    'dorian': -2,
    'phrygian': -3, # should be -4, but we want a sharp below the octave
    'lydian': 1,
    'mixolydian': -1,
    'aeolian': -2,  # should be -3, but we want a sharp below the fifth
    'locrian': -5,
}
