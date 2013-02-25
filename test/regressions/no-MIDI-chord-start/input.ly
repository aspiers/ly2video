\version "2.16.0"

\header {
}

music = {
    \new Voice {
        \relative c' {
            r4 d e f
        }
    }
}

\score {
    <<
        \music
        \new ChordNames {
            \chordmode { c1:5 }
        }
    >>
    \layout { }
}

\score {
    \music
    \midi { }
}
