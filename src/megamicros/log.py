# megamicros.log.py
#
# ® Copyright 2024-2025 Bimea
# Author: bruno.gas@bimea.io
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Megamicros logging utilities.

This module provides logging functionality for the Megamicros library with colored output
and file logging capabilities.

Features:
    - Stream handler for console output with colors (Unix-like systems)
    - File handler for persistent logging to './megamicros.log'
    - Configurable log levels: debug, info, warning, error, critical
    - Default level set to NOTSET (no output until explicitly configured)

Examples:
    Basic usage::

        from megamicros import log
        
        # Set logging level
        log.setLevel('info')
        
        # Log messages
        log.debug('Debug message')
        log.info('System ready')
        log.warning('This is a warning')
        log.error('An error occurred')
        log.critical('Critical system failure')

    Advanced usage::

        from megamicros import log
        import logging
        
        # Enable debug mode for development
        log.setLevel('debug')
        
        # Check current level
        current_level = log.level
        print(f"Current log level: {current_level}")
        
        # Use with exception handling
        try:
            # Your code here
            pass
        except Exception as e:
            log.error(f"Exception caught: {e}")
            if log.level == logging.DEBUG:
                log.tracedebug()  # Print full traceback

    Testing all log levels::

        from megamicros import log
        
        log.setLevel('debug')
        log.debug('This is a debug message')
        log.info('This is an info message') 
        log.warning('This is a warning message')
        log.error('This is an error message')
        log.critical('This is a critical message')

Note:
    Colors are automatically disabled on Windows systems and enabled on Unix-like systems.
    The default log file './megamicros.log' is created in the current working directory.

See Also:
    formats_str(): Get available format options and conversions
    tracedebug(): Print debug trace information

Documentation:
    Full MegaMicros documentation is available at: https://readthedoc.bimea.io
"""



import logging
import traceback
import platform

DEBUG_MODE = True
DEFAULT_LOGFILE = './megamicros.log'

class MuFormatter(logging.Formatter):
	"""Logging Formatter to add colors and count warning / errors
	
	Note that the colors are not working on Windows
	"""

	if platform.system() == 'Windows':
		red = ""
		green = ""
		blue = ""
		magenta = ""
		grey = ""
		yellow = ""
		bold_red = ""
		bold_black = ""
		reset = ""
	else:	
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
mulog_ch.setFormatter( MuFormatter() )

mulog_ch2 = logging.FileHandler( DEFAULT_LOGFILE, mode='a', encoding='utf-8', delay=False, errors=None)
mulog_ch2.setLevel( logging.DEBUG )
mulog_ch2.setFormatter( MuFormatter() )

log = logging.getLogger( __name__ )
log.addHandler( mulog_ch2 )
log.addHandler( mulog_ch )
log.setLevel( logging.NOTSET )

def formats_str( arg: int|str|None = None ) -> int|str|list[dict[str, str|int]]|None :
	"""Convert between log level names and logging constants.

	This function provides bidirectional conversion between string labels
	('debug', 'info', etc.) and their corresponding logging module constants.

	Args:
		arg: Can be:
			- int: logging constant (returns corresponding string label)
			- str: string label (returns corresponding logging constant) 
			- None: returns list of all available formats
			
	Returns:
		- str: label name if arg is int
		- int: logging constant if arg is str  
		- list: all available formats if arg is None
		- None: if arg type is invalid
		
	Examples:
		>>> formats_str(logging.DEBUG)
		'debug'
		>>> formats_str('info')
		20
		>>> formats_str()
		[{'label': 'debug', 'format': 10}, ...]
	"""
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
	"""Print traceback information if debug level is active.
    
    Only prints the full exception traceback when the current log level
    is set to DEBUG. Does nothing at other log levels.
    
    Examples:
        >>> try:
        ...     1/0
        ... except:
        ...     log.tracedebug()  # Only prints if log.level == logging.DEBUG
    """
	if log.level == logging.DEBUG:
		print( traceback.format_exc() )
