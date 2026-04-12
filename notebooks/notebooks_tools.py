import numpy as np
import matplotlib.pyplot as plt

def plot_signal(signal, sampling_frequency):
    time = np.arange(signal[0,:].shape[0]) / sampling_frequency
    plt.figure(figsize=(12, 6))
    for i in range(signal.shape[0]):
        plt.plot(time, signal[i,:] + i*0.5, label=f'MEMS {i}')  # Offset for visibility
    plt.title('Acquired Signal from All MEMS')
    plt.xlabel('Time (s)')
    plt.ylabel('Amplitude (offset for visibility)')
    plt.legend()
    plt.grid()
    plt.show()