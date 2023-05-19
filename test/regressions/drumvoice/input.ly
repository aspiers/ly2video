\version "2.20.0"

music = {
  \new DrumStaff {
    \set Staff.instrumentName = #"drums"
      \new DrumVoice {
        \drummode {
          \time 4/4
          \tempo 4 = 84
          <<
          { cymr8 cymr8 \tuplet3/2{hh16 hh hh} hh8 \tuplet3/2{tomh16 tomh tomh} \tuplet3/2{tomh16 tomh toml} \tuplet3/2{tomh16 tomfh tomh} tomfh8 }
	  \\
          { bd8 bd8 s4 s2 }
          >>
	}
      }
    }
}

\score {
  \music
  \layout { }
}

\score {
  \music
  \midi { }
}
