# Guide Utilisateur Megamicros v4.0

> **Documentation pour l'utilisation de la bibliothèque Python Megamicros v4.0**  
> Bibliothèque de traitement pour antennes de microphones MEMS (32 à 1024 microphones)

---

## Table des matières

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Démarrage rapide](#démarrage-rapide)
4. [Sources de données](#sources-de-données)
5. [Configuration avancée](#configuration-avancée)
6. [API détaillée](#api-détaillée)
7. [Exemples d'utilisation](#exemples-dutilisation)
8. [Migration depuis v3.x](#migration-depuis-v3x)
9. [Résolution de problèmes](#résolution-de-problèmes)

---

## Introduction

Megamicros est une bibliothèque Python pour l'acquisition et le traitement de signaux depuis des antennes de microphones MEMS. La version 4.0 introduit une architecture multi-sources tout en restant **100% compatible** avec le code v3.x.

### Principales fonctionnalités

- ✅ **Multi-sources** : USB, fichiers H5, générateur aléatoire, WebSocket
- ✅ **Temps réel** : Acquisition asynchrone avec itération non-bloquante
- ✅ **Beamforming** : Algorithmes FDAS, OMP pour localisation acoustique
- ✅ **Portabilité** : Windows, macOS, Linux
- ✅ **Type-safe** : Configuration typée avec dataclasses

---

## Installation

### Via pip (recommandé)

```bash
pip install megamicros
```

### Depuis le dépôt GitHub

```bash
git clone https://github.com/bimea/megamicros.git
cd megamicros
pip install -e .
```

### Dépendances optionnelles

```bash
# Pour le développement
pip install megamicros[dev]

# Pour WebSocket (en développement)
pip install megamicros[websocket]

# Pour les simulations acoustiques
pip install megamicros[simulation]
```

### Configuration USB (Linux uniquement)

Sur Linux, créez le fichier `/etc/udev/rules.d/99-megamicros-devices.rules` :

```bash
SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac00", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac01", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac02", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac03", MODE="0666"
```

Puis redémarrez le service udev ou reconnectez le périphérique.

---

## Démarrage rapide

### Acquisition temps réel (USB)

```python
from megamicros import Megamicros

# Créer une antenne (détection automatique USB)
antenna = Megamicros()

# Configurer et démarrer l'acquisition
antenna.run(
    mems=[0, 1, 2, 3],           # Activer les MEMS 0 à 3
    sampling_frequency=50000,     # 50 kHz
    duration=10,                  # 10 secondes
    frame_length=1024             # 1024 échantillons par trame
)

# Traiter les données en temps réel
for frame in antenna:
    # frame.shape = (4, 1024)
    process(frame)

# Attendre la fin de l'acquisition
antenna.wait()
```

### Lecture fichier H5

```python
from megamicros import Megamicros

# Lire depuis un fichier
antenna = Megamicros(filepath='recording.h5')

antenna.run(
    mems=[0, 1, 2, 3],
    frame_length=1024
)

for frame in antenna:
    analyze(frame)
```

### Tests sans matériel

```python
from megamicros import Megamicros

# Générateur aléatoire (idéal pour les tests)
antenna = Megamicros()  # Aucun hardware détecté → mode aléatoire

antenna.run(
    mems=[0, 1, 2, 3],
    sampling_frequency=44100,
    duration=5
)

for frame in antenna:
    # Données aléatoires pour tester votre pipeline
    assert frame.shape == (4, 1024)
```

---

## Sources de données

La v4.0 introduit un système de sources de données modulaire. Megamicros sélectionne automatiquement la source appropriée.

### 1. USB Hardware Source

**Utilisation :** Acquisition depuis matériel Megamicros (Mu32, Mu256, Mu1024)

```python
# Détection automatique
antenna = Megamicros()

# Ou explicite
antenna = Megamicros(usb=True)

# Avec configuration USB spécifique
from megamicros import UsbConfig
usb_config = UsbConfig(
    vendor_id=0xFE27,
    product_id=0xAC03,  # Mu1024
    buffers_number=16
)
antenna = Megamicros(usb=True)
```

**Matériel supporté :**
- Mu32-usb2 (Product ID: 0xAC00) - 32 MEMS
- Mu32-usb3 (Product ID: 0xAC01) - 32 MEMS
- Mu256 (Product ID: 0xAC02) - 256 MEMS
- Mu1024 (Product ID: 0xAC03) - 1024 MEMS

### 2. H5 File Source

**Utilisation :** Lecture de fichiers MuH5 enregistrés

```python
# Lecture simple
antenna = Megamicros(filepath='data/recording.h5')

# Avec pathlib
from pathlib import Path
antenna = Megamicros(filepath=Path('data') / 'recording.h5')
```

**Format MuH5 :**
- Format HDF5 avec structure `/muh5`
- Métadonnées : fréquence, canaux, durée
- Support vidéo (optionnel)

### 3. Random Source

**Utilisation :** Génération de signaux aléatoires pour tests

```python
# Automatique si aucun hardware/fichier
antenna = Megamicros()

# Avec graine pour reproductibilité
antenna = Megamicros(seed=42)
```

**Cas d'usage :**
- Tests unitaires sans matériel
- Développement d'algorithmes
- Validation de pipeline de traitement

### 4. WebSocket Source (🚧 En développement)

**Utilisation :** Dispositifs distants via WebSocket

```python
# Connexion à un périphérique distant
antenna = Megamicros(url='ws://remote-antenna.local:8080')

# Avec authentification
antenna = Megamicros(
    url='wss://secure-antenna.example.com',
    api_key='your-api-key'
)
```

---

## Configuration avancée

### Utilisation de AcquisitionConfig

Pour une meilleure organisation et validation, utilisez les objets de configuration :

```python
from megamicros import Megamicros, AcquisitionConfig

# Créer une configuration
config = AcquisitionConfig(
    mems=[0, 1, 2, 3, 4, 5, 6, 7],
    sampling_frequency=50000,
    frame_length=2048,
    duration=60,
    datatype='float32',
    counter=True,
    queue_size=100,
    sensibility=3.54e-6
)

# Utiliser la configuration
antenna = Megamicros()
antenna.run(**config.__dict__)

# Vérifier les valeurs calculées
print(f"Échantillons totaux : {config.total_samples}")
print(f"Nombre de trames : {config.total_frames}")
print(f"Canaux actifs : {config.active_channels}")
```

### Types de données

#### int32 (par défaut)
- Données brutes du convertisseur 24 bits
- Plage : -2²³ à 2²³-1
- Pas de conversion de sensibilité

```python
antenna.run(mems=[0,1,2,3], datatype='int32')
```

#### float32
- Conversion automatique en Pascals
- Applique le facteur de sensibilité
- Pratique pour analyse acoustique

```python
antenna.run(
    mems=[0,1,2,3], 
    datatype='float32',
    sensibility=3.54e-6  # Pa/digit
)
```

### Canal compteur

Le canal compteur permet de vérifier la continuité des données :

```python
antenna.run(
    mems=[0, 1],
    counter=True,        # Activer le compteur
    skip_counter=False   # Inclure dans les données
)

for frame in antenna:
    # frame[0] = compteur
    # frame[1:] = MEMS
    counter_value = frame[0, 0]
    print(f"Trame #{counter_value}")
```

### Gestion de la queue

```python
antenna.run(
    mems=[0,1,2,3],
    queue_size=50,       # Max 50 trames en mémoire
    queue_timeout=2000   # Timeout 2s
)

# Vérifier l'état de la queue
print(f"Trames en attente : {antenna.queue_content}")
print(f"Trames perdues : {antenna.transfert_lost}")
```

### Accumulation de frames entre acquisitions

**Important** : Depuis v4.0, les frames s'**accumulent** entre plusieurs appels à `run()` !

```python
# Première acquisition
antenna.run(mems=[0,1,2,3], duration=1.0)
antenna.wait()
print(f"Après run 1 : {antenna.queue_content} trames")  # ~43 trames

# Deuxième acquisition SANS vider la queue → accumulation !
antenna.run(mems=[0,1,2,3], duration=1.0)
antenna.wait()
print(f"Après run 2 : {antenna.queue_content} trames")  # ~86 trames

# Pour repartir de zéro, utiliser clear_queue()
cleared = antenna.clear_queue()
print(f"Vidé {cleared} trames")
```

**Comportements** :
- ✅ Queue préservée entre les `run()` → accumulation possible
- ✅ `wait()` ne vide PAS la queue → frames disponibles après
- ✅ `clear_queue()` vide explicitement → redémarrage propre
- ⚠️ Si `queue_size` change → nouvelle queue créée (frames précédentes perdues)

---

## API Détaillée

### Classe Megamicros

```python
class Megamicros:
    def __init__(
        self,
        usb: bool | None = None,
        filepath: str | Path | None = None,
        url: str | None = None,
        source: DataSource | None = None,
        vendor_id: int = 0xFE27,
        product_id: int = 0xAC03,
        **kwargs
    )
```

#### Méthode run()

```python
def run(
    self,
    mems: list[int] | None = None,
    analogs: list[int] | None = None,
    sampling_frequency: int = 44100,
    frame_length: int = 1024,
    duration: float = 0,
    datatype: str = 'int32',
    counter: bool = False,
    skip_counter: bool = False,
    queue_size: int = 0,
    queue_timeout: int = 1000,
    sensibility: float = 3.54e-6,
    **kwargs
) -> Megamicros
```

**Paramètres :**
- `mems` : Liste des MEMS actifs (défaut : tous disponibles)
- `analogs` : Liste des canaux analogiques
- `sampling_frequency` : Fréquence d'échantillonnage en Hz
- `frame_length` : Nombre d'échantillons par trame
- `duration` : Durée en secondes (0 = infini)
- `datatype` : `'int32'` ou `'float32'`
- `counter` : Activer le canal compteur
- `skip_counter` : Exclure le compteur de la sortie
- `queue_size` : Taille max de la queue (0 = illimité)
- `queue_timeout` : Timeout queue en ms
- `sensibility` : Sensibilité MEMS en Pa/digit

**Retourne :** `self` (chaînage de méthodes)

#### Méthode wait()

```python
def wait(self) -> None
```

Bloque jusqu'à la fin de l'acquisition. **Toujours appeler après itération !**

**Important** : `wait()` ne vide PAS la queue. Les frames restent disponibles pour itération après `wait()`. Utilisez `clear_queue()` pour un nettoyage explicite.

#### Méthode stop()

```python
def stop(self) -> None
```

Arrête l'acquisition prématurément.

#### Méthode clear_queue()

```python
def clear_queue(self) -> int
```

Vide la queue et retourne le nombre de trames supprimées.

**Utilisation** : Appeler avant `run()` pour repartir de zéro (sans accumulation).

```python
# Vider la queue avant une nouvelle acquisition
cleared = antenna.clear_queue()
print(f"Vidé {cleared} trames")

antenna.run(mems=[0,1,2], duration=1.0)
```

#### Itération

```python
def __iter__(self) -> Iterator[np.ndarray]
```

Itère sur les trames de données. Chaque trame est un `np.ndarray` de forme `(canaux, échantillons)`.

#### Propriétés

```python
@property
def available_mems(self) -> list[int]
    """Liste des MEMS disponibles"""

@property
def available_analogs(self) -> list[int]
    """Liste des canaux analogiques disponibles"""

@property
def mems(self) -> list[int]
    """MEMS actifs"""

@property
def sampling_frequency(self) -> int
    """Fréquence d'échantillonnage"""

@property
def frame_length(self) -> int
    """Longueur de trame"""

@property
def duration(self) -> float
    """Durée d'acquisition"""

@property
def datatype(self) -> str
    """Type de données"""

@property
def running(self) -> bool
    """État d'acquisition"""

@property
def queue_content(self) -> int
    """Nombre de trames en queue"""

@property
def transfert_lost(self) -> int
    """Nombre de trames perdues"""

@property
def infos(self) -> dict
    """Informations complètes (dict)"""
```

---

## Exemples d'utilisation

### Exemple 1 : Enregistrement simple

```python
from megamicros import Megamicros
import numpy as np

antenna = Megamicros()

# Acquisition de 10 secondes
antenna.run(
    mems=list(range(32)),  # Tous les MEMS
    sampling_frequency=50000,
    duration=10,
    frame_length=1024
)

# Stocker toutes les données
all_frames = []
for frame in antenna:
    all_frames.append(frame)

antenna.wait()

# Concaténer
signal = np.concatenate(all_frames, axis=1)
print(f"Signal complet : {signal.shape}")
```

### Exemple 2 : Traitement temps réel

```python
from megamicros import Megamicros
from scipy import signal as sp

antenna = Megamicros()

antenna.run(
    mems=[0, 1, 2, 3],
    sampling_frequency=44100,
    duration=30,
    frame_length=2048
)

# Filtre passe-bande
sos = sp.butter(4, [100, 8000], 'bandpass', fs=44100, output='sos')

for frame in antenna:
    # Filtrer chaque canal
    filtered = sp.sosfilt(sos, frame, axis=1)
    
    # Calculer l'énergie
    energy = np.mean(filtered**2, axis=1)
    print(f"Énergie : {energy}")

antenna.wait()
```

### Exemple 3 : Analyse de fichier H5

```python
from megamicros import Megamicros
import matplotlib.pyplot as plt

# Lire fichier
antenna = Megamicros(filepath='recording.h5')

print(f"MEMS disponibles : {antenna.available_mems}")

antenna.run(
    mems=[0],  # Un seul canal
    frame_length=4096
)

# Récupérer la première trame
frame = next(iter(antenna))

# Spectrogramme
plt.specgram(frame[0], Fs=antenna.sampling_frequency)
plt.colorbar()
plt.show()
```

### Exemple 4 : Beamforming

```python
from megamicros import Megamicros
from megamicros.acoustics.bmf import BeamformerFDAS
from megamicros.geometry import circle
import numpy as np

# Définir géométrie de l'antenne
mems_positions = np.array(circle(
    points_number=32,
    radius=0.175,
    height=0.0,
    angle_offset=0,
    clockwise=True
))

# Grille de localisation
x = np.linspace(-1, 1, 50)
y = np.linspace(-1, 1, 50)
X, Y = np.meshgrid(x, y)
locations = np.stack([X.ravel(), Y.ravel(), np.ones(2500)], axis=1)

# Acquisition
antenna = Megamicros()
antenna.run(
    mems=list(range(32)),
    sampling_frequency=50000,
    duration=1,
    frame_length=4096
)

# Beamformer
bf = BeamformerFDAS()
bf.setMemsPosition(mems_positions)
bf.setLocations(locations)

for frame in antenna:
    # Calculer carte acoustique
    acoustic_map = bf.run(frame, method='max')
    
    # Trouver position de la source
    max_idx = np.argmax(acoustic_map)
    source_pos = locations[max_idx]
    print(f"Source détectée : {source_pos}")

antenna.wait()
```

### Exemple 5 : Configuration réutilisable

```python
from megamicros import Megamicros, AcquisitionConfig

# Définir configuration standard
STANDARD_CONFIG = AcquisitionConfig(
    mems=list(range(8)),
    sampling_frequency=50000,
    frame_length=2048,
    datatype='float32',
    queue_size=100
)

def acquire_and_process(duration: float):
    """Acquisition avec config standard."""
    antenna = Megamicros()
    
    # Créer config dérivée
    config = AcquisitionConfig(
        **{**STANDARD_CONFIG.__dict__, 'duration': duration}
    )
    
    antenna.run(**config.__dict__)
    
    frames = []
    for frame in antenna:
        frames.append(frame)
    
    antenna.wait()
    return np.concatenate(frames, axis=1)

# Utiliser
signal_10s = acquire_and_process(10)
signal_60s = acquire_and_process(60)
```

---

## Migration depuis v3.x

### Compatibilité

**Bonne nouvelle :** Votre code v3.x fonctionne sans modification !

```python
# Code v3.x - fonctionne en v4.0
from megamicros import Megamicros

antenna = Megamicros()
antenna.run(mems=[0,1,2,3], sampling_frequency=50000)

for data in antenna:
    process(data)

antenna.wait()
```

### Nouvelles fonctionnalités v4.0

#### 1. Sources explicites

```python
# v3.x : Uniquement USB
antenna = Megamicros()

# v4.0 : Multi-sources
antenna_usb = Megamicros(usb=True)
antenna_h5 = Megamicros(filepath='data.h5')
antenna_random = Megamicros()  # Fallback aléatoire
```

#### 2. Configuration typée

```python
# v3.x : Paramètres éparpillés
antenna.run(mems=[0,1], sampling_frequency=50000, duration=10, ...)

# v4.0 : Configuration centralisée (optionnelle)
from megamicros import AcquisitionConfig

config = AcquisitionConfig(
    mems=[0, 1],
    sampling_frequency=50000,
    duration=10
)
antenna.run(**config.__dict__)
```

#### 3. Tests sans hardware

```python
# v3.x : Nécessite hardware

# v4.0 : RandomDataSource
import pytest
from megamicros import Megamicros

def test_processing_pipeline():
    antenna = Megamicros()  # Pas de hardware requis
    antenna.run(mems=[0,1,2,3], duration=0.1)
    
    for frame in antenna:
        result = my_processing_function(frame)
        assert result.shape == (4, 1024)
    
    antenna.wait()
```

### Méthodes dépréciées

Ces méthodes v3.x fonctionnent toujours mais sont dépréciées :

```python
# Déprécié (v3.x)
antenna.setActiveMems([0,1,2,3])
antenna.setDuration(10)

# Préféré (v4.0)
antenna.run(mems=[0,1,2,3], duration=10)
```

---

## Résolution de problèmes

### Erreur : "No module named 'megamicros'"

```bash
# Vérifier l'installation
pip show megamicros

# Réinstaller
pip install --upgrade megamicros
```

### Erreur : "LIBUSB_ERROR_ACCESS"

**Linux :** Configurer les règles udev (voir [Installation](#installation))

**Vérification :**
```bash
lsusb | grep fe27
# Doit afficher le périphérique Megamicros
```

### Erreur : "Cannot iterate in state IDLE"

Vous avez oublié d'appeler `run()` :

```python
# ❌ Incorrect
antenna = Megamicros()
for frame in antenna:  # Erreur !
    pass

# ✅ Correct
antenna = Megamicros()
antenna.run(mems=[0,1,2,3])
for frame in antenna:
    pass
antenna.wait()
```

### Perte de trames

Si `antenna.transfert_lost > 0`, augmentez la taille de la queue :

```python
antenna.run(
    mems=[0,1,2,3],
    queue_size=200,  # Plus grande queue
    frame_length=512  # Ou trames plus courtes
)
```

### Performance lente

- Réduire `frame_length` pour diminuer la latence
- Augmenter `queue_size` pour bufferiser
- Utiliser `datatype='int32'` (plus rapide que float32)
- Optimiser votre traitement dans la boucle

### Logs de débogage

```python
from megamicros import log

# Activer les logs détaillés
log.setLevel('DEBUG')

# Niveaux disponibles : DEBUG, INFO, WARNING, ERROR, CRITICAL
```

---

## Ressources complémentaires

- **Documentation complète :** https://readthedoc.bimea.io
- **Code source :** https://github.com/bimea/megamicros
- **Exemples :** Dossier `notebooks/` du dépôt
- **Support :** bruno.gas@bimea.io

---

**Version :** 4.0.0  
**Dernière mise à jour :** Mars 2026  
**Licence :** MIT
