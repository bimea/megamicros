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
"""

import os
from os import path
from pathlib import Path
from datetime import date, datetime
import numpy as np
import json
import wave

import torch
from torch.utils.data import TensorDataset

from megamicros.log import log
from megamicros.exception import MuException
from megamicros.aidb.query import AidbSession, MuDbException
from megamicros.core.base import DEFAULT_MEMS_SENSIBILITY

DATASET_DEFAULT_LOGIN       = 'ailab'
DATASET_DEFAULT_EMAIL       = 'bruno.gas@biimea.com'
DATASET_DEFAULT_PASSWD      = '#T;uZnQ5UJ_JC~&'
DATASET_CONFIG_NAME         = 'dataset.json'


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
    __labels: list
    __login: str
    __email: str
    __passwd: str
    __transform = None
    __target_transform = None
    __download: bool
    __channels: list|None                      

    __meta: dict                                # Dataset meta informations
    __labels_meta: list                         # Meta info about labels
    __samples_meta: list                        # Meta info about samples


    def __init__( self, root: str|Path, url: str, login: str=DATASET_DEFAULT_LOGIN, email:str=DATASET_DEFAULT_EMAIL, password: str=DATASET_DEFAULT_PASSWD, labels: str|int|list=None, channels: int|list=None, transform=None, target_transform=None, download=False ):
        """
        Get meta informations from the remote database. 
        If download is True, download all sammples from the database and save them in a local directory as wav files.
        Either samples and labels can be transformed by giving a `transform` and/or `target_transform` callback as argument.

        Parameters
        ----------
        root: str|Path
            Path to the directory where the dataset is found or downloaded.
        dbhost: str
            hostname or IP address
        login: str, optionnal
            database acces login
        email: str, optionnal
            database user email
        passwd: str, optionnal
            database password
        labels: str|int|list, optionnal
            label identifier or name or list of labels identifier or name
        channels: int|list
            channel number or list of channels to get
        transform: callable, optional
            Optional transform to be applied on a sample.
        download: bool
            Whether to download the dataset if it is not found at root path. (default: False).
        """

        # We do not work with pathlib. Path type is just for torch dataset compatibility
        if type( root ) == Path:
            self.__root = str( root )
        else:
            self.__root = root

        # Check if dataset directory exist and make it if not
        DATASET_CONFIG_PATH = self.__root
        DATASET_CONFIG_FILENAME = os.path.join( DATASET_CONFIG_PATH, "datasetAIDB.json")
        DATASET_NEW = False
        if not path.exists( DATASET_CONFIG_FILENAME ):
            log.info( f" .Create new dataset" )
            os.makedirs( DATASET_CONFIG_PATH, exist_ok=True )
            DATASET_NEW = True

        # Set object properties
        self.__dbhost = url
        self.__labels = labels
        self.__login = login
        self.__email = email
        self.__password = password
        self.__channels = channels if type( channels ) is list else [channels] if type( channels ) is int else None
        self.__transform = transform
        self.__target_transform = target_transform
        self.__download = False

        if self.__channels is None:
            log.warning( f" .No channel specified in arguments list. Set to channel 0" )
            self.__channels = [0]

        # Open database
        try:
            with AidbSession( dbhost=self.__dbhost, login=self.__login, email=self.__email, password=self.__password ) as session:

                if type( labels ) is str or type( labels ) is int:
                    labels = [labels]
                elif type( labels ) is tuple:
                    labels = list( labels )
                
                if type( labels ) is not list:
                    raise MuAilabException( f"Unknown labels argument. Type is not correct: {type(labels)} " )
                
                # Check label existance and convert to label database identifiers
                self.__labels_meta = []
                self.__samples_meta = []
                for label_class, label in enumerate( labels ):
                    try:
                        if type( label ) is int:
                            label_meta = session.get_meta( object='label', id=label )
                            label_id = label
                        else:
                            label_meta = session.get_meta( object='label', field={'label': 'code', 'value': label} )
                            label_id = label_meta['id']

                        self.__labels_meta.append( {
                            'class': label_class,
                            'id': label_id,
                            'code': label_meta['code'],
                            'name': label_meta['name'],
                            'channels': self.__channels,
                            'comment': label_meta['comment']
                        } )

                    except MuDbException as e:
                        raise MuAilabException( f"Label id [{label}] not found in database" )
                
                # get labellings meta data and compute start and stop samples index in file
                log.info( f" .Collecting labellings metadata ..." )
                
                for label_idx, label in enumerate( self.__labels_meta ):
                    label_id = label['id']
                    labellings = session.load_labelings( label_id=label_id )
                    for labelling in labellings:
                        
                        file_meta = session.get_sourcefile( labelling['sourcefile_id'] )
                        file_timestamp = file_meta['info']['timestamp']
                        timestamp_start = labelling['datetime_start']
                        timestamp_end = labelling['datetime_end']
                        sampling_frequency = file_meta['info']['sampling_frequency']

                        start_time = timestamp_start - file_timestamp
                        end_time = timestamp_end - file_timestamp
                        sample_start = int( start_time * sampling_frequency )
                        sample_end = int( end_time * sampling_frequency )

                        self.__samples_meta.append( {
                            'label_class': label['class'],
                            'label_id': label_id,
                            'file_id': labelling['sourcefile_id'],
                            'start': sample_start,
                            'end': sample_end,
                            'sr': sampling_frequency
                        } )

                    # Add the samples number
                    self.__labels_meta[label_idx]['count'] = len( labellings )

                if DATASET_NEW:
                    # No local base 
                    if download:
                        # Now that we have all metadata info, one can save them
                        self.__meta = {
                            'labels_meta': self.__labels_meta,
                            'samples_meta': self.__samples_meta,
                            'crdate': datetime.now().strftime("%d/%m/%Y %H:%M:%S") ,
                            'uddate': None
                        }

                        with open( DATASET_CONFIG_FILENAME, 'w', encoding='utf-8') as json_file:
                            json.dump( self.__meta, json_file, ensure_ascii=False, indent=4 )

                        self.__download = True
                        
                    else:
                        # no dowload means that data are nt saved -> nothing to do
                        pass

                else:
                    if download:
                        # Load the existing meta file
                        with open( DATASET_CONFIG_FILENAME, 'r') as json_file:
                            existing_meta = json.load( json_file )

                        # Compare metadata with existing meta file
                        is_same = True
                        if len( existing_meta['labels_meta'] ) != len( self.__labels_meta ):
                            # Mismatch on the number of labels
                            is_same = False
                        else:
                            # same number of labels -> check every one
                            for label_idx, label in enumerate( self.__labels_meta ):
                                existing_label = next( (element for element in existing_meta['labels_meta'] if element['id'] == label['id']), None )
                                if existing_label is None or existing_label['count'] != label['count'] or existing_label['channels'] != label['channels']:
                                    is_same = False
                                    break
                        
                        if not is_same:
                            # re-write the local basis
                            DATASET_NEW = True
                            self.__meta = {
                                'labels_meta': self.__labels_meta,
                                'samples_meta': self.__samples_meta,
                                'crdate': existing_meta['crdate'],
                                'uddate': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                            }
                            with open( DATASET_CONFIG_FILENAME, 'w', encoding='utf-8') as json_file:
                                json.dump( self.__meta, json_file, ensure_ascii=False, indent=4 )  

                        self.__download = True                      

                    else:
                        # User dont want to dowload data -> we do not use the existing meta file
                        pass
                
                # Get data if requested by user
                if DATASET_NEW and download:
                    log.info(  f" .Collecting data ..." )

                    if not path.exists( os.path.join( DATASET_CONFIG_PATH, 'wav' ) ):
                        log.info( f" .Create wav directory" )
                        os.makedirs( os.path.join( DATASET_CONFIG_PATH, 'wav' ), exist_ok=True )

                    samples_number = len( self.__samples_meta )
                    print( f"Downloading {samples_number} samples from database..." )
                    for sample_idx, sample in enumerate( self.__samples_meta ):
                        data = np.frombuffer(
                            session.get_samples_range( 
                                start = sample['start'],
                                stop =  sample['end'],
                                channels = self.__channels,
                                id = sample['file_id']
                            ), 
                            dtype=np.int32 
                        )

                        if ( sample_idx*100/samples_number )%10 == 0:
                            print( f"{int(sample_idx*100/samples_number)}%" )
                        SAMPLE_FILENAME = os.path.join( DATASET_CONFIG_PATH, 'wav', f"{sample_idx}-{sample['label_class']}.wav" )
                        
                        with  wave.open( SAMPLE_FILENAME, mode='wb' ) as wavfile:
                            wavfile.setnchannels( len(self.__channels) )
                            wavfile.setsampwidth( 2 )
                            wavfile.setframerate( sample['sr'] )

                            data = data >> 8
                            wavfile.writeframesraw( np.int16( np.reshape( data, np.size( data ) ) ) )

                    print( f"100%" )

        except MuException as e:
            raise MuAilabException( f"Connection to database {self.__dbhost} failed ({type(e).__name__}): {e}" )


    def __len__( self ):
        """ Get the total samples number in dataset"""

        return len(self.__samples_meta)
    

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

        if torch.is_tensor(idx):
            idx = idx.tolist()

        try:
            if self.__download:
                # Get data from local file
                SAMPLE_FILENAME = os.path.join( self.__root, 'wav', f"{idx}-{self.__samples_meta[idx]['label_class']}.wav" )
                with wave.open( SAMPLE_FILENAME ,'r' )  as wavefile:
                    channels_number = wavefile.getnchannels()
                    samples_number = wavefile.getnframes()
                    data = np.frombuffer(
                        wavefile.readframes( samples_number ),
                        dtype=np.int16
                    ).astype(np.float32) * DEFAULT_MEMS_SENSIBILITY

                # transform binary data to torch tensor and get properties and label
                frame_fength =  len( data ) // channels_number
                data = torch.from_numpy( np.reshape( data, ( frame_fength, channels_number ) ).T )
                sr = int( self.__samples_meta[idx]['sr'] )
                label = self.__samples_meta[idx]['label_class']

            else:
                # Get data from remote database
                with AidbSession( dbhost=self.__dbhost, login=self.__login, email=self.__email, password=self.__password ) as session:
                    idx = int(idx)
                    data = np.frombuffer(
                        session.get_samples_range( 
                            start = self.__samples_meta[idx]['start'],
                            stop =  self.__samples_meta[idx]['end'],
                            channels = self.__channels,
                            id = self.__samples_meta[idx]['file_id']
                        ), 
                        dtype=np.int32 
                    ).astype(np.float32) * DEFAULT_MEMS_SENSIBILITY

                # transform binary data to torch tensor and get properties and label
                channels_number = len( self.__channels )
                frame_fength =  len( data ) // channels_number
                data = torch.from_numpy( np.reshape( data, ( frame_fength, channels_number ) ).T )
                sr = int( self.__samples_meta[idx]['sr'] )
                label = self.__samples_meta[idx]['label_class']

            # Exec processing callback if any 
            if self.__transform:
                data = self.__transform( data )

            if self.__target_transform:
                label = self.__target_transform( label )
            

        except MuException as e:
            raise MuAilabException( f"Connection to database {self.__dbhost} failed ({type(e).__name__}): {e}" )

        return data, label, sr
