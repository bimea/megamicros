# megamicros.ailab.dataset.py base class for Aidb dataset
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


""" Provide the base class for getting datas as Pytorch dataset from Aidb database 

Documentation
-------------
MegaMicros documentation is available on https://readthedoc.biimea.io

See
---
https://www.assemblyai.com/blog/end-to-end-speech-recognition-pytorch/
https://pytorch.org/audio/stable/tutorials/audio_io_tutorial.html
"""

import os
from os import path
from pathlib import Path
from datetime import date, datetime
import numpy as np
import json
import wave

import torch
import torchaudio
from torch.utils.data import TensorDataset

from megamicros.log import log
from megamicros.exception import MuException
from megamicros.aidb.query import AidbSession, MuDbException
from megamicros.core.base import DEFAULT_MEMS_SENSIBILITY

DATASET_DEFAULT_LOGIN       = 'ailab'
DATASET_DEFAULT_EMAIL       = 'bruno.gas@biimea.com'
DATASET_DEFAULT_PASSWD      = '#T;uZnQ5UJ_JC~&'
DATASET_CONFIG_NAME         = 'dataset.json'
DATASET_CONFIG_NAME_SPLIT   = 'dataset-split.json'


# =============================================================================
# Exception dedicaced to Megamicros Ailab tools
# =============================================================================

class MuAilabException( MuException ):
    """Exception base class for Megamicros Aidb systems """


class AidbTimeStrechingTransform( torch.nn.Module ):
    """ Time streching transform for Aidb dataset
    Speed up in time without modifying pitch by a factor which is determined
    by the ratio of input frames to output frames.

    Parameters
    ----------
    factor: float
        Time streching factor
    """

    def __init__( self, factor: float, output_length: int ):
        super().__init__()
        self._factor = factor
        self._output_length = output_length

    def forward( self, data: torch.Tensor ) -> torch.Tensor:
        """ Apply time streching to the given data

        Parameters
        ----------
        data: torch.Tensor
            Data to transform
        factor: float
            Max or min value of streching factor
        output_length: int
            Length of the output data

        Returns
        -------
        torch.Tensor
            Transformed data
        """

        print( f" .data.shape: {data.shape}")
        print( f" .data.dim(): {data.dim()}")
        print( f" factor={self._factor}" )
        print( f" output_length={self._output_length}")

        if data.dim() != 3:
            raise MuAilabException( "Input of AidbTimeStrechingTransform must be a 2d tensor." )

        actual_length = data.shape[1]
        print( f" .actual_length: {actual_length}" )
        new_factor = self._output_length / actual_length
        return torchaudio.functional.phase_vocoder( data, rate=new_factor )


