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

shorthands = {
    'marcato': '^',
    'stopped': '+',
    'tenuto': '-',
    'staccatissimo': '|',
    'accent': '>',
    'staccato': '.',
    'portato': '_',
    }

def groups(i18nFunc=None):
    i18n = i18nFunc or (lambda s: s)
    return (
        (i18n("Articulation"), (
            ('accent', i18n("Accent")),
            ('marcato', i18n("Marcato")),
            ('staccatissimo', i18n("Staccatissimo")),
            ('staccato', i18n("Staccato")),
            ('portato', i18n("Portato")),
            ('tenuto', i18n("Tenuto")),
            ('espressivo', i18n("Espressivo")),
            )),
        (i18n("Ornaments"), (
            ('trill', i18n("Trill")),
            ('prall', i18n("Prall")),
            ('mordent', i18n("Mordent")),
            ('turn', i18n("Turn")),
            ('prallprall', i18n("Prall prall")),
            ('prallmordent', i18n("Prall mordent")),
            ('upprall', i18n("Up prall")),
            ('downprall', i18n("Down prall")),
            ('upmordent', i18n("Up mordent")),
            ('downmordent', i18n("Down mordent")),
            ('prallup', i18n("Prall up")),
            ('pralldown', i18n("Prall down")),
            ('lineprall', i18n("Line prall")),
            ('reverseturn', i18n("Reverse turn")),
            )),
        (i18n("Signs"), (
            ('fermata', i18n("Fermata")),
            ('shortfermata', i18n("Short fermata")),
            ('longfermata', i18n("Long fermata")),
            ('verylongfermata', i18n("Very long fermata")),
            ('segno', i18n("Segno")),
            ('coda', i18n("Coda")),
            ('varcoda', i18n("Varcoda")),
            ('signumcongruentiae', i18n("Signumcongruentiae")),
            )),
        (i18n("Other"), (
            ('upbow', i18n("Upbow")),
            ('downbow', i18n("Downbow")),
            ('snappizzicato', i18n("Snappizzicato")),
            ('open', i18n("Open (e.g. brass)")),
            ('stopped', i18n("Stopped (e.g. brass)")),
            ('flageolet', i18n("Flageolet")),
            ('thumb', i18n("Thumb")),
            ('lheel', i18n("Left heel")),
            ('rheel', i18n("Right heel")),
            ('ltoe', i18n("Left toe")),
            ('rtoe', i18n("Right toe")),
            ('halfopen', i18n("Half open (e.g. hi-hat)")),
            )),
    )

def articulations(i18nFunc=None):
    """
    Yields two-tuples (name, translated title) for all articulations,
    usable to e.g. create a dict.
    """
    for title, group in groups(i18nFunc):
        for articulation in group:
            yield articulation

