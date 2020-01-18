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
This module defines a Tokenizer class to parse and tokenize LilyPond text.

Usage:

>>> from ly.tokenizer import Tokenizer
>>> tokenizer = Tokenizer()
>>> lilypond = r"\relative c' { c d-\markup { Hi There } }"
>>> for token in tokenizer.tokens(lilypond):
...  print token.__class__.__name__, repr(token)
...
Command u'\\relative'
Space u' '
PitchWord u'c'
Unparsed u"'"
Space u' '
OpenDelimiter u'{'
Space u' '
PitchWord u'c'
Space u' '
PitchWord u'd'
Unparsed u'-'
Markup u'\\markup'
Space u' '
OpenBracket u'{'
Space u' '
MarkupWord u'Hi'
Space u' '
MarkupWord u'There'
Space u' '
CloseBracket u'}'
Space u' '
CloseDelimiter u'}'
>>>

Some LilyPond construct enter a different parsing mode, you can get the current
Tokenizer.Parser instance with parser().

The tokens returned by the iterator returned by tokens() are all instances
of subclasses of unicode. They are either instances of a subclass of
Tokenizer.Token (if they were parsed) or Tokenizer.Unparsed (if the piece of
text was not understood).

The Unparsed class and all Token subclasses are attributes of the Tokenizer
class (so they are nested classes). You can subclass Tokenizer to add your own
token classes. Each token class defines the regular expression pattern it
matches in its rx class attribute.

There are also Parser subclasses, defined as Tokenizer class attributes.
Those are instantiated to look for specific tokens in LilyPond input text.
The items() static method of the Parser subclasses should return a tuple of
token classes (found as attributes of the Tokenizer (sub)class).

