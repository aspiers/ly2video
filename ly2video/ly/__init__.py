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

""" Basic LilyPond information and utility functions """


# Exceptions used by modules in this package
class NoMusicExpressionFound(Exception):
    """
    Raised if no music expression could be found in abs->rel.
    """
    pass


class QuarterToneAlterationNotAvailable(Exception):
    """
    Raised when there is no pitch name in the target languate
    when translating pitch names.
    """
    pass


_nums = (
    'Zero', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight',
    'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen',
    'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen')

_tens = (
    'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty',
    'Ninety', 'Hundred')

def nums(num):
    """
    Returns a textual representation of a number (e.g. 1 -> "One"), for use
    in LilyPond identifiers (that do not support digits).
    Supports numbers 0 to 109.
    """
    if num < 20:
        return _nums[num]
    d, r = divmod(num, 10)
    n = _tens[d-2]
    if r:
        n += _nums[r]
    return n


# Thanks: http://billmill.org/python_roman.html
_roman_numerals = (("M", 1000), ("CM", 900), ("D", 500), ("CD", 400),
("C", 100),("XC", 90),("L", 50),("XL", 40), ("X", 10), ("IX", 9), ("V", 5),
("IV", 4), ("I", 1))

def romanize(n):
    roman = []
    for ltr, num in _roman_numerals:
        k, n = divmod(n, num)
        roman.append(ltr * k)
    return "".join(roman)


def headers(i18nFunc=None):
    i18n = i18nFunc or (lambda s: s)
    return (
        ('dedication',  i18n("Dedication")),
        ('title',       i18n("Title")),
        ('subtitle',    i18n("Subtitle")),
        ('subsubtitle', i18n("Subsubtitle")),
        ('instrument',  i18n("Instrument")),
        ('composer',    i18n("Composer")),
        ('arranger',    i18n("Arranger")),
        ('poet',        i18n("Poet")),
        ('meter',       i18n("Meter")),
        ('piece',       i18n("Piece")),
        ('opus',        i18n("Opus")),
        ('copyright',   i18n("Copyright")),
        ('tagline',     i18n("Tagline")),
    )

headerNames = list(zip(*headers()))[0] # puvodne zip(*headers())[0]

def modes(i18nFunc=None):
    i18n = i18nFunc or (lambda s: s)
    return (
        ('major',       i18n("Major")),
        ('minor',       i18n("Minor")),
        ('ionian',      i18n("Ionian")),
        ('dorian',      i18n("Dorian")),
        ('phrygian',    i18n("Phrygian")),
        ('lydian',      i18n("Lydian")),
        ('mixolydian',  i18n("Mixolydian")),
        ('aeolian',     i18n("Aeolian")),
        ('locrian',     i18n("Locrian")),
    )

keys = (
    (0, 0), (0, 1),
    (1, -1), (1, 0), (1, 1),
    (2, -1), (2, 0),
    (3, 0), (3, 1),
    (4, -1), (4, 0), (4, 1),
    (5, -1), (5, 0), (5, 1),
    (6, -1), (6, 0),
)

keyNames = {
    'nederlands': (
        'C', 'Cis',
        'Des', 'D', 'Dis',
        'Es', 'E',
        'F', 'Fis',
        'Ges', 'G', 'Gis',
        'As', 'A', 'Ais',
        'Bes', 'B',
    ),
    'english': (
        'C', 'C#',
        'Db', 'D', 'D#',
        'Eb', 'E',
        'F', 'F#',
        'Gb', 'G', 'G#',
        'Ab', 'A', 'A#',
        'Bb', 'B',
    ),
    'deutsch': (
        'C', 'Cis',
        'Des', 'D', 'Dis',
        'Es', 'E',
        'F', 'Fis',
        'Ges', 'G', 'Gis',
        'As', 'A', 'Ais',
        'B', 'H',
    ),
    'norsk': (
        'C', 'Ciss',
        'Dess', 'D', 'Diss',
        'Ess', 'E',
        'F', 'Fiss',
        'Gess', 'G', 'Giss',
        'Ass', 'A', 'Aiss',
        'B', 'H',
    ),
    'italiano': (
        'Do', 'Do diesis',
        'Re bemolle', 'Re', 'Re diesis',
        'Mi bemolle', 'Mi',
        'Fa', 'Fa diesis',
        'Sol bemolle', 'Sol', 'Sol diesis',
        'La bemolle', 'La', 'La diesis',
        'Si bemolle', 'Si',
    ),
    'espanol': (
        'Do', 'Do sostenido',
        'Re bemol', 'Re', 'Re sostenido',
        'Mi bemol', 'Mi',
        'Fa', 'Fa sostenido',
        'Sol bemol', 'Sol', 'Sol sostenido',
        'La bemol', 'La', 'La sostenido',
        'Si bemol', 'Si',
    ),
    'vlaams': (
        'Do', 'Do kruis',
        'Re mol', 'Re', 'Re kruis',
        'Mi mol', 'Mi',
        'Fa', 'Fa kruis',
        'Sol mol', 'Sol', 'Sol kruis',
        'La mol', 'La', 'La kruis',
        'Si mol', 'Si',
    ),
}

keyNames['svenska'] = keyNames['norsk']
keyNames['suomi'] = keyNames['deutsch']
keyNames['catalan'] = keyNames['italiano']
keyNames['portugues'] = keyNames['espanol']

paperSizes = ['a3', 'a4', 'a5', 'a6', 'a7', 'legal', 'letter', '11x17']
