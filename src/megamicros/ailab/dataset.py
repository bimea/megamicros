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

import numpy as np


from megamicros.log import log
from megamicros.exception import MuException
from megamicros.aidb.query import AidbSession
from torch.utils.data import TensorDataset

DATASET_DEFAULT_LOGIN       = 'ailab'
DATASET_DEFAULT_EMAIL       = 'bruno.gas@biimea.com'
DATASET_DEFAULT_PASSWD      = '#T;uZnQ5UJ_JC~&'


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

    __dbhost: str
    __labels: list
    __login: str
    __email: str
    __passwd: str

    def __init__( self, dbhost: str, login: str=DATASET_DEFAULT_LOGIN, email:str=DATASET_DEFAULT_EMAIL, password: str=DATASET_DEFAULT_PASSWD, labels: list=[] ):
        """
        Get meta informations from the remote database

        Parameters
        ----------
        dbhost: str
            hostname or IP address
        login: str, optionnal
            database acces login
        email: str, optionnal
            database user email
        passwd: str, optionnal
            database password
        labels: list, optionnal
            labels identifier or name of data
        """

        self.__dbhost = dbhost
        self.__labels = labels
        self.__login = login
        self.__email = email
        self.__password = password
        self.__meta = None


        # Open database
        try:
            with AidbSession( dbhost=self.__dbhost, login=self.__login, email=self.__email, password=self.__password ) as session:
                # get meta data
                self.__meta = session.get_sourcefile( 1 )

            print( f'meta={self.__meta}')


        except MuException as e:
            raise MuAilabException( f"Connection to database {self.__dbhost} failed ({type(e).__name__}): {e}" )
