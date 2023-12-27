
# plot_antenna.py python program example for MegaMicros devices 
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
Plot an antenna geometry from a json file descriptor

MegaMicros documentation is available on https://readthedoc.biimea.io
"""

welcome_msg = '-'*20 + '\n' + 'plot_antenna program\n \
Copyright (C) 2023  Sorbonne University\n \
This program comes with ABSOLUTELY NO WARRANTY; for details see the source code\'.\n \
This is free software, and you are welcome to redistribute it\n \
under certain conditions; see the source code for details.\n' + '-'*20

import argparse
import numpy as np
import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

JSON_FILENAME = 'antenna.json'

def arg_parse() -> tuple:

    parser = argparse.ArgumentParser()
    parser.add_argument( "-f", "--filename", help=f"json filename" )
    args = parser.parse_args()

    filename = JSON_FILENAME
    if args.filename:
        filename = args.filename

    return filename


def plot_points( vectors ):
    fig = plt.figure()

    # Créer un tracé 3D
    ax = fig.add_subplot(111, projection='3d')

    # Tracer chaque point
    max_x = max_y = max_z = 0
    xmin = vectors[0][0]
    for vector in vectors:
        if vector[0] < xmin:
            xmin = vector[0]
        if vector[1] < xmin:
            xmin = vector[1]
        if vector[2] < xmin:    
            xmin = vector[2]

        if vector[0] > max_x:
            max_x = vector[0]
        if vector[1] > max_y:    
            max_y = vector[1]
        if vector[2] > max_y:
            max_z = vector[2]
        ax.scatter(vector[0], vector[1], vector[2])

    # Définir les limites du tracé
    ax.set_xlim([xmin, max_x])
    ax.set_ylim([xmin, max_y])
    ax.set_zlim([xmin, max_z])

    # Afficher le tracé
    plt.show()


def plot_vectors( vectors ):
    fig = plt.figure()

    # Créer un tracé 3D
    ax = fig.add_subplot(111, projection='3d')

    # Tracer chaque vecteur
    for vector in vectors:
        ax.quiver(0, 0, 0, vector[0], vector[1], vector[2])

    # Définir les limites du tracé
    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1])
    ax.set_zlim([0, 1])

    # Afficher le tracé
    plt.show()


def main():

    filename = arg_parse()

    print( welcome_msg )

    try:
        with open( filename ) as f:
            vectors = json.load(f)
            plot_points( vectors )

    except Exception as e:
        print( f'Failed to check json file: {e}' )
        exit()




if __name__ == "__main__":
	main()
