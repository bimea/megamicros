# megamicros.log.py logging messages process for MegaMicros libraries
#
# Copyright (c) 2023 Sorbonne Université
# Author: bruno.gas@sorbonne-universite.fr
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
MegaMicros documentation is available on https://readthedoc.biimea.io

Usage:
 >>> import megamicro.data
Or:
 >>> from  megamicro.data import log
"""

import logging
import traceback

DEBUG_MODE = True
DEFAULT_LOGFILE = './megamicros.log'

class Mu32Formatter(logging.Formatter):
	"""Logging Formatter to add colors and count warning / errors"""

	green = "\x1b[32;21m"
	blue = "\x1b[34;21m"
	magenta = "\x1b[35;21m"
	grey = "\x1b[38;21m"
	yellow = "\x1b[33;21m"
	red = "\x1b[31;21m"
	bold_red = "\x1b[31;1m"
	bold_black = "\x1b[30;1m"
	reset = "\x1b[0m"
	start_format = magenta + "%(asctime)s " + reset + bold_black + "[%(levelname)s]: " + reset

	FORMATS = {
		logging.DEBUG: start_format + green + "in %(name)s (%(filename)s:%(lineno)d): %(message)s" + reset,
		logging.INFO: magenta + "%(asctime)s " + reset + "[%(levelname)s]: " + blue + "%(message)s" + reset,
        logging.WARNING: start_format + yellow + "in %(name)s (%(filename)s:%(lineno)d): %(message)s" + reset,
        logging.ERROR: start_format + red + "in %(name)s (%(filename)s:%(lineno)d): %(message)s" + reset,
        logging.CRITICAL: start_format + bold_red + "in %(name)s (%(filename)s:%(lineno)d): %(message)s" + reset
    }

	def format(self, record):
		log_fmt = self.FORMATS.get( record.levelno )
		formatter = logging.Formatter( log_fmt )
		return formatter.format( record )


mulog_ch = logging.StreamHandler()
mulog_ch.setLevel( logging.DEBUG )
mulog_ch.setFormatter( Mu32Formatter() )

mulog_ch2 = logging.FileHandler( DEFAULT_LOGFILE, mode='a', encoding='utf-8', delay=False, errors=None)
mulog_ch2.setLevel( logging.DEBUG )
mulog_ch2.setFormatter( Mu32Formatter() )

log = logging.getLogger( __name__ )
log.addHandler( mulog_ch2 )
log.addHandler( mulog_ch )
log.setLevel( logging.NOTSET )

def formats_str( arg: int|str|None = None ) -> int|str|list[dict[str, str|int]]|None :

	formats: list[dict[str, str|int]] = [
		{'label': 'debug', 'format': logging.DEBUG },
		{'label': 'info', 'format': logging.INFO },
		{'label': 'warning', 'format': logging.WARNING },
		{'label': 'error', 'format': logging.ERROR },
		{'label': 'critical', 'format': logging.CRITICAL },
	]

	if type( arg ) == int:
		return next( ( format['label'] for format in formats if format['format']==arg ), None )
	elif type( arg ) == str:
		return next( ( format['format'] for format in formats if format['label']==arg ), None )
	elif arg is None:
		return formats
	else:
		return None
	

def tracedebug():
	if log.level == logging.DEBUG:
		print( traceback.format_exc() )
