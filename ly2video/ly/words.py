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
LilyPond reserved words for auto completion, and some regexps
"""

import re

keywords = (
    'accepts',
    'alias',
    'consists',
    'defaultchild',
    'denies',
    #'description',
    #'grobdescriptions',
    'include',
    #'invalid',
    'language',
    'name',
    #'objectid',
    'once',
    'remove',
    #'sequential',
    #'simultaneous',
    #'type',
    'version',
    'score',
    'book',
    'bookpart',
    'header',
    'paper',
    'midi',
    'layout',
    'with',
    'context',
)

keywords_completion = (
    'score {}',
    'header {}',
    'paper {}',
    'midi {}',
    'layout {}',
    'with {}',
    'context {}',
)

musiccommands = (
    'accent',
    'accentus',
    'acciaccatura',
    'addInstrumentDefinition',
    'addlyrics',
    'addQuote',
    'afterGrace',
    'afterGraceFraction',
    'aikenHeads',
    'aikenHeadsMinor',
    'allowPageTurn',
    'alternative',
    'AncientRemoveEmptyStaffContext',
    'applyContext',
    'applyMusic',
    'applyOutput',
    'appoggiatura',
    'arpeggio',
    'arpeggioArrowDown',
    'arpeggioArrowUp',
    'arpeggioBracket',
    'arpeggioNormal',
    'arpeggioParenthesis',
    'ascendens',
    'auctum',
    'augmentum',
    'autoAccidentals',
    'autoBeamOff',
    'autoBeamOn',
    'autochange',
    'balloonGrobText',
    'balloonLengthOff',
    'balloonLengthOn',
    'balloonText',
    'bar',
    'barNumberCheck',
    'bassFigureExtendersOff',
    'bassFigureExtendersOn',
    'bassFigureStaffAlignmentDown',
    'bassFigureStaffAlignmentNeutral',
    'bassFigureStaffAlignmentUp',
    'bendAfter',
    'blackTriangleMarkup',
    'bracketCloseSymbol',
    'bracketOpenSymbol',
    'break',
    'breathe',
    'breve',
    'cadenzaOff',
    'cadenzaOn',
    'caesura',
    'cavum',
    'change',
    'chordmode',
    'chordNameSeparator',
    'chordPrefixSpacer',
    'chordRootNamer',
    'chords',
    'circulus',
    'clef',
    'cm',
    'coda',
    'compressFullBarRests',
    'context',
    'cr',
    'cresc',
    'crescHairpin',
    'crescTextCresc',
    'cueDuring',
    'dashBar',
    'dashDash',
    'dashDot',
    'dashHat',
    'dashLarger',
    'dashPlus',
    'dashUnderscore',
    'decr',
    'default',
    'defaultTimeSignature',
    'deminutum',
    'denies',
    'descendens',
    'dim',
    'dimHairpin',
    'dimTextDecr',
    'dimTextDecresc',
    'dimTextDim',
    'displayLilyMusic',
    'displayMusic',
    'divisioMaior',
    'divisioMaxima',
    'divisioMinima',
    'dotsDown',
    'dotsNeutral',
    'dotsUp',
    'downbow',
    'downmordent',
    'downprall',
    'drummode',
    'drumPitchTable',
    'drums',
    'dynamicDown',
    'dynamicNeutral',
    'dynamicUp',
    'easyHeadsOff',
    'easyHeadsOn',
    'endcr',
    'endcresc',
    'enddecr',
    'enddim',
    'endincipit',
    'endSpanners',
    'episemFinis',
    'episemInitium',
    'escapedBiggerSymbol',
    'escapedExclamationSymbol',
    'escapedParenthesisCloseSymbol',
    'escapedParenthesisOpenSymbol',
    'escapedSmallerSymbol',
    'espressivo',
    'expandFullBarRests',
    'f',
    'featherDurations',
    'fermata',
    'fermataMarkup',
    'ff',
    'fff',
    'ffff',
    'fffff',
    'figuremode',
    'figures',
    'finalis',
    'fingeringOrientations',
    'flageolet',
    'flexa',
    'fp',
    'frenchChords',
    'fullJazzExceptions',
    'funkHeads',
    'funkHeadsMinor',
    'fz',
    'germanChords',
    'glissando',
    'grace',
    'graceSettings',
    'halfopen',
    'harmonic',
    'hideNotes',
    'hideStaffSwitch',
    'huge',
    'ictus',
    'ignatzekExceptionMusic',
    'ignatzekExceptions',
    'iij',
    'IIJ',
    'ij',
    'IJ',
    'improvisationOff',
    'improvisationOn',
    'in',
    'inclinatum',
    'includePageLayoutFile',
    'indent',
    'instrumentSwitch',
    'instrumentTransposition',
    'interscoreline',
    'italianChords',
    'keepWithTag',
    'key',
    'killCues',
    'label',
    'laissezVibrer',
    'large',
    'lheel',
    'ligature',
    'linea',
    'lineprall',
    'longa',
    'longfermata',
    'ltoe',
    'lyricmode',
    'lyrics',
    'lyricsto',
    'maininput',
    'majorSevenSymbol',
    'makeClusters',
    'marcato',
    'mark',
    'markup',
    'markuplines',
    'maxima',
    'melisma',
    'melismaEnd',
    'mergeDifferentlyDottedOff',
    'mergeDifferentlyDottedOn',
    'mergeDifferentlyHeadedOff',
    'mergeDifferentlyHeadedOn',
    'mf',
    'mm',
    'mordent',
    'mp',
    'musicMap',
    'neumeDemoLayout',
    'new',
    'newSpacingSection',
    'noBeam',
    'noBreak',
    'noPageBreak',
    'noPageTurn',
    'normalsize',
    'notemode',
    'numericTimeSignature',
    'octaveCheck',
    'oldaddlyrics',
    'oneVoice',
    'open',
    'oriscus',
    'ottava',
    'override',
    'overrideProperty',
    'p',
    'pageBreak',
    'pageTurn',
    'parallelMusic',
    'parenthesisCloseSymbol',
    'parenthesisOpenSymbol',
    'parenthesize',
    'partcombine',
    'partCombineListener',
    'partial',
    'partialJazzExceptions',
    'partialJazzMusic',
    'pes',
    'phrasingSlurDashed',
    'phrasingSlurDotted',
    'phrasingSlurDown',
    'phrasingSlurNeutral',
    'phrasingSlurSolid',
    'phrasingSlurUp',
    'pipeSymbol',
    'pitchedTrill',
    'pointAndClickOff',
    'pointAndClickOn',
    'portato',
    'pp',
    'ppp',
    'pppp',
    'ppppp',
    'prall',
    'pralldown',
    'prallmordent',
    'prallprall',
    'prallup',
    'predefinedFretboardsOff',
    'predefinedFretboardsOn',
    'pt',
    'quilisma',
    'quoteDuring',
    'relative',
    'RemoveEmptyRhythmicStaffContext',
    'RemoveEmptyStaffContext',
    'removeWithTag',
    'repeat',
    'repeatTie',
    'resetRelativeOctave',
    'responsum',
    'rest',
    'reverseturn',
    'revert',
    'rfz',
    'rheel',
    'rightHandFinger',
    'rtoe',
    'sacredHarpHeads',
    'sacredHarpHeadsMinor',
    'scaleDurations',
    'scoreTweak',
    'segno',
    'semicirculus',
    'semiGermanChords',
    'set',
    'sf',
    'sff',
    'sfp',
    'sfz',
    'shiftDurations',
    'shiftOff',
    'shiftOn',
    'shiftOnn',
    'shiftOnnn',
    'shortfermata',
    'showStaffSwitch',
    'signumcongruentiae',
    'skip',
    'skipTypesetting',
    'slurDashed',
    'slurDotted',
    'slurDown',
    'slurNeutral',
    'slurSolid',
    'slurUp',
    'small',
    'snappizzicato',
    'sostenutoOff',
    'sostenutoOn',
    'southernHarmonyHeads',
    'southernHarmonyHeadsMinor',
    'sp',
    'spacingTweaks',
    'spp',
    'staccatissimo',
    'staccato',
    'startAcciaccaturaMusic',
    'startAppoggiaturaMusic',
    'startGraceMusic',
    'startGroup',
    'startStaff',
    'startTextSpan',
    'startTrillSpan',
    'stemDown',
    'stemNeutral',
    'stemUp',
    'stopAcciaccaturaMusic',
    'stopAppoggiaturaMusic',
    'stopGraceMusic',
    'stopGroup',
    'stopped',
    'stopStaff',
    'stopTextSpan',
    'stopTrillSpan',
    'strokeFingerOrientations',
    'stropha',
    'sustainOff',
    'sustainOn',
    'tabFullNotation',
    'tag',
    'teeny',
    'tempo',
    'tempoWholesPerMinute',
    'tenuto',
    'textLengthOff',
    'textLengthOn',
    'textSpannerDown',
    'textSpannerNeutral',
    'textSpannerUp',
    'thumb',
    'tieDashed',
    'tieDotted',
    'tieDown',
    'tieNeutral',
    'tieSolid',
    'tieUp',
    'tildeSymbol',
    'time',
    'times',
    'timing',
    'tiny',
    'transpose',
    'transposedCueDuring',
    'transposition',
    'treCorde',
    'trill',
    'tupletDown',
    'tupletNeutral',
    'tupletUp',
    'turn',
    'tweak',
    'unaCorda',
    'unfoldRepeats',
    'unHideNotes',
    'unit',
    'unset',
    'upbow',
    'upmordent',
    'upprall',
    'varcoda',
    'versus',
    'verylongfermata',
    'virga',
    'virgula',
    'voiceFour',
    'voiceFourStyle',
    'voiceNeutralStyle',
    'voiceOne',
    'voiceOneStyle',
    'voiceThree',
    'voiceThreeStyle',
    'voiceTwo',
    'voiceTwoStyle',
    'walkerHeads',
    'walkerHeadsMinor',
    'whiteTriangleMarkup',
    'withMusicProperty',
)


musiccommands_completion = (
    'addlyrics {}',
    'alternative {}',
    'chordmode {}',
    'drummode {}',
    'figuremode {}',
    'keepWithTag #\'',
    'lyricmode {}',
    'notemode {}',
    'relative c\' {}',
    'removeWithTag #\'',
    'tag #\'',
    'tweak #\'',
)


modes = (
    'major',     
    'minor',     
    'ionian',    
    'dorian',    
    'phrygian',  
    'lydian',    
    'mixolydian',
    'aeolian',   
    'locrian',   
)


markupcommands_nargs = (
# no arguments
(
    'doubleflat',
    'doublesharp',
    'eyeglasses',
    'flat',
    'natural',
    'null',
    'semiflat',
    'semisharp',
    'sesquiflat',
    'sesquisharp',
    'sharp',
    'strut',
),
# one argument
(
    'backslashed-digit',
    'bold',
    'box',
    'bracket',
    'caps',
    'center-align',
    'center-column',
    'char',
    'circle',
    'column',
    'concat',
    'dir-column',
    'draw-line',
    'dynamic',
    'fill-line',
    'finger',
    'fontCaps',
    'fret-diagram',
    'fret-diagram-terse',
    'fret-diagram-verbose',
    'fromproperty',
    'harp-pedal',
    'hbracket',
    'hspace',
    'huge',
    'italic',
    'justify',
    'justify-field',
    'justify-string',
    'large',
    'larger',
    'left-align',
    'left-brace',
    'left-column',
    'line',
    'lookup',
    'markalphabet',
    'markletter',
    'medium',
    'musicglyph',
    'normalsize',
    'normal-size-sub',
    'normal-size-super',
    'normal-text',
    'number',
    'postscript',
    'right-align',
    'right-brace',
    'right-column',
    'roman',
    'rounded-box',
    'sans',
    'score',
    'simple',
    'slashed-digit',
    'small',
    'smallCaps',
    'smaller',
    'stencil',
    'sub',
    'super',
    'teeny',
    'text',
    'tied-lyric',
    'tiny',
    'transparent',
    'triangle',
    'typewriter',
    'underline',
    'upright',
    'vcenter',
    'vspace',
    'verbatim-file',
    'whiteout',
    'wordwrap',
    'wordwrap-field',
    'wordwrap-string',
),
# two arguments
(
    'abs-fontsize',
    'combine',
    'fontsize',
    'fraction',
    'halign',
    'hcenter-in',
    'lower',
    'magnify',
    'note',
    'on-the-fly',
    'override',
    'pad-around',
    'pad-markup',
    'pad-x',
    'path',     # added in LP 2.13.31
    'raise',
    'rotate',
    'translate',
    'translate-scaled',
    'with-color',
    'with-url',
),
# three arguments
(
    'arrow-head',
    'beam',
    'draw-circle',
    'eps-file',
    'filled-box',
    'general-align',
    'note-by-number',
    'pad-to-box',
    'page-ref',
    'with-dimensions',
),
# four arguments
(
    'put-adjacent',
))


markupcommands = sum(markupcommands_nargs, ())


markuplistcommands = (
    'column-lines',
    'justified-lines',
    'override-lines',
    'wordwrap-internal',
    'wordwrap-lines',
    'wordwrap-string-internal',
)


contexts = (
    'ChoirStaff',
    'ChordNames',
    'CueVoice',
    'Devnull',
    'DrumStaff',
    'DrumVoice',
    'Dynamics',
    'FiguredBass',
    'FretBoards',
    'Global',
    'GrandStaff',
    'GregorianTranscriptionStaff',
    'GregorianTranscriptionVoice',
    'Lyrics',
    'MensuralStaff',
    'MensuralVoice',
    'NoteNames',
    'PianoStaff',
    'RhythmicStaff',
    'Score',
    'Staff',
    'StaffGroup',
    'TabStaff',
    'TabVoice',
    'Timing',
    'VaticanaStaff',
    'VaticanaVoice',
    'Voice',
)


engravers = (
    'Accidental_engraver',
    'Ambitus_engraver',
    'Arpeggio_engraver',
    'Auto_beam_engraver',
    'Axis_group_engraver',
    'Balloon_engraver',
    'Bar_engraver',
    'Bar_number_engraver',
    'Beam_engraver',
    'Beam_performer',
    'Bend_engraver',
    'Break_align_engraver',
    'Breathing_sign_engraver',
    'Chord_name_engraver',
    'Chord_tremolo_engraver',
    'Clef_engraver',
    'Cluster_spanner_engraver',
    'Collision_engraver',
    'Completion_heads_engraver',
    'Control_track_performer',
    'Custos_engraver',
    'Default_bar_line_engraver',
    'Dot_column_engraver',
    'Dots_engraver',
    'Drum_note_performer',
    'Drum_notes_engraver',
    'Dynamic_align_engraver',
    'Dynamic_engraver',
    'Dynamic_performer',
    'Episema_engraver',
    'Extender_engraver',
    'Figured_bass_engraver',
    'Figured_bass_position_engraver',
    'Fingering_engraver',
    'Font_size_engraver',
    'Forbid_line_break_engraver',
    'Fretboard_engraver',
    'Glissando_engraver',
    'Grace_beam_engraver',
    'Grace_engraver',
    'Grace_spacing_engraver',
    'Grid_line_span_engraver',
    'Grid_point_engraver',
    'Grob_pq_engraver',
    'Hara_kiri_engraver',
    'Horizontal_bracket_engraver',
    'Hyphen_engraver',
    'Instrument_name_engraver',
    'Instrument_switch_engraver',
    'Key_engraver',
    'Key_performer',
    'Laissez_vibrer_engraver',
    'Ledger_line_engraver',
    'Ligature_bracket_engraver',
    'Lyric_engraver',
    'Lyric_performer',
    'Mark_engraver',
    'Measure_grouping_engraver',
    'Melody_engraver',
    'Mensural_ligature_engraver',
    'Metronome_mark_engraver',
    'Multi_measure_rest_engraver',
    'New_dynamic_engraver',
    'New_fingering_engraver',
    'Note_head_line_engraver',
    'Note_heads_engraver',
    'Note_name_engraver',
    'Note_performer',
    'Note_spacing_engraver',
    'Ottava_spanner_engraver',
    'Output_property_engraver',
    'Page_turn_engraver',
    'Paper_column_engraver',
    'Parenthesis_engraver',
    'Part_combine_engraver',
    'Percent_repeat_engraver',
    'Phrasing_slur_engraver',
    'Piano_pedal_align_engraver',
    'Piano_pedal_engraver',
    'Piano_pedal_performer',
    'Pitched_trill_engraver',
    'Pitch_squash_engraver',
    'Repeat_acknowledge_engraver',
    'Repeat_tie_engraver',
    'Rest_collision_engraver',
    'Rest_engraver',
    'Rhythmic_column_engraver',
    'Scheme_engraver',
    'Script_column_engraver',
    'Script_engraver',
    'Script_row_engraver',
    'Separating_line_group_engraver',
    'Slash_repeat_engraver',
    'Slur_engraver',
    'Slur_performer',
    'Spacing_engraver',
    'Span_arpeggio_engraver',
    'Span_bar_engraver',
    'Spanner_break_forbid_engraver',
    'Staff_collecting_engraver',
    'Staff_performer',
    'Staff_symbol_engraver',
    'Stanza_number_align_engraver',
    'Stanza_number_engraver',
    'Stem_engraver',
    'String_number_engraver',
    'Swallow_engraver',
    'Swallow_performer',
    'System_start_delimiter_engraver',
    'Tab_harmonic_engraver',
    'Tab_note_heads_engraver',
    'Tab_staff_symbol_engraver',
    'Tempo_performer',
    'Text_engraver',
    'Text_spanner_engraver',
    'Tie_engraver',
    'Tie_performer',
    'Time_signature_engraver',
    'Time_signature_performer',
    'Timing_translator',
    'Trill_spanner_engraver',
    'Tuplet_engraver',
    'Tweak_engraver',
    'Vaticana_ligature_engraver',
    'Vertical_align_engraver',
    'Vertically_spaced_contexts_engraver',
    'Volta_engraver',
)


midi_instruments = (
    # (1-8 piano)
    'acoustic grand',
    'bright acoustic',
    'electric grand',
    'honky-tonk',
    'electric piano 1',
    'electric piano 2',
    'harpsichord',
    'clav',
    # (9-16 chrom percussion)
    'celesta',
    'glockenspiel',
    'music box',
    'vibraphone',
    'marimba',
    'xylophone',
    'tubular bells',
    'dulcimer',
    # (17-24 organ)
    'drawbar organ',
    'percussive organ',
    'rock organ',
    'church organ',
    'reed organ',
    'accordion',
    'harmonica',
    'concertina',
    # (25-32 guitar)
    'acoustic guitar (nylon)',
    'acoustic guitar (steel)',
    'electric guitar (jazz)',
    'electric guitar (clean)',
    'electric guitar (muted)',
    'overdriven guitar',
    'distorted guitar',
    'guitar harmonics',
    # (33-40 bass)
    'acoustic bass',
    'electric bass (finger)',
    'electric bass (pick)',
    'fretless bass',
    'slap bass 1',
    'slap bass 2',
    'synth bass 1',
    'synth bass 2',
    # (41-48 strings)
    'violin',
    'viola',
    'cello',
    'contrabass',
    'tremolo strings',
    'pizzicato strings',
    'orchestral harp', # till LilyPond 2.12 was this erroneously called: 'orchestral strings'
    'timpani',
    # (49-56 ensemble)
    'string ensemble 1',
    'string ensemble 2',
    'synthstrings 1',
    'synthstrings 2',
    'choir aahs',
    'voice oohs',
    'synth voice',
    'orchestra hit',
    # (57-64 brass)
    'trumpet',
    'trombone',
    'tuba',
    'muted trumpet',
    'french horn',
    'brass section',
    'synthbrass 1',
    'synthbrass 2',
    # (65-72 reed)
    'soprano sax',
    'alto sax',
    'tenor sax',
    'baritone sax',
    'oboe',
    'english horn',
    'bassoon',
    'clarinet',
    # (73-80 pipe)
    'piccolo',
    'flute',
    'recorder',
    'pan flute',
    'blown bottle',
    'shakuhachi',
    'whistle',
    'ocarina',
    # (81-88 synth lead)
    'lead 1 (square)',
    'lead 2 (sawtooth)',
    'lead 3 (calliope)',
    'lead 4 (chiff)',
    'lead 5 (charang)',
    'lead 6 (voice)',
    'lead 7 (fifths)',
    'lead 8 (bass+lead)',
    # (89-96 synth pad)
    'pad 1 (new age)',
    'pad 2 (warm)',
    'pad 3 (polysynth)',
    'pad 4 (choir)',
    'pad 5 (bowed)',
    'pad 6 (metallic)',
    'pad 7 (halo)',
    'pad 8 (sweep)',
    # (97-104 synth effects)
    'fx 1 (rain)',
    'fx 2 (soundtrack)',
    'fx 3 (crystal)',
    'fx 4 (atmosphere)',
    'fx 5 (brightness)',
    'fx 6 (goblins)',
    'fx 7 (echoes)',
    'fx 8 (sci-fi)',
    # (105-112 ethnic)
    'sitar',
    'banjo',
    'shamisen',
    'koto',
    'kalimba',
    'bagpipe',
    'fiddle',
    'shanai',
    # (113-120 percussive)
    'tinkle bell',
    'agogo',
    'steel drums',
    'woodblock',
    'taiko drum',
    'melodic tom',
    'synth drum',
    'reverse cymbal',
    # (121-128 sound effects)
    'guitar fret noise',
    'breath noise',
    'seashore',
    'bird tweet',
    'telephone ring',
    'helicopter',
    'applause',
    'gunshot',
    # (channel 10 drum-kits - subtract 32768 to get program no.)
    'standard kit',
    'standard drums',
    'drums',
    'room kit',
    'room drums',
    'power kit',
    'power drums',
    'rock drums',
    'electronic kit',
    'electronic drums',
    'tr-808 kit',
    'tr-808 drums',
    'jazz kit',
    'jazz drums',
    'brush kit',
    'brush drums',
    'orchestra kit',
    'orchestra drums',
    'classical drums',
    'sfx kit',
    'sfx drums',
    'mt-32 kit',
    'mt-32 drums',
    'cm-64 kit',
    'cm-64 drums',
)


grobs = (
    'Accidental',
    'AccidentalCautionary',
    'AccidentalPlacement',
    'AccidentalSuggestion',
    'Ambitus',
    'AmbitusAccidental',
    'AmbitusLine',
    'AmbitusNoteHead',
    'Arpeggio',
    'BalloonTextItem',
    'BarLine',
    'BarNumber',
    'BassFigure',
    'BassFigureAlignment',
    'BassFigureAlignmentPositioning',
    'BassFigureBracket',
    'BassFigureContinuation',
    'BassFigureLine',
    'Beam',
    'BendAfter',
    'BreakAlignGroup',
    'BreakAlignment',
    'BreathingSign',
    'ChordName',
    'Clef',
    'ClusterSpanner',
    'ClusterSpannerBeacon',
    'CombineTextScript',
    'Custos',
    'DotColumn',
    'Dots',
    'DoublePercentRepeat',
    'DoublePercentRepeatCounter',
    'DynamicLineSpanner',
    'DynamicText',
    'DynamicTextSpanner',
    'Episema',
    'Fingering',
    'FretBoard',
    'Glissando',
    'GraceSpacing',
    'GridLine',
    'GridPoint',
    'Hairpin',
    'HarmonicParenthesesItem',
    'HorizontalBracket',
    'InstrumentName',
    'InstrumentSwitch',
    'KeyCancellation',
    'KeySignature',
    'LaissezVibrerTie',
    'LaissezVibrerTieColumn',
    'LedgerLineSpanner',
    'LeftEdge',
    'LigatureBracket',
    'LyricExtender',
    'LyricHyphen',
    'LyricSpace',
    'LyricText',
    'MeasureGrouping',
    'MelodyItem',
    'MensuralLigature',
    'MetronomeMark',
    'MultiMeasureRest',
    'MultiMeasureRestNumber',
    'MultiMeasureRestText',
    'NonMusicalPaperColumn',
    'NoteCollision',
    'NoteColumn',
    'NoteHead',
    'NoteName',
    'NoteSpacing',
    'OctavateEight',
    'OttavaBracket',
    'PaperColumn',
    'ParenthesesItem',
    'PercentRepeat',
    'PercentRepeatCounter',
    'PhrasingSlur',
    'PianoPedalBracket',
    'RehearsalMark',
    'RepeatSlash',
    'RepeatTie',
    'RepeatTieColumn',
    'Rest',
    'RestCollision',
    'Script',
    'ScriptColumn',
    'ScriptRow',
    'SeparationItem',
    'Slur',
    'SostenutoPedal',
    'SostenutoPedalLineSpanner',
    'SpacingSpanner',
    'SpanBar',
    'StaffGrouper',
    'StaffSpacing',
    'StaffSymbol',
    'StanzaNumber',
    'Stem',
    'StemTremolo',
    'StringNumber',
    'StrokeFinger',
    'SustainPedal',
    'SustainPedalLineSpanner',
    'System',
    'SystemStartBar',
    'SystemStartBrace',
    'SystemStartBracket',
    'SystemStartSquare',
    'TabNoteHead',
    'TextScript',
    'TextSpanner',
    'Tie',
    'TieColumn',
    'TimeSignature',
    'TrillPitchAccidental',
    'TrillPitchGroup',
    'TrillPitchHead',
    'TrillSpanner',
    'TupletBracket',
    'TupletNumber',
    'UnaCordaPedal',
    'UnaCordaPedalLineSpanner',
    'VaticanaLigature',
    'VerticalAlignment',
    'VerticalAxisGroup',
    'VoiceFollower',
    'VoltaBracket',
    'VoltaBracketSpanner',
)


def schemeprops(grob = None):
    """
    Returns the list of scheme properties the named grob type
    supports.
    """
    # FIXME:
    # - get those from LilyPond
    # - return only properties relevant to the grob
    # - do something with the embedded documentation
    return all_user_grob_properties


all_user_grob_properties = (
    'add-stem-support',
    'after-last-staff-spacing',
    'after-line-breaking',
    'align-dir',
    'allow-loose-spacing',
    'allow-span-bar',
    'alteration',
    'alteration-alist',
    'annotation',
    'arpeggio-direction',
    'arrow-length',
    'arrow-width',
    'auto-knee-gap',
    'average-spacing-wishes',
    'avoid-note-head',
    'avoid-slur',
    'axes',
    'bar-size',
    'base-shortest-duration',
    'baseline-skip',
    'beam-thickness',
    'beam-width',
    'beamed-stem-shorten',
    'beaming',
    'beamlet-default-length',
    'beamlet-max-length-proportion',
    'before-line-breaking',
    'between-cols',
    'between-staff-spacing',
    'bound-details',
    'bound-padding',
    'bracket-flare',
    'bracket-visibility',
    'break-align-anchor',
    'break-align-anchor-alignment',
    'break-align-orders',
    'break-align-symbol',
    'break-align-symbols',
    'break-overshoot',
    'break-visibility',
    'breakable',
    'c0-position',
    'circled-tip',
    'clip-edges',
    'collapse-height',
    'color',
    'common-shortest-duration',
    'concaveness',
    'connect-to-neighbor',
    'control-points',
    'damping',
    'dash-definition',
    'dash-fraction',
    'dash-period',
    'default-direction',
    'default-next-staff-spacing',
    'details',
    'digit-names',
    'direction',
    'dot-count',
    'dot-negative-kern',
    'dot-placement-list',
    'duration-log',
    'eccentricity',
    'edge-height',
    'edge-text',
    'expand-limit',
    'extra-dy',
    'extra-offset',
    'extra-spacing-height',
    'extra-spacing-width',
    'extra-X-extent',
    'extra-Y-extent',
    'flag',
    'flag-count',
    'flag-style',
    'font-encoding',
    'font-family',
    'font-name',
    'font-series',
    'font-shape',
    'font-size',
    'force-hshift',
    'fraction',
    'french-beaming',
    'fret-diagram-details',
    'full-length-padding',
    'full-length-to-extent',
    'full-measure-extra-space',
    'full-size-change',
    'gap',
    'gap-count',
    'glyph',
    'glyph-name',
    'glyph-name-alist',
    'grow-direction',
    'hair-thickness',
    'harp-pedal-details',
    'head-direction',
    'height',
    'height-limit',
    'hide-tied-accidental-after-break',
    'horizontal-shift',
    'horizontal-skylines',
    'ignore-collision',
    'implicit',
    'inspect-index',
    'inspect-quants',
    'inter-loose-line-spacing',
    'inter-staff-spacing',
    'keep-fixed-while-stretching',
    'keep-inside-line',
    'kern',
    'knee',
    'knee-spacing-correction',
    'labels',
    'layer',
    'ledger-line-thickness',
    'left-bound-info',
    'left-padding',
    'length',
    'length-fraction',
    'line-break-penalty',
    'line-break-permission',
    'line-break-system-details',
    'line-count',
    'line-positions',
    'line-thickness',
    'long-text',
    'max-beam-connect',
    'max-stretch',
    'measure-count',
    'measure-length',
    'merge-differently-dotted',
    'merge-differently-headed',
    'minimum-distance',
    'minimum-length',
    'minimum-length-fraction',
    'minimum-space',
    'minimum-X-extent',
    'minimum-Y-extent',
    'neutral-direction',
    'neutral-position',
    'next',
    'next-staff-spacing',
    'no-alignment',
    'no-ledgers',
    'no-stem-extend',
    'non-affinity-spacing',
    'non-default',
    'non-musical',
    'note-names',
    'outside-staff-horizontal-padding',
    'outside-staff-padding',
    'outside-staff-priority',
    'packed-spacing',
    'padding',
    'padding-pairs',
    'page-break-penalty',
    'page-break-permission',
    'page-turn-penalty',
    'page-turn-permission',
    'parenthesized',
    'positions',
    'prefer-dotted-right',
    'ratio',
    'remove-empty',
    'remove-first',
    'restore-first',
    'rhythmic-location',
    'right-bound-info',
    'right-padding',
    'rotation',
    'same-direction-correction',
    'script-priority',
    'self-alignment-X',
    'self-alignment-Y',
    'shorten-pair',
    'shortest-duration-space',
    'shortest-playing-duration',
    'shortest-starter-duration',
    'side-axis',
    'side-relative-direction',
    'size',
    'skyline-horizontal-padding',
    'slash-negative-kern',
    'slope',
    'slur-padding',
    'space-alist',
    'space-to-barline',
    'spacing-increment',
    'springs-and-rods',
    'stacking-dir',
    'staff-affinity',
    'staff-padding',
    'staff-position',
    'staff-space',
    'stem-attachment',
    'stem-end-position',
    'stem-spacing-correction',
    'stemlet-length',
    'stencil',
    'stencils',
    'strict-grace-spacing',
    'strict-note-spacing',
    'stroke-style',
    'style',
    'text',
    'text-direction',
    'thick-thickness',
    'thickness',
    'thin-kern',
    'threshold', #removed in 2.14
    'tie-configuration',
    'to-barline',
    'toward-stem-shift',
    'transparent',
    'uniform-stretching',
    'used',
    'vertical-skylines',
    'when',
    'whiteout',
    'width',
    'word-space',
    'X-extent',
    'X-offset',
    'Y-extent',
    'Y-offset',
    'zigzag-length',
    'zigzag-width',
)


schemefuncs = (
    'set-accidental-style \'',
    'set-global-staff-size',
    'set-octavation',
    'define-public',
    'define-music-function',
    'define-markup-command',
    'markup',
    'parser',
    'location',
    'number?',
    'string?',
    'pair?',
    'ly:duration?',
    'ly:grob?',
    'ly:make-moment',
    'ly:make-pitch',
    'ly:music?',
    'ly:moment?',
    'ly:format',
    'markup?',
    'interpret-markup',
    'make-line-markup',
    'make-center-markup',
    'make-column-markup',
    'make-musicglyph-markup',
    'color?',
    'rgb-color',
    'x11-color \'',
)


headervars = (
    'dedication',
    'title',
    'subtitle',
    'subsubtitle',
    'poet',
    'composer',
    'meter',
    'opus',
    'arranger',
    'instrument',
    'piece',
    'breakbefore',
    'copyright',
    'tagline',
    'mutopiatitle',
    'mutopiacomposer',
    'mutopiapoet',
    'mutopiaopus',
    'mutopiainstrument',
    'date',
    'enteredby',
    'source',
    'style',
    'maintainer',
    'maintainerEmail',
    'maintainerWeb',
    'moreInfo',
    'lastupdated',
    'texidoc',
    'footer',
)
    

papervars = (
    # page
    'paper-height',
    'paper-width',
    'top-margin',
    'bottom-margin',
    'left-margin',
    'right-margin',
    'line-width',
    
    # vertical
    'after-title-space', # 2.12
    'after-title-spacing', # 2.14
    'before-title-space', # 2.12
    'before-title-spacing', # 2.14
    'between-system-padding', # 2.12
    'between-system-space', # 2.12
    'between-scores-system-spacing', # 2.14
    'between-system-spacing', # 2.14
    'between-title-space', # 2.12
    'between-title-spacing', # 2.14
    'bottom-system-spacing', # 2.14
    'top-title-spacing', # 2.14
    'top-system-spacing', # 2.14
    'page-top-space', # 2.12 only
    
    # horizontal
    'binding-offset', # 2.14
    'horizontal-shift',
    'indent',
    'short-indent',
    'two-sided', # 2.14
    'inner-margin', # 2.14
    'outer-margin', # 2.14
    
    # debugging
    'annotate-spacing',
    
    # other
    'auto-first-page-number',
    'blank-last-page-force',
    'blank-page-force',
    'check-consistency', # 2.14
    'first-page-number',
    'foot-separation', # not in 2.14?
    'head-separation', # not in 2.14?
    'max-systems-per-page', # 2.14
    'min-systems-per-page', # 2.14
    'page-breaking-between-system-padding',
    'page-count',
    'page-limit-inter-system-space',
    'page-limit-inter-system-space-factor',
    'page-spacing-weight', # 2.14
    'print-all-headers',
    'print-first-page-number',
    'print-page-number',
    'ragged-bottom',
    'ragged-last',
    'ragged-last-bottom',
    'ragged-right',
    'system-separator-markup',
    'system-count',
    'systems-per-page', # 2.14
    
    # different markups
    'bookTitleMarkup',
    'evenFooterMarkup',
    'evenHeaderMarkup',
    'oddFooterMarkup',
    'oddHeaderMarkup',
    'scoreTitleMarkup',
    'tocItemMarkup',
    'tocTitleMarkup',
    
    # undocumented?
    #'blank-after-score-page-force',
    #'force-assignment',
    #'input-encoding',
    #'output-scale',
)


layoutvars = (
    'indent',
    'short-indent',
    'system-count',
)


contextproperties = (
    'aDueText',
    'alignAboveContext',
    'alignBassFigureAccidentals',
    'alignBelowContext',
    #'allowBeamBreak', #not in 2.12 and 2.14
    'associatedVoice',
    'autoAccidentals',
    'autoBeamCheck',
    'autoBeaming',
    #'autoBeamSettings', # moved to beamSettings in 2.14
    'autoCautionaries',
    'automaticBars',
    'barAlways',
    'barCheckSynchronize',
    'barNumberVisibility',
    'bassFigureFormatFunction',
    'bassStaffProperties',
    'baseMoment',
    'beamExceptions',
    'beamSettings',
    'beatGrouping',
    'beatLength',
    'beatStructure',
    'chordChanges',
    'chordNameExceptions',
    'chordNameExceptionsFull',
    'chordNameExceptionsPartial',
    'chordNameFunction',
    'chordNameSeparator',
    'chordNoteNamer',
    'chordPrefixSpacer',
    'chordRootNamer',
    'clefGlyph',
    'clefOctavation',
    'clefPosition',
    'completionBusy',
    'connectArpeggios',
    'countPercentRepeats',
    'createKeyOnClefChange',
    'createSpacing',
    'crescendoSpanner',
    'crescendoText',
    'currentBarNumber',
    'decrescendoSpanner',
    'decrescendoText',
    'defaultBarType',
    'doubleRepeatType',
    'doubleSlurs',
    'drumPitchTable',
    'drumStyleTable',
    #'dynamicAbsoluteVolumeFunction', # not in 2.12 and 2.14
    'explicitClefVisibility',
    'explicitKeySignatureVisibility',
    'extendersOverRests',
    'extraNatural',
    'figuredBassAlterationDirection',
    'figuredBassCenterContinuations',
    'figuredBassFormatter',
    'figuredBassPlusDirection',
    'fingeringOrientations',
    'firstClef',
    'followVoice',
    'fontSize',
    'forbidBreak',
    'forceClef',
    'fretLabels',
    'gridInterval',
    #'hairpinToBarline', # not in 2.12 and 2.14
    'harmonicAccidentals',
    'harmonicDots',
    'highStringOne',
    'ignoreBarChecks',
    'ignoreFiguredBassRest',
    'ignoreMelismata',
    'implicitBassFigures',
    'implicitTimeSignatureVisibility',
    'instrumentCueName',
    'instrumentEqualizer',
    'instrumentName',
    'instrumentTransposition',
    'internalBarNumber',
    'keepAliveInterfaces',
    'keyAlterationOrder',
    'keySignature',
    'lyricMelismaAlignment',
    'majorSevenSymbol',
    'markFormatter',
    'maximumFretStretch',
    'measureLength',
    'measurePosition',
    'melismaBusyProperties',
    'metronomeMarkFormatter',
    'middleCClefPosition',
    'middleCOffset',
    'middleCPosition',
    'midiInstrument',
    'midiMaximumVolume',
    'midiMinimumVolume',
    'minimumFret',
    'minimumPageTurnLength',
    'minimumRepeatLengthForPageTurn',
    'noChordSymbol', # since 2.14
    'noteToFretFunction',
    'ottavation',
    'output',
    'pedalSostenutoStrings',
    'pedalSostenutoStyle',
    'pedalSustainStrings',
    'pedalSustainStyle',
    'pedalUnaCordaStrings',
    'pedalUnaCordaStyle',
    'predefinedDiagramTable',
    'printKeyCancellation',
    'printOctaveNames',
    'printPartCombineTexts',
    'proportionalNotationDuration',
    'recordEventSequence',
    'rehearsalMark',
    'repeatCommands',
    'repeatCountVisibility',
    'restNumberThreshold',
    'shapeNoteStyles',
    'shortInstrumentName',
    'shortVocalName',
    'skipBars',
    'skipTypesetting',
    'soloIIText',
    'soloText',
    'squashedPosition',
    'staffLineLayoutFunction',
    'stanza',
    'stemLeftBeamCount',
    'stemRightBeamCount',
    'stringNumberOrientations',
    'stringOneTopmost',
    'stringTunings',
    'strokeFingerOrientations',
    'subdivideBeams',
    'suggestAccidentals',
    'systemStartDelimiter',
    'systemStartDelimiterHierarchy',
    'tablatureFormat',
    'tempoHideNote',
    'tempoText',
    'tempoUnitCount',
    'tempoUnitDuration',
    'tempoWholesPerMinute',
    'tieWaitForNote',
    'timeSignatureFraction',
    'timing',
    'tonic',
    'topLevelAlignment', # since 2.14
    'trebleStaffProperties',
    'tremoloFlags',
    'tupletFullLength',
    'tupletFullLengthNote',
    'tupletSpannerDuration',
    'useBassFigureExtenders',
    'verticallySpacedContexts',
    'vocalName',
    'voltaSpannerDuration',
    'whichBar',
)


repeat_types = (
    'unfold',
    'percent',
    'volta',
    'tremolo',
)


accidentalstyles = (
    'default',
    'voice',
    'modern',
    'modern-cautionary',
    'modern-voice',
    'modern-voice-cautionary',
    'piano',
    'piano-cautionary',
    'neo-modern',
    'neo-modern-cautionary',
    'neo-modern-voice',
    'neo-modern-voice-cautionary',
    'dodecaphonic',
    'teaching',
    'no-reset',
    'forget',
)


clefs_plain = (
    'treble',
    'violin',
    'G',
    'alto',
    'C',
    'tenor',
    'bass',
    'subbass',
    'F',
    'french',
    'mezzosoprano',
    'soprano',
    'varbaritone',
    'baritone',
    'percussion',
    'tab',
)
    

clefs = clefs_plain + (
    'treble_8',
    'bass_8',
)


break_visibility = (
    'all-invisible',
    'begin-of-line-visible',
    'end-of-line-visible',
    'all-visible',
    'begin-of-line-invisible',
    'end-of-line-invisible',
    'center-invisible',
)

mark_formatters = (
    'format-mark-alphabet',
    'format-mark-barnumbers',
    'format-mark-letters',
    'format-mark-numbers',
    'format-mark-box-alphabet',
    'format-mark-box-barnumbers',
    'format-mark-box-letters',
    'format-mark-box-numbers',
    'format-mark-circle-alphabet',
    'format-mark-circle-barnumbers',
    'format-mark-circle-letters',
    'format-mark-circle-numbers',
)


set_context_re = re.compile(r'\\(un)?set\s+(' + '|'.join(contexts) + r')\s*.\s*$')
context_re = re.compile(r'\b(' + '|'.join(contexts) + r')\s*\.\s*$')
grob_re = re.compile(r'\b(' + '|'.join(grobs) + r')\s*$')
