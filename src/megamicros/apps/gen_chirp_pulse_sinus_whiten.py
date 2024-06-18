
# Create a wav file with a sinusoidal signal of 5 seconds duration.

import numpy as np
from scipy.io.wavfile import write, read
from scipy.signal import chirp
import matplotlib.pyplot as plt

def main():
    # Paramètres
    duration = 5  # Durée en secondes
    freq = 1000  # Fréquence du signal en Hz
    sample_rate = 44100  # Taux d'échantillonnage en Hz

    # Générer le temps des échantillons
    t = np.arange(sample_rate * duration)

    # Générer le signal sinusoïdal
    y_s = 0.5 * np.sin(2 * np.pi * freq * t / sample_rate)

    # Générer le bruit blanc
    y_b = np.random.normal(0, 0.5, sample_rate * duration)

    # get impulsional signal
    fs, y_i  = read( 'Rafale_Pulse_10k.wav' )

    # create chirp signal
    duration = 5  # Durée en secondes
    f0 = 20  # Fréquence de départ en Hz
    f1 = 10000  # Fréquence de fin en Hz
    sample_rate = 44100  # Taux d'échantillonnage en Hz

    # Générer le temps des échantillons
    t = np.linspace(0, duration, sample_rate * duration, False)

    # Générer le signal chirp
    y_c = chirp(t, f0, duration, f1, method='linear')

    y = np.concatenate((y_s, y_b))
    y = np.concatenate((y_c, y))
    # y = np.concatenate((y_i, y))

    # Écrire le fichier wav
    write('gen_chirp_pulse_sinus_whiten.wav', sample_rate, y)

    # Tracer le signal
    plt.figure()
    plt.plot(y)
    plt.title('Signal final')
    plt.xlabel('Échantillons')
    plt.ylabel('Amplitude')
    plt.show()

    input( "Press Enter to continue...")
    plt.close()


if __name__ == "__main__":
    main()

