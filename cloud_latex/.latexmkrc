#!/usr/bin/env perl

# upLaTeX + dvipdfmx
$latex = 'uplatex -synctex=1 -halt-on-error -interaction=nonstopmode %O %S';
$bibtex = 'upbibtex %O %B';
$dvipdf = 'dvipdfmx %O -o %D %S';
$makeindex = 'mendex %O -o %D %S';
$pdf_mode = 3;  # dvipdfmx
$max_repeat = 5;
