# megamicros.exception.py
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
@file megamicros.exception.py
@brief Megamicros exception base class
@documentation MegaMicros documentation is available on https://readthedoc.bimea.io
@usage from megamicros.exception import MuException
"""


from megamicros.log import log 

class MuException( Exception ):
    """Exception base class for Megamicros """

    def __init__( self, message: str="" ):
        super().__init__( message )
