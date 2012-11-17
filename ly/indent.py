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
Indent LilyPond input.

Recognizes common LilyPond mode and Scheme mode.

This module is not dependent on any other module,
besides the Python standard re module.
"""

import re

# tokens to look for in LilyPond mode
lily_re = (
    r"(?P<indent>\{|<<)"
    r"|(?P<dedent>>>|\})"
    r'|(?P<string>"(\\[\\"]|[^"])*")'
    r"|(?P<newline>\n[^\S\n]*)"
    r"|(?P<space>[^\S\n]+)"
    r"|(?P<scheme>#)"
    r"|(?P<blockcomment>%\{.*?%\})"
    r"|(?P<longcomment>%%%[^\n]*)"
    r"|(?P<comment>%[^\n]*)"
    )

# tokens to look for in Scheme mode
scheme_re = (
    r"(?P<indent>\()"
    r"|(?P<dedent>\))"
    r'|(?P<string>"(\\[\\"]|[^"])*")'
    r"|(?P<newline>\n[^\S\n]*)"
    r"|(?P<space>[^\S\n]+)"
    r"|(?P<lilypond>#\{)"
    r"|(?P<longcomment>;;;[^\n]*)"
    r"|(?P<blockcomment>#!.*?!#)"
    r"|(?P<comment>;[^\n]*)"
    )

# tokens to look for in LilyPond-inside-Scheme mode
schemelily_re = r"(?P<backtoscheme>#\})|" + lily_re


# Parse LilyPond text
lily = re.compile(lily_re, re.DOTALL)

# Parse LilyPond-in-Scheme text
schemelily = re.compile(schemelily_re, re.DOTALL)

# Parse Scheme text, instantiate to keep state (depth)
class scheme:
    search = re.compile(scheme_re, re.DOTALL).search
    depth = 0


# searches for indent inside a string
indent_rx = re.compile(r'\n([^\S\n]*)')

    
def indent(text,
        start = None,
        indentwidth = 2,
        tabwidth = 8,
        usetabs = None,
        startscheme = False
        ):
    """
    Properly indents the LilyPond input in text.
    
    If start is an integer value, use that value as the indentwidth to start
    with, disregarding the current indent of the first line.
    If it is None, use the indent of the first line.
    
    indentwidth: how many positions to indent (default 2)
    tabwidth: width of a tab character
    usetabs: whether to use tab characters in the indent:
        - None = determine from document
        - True = use tabs for the parts of the indent that exceed the tab width
        - False = don't use tabs.
    startscheme: start in scheme mode (not very robust)
    """
    
    # record length of indent of first line
    space = re.match(r'[^\S\n]*', text).group()
    if start is None:
        start = len(space.expandtabs(tabwidth))
    if usetabs is None:
        usetabs = '\t' in space or '\n\t' in text
    
    mode = [lily]       # the mode to parse in
    indent = [start]    # stack with indent history
    pos = len(space)    # start position in text
    output = []         # list of output lines
    
    if startscheme:
        mode.append(scheme())
    if usetabs:
        makeindent = lambda i: '\t' * int(i / tabwidth) + ' ' * (i % tabwidth)
    else:
        makeindent = lambda i: ' ' * i
    
    line = []           # list to build the output, per line
    curindent = -1      # current indent in count of spaces, -1 : not yet set
    
    # Search the text from the previous position
    # (very fast: does not alter the string in text)
    m = mode[-1].search(text, pos)
    while m:
        # also append text before the found token
        more = pos < m.start()
        if more:
            line.append(text[pos:m.start()])
        
        # type, text, and new position for next search
        item, token, pos = m.lastgroup, m.group(), m.end()

        # If indent not yet determined, set it to 0 if we found a long comment
        # (with three or more %%% or ;;; characters). Was any other text found,
        # keep the current indent level for the current line.
        # (Our current indent can change if our line starts with dedent tokens.)
        if curindent == -1:
            if item == 'longcomment':
                curindent = 0
            elif (more or item not in ('dedent', 'space', 'backtoscheme')):
                curindent = indent[-1]
        
        # Check if we found a multiline block comment.
        # Thoses are handled specially. Indents inside the block comment are
        # preserved but positioned as close as possible to the current indent.
        # So the algorithm cuts the shortest indent off from all lines and then
        # adds the current indent.
        if item == 'blockcomment' and '\n' in token:
            # Find the shortest indent inside the block comment
            shortest = min(len(n.group(1).expandtabs(tabwidth))
                for n in indent_rx.finditer(token))
            # Remove that indent from all lines
            fixindent = lambda n: '\n' + makeindent(
                curindent - shortest + len(n.group(1).expandtabs(tabwidth)))
            token = indent_rx.sub(fixindent, token)
        
        elif mode[-1] in (lily, schemelily):
            # we are parsing in LilyPond mode.
            if item == 'indent':
                indent.append(indent[-1] + indentwidth)
            elif item == 'dedent' and len(indent) > 1:
                indent.pop()
            elif item == 'scheme':
                mode.append(scheme())       # enter scheme mode
            elif item == 'backtoscheme':
                indent.pop()
                mode.pop()                  # leave lilypond mode, back to scheme
        else:
            # we are parsing in Scheme mode.
            if item == 'indent':
                mode[-1].depth += 1         # count parentheses
                # look max 10 characters ahead to vertically align opening
                # parentheses, but stop at closing parenthesis, quote or newline.
                n = re.search(r'[()"\n]', text[pos:pos+10])
                if n and n.group() == '(':
                    indent.append(indent[-1] + n.start() + 1)
                else:
                    indent.append(indent[-1] + indentwidth)
                
            elif item == 'dedent':
                if mode[-1].depth:
                    indent.pop()
                if mode[-1].depth <= 1:
                    mode.pop()              # leave scheme mode
                else:
                    mode[-1].depth -= 1     # count parentheses backwards
            elif item == 'lilypond':
                mode.append(schemelily)     # enter lilypond-in-scheme mode
                indent.append(indent[-1] + indentwidth)
            elif mode[-1].depth == 0:
                # jump out if we got one atom or are at a space or end of line
                # and still no opening parenthesis. But stay if we only just
                # had a hash(#).
                if (item in ('string', 'comment', 'longcomment')
                    or (more and item in ('newline', 'space'))):
                    mode.pop()
        
        if item == 'newline':
            # Write out the line
            output.append(makeindent(curindent) + ''.join(line))
            line = []
            curindent = -1
        else:
            line.append(token)
        
        # On to the next token
        m = mode[-1].search(text, pos)
    
    # Still some text left?
    if pos < len(text):
        line.append(text[pos:])
    if line:
        if curindent == -1:
            curindent = indent[-1]
        output.append(makeindent(curindent) + ''.join(line))
    else:
        output.append(makeindent(start))
    # Return formatted output
    return '\n'.join(output)

    
if __name__ == '__main__':
    
    import sys, optparse
    
    op = optparse.OptionParser(usage='usage: %prog [options] [filename]')
    op.add_option('-o', '--output',
        help='write to this file instead of standard output')
    op.add_option('-i', '--indent-width', type='int', default=2,
        help='indent width in characters to use [default: %default]')
    op.add_option('-t', '--tab-width', type='int', default=8,
        help='tab width to assume [default: %default]')
    op.add_option('-s', '--start-indent', type='int', default=0,
        help='start indent [default: %default]')
    op.add_option('--scheme', action='store_true',
        help='start indenting in Scheme mode')
    op.add_option('-u', '--use-tabs', action='store_true',
        help='use tabs instead of spaces for indent')
    options, args = op.parse_args()
    # TODO: encoding
    # TODO: error handling
    infile = args and open(args[0]) or sys.stdin
    text = infile.read()
    text = indent(text,
        start=options.start_indent,
        indentwidth=options.indent_width,
        tabwidth=options.tab_width,
        usetabs=options.use_tabs,
        startscheme=options.scheme
        )
    outfile = options.output and (options.output) or sys.stdout
    outfile.write(text)
    
    if infile is not sys.stdin:
        infile.close()
    if outfile is not sys.stdout:    
        outfile.close()
    sys.exit(0)
