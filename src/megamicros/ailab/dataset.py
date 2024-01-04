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
import shutil 
from pathlib import Path
from datetime import date, datetime
import numpy as np
import json
import wave
import random

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
DATASET_GZIP_NAME           = 'dataset.zip'    


# =============================================================================
# Exception dedicaced to Megamicros Ailab tools
# =============================================================================

class MuAilabException( MuException ):
    """Exception base class for Megamicros Aidb systems """


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
    __current_index: int = 0                        # Dataset initial index value for iteration


    @property
    def sample_rate( self ) -> int:

        """ Get the sample rate of the dataset """
        return int( self.__dataset_meta['samples'][0]['sr'] )

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
        
        If `split_size` is given, samples are split into samples or `split_size` seconds. 
        In addition, if `zero_padding` is provided, remainder samples whose duration is greater than half of the requested duration are zero padded.
        Samples whose duration is less than the split size are lost. 
        This ensure that all samples have same size.
        
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
            Optional transform to be applied on samples.
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
            log.warning( f" .No channel specified in arguments list. Set to channel one" )
            self.__channels = [1]

        # Load metadata from database
        self.__dataset_meta = self.download_metadata( dataset_name )

        # Compare with local backup if any
        if self.check_dataset():
            log.info( f" .Dataset {dataset_name} is up to date" )
        else:
            log.info( f" .Dataset {dataset_name} is not up to date. Downloading..." )

            # Remove all local data files
            self.cleanup_local_repos()

            # Save new metadata json file
            self.save_metadata()

            # Download data  and save them as gzip file
            self.download_data( dataset_name )

            # Unpack gzip file
            self.unpack_data()

        # At this stage we have a local gzip file containing all samples and a local json file containing the dataset meta informations
        # We also have a `wav` directory with all uncompressed wav files 
        # All is up to date. We can now prepare the split, learn and test tables if needed

        # Build the split data table
        if self.__split_size is not None:
            self.build_split_table()

        # Start iteration index
        self.__current_index = 0


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

        # Check wav path existance
        if not os.path.exists( os.path.join( self.__root, 'wav' ) ):
            return False

        # Check if dataset meta file has been downloaded from remote database
        if self.__dataset_meta is None:
            return False

        # Count wav files in wav directory
        wav_count = len( [f for f in os.listdir( os.path.join( self.__root, 'wav' ) ) if f.endswith('.wav')] )
        if wav_count != len( self.__dataset_meta['samples'] ):
            log.info( f" .Wav files are already there but dataset is not complete. Should rebuilded" )
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
    

    def download_metadata( self, dataset_name ):
        """ Get metadata from the remote dataset which name is `dataset_name` 
        
        Parameters
        ----------
        dataset_name: str
            name of dataset to download from database
        """

        try:
            with AidbSession( dbhost=self.__dbhost, login=self.__login, email=self.__email, password=self.__password ) as session:
                dataset_meta = session.get_dataset_metadata( name=dataset_name )
        except MuException as e:
            raise MuAilabException( f"Connection to database {self.__dbhost} failed ({type(e).__name__}): {e}" )
        
        return dataset_meta


    def cleanup_local_repos( self ):
        """ Delete local dataset if any """
            
        # Delete local dataset
        if path.exists( self.__root ):
            log.info( f" .Remove local dataset {self.__dataset_name}" )

            try:
                shutil.rmtree( self.__root )
                log.info( f" .Directory removed successfully" )
            except FileNotFoundError:
                print("Directory does not exist")
                raise MuAilabException( f"Directory does not exist" )
            except PermissionError:
                print("Permission denied")
                raise MuAilabException( f"Permission denied" )
            except Exception as e:
                print(f"An error occurred: {str(e)}")


    def save_metadata( self ):
        """ Save dataset metadata in local json file """

        # Create dataset directory if needed
        if not path.exists( self.__root ):
            log.info( f" .Create new dataset local directory" )
            os.makedirs( self.__root, exist_ok=True )

        # Save metadata json file
        config_filename = os.path.join( self.__root, DATASET_CONFIG_NAME )
        with open( config_filename, 'w', encoding='utf-8') as json_file:
            json.dump( self.__dataset_meta, json_file, ensure_ascii=False, indent=4 )

        log.info( f" .Successfully saved dataset metadata in {config_filename}" )


    def download_data( self, dataset_name ):
        """ Get data instance of the remote dataset which name is `dataset_name` 
        
        Parameters
        ----------
        dataset_name: str
            name of dataset to download from database
        return: bytes
            gzip compressed data
        """

        try:
            with AidbSession( dbhost=self.__dbhost, login=self.__login, email=self.__email, password=self.__password ) as session:
                gzip_data = session.download_dataset( name=dataset_name )
        except MuException as e:
            raise MuAilabException( f"Connection to database {self.__dbhost} failed ({type(e).__name__}): {e}" )

        # Create dataset directory if needed
        if not path.exists( self.__root ):
            log.info( f" .Create new dataset path" )
            os.makedirs( self.__root, exist_ok=True )

        # Save data gzip file
        gzip_filename = os.path.join( self.__root, DATASET_GZIP_NAME )
        with open( gzip_filename, 'bw' ) as gzip_file:
            gzip_file.write( gzip_data )


    def unpack_data( self ):
        """ Uncompress data from gzip file supposing gzip file is in the dataset directory

        If wav directory already exists with the good number of files, nothing is done
        """

        # Check if wav files are alredady there
        if os.path.exists( os.path.join( self.__root, 'wav' ) ):
            # Count wav files in dataset ditrectory
            wav_count = len( [f for f in os.listdir( os.path.join( self.__root, 'wav' ) ) if f.endswith('.wav')] )
            if wav_count == len( self.__dataset_meta['samples'] ):
                log.info( f" .Wav files are already there. Dataset successfully built" )
                return
            else:
                log.info( f" .Wav files are already there but dataset is not complete. Rebuilding dataset..." )
                shutil.rmtree( os.path.join( self.__root, 'wav' ) )

        # Build or rebuild dataset
        else:
            # Create wav directory if not exist
            if not os.path.exists( os.path.join( self.__root, 'wav' ) ):
                log.info( f" .Create wav directory" )
                os.makedirs( os.path.join( self.__root, 'wav' ), exist_ok=True )

            # Uncompress data
            log.info( f" .Uncompress data" )
            gzip_filename = os.path.join( self.__root, DATASET_GZIP_NAME )
            shutil.unpack_archive( gzip_filename,  os.path.join( self.__root, 'wav' ) )


    def build_split_table( self ):
        """ Build the split table from the dataset metadata

        The table is a new index of samples with their labels and their duration.
        A sliding factor (margin) is added such has to allow window moving inside the given interval 
        """

        subsamples = []
        for sample_idx, sample in enumerate( self.__dataset_meta['samples'] ):
            
            # sample size
            sample_size = sample['end'] - sample['start'] + 1
            subsample_size = int( self.__split_size * sample['sr'] )
            subsamples_count = sample_size//subsample_size

            # Add sub samples to the split table
            if subsamples_count > 0:
                for subsample_idx in range( subsamples_count ):
                    subsamples.append( {
                        'labeling_id': sample['labeling_id'],
                        'label_id': sample['label_id'],
                        'sample_idx': sample_idx,
                        'range': subsample_idx,
                        'size': subsample_size,
                        'margin': sample_size % subsample_size
                    } ) 

            # If sample size is less than split size, add it to the split table with a negative margin
            else:
                subsamples.append( {
                    'labeling_id': sample['labeling_id'],
                    'label_id': sample['label_id'],
                    'sample_idx': sample_idx,
                    'range': 0,
                    'size': sample_size,
                    'margin': -1
                } ) 

        self.__dataset_meta_split = {
            'samples': subsamples,
            'count': len( subsamples ),
            'size': subsample_size
        }


    def __len__( self ):
        """ Get the total samples number in dataset """

        if self.__split_size is None:
            return len( self.__dataset_meta['samples'] )
        else:   
            return len( self.__dataset_meta_split['samples'] )


    def __iter__(self):
        """ Get iterator on dataset """

        return self
    

    def __getitem__( self, idx ):
        """ get sample which index is given as argument 
        
        Return
        ------
        data: torch.Tensor
            Tensor built from a numpy array which dimensions are (samples_number, channels_number)
        sample rate: int 
            Sample sampling frequency
        label: int
            The label identifier in database (for now)
        """

        if torch.is_tensor( idx ):
            idx = idx.tolist()

        try:
            # Get data from original dataset            
            if self.__split_size is None:
                if idx >= len( self.__dataset_meta['samples'] ):
                    raise MuAilabException( f"Sample index {idx} out of range (0 to {len( self.__dataset_meta['samples'])-1 })" )

                label = self.__dataset_meta['samples'][idx]['label_class']
                filename = os.path.join( self.__root, 'wav', f"{idx}-{label}.wav" )
                with wave.open( filename ,'r' )  as wavefile:
                    channels_number = wavefile.getnchannels()
                    samples_number = wavefile.getnframes()
                    data = np.frombuffer(
                        wavefile.readframes( samples_number ),
                        dtype=np.int16
                    ).astype(np.float32) * DEFAULT_MEMS_SENSIBILITY

            # Get data from split dataset
            else:
                if idx >= len( self.__dataset_meta_split['samples'] ):
                    raise MuAilabException( f"Sample index {idx} out of range (0 to {len( self.__dataset_meta_split['samples'])-1 })" )

                # Get sample filename in original dataset
                sample_idx = self.__dataset_meta_split['samples'][idx]['sample_idx']
                label = self.__dataset_meta['samples'][sample_idx]['label_class']
                filename = os.path.join( self.__root, 'wav', f"{sample_idx}-{label}.wav" )
                
                # Set the start subsample index
                start = self.__dataset_meta_split['samples'][idx]['range'] * self.__dataset_meta_split['samples'][idx]['size']
                
                # Sample size is less than the split size -> zero padding
                if self.__dataset_meta_split['samples'][idx]['margin'] == -1:
                    delta = self.__dataset_meta_split['size'] - self.__dataset_meta_split['samples'][idx]['size']
                    
                    with wave.open( filename ,'r' )  as wavefile:
                        channels_number = wavefile.getnchannels()
                        samples_number = wavefile.getnframes()
                        data = np.frombuffer(
                            wavefile.readframes( samples_number ),
                            dtype=np.int16
                        ).astype(np.float32) * DEFAULT_MEMS_SENSIBILITY
                        data = np.concatenate( (data, np.zeros( delta ) ) )
                        samples_number += delta

                else:
                    # Add random margin if margin is available
                    if self.__dataset_meta_split['samples'][idx]['margin'] > 0:
                        margin = random.randint( 0, self.__dataset_meta_split['samples'][idx]['margin'] )
                        start += margin

                    # Load subsample
                    with wave.open( filename ,'r' )  as wavefile:
                        channels_number = wavefile.getnchannels()
                        samples_number = self.__dataset_meta_split['size']
                        wavefile.setpos( start )
                        data = np.frombuffer(
                            wavefile.readframes( samples_number ),
                            dtype=np.int16
                        ).astype(np.float32) * DEFAULT_MEMS_SENSIBILITY

            # transform binary data to torch tensor and reshape it
            data = torch.from_numpy( np.reshape( data, ( samples_number, channels_number ) ).T )

            # Exec processing callback if any 
            if self.__transform:
                data = self.__transform( data )

            if self.__target_transform:
                label = self.__target_transform( label )

        except Exception as e:
            raise MuAilabException( f"Unable to extract sample from dataset: {e}" )

        return data, label


    def __next__( self ):
        """ Get next sample in dataset or raise a StopIteration exception if end of dataset is reached """

        if self.__split_size is None:
            if self.__current_index >= len( self.__dataset_meta['samples'] ):
                raise StopIteration
        elif self.__current_index >= len( self.__dataset_meta_split['samples'] ):
                raise StopIteration

        result = self.__getitem__( self.__current_index )
        self.__current_index += 1

        return result