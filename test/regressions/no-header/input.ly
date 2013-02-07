\version "2.16.0"

\include "articulate.ly"

music = \new Voice {
  \relative c' {
    c4 d e f
  }
}

\score {
  \music
  \layout { }
  \midi { }
}