Upon class construction of the/a Tokenizer (sub)class, a regular expression is
automatically created for each Parser subclass to parse a piece of LilyPond input
text for the list of tokens returned by its items() method. You can also easily
subclass the Parser classes.
"""

import re
import rx
import pitch
import words


def _make_re(classes):
    """Builds a regular expression to parse a text for the given token classes.
    
    Expects a list of classes representing LilyPond input atoms. Returns
    compiled regular expression with named groups, to match input of the listed
    types. Reads the rx class attribute of the given classes.
    
    """
    return re.compile("|".join(
        "(?P<{0}>{1})".format(cls.__name__, cls.rx) for cls in classes))


class _tokenizer_meta(type):
    """ Metaclass for the Tokenizer class.
    
    This metaclass makes sure that the regex patterns of Parser subclasses
    inside a subclassed Tokenizer are always correct.
    
    It checks the items() method of all Parser subclasses and creates a
    pattern attribute. If that's different, a new copy (subclass) of the Parser
    subclass is created with the correct pattern.
    
    """
    def __init__(cls, className, bases, attrd):
        for name in dir(cls):
            attr = getattr(cls, name)
            if (isinstance(attr, type) and issubclass(attr, cls.Parser)
                    and attr is not cls.Parser):
                # We have a Parser subclass. If it has already a pattern
                # that's different from the one created from the items()
                # method output, copy the class. (The pattern is a compiled
                # regex pattern.)
                pattern = _make_re(attr.items(cls))
                if 'pattern' not in attr.__dict__:
                    attr.pattern = pattern
                elif attr.pattern.pattern != pattern.pattern:
                    setattr(cls, name, type(name, (attr,), {'pattern': pattern}))


class Tokenizer(object):
    """An environment to parse LilyPond text input.
    
    There are two types of nested classes (accessible as class attributes, but
    also via a Tokenizer instance):
    
    - Subclasses of Token (or Unparsed): tokens of LilyPond input.
    - Subclasses of Parser: container with regex to parse LilyPond input.
    
    """
    __metaclass__ = _tokenizer_meta
    
    def __init__(self, parserClass = None):
        self.reset(parserClass)
        
    def reset(self, parserClass = None):
        """
        Reset the tokenizer instance (forget state), so that it can be used
        again.
        """
        if parserClass is None:
            parserClass = self.ToplevelParser
        self.state = [parserClass()]
        self.language = "nederlands"

    def parser(self, depth = -1):
        """ Return the current (or given) parser instance. """
        return self.state[depth]
        
    def enter(self, parserClass, token = None, argcount = None):
        """ (Internal) Enter a new parser. """
        self.state.append(parserClass(token, argcount))

    def leave(self):
        """ (Internal) Leave the current parser and pop back to the previous. """
        if len(self.state) > 1:
            self.state.pop()
        
    def endArgument(self):
        """
        (Internal) End an argument. Decrease argcount and leave the parser
        if it would reach 0.
        """
        while len(self.state) > 1 and self.state[-1].level == 0:
            if self.state[-1].argcount > 1:
                self.state[-1].argcount -= 1
                return
            elif self.state[-1].argcount == 0:
                return
            self.state.pop()
            
    def inc(self):
        """
        (Internal) Up the level of the current parser. Indicates nesting
        while staying in the same parser.
        """
        self.state[-1].level += 1
        
    def dec(self):
        """
        (Internal) Down the level of the current parser. If it has reached zero,
        leave the current parser. Otherwise decrease argcount and leave if that
        would reach zero.
        """
        while self.state[-1].level == 0 and len(self.state) > 1:
            self.state.pop()
        if self.state[-1].level > 0:
            self.state[-1].level -= 1
            self.endArgument()
            
    def depth(self):
        """
        Return a two-tuple representing the depth of the current state.
        This is useful to quickly check when a part of LilyPond input ends.
        """
        return len(self.state), self.state[-1].level

    def tokens(self, text, pos = 0):
        """Iterate over the LilyPond tokens in the string.
        
        All returned tokens are a subclass of unicode.
        When they are reassembled, the original string is restored (i.e. no
        data is lost).
        
        The tokenizer does its best to parse LilyPond input and return
        meaningful strings. It recognizes being in a Scheme context, and also
        "LilyPond in Scheme" (the #{ and #} constructs).
        
        """
        m = self.parser().parse(text, pos)
        while m:
            if pos < m.start():
                yield self.Unparsed(text[pos:m.start()], pos)
            tokenClass = getattr(self, m.lastgroup)
            yield tokenClass(m, self)
            pos = m.end()
            m = self.parser().parse(text, pos)
        if pos < len(text):
            yield self.Unparsed(text[pos:], pos)
    
    def freeze(self):
        """
        Returns the frozen state of this tokenizer as an immutable tuple
        """
        state = tuple((
                    parser.__class__,
                    parser.token,
                    parser.level,
                    parser.argcount,
                ) for parser in self.state)
        return state, self.language
            
    def thaw(self, frozenState):
        """
        Accepts a tuple such as returned by freeze(), and restores
        the state of this tokenizer from it.
        """
        state, self.language = frozenState
        self.state = []
        for cls, token, level, argcount in state:
            parser = cls(token, argcount)
            parser.level = level
            self.state.append(parser)
    
    
    # Classes that represent pieces of lilypond text:
    # base classes:
    class Token(unicode):
        """Represents a parsed piece of LilyPond text.
        
        The subclass determines the type.
        
        The matchObj delivers the string and the position.
        The tokenizer's state can be manipulated on instantiation.
        
        """
        def __new__(cls, matchObj, tokenizer):
            obj = unicode.__new__(cls, matchObj.group(), "utf-8")
            obj.pos, obj.end = matchObj.span()
            return obj

    class Item(Token):
        """A token that decreases the argument count of the current parser."""
        def __init__(self, matchObj, tokenizer):
            tokenizer.endArgument()

    class Increaser(Token):
        """A token that increases the level of the current parser."""
        def __init__(self, matchObj, tokenizer):
            tokenizer.inc()
            
    class Decreaser(Token):
        """A token that decreases the level of the current parser."""
        def __init__(self, matchObj, tokenizer):
            tokenizer.dec()

    class Leaver(Token):
        """A token that leaves the current parser."""
        def __init__(self, matchObj, tokenizer):
            tokenizer.leave()


    # Types of lilypond input
    class Unparsed(Token):
        """Represents an unparsed piece of LilyPond text.
        
        Needs to be given a value and a position (where the string was found).
        
        """
        def __new__(cls, value, pos):
            obj = unicode.__new__(cls, value, "utf-8")
            obj.pos = pos
            obj.end = pos + len(obj)
            return obj

    ##
    ## Whitespace
    ##
    class NewLine(Token):
        rx = r"\n"
        
    class Space(Token):
        rx = r"\s+"

    ##
    ## Quoted Strings
    ##
    class String(Token):
        """ Base class for quoted string fragments. """
    
    class StringQuoted(String, Item):
        """ A complete quoted string without a newline. """
        rx = r'"(\\[\\"]|[^"\n])*"'
        
    class StringQuoteStart(String):
        rx = '"'
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.StringParser, self)
        
    class StringQuoteEnd(String):
        rx = '"'
        def __init__(self, matchObj, tokenizer):
            tokenizer.leave()
            tokenizer.endArgument()
        
    class StringFragment(String):
        rx = r'(\\[\\"]|[^"\n])+'

    ##
    ## Comments
    ##
    class Comment(Token):
        """ Base class for LineComment and BlockComment (also Scheme) """
    
    class LineComment(Comment):
        rx = r"%[^\n]*"
    
    class BlockCommentStart(Comment):
        rx = r"%\{"
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.BlockCommentParser, self)
    
    class BlockCommentEnd(Comment, Leaver):
        rx = r"%\}"
            
    class BlockCommentFragment(Comment):
        rx = r"(%(?!\})|[^%\n])+"
        
    ##
    ## Scheme
    ##
    class SchemeToken(Token):
        """ Base class for Scheme tokens. """
        pass
    
    class Scheme(SchemeToken):
        rx = '#'
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.SchemeParser, self)

    class SchemeOpenParenthesis(Increaser, SchemeToken):
        rx = r"\("

    class SchemeCloseParenthesis(Decreaser, SchemeToken):
        rx = r"\)"

    class SchemeQuote(SchemeToken):
        rx = r"[',`]"
    
    class SchemeChar(Item, SchemeToken):
        rx = r"#\\([a-z]+|.)"

    class SchemeWord(Item, SchemeToken):
        rx = r'[^()"{}\s]+'

    class SchemeLily(Token):
        rx = r"#\{"
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.ToplevelParser, self)
    
    class EndSchemeLily(Leaver):
        rx = r"#\}"
    
    ##
    ## Scheme comments
    ##
    class SchemeLineComment(Comment, SchemeToken):
        rx = r";[^\n]*"
    
    class SchemeBlockCommentStart(Comment, SchemeToken):
        rx = '#!'
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.SchemeBlockCommentParser, self)

    class SchemeBlockCommentEnd(Comment, Leaver):
        rx = '!#'
            
    class SchemeBlockCommentFragment(Comment):
        rx = r"(!(?!#)|[^!\n])+"
        
    ##
    ## LilyPond commands
    ##
    class Command(Item):
        rx = r"\\[A-Za-z]+(-[A-Za-z]+)*"
        
    class Section(Command):
        """Introduce a section with no music, like \\layout, etc."""
        rx = r"\\(with|layout|midi|paper|header)\b"
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.SectionParser, self)

    class Context(Command):
        """ Introduce a \context section within layout, midi. """
        rx = r"\\context\b"
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.ContextParser, self)
            
    class Markup(Command):
        rx = r"\\markup\b"
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.MarkupParser, self)

    class MarkupLines(Command):
        rx = r"\\markuplines\b"
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.MarkupParser, self)
    
    class Language(Command):
        rx = r"\\language\b"
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.LanguageParser, self)
    
    class LanguageName(StringQuoted):
        rx = r'"({0})"'.format('|'.join(pitch.pitchInfo.keys()))
        def __init__(self, matchObj, tokenizer):
            tokenizer.language = self[1:-1]
            tokenizer.endArgument()
    
    class Include(Command):
        rx = r"\\include\b"
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.IncludeParser, self)
    
    class IncludeFile(StringQuoted):
        rx = r'"(\\[\\"]|[^"])*"'
    
    class IncludeLanguageFile(IncludeFile):
        rx = r'"({0})\.ly"'.format('|'.join(pitch.pitchInfo.keys()))
        def __init__(self, matchObj, tokenizer):
            tokenizer.language = self[1:-4]
            tokenizer.endArgument()
    
    class OpenDelimiter(Increaser):
        rx = r"<<|\{"
        
    class CloseDelimiter(Decreaser):
        rx = r">>|\}"

    class Dynamic(Token):
        rx = r"\\[<>!]"

    class VoiceSeparator(Token):
        rx = r"\\\\"

    class Articulation(Token):
        rx = r"[-_^][_.>|+^-]"
        
    class OpenBracket(Increaser):
        rx = r"\{"

    class CloseBracket(Decreaser):
        rx = r"\}"

    class PitchWord(Item):
        """ A word with just alphanumeric letters """
        rx = r"[A-Za-z]+"
        
    class MarkupScore(Command):
        rx = r"\\score\b"
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.ToplevelParser, self, 1)
            
    class MarkupCommand(Command):
        def __init__(self, matchObj, tokenizer):
            command = self[1:]
            if command in words.markupcommands_nargs[0]:
                tokenizer.endArgument()
            else:
                for argcount in 2, 3, 4:
                    if command in words.markupcommands_nargs[argcount]:
                        break
                else:
                    argcount = 1
                tokenizer.enter(tokenizer.MarkupParser, self, argcount)

    class MarkupWord(Item):
        rx = r'[^{}"\\\s#]+'

    class LyricMode(Command):
        rx = r"\\(lyricmode|((old)?add)?lyrics|lyricsto)\b"
        def __init__(self, matchObj, tokenizer):
            if self == "\\lyricsto":
                argcount = 2
            else:
                argcount = 1
            tokenizer.enter(tokenizer.LyricModeParser, self, argcount)
            
    class ChordMode(Command):
        rx = r"\\(chords|chordmode)\b"
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.ChordModeParser, self)

    class FigureMode(Command):
        rx = r"\\(figures|figuremode)\b"
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.FigureModeParser, self)

    class NoteMode(Command):
        rx = r"\\(notes|notemode)\b"
        def __init__(self, matchObj, tokenizer):
            tokenizer.enter(tokenizer.NoteModeParser, self)

    class LyricWord(Item):
        rx = r"[^\W\d]+"
        

    ### Parsers
    class Parser(object):
        """
        This is the base class for parsers.  The Tokenizer's meta class 
        looks for descendants of this class and creates parsing patterns.
        """
        pattern = None  # This is filled in by the Tokenizer's meta class.
        items = staticmethod(lambda cls: ())
        argcount = 0
        
        def __init__(self, token = None, argcount = None):
            self.level = 0
            self.token = token
            if argcount is not None:
                self.argcount = argcount

        def parse(self, text, pos):
            return self.pattern.search(text, pos)

    class StringParser(Parser):
        items = staticmethod(lambda cls: (
            cls.StringQuoteEnd,
            cls.StringFragment,
            cls.NewLine,
        ))
    
    class CommentParser(Parser):
        """ Base class for comment parsers. """
        
    class BlockCommentParser(CommentParser):
        items = staticmethod(lambda cls: (
            cls.BlockCommentEnd,
            cls.BlockCommentFragment,
            cls.NewLine,
        ))
        
    class SchemeBlockCommentParser(CommentParser):
        items = staticmethod(lambda cls: (
            cls.SchemeBlockCommentEnd,
            cls.SchemeBlockCommentFragment,
            cls.NewLine,
        ))
        
    # base stuff to parse in LilyPond input
    lilybaseItems = classmethod(lambda cls: (
        cls.BlockCommentStart,
        cls.LineComment,
        cls.StringQuoted,
        cls.StringQuoteStart,
        cls.EndSchemeLily,
        cls.Scheme,
        cls.Section,
        cls.LyricMode,
        cls.ChordMode,
        cls.FigureMode,
        cls.NoteMode,
        cls.Markup,
        cls.MarkupLines,
        cls.Include,
        cls.Language,
        cls.Command,
        cls.Space,
    ))
    
    class ToplevelParser(Parser):
        items = staticmethod(lambda cls: (
            cls.OpenDelimiter,
            cls.CloseDelimiter,
            cls.PitchWord,
            cls.Dynamic,
            cls.VoiceSeparator,
            cls.Articulation,
        ) + cls.lilybaseItems())
    
    class SchemeParser(Parser):
        argcount = 1
        items = staticmethod(lambda cls: (
            cls.StringQuoteStart,
            cls.SchemeChar,
            cls.SchemeQuote,
            cls.SchemeLineComment,
            cls.SchemeBlockCommentStart,
            cls.SchemeOpenParenthesis,
            cls.SchemeCloseParenthesis,
            cls.SchemeLily,
            cls.SchemeWord,
            cls.Space,
        ))
    
    class MarkupParser(Parser):
        argcount = 1
        items = staticmethod(lambda cls: (
            cls.MarkupScore,
            cls.MarkupCommand,
            cls.OpenBracket,
            cls.CloseBracket,
            cls.MarkupWord,
        ) + cls.lilybaseItems())
        
    class InputModeParser(Parser):
        """
        Abstract base class for input modes such as \lyricmode, \figuremode,
        \chordmode etc.
        """
        argcount = 1

    class LyricModeParser(InputModeParser):
        items = staticmethod(lambda cls: (
            cls.OpenBracket,
            cls.CloseBracket,
            cls.LyricWord,
        ) + cls.lilybaseItems())

    class ChordModeParser(ToplevelParser, InputModeParser):
        argcount = 1

    class FigureModeParser(ToplevelParser, InputModeParser):
        argcount = 1

    class NoteModeParser(ToplevelParser, InputModeParser):
        argcount = 1

    class SectionParser(Parser):
        argcount = 1
        items = staticmethod(lambda cls: (
            cls.OpenBracket,
            cls.CloseBracket,
            cls.Context,
        ) + cls.lilybaseItems())
    
    class ContextParser(Parser):
        argcount = 1
        items = staticmethod(lambda cls: (
            cls.OpenBracket,
            cls.CloseBracket,
        ) + cls.lilybaseItems())

    class IncludeParser(Parser):
        argcount = 1
        items = staticmethod(lambda cls: (
            cls.IncludeLanguageFile,
            cls.IncludeFile,
        ) + cls.lilybaseItems())

    class LanguageParser(Parser):
        argcount = 1
        items = staticmethod(lambda cls: (
            cls.LanguageName,
        ) + cls.lilybaseItems())
        

class LineColumnMixin(object):
    """
    Mixin to iterate over tokens, adding line and column attributes
    to every token.
    """
    def tokens(self, text, pos = 0):
        cursor = Cursor()
        if pos:
            cursor.walk(text[:pos])
        for token in super(LineColumnMixin, self).tokens(text, pos):
            token.line = cursor.line
            token.column = cursor.column
            yield token
            cursor.walk(token)


class MusicTokenizer(LineColumnMixin, Tokenizer):
    """
    A Tokenizer more directed to parsing music.
    It detects full pitches, chords, etc.
    """
    class OpenChord(Tokenizer.Token):
        rx = "<"
        
    class CloseChord(Tokenizer.Token):
        rx = ">"
        
    class Pitch(Tokenizer.Item):
        rx = rx.named_pitch
        def __init__(self, matchObj, tokenizer):
            self.step = matchObj.group('step')
            self.octave = matchObj.group('octave') or ''
            self.cautionary = matchObj.group('cautionary') or ''
            self.octcheck = matchObj.group('octcheck') or ''
        
    class ToplevelParser(Tokenizer.ToplevelParser):
        items = staticmethod(lambda cls: (
            cls.OpenDelimiter,
            cls.CloseDelimiter,
            cls.OpenChord,
            cls.CloseChord,
            cls.Pitch,
            cls.Dynamic,
            cls.VoiceSeparator,
            cls.Articulation,
        ) + cls.lilybaseItems())
    
    class ChordModeParser(ToplevelParser, Tokenizer.ChordModeParser): pass
    class NoteModeParser(ToplevelParser, Tokenizer.NoteModeParser): pass

    def readStep(self, pitchToken):
        return pitch.pitchReader[self.language](pitchToken.step)


class LineColumnTokenizer(LineColumnMixin, Tokenizer):
    """
    Basic Tokenizer which records line and column, adding those
    as attributes to every token.
    """
    pass


class Cursor(object):
    """
    A Cursor instance can walk() over any piece of plain text,
    maintaining line and column positions by looking at newlines in the text.

    Subclass this to let a ChangeList perform changes on the instance.
    The actions are called in sorted order, but the cursor positions
    reflect the updated state of the document.
    """
    def __init__(self, other = None, column = 0):
        if isinstance(other, Cursor):
            self.line = other.line
            self.column = other.column
            self.anchorLine = other.anchorLine
            self.anchorColumn = other.anchorColumn
        else:
            self.line = other or 0
            self.column = column
            self.anchorLine = 0
            self.anchorColumn = 0
    
    def walk(self, text):
        lines = text.count('\n')
        if lines:
            self.line += lines
            self.column = len(text) - text.rfind('\n') - 1
        else:
            self.column += len(text)
    
    def anchor(self, text):
        """
        Sets the anchor to the end of text.
        """
        lines = text.count('\n')
        if lines:
            self.anchorLine = self.line + lines
            self.anchorColumn = len(text) - text.rfind('\n') - 1
        else:
            self.anchorLine = self.line
            self.anchorColumn = self.column + len(text)

    def __enter__(self):
        """ Called before edits are made. """
        pass
    
    def __exit__(self, *args):
        """ Called after edits have been done. """
        pass
    
    def insertText(self, text):
        """ Insert text at current cursor position. """
        pass
    
    def removeText(self):
        """ Delete text from current position to anchor. """
        pass
    
    def replaceText(self, text):
        """ Replace text from current position to anchor with text. """
        pass
        

class ChangeList(object):
    """
    Manages a list of changes to a string.
    """
    
    # whether our items must be sorted.
    # If False, the user must add the changes in the correct order!
    sortItems = True
    
    def __init__(self, text):
        self._changes = []
        # maps (line, column) tuples to new text
        self.token_changes_by_coords = {}
        self._text = text
        
    def replace(self, pos, end, text):
        if text != self._text[pos:end]:
            self._changes.append((pos, end, text))
        
    def replaceToken(self, token, text):
        if token != text:
            self._changes.append((token.pos, token.end, text))
            self.token_changes_by_coords[(token.line, token.column)] = text
            
    def remove(self, pos, end):
        self._changes.append((pos, end, None))
    
    def removeToken(self, token):
        self._changes.append((token.pos, token.end, None))
        
    def insert(self, pos, text):
        self._changes.append((pos, pos, text))
        
    def changes(self):
        """
        Return an iterator over the changes.

        Each entry from the iterator is a tuple(pos, end, text).  pos
        and end define the slice of the original string to remove,
        text is the text to insert at that position.
        """
        if self.sortItems:
            return sorted(self._changes)
        else:
            return self._changes
        
    def newTextForLineColumn(self, line, column):
        """
        Return the replacement text for a token at the given line and
        column, or None if the token has no change.
        """
        return self.token_changes_by_coords.get((line, column))

    def apply(self):
        """
        Return a new string constructed from the original string
        with all the changes applied.
        """
        def parts():
            index = 0
            for pos, end, text in self.changes():
                if pos > index:
                    yield self._text[index:pos]
                if text:
                    yield text
                index = end
            if index < len(self._text):
                yield self._text[index:]
        
        return ''.join(parts())

    def applyToCursor(self, cursor):
        index = 0
        with cursor:
            for pos, end, text in self.changes():
                if pos > index:
                    cursor.walk(self._text[index:pos])
                if end > pos:
                    cursor.anchor(self._text[pos:end])
                    if text:
                        cursor.replaceText(text)
                        cursor.walk(text)
                    else:
                        cursor.removeText()
                else:
                    cursor.insertText(text)
                    cursor.walk(text)
                index = end


