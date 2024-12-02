# mu256.core.py python program interface for MegaMicro Mu256 transceiver 
#
# Copyright (c) 2022 Distalsense
# Author: bruno.gas@distalsense.com
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
Mu256 documentation is available on https://distalsense.io
See documentation on usb device programming with libusb on https://pypi.org/project/libusb1/1.3.0/#documentation
Examples are available on https://github.com/vpelletier/python-libusb1

Please, note that the following packages should be installed before using this program:
	> pip install libusb1
"""


__VERSION__ = 1.0

import sys
import logging
import libusb1
import usb1
import time
from ctypes import byref, sizeof, create_string_buffer, CFUNCTYPE
import numpy as np
from math import ceil as ceil
import queue

MU_BEAMS_NUMBER				= 32
MU_BEAM_MEMS_NUMBER			= 8
MU_ANALOG_CHANNELS		    = 4
MU_LOGIC_CHANNELS		    = 4

MU_USB2_BUS_ADDRESS 		= 0x82

MU_USB3_BUS_ADDRESS 		= 0x81
MU_VENDOR_ID 				= 0xFE27
MU_VENDOR_PRODUCT			= 0xAC01

MU_DEFAULT_CLOCKDIV			= 0x09
MU_DEFAULT_PACKET_SIZE		= 512*1024
MU_DEFAULT_PACKET_NUMBER	= 0
MU_DEFAULT_TIMEOUT			= 1000
MU_DEFAULT_DATATYPE			= "int32"
MU_DEFAULT_ACTIVATED_MEMS	= (0, )
MU_DEFAULT_SAMPLING_FREQUENCY	= 50000

LIBUSB_RECIPIENT_DEVICE 	= 0x00
LIBUSB_REQUEST_TYPE_VENDOR 	= 0x40
LIBUSB_ENDPOINT_OUT 		= 0x00
LIBUSB_DEFAULT_TIMEOUT		= 1000

MU_CMD_ACTIVE 					= 0x05
MU_DEFAULT_BUFFERS_NUMBER 		= 8
MU_TRANSFER_DATAWORDS_SIZE		= 4
MU_TRANSFER_DATABYTES_SIZE		= MU_TRANSFER_DATAWORDS_SIZE * 8
MU_DEFAULT_BUFFER_LENGTH		= 512
MU_DEFAULT_DURATION				= 1


class Mu256Formatter(logging.Formatter):
	"""Logging Formatter to add colors and count warning / errors"""

	green = "\x1b[256;21m"
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



mu256ch = logging.StreamHandler()
mu256ch.setLevel( logging.DEBUG )
mu256ch.setFormatter( Mu256Formatter() )

mu256log = logging.getLogger( __name__ )
mu256log.setLevel( logging.WARNING )
mu256log.addHandler( mu256ch )


class Mu256Exception( Exception ):
	value = None

	def __init__( self, value=None ):
		Exception.__init__( self )
		if value is not None:
			self.value = value

	def __str__(self):
		return '%s [%s]' % ( 'Mu256Exception: ', self.value )


class MegaMicro:
	pass

class Mu256( MegaMicro ):

	def __init__( self ):
		"""
		Set default values
		"""
		self._signal_q = queue.Queue()
		self._mems = MU_DEFAULT_ACTIVATED_MEMS
		self._mems_number = len( self._mems )
		self._clockdiv = MU_DEFAULT_CLOCKDIV
		self._sampling_frequency = 500000 / ( MU_DEFAULT_CLOCKDIV + 1 )
		self._buffer_length = MU_DEFAULT_BUFFER_LENGTH
		self._buffers_number = MU_DEFAULT_BUFFERS_NUMBER
		self._duration = MU_DEFAULT_DURATION
		self._transfers_count = int( ( MU_DEFAULT_DURATION * ( 500000 / ( MU_DEFAULT_CLOCKDIV + 1 ) ) )//MU_DEFAULT_BUFFER_LENGTH )
		self._datatype = MU_DEFAULT_DATATYPE
		self._callback_fn = None
		self._transfer_index = 0
		self._recording = False

	def __del__( self ):
		mu256log.info( '-'*20 )
		mu256log.info('Mu256: end')

	@property
	def signal_q( self ):
		return self._signal_q

	@property
	def mems( self ):
		return self._mems

	@property
	def mems_number( self ):
		return self._mems_number

	@property
	def clockdiv( self ):
		return self._clockdiv

	@property
	def sampling_frequency( self ):
		return self._sampling_frequency

	@property
	def buffer_length( self ):
		return self._buffer_length

	@property
	def buffers_number( self ):
		return self._buffers_number

	@property
	def duration( self ):
		return self._duration

	@property
	def transfers_count( self ):
		return self._transfers_count

	@property
	def datatype( self ):
		return self._datatype

	def check_usb( self, vendor_id, vendor_pr, verbose=True ):
		"""
		check for Mu256 usb plug in verbose mode off
		"""
		if verbose==False:
			with usb1.USBContext() as context:
				handle = context.openByVendorIDAndProductID( 
					vendor_id,
					vendor_pr,
					skip_on_error=True,
				)
				if handle is None:
					raise Mu256Exception( 'Mu256 USB3 device is not present or user is not allowed to access device' )

				try:
					with handle.claimInterface( 0 ):
						pass
				except Exception as e:	
					raise Mu256Exception( 'Mu256 USB3 device buzy: cannot claim it' )

			return

		"""
		check for Mu256 usb plug in verbose mode on
		"""
		mu256log.info('Mu256::check_usb')

		Mu256_device = None
		mu256log.info( 'found following devices:' )
		with usb1.USBContext() as context:
			mu256log.info( '-'*20 )
			for device in context.getDeviceIterator( skip_on_error=True ):
				mu256log.info( 'ID %04x:%04x' % (device.getVendorID(), device.getProductID()), '->'.join(str(x) for x in ['Bus %03i' % (device.getBusNumber(), )] + device.getPortNumberList()), 'Device', device.getDeviceAddress() )
				if device.getVendorID() == vendor_id and device.getProductID() == vendor_pr:
					Mu256_device = device
			mu256log.info( '-'*20 )
			if Mu256_device is None:
				raise Mu256Exception( 'Mu256 USB3 device is not present or user is not allowed to access device' )
			else:
				mu256log.info( 'found MegaMicro device %04x:%04x ' % ( Mu256_device.getVendorID(), Mu256_device.getProductID() ) )

			"""
			open Usb device and claims interface
			"""	
			handle = context.openByVendorIDAndProductID( 
				vendor_id,
				vendor_pr,
				skip_on_error=True,
			)

			if handle is None:
				raise Mu256Exception( 'Mu256 USB3 device is not present or user is not allowed to access device' )

			try:
				with handle.claimInterface( 0 ):
					pass
			except Exception as e:	
				mu256log.info( 'Mu256 USB3 device buzy: cannot claim it' )
			
			mu256log.info( '-'*20 )
			mu256log.info( 'Found following device characteristics :' )
			mu256log.info( '  Bus number: ', Mu256_device.getBusNumber() )
			mu256log.info( '  ports number: ', Mu256_device.getPortNumber() )
			mu256log.info( '  device address: ', Mu256_device.getDeviceAddress() )
			deviceSpeed =  Mu256_device.getDeviceSpeed()
			if deviceSpeed  == libusb1.LIBUSB_SPEED_LOW:
				mu256log.info( '  device speed:  [LOW SPEED] (The OS doesn\'t report or know the device speed)' )
			elif deviceSpeed == libusb1.LIBUSB_SPEED_FULL:
				mu256log.info( '  device speed:  [FULL SPEED] (The device is operating at low speed (1.5MBit/s))' )
			elif deviceSpeed == libusb1.LIBUSB_SPEED_HIGH:
				mu256log.info( '  device speed:  [HIGH SPEED] (The device is operating at full speed (12MBit/s))' )
			elif deviceSpeed == libusb1.LIBUSB_SPEED_SUPER:
				mu256log.info( '  device speed:  [SUPER SPEED] (The device is operating at high speed (480MBit/s))' )
			elif deviceSpeed == libusb1.LIBUSB_SPEED_SUPER_PLUS:
				mu256log.info( '  device speed:  [SUPER PLUS SPEED] (The device is operating at super speed (5000MBit/s))' )
			elif deviceSpeed == libusb1.LIBUSB_SPEED_UNKNOWN:
				mu256log.info( '  device speed:  [LIBUSB_SPEED_UNKNOWN] (The device is operating at unknown speed)' )
			else:
				mu256log.info( '  device speed:  [?] (The device is operating at unknown speed)' )
			mu256log.info( '-'*20 )


	def ctrlWrite( self, handle, request, data ):
		"""
		Send a write command tp Mu256 FPGA through the usb interface
		"""
		ndata = handle.controlWrite(
						# command type
			LIBUSB_RECIPIENT_DEVICE | LIBUSB_REQUEST_TYPE_VENDOR | LIBUSB_ENDPOINT_OUT,
			request, 	# command
			0,			# command parameter value
			0,			# index
			data,		# data to send 
			LIBUSB_DEFAULT_TIMEOUT 
		)
		if ndata != sizeof( data ):
			mu256log.warning( 'Mu256::ctrlWrite(): command failed with ', ndata, ' data transfered against ', sizeof( data ), ' wanted ' )


	def ctrlTixels( self, handle, samples_number ):
		"""
		Set the samples number to be sent by the Mu256 system 
		"""
		buf = create_string_buffer( 5 )
		buf[0] = b'\x04'  # commande COUNT
		buf[1] = bytes(( samples_number & 0x000000ff, ) )
		buf[2] = bytes( ( ( ( samples_number & 0x0000ff00 ) >> 8 ),) )
		buf[3] = bytes( ( ( ( samples_number & 0x00ff0000 ) >> 16 ),) )
		buf[4] = bytes( ( ( ( samples_number & 0xff000000 ) >> 24 ),) )
		self.ctrlWrite( handle, 0xB4, buf )


	def ctrlResetAcq256( self, handle ):
		"""
		Reset and purge fifo
		"""
		buf = create_string_buffer( 1 )
		buf[0] = b'\x00'
		self.ctrlWrite( handle, 0xB0, buf )
		buf[0] = b'\x06'
		self.ctrlWrite( handle, 0xB0, buf )


	def ctrlResetFx3( self, handle ):

		buf = create_string_buffer( 1 )
		buf[0] = b'\x00'
		self.ctrlWrite( handle, 0xC0, buf )
		self.ctrlWrite( handle, 0xC2, buf )


	def ctrlClockdiv( self, handle, clockdiv=0x09 ):
		"""
		Init acq256
		"""
		buf = create_string_buffer( 2 )
		buf[0] = b'\x01'  # commande init
		buf[1] = clockdiv 	
		self.ctrlWrite( handle, 0xB1, buf )
		"""
		wait for mems activation 
		"""
		time.sleep(1)


	def ctrlDatatype( self, handle, datatype='int32' ):
		"""
		Set datatype
		"""
		buf = create_string_buffer( 2 )
		buf[0] = b'\x09'
		if datatype=='int32':
			buf[1] = b'\x00' 
		elif datatype=='float256':
			buf[1] = b'\x01'
		else:
			raise Mu256Exception( 'Mu256::ctrlDatatype(): Unknown data type [%s]. Please, use [int32] or [float256]' % datatype )

		self.ctrlWrite( handle, 0xB1, buf )


	def ctrlMems( self, handle, request, mems='all' ):
		"""
		Activate or deactivate MEMs
		"""
		buf = create_string_buffer( 4 )
		buf[0] = b'\x05'			# command
		buf[1] = 0x00				# module
		if mems == 'all':
			if request == 'activate':
				for beam in range( MU_BEAMS_NUMBER ):
					buf[2] = beam		# beam number
					buf[3] = 0xFF		# active MEMs map
					self.ctrlWrite( handle, 0xB3, buf )
			elif request == 'deactivate':
				for beam in range( MU_BEAMS_NUMBER ):
					buf[2] = beam		
					buf[3] = 0x00		
					self.ctrlWrite( handle, 0xB3, buf )
			else:
				raise Mu256Exception( 'In Mu256::ctrlMems(): Unknown parameter [%s]' % request )
		else:
			if request == 'activate':
				map_mems = [0 for _ in range( MU_BEAMS_NUMBER )]
				for mic in mems:
					mic_index = mic % MU_BEAM_MEMS_NUMBER
					beam_index = int( mic / MU_BEAM_MEMS_NUMBER )
					if beam_index >= MU_BEAMS_NUMBER:
						raise Mu256Exception( 'microphone index [%d] is out of range (should be less than %d)' % ( mic,  MU_BEAMS_NUMBER*MU_BEAM_MEMS_NUMBER ) )
					map_mems[beam_index] += ( 0x01 << mic_index )

				for beam in range( MU_BEAMS_NUMBER ):
					if map_mems[beam] != 0:
						buf[2] = beam
						buf[3] = map_mems[beam]				
						self.ctrlWrite( handle, 0xB3, buf )
			else:
				raise Mu256Exception( 'In Mu256::ctrlMems(): request [%s] is not implemented' % request )


	def ctrlAnalogics( self, handle, request, channels='all' ):
		"""
		Activate or deactivate analogic, status and counter channels
		"""
		buf = create_string_buffer( 4 )
		if channels == 'all':
			if request == 'deactivate':
				buf[0] = MU_CMD_ACTIVE
				buf[1] = 0x00
				buf[2] = 0xFF
				buf[3] = 0x00
				self.ctrlWrite( handle, 0xB3, buf )

	def ctrlStart( self, handle ):
		buf = create_string_buffer( 2 )
		buf[0] = 0x02
		buf[1] = 0x00
		self.ctrlWrite( handle, 0xB1, buf )


	def ctrlStop( self, handle ):
		buf = create_string_buffer( 2 )
		buf[0] = 0x03
		buf[1] = 0x00
		self.ctrlWrite( handle, 0xB1, buf )


	"""
	Callback flushing function: only intended to flush Mu256 internal buffers
	"""
	def processFlush( self, transfer ):
		if transfer.getActualLength() > 0:
			mu256log.info( ' .flushed %d data bytes' % transfer.getActualLength() )


	"""
	Callback run function: check error transfer, call user callback function and then submit for new transfer
	"""
	def processRun( self, transfer ):
		"""
		Run callback function
		"""
		if transfer.getStatus() != usb1.TRANSFER_COMPLETED:

			if ( transfer.getStatus() == usb1.TRANSFER_ERROR or transfer.getStatus() == usb1.TRANSFER_CANCELLED
				or transfer.getStatus() == usb1.TRANSFER_NO_DEVICE ):
				mu256log.error( 'transfer not completed with error [%d]. Aborting.' % transfer.getStatus() )
				return
			else:
				"""
				resubmit without processing data
				"""
				mu256log.warning( 'Mu256: Transfer not completed with code [%d]. Complete without processing data.' % transfer.getStatus() )
				if( self._recording ):
					transfer.submit()
				return

		data = np.frombuffer( transfer.getBuffer()[:transfer.getActualLength()], dtype=np.int32 )
		if len( data ) != self._buffer_length * self._mems_number:
			mu256log.warning( 'Mu256: got %d samples against %d samples desired. Complete without processing data' % ( len( data ), self._buffer_length * self._mems_number ) )
			if( self._recording ):
				transfer.submit()
			return

		"""
		Call user callback processing function if any.
		Otherwise push data in the object signal queue
		"""
		if self._callback_fn != None:
			self._callback_fn( self, data )
		else:
			self._signal_q.put( data )
		
		"""
		Resubmit transfer once data is processed and while recording mode is on
		"""
		if( self._recording ):
			transfer.submit()

		"""
		Control duration and stop acquisition if the transfer count is reach
		_transfers_count set to 0 means the acquisition is infinite loop
		"""
		self._transfer_index += 1
		if self._transfers_count != 0 and  self._transfer_index > self._transfers_count:
			self._recording = False
	


	def run( self, sampling_frequency=MU_DEFAULT_SAMPLING_FREQUENCY, buffers_number=MU_DEFAULT_BUFFERS_NUMBER, buffer_length=MU_DEFAULT_BUFFER_LENGTH, duration=MU_DEFAULT_DURATION, datatype=MU_DEFAULT_DATATYPE, mems=MU_DEFAULT_ACTIVATED_MEMS, post_callback_fn=None, callback_fn=None ):
		"""
		Run is a generic acquisition method that get signals from the activated MEMs
		- clockdiv decide for the sampling frequency. 
		The sampling frequency is given by int( 500000/( clockdiv+1 ) ).Ex: 0x09 set for 50kHz
		- buffers_number is the number of buffers used by the USB device for the data bulk transfer
		Buffers_number can be set from 1 to n>1 (default is given by MU_DEFAULT_BUFFERS_NUMBER).
		- buffer_length is the number of samples that will be sent for each microphone by the Mu256 system in each transfer buffer 
		Buffers_number_number and buffer_length have effects on latence and real time capabilities.
		Setting buffers_number to 1 should be used only for autotest purpose since it cannot ensure real time processing.
		The more buffers_number is the more real time can be ensured without timeout or data flow breaks problems.
		Conversely latency is increased.
		- duration is the desired recording time in seconds
		"""
		try:
			self._clockdiv = max( int( 500000 / sampling_frequency ) - 1, 9 )
			self._sampling_frequency = 500000 / ( self._clockdiv + 1 )
			self._buffer_length = buffer_length
			self._buffers_number = buffers_number
			self._duration = duration
			self._mems = mems
			self._mems_number = len( self._mems )
			self._transfers_count = int( ( self._duration * self._sampling_frequency ) // self._buffer_length )
			self._callback_fn = callback_fn

			"""
			Do some controls and print recording parameters
			"""
			mu256log.info( 'Mu256: Start running recording...')
			mu256log.info( '-'*20 )

			if datatype != 'int32' and datatype != 'float256':
				raise Mu256Exception( 'Unknown datatype [%s]' % datatype )
			self._datatype = datatype

			if sampling_frequency > 50000:
				mu256log.warning( 'Mu256: desired sampling frequency [%s Hz] is greater than the max admissible sampling frequency. Adjusted to 50kHz' % sampling_frequency )
			else:
				mu256log.info( 'Mu256: sampling frequency: %d Hz' % self._sampling_frequency )

			mu256log.info( ' .desired recording duration: %d s' % self._duration )
			mu256log.info( ' .minimal recording duration: %f s' % ( ( self._transfers_count*self._buffer_length ) / self._sampling_frequency ) )
			mu256log.info( ' .datatype: %s' % self._datatype )
			mu256log.info( ' .number of USB transfer buffers: %d' % self._buffers_number )
			mu256log.info( ' .buffer length in samples number: %d (%f ms duration)' % ( self._buffer_length, self._buffer_length*1000/self._sampling_frequency ) )
			mu256log.info( ' .minimal transfers count: %d' % self._transfers_count )
			mu256log.info( ' .%d activated microphones' % self._mems_number )
			mu256log.info( ' .activated microphones: %s' % str( self._mems ) )

			with usb1.USBContext() as context:
				"""
				open Usb device and claims interface
				"""	
				handle = context.openByVendorIDAndProductID( 
					MU_VENDOR_ID,
					MU_VENDOR_PRODUCT,
					skip_on_error=True,
				)
				if handle is None:
					raise Mu256Exception( 'Mu256 USB3 device is not present or user is not allowed to access device' )

				try:
					with handle.claimInterface( 0 ):

						"""
						init Mu256 and send acquisition starting command
						"""
						self.ctrlResetAcq256( handle )
						#self.ctrlResetFx3( handle )
						self.ctrlClockdiv( handle, self._clockdiv )
						self.ctrlTixels( handle, 0 )
						self.ctrlDatatype( handle, self._datatype )
						self.ctrlMems( handle, request='activate', mems=self._mems )
						self.ctrlAnalogics( handle, request='deactivate' )
						self.ctrlStart( handle )

						"""
						Allocate the list of transfer objects
						"""
						transfer_list = []
						for _ in range( self.buffers_number ):
							transfer = handle.getTransfer()
							transfer.setBulk(
								usb1.ENDPOINT_IN | MU_USB3_BUS_ADDRESS,
								self._mems_number * MU_TRANSFER_DATAWORDS_SIZE * self._buffer_length,
								callback=self.processRun
							)
							transfer.submit()
							transfer_list.append( transfer )

						"""
						Loop as long as there is at least one submitted transfer
						"""
						self._transfer_index = 0
						self._recording = True
						while any( x.isSubmitted() for x in transfer_list ):
							try:
								context.handleEvents()
							except KeyboardInterrupt:
								print( 'Mu256: keyboard interruption...' )
								self._recording = False					
							except usb1.USBErrorInterrupted:
								self._recording = False

						"""
						Send stop command to Mu256 FPGA
						"""
						self.ctrlStop( handle )

						"""
						Flush Mu256 remaining data 
						"""
						for transfer in transfer_list:
							transfer.setBulk(
								usb1.ENDPOINT_IN | MU_USB3_BUS_ADDRESS,
								self._mems_number * MU_TRANSFER_DATAWORDS_SIZE * self._buffer_length,
								callback=self.processFlush,
								timeout=1
							)
							transfer.submit()

						while any( x.isSubmitted() for x in transfer_list ):
							try:
								context.handleEvents()
							except Exception as e:
								raise Mu256Exception( 'Mu256 USB3 transfer flushing failed: [%s]' % e )

						"""
						Reset Mu256
						"""
						self.ctrlResetAcq256( handle )

				except Exception as e:	
					raise Mu256Exception( 'Mu256 USB3 run failed: [%s]' % e )

			mu256log.info( ' .end of acquisition' )
			mu256log.info( ' .processing data...' )

			"""
			Call the final callback user function if any 
			"""
			if post_callback_fn != None:
				post_callback_fn( self )
		except Mu256Exception as e:
			mu256log.critical( str( e ) )
			raise
		except:
			mu256log.critical( 'Unexpected error:', sys.exc_info()[0] )
			raise


	def post_callback_autotest( self, mu256 ):
		""" 
		end processing callback function for autotesting the Mu256 system 
		"""
		q_size = self.signal_q.qsize()
	
		if q_size== 0:
			raise Mu256Exception( 'Processing autotest: No received data !' )

		"""
		get queued signals from Mu256
		"""
		signal = []
		for _ in range( q_size ):
			signal = np.append( signal, self.signal_q.get( block=False ) )
		signal = signal.reshape( self.buffer_length * q_size, self.mems_number )

		"""
		compute mean energy
		"""
		mic_power = np.sum( signal**2, axis=0 )		

		"""
		print results
		"""
		print( '-'*20 )
		print( ' .counted', q_size, 'recorded data buffers' )
		print( ' .equivalent recording time is:', q_size * self.buffer_length / self.sampling_frequency, 's' )
		print( ' .detected', len( np.where( mic_power > 0 )[0] ), 'active MEMs:', np.where( mic_power > 0 )[0] )
		print( '-'*20 )

	def callback_power( self, mu256, data: np.ndarray ):
		""" 
		Compute energy (mean power) on transfered frame
		"""
		signal = data.reshape( mu256.buffer_length, mu256.mems_number )
		signal = np.float256( signal )/np.float256( 0x07FF )
		mean_power = np.sum( signal**2, axis=0 ) / mu256.buffer_length

		self.signal_q.put( mean_power )



def main():
	print( 'This is the main function of the module Mu256. Performs autotest' )
	mu256 = Mu256()
	mu256.run( 
		mems=[i for i in range(256)],
		post_callback_fn=mu256.post_callback_autotest,
	)


def __main__():
	main()


if __name__ == "__main__":
	main()



