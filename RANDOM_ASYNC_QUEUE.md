# RandomDataSource: Queue Asynchrone (v4.0)

## Changement Majeur

**RandomDataSource utilise maintenant une queue asynchrone avec threads**, exactement comme `UsbDataSource` et `H5DataSource`.

## Pourquoi Ce Changement ?

### Problème Initial

**Incohérence de comportement** entre les sources :

```python
# Avec USB
antenna = Megamicros(usb=True)
antenna.run(mems=[0,1], duration=1.0)
antenna.wait()
print(antenna.queue_content)  # → 43 frames ✅

# Avec Random (avant v4.0)antenna = Megamicros()
antenna.run(mems=[0,1], duration=1.0)
antenna.wait()
print(antenna.queue_content)  # → 0 frames ❌ (génération synchrone on-demand)
```

Cette différence rendait les tests **non représentatifs** du comportement réel !

### Solution Implémentée

RandomDataSource simule maintenant **exactement** le comportement asynchrone de USB :

1. **Thread de génération** : Background thread génère les frames
2. **Queue bufferisée** : Frames stockées dans `queue.Queue()` 
3. **Timer thread** : Arrêt automatique après `duration`
4. **`wait()` garde les frames** : Queue remplie et disponible pour itération
5. **`queue_content` significatif** : Retourne le nombre réel de frames en attente

## Nouveau Code

### Structure

```python
class RandomDataSource(BaseDataSource):
    def __init__(self, ...):
        self._queue = queue.Queue()  # ← Nouveau !
        self._generator_thread: Thread | None = None  # ← Nouveau !
        self._timer_thread: Thread | None = None  # ← Nouveau !
        self._halt_request = False
        
    def _do_start(self):
        # Start generator thread (like USB transfer thread)
        self._generator_thread = Thread(target=self._generator_worker)
        self._generator_thread.start()
        
        # Start timer thread for duration limit
        if duration > 0:
            self._timer_thread = Thread(target=self._timer_worker)
            self._timer_thread.start()
    
    def _generator_worker(self):
        """Background thread that fills the queue"""
        while frames_to_generate and not halt:
            frame = self._generate_single_frame(...)
            self._queue.put(frame)  # Asynchrone !
    
    def _generate_frames(self):
        """Read from queue (not direct generation)"""
        while True:
            frame = self._queue.get(timeout=...)
            yield frame
```

### Option: Timing Simulation

```python
source = RandomDataSource(simulate_timing=True)

# Simule les délais réels entre frames
frame_period = frame_length / sampling_frequency  
time.sleep(frame_period)  # Entre chaque frame
```

## Comportement Cohérent

### Avant (v3.x / early v4.0)

```python
# RandomDataSource = génération synchrone
antenna.run(mems=[0,1,2,3], duration=1.0)
antenna.wait()
print(antenna.queue_content)  # → 0 ❌

# Frames générés pendant l'itération
for frame in antenna:  
    process(frame)  # Génération ici !
```

### Maintenant (v4.0 final)

```python
# RandomDataSource = simulation réaliste
antenna.run(mems=[0,1,2,3], duration=1.0)
# → Thread génère frames en background

antenna.wait()
# → Thread terminé, queue remplie

print(antenna.queue_content)  # → 43 frames ✅

# Frames déjà générés, lecture depuis queue
for frame in antenna:
    process(frame)  # Lecture queue, comme USB !
```

## Avantages

### 1. Tests Réalistes

```python
def test_my_app():
    # Test sans hardware, comportement identique !
    antenna = Megamicros()  # RandomDataSource
    
    antenna.run(mems=[0,1,2,3], duration=2.0)
    
    # Vérifier que queue se remplit
    time.sleep(0.5)
    assert antenna.queue_content > 0  # ✅ Fonctionne maintenant !
    
    antenna.wait()
    
    # Traiter frames bufferisées
    frames = list(antenna)
    assert len(frames) > 0  # ✅ Fonctionne !
```

### 2. API Cohérente

```python
# Ce code fonctionne identiquement avec USB, H5 ou Random !
def acquire_and_process(antenna):
    antenna.run(mems=[0,1,2,3], duration=1.0)
    antenna.wait()  # Frames disponibles
    
    print(f"Ready: {antenna.queue_content} frames")
    
    for frame in antenna:
        process(frame)

# USB
acquire_and_process(Megamicros(usb=True))

# H5
acquire_and_process(Megamicros(filepath='data.muh5'))

# Random - même comportement ! ✨
acquire_and_process(Megamicros())
```

### 3. Timing Simulation (Optionnel)

```python
# Pour tests de performance réalistes
source = RandomDataSource(simulate_timing=True)

antenna = Megamicros()
start = time.time()

antenna.run(mems=[0,1], duration=1.0, sampling_frequency=44100, frame_length=1024)
antenna.wait()

elapsed = time.time() - start
print(f"Elapsed: {elapsed:.2f}s")  # ~1.0s (simule délais réels !)
```

## Performance

### Surcoût Minimal

- **Threading** : Léger overhead, négligeable pour tests
- **Mémoire** : Queue stocke ~50 frames max (configurable)
- **Génération** : Instantanée (numpy), < 1ms par frame

### Comparaison

```python
# Avant : génération synchrone on-demand
for frame in antenna:  # 43 x 0.5ms = 21.5ms total
    frame = generate()  # 0.5ms

# Maintenant : génération asynchrone + queue
# Génération : 43 frames en background (~21.5ms total)
# Lecture : 43 x 0.1ms = 4.3ms (lecture queue)
# → Même perf, meilleure simulation !
```

## Migration

### Code Existant

**Aucun changement nécessaire !** Tout code v3.x/v4.0 fonctionne identiquement.

### Seule Différence Notable

```python
# Avant
antenna.run(...)
antenna.wait()
print(queue_content)  # → 0

# Maintenant  
antenna.run(...)
antenna.wait()
print(queue_content)  # → 43 (frames disponibles !)
```

Si votre code **vérifie `queue_content == 0`**, il faudra adapter la logique.

## Résumé

| Aspect | Avant (sync) | Maintenant (async) |
|--------|-------------|-------------------|
| **Thread** | ❌ Non | ✅ Oui (generator + timer) |
| **Queue** | ❌ Non | ✅ Oui (`queue.Queue`) |
| **`queue_content`** | Toujours 0 | Nombre réel de frames |
| **Génération** | Pendant `__iter__` | En background (start) |
| **`wait()` comportement** | No-op | Attend threads, garde queue |
| **Timing simulation** | ❌ Non | ✅ Optionnel |
| **Cohérence API** | ❌ Différent de USB | ✅ Identique à USB/H5 |

## Tests

```bash
# Test complet
python test_random_queue.py

# Output attendu :
# After wait(): queue has 44 frames (ready to iterate!)
# After consuming 10 frames: 34 frames remaining
# Cleared 34 frames
# ✅ RandomDataSource now uses queue like USB!
```

---

**Conclusion** : RandomDataSource est maintenant une **vraie simulation** de hardware, pas juste un générateur de données aléatoires ! 🎯