class AidbDataset( TensorDataset ):
    """ Aidb dataset 
    __init__() get meta informations from the remote database
    __getitem__() is overloaded to support the dataset indexing
    """

    __root: str
    __dbhost: str
    __dataset_name: str
    __login: str
    __email: str
    __password: str
    __transform = None
    __target_transform = None
    __channels: list|None     
    __split_size: float = None
    __zero_padding: bool = False           

    __dataset_meta: dict = None                     # Database dataset meta informations
    __dataset_meta_split: dict = None               # Database split dataset meta informations
    __meta: dict                                    # Dataset meta informations


    @property
    def sample_rate( self ) -> int:

        """ Get the sample rate of the dataset """
        return int( self.__dataset_meta['samples'][0]['sr'] ) if self.__split_size is None else int( self.__dataset_meta_split['samples'][0]['sr'] )

    @property
    def sample_frequency( self ) -> int:
        """ Get the sample frequency of the dataset """

        return self.sample_rate


    def __init__( self, 
        root: str|Path, 
        url: str, 
        dataset_name: str,
        login: str=DATASET_DEFAULT_LOGIN, 
        email:str=DATASET_DEFAULT_EMAIL, 
        password: str=DATASET_DEFAULT_PASSWD, 
        channels: int|list=None, 
        transform=None, 
        target_transform=None, 
        split_size: None|float=None,
        zero_padding: bool=False ):
        """
        Get meta informations from the remote dataset which name is `dataset_name`. 
        All sammples are downloaded from the database and saved in a local directory as wav files.
        Either samples and labels can be transformed by giving a `transform` and/or `target_transform` callback as argument.

        Note that the transforms specified in a dataset are applied every time an item is retrieved from the dataset, 
        which includes every batch during training. 
        This means that if you're using random data augmentation techniques during training,
        these transformations will be applied randomly and differently for each epoch of training.
        
        If `sample_duration` is given, samples are cut (and/or stretched wether the `time_stretching` argument is provided or not) to fit the given duration.
        In that case, samples that are more than several times longer than the requested duration are split.  
        A json index file is created which name is given by the `DATASET_CONFIG_NAME` constant

        Parameters
        ----------
        root: str|Path
            Path to the directory where the dataset is found or downloaded.
        dbhost: str
            hostname or IP address
        dataset_name: str
            name of dataset to download from database
        login: str, optionnal
            database acces login
        email: str, optionnal
            database user email
        passwd: str, optionnal
            database password
        channels: int|list
            channel number or list of channels to get
        transform: callable, optional
            Optional transform to be applied on a sample.
        split_size: float, optionnal
            gives the duration of samples to split in seconds. If None, all samples are left unchanged (default: None).
            Samples which duration is less than the split size are left unchanged. 
        zero_padding: bool, optionnal
            If True, samples which duration is less than the split size are zero padded. (default: False)
        """

        # We do not work with pathlib. Path type is just for torch dataset compatibility
        if type( root ) == Path:
            self.__root = str( root )
        else:
            self.__root = root

        # Set object properties
        self.__dbhost = url
        self.__dataset_name = dataset_name
        self.__login = login
        self.__email = email
        self.__password = password
        self.__channels = channels if type( channels ) is list else [channels] if type( channels ) is int else None
        self.__transform = transform
        self.__target_transform = target_transform

        if zero_padding and split_size is None:
            raise MuAilabException( f"Zero padding is not allowed if split size is not given" )

        self.__split_size = split_size
        self.__zero_padding = zero_padding

        if self.__channels is None:
            log.warning( f" .No channel specified in arguments list. Set to channel 0" )
            self.__channels = [0]

        # Get metadata from database
        self.__dataset_meta = self.download_metadata( dataset_name )

        # Get original dataset from database
        if self.__split_size is None:
            
            if self.check_dataset():
                log.info( f" .Dataset {dataset_name} is up to date" )
            else:
                log.info( f" .Dataset {dataset_name} is not up to date. Downloading..." )
                self.download_dataset( self.__dataset_meta )
        
        # Get dataset from database and split it
        else:
            if self.check_dataset():
                # There is already an up to date local original dataset that can be split
                log.info( f" .There is an original up do date dataset {dataset_name}" )
                if self.check_dataset_split_wav():
                    # There is already an up to date local split dataset -> nothing to do
                    log.info( f" .Split dataset {dataset_name} is up to date. Nothing do do." )
                else:
                    # Generate split dataset from local original dataset
                    log.info( f" .Generate split dataset from local original dataset..." )
                    # !!! WARNING !!!
                    # The split_from_local_dataset failed to generate the split dataset
                    # -> use download_dataset_and_split instead. Should be fixed
                    #self.split_from_local_dataset()
                    self.download_dataset_and_split()
            elif not self.check_dataset_split_wav():
                # There is no local dataset or it is not up to date
                log.info( f" .Split dataset {dataset_name} is not up to date. Downloading..." )
                self.download_dataset_and_split()
            else:
                # There is already an up to date local split dataset -> nothing to do
                pass


    def split_from_local_dataset( self ):
        """ Generate split dataset from local original dataset """

        # Create split directory if not exist
        if not path.exists( os.path.join( self.__root, 'split', 'wav' ) ):
            log.info( f" .Create split/wav directory" )
            os.makedirs( os.path.join( self.__root, 'split', 'wav' ), exist_ok=True )

        # Delete all files in split/wav directory if any
        else:
            for file in os.listdir( os.path.join( self.__root, 'split', 'wav' ) ):
                os.remove( os.path.join( self.__root, 'split', 'wav', file ) )

        # Build the split samples meta data
        split_samples = self.build_split_samples( self.__dataset_meta )

        # Save the split samples meta data
        log.info( f" .Save new split meta file" )
        self.__dataset_meta_split = {
            'samples': split_samples,
            'split_size': self.__split_size,
            'zero_padding': self.__zero_padding,
            'crdate': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
        json_split_filename = os.path.join( self.__root, 'split', DATASET_CONFIG_NAME_SPLIT )
        with open( json_split_filename, 'w', encoding='utf-8') as json_file:
            json.dump( self.__dataset_meta_split, json_file, ensure_ascii=False, indent=4 )

        # Get data from local repository and split them according to the split meta data
        percent = 0
        percent_before = 0
        samples_number = len( self.__dataset_meta_split['samples'])
        if self.__zero_padding:
            sampling_frequency = self.__dataset_meta['samples'][0]['sr']
            samples_witdh = int( self.__split_size * sampling_frequency )


        for sample_idx, sample in enumerate( self.__dataset_meta_split['samples'] ):
            # Get data from local repository
            ORIGINAL_SAMPLE_FILENAME = os.path.join( self.__root, 'wav', f"{sample_idx}-{sample['label_id']}.wav" )

            # Read wavfile
            with wave.open( ORIGINAL_SAMPLE_FILENAME, mode='rb' ) as wavfile:
                data = np.frombuffer( 
                    wavfile.readframes( wavfile.getnframes() ), 
                    dtype=np.int16
                )
                data = np.reshape( data, ( wavfile.getnframes(), wavfile.getnchannels() ) )
                data = data[sample['start']:sample['stop'],:]    

            # Perform zero padding if requested
            if self.__zero_padding:
                if np.shape( data )[0] < samples_witdh:
                    data = data + np.ndarray( (samples_witdh - np.shape( data )[0], wavfile.getnchannels() ), dtype=np.int16 )           

            data = data.flatten()

            # Save data as wav file in 16 bits integer format
            SAMPLE_FILENAME = os.path.join( self.__root, 'split', 'wav', f"{sample_idx}-{sample['labeling_id']}-{sample['label_id']}.wav" )

            # Save wav file
            with  wave.open( SAMPLE_FILENAME, mode='wb' ) as wavfile:
                wavfile.setnchannels( len( self.__channels ) )
                wavfile.setsampwidth( 2 )
                wavfile.setframerate( int( sample['sr'] ) )
                wavfile.writeframesraw( data )

            # Print counter
            percent_before = percent
            percent = sample_idx*100//samples_number
            if percent%20 == 0 or percent%20 < percent_before%20 :
                print( f"{percent}%" )



    def build_split_samples( self, dataset_meta: dict ) -> list:
        """ Build the samples index list

        Parameters
        ----------
        dataset_meta: dict
            The original dataset meta data
        """

        # Build the split samples meta data
        split_samples = []
        for sample in dataset_meta['samples']:
            sample_start = sample['start']
            sample_end = sample['end']
            sr = int( sample['sr'] )
            sample_duration = ( sample_end - sample_start ) / sr
            if int( sample_duration/self.__split_size ) > 0:

                # Sample is longer than requested duration -> split it
                split_number = int( sample_duration/self.__split_size )
                for splitnumber in range( split_number ):
                    split_start = int( sample_start + splitnumber * self.__split_size * sr )
                    split_end = int( split_start + self.__split_size * sr - 1)
                    split_samples.append( {
                        'labeling_id': sample['labeling_id'],
                        'label_id': sample['label_id'],
                        'file_id': sample['sourcefile_id'],
                        'start': split_start,
                        'end': split_end,
                        'sr': sr
                    } )

                # Add remainder signal if its size is greater than half of the requested duration
                if sample_duration - split_number * self.__split_size > self.__split_size/2:
                    split_start = int( sample_start + split_number * self.__split_size * sr )
                    split_end = int( sample_end )
                    split_samples.append( {
                        'labeling_id': sample['labeling_id'],
                        'label_id': sample['label_id'],
                        'file_id': sample['sourcefile_id'],
                        'start': split_start,
                        'end': split_end,
                        'sr': sr
                    } )

            # Sample is shorter than requested duration -> keep it if its size is greater than half of the requested duration
            elif sample_duration > self.__split_size/2: 
                split_samples.append( {
                    'labeling_id': sample['labeling_id'],
                    'label_id': sample['label_id'],
                    'file_id': sample['sourcefile_id'],
                    'start': sample_start,
                    'end': sample_end,
                    'sr': sr
                } )

            # Sample is too short -> do not keep it
            else:
                pass

        return split_samples


    def download_dataset_and_split( self ):
        """ Get data from database and save them as wav files in the dataset directory after split and zero padding if requested """

        # Create split directory if not exist
        if not path.exists( os.path.join( self.__root, 'split', 'wav' ) ):
            log.info( f" .Create split/wav directory" )
            os.makedirs( os.path.join( self.__root, 'split', 'wav' ), exist_ok=True )

        # Delete all files in split/wav directory if any
        else:
            for file in os.listdir( os.path.join( self.__root, 'split', 'wav' ) ):
                os.remove( os.path.join( self.__root, 'split', 'wav', file ) )
                        
        # Build the split samples meta data
        split_samples = self.build_split_samples( self.__dataset_meta )

        # Save the split samples meta data
        log.info( f" .Save new split meta file" )
        self.__dataset_meta_split = {
            'samples': split_samples,
            'split_size': self.__split_size,
            'zero_padding': self.__zero_padding,
            'crdate': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
        json_split_filename = os.path.join( self.__root, 'split', DATASET_CONFIG_NAME_SPLIT )
        with open( json_split_filename, 'w', encoding='utf-8') as json_file:
            json.dump( self.__dataset_meta_split, json_file, ensure_ascii=False, indent=4 )
                
        # Get data from database and split them according to the split meta data
        percent = 0
        percent_before = 0
        samples_number = len( self.__dataset_meta_split['samples'])
        if self.__zero_padding:
            sampling_frequency = self.__dataset_meta['samples'][0]['sr']
            samples_witdh = int( self.__split_size * sampling_frequency )

        with AidbSession( dbhost=self.__dbhost, login=self.__login, email=self.__email, password=self.__password ) as session:

            for sample_idx, sample in enumerate( self.__dataset_meta_split['samples'] ):
                data = np.frombuffer(
                    session.get_samples_range( 
                        start = sample['start'],
                        stop =  sample['end'],
                        channels = self.__channels,
                        id = sample['file_id']
                    ), 
                    dtype=np.int32 
                )

                # Save data as wav file in 16 bits integer format
                SAMPLE_FILENAME = os.path.join( self.__root, 'split', 'wav', f"{sample_idx}-{sample['labeling_id']}-{sample['label_id']}.wav" )
                data = np.int16( data >> 8 )

                # Perform zero padding if requested
                if self.__zero_padding:
                    if len( data ) < samples_witdh:
                        data = np.pad( data, (0, samples_witdh - len( data )), 'constant' )

                # Save wav file
                with  wave.open( SAMPLE_FILENAME, mode='wb' ) as wavfile:
                    wavfile.setnchannels( len( self.__channels ) )
                    wavfile.setsampwidth( 2 )
                    wavfile.setframerate( int( sample['sr'] ) )
                    wavfile.writeframesraw( data )

                # Print counter
                percent_before = percent
                percent = sample_idx*100//samples_number
                if percent%20 == 0 or percent%20 < percent_before%20 :
                    print( f"{percent}%" )


    def download_dataset( self, dataset_meta: dict ):
        """ Get data from database and save them as wav files in the dataset directory 
        
        Parameter
        ---------
        dataset_meta: dict
            The original dataset meta data
        """

        # Create dataset directory if needed
        if not path.exists( self.__root ):
            log.info( f" .Create new dataset path" )
            os.makedirs( self.__root, exist_ok=True )

        # Save metadata json file
        config_filename = os.path.join( self.__root, DATASET_CONFIG_NAME )
        with open( config_filename, 'w', encoding='utf-8') as json_file:
            json.dump( dataset_meta, json_file, ensure_ascii=False, indent=4 )            

        # Delete existing wav files if any
        if path.exists( os.path.join( self.__root, 'wav' ) ):
            log.info( f" .Remove existing wav files" )
            for file in os.listdir( os.path.join( self.__root, 'wav' ) ):
                os.remove( os.path.join( self.__root, 'wav', file ) )
        else:
            log.info( f" .Create wav directory" )
            os.makedirs( os.path.join( self.__root, 'wav' ), exist_ok=True )           

        # Download samples and save them as wav files
        with AidbSession( dbhost=self.__dbhost, login=self.__login, email=self.__email, password=self.__password ) as session:
            for sample_idx, sample in enumerate( self.__dataset_meta['samples'] ):
                data = np.frombuffer(
                    session.get_samples_range( 
                        start = sample['start'],
                        stop =  sample['end'],
                        channels = self.__channels,
                        id = sample['sourcefile_id']
                    ), 
                    dtype=np.int32 
                )

                # Save data as wav file in 16 bits integer format
                SAMPLE_FILENAME = os.path.join( self.__root, 'wav', f"{sample_idx}-{sample['label_id']}.wav" )
                data = np.int16( data >> 8 )
                with wave.open( SAMPLE_FILENAME, mode='wb' ) as wavfile:
                    wavfile.setnchannels( len( self.__channels ) )
                    wavfile.setsampwidth( 2 )
                    wavfile.setframerate( int( sample['sr'] ) )
                    wavfile.writeframesraw( data )


    def download_metadata( self, dataset_name ):
        """ Get metadata from the remote dataset which name is `dataset_name` 
        
        Parameters
        ----------
        dataset_name: str
            name of dataset to download from database
        """

        try:
            with AidbSession( dbhost=self.__dbhost, login=self.__login, email=self.__email, password=self.__password ) as session:
                dataset_meta = session.get_dataset( name=dataset_name )
        except MuException as e:
            raise MuAilabException( f"Connection to database {self.__dbhost} failed ({type(e).__name__}): {e}" )
        
        return dataset_meta


    def check_dataset_split_wav( self ) -> bool:
        """ Check if local split dataset wav files are up to date
        Notice that this method does not check the wav file themselves but only their number and their size

        Return
        ------
        bool
            True if local dataset is up to date, False otherwise
        """ 

        # Check split directory existance
        if not path.exists( os.path.join( self.__root, 'split', 'wav' ) ):
            return False
        
        # Check split json config file existance
        json_split_filename = os.path.join( self.__root, 'split', DATASET_CONFIG_NAME_SPLIT )
        if not path.exists( json_split_filename ):
            return False

        # Get existing split dataset meta file
        try:
            with open( json_split_filename, 'r') as json_file:
                existing_split_meta = json.load( json_file )

        except json.decoder.JSONDecodeError as e:
            log.info( f"Existing split dataset meta file {json_split_filename} seems not valid. Downloading split dataset..." )
            return False
        except Exception as e:
            log.info( f"Failed to open local split json metafile {json_split_filename}. Downloading split dataset..." )
            return False
        
        if existing_split_meta['split_size'] != self.__split_size or existing_split_meta['zero_padding'] != self.__zero_padding:
            return False

        return True



    def check_dataset( self ) -> bool :
        """ Check if local dataset is up to date 
        Just compare the dataset meta file with the one in database
        
        Return
        ------
        bool
            True if local dataset is up to date, False otherwise
        """

        # Check if dataset directory exist
        if not path.exists( self.__root ):
            return False

        # Check json config file existance
        config_filename = os.path.join( self.__root, DATASET_CONFIG_NAME )
        if not path.exists( config_filename ):
            return False

        if self.__dataset_meta is None:
            return False
        
        # Get existing dataset meta file
        try:
            with open( config_filename, 'r') as json_file:
                existing_meta = json.load( json_file )
        except json.decoder.JSONDecodeError as e:
            log.info( f"Existing dataset meta file {config_filename} seems not valid. Downloading dataset..." )
            return False
        except Exception as e:
            log.info( f"Failed to open local json metafile {config_filename}. Downloading dataset..." )
            return False
        
        # Check if existing meta file is the same as the one in database
        if not 'dataset' in existing_meta or not 'crdate' in existing_meta:
            log.info( f" .Existing dataset meta file {config_filename} is not valid. Downloading dataset..." )
            return False
        
        if existing_meta['crdate'] != self.__dataset_meta['crdate']:
            log.info( f" .Existing dataset meta file {config_filename} is not up to date. Downloading dataset..." )
            return False
        
        return True



    def __len__( self ):
        """ Get the total samples number in dataset"""

        if self.__split_size is not None:
            return len(self.__dataset_meta_split['samples'])
        else:   
            return len(self.__dataset_meta['samples'])

    

    def __getitem__( self, idx ):
        """ get sample which index is given as argument 
        
        Return
        ------
        data: torch.Tensor
            Tensor built from a numpy array which dimensions are (samples_number, channels_number)
        sample rate: int 
            Data sampling frequency
        label: int
            The label identifier in database (for now)
        """

        if torch.is_tensor( idx ):
            idx = idx.tolist()

        try:
            # Get data from split directory
            if self.__split_size is not None:
                SAMPLE_FILENAME = os.path.join( self.__root, 'split', 'wav', f"{idx}-{self.__dataset_meta_split['samples'][idx]['labeling_id']}-{self.__dataset_meta_split['samples'][idx]['label_id']}.wav" )
                with wave.open( SAMPLE_FILENAME ,'r' )  as wavefile:                
                    channels_number = wavefile.getnchannels()
                    samples_number = wavefile.getnframes()
                    data = np.frombuffer(
                        wavefile.readframes( samples_number ),
                        dtype=np.int16
                    ).astype(np.float32) * DEFAULT_MEMS_SENSIBILITY

                label = self.__dataset_meta_split['samples'][idx]['label_id']

            # Get data from wav directory
            else:
        
                SAMPLE_FILENAME = os.path.join( self.__root, 'wav', f"{idx}-{self.__dataset_meta['samples'][idx]['label_id']}.wav" )
                with wave.open( SAMPLE_FILENAME ,'r' )  as wavefile:
                    channels_number = wavefile.getnchannels()
                    samples_number = wavefile.getnframes()
                    data = np.frombuffer(
                        wavefile.readframes( samples_number ),
                        dtype=np.int16
                    ).astype(np.float32) * DEFAULT_MEMS_SENSIBILITY

                label = self.__dataset_meta['samples'][idx]['label_id']

            # transform binary data to torch tensor and reshape it
            frame_fength = len( data ) // channels_number
            data = torch.from_numpy( np.reshape( data, ( frame_fength, channels_number ) ).T )

            # Exec processing callback if any 
            if self.__transform:
                data = self.__transform( data )

            if self.__target_transform:
                label = self.__target_transform( label )
            

        except MuException as e:
            raise MuAilabException( f"Connection to database {self.__dbhost} failed ({type(e).__name__}): {e}" )

        return data, label





"""

        try:
            with AidbSession( dbhost=self.__dbhost, login=self.__login, email=self.__email, password=self.__password ) as session:
                
                # Get dataset metafile
                dataset_meta = session.get_dataset( name=self.__dataset_name )
                should_be_downloaded = False

                # Check if dataset directory exist and make it if not and then save dataset meta file
                config_filename = os.path.join( self.__root, DATASET_CONFIG_NAME )
                if not path.exists( self.__root ):
                    log.info( f" .Create new dataset" )
                    os.makedirs( self.__root, exist_ok=True )

                    # Save dataset meta file
                    with open( config_filename, 'w', encoding='utf-8') as json_file:
                        json.dump( dataset_meta, json_file, ensure_ascii=False, indent=4 )
                    
                    self.__meta =  dataset_meta
                    should_be_downloaded = True

                # Dataset directory exist -> check json config file existance
                else:
                    if not path.exists( config_filename ):
                        log.info( f" .Create new dataset" )
                        self.__meta =  dataset_meta
                        should_be_downloaded = True
                    
                    else:
                        # Get existing dataset meta file
                        with open( config_filename, 'r') as json_file:
                            try:
                                existing_meta = json.load( json_file )
                        
                                # Check if existing meta file is the same as the one in database
                                if not 'dataset' in existing_meta or not 'crdate' in existing_meta:
                                    log.info( f" .Existing dataset meta file {config_filename} is not valid. Downloading dataset..." )
                                    should_be_downloaded = True
                                elif existing_meta['crdate'] != dataset_meta['crdate']:
                                    log.info( f" .Existing dataset meta file {config_filename} is not up to date. Downloading dataset..." )
                                    should_be_downloaded = True

                            except json.decoder.JSONDecodeError as e:
                                log.info( f" .Existing dataset meta file {config_filename} is not valid. Downloading dataset..." )
                                should_be_downloaded = True

                    if should_be_downloaded:
                        # Save dataset meta file
                        log.info( f" .Save new dataset meta file" )
                        with open( config_filename, 'w', encoding='utf-8') as json_file:
                            json.dump( dataset_meta, json_file, ensure_ascii=False, indent=4 )

                        self.__meta =  dataset_meta

                    else:
                        # Should not be downloaded -> use existing meta data
                        self.__meta =  existing_meta

                        # Check for channels. 
                        # If user as changed channels list, we have to download dataset
                        # This check is performed by looking at the first wav file which can be in wav directory or in split/wav directory
                        if self.__split_size is None:
                            wavpath = os.path.join( self.__root, 'wav' )
                        elif path.exists( os.path.join( self.__root, 'split' ) ):
                            wavpath = os.path.join( self.__root, 'split', 'wav' )
                        else:
                            wavpath = os.path.join( self.__root, 'wav' )

                        first_vawfile = next( (f for f in os.listdir( wavpath ) if f.endswith('.wav')), None )
                        if first_vawfile is None:
                            # No wav file in directory -> download dataset
                            log.info( f" .No wav file in directory {wavpath}. Downloading dataset..." )
                            should_be_downloaded = True
                        else:
                            # Get first wav file in directory and check channels number
                            try:
                                with wave.open( os.path.join( wavpath, first_vawfile ) ,'r' )  as wavefile:
                                    channels_number = wavefile.getnchannels()

                                if channels_number != len( self.__channels ):
                                    # Channels number mismatch -> download dataset
                                    log.info( f" .Channels number mismatch in directory {wavpath}. Downloading dataset..." )
                                    should_be_downloaded = True   

                            except wave.Error as e:
                                # File is not a wav file -> download dataset
                                log.info( f" .File {os.path.join( wavpath, first_vawfile )} is not a vaild wav file. Downloading dataset..." )
                                should_be_downloaded = True                    

                            
                # Download dataset if needed
                if should_be_downloaded:

                    # Delete existing wav files
                    if path.exists( os.path.join( self.__root, 'wav' ) ):
                        for file in os.listdir( os.path.join( self.__root, 'wav' ) ):
                            os.remove( os.path.join( self.__root, 'wav', file ) )

                    # Download dataset
                    log.info(  f" .Collecting data ..." )

                    if not path.exists( os.path.join( self.__root, 'wav' ) ):
                        log.info( f" .Create wav directory" )
                        os.makedirs( os.path.join( self.__root, 'wav' ), exist_ok=True )

                    # Get samples with split and zero padding if requested
                    if self.__split_size is not None:
                        self.split_data( session )

                    # Get samples without any split or zero padding
                    else:
                        for sample_idx, sample in enumerate( self.__meta['samples'] ):
                            data = np.frombuffer(
                                session.get_samples_range( 
                                    start = sample['start'],
                                    stop =  sample['end'],
                                    channels = self.__channels,
                                    id = sample['sourcefile_id']
                                ), 
                                dtype=np.int32 
                            )

                            # Save data as wav file in 16 bits integer format
                            SAMPLE_FILENAME = os.path.join( self.__root, 'wav', f"{sample_idx}-{sample['label_id']}.wav" )
                            data = np.int16( data >> 8 )
                            with  wave.open( SAMPLE_FILENAME, mode='wb' ) as wavfile:
                                wavfile.setnchannels( len( self.__channels ) )
                                wavfile.setsampwidth( 2 )
                                wavfile.setframerate( int( sample['sr'] ) )
                                wavfile.writeframesraw( data )
                else:
                    # Dataset is already downloaded -> nothing to do
                    log.info( f" .Dataset already downloaded and up to date" )
                    
                    # Check for dataset split
                    should_be_split = False
                    if self.__split_size is not None:
                        # Check if split directory exist and make it if not
                        if not path.exists( os.path.join( self.__root, 'split', 'wav' ) ):
                            should_be_split = True 
                        elif not path.exists( os.path.join( self.__root, 'split', DATASET_CONFIG_NAME_SPLIT ) ):
                            should_be_split = True
                        else:
                            # Check if split size is the same
                            with open( os.path.join( self.__root, 'split', DATASET_CONFIG_NAME_SPLIT ), 'r') as json_file:
                                try:
                                    existing_split_meta = json.load( json_file )
                                    if existing_split_meta['split_size'] != self.__split_size or existing_split_meta['zero_padding'] != self.__zero_padding:
                                        should_be_split = True
                                    else:
                                        # Should not be split -> use existing split meta data
                                        self.__meta['split'] = existing_split_meta

                                except json.decoder.JSONDecodeError as e:
                                    should_be_split = True

                    # Make the split dataset if needed 
                    if should_be_split:
                        log.info( f" .Create/update split dataset" )
                        self.split_data( session )

        except MuException as e:
            raise MuAilabException( f"Connection to database {self.__dbhost} failed ({type(e).__name__}): {e}" )



"""