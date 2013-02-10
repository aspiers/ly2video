\version "2.16.0"

\header {
}

music = \new Voice {
  \relative c' {
    <a c e>1 q <f a c>2 q
  }
}

\score {
  \music
  \layout { }
  \midi { }
}
