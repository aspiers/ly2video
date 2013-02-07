\version "2.16.0"

\include "articulate.ly"

\header {
}

music = \new Voice {
  \relative c' {
    c4 d \turn e f
  }
}

\score {
  \music
  \layout { }
}

\score {
  \articulate \music
  \midi { }
}
