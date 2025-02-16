"""
Commentaires

1) pycuda n'est pas disponible sur MacOs.

2) La macro `psutil.REALTIME_PRIORITY_CLASS` n'est pas disponible sur les systèmes MacOS.

3) Le message:
`in megamicros.log (mu.py:774): Megamicros.__callback(): from transfer[3]: data has been lost. Send a restart request...`
est un warning qui signifie que le thread d'acquisition a perdu des données (calculé par comparaison de l'état du compteur entre deux trames reçues).
A ce stade aucun 'restart request' n'est réalisé (seulement prévu dans une future release).

4) Supprimer le compteur supprime le contrôle de la perte de données. Mais COUNTER = False ne fonctionne pas -> reshape error line 612.

5) FRAME_LENGTH = 512 fonctionne mais toutes les données sont perdues. Le transfert est poursuivi, mais sans succès.  

6) DEFAULT_SAMPLING_FREQUENCY=10000Hz ne fonctionne pas (le programme tourne à l'infini).

7) QUEUE_SIZE=1 et QUEUE_MAXSIZE=0 -> pas de stockage en queue. Perte des données après 0.88s d'acquisition

8) STATUS=False -> `could not broadcast input array from shape (255,256) into shape (256,256)` line 619
 
"""
import sys
sys.path.append( '../../../' )

import sys
import time
import numpy as np
import scipy.signal as sig
from queue import Empty
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QSpinBox, QGridLayout, QFrame, QLabel
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal, QThread
from PyQt6.QtGui import QPixmap, QFont, QTransform, QColor
import pyqtgraph as pg
from megamicros.log import log
from megamicros.core.mu import Megamicros
from collections import deque
import psutil  # Add this import

DEFAULT_DURATION = 1
FRAME_LENGTH = 256
DEFAULT_MEMS_NUMBER = 256
DEFAULT_SAMPLING_FREQUENCY = 50000

QUEUE_MAXSIZE = 0 # 32
QUEUE_SIZE = 1 # 2 
LOG_LEVEL = 'DEBUG' # 'INFO'
COUNTER = True # False -> reshape error
STATUS = True

CmName = 'inferno'
ColorMap = pg.colormap.get(CmName)
FRFMems =  np.load('FRFMemsHOSMAAvg.npz')
fFRF =  FRFMems['f']
vFRF =  FRFMems['FRF']
Po = 20e-6  

WelcomeMsg = '-'*20 + '\n' + 'Mu_CtrlBoard program\n \
Copyright (C) 2024  Sorbonne University\n \
This program comes with ABSOLUTELY NO WARRANTY; for details see the source code\'.\n \
This is free software, and you are welcome to redistribute it\n \
under certain conditions; see the source code for details.\n' + '-'*20
###################aiQMainWindow################################################################### 
class Worker(QObject):
    finished = pyqtSignal()
    dataReady = pyqtSignal()

    def __init__(self, mu256ControlBoard):
        super().__init__()
        self.mu256ControlBoard = mu256ControlBoard
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            self.mu256ControlBoard.PlotOnTheFly()
            self.dataReady.emit()
        self.finished.emit()

    def stop(self):
        self.running = False

