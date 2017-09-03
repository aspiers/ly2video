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

""" All kinds or regular expressions dealing with the LilyPond format """

import re

step = (
    r"\b("
    r"[a-h]("
        r"(iss){1,2}|(ess){1,2}|(is){1,2}|(es){1,2}"
        r"|(sharp){1,2}|(flat){1,2}|ss?|x|ff?"
        r"|(is)?ih|(es)eh|t?q[sf]"      # quarter tones
    r")?"
    r"|(do|re|mi|fa|sol|la|si)("
        r"dd?|bb?|ss?|kk?"
        r"b?sb|d?sd|[bs]t?qt"           # quarter tones
    r")?"
    r"|as|asess?|asas|es|esess?"        # special cases
    r"|eseh|as[ae]h"                    # special quarter tone cases
    r")(?![A-Za-z])"
)
named_step = "(?P<step>" + step + ")"

rest = r"(\b[Rrs]|\\skip)(?![A-Za-z])"
named_rest = "(?P<rest>" + rest + ")"

octave = r"('+|,+|(?![A-Za-z]))"
named_octave = "(?P<octave>" + octave + ")"

cautionary = r"[?!]?"
named_cautionary = "(?P<cautionary>" + cautionary + ")"

octcheck = "=[',]*"
named_octcheck = "(?P<octcheck>" + octcheck + ")"

pitch = (
    step + octave + cautionary + r"(\s*" + octcheck + r")?")
named_pitch = (
    named_step + named_octave + named_cautionary + r"(\s*" +
    named_octcheck + r")?")

duration = (
    r"(?P<duration>"
        r"(?P<dur>"
            r"\\(maxima|longa|breve)\b|"
            r"(1|2|4|8|16|32|64|128|256|512|1024|2048)(?!\d)"
        r")"
        r"(\s*(?P<dots>\.+))?"
        r"(?P<scale>(\s*\*\s*\d+(/\d+)?)*)"
    r")"
)

quotedstring = r"\"(?:\\\\|\\\"|[^\"])*\""

skip_pitches = (
    # skip \relative or \transpose pitch, etc:
    r"\\(relative|transposition)\s+" + pitch +
    r"|\\transpose\s+" + pitch + r"\s*" + pitch +
    # and skip commands
    r"|\\[A-Za-z]+"
)

# a sounding pitch/chord with duration
chord = re.compile(
    # skip this:
    r"<<|>>|" + quotedstring +
    # but catch either a pitch plus an octave
    r"|(?P<full>(?P<chord>" + named_pitch +
    # or a chord:
    r"|<(\\[A-Za-z]+|" + quotedstring + r"|[^>])*>"
    r")"
    # finally a duration?
    r"(\s*" + duration + r")?)"
    r"|" + skip_pitches
)

# a sounding pitch/chord OR rest/skip with duration
chord_rest = re.compile(
    # skip this:
    r"<<|>>|" + quotedstring +
    # but catch either a pitch plus an octave
    r"|(?P<full>(?P<chord>" + named_pitch +
    # or a chord:
    r"|<(\\[A-Za-z]+|" + quotedstring + r"|[^>])*>"
    # or a spacer or rest:
    r"|" + named_rest +
    r")"
    # finally a duration?
    r"(\s*" + duration + r")?)"
    r"|" + skip_pitches
)

finddurs = re.compile(duration)

lyric_word = re.compile(r'[^\W0-9_]+', re.UNICODE)

include_file = re.compile(r'\\include\s*"([^"]+)"')

# does not take percent signs inside quoted strings into account
comment = r'%\{.*?%\}|%.*?\n'
all_comments = re.compile(comment, re.DOTALL)

# document language
language = re.compile(
    r'.*\\((include)|language)\s*"('
        "nederlands|english|deutsch|norsk|svenska|suomi|"
        "italiano|catalan|espanol|portugues|vlaams"
    r')(?(2)\.ly)"', re.DOTALL)

# point and click, check for matchgroup 1 (on) and/or 2 (off)
point_and_click = re.compile(
    quotedstring + "|" + comment +
    r"|(\\pointAndClickOn\b|#\s*\(ly:set-option\s+'point-and-click\s+#t\s*\))"
    r"|(\\pointAndClickOff\b|#\s*\(ly:set-option\s+'point-and-click\s+#f\s*\))",
    re.DOTALL)

# dynamics
dynamic_mark = re.compile(r"[^_-]?\\(f{1,5}|p{1,5}|mf|mp|fp|spp?|sff?|sfz|rfz)\b")
dynamic_spanner = re.compile(r"[^_-]?\\[<>]")

    