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
General functions that parse LilyPond document text.
"""

import os
import ly.rx


def findIncludeFiles(lyfile, path=()):
    """Finds files included by the document in lyfile.
    
    If path is given, it must be a list of directories that are also searched
    for files to be included.
    
    """
    files = set()
    basedir = os.path.dirname(lyfile)
    
    def find(lyfile):
        if os.access(lyfile, os.R_OK):
            files.add(lyfile)
            directory = os.path.dirname(lyfile)
            # read the file and delete the comments.
            with open(lyfile) as f:
                text = ly.rx.all_comments.sub('', f.read().decode('utf-8', 'ignore'))
            for f in ly.rx.include_file.findall(text):
                # old include (relative to master file)
                find(os.path.join(basedir, f))
                # new, recursive, relative include
                if directory != basedir:
                    find(os.path.join(directory, f))
                # if path is given, also search there:
                for p in path:
                    find(os.path.join(p, f))
    find(lyfile)
    return files

def documentLanguage(text):
    """Return the LilyPond pitch language name for the document, if set."""
    text = ly.rx.all_comments.sub('', text)
    m = ly.rx.language.match(text)
    if m:
        return m.group(3)

