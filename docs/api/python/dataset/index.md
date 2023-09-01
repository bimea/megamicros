# Dataset

Les *Dataset* désignent des bases de données de signaux exploitables pour la réalisation d'apprentissages machine. 
*Aidb* permet de créer puis de télécharger des Dataset

## Structuration des données dans un Dataset

Les *Dataset* pour les signaux beamformés sont des fichiers *HDF5* (extension .h5) qui peuvent contenir:

* les signaux brutes issus des microphones d'une antenne n'ayant subi aucun traitement préalable
* les signaux beamformés, c'est à dire reconstruits après une étape de beamforming

Le Dataset comporte un ensemble de méta-données:

* les informations d'acquisition (fréquence d'édhantillonnage, etc.);
* les informations de segmentation (début et fin des trames);
* les informations d'étiquetage lorsque les signaux sont labellisés.

Les fichiers générés au format *.h5* par *Aidb* ont des noms qui prennent la forme suivante:

```bash
    mudset-<code_du_dataset>-YYYYMMDD-HHMMSS.h5
```

où ``<code_du_dataset>`` désigne le code donné au dataset lotrs de sa création et ``YYYYMMDD-HHMMSS`` désigne la date de création du dataset.


### Arborescence

Les fichiers H5 comportent par convention un premier groupe racine appelé ``mudset``.
Les attributs de ce groupe racine sont les méta-données du dataset:

```python
    {
        'mudset': {                 # main group
            'attrs': {              # main group attributs
                'name': '',
                'code': '',
                'domain': '',
                'labels': [],
                'channels': [],
                'crdate': 'creation_date',
                'timestamp': 123456,
                'labels_number': 0,
                'channels_number': 0,
                'records_number': 0,
                'sampling_frequency': 0,
                'sample_width': 0
            }
        }
    }
```

Chaque label se voit associer un sous-groupe dédié. 
Au sein de ce sous-groupe sont créés autant de sous-groupes que d'examples à sauvegarder et pour chaqun des examples, un ou plusieurs dataset sont créés pour les signaux.
Pour un label dont le code est ``label1``: 

```python
    {
        'mudset': {
            'label1': {             # label1 sub-group
                'attrs': {          # label1 sub-group attributs
                    'rn': 0,        # records number
                },
                '0': {              # record 0 sub-sub-group
                    'attrs': {      # record 0 attributs
                        'sn': 0,    # samples number
                        'sw': 0,    # sample width in bytes [optionnal]
                        'sf': 0,    # sampling frequency [optionnal]
                    }
                    'raw': []       # raw signal dataset
                }
            }
        }
    }
```

Relativement aux formats des signaux, deux cas de figurent peuvent se présenter: les enregistrements sont de types différents (en fréquence d'échantillonage et/ou en quantification ), ou de même type.
Dans le premier cas les attributs ``sd`` et/ou ``sw`` des datasets sont positionnés avec les bonnes valeurs. 
Dans le deuxième cas, seuls les attributs du groupe racine sont positionnés. 

#### Exemple de lecture d'un *Dataset*

```python
    import numopy as numpyimport h5py
    import matplotlib.pyplot as plt

    f = h5py.File('mudset-dataset13-20230107-171412.h5')
    list(f.keys())
    # ['mudset']
    list( f['mudset'].keys() )
    # ['label1']
    list( f['mudset'].attrs )
    # ['channels_number', 'code', 'crdate', 'domain', 'labels_number', 'name', 'records_number', 'sample_width', 'sampling_frequency', 'timestamp']
    dict( f['mudset'].attrs )
    # {'channels_number': 2, 'code': 'dataset13', 'crdate': '2023-01-07 17:14:12.296461', 'domain': 'Elevage porcin', 'labels_number': 1, 'name': 'dataset13', 'records_number': 1, 'sample_width': False, 'sampling_frequency': False, 'timestamp': 1673111652.296461}
    print( f['mudset'].attrs )
    list( f['mudset']['label1']['0'].keys() )
    #n ['raw']
    list( f['mudset']['label1'].attrs )
    # ['rn']
    print( f['mudset']['label1'].attrs['rn'] )
    # 1
    frame = f['mudset']['label1']['0']['raw']
    np.size(frame)
    # 33884
```

```python
    import numpy as np
    import h5py
    import matplotlib.pyplot as plt

    f = h5py.File( 'dataset14.h5' )
    frame = f['mudset']['label1']['0']['raw']

    meta_data = dict( f['mudset'].attrs )
    sampling_frequency = meta_data['sampling_frequency']
    channels_number = meta_data['channels_number']
    samples_number = int( np.size(frame) / channels_number )
    time = np.array( range( samples_number) )/sampling_frequency

    sampling_frequency = 10000.0
    print( 'sampling_frequency=', sampling_frequency )
    print( 'size(frame)=', np.shape( frame ) )

    if channels_number > 1:
        signals = np.reshape( frame, (channels_number, samples_number))
        
        fig, axs = plt.subplots( channels_number )
        fig.suptitle('Mems activity')
        for s in range( channels_number ):
            axs[s].plot( time, signals[s,:] )
            axs[s].set( xlabel='time in seconds', ylabel='mic %d' % s )

    else:
        fig, ax = plt.subplots()
        fig.suptitle('Mems activity')
        ax.plot( time, frame[0,:] )

    plt.show()
```
