# Comprehensive introduction to the Delay and Sum beamforming algorithm

Let us consider the signal emitted by a monopolar source $s_0(t)$.
The distance from the source to the microphone $m$ is $R_{s_0m}=|\mathbf{r}_m-\mathbf{r}_{s_0}|$ where $\mathbf{r}_m$ and $\mathbf{r}_{s_0}$ are the respective spatial position of the microphone and the source.

The received signal at microphone $m$ can be writen as:

$$
    p_m(t) = s_0(t) \star \frac{\delta(t-\frac{R_{s_0m}}{c})}{R_{s_0m}} = \frac{s_0(t-\frac{R_{s_0m}}{c})}{R_{s_0m}}
$$

The corresponding signal spectrum is :

$$
    p_m(f) = s_0(f)\frac{e^{-{2\pi jf\frac{R_{s_0m}}{c}}}}{R_{s_0m}}
$$

Removing the propagation delay from the source to the microphone need to add a phase shift :

$$
    p_m(f)e^{2\pi jf\frac{R_{s_0m}}{c}} = s_0(f)\frac{e^{-{2\pi fj\frac{R_{s_0m}}{c}}}}{R_{s_0m}}e^{2\pi jf\frac{R_{s_0m}}{c}} = \frac{1}{R_{s_0m}}s_0(f)
$$

Considering now $N$ microphones pointing to a space location $\mathbf{r}_s$. Somming over all the $M$ antena microphones gives:

$$
    \hat{S}(s, f) = \sum_{m=1}^M p_m(f)e^{2\pi j f\frac{R_{sm}}{c}}
$$

If a source $s_0$ is at the location, one as:

$$
    \hat{S}(s=s_0, f) \simeq \frac{M}{R_{s_0m}}s_0(f)
$$

If no source:

$$
    \hat{S}(s\neq s_0, f) \overset{M \rightarrow \infty}{\longrightarrow} \alpha E[e^{—2\pi jf\beta}]  = 0
$$

Where $\alpha$ is an attenuator coeficient related to the distances to sources.

## Vectorial formulation

One as $M$ signal frames comming from the $M$ microphones. $M$ spectra are estimated on the incomming frames.
Let us consider the vector $\mathbf{p}$ of the $M$ pressures for a given frequency $f$:

$$
    \mathbf{p}(f) = \left[ \begin{array}{l}
        p_1 \\
        p_2 \\
        \ldots \\
        p_M
    \end{array}\right]
$$

Consider now $N$ space locations where we want to estimate the spectrum. 
The distance matrix $D$ that gives the distances between microphones and locations is:

$$
    \mathbf{D} = \left[ \begin{array}{llll}
        D_{1,1} & D_{1,2} & \ldots & D_{1,M} \\
        D_{2,1} & D_{2,2} & \ldots & D_{2,M} \\
        D_{3,1} & & & \\
        \ldots  & & & \\
        D_{N,1} & & & \\
    \end{array}\right]
$$

where $D_{i,j} = |\mathbf{r}_{m_j} - \mathbf{r}_{s_i}|$ is the distance between the space location $\mathbf{s}_i$ and the microphone $\mathbf{m}_j$

The beamformer matrix at frequency $f$ is given by:

$$
    \mathbf{H}(f) = e^{2\pi j \frac{f}{c} \mathbf{D}}
$$

By multiplying one pressure vector $\mathbf{p}$ by one line $i$ of the $\mathbf{H}$ beamformer matrix, one as for the location $\mathbf{r}_i$:

