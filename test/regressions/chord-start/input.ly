\version "2.16.0"

\header {
}

\score {
    <<
        \new Voice {
            \relative c' {
                r4 d e f
            }
        }
        \new ChordNames {
            \chordmode { c1:5 }
        }
    >>
    \layout { }
    \midi { }
}
