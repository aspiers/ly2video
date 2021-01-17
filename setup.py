#!/usr/bin/env python3

from setuptools import setup

setup(name='ly2video',
      version='0.4.1',
      description='Converts Lilypond files to videos',
      license='GPLv3',
      author='Adam Spiers',
      author_email='github@adamspiers.org',
      url='https://github.com/aspiers/ly2video',
      packages=['ly2video'],
      entry_points={
          'console_scripts': [
              'ly2video = ly2video.cli:main'
          ]
      },
      scripts=[
          'scripts/midi-rubato',
          'scripts/xsc2beatmap'
      ],
)
