# megamicros.db.query.py python module for database interface
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

from datetime import datetime
import numpy as np

from megamicros.log import log
from megamicros.data import MuAudio, FILETYPE_MUH5, FILETYPE_WAV
from megamicros.aidb.exception import MuDbException
from megamicros.aidb.session import RestDBSession, DEFAULT_TIMEOUT


DEFAULT_LIMIT = 50
DATABASE_TABLES = ['config', 'domain', 'campaign', 'device', 'directory', 'sourcefile', 'tagcat', 'tag', 'context', 'label', 'filelabeling', 'dataset']

FILETYPE_H5 = 1
FILETYPE_MP4 = 2
FILETYPE_WAV = 3
FILETYPE_MUH5 = 4

class AidbSession( RestDBSession ):

# =============================================================================
# User interface
# =============================================================================

    def getInfo( self ) -> dict :
        """ get general info about database content 
        
        Returns
        -------
        result: list
            list of dictionaries giving info on domains registered in database
        """

        result = {}
        result["domains"] = self.getDomains()

        return result


    def getDomains( self, limit: int=DEFAULT_LIMIT ) -> list :
        """ get domains info
        
        Parameters
        ----------
        limit: int
            limit number of responses 

        Returns
        -------
        domains: list
            list of dictionaries giving info on domains registered in database
        """

        response = self.get( f"/domain/?limit={limit}" ).json()['results']

        domains = []
        for domain in response:
            domains.append( {
                "name": domain["name"],
                "id": domain["id"],
            } )

        return domains
    

    def getCampaigns( self, domain_id: int, limit: int=DEFAULT_LIMIT ) -> list :
        """ get all campaigns belonging to a domain
         
        Parameters
        ----------
        domain_id: int
            domain identier in database
        limit: int
            limit number of responses 

        Returns
        -------
        campaigns: list
            list of campaigns found in database
        """

        try:
            response = self.get( f'/campaign/?domain={domain_id}&limit={limit}' ).json()["results"]
        except MuDbException:
            return []

        campaigns = []
        for campaign in response:
            campaigns.append( {
                "name": campaign["name"],
                "id": campaign["id"],
                "date": campaign["date"]
            } )            

        return campaigns


    def getDevices( self, limit: int = DEFAULT_LIMIT ) -> list :
        """ get devices info
        
        Parameters
        ----------
        limit: int
            limit number of responses 

        Returns
        -------
        devices: list
            list of dictionaries giving info on devices registered in database
        """

        response = self.get( f'/device/?limit={limit}' ).json()["results"]

        devices = []
        for device in response:
            devices.append( {
                "name": device["name"],
                "id": device["id"],
                "type": device["type"],
                "identifier": device["identifier"]
            } )

        return devices


    def getSourcefiles( self, limit: int = DEFAULT_LIMIT ) -> dict :
        """ Get sourcefiles info
        
        Parameters
        ----------
        limit: int
            limit number of responses 
        
        Returns
        -------
        devices: list
            list of dictionaries giving info on files containing audio signals in database
        """

        sourcefiles = {}
        response = self.get( f'/sourcefile/?limit={limit}' ).json()

        sourcefiles["count"] = response["count"]
        sourcefiles["content"] = []
        
        for src in response["results"]:
            sourcefiles["content"].append( {
                "id": src['id'],
                "filename": src["filename"],
                "type": src["type"],
                "datetime": src["datetime"],
                "duration": src["duration"]
            } )
        
        return sourcefiles
    

    def getSourcefileInfo( self, id: int|None=None, url: str|None=None, filename: str|None=None ) -> dict :
        """ Get sourcefiles infos from source file identifier or url
        
        Parameters
        ----------
        id: int
            sourcefile DB identifier
        url: str
            sourcefile DB address
        filename: str
            name of the source file with its extension
        
        Return
        ------
        info: dict
            sourcefiles info dictionaries
        """
        
        if id is not None:
            try:
                response = self.get( f'/sourcefile/{id}' ).json()
            except MuDbException as e:
                log.info( f" .{e}" )
                return {}
            
        elif url is not None:
            try:
                response = self.get( url, full_url=True ).json()
            except MuDbException as e:
                log.info( f" .{e}" )
                return {}
            
        elif filename is not None:
            try:
                response = self.get( f'/sourcefile/?filename={filename}' ).json()
            except MuDbException as e:
                log.info( f" .{e}" )
                return {}
        else:
            raise MuDbException( f"Cannot get file from DB: no id, url or file name given as input" )
                 
        return response


    def loadSourcefile( self, id: int ):
        """ Upload a sound file from database 

        Parameters
        ----------
        id: int
            sourcefile DB identifier
        
        Return
        ------
        signal: np.ndarray
            muh5 file
        """

        try:
            response = self.get( f'/sourcefile/{id}/upload' ).content
        except MuDbException as e:
            log.info( f" .{e}" )
            return {}
        
        return response
 

