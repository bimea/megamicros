# megamicros.virtual.py
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
Module that simulates a virtual antenna using generators

Features:


Examples:
    Basic usage::

        from megamicros import log
        from megamicros.virtual import VirtMArray

        antenna = VirtMArray()

        antenna.run(
            mems=[0, 1, 2, 3, 4, 5, 6, 7],
            sampling_frequency=44100,
            duration=10,
            frame_length=1024,
            datatype='int32'
        )
        antenna.wait()

        # Print frames stored in the queue
        print(f"queue content : {antenna.queue_content} frames")

        # Retrieve data from the queue
        for data in antenna:
            print( f"data={data}" )

    Advanced usage::

        See the Notebooks for advanced usage examples.

Documentation:
    Full MegaMicros documentation is available at: https://readthedoc.bimea.io
"""