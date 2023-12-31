# megamicros_aidb/apps/aidb/core/serializers.py
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
Megamicros AIDB serializers

MegaMicros documentation is available on https://readthedoc.biimea.io
"""



from array import array
import os
from os import listdir, path as ospath
import io
import wave
import ffmpeg
import uuid
import json
import ast
import shutil
import numpy as np
from contextlib import nullcontext
from datetime import datetime, timedelta
from pytz import timezone
from pathlib import Path
import h5py
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.db import models
from rest_framework import serializers
from rest_framework.response import Response
from .models import Config, Domain, Campaign, Device, Directory, Tagcat, Tag, SourceFile, Context, FileContexting, Label, FileLabeling, Dataset
from .sp import compute_q50_from_file, compute_energy_from_file, compute_energy_from_wavfile, extract_range_from_wavfile, compute_energy_from_muh5file, genwav_from_range_wavfile, genwav_from_range_muh5file
from .sp import extract_range_from_muh5file, extract_samples_from_muh5file, extract_samples_from_wavfile
from .sp import compress_dataset
from .sp import save_context_on_muh5_file, update_context_on_muh5_file, save_label_on_muh5_file, update_label_on_muh5_file, save_dataset_on_muh5_file, remove_dataset_muh5_file
from megamicros.log import log
from megamicros.aidb.exception import MuDbException

"""
Django Rest Framework ManyToMany through, see: https://bitbucket.org/snippets/adautoserpa/MeLa/django-rest-framework-manytomany-through
"""


"""
Some additional validators for serializers
"""
class PathValidator:
    def __init__( self, max_length=256, fieldname='path' ):
        self.fieldname = fieldname
        self.max_length = max_length

    def __call__( self, fields ):
        if len( fields[self.fieldname] ) > self.max_length:
            message = f"Path {fields[self.fieldname]} is too long. Please check"
            raise serializers.ValidationError( message )

        if ospath.exists( fields[self.fieldname] ) == False:
            message = f"Path <{fields[self.fieldname]}> does not exist. Please check path existance"
            raise serializers.ValidationError( message )

"""
Base serializer classes
"""
class ConfigSerializer( serializers.ModelSerializer ):
    uddate = serializers.DateTimeField( read_only=True )

    class Meta:
        model = Config
        fields = ['id', 'url', 'host', 'dataset_path', 'active', 'comment', 'crdate', 'uddate']
        validators = [PathValidator( fieldname='dataset_path' )]
    
    def create(self, validated_data):
        if validated_data['active'] == True:
            """
            Deactivate any other config
            """
            Config.objects.filter( active=True ).update( active=False )

        log.info( f" .Successfully created new config" )
        return Config.objects.create( **validated_data )

    def update( self, instance: Config, validated_data ):

        instance.host = validated_data.get( 'host', instance.host )
        instance.dataset_path = validated_data.get( 'dataset_path', instance.dataset_path )
        instance.active = validated_data.get( 'active', instance.active )
        instance.comment = validated_data.get( 'comment', instance.comment )
        instance.uddate = datetime.now()

        if instance.active == True:
            """
            Deactivate any other config
            """
            Config.objects.filter( active=True ).update( active=False )

        instance.save()
        log.info( f" .Successfully updated config" )

        return instance


class TagcatSerializer( serializers.ModelSerializer ):
    tags = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='tag-detail' )

    class Meta:
        model = Tagcat
        fields = ['id', 'url', 'name', 'comment', 'crdate', 'tags']

class TagSerializer( serializers.ModelSerializer ):
    contexts = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='context-detail' )
    labels = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='label-detail' )
    filelabelings = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='filelabeling-detail' )

    class Meta:
        model = Tag
        fields = ['id', 'url', 'name', 'tagcat', 'comment', 'contexts', 'labels', 'filelabelings', 'crdate']

class DomainSerializer( serializers.HyperlinkedModelSerializer ):
    campaigns = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='campaign-detail' )
    contexts = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='context-detail' )
    labels = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='label-detail' )
    datasets = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='dataset-detail' )

    class Meta:
        model = Domain
        fields = ['id', 'url', 'name', 'comment', 'info', 'crdate', 'campaigns', 'contexts', 'labels', 'datasets']

class CampaignSerializer( serializers.HyperlinkedModelSerializer ):
    directories = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='directory-detail' )

    class Meta:
        model = Campaign
        fields = ['id', 'url', 'domain', 'name', 'date', 'comment', 'info', 'crdate', 'directories']

class DeviceSerializer( serializers.HyperlinkedModelSerializer ):
    directories = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='directory-detail' )

    class Meta:
        model = Device
        fields = ['id', 'url', 'name', 'type', 'identifier', 'comment', 'info', 'crdate', 'directories']

class DirectorySerializer( serializers.HyperlinkedModelSerializer ):
    class Meta:
        model = Directory
        fields = ['id', 'url', 'name', 'path', 'campaign', 'device', 'comment', 'info', 'crdate']
        validators = [PathValidator()]

class DirectoryFileSerializer( serializers.HyperlinkedModelSerializer ):
    files = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='sourcefile-detail' )

    class Meta:
        model = Directory
        fields = ['id', 'url', 'name', 'path', 'campaign', 'device', 'files', 'comment', 'info', 'crdate']
        validators = [PathValidator()]

class ContextSerializer( serializers.HyperlinkedModelSerializer ):
    class Meta:
        model = Context
        fields = ['id', 'url', 'parent', 'children', 'domain', 'name', 'code', 'type', 'comment', 'info', 'tags', 'crdate']

    def get_fields( self ):
        """ because of self-reference we have to define ourself the children field """ 
        fields = super( ContextSerializer, self).get_fields()
        fields['children'] = ContextSerializer( many=True, read_only=True )
        return fields

class LabelSerializer( serializers.HyperlinkedModelSerializer ):
    class Meta:
        model = Label
        fields = ['id', 'url', 'parent', 'children', 'domain', 'name', 'code', 'comment', 'info', 'tags', 'crdate']

    def get_fields( self ):
        """ because of self-reference we have to define ourself the children field """ 
        fields = super( LabelSerializer, self).get_fields()
        fields['children'] = LabelSerializer( many=True, read_only=True )
        return fields

class SourceFileSerializer( serializers.HyperlinkedModelSerializer ):
    contexts = ContextSerializer( many=True, read_only=True,  )
    labels = LabelSerializer( many=True, read_only=True,  )
    
    class Meta:
        model = SourceFile
        fields = ['id', 'url', 'filename', 'type', 'datetime', 'duration', 'directory', 'size', 'integrity', 'contexts', 'labels', 'tags', 'comment', 'info', 'crdate']

class FileContextingSerializer( serializers.HyperlinkedModelSerializer):
    code = serializers.HiddenField( default='' )
    sourcefile_id = serializers.ReadOnlyField( source='sourcefile.id' )
    sourcefile_filename = serializers.ReadOnlyField( source='sourcefile.filename' )
    context_id = serializers.ReadOnlyField( source='context.id' )
    context_name = serializers.ReadOnlyField( source='context.name' )
    context_code = serializers.ReadOnlyField( source='context.code' )
    context_type = serializers.ReadOnlyField( source='context.type' )
    context_start = serializers.ReadOnlyField( source='context.datetime_start' )
    context_end = serializers.ReadOnlyField( source='context.datetime_end' )

    class Meta:
        model = FileContexting
        fields = ['id', 'url', 'sourcefile', 'context', 'datetime_start', 'datetime_end', 'code', 'comment', 'info', 'sourcefile_id', 'sourcefile_filename', 'context_id', 'context_name', 'context_code', 'context_type', 'context_start', 'context_end']

    """
    validation
    """
    def validate( self, data ):
        if data['datetime_start'] >= data['datetime_end']:
            raise serializers.ValidationError("Context should start before finishing")
        
        """
        Generate the uniqueless code
        """
        if data['code'] == '':
            """
            Generate an uuid code only if we are in create mode
            """
            data['code'] = str( uuid.uuid1() )

        return data


    def create(self, validated_data):

        """
        Save context on file
        """
        sourcefile: SourceFile = validated_data['sourcefile']
        directory: Directory = sourcefile.directory
        context: Context = validated_data['context']
        segment_code = uuid.UUID( validated_data['code'] ).fields
        log.info( f' .Generated segment code is {segment_code}' )

        """ We abandon storing labels and contexts on original source file """
        #save_context_on_muh5_file( 
        #    directory.path + '/' + sourcefile.filename, 
        #    context.code, 
        #    segment_code, 
        #    validated_data['datetime_start'], 
        #    validated_data['datetime_end']
        #)

        return FileContexting.objects.create( **validated_data )


    def update(self, instance: FileContexting, validated_data):
        """
        Can update following fields (but not sourcefile, nor contexting code)
        """
        instance.context = validated_data.get( 'context', instance.context )
        instance.comment = validated_data.get( 'comment', instance.comment )
        instance.info = validated_data.get( 'info', instance.info )
        instance.datetime_start = validated_data.get( 'datetime_start', instance.datetime_start )
        instance.datetime_end = validated_data.get( 'datetime_end', instance.datetime_end )

        """ We renounce to update origin files when labeling """
        #update_context_on_muh5_file( 
        #    instance.sourcefile.directory.path + '/' + instance.sourcefile.filename,
        #    instance.context.code,
        #    list( uuid.UUID( instance.code ).fields ),
        #    instance.datetime_start,
        #    instance.datetime_end
        #)

        instance.save()
        log.info( f" .Successfully updated segment {instance.code}" )

        return instance


class FileLabelingSerializer( serializers.HyperlinkedModelSerializer  ):
    code = serializers.HiddenField( default='' )
    sourcefile_id = serializers.ReadOnlyField( source='sourcefile.id' )
    sourcefile_filename = serializers.ReadOnlyField( source='sourcefile.filename' )
    label_id = serializers.ReadOnlyField( source='label.id' )
    label_name = serializers.ReadOnlyField( source='label.name' )
    label_code = serializers.ReadOnlyField( source='label.code' )

    class Meta:
        model = FileLabeling
        fields = ['id', 'url', 'sourcefile', 'label', 'contexts', 'tags', 'datetime_start', 'datetime_end', 'code', 'comment', 'info', 'crdate', 'sourcefile_id', 'sourcefile_filename', 'label_id', 'label_name', 'label_code']

    """
    validation
    """
    def validate( self, data ):
        """ 
        Validate data if they are provided. 
        Note that with the [PATCH] request, some data may not be provided 
        """
        log.info( ' .Validating file labelling with data: ' + str( data ) )
        if 'datetime_start' in data and 'datetime_end' in data:
            if data['datetime_start'] >= data['datetime_end']:
                log.info( ' .Label should start before finishing' )
                raise serializers.ValidationError("Label should start before finishing")

        """
        Generate the uniqueless code
        """
        if 'code' in data and data['code'] == '':
            """
            Generate an uuid code only if we are in create mode, that is if code is submitted and empty
            """
            data['code'] = str( uuid.uuid1() )

        return data



"""
Processing seralizer classes
"""
class SourceDirectoryCheckSerializer:    
    """
    Check directory existance and return content info 
    """
    def __init__( self, dir: Directory, context=None ):
        try:
            h5 = []
            muh5 = []
            wav = []
            mp4 = []
            other = []
            content = listdir( dir.path )
            for filename in content:
                ext = Path( filename ).suffix
                if ext == '.h5':
                    """
                    check for muh5 file
                    """
                    try:
                        with h5py.File( dir.path + '/' + filename, 'r' ) as muh5_file:
                            if not muh5_file['muh5']:
                                h5.append( filename)
                            else:
                                muh5.append( filename)
                    except Exception as e:
                        continue

                elif ext == '.wav':
                    wav.append( filename)
                elif ext == '.mp4':
                    mp4.append( filename)
                else:
                    other.append( filename )

            self.data = { 
                'status': 'ok',
                'path': dir.path,
                #'device': dir.device,
                'number': {
                    'h5': len( h5 ), 'muh5': len( muh5 ), 'wav': len( wav ), 'mp4': len( mp4 ), 'other': len( other ),
                    'total': len( h5 ) + len( muh5 ) + len( wav ) + len( mp4 ) + len( other )
                },
                'content': {
                    'h5' : h5, 'muh5': muh5, 'wav': wav, 'mp4': mp4, 'other': other
                }
            }

        except Exception as e:
            self.data = { 'status': 'error', 'message': str( e ) }


class SourceDirectoryReviseSerializer:
    """
    Update directory by recording content in database.
    Records file name are supposed following the 'xxx-YYYmmdd-hhmmss.ext' format with local time set to Europe/Paris:
        datetime = pytz.timezone( 'Europe/Paris' ).localize( datetime.strptime(s, '%Y%m%d %H%M%S') )
    More general way could be to considere filenames coded as UTC. We would have then to replace UTC time zone by the local time zone:
        from datetime import datetime, timezone
        datetime_utc = datetime.strptime(s, '%Y%m%d %H%M%S').replace( tzinfo=timezone.utc )
        datetime = datetime_utc.astimezone( pytz.timezone( 'Europe/Paris' ) )
    """
    ERROR_ALREADY_EXIST = 1
    ERROR_NOT_MUH5 = 2
    ERROR_NOT_H5 = 3
    ERROR_OPEN = 4
    ERROR_MODEL_CREATE = 5
    ERROR_NOT_WAV = 6
    ERROR_NOT_MP4 = 7
    ERROR_NOT_IMPLEMENTED = 8

    def __init__( self, dir: Directory, context=None ):
        try:
            response = []
            files = listdir( dir.path )
            for file in files:
                filename = dir.path + '/' + file
                if SourceFile.objects.filter( directory=dir, filename=file ).exists():
                    """
                    file already in database
                    """
                    response.append( {'filename': file, 'status': 'error', 'code': self.ERROR_ALREADY_EXIST, 'message': f"file {file} already exists in db"} )
                else:
                    try:
                        ext = Path( file ).suffix
                        if ext == '.h5':
                            with h5py.File( filename, 'r' ) as h5_file:
                                if not h5_file['muh5']:
                                    """
                                    this is an ordinary H5 file
                                    """
                                    dt = ospath.splitext( file )[0].split( '-' )
                                    if len( dt ) != 3:
                                        """
                                        Seems that filename has not the type-date-time.h5 form -> set initial unix time
                                        Beware that using info['ctime'] may lead to errors since this date can be the last copy date for example
                                        """
                                        dt = datetime.fromtimestamp( 0 )
                                    else:                            
                                        dt = timezone( 'UTC' ).localize( datetime.strptime( dt[1] + ' ' + dt[2], '%Y%m%d %H%M%S') )
                                        dt = dt + timedelta( milliseconds=0 )

                                    """
                                    create and save File object in database
                                    """
                                    try:
                                        h5_object = SourceFile(
                                            filename = file,
                                            type = SourceFile.H5,
                                            datetime = dt,
                                            duration = int( 0 ),                                # unknown duration
                                            size = 0,                                          # unknown size
                                            integrity = True,
                                            directory = dir,
                                            info = {
                                                'ctime': datetime.fromtimestamp( ospath.getctime( filename ) ).strftime( '%Y-%m-%d %H:%M:%S.%f' ),
                                                'mtime': datetime.fromtimestamp( ospath.getmtime( filename) ).strftime( '%Y-%m-%d %H:%M:%S.%f' ),
                                                'size': ospath.getsize( filename )
                                            }                           
                                        )
                                        h5_object.save()

                                    except Exception as e:
                                        response.append( {'filename': file, 'status': 'error', 'code': self.ERROR_MODEL_CREATE, 'message': f"Unable to create db model from file {file}: {e}"} )
                                        continue

                                    response.append( {'filename': file, 'status': 'ok'} )
                                
                                else:
                                    """
                                    this is a MUH5 file
                                    """         
                                    group = h5_file['muh5']
                                    info = dict( zip( group.attrs.keys(), group.attrs.values() ) )
                                    try:
                                        """
                                        get datetime from file internal parameter 'date'
                                        """
                                        try:
                                            dt = timezone( 'UTC' ).localize( datetime.strptime( info['date'], '%Y-%m-%d %H:%M:%S.%f') )        
                                        except Exception as e:
                                            # try to confirm validity without the microseconds field
                                            dt = timezone( 'UTC' ).localize( datetime.strptime( info['date'], '%Y-%m-%d %H:%M:%S') )

                                            # check if there are microseconds in the file timestamp
                                            timestamp = float( info['timestamp'] )
                                            dt_corrected = datetime.fromtimestamp( timestamp )

                                            # fix datetime if possible
                                            if dt_corrected.microsecond != 0:
                                                dt = datetime( dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt_corrected.microsecond )
                                            
                                            # fix date with the good format (whatever the previous fix):
                                            info['date'] = dt.strftime( '%Y-%m-%d %H:%M:%S.%f' )

                                        """
                                        create and save File object in database
                                        """
                                        h5_object = SourceFile( 
                                            filename = file,
                                            type = SourceFile.MUH5,
                                            datetime = dt,
                                            duration = int( info['duration'] ),
                                            size = ospath.getsize( filename ),                            
                                            integrity = True,
                                            directory = dir,
                                            info = {
                                                'ctime': datetime.fromtimestamp( ospath.getctime( filename ) ).strftime( '%Y-%m-%d %H:%M:%S.%f' ),
                                                'mtime': datetime.fromtimestamp( ospath.getmtime( filename ) ).strftime( '%Y-%m-%d %H:%M:%S.%f' ),
                                                'size': ospath.getsize( filename ),
                                                'sampling_frequency': float( info['sampling_frequency'] ),
                                                'timestamp': float( info['timestamp'] ),
                                                'duration': float( info['duration'] ),
                                                'date': info['date'],
                                                'channels_number': int( info['channels_number'] ),          # int64 is not JSON serializable
                                                'analogs_number': int( info['analogs_number'] ),            # idem...
                                                'mems_number': int( info['mems_number'] ),
                                                'dataset_number': int( info['dataset_number'] ),
                                                'dataset_duration': int( info['dataset_duration'] ),
                                                'dataset_length': int( info['dataset_length'] ),
                                                'compression': int( info['compression'] ),                  # bool_ is not JSON serializable
                                                'counter': int( info['counter'] ),                          # bool_ is not JSON serializable
                                                'counter_skip': int( info['counter_skip'] ),                # bool_ is not JSON serializable
                                                'analogs': info['analogs'].tolist(),                        # array is not JSON serializable
                                                'mems': info['mems'].tolist()                               # idem...
                                            }
                                        )
                                        h5_object.save()
                                    except Exception as e:
                                        response.append( {'filename': file, 'status': 'error', 'code': self.ERROR_MODEL_CREATE, 'message': f"Unable to create db model from file {file}: {e}"} )
                                        continue

                                    response.append( {'filename': file, 'status': 'ok'} )                            

                        elif ext == '.wav':
                            with wave.open( filename, 'r' ) as wav_file:
                                """
                                get datetime from filename
                                """
                                dt = ospath.splitext( file )[0].split( '-' )
                                if len( dt ) != 3:
                                    """
                                    Seems that filename has not the type-date-time.wav form -> set initial unix time
                                    Beware that using info['ctime'] may lead to errors since this date may be the last copy date for example
                                    """
                                    dt = datetime.fromtimestamp( 0 )
                                else:                            
                                    dt = timezone( 'UTC' ).localize( datetime.strptime( dt[1] + ' ' + dt[2], '%Y%m%d %H%M%S') )
                                    dt = dt + timedelta( milliseconds=0 )

                                info = {
                                    'ctime': datetime.fromtimestamp( ospath.getctime( filename ) ).strftime( '%Y-%m-%d %H:%M:%S.%f' ),
                                    'mtime': datetime.fromtimestamp( ospath.getmtime( filename) ).strftime( '%Y-%m-%d %H:%M:%S.%f' ),
                                    'size': ospath.getsize( filename ),
                                    'sampling_frequency': float( wav_file.getframerate() ),
                                    'samples_number': wav_file.getnframes(),                                    # samples number
                                    'channels_number': wav_file.getnchannels(),                                 # channels number
                                    'compression': 0 if wav_file.getcomptype() == 'NONE' else 1,                # compressed or not
                                    'compression_type': wav_file.getcomptype(),                                 # compression algo
                                    'compression_name': wav_file.getcompname(),                                 # human readable compression type
                                    'sample_width': wav_file.getsampwidth(),                                    # sample width in bytes
                                    'duration': float( wav_file.getnframes()/float( wav_file.getframerate() ) )
                                }

                                """
                                create and save File object in database
                                """
                                try:
                                    wav_object = SourceFile(
                                        filename = file,
                                        type = SourceFile.WAV,
                                        datetime = dt,
                                        duration = int( info['samples_number']//info['sampling_frequency'] ),           # duration in seconds
                                        size = ospath.getsize( filename ),          
                                        integrity = True,
                                        directory = dir,
                                        info = info                            
                                    )
                                    wav_object.save()
                                except Exception as e:
                                    response.append( {'filename': file, 'status': 'error', 'code': self.ERROR_MODEL_CREATE, 'message': f"Unable to create db model from file {file}: {e}"} )
                                    continue
                                
                                response.append( {'filename': file, 'status': 'ok'} )

                        elif ext == '.mp4':
                            info = ffmpeg.probe( filename, cmd='ffprobe' )

                            dt = ospath.splitext( file )[0].split( '-' )
                            if len( dt ) != 3:
                                """
                                Seems that filename has not the type-date-time.mp4 form -> set initial unix time
                                Beware that using info['ctime'] may lead to errors since this date may be the last copy date for example
                                """
                                dt = datetime.fromtimestamp( 0 )
                            else:
                                #dt = timezone( 'Europe/Paris' ).localize( datetime.strptime( dt[1] + ' ' + dt[2], '%Y%m%d %H%M%S') )                            
                                dt = timezone( 'UTC' ).localize( datetime.strptime( dt[1] + ' ' + dt[2] + '.0', '%Y%m%d %H%M%S.%f') )   
                                dt = dt + timedelta( milliseconds=0 )                         

                            """
                            create and save File object in database
                            """
                            try:
                                mp4_object = SourceFile(
                                    filename = file,
                                    type = SourceFile.MP4,
                                    datetime = dt,
                                    duration = int( float( info['format']['duration'] ) ),                      # duration in seconds
                                    size = ospath.getsize( filename ),
                                    integrity = True,
                                    directory = dir,
                                    info = {
                                        'ctime': datetime.fromtimestamp( ospath.getctime( filename ) ).strftime( '%Y-%m-%d %H:%M:%S.%f' ),
                                        'mtime': datetime.fromtimestamp( ospath.getmtime( filename) ).strftime( '%Y-%m-%d %H:%M:%S.%f' ),
                                        'size': ospath.getsize( filename ),
                                        'frame_rate': info['streams'][0]['r_frame_rate'],
                                        'time_base': info['streams'][0]['time_base'],
                                        'nb_frames': int( info['streams'][0]['nb_frames'] ),
                                        'duration': float( info['format']['duration'] ),
                                        'width': info['streams'][0]['width'],
                                        'height': info['streams'][0]['height'],
                                        'format': info['format']
                                    }                     
                                )
                                mp4_object.save()

                            except Exception as e:
                                response.append( {'filename': file, 'status': 'error', 'code': self.ERROR_MODEL_CREATE, 'message': f"Unable to create db model from file {file}: {e}"} )
                                continue

                            response.append( {'filename': file, 'status': 'ok'} )

                        else:
                            response.append( {'filename': file, 'status': 'error', 'code': self.ERROR_NOT_IMPLEMENTED, 'message': f"Unknown or not implemented file type <{ext}>"} )

                    except Exception as e:
                        response.append( {'filename': file, 'status': 'error', 'code': self.ERROR_OPEN, 'message': f"file {file} opening failed: {e}"} )

            self.data = { 'status': 'ok', 'response': response }

        except Exception as e:
            self.data = { 'status': 'error', 'message': str( e )}



class SourceFileUploadSerializer:
    """
    Check file existance and upload it 
    """

    ERROR_UNCHECKED = 1
    ERROR_SYSTEM = 2

    def __init__( self, file: SourceFile, context=None ):
        if file.integrity == None:
            """
            This should never occure...
            """
            self.data = { 'status': 'error', 'code': self.ERROR_UNCHECKED,  'message': 'Unchecked file' }

        try:
            filename = Directory.objects.get( pk=file.directory.id ).path + '/' + file.filename
            with open( filename, 'rb') as file_to_upload:
                if file.type == file.H5:
                    self.data = HttpResponse( file_to_upload, content_type='application/x-hdf5' )
                elif file.type == file.MUH5:
                    self.data = HttpResponse( file_to_upload, content_type='application/x-hdf5' )
                elif file.type == file.WAV:
                    self.data = HttpResponse( file_to_upload, content_type='audio/x-wav' )
                elif file.type == file.MP4:
                    self.data = HttpResponse( file_to_upload, content_type='video/mp4' )
                else:
                    raise Exception( f"Unknown file format/type: {file.type}" )
                self.data['Content-Disposition'] = f"attachment; filename={file.filename}"

        except Exception as e:
            raise e


class SourceFileSegmentationSerializer:
    """
    Perform segmentation on files
    """

    DEFAULT_FRAME_DURATION = 100
    DEFAULT_CHANNEL_NUMBER = 1
    
    def __init__( self, file: SourceFile, request, algorithm ):

        try:
            """ check query parameters """
            frame_duration = request.query_params.get('frame_duration')
            frame_duration = self.DEFAULT_FRAME_DURATION if frame_duration is None else int( frame_duration )

            channel_id = request.query_params.get('channel_id')
            channel_id = self.DEFAULT_CHANNEL_NUMBER if channel_id is None else int( channel_id )

            """ get file path """
            filename = Directory.objects.get( pk=file.directory.id ).path + '/' + file.filename

            sampling_frequency = file.info['sampling_frequency'] 
            frame_width = int( frame_duration*sampling_frequency/1000 )
            
            if algorithm == 'energy':
                data = compute_energy_from_file( filename, file.type, channel_id=channel_id, frame_duration=frame_duration, power=False, norm=False )
            elif  algorithm == 'power':
                data = compute_energy_from_file( filename, file.type, channel_id=channel_id, frame_duration=frame_duration, power=True, norm=False )
            elif algorithm == 'q50':
                data = compute_q50_from_file( filename, file.type, channel_id=channel_id, frame_duration=frame_duration, norm = False )
            else:
                raise Exception( f"Unknown segmentation algorithm [{algorithm}]" )

            segmentation = {
                'filename': file.filename,
                'filetype': file.WAV,
                'algo': algorithm,
                'sampling_frequency': sampling_frequency,
                'frame_duration': frame_duration,
                'frame_width': frame_width,
                'channel_id': channel_id,
                'data_length': len( data ),
                'max_value': np.amax( data ),
                'min_value': np.amin( data ),
                'data': data
            }
            self.data = Response( segmentation ) 

        except Exception as e:
            raise e 



class SourceFileUploadEnergySerializer:
    """
    Check file existance and compute energy on the given channel 
    """

    ERROR_UNCHECKED = 1
    ERROR_SYSTEM = 2

    def __init__( self, file: SourceFile, channel_id=None, context=None, frame_width=None ):
        if file.integrity == None or file.integrity == False:
            """
            This should never occure...
            """
            self.data = { 'status': 'error', 'code': self.ERROR_UNCHECKED,  'message': 'Unchked file or file integrity problem' }
            return

        try:
            if channel_id is None:
                channel_id = 0

            filename = Directory.objects.get( pk=file.directory.id ).path + '/' + file.filename
            if file.type == file.WAV:
                energy = compute_energy_from_wavfile( filename, channel_id=channel_id, frame_width=frame_width )
                self.data = HttpResponse( energy.tobytes(), headers={
                    'Content-Type': 'application/octet-stream',
                    'Content-Disposition': f"attachment; filename=energy-{Path( file.filename).stem}.data",
                })
            elif file.type == file.MUH5:
                energy = compute_energy_from_muh5file( filename, channel_id=channel_id, frame_width=frame_width )
                self.data = HttpResponse( energy.tobytes(), headers={
                    'Content-Type': 'application/octet-stream',
                    'Content-Disposition': f"attachment; filename=energy-{Path( file.filename).stem}.data",
                })                
            else:
                raise Exception( f"Energy computing on format/type: {file.type} not implemented" )

            #self.data['Content-Disposition'] = f"attachment; filename=energy-{Path( file.filename).stem}.data"

        except Exception as e:
            raise e


class SourceFileUploadRangeSerializer:

    ERROR_UNCHECKED = 1
    ERROR_SYSTEM = 2

    def __init__( self, file: SourceFile, start: float, stop: float, left: int, right: int, context=None, request=None ):
        if file.integrity == None or file.integrity == False :
            """
            This should never occure...
            """
            self.data = { 'status': 'error', 'code': self.ERROR_UNCHECKED,  'message': 'Uncheked file or file integrity problem' }

        try:
            filename = Directory.objects.get( pk=file.directory.id ).path + '/' + file.filename
            if file.type == file.WAV:
                signal = extract_range_from_wavfile( filename, start, stop )
                self.data = HttpResponse( signal.tobytes(), headers={
                    'Content-Type': 'application/octet-stream',
                    'Content-Disposition': f"attachment; filename=range-{Path( file.filename).stem}.data",
                })
            elif file.type == file.MUH5:
                if request is None:
                    # use the mems given as url parameters, left and right 
                    mems = (left, right)
                else:
                    # when passed as query parameters, channels overwrites the usual url parameters  
                    mems = request.query_params.get('channels')
                    if mems is None:
                        mems = (left, right)
                    else:
                        # the form of query param should be: ?channels=1,2,3,4
                        mems = ast.literal_eval( f"({mems})" )

                signal = extract_range_from_muh5file( filename, start, stop, channels=mems )
                self.data = HttpResponse( signal.tobytes(), headers={
                    'Content-Type': 'application/octet-stream',
                    'Content-Disposition': f"attachment; filename=range-{Path( file.filename).stem}.data",
                })                
            else:
                raise Exception( f"Range extraction on format/type: {file.type} not implemented" )            
        except Exception as e:
            raise e

class SourceFileUploadSamplesSerializer:
    """ Get range of samples from MuH5 files """

    ERROR_UNCHECKED = 1
    ERROR_SYSTEM = 2

    def __init__( self, file: SourceFile, start: int, stop: int, left: int, right: int, context=None, request=None ):
        if file.integrity == None or file.integrity == False :
            """
            This should never occure...
            """
            self.data = { 'status': 'error', 'code': self.ERROR_UNCHECKED,  'message': 'Uncheked file or file integrity problem' }

        try:
            filename = Directory.objects.get( pk=file.directory.id ).path + '/' + file.filename
            if file.type == file.WAV:
                signal = extract_samples_from_wavfile( filename, start, stop )
                self.data = HttpResponse( signal.tobytes(), headers={
                    'Content-Type': 'application/octet-stream',
                    'Content-Disposition': f"attachment; filename=samples-{Path( file.filename).stem}.data",
                })
            elif file.type == file.MUH5:
                if request is None:
                    # use the mems given as url parameters, left and right 
                    mems = (left, right)
                else:
                    # when passed as query parameters, channels overwrites the usual url parameters  
                    mems = request.query_params.get('channels')
                    if mems is None:
                        mems = (left, right)
                    else:
                        # the form of query param should be: ?channels=1,2,3,4
                        mems = ast.literal_eval( f"({mems})" )

                # Get data in their original type (np.int32)
                signal = extract_samples_from_muh5file( filename, start, stop, channels=mems, dtype=np.int32 )
                self.data = HttpResponse( signal.tobytes(), headers={
                    'Content-Type': 'application/octet-stream',
                    'Content-Disposition': f"attachment; filename=samples-{Path( file.filename).stem}.data",
                })                
            else:
                raise Exception( f"Samples exctraction on format/type: {file.type} not implemented" )            
        except Exception as e:
            raise e


class SourceFileUploadAudioSerializer:

    ERROR_UNCHECKED = 1
    ERROR_SYSTEM = 2

    def __init__( self, file: SourceFile, start: float, stop: float, left: int, right: int, context=None ):
        """
        Audio file downloader serializer

        Parameters
        ===========
        * left (int): left channel number (mems)
        * right (int): right channel number (mems)
        * label_name (str): label name if the audio segment is labelized

        """
        if file.integrity == None or file.integrity == False :
            """
            This should never occure...
            """
            self.data = { 'status': 'error', 'code': self.ERROR_UNCHECKED,  'message': 'Uncheked file or file integrity problem' }

        try:
            filename = Directory.objects.get( pk=file.directory.id ).path + '/' + file.filename
            if file.type == file.WAV:
                signal = genwav_from_range_wavfile( filename, start, stop )
                self.data = HttpResponse( signal, headers={
                    'Content-Type': 'audio/wav',
                    'Content-Disposition': f"attachment; filename=range-{Path( file.filename).stem}.data",
                })
            elif file.type == file.MUH5:
                mems = (left, right)
                signal = genwav_from_range_muh5file( filename, start, stop, channels=mems )
                self.data = HttpResponse( signal, headers={
                    'Content-Type': 'audio/wav',
                    'Content-Disposition': f"attachment; filename={Path( file.filename).stem}-{str(left)}-{str(right)}.data",
                })                
            else:
                raise Exception( f"Energy computing on format/type: {file.type} not implemented" )

        except Exception as e:
            raise e


class DatasetSerializer( serializers.HyperlinkedModelSerializer ):
    """ Dataset serializer """

    info = serializers.JSONField( initial=dict )
    filename = serializers.CharField( read_only=True )
    filelabelings  = serializers.HyperlinkedRelatedField( many=True, read_only=True, view_name='filelabeling-detail' )
    
    class Meta:
        model = Dataset
        fields = ['id', 'url', 'name', 'code', 'domain', 'labels', 'contexts', 'filelabelings', 'filename', 'tags', 'comment', 'info', 'crdate' ]

    def validate( self, data ):
        """ Overload the default validate method """

        log.info( f" .Validating dataset with data: {data}" )
        
        # Datasets cannot have same code (in creating mode)
        # Note that this is not a problem in updating mode since the code is not a field to be updated
        if self.instance is None:
            # we are in creating mode

            data['code'] = data['code'].replace( ' ', '-' )
            # If the same code is used for another dataset, throw an exception
            if Dataset.objects.filter( code=data['code'] ).exists():

                # get this dataset and throw an exception
                dataset = Dataset.objects.get( code=data['code'] )
                raise serializers.ValidationError( f"A dataset '{dataset.name}' with same code '{data['code']}' already exists" )

            # Check if the dataset info is not empty
            if 'info' in data:
                # Check if the info contains the required fields
                if 'channels' not in data['info']:
                    raise serializers.ValidationError( f"Missing `channels` field in `info` field" )
                if data['info']['channels'] is None or data['info']['channels'] == '':
                    raise serializers.ValidationError( f"Empty `channels` field in `info` field" )
                if type(data['info']['channels']) is not tuple and type(data['info']['channels']) is not list and type(data['info']['channels']) is not int:
                    raise serializers.ValidationError( f"Invalid `channels` field in `info` field: should be a list or an integer" )
                if type(data['info']['channels']) is int:
                    data['info']['channels'] = [data['info']['channels']]

                channels = data['info']['channels']
                log.info( f" .Found dataset info field: {data['info']}" )
                
                # Check channels number
                if len( channels ) < 1:
                    raise serializers.ValidationError( f"Invalid json `info['channels']` field: should contain at least one channel" )

                if len( channels ) > 2:
                    raise serializers.ValidationError( f"Invalid json `info['channels']` field: should contain at most two channels (more channels not yet available)" )

        return data


    def create(self, validated_data):
        """ populate the filelabelings field """

        log.info( f" .Note that label detection is limited to MUH5 files" )

        # Get filelabelings. Only labels are taken into account and only MUH5 files
        filelabelings = []
        for label in validated_data['labels']:
            selected = FileLabeling.objects.filter( label=label, sourcefile__type=SourceFile.MUH5 )
            filelabelings += selected
            log.info( f" .Label '{label}': detected on {len(selected)} labelized files" )

        if not filelabelings:
            log.info( f" .No labelized file found for dataset {validated_data['name']}" )

        # Update filelabelings field
        validated_data['filelabelings'] = filelabelings

        # Set dataset json filename
        validated_data['filename'] = f"dataset-{validated_data['code']}-{datetime.now().strftime( '%Y%m%d-%H%M%S' )}.json"

        # Create and save dataset
        dataset = super().create( validated_data )

        # Create and store the metadata in json file and compress data if requested
        try:
            if validated_data['info'] and 'channels' in validated_data['info']:
                self.store( dataset, 'all' )
            else:
                self.store( dataset, 'meta' )

        except Exception as e:
            dataset.delete()
            raise serializers.ValidationError( f"Failed to store metadata of dataset: {e}" )
        
        return dataset
    

    def store( self, dataset: Dataset, option='all' ):
        """ Create an instance of the dataset 
        
        Parameters
        ----------
        dataset: Dataset
            Dataset instance to be stored
        option: str
            Option to be used for storing the dataset. Can be 'all', 'meta' or 'instance
        """

        log.info( f" .Storing dataset `{dataset.name}` with option `{option}`" )

        # Get config
        try:
            config = Config.objects.get( active=True )
        except Exception as e:
            raise serializers.ValidationError( f"Cannot get active configuration: {e}" )

        # Get channels and check instance creation
        if option == 'all' or option == 'instance':
            info = dataset.info
            channels = info['channels']
            channels_number = len( channels )
            log.info( f" .Creating instance for dataset {dataset.name} with {channels_number} channels" )

            # Build a temporary directory where to store the instance files
            instance_dir = os.path.join( config.dataset_path, 'tmp' )
            log.info( f" .Creating temporary directory {instance_dir} for dataset {dataset.name}")
            if not os.path.exists( instance_dir ):
                os.makedirs( instance_dir )
            else:
                # Remove all files in the directory
                log.info( f" .Found existing temporary directory {instance_dir}. Removing all files")
                for file in os.listdir( instance_dir ):
                    os.remove( os.path.join( instance_dir, file ) )

        # Init meta data for dataset
        dataset_labels_table = [{'label_class': idx, 'label_id': label.id, 'label_code': label.code} for idx, label in enumerate( dataset.labels.all() )]
        log.info( f" .Found {len(dataset_labels_table)} labels for dataset {dataset.name}: {dataset_labels_table}" )
        dataset_metadata = {
            'name': dataset.name,
            'code': dataset.code,
            'domain': dataset.domain.name,
            'labels_code': [label.code for label in dataset.labels.all()],
            'labels_id': [label.id for label in dataset.labels.all()],
            'labels_table': dataset_labels_table,
            'filename': dataset.filename
        }

        # Build meta data by collecting all filelabelings
        samples_metadata = []
        for sample_idx, filelabeling in enumerate( dataset.filelabelings.all() ):

            # Get file timestamp and segment timestamps, then convert to samples start and stop
            label_id = filelabeling.label.id
            log.info( f" .label_id= {label_id}")

            # find label class from label id in dataset_labels_table:
            label_class = next((label['label_class'] for label in dataset_labels_table if label['label_id'] == label_id), None)
            log.info( f" .label_class= {label_class}")

            file_timestamp = filelabeling.sourcefile.info['timestamp']
            timestamp_start = filelabeling.datetime_start
            timestamp_end = filelabeling.datetime_end
            sampling_frequency = filelabeling.sourcefile.info['sampling_frequency']
            start_time = timestamp_start - file_timestamp
            end_time = timestamp_end - file_timestamp
            sample_start = int( start_time * sampling_frequency )
            sample_end = int( end_time * sampling_frequency )

            samples_metadata.append( {
                'labeling_id': filelabeling.id,
                'start': sample_start,
                'end': sample_end,
                'sourcefile_id': filelabeling.sourcefile.id,
                'label_code': filelabeling.label.code,
                'label_id': label_id,
                'label_class': label_class,
                'timestamp': filelabeling.sourcefile.info['timestamp'],
                'type': filelabeling.sourcefile.type,
                'sw': 4 if filelabeling.sourcefile.type==SourceFile.MUH5 else filelabeling.sourcefile.info['sample_width'],
                'sr': sampling_frequency                
            } )

            # Get file data
            if option == 'all' or option == 'instance':
                filename = Directory.objects.get( pk=filelabeling.sourcefile.directory.id ).path + '/' + filelabeling.sourcefile.filename
                if filelabeling.sourcefile.type == SourceFile.MUH5:
                    data = extract_samples_from_muh5file( filename, sample_start, sample_end, channels=channels, dtype=np.int32 )
                    data = np.int16( data >> 8 )
                elif filelabeling.sourcefile.type == SourceFile.WAV:
                    data = extract_samples_from_wavfile( filename, sample_start, sample_end )
                else:
                    raise serializers.ValidationError( f"Cannot create meta data for dataset: unknown file type {filelabeling.sourcefile.type}" )

                # Save data as wav file in 16 bits integer format
                SAMPLE_FILENAME = os.path.join( instance_dir, f"{sample_idx}-{label_class}.wav" )
                with wave.open( SAMPLE_FILENAME, mode='wb' ) as wavfile:
                    wavfile.setnchannels( channels_number )
                    wavfile.setsampwidth( 2 )
                    wavfile.setframerate( int( sampling_frequency ) )
                    wavfile.writeframesraw( data )

        dataset_metadata['count'] = len( samples_metadata )
        metadata = {
            'dataset': dataset_metadata,
            'samples': samples_metadata,
            'crdate': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        }

        # Save metadata in json file
        try:
            json_filename = os.path.join( config.dataset_path, dataset.filename )
            log.info( f" .Saving metadata file {json_filename} for dataset '{dataset.name}'" )
            with open( json_filename, 'w', encoding='utf-8') as json_file:
                json.dump( metadata, json_file, ensure_ascii=False, indent=4 )

        except Exception as e:
            raise serializers.ValidationError( f"Failed to save dataset {dataset.name}: {e}" )
        
        # Compress all files in the temporary directory and remove initial wav files
        if option == 'all' or option == 'instance':
            try:
                gzip_filename = ospath.splitext( dataset.filename )[0]

                # Compress all .wav files in the temporary directory
                log.info( f" .Compressing dataset {dataset.name} in {gzip_filename}.zip" )
                shutil.make_archive( os.path.join( config.dataset_path, gzip_filename ), 'zip', instance_dir )

                # Remove all files in the temporary directory
                log.info( f" .Removing temporary directory {instance_dir} content" )
                for file in os.listdir( instance_dir ):
                    os.remove( os.path.join( instance_dir, file ) )
                
            except Exception as e:
                # Remove the metadata file and raise exception
                os.remove( json_filename )
                if os.path.exists( gzip_filename ):
                    os.remove( gzip_filename )
                raise serializers.ValidationError( f"Failed to compress dataset {dataset.name}: {e}" )

        log.info( f" .Dataset {dataset.name} successfully stored" )


    def update( self, instance: Dataset, validated_data ):
        """ Update dataset content 
        
        instance: Dataset 
            object to be updated
        validated_data: dict
            new data to be set
        """

        # Check name, code, domain and comment
        if instance.name != validated_data['name']:
            raise serializers.ValidationError( f"Cannot rename dataset. Please remove the dataset and create a new one" )
        if instance.code != validated_data['code']:
            raise serializers.ValidationError( f"Cannot change dataset code. Please remove the dataset and create a new one" )

        if instance.domain != validated_data['domain']:
            instance.domain = validated_data['domain']
        if instance.comment != validated_data['comment']:
            instance.comment = validated_data['comment']

        # Check if code has been changed and if so, update the filename
        json_needs_update = False
        gzip_needs_update = False

        # Check if code, labels, ... dataset has been changed
        if instance.labels != validated_data['labels']:
            log.info( f" .Labels have been changed: updating the dataset labels" )
            instance.labels.set( validated_data['labels'] )
            json_needs_update = True

        # Check if contexts dataset has been changed
        if instance.contexts != validated_data['contexts']:
            log.info( f" .Contexts have been changed: updating the dataset contexts" )
            instance.contexts.set( validated_data['contexts'] )
            json_needs_update = True

        # Check if tags dataset has been changed
        if instance.tags != validated_data['tags']:
            log.info( f" .Tags have been changed: updating the dataset tags" )
            instance.tags.set( validated_data['tags'] )
            json_needs_update = True

        # Check channels
        if validated_data['info'] and 'channels' in validated_data['info']:
            if not instance.info or 'channels' not in instance.info or instance.info['channels'] != validated_data['info']['channels']:
                log.info( f" .Channels have been changed: updating the dataset channels" )
                json_needs_update = True
                gzip_needs_update = True
        elif instance.info and 'channels' in instance.info:
            if not validated_data['info'] or 'channels' not in validated_data['info'] or instance.info['channels'] != validated_data['info']['channels']:
                log.info( f" .Channels have been changed: updating the dataset channels" )
                json_needs_update = True
                gzip_needs_update = True
        else:
            log.info( f" .No channels have been changed" )

        if json_needs_update:
            # Get new filelabelings
            filelabelings = []
            for label in instance.labels.all():
                selected = FileLabeling.objects.filter( label=label, sourcefile__type=SourceFile.MUH5 )
                filelabelings += selected
                log.info( f" .Label '{label}': detected on {len(selected)} labelized files" )

            # save filelabelings
            instance.filelabelings.set( filelabelings )

            # store update metadata in json file
            try:
                log.info( f" .Updating dataset json file..." )
                if gzip_needs_update:
                    self.store( instance, 'all' )
                else:
                    self.store( instance, 'meta' )

            except Exception as e:
                log.info( f" .Failed to update metadata of dataset: {e}. Actually, the dataset json file has not been updated")
                raise serializers.ValidationError( f"Failed to update metadata of dataset: {e}.  Actually, the dataset json file has not been updated" )

        # Save dataset
        super().update( instance, validated_data )

        return instance


    def remove( self ):
        """
        Remove stored dataset if any
        """
        
        # Get config and dataset object
        try:
            config = Config.objects.get( active=True )
            dataset: Dataset = self.instance
            json_filename = os.path.join( config.dataset_path, dataset.filename )
            gzip_filename = ospath.splitext( json_filename )[0] + '.zip'

        except Exception as e:
            raise serializers.ValidationError( f"Cannot get active configuration: {e}" )
        
        # Remove dataset metadata file
        if dataset.filename:
            log.info( f" .Removing metadata file for dataset '{dataset.name}'" )

            if os.path.exists( json_filename ):
                os.remove( json_filename )
                log.info( f" .'{json_filename}' file successfully removed" )
            else:
                log.info( f" .'{json_filename}' file removing failed: file not found" )

            if os.path.exists( gzip_filename ):
                os.remove( gzip_filename )
                log.info( f" .'{gzip_filename}' file successfully removed" )
            else:
                log.info( f" .'{gzip_filename}' file removing failed: file not found" )
        else:
            log.info( f" .No stored metadata to remove for dataset '{dataset.name}'" )



class DatasetUploadMetaSerializer:
    """ Upload serializer for Dataset. Send a http response with meta info content. """

    def __init__( self, dataset: Dataset ):
        """
        Download the stored dataset jason metadata file
        Endpoint: /dataset/<id>/upload
        """
        
        # A stored file exist for dataset
        if dataset.filename:

            # check file existance
            config = Config.objects.get( active=True )
            filename = os.path.join( config.dataset_path, dataset.filename )
            if not ospath.exists( filename ):
                log.info( f" .Dataset uploading failed: file not found" )
                raise MuDbException( f"Unable to upload: no dataset file found." )            

            # download file content
            log.info( f" .Starting dataset file download..." )
            with open( filename, 'rb') as file_to_upload:
                self.data = HttpResponse( file_to_upload, content_type='application/json' )
                self.data['Content-Disposition'] = f"attachment; filename={dataset.code}.json"

        else:
            # dataset has not been stored -> send error tresponse to client
            # Note that this should never occure since the dataset is stored before the upload
            # A possible response could be to create an empty json stream and send it
            raise MuDbException( f"No dataset metadata file found" )
            data = {}
            self.data = HttpResponse( json.dumps(data), content_type='application/json' )   
            self.data['Content-Disposition'] = f'attachment; filename={dataset.code}.json'


class DatasetUploadSerializer:
    """ Upload serializer for Dataset. Send a http response with gzip data instance of dataset. """

    def __init__( self, dataset: Dataset ):
        """
        Download the stored gzip file
        Endpoint: /dataset/<id>/upload
        """
        
        # A stored file exist for dataset
        if dataset.filename:

            # check file existance
            config = Config.objects.get( active=True )
            filename = os.path.join( config.dataset_path, dataset.filename )
            gzip_filename = ospath.splitext( filename )[0] + '.zip'
            if not ospath.exists( gzip_filename ):
                log.info( f" .Dataset uploading failed: file not found" )
                raise MuDbException( f"Unable serve: no dataset file found. One reason may be that you have not created a dataset instance" )          

            # download file content
            log.info( f" .Starting dataset file download..." )
            with open( gzip_filename, 'rb') as file_to_upload:
                self.data = HttpResponse( file_to_upload, content_type='application/zip' )
                self.data['Content-Disposition'] = f"attachment; filename={dataset.code}.zip"

        else:
            # dataset has not been stored -> send error tresponse to client
            raise MuDbException( f"No dataset gzip instance file found" )
