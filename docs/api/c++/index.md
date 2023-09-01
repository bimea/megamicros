# The C++ Megamicros library

The *Megamicros-c++* library has been designed for very specific usages such as installing a server for sending audio or high level data coming from a microphone array through the network.

The library is build over the *libusb 1.0* library.

* [Megamicros](megamicros/index.md)
* [MegamicrosUSB](megamicros-usb/index.md)
* [Usb](usb/index.md)

## Installing

First you have to install the *cmake* utilitary, the *pkg-config* utilitary and the *libusb* C library on your system. On Mac systems:

```bash
  $ > brew install cmake pkg-config libusb
```

On linux/Ubuntu systems, install the [libusb library](https://libusb.info/):

```bash
  $ > sudo apt install cmake libusb-1.0-0 libusb-1.0-0-dev
```

Then you can take a look at package directories by typing:

```bash
  $ > dpkg -L libusb-1.0-0-dev
```
[Websocketpp](https://www.zaphoyd.com/projects/websocketpp/) is also used for internet communication. On Mac os:

```bash
  $ > brew install websocketpp
```

On linux/Ubuntu systems :

```bash
  $ > sudo apt install libwebsocketpp-dev
  $ > sudo apt-get install libboost-all-dev
```

Other thirdparty packages are needed, but they should be automatically installed with *cmake* since they are included in the main *CMakeLists.txt* file.

* [JSON for Modern C++](https://json.nlohmann.me/);
* [FFTW](http://www.fftw.org/) for Fast Fourrier algorithms;


## Configuring

Les librairies ci-dessous doivent être correctement installées et accesibles par l'utilitaire de compilation *cmake*.
Pour vérifier cela:

```bash
  $ > pkg-config --list-all | grep libusb
  $ > pkg-config --list-all | grep jsoncpp
  $ > ls /usr/local/include/websocketpp
```

Par défaut *brew* installe les fichiers d'en-tête dans 

```bash
/usr/local/Cellar/websocketpp/0.8.2/include/websocketpp
```
Fastest Fourrier Transform in teh West
!!! warning

    Concerning websocketpp install on MacOs systems, hdf5@1.8 is keg-only, which means it was not symlinked into /opt/homebrew,
    because this is an alternate version of another formula.

    If you need to have hdf5@1.8 first in your PATH, run:

    ```bash
    $ > echo 'export PATH="/opt/homebrew/opt/hdf5@1.8/bin:$PATH"' >> ~/.zshrc
    ```
    For compilers to find hdf5@1.8 you may need to set:

    ```bash
    $ > export LDFLAGS="-L/opt/homebrew/opt/hdf5@1.8/lib"
    $ > export CPPFLAGS="-I/opt/homebrew/opt/hdf5@1.8/include"
    ```

!!! note

    The compiler may not find some include files. 
    In this case, check that your include files are in ``/usr/local/include``. 
    This is the root include directory which is defined in the default include path variable of cmake.
    If this is not the case, you can either change the cmake include path variable accordingly or add a link as below:


    ```bash
    $ > sudo ln -s /opt/homebrew/include /usr/local/include
    ``` 



## Architecture

```bash
  Megamicros_cpp
  |----- CMakeLists.txt
  |----- src
          |---- CMakeLists.txt
          |---- fonct.cpp
          |---- fonct.hpp
          |---- monct.cpp
          |---- monct.hpp
  |----- tests
          |---- CMakeLists.txt
          |---- test_xxx.cc
          |---- test_yyy.cc
  |----- apps
          |---- CMakeLists.txt
          |---- muserver
                  |---- CMakeLists.txt
                  |---- prog1.cc
                  |---- prog1.hpp
                  |---- prog2.cc
                  |---- prog2.hpp
  |----- build 
```

<figure markdown>
  ![Class hierarchy](images/Architecture_Mu32.jpg){ width="800" }
  <figcaption>Class hierarchy</figcaption>
</figure>



## Bibliography


* [CMake Tutorial](http://sirien.metz.supelec.fr/depot/SIR/TutorielCMake/)
* [Libusb](https://libusb.info/)
* [Websocketpp](https://www.zaphoyd.com/projects/websocketpp)
* [JSON for Modern C++](https://json.nlohmann.me/)
* [FFTW](http://www.fftw.org/)
* [The Fastest Fourier Transform in the West (FFTW pdf documentation)](http://www.fftw.org/fftw3.pdf)
* [Intel OneAPI c/c++](https://www.intel.com/content/www/us/en/developer/tools/oneapi/base-toolkit.html)
* [Intel OneAPI c/c++ (downloading)](https://www.intel.com/content/www/us/en/developer/tools/oneapi/base-toolkit-download.html)









