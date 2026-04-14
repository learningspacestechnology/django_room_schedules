# EdGEL Fonts


The following weights are in use:

**Crimson Text** - Last modified 2014-06-19 (5b3f19c9114746030129ae2fe23ecadca73aecd1)

* 400 normal
* 400 italic

**Source Sans Pro** - Last modified 2017-06-05 (v10)

* 300 normal
* 300 italic
* 400 normal
* 400 italic
* 600 normal
* 700 normal
* 700 italic

Fonts licensed under [SIL Open Font License, 1.1](http://scripts.sil.org/OFL):
 
* "Crimson Text" - Copyright (c) 2010, Sebastian Kosch (sebastian@aldusleaf.org), with Reserved Font Name "Crimson".
* "Source Sans Pro" - Copyright 2010, 2012, 2014 Adobe Systems Incorporated (http://www.adobe.com/), with Reserved Font Name Source.

## Source Sans Pro
The "Source Sans Pro" font is sourced from [Google Fonts](https://fonts.google.com/).

It can be updated by downloading from the hosted [Google Web Fonts Helper](https://google-webfonts-helper.herokuapp.com/).
See https://github.com/majodev/google-webfonts-helper for source and details of the API as an alternative way to access these files.

## Crimson Text
The "Crimson Text" font (or just "Crimson") currently only has an old, incomplete version hosted on Google Fonts.  The font can be downloaded from [https://github.com/skosch/Crimson/commits/master](https://github.com/skosch/Crimson/commits/master)

To subset the font, you can use [Font Squirrel](https://www.fontsquirrel.com/tools/webfont-generator) and upload the OTF Desktop file.  Use expert settings:

* Font formats: WOFF, WOFF2
* Truetype hinting: keep existing
* Rendering: Nothing selected
* Fix missing glyphs: Spaces and hyphens
* X-Height matching: None
* Protection: None
* Subsetting: Custom subsetting.  Nothing should be selected, only the Unicode Ranges filled in (see below).
* OpenType features: Nothing selected.
* OpenType Flattening: Nothing selected.
* CSS: No Base64 encoding, no Style link, any CSS filename you like.
* Advanced options: Font name suffix should match the character subset being generated (see below).
 
Note, the most recent commit (at time of writing 3df8aeb on 17 March 2017) cannot be used because the kerning has been corrupted, most notably on the lower case letter "a".

The unicode ranges are the same as used by Google Fonts:

* cyrillic-ext: 0460-052F,20B4,2DE0-2DFF,A640-A69F
* cyrillic: 0400-045F,0490-0491,04B0-04B1,2116
* greek-ext: 1F00-1FFF
* greek: 0370-03FF
* vietnamese: 0102-0103,1EA0-1EF9,20AB
* latin-ext: 0100-024F,1E00-1EFF,20A0-20AB,20AD-20CF,2C60-2C7F,A720-A7FF
* latin: 0000-00FF,0131,0152-0153,02C6,02DA,02DC,2000-206F,2074,20AC,2212,2215
* all: Not subsetted. 

We use a unicode range of U+E6E1 for the fallback, not subsetted (large) font files for browsers that don't support unicode-range since this code should not occur on a page in normal use.
