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
LilyPond version information
"""

import os, re, weakref
from functools import wraps
from subprocess import Popen, PIPE, STDOUT

import ly.rx

def getVersion(text):
    """
    Determine the version of a LilyPond document.
    Returns a Version instance or None.
    """
    text = ly.rx.all_comments.sub('', text)
    match = re.search(r'\\version\s*"(.*?)"', text)
    if match:
        return Version.fromString(match.group(1))


# Utility functions.....
def cacheresult(func):
    """
    A decorator that performs the decorated method call only the first time,
    caches the return value, and returns that next time.
    The argments tuple should be hashable.
    """
    cache = weakref.WeakKeyDictionary()
    @wraps(func)
    def wrapper(obj, *args):
        h = hash(args)
        try:
            return cache[obj][h]
        except KeyError:
            result = cache.setdefault(obj, {})[h] = func(obj, *args)
            return result
    return wrapper


class Version(tuple):
    """
    Contains a version as a two- or three-tuple (major, minor [, patchlevel]).
    
    Can format itself as "major.minor" or "major.minor.patch"
    Additionally, three attributes are defined:
    - major     : contains the major version number as an int
    - minor     : contains the minor version number as an int
    - patch     : contains the patch level as an int or None
    """
    def __new__(cls, major, minor, patch=None):
        if patch is None:
            obj = tuple.__new__(cls, (major, minor))
        else:
            obj = tuple.__new__(cls, (major, minor, patch))
        obj.major = major
        obj.minor = minor
        obj.patch = patch
        return obj
        
    def __format__(self, formatString):
        return str(self)
        
    def __str__(self):
        return ".".join(map(str, self))

    @classmethod
    def fromString(cls, text):
        match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
        if match:
            return cls(*map(lambda g: int(g) if g else None, match.groups()))

            
class LilyPondInstance(object):
    """
    Contains information about a LilyPond instance, referred to by a command
    string defaulting to 'lilypond'.
    """
    
    # name of the convert-ly command
    convert_ly_name = 'convert-ly'
    
    def __new__(cls, command='lilypond', cache=True):
        """
        Return a cached instance if available and cache == True.
        """
        if '_cache' not in cls.__dict__:
            cls._cache = {}
        elif cache and command in cls._cache:
            return cls._cache[command]
        obj = cls._cache[command] = object.__new__(cls)
        obj._command = command
        return obj
    
    @cacheresult
    def command(self):
        """
        Returns the command with full path prepended.
        """
        cmd = self._command
        if os.path.isabs(cmd):
            return cmd
        elif os.path.isabs(os.path.expanduser(cmd)):
            return os.path.expanduser(cmd)
        elif os.sep in cmd and os.access(cmd, os.X_OK):
            return os.path.abspath(cmd)
        else:
            for p in os.environ.get("PATH", os.defpath).split(os.pathsep):
                if os.access(os.path.join(p, cmd), os.X_OK):
                    return os.path.join(p, cmd)
    
    def bindir(self):
        """
        Returns the directory the LilyPond command is in.
        """
        cmd = self.command()
        if cmd:
            return os.path.dirname(cmd)
    
    def path_to(self, command):
        """
        Returns the full path to the given command, by joining our bindir() with
        the command.
        """
        bindir = self.bindir()
        if bindir:
            return os.path.join(bindir, command)
            
    def convert_ly(self):
        """
        DEPRECATED: Use path_to('convert-ly') instead.
        Returns the full path of the convert-ly command that is in the
        same directory as the corresponding lilypond command.
        """
        return self.path_to(self.convert_ly_name)
            
    def prefix(self):
        """
        Returns the prefix of a command. E.g. if command is "lilypond"
        and resolves to "/usr/bin/lilypond", this method returns "/usr".
        """
        cmd = self.command()
        if cmd:
            return os.path.dirname(os.path.dirname(cmd))
        
    @cacheresult
    def version(self):
        """
        Returns the version returned by command -v as an instance of Version.
        """
        try:
            output = Popen((self._command, '-v'), stdout=PIPE, stderr=STDOUT).communicate()[0]
            return Version.fromString(output)
        except OSError:
            pass

    @cacheresult
    def datadir(self):
        """
        Returns the datadir of this LilyPond instance. Most times something
        like "/usr/share/lilypond/2.13.3/"
        """
        # First ask LilyPond itself.
        try:
            d = Popen((self._command, '-e',
                "(display (ly:get-option 'datadir)) (newline) (exit)"),
                stdout=PIPE).communicate()[0].strip()
            if os.path.isabs(d) and os.path.isdir(d):
                return d
        except OSError:
            pass
        # Then find out via the prefix.
        version, prefix = self.version(), self.prefix()
        if prefix:
            dirs = ['current']
            if version:
                dirs.append(str(version))
            for suffix in dirs:
                d = os.path.join(prefix, 'share', 'lilypond', suffix)
                if os.path.isdir(d):
                    return d

    @cacheresult
    def lastConvertLyRuleVersion(self):
        """
        Returns the version of the last convert-ly rule of this lilypond
        instance.
        """
        try:
            output = Popen((self.convert_ly(), '--show-rules'), stdout=PIPE).communicate()[0]
            for line in reversed(output.splitlines()):
                match = re.match(r"(\d+)\.(\d+)\.(\d+):", line)
                if match:
                    return Version(*map(int, match.groups()))
        except OSError:
            pass
        
    @cacheresult
    def fontInfo(self, fontname):
        """
        Returns a SvgFontInfo object containing information about
        the named font (e.g. "emmentaler-20").
        """
        datadir = self.datadir()
        if datadir:
            font = os.path.join(datadir, "fonts", "svg", fontname + ".svg")
            if os.path.exists(font):
                import ly.font
                return ly.font.SvgFontInfo(font)
            

