#!/usr/bin/env python2

from setuptools import setup

setup(name='ly2video',
      version='0.4.1',
      description='Converts Lilypond files to videos',
      license='GPLv3',
      author='Adam Spiers',
      author_email='github@adamspiers.org',
      url='https://github.com/aspiers/ly2video',
      packages=['ly'],
      scripts=['ly2video.py', 'midi-rubato', 'xsc2beatmap'],
)