$$
\begin{eqnarray}
    [H_{i,1}, H_{i,2}, \ldots, H_{i,M}]_{(f)}
    \left[ \begin{array}{l}
        p_1 \\
        p_2 \\
        \ldots \\
        p_M
    \end{array}\right]
    & = &
    \sum_{m=1}^M p_m(f) H_{i,m}(f) = \sum_{m=1,f}^M p_m(f)  e^{2\pi j \frac{f}{c} D_{i,m}} \\
    & = &
    \sum_{m=1}^M p_m(f)  e^{2\pi j \frac{f}{c} R_{s_im}} \\
    & = &
    \left\{ \begin{array}{l}
        \alpha s_i(f) \mbox{ if there is a source $s_i$ at the location $\mathbf{r}_i$} \\
        \simeq 0 \mbox{ if not }
    \end{array} \right.
\end{eqnarray}
$$

Denoting $\mathbf{s}$ as the vector of all the source locations in the sources space, one can compute the sources estimated spectra at 
frequency $f$ by:
$$
    \mathbf{s}(f) = \mathbf{H}(f) \mathbf{p}(f)
$$

At frequency $f$, the location can be given by finding the maximum energy:

$$
    l = \operatorname*{argmax}_{i=1,N} \{ || s_i(f) || \}
$$


## The algorithm

The beamforming algorithm is defined as one of the built-in callback functions, both in the Python library and the C++ library.

## The MVDR beamformer

Source : [6] (the exact method)

The DOA estimating requires to compute the module of every beamformed channel:

$$
    \|\textbf{s}(f)\|^2 = \| \mathbf{H}(f) \mathbf{p}(f) \|^2
$$

so as to find the channel by finding the maximum energy. One as:

\begin{aligned}
    \|\textbf{s}(f)\|^2 &= ( \mathbf{H}(f)^\top \mathbf{p}(f) )(\mathbf{H}(f)^\top \mathbf{p}(f))^\top \\
    &= ( \mathbf{H}(f)^\top \mathbf{p}(f) )( \mathbf{p}(f)^\top \mathbf{H}(f) ) \\
    &=  \mathbf{H}(f)^\top \Phi_{pp}  \mathbf{H}(f)
\end{aligned}

$\top$ denotes the Hermitian transpose that states for complex numbers.

To obtain an optimal beamformer we have to minimize the power spectrum of the output given by 
$\phi_{ss} = \mathbf{H}\Phi_{pp}\mathbf{H}$, where  $\phi_{ss}$ is the auto-spectral density matrix of the noisy inputs. 
In order to avoid the trivial solution, $\mathbf{H} = 0$, we use the distortionless criterion, $\mathbf{H}^\top D = 1$, which demands that in the absence of noise, the output of the MVDR beamformer
must equal with the desired signal.

The weight vector $\mathbf{H}$ emerging from the solution of this constrained min-
imization problem, corresponds to the MVDR or superdirective beamformer
and is given by:

$$
    \mathbf{H} = \frac{D^\top \Phi^{-1}_{vv}}{D^\top \Phi^{-1}_{vv}D}
$$


## Spectral aliasing problem

See [4] (p. 426).

Spatial aliasing occurs when the aperture of the array is not adequately sampled in space by the sensors for a given wavelength. It is the same effect occurring in the time domain when the sampling frequency does not satisfy Shannon’s theorem. However, if time domain aliasing error can be avoided by applying anti-aliasing filters, an analogous process cannot apply in spatial domain. A spatial undersampling of the array aperture results in the inability to distinguish between multiple directions of arrival. In an acoustic map, this effect yields ghost sources of levels similar as the true sources. Severe aliasing problem always occurs in regular arrays (e.g. square lattice arrays), also called redundant arrays, because of the repeated sampling spacing. One option to reduce spatial aliasing is to spatially sample at an interval that does not exceed one-half wavelength (Nyquist rate). Since this is sometimes impractical because of the considerable sensor count to meet the Nyquist criterion, other options are adopted. Indeed, in order to significantly reduce spatial aliasing, microphone arrays must guarantee non-redundancy in spatial sampling. This can be achieved by using non-redundant arrays with almost unique intra–sensor spacings (also known as vector spacings). This strategy leads to the class of arrays known as irregular or aperiodic arrays.

## Array calibration

See [4] (p. 429).

When dealing with acoustic beamforming, three calibration steps should be considered:

* microphone sensitivity calibration;
* array calibration;
* in-situ calibration.

Microphone sensitivity calibration consists in the standard measurement of microphone sensitivity using the pressure comparison method described in IEC 61094-5, in which each microphone is fed with a known broadband or single frequency pressure level.

Microphone array calibration has the main objectives of labeling each microphone channel, assessing and correcting the inter-microphone phase delay [38], estimating the directivity response of the entire array [39] and identifying the position of the installed microphones [40]. Indeed, small differences between the theoretical and the actual microphone location affect the beamforming result. This is particularly important in the high frequency range (i.e. at 80 kHz, a typical working range in wind tunnel aeroacoustic applications based on airplane models) where an error of few millimeters is comparable to the source wavelength.
The strength of acoustic beamforming is related to the ‘‘cooperation” between microphones rather than to the quality of each single sensor, and a calibration procedure that checks the whole array is highly advisable. However, when the count of sensors becomes large, the calibration step could be extremely time consuming. Muller proposed an array calibration procedure [13] based on the reproduction of a white noise monopole source, by means of a small loudspeaker, placed nearby the
expected source location. The CSM obtained from this measurement step is then used to fully remove systematic differences between microphones and partially correct the effect of sensor positioning errors, at least for sources near to the calibration source.

Finally, it is highly advisable to perform an in-situ calibration [41]. There are at least two main reasons for such final step: it makes it possible to check differences in microphone locations after the final installation of the array (the antenna can indeed undergo damages/deformations that nullify the previous calibration); it takes into account also the test environment and its influence on wave propagation. In wind tunnel applications the in-situ calibration is performed by placing a monopole source inside an anechoic emi-enclosure that avoids reflections so that only the direct path is observed by the array.


# Autocalibrating

In what follows, the positions of the microphones are no more known.
Considering two microphones $m_1$ and $m_2$ with their proper shift that should be estimated suche that $p'_{m_1}(f) = p'_{m_2}(f)$ with:

$$
    p'_m(f) = p_m(f)e^{2\pi jf\frac{D_{sm}}{c}}
$$

One can define the quadratic error:

$$
    Q_{m_1,m_2} = \|  p'_{m_2}(f) - p'_{m_1}(f) \| = \| p_{m_2}(f)e^{\frac{D_{sm_2}}{c}} - p_{m_1}(f)e^{\frac{D_{sm_1}}{c}} \|
$$

In details, $D_{sm}=| \textbf{r}_m - \textbf{r}_s|$.
By adding the antena position:

$$
    D_{sm}=| ( \textbf{r}_m - \textbf{r}_a ) - (\textbf{r}_s - \textbf{r}_a ))|
    = \sqrt{ |\textbf{r}_m - \textbf{r}_a|^2 + |\textbf{r}_s - \textbf{r}_a|^2 -2( \textbf{r}_m - \textbf{r}_a )(\textbf{r}_s - \textbf{r}_a )}
$$

# The spectral aliasing problem

MEMS distance size is 0.06 meters. Spatial period is then $p=0.06$ meters and time period is:

$$
    \tau = \frac{p}{c}
$$

Then the maximum freqency is given by:

$$
    F_{m} = \frac{1}{2\tau} = \frac{c}{2p} = \frac{340}{0.12} = 2833 Hz
$$

Audio signal with frequencies over than 2833Hz are subject to the oversampling problem.

# Bibliographie

* [MVDR Beamforming: A Tutorial](https://nateanl.github.io/2021/07/21/mvdr-tutorial/)
* [Speech Enhancement with MVDR Beamforming (PyTorch)](https://pytorch.org/audio/main/tutorials/mvdr_tutorial.html)
* [A Generalized Estimation Approach for Linear and Nonlinear Microphone Array Post-Filters](https://hal.science/hal-00499179/document)
* [4] Acoustic beamforming for noise source localization – Reviews, methodology and applications, Paolo Chiariotti a, Milena Martarelli b, Paolo Castellini a.
* [Adaptive beamformer](https://en.wikipedia.org/wiki/Adaptive_beamformer)
* [6] Formation de voies: détermination du vesteur de pointage (Pascal2009.pdf)