class Mu256ControlBoard(QMainWindow) : 
    def __init__(self):
        super().__init__()        
        self.Init_Params()
        self.Init_UI()     
        self.Init_Mu()
        
    def Init_Params(self) : 
        self.h5Rec = False
        self.Du = 0        
        self.Fe = 50000
        self.maxF = 2500
        self.DataFrameLength = FRAME_LENGTH
        self.NbFramesInBlock = 10
        self.Decim = 5
        self.DataBlockLength = self.DataFrameLength*self.NbFramesInBlock
        self.NOverlap = int(0.5*self.DataBlockLength)
        self.DataBufferLength = int(self.NOverlap + self.DataBlockLength)
        self.PlotDuration = 20 # s
        self.Nfft = self.DataBufferLength
        self.Fen = sig.windows.hann(self.Nfft).astype(np.float32)
        self.DataBuffer = np.zeros((DEFAULT_MEMS_NUMBER, self.DataBufferLength), dtype=np.float32)
        self.SpecgmBufferLength = int(np.round(self.PlotDuration * self.Fe / self.DataBlockLength))
        self.SignalBufferLength = int(np.round(self.PlotDuration * self.Fe ))
        self.PlottedMic = 0
        self.Compteur = 0
        self.dBMin = 50
        self.dBMax = 120  
        self.DataBuffer = np.zeros((DEFAULT_MEMS_NUMBER, self.DataBufferLength))    
    
    def Init_UI(self):
        # Create a central widget
        self.move(0,0)
        container = QWidget()
        self.setCentralWidget(container)
        self.setStyleSheet("background-color: black; color: white")

        # Create a grid layout
        MainWinLayout = QGridLayout()
        
        container.setLayout(MainWinLayout)
        ###########################################
        # Add Title Frame
        TitleFrame = QFrame()
        TtlFrameLayout = QGridLayout()
        TitleFrame.setLayout(TtlFrameLayout)
        ###########################################
        # Add Logo
        image_label = QLabel()
        pixmap = QPixmap('./Logos/LogoBimea_TransparentW.png')  # Replace with your image path
        pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        image_label.setPixmap(pixmap)        
        TtlFrameLayout.addWidget(image_label, 0, 0, 1, 1)
        ###########################################
        # Add Title
        Title = QLabel("Mµ256 Control Board")
        Title.setFont(QFont('Calibri', 40, ))
        TtlFrameLayout.addWidget(Title, 0, 1,1,2)
        ###########################################
        # Add Logo
        image_label = QLabel()
        pixmap = QPixmap('../Logos/Logo_SU-SIM_clair.png')  # Replace with your image path
        pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        image_label.setPixmap(pixmap)
        TtlFrameLayout.addWidget(image_label, 0, 3, 1, 1)        
        MainWinLayout.addWidget(TitleFrame, 0, 0, 1, 4)
        ###########################################
        # Add a frame with parameters spinboxes
        ParamFrame = QFrame()
        PrmFrameLayout = QGridLayout()
        ParamFrame.setLayout(PrmFrameLayout)

        self.SpinBoxFe = QSpinBox(prefix = 'Fe = ', value = 50, suffix = ' kHz', minimum = 1, maximum = 50, singleStep = 1)
        self.SpinBoxFe.setFont(QFont('Calibri', 10))
        self.SpinBoxFe.setFixedWidth(150)
        self.SpinBoxFe.setStyleSheet('border : black; background-color: lightgray; color: black')

        self.TrueFeLbl = QLabel()
        self.TrueFeLbl.setFont(QFont('Calibri', 10))
        self.TrueFeLbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)  
        self.TrueFeLbl.setStyleSheet('border : black; background-color: lightgray; color: red')
        self.TrueFeLbl.setFixedWidth(150)
        
        self.SpinBoxMindB = QSpinBox(prefix = 'dBMin = ', value = 50, suffix = ' ', minimum = 0, maximum = 60, singleStep = 10)
        self.SpinBoxMindB.setFont(QFont('Calibri', 10))
        self.SpinBoxMindB.setFixedWidth(150)
        self.SpinBoxMindB.setStyleSheet('border : black; background-color: lightgray; color: black')
        self.SpinBoxMindB.valueChanged.connect(self.ChangeDB)
        
        self.SpinBoxMaxdB = QSpinBox()
        self.SpinBoxMaxdB.setPrefix('dBMax = ')
        self.SpinBoxMaxdB.setSuffix(' ')
        self.SpinBoxMaxdB.setRange(60, 120)
        self.SpinBoxMaxdB.setSingleStep(10)
        self.SpinBoxMaxdB.setValue(120)
        
        self.SpinBoxMaxdB.setFont(QFont('Calibri', 10))
        self.SpinBoxMaxdB.setFixedWidth(150)
        self.SpinBoxMaxdB.setStyleSheet('border : black; background-color: lightgray; color: black')
        self.SpinBoxMaxdB.valueChanged.connect(self.ChangeDB)
        
        self.SpinBoxDu = QSpinBox(prefix = 'Record Duration = ', value = 0, suffix = ' s', minimum = 0, maximum = 60, singleStep = 1)
        self.SpinBoxDu.setFont(QFont('Calibri',10))
        self.SpinBoxDu.setFixedWidth(200)
        self.SpinBoxDu.setStyleSheet('border : black; background-color: lightgray; color: black')        
        self.SpinBoxDu.valueChanged.connect(self.ChangeDu)
        
        PrmFrameLayout.addWidget(self.SpinBoxFe, 0, 0)
        PrmFrameLayout.addWidget(self.TrueFeLbl, 0, 1)
        PrmFrameLayout.addWidget(self.SpinBoxMindB, 0, 3)
        PrmFrameLayout.addWidget(self.SpinBoxMaxdB, 0, 4)
        PrmFrameLayout.addWidget(self.SpinBoxDu, 0, 6)
        
        MainWinLayout.addWidget(ParamFrame, 1, 0, 1, 1)

        ###########################################
        # Add a frame with buttons
        ButtonFrame = QFrame()
        BtnFrameLayout = QGridLayout()
        ButtonFrame.setLayout(BtnFrameLayout)
        ButtonFrame.setFixedHeight(150)
        ButtonFrame.setFixedWidth(300)
        self.StartStopBtn = QPushButton("Start")
        self.StartStopBtn.setStyleSheet("background-color: gray; color: white")
        self.StartStopBtn.setFont(QFont('Calibri', 20))
        self.StartStopBtn.clicked.connect(self.StartStop)

        self.ExitBtn = QPushButton("Exit")
        self.ExitBtn.setStyleSheet("background-color: gray; color: white")
        self.ExitBtn.setFont(QFont('Calibri', 20))
        self.ExitBtn.clicked.connect(self.Exit)
        
        self.ResetBtn = QPushButton("Reset")
        self.ResetBtn.setStyleSheet("background-color: gray; color: white")
        self.ResetBtn.setFont(QFont('Calibri', 20))
        self.ResetBtn.clicked.connect(self.Reset)

        #############################################
        # Add Labels, RMS, Sigs and spectrogram in a frame
        #############################################
        MonitorFrame = QFrame()
        MntrFrameLayout = QGridLayout()
        MonitorFrame.setLayout(MntrFrameLayout)
        ###########################################
        # Add a frame with labels
        LabelFrame = QFrame()
        LblFrameLayout = QGridLayout()
        LabelFrame.setLayout(LblFrameLayout)
        LabelFrame.setFixedHeight(130)
        LabelFrame.setFixedWidth(300)
        
        # Lp level moyen en dB    
        LpLbl = QLabel('<html><body>L<sub>p</sub> (dB) :</body></html>')
        LpLbl.setFont(QFont('Calibri', 25, 2))
        LpLbl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)  # Center horizontally and vertically
        LpLbl.setStyleSheet("background-color:black; color: white")
        LpLbl.setFixedHeight(50)
        self.LpVal = QLabel("") 
        self.LpVal.setFont(QFont('Calibri', 25, 2))
        self.LpVal.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)  # Center horizontally and vertically
        self.LpVal.setStyleSheet("background-color:darkred; color: yellow; border: 1px solid gray")
        self.LpVal.setFixedHeight(50)
        
        # Duree de fonctionnement
        TimeLbl = QLabel("T (s) :") 
        TimeLbl.setFont(QFont('Calibri', 25, 2))
        TimeLbl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)  # Center horizontally and vertically
        TimeLbl.setStyleSheet("background-color: black; color: white")
        TimeLbl.setFixedHeight(50)
        self.TimeVal = QLabel("") 
        self.TimeVal.setFont(QFont('Calibri', 25, 2))
        self.TimeVal.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)  # Center horizontally and vertically
        self.TimeVal.setStyleSheet("background-color: darkred; color: yellow; border: 1px solid gray")
        self.TimeVal.setFixedHeight(50)

        #############################################
        # Add RMS plot
        # Leds de niveau rms des micros
        self.RMSgrph = pg.ScatterPlotItem(pxMode=False, hoverable=True, hoverPen=pg.mkPen('r',width=1), hoverSize=1)  
        Mics = []       
        for i in range(DEFAULT_MEMS_NUMBER//8):
            for j in range(8):
                Mics.append({'pos': (j,i), 'size': 0.8, 'symbol' : 's',
                                'pen': {'color': 'w', 'width': 0.5}, 
                                'brush': ColorMap.map(DEFAULT_MEMS_NUMBER)})
        
        self.RMSgrph.addPoints(Mics)
        RMSpw = pg.PlotWidget()
        RMSpw.addItem(self.RMSgrph)
        RMSpw.setAspectLocked()    
        RMSpw.setFixedWidth(300)
        RMSpw.setFixedHeight(700)        
        RMSpw.showGrid(x=True, y=True)
        RMSpw.setLabel('bottom','# Micro')
        RMSpw.setLabel('top', '# Micro')
        RMSpw.setLabel('left', '# Beam')
        RMSpw.setLabel('right', '# Beam')
        RMSpw.setTitle('Microphones RMS Level')
        RMSpw.showGrid(x=True, y=True)
        self.RMSgrph.scene().sigMouseClicked.connect(self.ChangeNumPlot)
        
        #############################################
        # Add MicsFRF plot
        self.NFreqs = int(self.Nfft / 2 + 1)
        self.Freqs = np.fft.rfftfreq(self.Nfft, 1/self.Fe) 
        self.MicsFRFpw = pg.PlotWidget()
        self.MicsFRFpw.showGrid(x=True, y=True)
        self.MicsFRFCurv = self.MicsFRFpw.plot(pen={'color' :'green', 'width' : 1})  
        self.FRFMems = self.ResampleFRFMems()
        self.MicsFRFCurv.setData(self.Freqs, 20*np.log10(self.FRFMems))    
        self.MicsFRFpw.setLabel('left','', units = 'dB')
        self.MicsFRFpw.setLabel('bottom', 'Frequency', units = 'Hz')
        self.MicsFRFpw.setTitle(f'Microphones FRF')
        self.MicsFRFpw.setXRange(min = 0, max = 20e3)
        # self.MicsFRFpw.setYRange(min = -10, max = 10)
        # self.MicsFRFpw.setFixedHeight(150)    
        # self.MicsFRFpw.setFixedWidth(300)
        
        #############################################
        # Add Signal plot
        self.tSig = np.arange(self.SignalBufferLength)/(self.Fe)
        self.Signal = np.zeros((self.SignalBufferLength,))
        self.Signpw = pg.PlotWidget()
        self.Signpw.showGrid(x=True, y=True)
        self.SignalCurv = self.Signpw.plot(pen='magenta')  
        self.SignalCurv.setData(self.tSig,self.Signal)    
        self.Signpw.setLabel('left','Pressure', units = 'Pa')
        self.Signpw.setLabel('bottom', 'time', units = 's')
        self.Signpw.setTitle(f'Signal of Microphone # {self.PlottedMic:d}')
        self.Signpw.getPlotItem().getViewBox().autoRange()
        self.Signpw.setFixedHeight(300)
        self.Signpw.setDownsampling(mode='peak')
        self.Signpw.setClipToView(True)
        
        #############################################
        # Add Spectrogram plot
        Fmax = self.Fe/2
        self.maxN = int(self.maxF/Fmax*(self.Nfft/2+1))
        self.Specgm = np.zeros((self.maxN, self.SpecgmBufferLength))
        self.Specgpw = pg.PlotWidget()
        self.Specgpw.setTitle(f'Spectrogram of Microphone # {self.PlottedMic:d}')
        self.Specgpi = self.Specgpw.getPlotItem()
        self.Specgii = pg.ImageItem(self.Specgm)
        ScaleX = self.PlotDuration/self.SpecgmBufferLength
        ScaleY = self.maxF/self.maxN
        transform = QTransform()
        transform.scale(ScaleX, ScaleY)
        self.Specgii.setTransform(transform)
        self.Specgii.setPos(0,0)
        self.Specgpi.addItem(self.Specgii)
        self.Specgii.setColorMap(pg.colormap.get('inferno'))  # Set the color map
        self.Specgpw.setXLink(self.Signpw)
        self.Specgpw.showGrid(x=True, y=True)
        self.Specgpw.setYRange(min = 0, max = self.maxF)
        self.Specgpw.setLabel('left','frequency', units =  'Hz')
        self.Specgpw.setLabel('bottom', 'time',units = 's')
        self.Specgpw.setFixedHeight(300)
        self.Specgpw.setClipToView(True)
        
        # #############################################
        # Add octave spectrum plot
        self.OBands, _, OCntrFrqsLbl = self.Init_OctaveSpectrum() 
        self.OLvls = np.zeros(len(OCntrFrqsLbl))
        OBrushesList = [QColor('darkmagenta')]*10 + [QColor('darkred')]
        self.Octavbgi = pg.BarGraphItem(x=np.arange(len(OCntrFrqsLbl)), height=self.OLvls, width=0.9, 
                                        brushes=OBrushesList)
        self.Octavpw = pg.PlotWidget()
        self.Octavpw.addItem(self.Octavbgi)
        self.Octavpw.setLabel('left','Level', units = 'dB')
        self.Octavpw.setLabel('bottom', 'Frequency', units = 'Hz')
        self.Octavpw.setTitle(f'Octave Spectrum of Mic # {self.PlottedMic:d}')
        self.Octavpw.showGrid(x = True, y = True)
        self.Octavpw.setYRange(min = 0, max = self.dBMax)
        ticks = [(i, label) for i, label in enumerate(OCntrFrqsLbl)]
        x_axis = self.Octavpw.getAxis('bottom')
        x_axis.setTicks([ticks])      
        self.Octavpw.setFixedHeight(200)
        self.Octavpw.setFixedWidth(300)

        BtnFrameLayout.addWidget(self.StartStopBtn, 0, 0)
        BtnFrameLayout.addWidget(self.ExitBtn, 1, 0 )
        BtnFrameLayout.addWidget(self.ResetBtn, 2, 0 )

        LblFrameLayout.addWidget(LpLbl,         0, 0) 
        LblFrameLayout.addWidget(self.LpVal,    0, 1)        
        LblFrameLayout.addWidget(TimeLbl,       1, 0)       
        LblFrameLayout.addWidget(self.TimeVal,  1, 1)
                
        MntrFrameLayout.addWidget(RMSpw,            0, 0, 4, 1)
        MntrFrameLayout.addWidget(self.MicsFRFpw,   0, 1)
        MntrFrameLayout.addWidget(ButtonFrame,      1, 1)
        MntrFrameLayout.addWidget(LabelFrame,       2, 1)
        MntrFrameLayout.addWidget(self.Octavpw,     3, 1)
        MntrFrameLayout.addWidget(self.Signpw,      0, 2, 2, 1)
        MntrFrameLayout.addWidget(self.Specgpw,     2, 2, 2, 1)
                
        MainWinLayout.addWidget(MonitorFrame,   2, 0)

    ######################################################################
    def Init_Mu(self):
        log.setLevel( LOG_LEVEL )
        #Define an empty Mu
        self.Mu = Megamicros()
        if self.Mu.system_type.name =='mu256':
            self.MemsNumber = 256
            self.mems = [i for i in range(self.MemsNumber)]
        else :
            print('Uncompatible System !')
            exit()

        self.Mu.setAvailableMems( self.mems )
        self.NbBeams = self.MemsNumber//8     
    
    
    def Init_OctaveSpectrum(self):
        OCntrFrqs = np.array([31.5, 63, 125,  250, 500, 1000, 2000,  4000, 8000, 16000, 100000])
        OCntrFrqsLbl = ['31','63', '125','250','500','1k','2k','4k','8k','16k','All']        
        OBands = []
        for f in OCntrFrqs[:-1] :        
            OBands.append((f / (2 ** (1/2)), f * (2 ** (1/2))))
        return OBands, OCntrFrqs, OCntrFrqsLbl
        
    def Process_OctaveSpectrum(self):      
        OBandsLevel = []
        for band in self.OBands:
                band_mask = (self.Freqs >= band[0]) & (self.Freqs <= band[1])
                band_level = np.sum(np.abs(self.Specg[band_mask]) ** 2)
                if band_level > 0 :
                    OBandsLevel.append(10 * np.log10(band_level/Po**2))
                else: 
                    OBandsLevel.append(0)
        OverAllLvl = 10*np.log10(np.sum(np.abs(self.Specg+Po) ** 2)/20e-6**2)
        OBandsLevel.append(OverAllLvl)
        return np.array(OBandsLevel)
        
    ######################################################################    
    def LaunchMu(self) :     
        self.ChangeFe()
        self.Mu.run( 
            mems = self.mems,						                        # activated mems
            duration = self.SpinBoxDu.value(),
            counter = COUNTER,
            analogs = [0],						                        # activated analogs
            sampling_frequency = self.SpinBoxFe.value()*1000,					
            status = STATUS,
            h5_recording = self.h5Rec,
            frame_length = FRAME_LENGTH,
            verbose = False,
            queue_maxsize = QUEUE_MAXSIZE,
            queue_size = QUEUE_SIZE
        )
        self.Fe = self.Mu.sampling_frequency
        self.ChangeFe()
    
    ######################################################################
    def ResampleFRFMems(self):
        FRFMems = np.load('FRFMemsHOSMAAvg.npz')
        FRFMemsfreqs = FRFMems['f']
        FRFMemsVals = FRFMems['FRF']
        FRFMemsVals = [f for f in FRFMemsVals if f < self.Fe / 2]
        NewFRFMems = sig.resample(FRFMemsVals, int(self.NFreqs)).astype(np.float32) + 0.905
        fcb = 500
        indices = np.where(self.Freqs < fcb)       
        #NewFRFMems[indices] *=np.exp(1-self.Freqs[indices]/fcb)+1
        # print(NewFRFMems[indices])
        #self.MicsFRFCurv.setData(self.Freqs, 20*np.log10(NewFRFMems))    
        self.MicsFRFCurv.setData(self.Freqs, (NewFRFMems))    

        return NewFRFMems
    
    ######################################################################
    def StartStop(self):
        if not self.Mu.running:
            self.DataFrameLength = FRAME_LENGTH  # or your desired initial value

            self.SignalCurv.setData(self.tSig, np.zeros_like(self.tSig))
            if self.SpinBoxDu.value():
                self.h5Rec = True
                self.StartStopBtn.setStyleSheet("background-color: black; color: black")
                self.StartStopBtn.setEnabled(False)
            else:
                self.h5Rec = False
                self.StartStopBtn.setText('Stop')
                self.StartStopBtn.setStyleSheet("background-color: gray; color: white")
                self.StartStopBtn.setEnabled(True)
            self.SpinBoxFe.setEnabled(False)
            self.SpinBoxDu.setEnabled(False)
            self.ExitBtn.setEnabled(False)
            self.ExitBtn.setStyleSheet("background-color: black; color: black")
            self.LaunchMu()

            self.thread = QThread()
            self.worker = Worker(self)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.dataReady.connect(self.updateUI)

            self.thread.start()

            self.StartStopBtn.setEnabled(True)
            self.StartStopBtn.setStyleSheet("background-color: gray; color: white")
            self.ExitBtn.setEnabled(True)
            self.ExitBtn.setStyleSheet("background-color: gray; color: white")
            self.SpinBoxFe.setEnabled(True)
            self.SpinBoxDu.setEnabled(True)
            self.t0 = time.time()

        else:  # Stop
            self.worker.stop()
            self.thread.quit()
            self.thread.wait()
            self.Mu.stop()

    def updateUI(self):
        self.UpdateRMS()
        self.UpdateSignal()
        self.UpdateTime()
        self.SMABlock2Spec()
        self.UpdateSpectrogram()
        self.UpdateOctaveSpectrum()

    ######################################################################
    def Exit(self):
        if self.Mu.running:
            self.Mu.stop()
        sys.exit()

    ######################################################################        
    def Reset(self):
        self.Mu.stop()
        self.Mu = Megamicros()
        self.ChangeFe() 
        self.StartStopBtn.setText('Start')
        self.StartStopBtn.setEnabled(True)
           
    ######################################################################
    def ChangeNumPlot(self,event):        
        x,y = int(np.round(event.pos().x())),int(np.round(event.pos().y()))    
        if y < self.NbBeams and y >= 0 and x < 8 and x >= 0:         
            self.PlottedMic = y*8+x
            self.Signpw.setTitle(f'Signal of Microphone # {self.PlottedMic:d}')
            self.Octavpw.setTitle(f'Octave Spectrum of Mic # {self.PlottedMic:d}')
            self.Specgpw.setTitle(f'Spectrogram of Microphone # {self.PlottedMic:d}')   
            print(f'Beam {y:d} Mic {x:d} selected')                  
    
    ######################################################################
    def ChangeFe(self):        
        self.Fe = self.Mu.sampling_frequency
        self.TrueFeLbl.setText(f" --> {self.Mu.sampling_frequency*1e-3:.1f} kHz")
        self.maxF = np.min((2500, self.Fe/2))   
        self.DataFrameLength = FRAME_LENGTH
        self.DataBlockDuration = self.DataBlockLength / self.Fe
        self.tSig = np.arange(int(self.PlotDuration *self.Fe))/self.Fe 
        self.SignalBufferLength = int(self.PlotDuration * self.Fe)
        self.SpecgmBufferLength = int(self.SignalBufferLength/self.DataBlockLength)
        self.Nfft = self.DataBufferLength
        self.Fen = sig.windows.hann(self.Nfft).astype(np.float32)
        
        ScaleX = self.PlotDuration/self.SpecgmBufferLength
        ScaleY = self.maxF/self.maxN
        transform = QTransform()
        transform.scale(ScaleX, ScaleY)
        self.Specgii.setTransform(transform)
        self.Specgii.setPos(0,0)       
       
        self.NFreqs = int(self.Nfft / 2 + 1)
        self.FRFMemsResampled = self.ResampleFRFMems() + 0.905
        self.Specgm = np.zeros((self.NFreqs, self.SpecgmBufferLength), dtype=np.float32)
        self.Specgii.setImage(self.Specgm, levels = [self.dBMin, self.dBMax])
        self.Signal = np.zeros((self.SignalBufferLength,), dtype=np.float32)
        self.Freqs = np.fft.rfftfreq(self.Nfft,1/self.Fe).astype(np.float32)
        self.Compteur = 0     
        self.Start = True  
        
    ######################################################################
    def ChangeDu(self):        
        self.Du = self.SpinBoxDu.value()
    
    ######################################################################
    def ChangeDB(self):        
        self.dBMin = self.SpinBoxMindB.value()
        self.dBMax = self.SpinBoxMaxdB.value()
        self.Specgii.setImage(self.Specgm.T, levels = [self.dBMin, self.dBMax] ) 
    
    ######################################################################
    def UpdateRMS(self) : 
        Lvl = np.std(self.DataBuffer, 1) + Po     
        LvldB = 20*np.log10(Lvl/Po)
        NormLvldB = (np.array(LvldB) - self.dBMin)/(self.dBMax-self.dBMin)
        Brsh = np.array(ColorMap.map(NormLvldB))
        self.RMSgrph.setBrush(Brsh)
        AvgRMS = np.mean(Lvl[Lvl != 0])
        AvgdB = int(20*np.log10( AvgRMS /Po))
        self.LpVal.setText(f"{int(AvgdB):d}")
    
    ######################################################################
    def UpdateTime(self):
        self.delta = time.time() - self.t0    
        self.TimeVal.setText(f"{self.delta:.1f}")              
    
    ######################################################################
    def UpdateSpectrogram(self): 
        self.Specg = np.abs(self.Spec[self.PlottedMic,:])**2 / (self.DataFrameLength)
        self.Specgm[:, :-1] = self.Specgm[:, 1:]
        self.Specgm[:, -1] = 10*np.log10((self.Specg + Po**2) / Po**2)
        self.Specgpw.setYRange(min = 200, max = self.maxF)
        self.Specgii.setImage(np.flipud(self.Specgm.T), levels = [self.dBMin, self.dBMax] ) 
    
    ######################################################################
    def UpdateOctaveSpectrum(self):
        self.OLvls = self.Process_OctaveSpectrum()
        self.Octavbgi.setOpts(height = self.OLvls) 
        
    ######################################################################
    def UpdateSignal(self) :
        self.Signal[:-self.DataBlockLength] = self.Signal[self.DataBlockLength:]
        self.Signal[-self.DataBlockLength:] = self.DataBuffer[self.PlottedMic,-self.DataBlockLength:]
        self.SignalCurv.setData(self.tSig[::self.Decim], np.flip(self.Signal[::self.Decim]))
        max = np.max(np.abs(self.Signal))
        max = np.max((0.5,max))
        self.Signpw.setYRange(min = -max, max = max)
        
     ######################################################################
    def SMABlock2Spec(self) :
        self.Spec = np.fft.rfft(self.DataBuffer * self.Fen, self.Nfft) / self.FRFMemsResampled[None, :]
    
    ######################################################################
    def PlotOnTheFly(self): 
        try:
            self.DataBuffer[:, :int(self.DataBlockLength/2)] = self.DataBuffer[:, int(-self.DataBlockLength/2):]
            for i in range(self.NbFramesInBlock):
                #print(i)
                offset = i * self.DataFrameLength +int(self.DataBlockLength/2)
                self.DataBuffer[:, offset:offset+self.DataFrameLength] = self.Mu.queue.get(block=True, timeout=1)[1:-2, :]*self.Mu.sensibility  # Attempt to get data from the queue
                        
        except Empty:  # Handle the case where the queue is empty
            print('Empty Queue')
         
        if self.Mu.running :     
            self.UpdateRMS()
            self.UpdateSignal()
            self.UpdateTime()
            self.SMABlock2Spec()
            self.UpdateSpectrogram()
            self.UpdateOctaveSpectrum()    
        
        if not self.Mu.running :     
            self.StartStopBtn.setText('Start')
            self.StartStopBtn.setEnabled(True)
            self.StartStopBtn.setStyleSheet("background-color: gray; color: white")
            self.ExitBtn.setText('Exit')
            self.ExitBtn.setEnabled(True)
            self.ExitBtn.setStyleSheet("background-color: gray; color: white")    
            self.SpinBoxFe.setEnabled(True) 
            self.SpinBoxDu.setEnabled(True)
        
######################################################################
if __name__ == '__main__':
    import platform
    os_name = platform.system()

    # Set the process priority to real-time
    # there is no REALTIME_PRIORITY_CLASS const available in psutil for macos systems
    if os_name == 'Windows':
        p = psutil.Process()
        p.nice(psutil.REALTIME_PRIORITY_CLASS)
    
    app = QApplication(sys.argv)
    MainWin = Mu256ControlBoard()
    MainWin.show()
    sys.exit(app.exec())