# =============================================================================
# Generics
# =============================================================================

    def get_meta( self, object:str, id:int|None=None, url:str|None=None, field:dict|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """ Get object metadata content from identifier url or other fields given as argument

        Parameters
        ----------
        object: str
            object name (the database table name)
        id: int, optional
            object identifier in database
        url: str, optional
            object full url in database
        field: dict, optional
            dictionary of the form ``{'label': 'field_name', 'value': value }`` giving the field for searching
        timeout: int, optional
            the time after which the call throw a timeout exception
        """
        if object not in DATABASE_TABLES:
            log.error( f"Fetching metadata failed for object {object}: unknown object" )
            raise MuDbException( f"Cannot fetch metadata for object {object} which is not known!")

        if id is not None:
            log.info( f" .Downloading metadata for object '{object}' [{id}]..." )
            response = self.get( f"/{object}/{id}", timeout=timeout ).json()
            log.info( f" .Object {object} found with identifier [{id}] " )
            return response
        
        if url is not None:
            log.info( f" .Downloading metadata for object {object} from its url [{url}]..." )
            response = self.get( url, full_url=True, timeout=timeout ).json()
            log.info( f" .Object {object} found with url [{url}] " )
            return response 

        elif field is not None:
            assert 'label' in field and 'value' in field, "field argument should be of the form {'label':'field_name', 'value':value}"
            field_query = f"{field['label']}={field['value']}"
            log.info( f" .Downloading metadata for object '{object}' from field '{field['label']}'..." )
            response = self.get( f"/{object}/?{field_query}", timeout=timeout ).json()
        else:
            log.warning( f"No field was given nor identifier or url: cannot find object {object} metadata" )
            return {}           

        if response['count'] == 0:
            log.info( f" .Found no object {object}" )
            return {}
        elif response['count'] > 1:
            log.info( f" .Found more than one object {object}. Returning the first (id is [{response['results'][0]['id']}])" )
            return response['results'][0]
        else:
            log.info( f" .Object {object} found with identifier [{response['results'][0]['id']}] " )
            return response['results'][0]
        

# =============================================================================
# Domains
# =============================================================================

    def get_domain( self, id:int|None=None, url:str|None=None, name:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Get domain metadata content from identifier url or name
        """
        field = None if name is None else {'label': 'name', 'value': name}
        return self.get_meta( object='domain', id=id, url=url, field=field, timeout=timeout )


    def load_domains( self, limit:int=DEFAULT_LIMIT ) -> list[dict]:
        """
        Get all the domains defined in the database

        ## Parameters
        * limit: max number of responses
        """
        
        log.info( f" .Downloading domains from {self.dbhost}..."  )
        response = self.get( f"/domain/?limit={limit}" ).json()['results']
        log.info( f" .Received {len( response )} domains" )
        return response


# =============================================================================
# Campaigns
# =============================================================================

    def get_campaign( self, id:int|None=None, url:str|None=None, name:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Get campaign metadata content from identifier url or name
        """
        field = None if name is None else {'label': 'name', 'value': name}
        return self.get_meta( object='campaign', id=id, url=url, field=field, timeout=timeout )
        

    def load_campaigns( self, limit:int=DEFAULT_LIMIT ) -> list[dict]:
        """
        Get all the campaigns defined in the database

        ## Parameters
        * limit: max number of responses
        """
        
        log.info( f" .Downloading campaigns from {self.dbhost}..."  )
        response = self.get( f"/campaign/?limit={limit}" ).json()['results']
        log.info( f" .Received {len( response )} campaigns" )
        return response

# =============================================================================
# Directory
# =============================================================================

    def get_directory( self, id:int|None=None, url:str|None=None, name:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Get directory metadata content from identifier url or name
        """
        field = None if name is None else {'label': 'name', 'value': name}
        return self.get_meta( object='directory', id=id, url=url, field=field, timeout=timeout )


    def load_directory_files( self, id:int, file_type:int, file_datetime:str, limit:int=DEFAULT_LIMIT ) -> list[dict]:
        """
        Get metadata on files in directory

        ## Parameters
        * id: directory identifier
        * file_type: type of files ()
        * file_datetime: the datetime string (format: YYYY-MM-DDThh:mm:ss.0Z) of the file
        """ 

        #assert (
        #    file_type == FILETYPE_MUH5 or file_type == FILETYPE_WAV or file_type == FILETYPE_MP4 or file_type == FILETYPE_H5, 
        #    f"Unknown file type '{file_type}"
        #)

        log.info( f" .Downloading files of type {file_type} at date {file_datetime} from directory {id}..."  )
        url_request = f"/directory/{str(id)}/files/{str(file_type)}/datetime/{file_datetime}/?limit={str(limit)}"
        response = self.get( url_request ).json()
        assert 'results' not in response, "There is a 'results' entry in this request response while it should not"
        if 'results' in response:
            response = response['results']
        log.info( f" .Received {len( response )} files" )

        return response



# =============================================================================
# Devices
# =============================================================================

    def get_device( self, id:int|None=None, url:str|None=None, name:str|None=None, identifier:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Get device content from identifer
        """
        field = None if name is None else {'label': 'name', 'value': name}

        if name is not None:
            field = {'label': 'name', 'value': name}
        elif identifier is not None:
            field = {'label': 'identifier', 'value': identifier}
        else:
            field = None

        return self.get_meta( object='device', id=id, url=url, field=field, timeout=timeout )


    def load_devices( self, limit:int=DEFAULT_LIMIT ) -> list[dict]:
        """
        Get all the devices defined in the database

        ## Parameters
        * limit: max number of responses
        """
        
        log.info( f" .Downloading devices from {self.dbhost}..."  )
        response = self.get( f"/device/?limit={limit}" ).json()['results']
        log.info( f" .Received {len( response )} devices" )
        return response


# =============================================================================
# Tags categories
# =============================================================================

    def get_tagcat( self, id:int|None=None, url:str|None=None, name:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Get tag category metadata content from identifier url or name
        """
        field = None if name is None else {'label': 'name', 'value': name}
        return self.get_meta( object='tagcat', id=id, url=url, field=field, timeout=timeout )

    def load_tagcats( self, limit:int=DEFAULT_LIMIT, timeout:int=DEFAULT_TIMEOUT ) -> list[dict]:
        """
        Load tags from database
        """
        log.info( f" .Downloading tags categories from {self.dbhost}..." )
        response = self.get( f"/tagcat/?limit={limit}", timeout=timeout ).json()['results']
        log.info( f" .Received {len( response )} tags categories" )

        return response
    
    def create_tagcat( self, name:str, comment: str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Save a new tag category in database
        
        Parameters
        ==========
        * name: the name of the category
        * comment: some optional comments
        """

        log.info( f" .Sending POST request for tag category creating..." )
        response = self.post(
            request='/tagcat/',
            content = {
                'name': name,
                "comment": None if not comment else comment 
            },
            timeout=timeout
        ).json()
        log.info( f" .Successfully saved new tag category <{name}> on database")

        return response


    def update_tagcat( self, id:int, u_name:str, u_comment:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Update a tag category in database
        
        Parameters
        ==========
        * id: the category identifier  
        * u_name: the new name of the category
        * u_comment: some new optional comments
        """

        log.info( f" .Sending PUT request for tag category updating..." )

        response = self.put( 
            request = f"/tagcat/{id}/",
            content = {
                'name': u_name,
                "comment": None if not u_comment else u_comment
            },
            timeout=timeout
        ).json()
        log.info( f" .Successfully updated tag category <{u_name}> on database")

        return response
    

    def delete_tagcat( self, id:int ) -> dict:
        """
        delete a tag category in database
        
        Parameters
        ==========
        * id: the category identifier
        """

        log.info( f" .Sending DELETE request on target for tag category deleting..." )
        response = self.delete( request=f"/tagcat/{id}/" ).json()
        log.info( f" .Successfully deleted tag category <{id}> on database")

        return response


# =============================================================================
# Tags
# =============================================================================

    def get_cat( self, id:int|None=None, url:str|None=None, name:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Get tag metadata content from identifier url or name
        """
        field = None if name is None else {'label': 'name', 'value': name}
        return self.get_meta( object='cat', id=id, url=url, field=field, timeout=timeout )


    def load_tags( self, tagcat_id:int|None=None, limit:int=DEFAULT_LIMIT, timeout:int=DEFAULT_TIMEOUT ) -> list[dict]:
        """
        Load tags from database
        """
        log.info( f" .Downloading tags from {self.dbhost}..." )
        request_url = f"/tag/?limit={limit}"
        if tagcat_id is not None:
            request_url = f"{request_url}&tagcat={tagcat_id}"
        response = self.get( request_url, timeout=timeout ).json()['results']
        log.info( f" .Received {len( response )} tags" )

        return response


    def create_tag( self, name:str, tagcat_id: int|None=None, comment: str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Save a new tag in database
        
        Parameters
        ==========
        * name: the name of the tag
        * tagcat_id: tag category
        * comment: some optional comments
        """

        log.info( f" .Sending POST request for tag creating..." )
        response = self.post(
            request='/tag/',
            content = {
                'name': name,
                'tagcat': tagcat_id,
                "comment": None if not comment else comment 
            },
            timeout=timeout
        ).json()
        log.info( f" .Successfully saved new tag <{name}> on database")

        return response


    def update_tag( self, id:int, u_name:str, u_tagcat_id: int|None=None, u_comment:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Update a tag category in database
        
        Parameters
        ==========
        * id: the category identifier  
        * u_name: the new name of the category
        * u_tagcat_id: tag category
        * u_comment: some new optional comments
        """

        log.info( f" .Sending PUT request for tag updating..." )

        response = self.put( 
            request = f"/tag/{id}/",
            content = {
                'name': u_name,
                'tagcat': u_tagcat_id,
                "comment": None if not u_comment else u_comment
            },
            timeout=timeout
        ).json()
        log.info( f" .Successfully updated tag <{u_name}> on database")

        return response
    

    def delete_tag( self, id:int ) -> dict:
        """
        delete a tag in database
        
        Parameters
        ==========
        * id: the tag identifier
        """

        log.info( f" .Sending DELETE request on target for tag deleting..." )
        response = self.delete( request=f"/tag/{id}/" ).json()
        log.info( f" .Successfully deleted tag <{id}> on database")

        return response


# =============================================================================
# Labels
# =============================================================================

    def get_label( self, id:int|None=None, url:str|None=None, name:str|None=None, code:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Get tag metadata content from identifier url or name
        """
        if name is not None:
            field = {'label': 'name', 'value': name}
        elif code is not None:
            field = {'label': 'code', 'value': code}
        else:
            field = None

        return self.get_meta( object='label', id=id, url=url, field=field, timeout=timeout )


    def load_labels( self, domain_id:int|None=None, limit:int=DEFAULT_LIMIT, timeout:int=DEFAULT_TIMEOUT ) -> list[dict]:
        """
        Get all the labels defined in the database

        ## Parameters
        * domain_id: the domain identifier for response filtering (default: all domains)
        * limit: max number of responses
        """
        
        log.info( f" .Downloading labels from {self.dbhost}..." )
        request_url = f"/label/?limit={limit}"
        if domain_id is not None:
            request_url = f"{request_url}&domain={domain_id}"
        response = self.get( request_url, timeout=timeout ).json()['results']
        log.info( f" .Received {len( response )} labels" )

        return response


    def create_label( self, name: str, code: str, domain_id: int, tags_id:list|None, parent_id:int|None=None, comment:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Create a new label in database
        
        Parameters
        ==========
        * name: name of the label
        * code: code
        * domain_id: the domain identifier
        * tags_id: the list of all tags identifiers
        * comment: some optional comments
        """

        # build tags url
        tags = [] if tags_id is None else [ f"{self.dbhost}/tag/{labeltag_id}/" for labeltag_id in tags_id]

        log.info( f" .Sending POST request for label creating..." )
        response = self.post(
            request='/label/',
            content = {
                'parent': None if parent_id is None else f"{self.dbhost}/label/{parent_id}/",
                'domain': f"{self.dbhost}/domain/{domain_id}/",
                'name': name,
                'code': code,
                'comment': None if not comment else comment,
                'info': None,
                'tags': tags
            },
            timeout=timeout
        ).json()

        log.info( f" .Successfully created new label {name} at endpoint {response['url']}")

        return response


    def update_label( self, id:int, name:str, code:str, domain_id:int, tags_id:list|None, parent_id:int|None=None, comment:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Update a label in database
        
        Parameters
        ==========
        * id: the label identifier in database
        * name: name of the label
        * code: code
        * domain_id: the domain identifier
        * tags_id: the list of all tags identifiers
        * comment: some optional comments
        """

        log.info( f" .Sending PUT request for label updating..." )

        # build the tags url
        tags = [] if tags_id is None else [ f"{self.dbhost}/tag/{labeltag_id}/" for labeltag_id in  tags_id]

        response = self.put( 
            request=f"/label/{id}/",
            content = {
                'parent': None if parent_id is None else f"{self.dbhost}/label/{parent_id}/",
                'domain': f"{self.dbhost}/domain/{domain_id}/",
                'name': name,
                'code': code,
                'comment': None if not comment else comment,
                'info': None,
                'tags': tags
            },
            timeout=timeout
        ).json()

        log.info( f" .Successfully updated label <{name}> on database")
        return response


    def delete_label( self, id:int ):
        """
        delete a label in database
        
        Parameters
        ==========
        * id: the label identifier
        """

        log.info( f" .Sending DELETE request for label deleting..." )
        response = self.delete( request=f"/label/{id}/" ).json()
        log.info( f" .Successfully deleted label <{id}> on database")

        return response


# =============================================================================
# Context
# =============================================================================

    def get_context( self, id:int|None=None, url:str|None=None, name:str|None=None, code:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Get context metadata content from identifier url or name
        """
        if name is not None:
            field = {'label': 'name', 'value': name}
        elif code is not None:
            field = {'label': 'code', 'value': code}
        else:
            field = None

        return self.get_meta( object='context', id=id, url=url, field=field, timeout=timeout )


    def load_contexts( self, domain_id:int|None=None, limit:int=DEFAULT_LIMIT, timeout:int=DEFAULT_TIMEOUT ) -> list[dict]:
        """
        Load contexts from database
        """
        log.info( f" .Downloading contexts from {self.dbhost}..." )
        request_url = f"/context/?limit={limit}"
        if domain_id is not None:
            request_url = f"{request_url}&domain={domain_id}"
        response = self.get( request_url, timeout=timeout ).json()['results']
        log.info( f" .Received {len( response )} contexts" )

        return response

    def create_context( self, name:str, code:str, type:int, domain_id:int, tags_id:list|None, parent_id:int|None, comment:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Create a new context in database
        
        Parameters
        ==========
        * name: the name of the context
        * code: the code
        * type: the context type 
        * domain_id: the domain identifier
        * tags_id: the list of all tags identifiers
        * parent_id: the parent identifier or None if not
        * comment: some optional comments
        """

        # build the tags url
        tags = [] if tags_id is None else [ f"{self.__dbhost}/tag/{contexttag_id}/" for contexttag_id in tags_id]

        response = self.post( 
            request='/context', 
            content = {
                'parent': None if parent_id is None else f"{self.dbhost}/context/{parent_id}/",
                'domain': f"{self.dbhost}/domain/{domain_id}/",
                'name': name,
                'code': code,
                'type': type,
                'comment': None if not comment else comment,
                'info': None,
                'tags': tags
            },
            timeout=timeout
        ).json()

        log.info( f" .Successfully created new context {name} at endpoint {response['url']}")

        return response


    def update_context( self, id:int, name:str, code:str, type:int, domain_id:int, tags_id:list|None, parent_id:int|None, comment:str|None=None ) -> dict:
        """
        Update a context in database
        
        Parameters
        ==========
        * id: the context identifier in database
        * name: name of the label
        * code: code
        * type: context type 
        * domain_id: the domain identifier
        * tags_id: the list of all tags identifiers
        * parent_id: the parent identifier or None
        * comment: some optional comments
        """

        log.info( f" .Sending PUT request on target <{self.dbhost}/context/{id}/>..." )

        # build the tags url
        tags = [] if tags_id is None else [f"{self.dbhost}/tag/{contexttag_id}/" for contexttag_id in tags_id]

        response = self.put( 
            request=f"/context/{id}/",
            content = {
                'parent': None if parent_id is None else f"{self.dbhost}/context/{parent_id}/",
                'domain': f"{self.dbhost}/domain/{domain_id}/",
                'name': name,
                'code': code,
                'type': type,
                'comment': None if not comment else comment,
                'info': None,
                'tags': tags
            }
        ).json()

        log.info( f" .Successfully updated context <{name}> on database")
        return response
    

    def delete_context( self, id:int ) -> dict:
        """
        delete a context in database
        
        Parameters
        ==========
        * id (int): the context identifier
        """

        log.info( f" .Sending DELETE request for context id {id}..." )
        response = self.delete( request=f"/context/{id}/" ).json()
        log.info( f" .Successfully deleted context <{id}> on database")

        return response


# =============================================================================
# Sourcefiles
# =============================================================================

    def get_sourcefile( self, id:int|None=None, url:str|None=None, filename:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """ Get context metadata content from identifier url or name
        """
        field = None if filename is None else {'label': 'filename', 'value': filename}
        return self.get_meta( object='sourcefile', id=id, url=url, field=field, timeout=timeout )
        

    def patch_sourcefile( self, id:int, tags_id:list|None=None, comment:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Update a label in database
        
        Parameters
        ==========
        * id: the label identifier in database
        * tags_id: the list of all tags identifiers
        * comment: some optional comments
        """

        if tags_id is None and comment is None:
            raise MuDbException( "Cannot patch sourcefile: no tags nor comment or other field(s) given")
        
        log.info( f" .Sending PATCH request for sourcefile updating..." )

        content = {}
        if tags_id is not None:
            # build the tags url
            content['tags'] = [ f"{self.dbhost}/tag/{tag_id}/" for tag_id in tags_id ]

        if comment is not None and comment:
            content['comment'] = comment

        response = self.patch( 
            request=f"/sourcefile/{id}/",
            content = content,
            timeout=timeout
        ).json()

        log.info( f" .Successfully updated sourcefile [{id}] on database")
        return response
    
    def get_samples_range( self, start: int, stop:int, channels: np.ndarray, id:int|None=None, url:str|None=None, filename:str|None=None, timeout:int=DEFAULT_TIMEOUT ):
        """ Get range samples (stop - start) from DB signal 
        
        Parameters
        ----------
        start: int
            starting sample number in signal
        stop: int
            last sample number in signal
        channels: no.ndarray
            array of channels to get 
        id: int|None
            file identifier in database
        url: str|None
            file url
        filename: str|None
            file name
        timeout: int
            timeout after what the request failed
        """
        
        # Get metadata from file
        field = None if filename is None else {'label': 'filename', 'value': filename}
        try:
            meta = self.get_meta( object='sourcefile', id=id, url=url, field=field, timeout=timeout )
        except Exception as e:
            raise MuDbException( f"Unable to get metadata from file: {str( e )}" )
        
        if id is None:
            id = int(meta['id'])
        if filename is None:
            filename = meta['filename']
        if url is None:
            url = meta['url']

        log.info( f" .Getting signals from file `{filename} (id={id})` at endpoint {url}" )

        # Format the request
        channels_str = ( ''.join( str( integer ) + ',' for integer in channels ) )[:-1]
        request_url = f"sourcefile/{id}/samples/{start}/{stop}/channels/0/0/?channels={channels_str}"

        log.info( f" .Requesting data in range [{start}, {stop}] samples (length={stop-start} samples)" )

        try:
            response = self.get( request_url ).content
        except MuDbException as e:
            log.info( f" .{e}" )
            return {}

        # Return bytes content response
        return response

        """
        try:
            log.info( f" .Opening DB file on endpoint {url}" )
            with requests.get(url, stream=True) as response:

                # Get the content type and length from the response headers
                content_type = response.headers.get('content-type')
                content_length = int( response.headers.get('content-length') )

                log.info( f" .Got positive response from server with for {content_type} data of {content_length} bytes length" )
                log.info( f" .Start receiving {content_length//chunk_size} paquets of size {self.frame_length} x {channels_number}" )
                if (content_length%chunk_size) % (channels_number*4) != 0:
                    raise MuDBException( f"Inconsistency between data received ({content_length}) bytes and query ({self.frame_length} x {channels_number})" )
                
                log.info( f" .Last chunk will carry {int( (content_length%chunk_size)/channels_number/4 )} remaining samples" )

                # Check if the request was successful
                response.raise_for_status()

        except Exception as e:
            pass 
        """




# =============================================================================
# Labelings
# =============================================================================

    def get_labeling( self, id:int|None=None, url:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Get labeling metadata content from identifier url or name
        """
        return self.get_meta( object='filelabeling', id=id, url=url, timeout=timeout )


    def load_labelings( self, sourcefile_id:int|None=None, label_id:int|None=None, limit:int=DEFAULT_LIMIT, timeout:int=DEFAULT_TIMEOUT ) -> list[dict]:
        """
        Load labelings from database
        """

        # build request with elements filtering if any
        request_url = f"/filelabeling/?limit={limit}"
        if sourcefile_id is not None:
            request_url = f"{request_url}&sourcefile={sourcefile_id}"

        if label_id is not None:
            request_url = f"{request_url}&label={label_id}"

        log.info( f" .Downloading labelings from {self.dbhost}..." )
        response = self.get( request_url, timeout=timeout ).json()['results']
        log.info( f" .Received {len( response )} labelings" )

        return response
    

    def create_labeling( self, sourcefile_id:int, label_id:int, contexts_id:list|None, tags_id:list|None, timestamp_start:float, timestamp_end:float, comment:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Create a new labeling in database
        
        Parameters
        ==========
        * soucefile_id: the file identifier
        * label_id: label identifier
        * contexts_id: list of contexts identifiers
        * tags_id: the list of all tags identifiers
        * timestamp_start: the start audio timestamp (universal time)
        * timestamp_end: the end audio timestamp (universal time)
        * comment: some optional comments
        """

        # build tags url
        tags = [] if tags_id is None else [ f"{self.dbhost}/tag/{tag_id}/" for tag_id in  tags_id]

        # build contexts url
        contexts = [] if contexts_id is None else [ f"{self.dbhost}/context/{context_id}/" for context_id in  contexts_id]

        log.info( f" .Sending POST request for labeling creating..." )
        response = self.post(
            request='/filelabeling/',
            content = {
                'sourcefile': f"{self.dbhost}/sourcefile/{sourcefile_id}/",
                'label': f"{self.dbhost}/label/{label_id}/",
                'contexts': contexts,
                'tags': tags,
                'datetime_start': timestamp_start,
                'datetime_end': timestamp_end,
                'comment': None if comment is None or not comment else comment,
                'info': None,
            },
            timeout=timeout
        ).json()
        log.info( f" .Successfully created new labeling [{response['id']}]")

        return response


    def patch_labeling( self, id:int, label_id:int, contexts_id:list|None, tags_id:list|None, comment:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Update filelabeling using the PATCH REST command. Only the four field given as args can be updated.
        For more you have to delete the entry. 

        ## Parameters
        * id: the labeling database identifier
        * label_id: the label database identifier (mandatory)
        * contexts_id: the contexts identifiers list
        * tags_id: the tags identifiers list
        * comment: somme comments on the labeling
        """

        # build the tags url
        tags = [] if tags_id is None else [ f"{self.dbhost}/tag/{tag_id}/" for tag_id in tags_id ]

        # build the contexts url
        contexts = [] if contexts_id is None else [ f"{self.dbhost}/context/{ctx_id}/" for ctx_id in contexts_id ]

        log.info( f" .Sending PATCH request for labeling updating..." )
        response = self.patch( 
            request=f"/filelabeling/{id}/",
            content = {
                'label': f"{self.dbhost}/label/{label_id}/",
                'contexts': contexts,
                'tags': tags,
                'comment': None if comment is None or not comment else comment
            },
            timeout=timeout
        ).json()

        log.info( f" .Successfully updated label [{id}] on database")
        return response


    def delete_labeling( self, id:int ):
        """
        delete a labeling in database
        
        ## Parameters
        * id: the label identifier to delete
        """

        log.info( f" .Sending DELETE request for labeling deleting..." )
        response = self.delete( request=f"/filelabeling/{id}/" ).json()
        log.info( f" .Successfully deleted labeling <{id}> on database")

        return response


# =============================================================================
# Dataset
# =============================================================================

    def load_datasets( self, domain_id:int|None=None, labels_id:list|None=None, contexts_id:list|None=None, tags_id:list|None=None, limit:int=DEFAULT_LIMIT, timeout:int=DEFAULT_TIMEOUT ) -> list[dict]:
        """
        Load labelings from database
        """

        # build request with elements filtering if any
        request_url = f"/dataset/?limit={limit}"
        if domain_id is not None:
            request_url = f"{request_url}&domain={domain_id}"

        if labels_id is not None:
            request_url = f"{request_url}&" + '&'.join( f"labels={label_id}" for label_id in labels_id )

        if contexts_id is not None:
            request_url = f"{request_url}&" + '&'.join( f"contexts={context_id}" for context_id in contexts_id )

        if tags_id is not None:
            request_url = f"{request_url}&" + '&'.join( f"tags={tag_id}" for tag_id in tags_id )

        log.info( f" .Downloading datasets from {self.dbhost}..." )
        response = self.get( request_url, timeout=timeout ).json()['results']
        log.info( f" .Received {len( response )} datasets" )

        return response

    def get_dataset_metadata( self, id:int|None=None, url:str|None=None, name:str|None=None, code:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Get dataset metadata content from identifier, url, name or code

        Parameter
        ---------

        id: int|None
            identifier of the dataset
        url: str|None
            url of the dataset (should full pathname with endpoint)
        name: str|None
            name of the dataset
        code: str|None
            code of the dataset
        timeout: int
            timeout after what the request failed

        Return
        ------
        dataset: dict
            the dataset metadata content as a dict object
        """

        # id and url are not provided, find the dataset from its name
        if id is None and url is None:
            if name is None and code is None:
                raise MuDbException( "Cannot get dataset: no identifier nor name or code given" )
            elif name is not None:
                field = {'label': 'name', 'value': name}
            elif code is not None:
                field = {'label': 'code', 'value': code}

            object = self.get_meta( object='dataset', field=field, timeout=timeout )
            id = object['id']
        
        if id is not None:
            response = self.get(  f"/dataset/{id}/meta", timeout=timeout ).json()
        else:
            response = self.get( url, timeout=timeout, full_url=True ).json()
            
        return response        

    def download_dataset( self, id:int|None=None, url:str|None=None, name:str|None=None, code:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """ Upload dataset data from identifier, url, name or code

        Parameter
        ---------

        id: int|None
            identifier of the dataset
        url: str|None
            url of the dataset (should full pathname with endpoint)
        name: str|None
            name of the dataset
        code: str|None
            code of the dataset
        timeout: int
            timeout after what the request failed

        Return
        ------
        data
            the zip compressed dataset data content in bytes
        """

        # id and url are not provided, find the dataset from its name
        if id is None and url is None:
            if name is None and code is None:
                raise MuDbException( "Cannot get dataset: no identifier nor name or code given" )
            elif name is not None:
                field = {'label': 'name', 'value': name}
            elif code is not None:
                field = {'label': 'code', 'value': code}

            object = self.get_meta( object='dataset', field=field, timeout=timeout )
            id = object['id']
        
        if id is not None:
            response = self.get(  f"/dataset/{id}/upload", timeout=timeout )
        else:
            response = self.get( url, timeout=timeout, full_url=True )
            
        # Check if the response is a zip file
        if response.headers['Content-Type'] != 'application/zip':
            if response.headers['Content-Type'] == 'application/json':
                if response.json()['status'] == 'error':
                    raise MuDbException( f"Failed to download data. Server response was: {response.json()['message']}" )
                else:
                    raise MuDbException( f"Failed to download data. Server response was: {response.json()}" )                
            else:
                raise MuDbException( f"Failed to download data: server didn't give a zip file as response" )

        return response.content


    def create_dataset( self, name:str, code:str, domain_id:int, labels_id:list|None, contexts_id:list|None=None, tags_id:list|None=None, comment:str|None=None, timeout:int=DEFAULT_TIMEOUT ) -> dict:
        """
        Create a new label in database
        
        Parameters
        ==========
        * name: the dataset name
        * code: the dataset code
        * domain_id: domain identifier
        * labels_id: labels identifier
        * contexts_id: list of contexts if any
        * tags_id: list of tags if any
        * comment: some optional comments
        """

        # build labels, tags and contexts url
        labels = [] if labels_id is None else[ f"{self.dbhost}/label/{label_id}/" for label_id in labels_id]
        tags = [] if tags_id is None else [ f"{self.dbhost}/tag/{tag_id}/" for tag_id in tags_id]
        contexts = [] if contexts_id is None else [ f"{self.dbhost}/context/{context_id}/" for context_id in contexts_id]

        response  = self.post(
            request = '/dataset/',
            content = {
                'name': name,
                'code': code,
                'domain': f"{self.dbhost}/domain/{domain_id}/",   
                'labels': labels,
                'contexts': contexts,
                'tags': tags,
                'comment': None if comment is None or not comment else comment,
                'info': {},
            },
            timeout=timeout
        ).json()

        log.info( f" .Successfully created new dataset [{response['id']}]")


    def delete_dataset( self, id:int ):
        """
        delete a dataset in database
        
        Parameters
        ==========
        * id: the dataset identifier
        """

        log.info( f" .Sending DELETE request for dataset deleting..." )
        response = self.delete( request=f"/dataset/{id}/" ).json()
        log.info( f" .Successfully deleted dataset <{id}> on database")

        return response


# =============================================================================
# Get audio signals from database
# =============================================================================

    def load_labelized( self, label_id:int, sourcefile_id:int|None=None, tags_id:None|int|list[int]=None, limit:int|None=None, timeout:int=DEFAULT_TIMEOUT, channels:list|None=None ) -> list[MuAudio]:
        """
        Load labelized audio data from database

        Parameters
        ----------
        label_id: int
            the label identifier
        sourcefile_id: int, optional
            file identifier for file filtering (default: all database files are considered)
        tags_id: int, optional
            tag's identifiers for response filtering (default: all tags accepted)
        limit: int, optional
            max number of audio signals to download. Default is 100
        timeout: int, optional
            the delay before abandon if the server does not responds
        channels: list, optional
            list of channels to extract from the file, default is [1,2]

        Returns
        -------
        results: list
            List of MuAudio objects 
        """

        # Get labelized signal's metadata
        log.info( f" .Downloading labelized audio files from {self.dbhost}..." )

        queries = [f"label={str( label_id )}"]
        if limit is not None:
            queries.append( f"limit={str( limit )}" )

        if sourcefile_id is not None:
            queries.append( f"sourcefile={str( sourcefile_id )}" )

        if tags_id is not None:
            if type( tags_id ) is int:
                queries.append( f"tags={str( tags_id )}" )
            elif type( tags_id ) is list[int]:                    
                queries.append( f"tags={str( tag_id )}" for tag_id in tags_id ) 
            else:
                log.error( "Unknown type of identifier for 'tags_id' parameter. This can be a bug issue" )
                raise MuDbException( "Unknown type of identifier for 'tags_id' parameter" )
        
        response = self.get( f"/filelabeling/?{'&'.join( queries )}", timeout=timeout ).json()
        print( f"request=/filelabeling/?{'&'.join( queries )}" )
        
        
        if response['count'] == 0:
            log.info( f" .No signal labelized found for label {label_id}'")
            return []
        else:
            log.info( f" .Found {response['count']} labelized audio files" )
            if limit is not None:
                log.info( f" .Limit is set to {limit} audio files" )
    
        # Build MuAuio objects for every labelized file found
        results = []
        for labeling in response['results']:

            # get sourcefile metada
            sourcefile = self.get_sourcefile( labeling['sourcefile_id'] )

            # check file datetime
            if sourcefile['type'] == FILETYPE_MUH5:
                datetime_file = datetime.strptime( sourcefile['datetime'], "%Y-%m-%dT%H:%M:%S.%fZ" )
            elif sourcefile['type'] == FILETYPE_WAV:
                datetime_file = datetime.strptime( sourcefile['datetime'], "%Y-%m-%dT%H:%M:%SZ" )
            else:
                log.info(  f" .Failed to get get signal from file '{sourcefile['filename']}': file type [{sourcefile['type']}] is not yet considered" )
                continue

            # set the database request endpoint for signal uploading            
            start = ( datetime.fromtimestamp( labeling['datetime_start'] ) - datetime_file ).total_seconds()
            end = ( datetime.fromtimestamp( labeling['datetime_end'] ) - datetime_file ).total_seconds()

            # download signal from database
            url = f"{labeling['sourcefile']}range/{start}/{end}/channels/1/2/"
            if channels is not None:
                url = f"{url}?channels={str(channels).replace( '[', '' ).replace( ']', '' ).replace( ' ', '' )}"
                channels_number = len( channels )
            else:
                channels_number = 2
            
            response =  self.get( url, timeout=timeout, full_url=True )
            if response.headers['Content-Type'] == 'application/json':
                log.info( f" .Received a negative answer from server for labeling [{labeling['id']}]: {response.json()['message']}" )
                continue

            audio = np.frombuffer( response.content, dtype=np.float32 )

            samples_number = int( audio.size / channels_number )
            audio = np.reshape( audio, ( samples_number, channels_number ) ).T
            results.append( 
                MuAudio( audio, sampling_frequency=sourcefile['info']['sampling_frequency'], label=labeling['label_code'])
            )

        return results