# Frame Accumulation Between Runs - v4.0 Behavior

## Question Initiale

**"If run many times cell 3, frames in queue are not added. Is this what you wanted: to not cumulate between runs?"**

## Réponse

**NON** - Le comportement a été modifié suite à votre feedback. Maintenant les frames **s'accumulent** entre les runs !

---

## Comportement Actuel (v4.0)

### Queue Préservée Entre Runs

```python
from megamicros import Megamicros

antenna = Megamicros()

# Run 1
antenna.run(mems=[0,1,2], duration=0.5)
antenna.wait()
print(antenna.queue_content)  # → 22 frames

# Run 2 SANS clear_queue() → accumulation !
antenna.run(mems=[0,1,2], duration=0.5)
antenna.wait()
print(antenna.queue_content)  # → 44 frames (22 + 22)

# Run 3
antenna.run(mems=[0,1,2], duration=0.5)
antenna.wait()
print(antenna.queue_content)  # → 66 frames (22 + 22 + 22)
```

### `wait()` Préserve la Queue

```python
antenna.run(duration=1.0)
antenna.wait()  # Attend la fin, mais garde les frames

# Les frames sont TOUJOURS disponibles
for frame in antenna:
    print(f"Frame: {frame.shape}")
```

### `clear_queue()` pour Redémarrer

```python
# Si vous voulez repartir de zéro
antenna.clear_queue()

antenna.run(duration=1.0)
antenna.wait()
print(antenna.queue_content)  # → ~43 frames (nouveau)
```

---

## Avantages de l'Accumulation

✅ **Flexibilité** : Combiner plusieurs acquisitions courtes
```python
# Acquérir 10 segments de 0.1s
for i in range(10):
    antenna.run(duration=0.1)
    antenna.wait()

# Toutes les frames sont disponibles
print(f"Total: {antenna.queue_content} frames")
```

✅ **Pas de perte de données** : Si vous oubliez de consommer les frames
```python
antenna.run(duration=1.0)
antenna.wait()
# Oups, j'ai oublié d'itérer...

antenna.run(duration=1.0)  # Les frames précédentes sont toujours là !
antenna.wait()
```

✅ **Contrôle explicite** : `clear_queue()` quand vous voulez
```python
antenna.clear_queue()  # Redémarrer proprement
antenna.run(duration=1.0)
```

---

## Exception : Changement de `queue_size`

Si vous changez `queue_size` entre deux runs, une **nouvelle queue** est créée :

```python
antenna.run(queue_size=50, duration=0.5)
antenna.wait()
# queue_content = 22 frames

antenna.run(queue_size=100, duration=0.5)  # ⚠️ Nouvelle queue
antenna.wait()
# queue_content = 22 frames (les anciennes sont perdues)
```

**Warning** affiché dans les logs :
```
Queue size changed (50→100) - previous frames lost
```

---

## Implémentation

### RandomDataSource

**Avant** (ancien comportement) :
```python
def _do_configure(self, config: AcquisitionConfig) -> None:
    # Clear queue from any previous run
    while not self._queue.empty():
        try:
            self._queue.get_nowait()
        except queue.Empty:
            break
```

**Après** (nouveau comportement) :
```python
def _do_configure(self, config: AcquisitionConfig) -> None:
    # NOTE: Queue is NOT cleared - frames accumulate between runs!
    # Use Megamicros.clear_queue() to manually discard frames if needed.
```

### UsbDataSource

**Avant** (ancien comportement) :
```python
def _do_configure(self, config: AcquisitionConfig) -> None:
    # Setup queue
    self._queue = queue.Queue(maxsize=config.queue_size)  # ← Nouvelle queue
```

**Après** (nouveau comportement) :
```python
def _do_configure(self, config: AcquisitionConfig) -> None:
    # Setup queue (recreate only if size changed)
    if config.queue_size != self._queue_size:
        old_size = self._queue_size
        self._queue = queue.Queue(maxsize=config.queue_size)
        self._queue_size = config.queue_size
        if old_size > 0:
            log.warning(f"Queue size changed ({old_size}→{config.queue_size}) - previous frames lost")
    # NOTE: If queue_size unchanged, queue is preserved (frames accumulate)!
```

---

## Tests

### Test 1 : Accumulation Simple

```bash
$ python test_frame_accumulation.py
=== First run (0.5s) ===
Queue content after run 1: 22 frames

=== Second run (0.5s) WITHOUT clear_queue() ===
Queue content after run 2: 44 frames
✨ Expected ~44 frames per run → total ~88 frames

✅ Frames now ACCUMULATE between runs!
```

### Test 2 : UX Improvements

```bash
$ python test_ux_improvements.py
Test 3: wait() keeps frames...
  ✓ wait() completed (frames available for iteration)
  ✓ Retrieved 44 frames after wait()
  ✓ Test passed!

All tests passed! ✨
```

---

## Résumé

| Comportement | v3.x | v4.0 (avant) | v4.0 (après) |
|-------------|------|--------------|--------------|
| **Frames entre runs** | ❌ Perdues | ❌ Perdues | ✅ **Accumulées** |
| **`wait()` vide queue** | ❌ Non | ❌ Non | ❌ Non |
| **`clear_queue()` disponible** | ❌ Non | ✅ Oui | ✅ Oui |
| **Contrôle utilisateur** | ⚠️ Limité | ⚠️ Moyen | ✅ **Total** |

---

## Recommandations

### Pattern 1 : Acquisition Unique
```python
antenna.clear_queue()  # ← Recommandé
antenna.run(duration=1.0)
for frame in antenna:
    process(frame)
antenna.wait()
```

### Pattern 2 : Accumulation Multiple
```python
# Acquérir plusieurs segments
for i in range(5):
    antenna.run(duration=0.2)
    antenna.wait()

# Traiter toutes les frames d'un coup
all_frames = [frame for frame in antenna]
```

### Pattern 3 : Consommation Continue
```python
antenna.run(duration=10.0)  # Long

# Consommer en temps réel
for frame in antenna:
    process_realtime(frame)

antenna.wait()  # Toujours appeler !
```

---

**Date** : 7 mars 2026  
**Version** : Megamicros v4.0.0-dev  
**Auteur** : Bruno Gas <bruno.gas@bimea.io>
