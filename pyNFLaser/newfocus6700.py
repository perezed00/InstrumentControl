import numpy as numpy
import sys
import time
import ipdb
import numpy as np

import os
try:
    import clr
    clr.AddReference(r'mscorlib')
    from System.Text import StringBuilder
    from System import Int32
    from System.Reflection import Assembly
except:
    pass
import ipdb

path = os.path.realpath('../')
if not path in sys.path:
    sys.path.insert(0, path)
from pyDecorators import InOut, ChangeState


class NewFocus6700(object):
    '''
    Class for Newfocus 67xx laser control through USB with proper 
    usb driver installed. 
    
    Args:
        key: laser DeviceKey 
        id:  laser id
    Methods:
        Open: open laser instance
        Close: close laser instance
    Properties (Fetch/Set):
        self.connected: laser connection active or no
        self.output: ON/OFF output state of the laser
        self.lbd :float: laser wavelength in nm
        self.current :float: laser current in A
        self.scan_limt :[float, float]: DC scan limit in nm
        self.scan_speed :float: DC scan speed in nm
        self.scan :bool: dc scan status
        self.beep :bool: set/disabel beep
        self.error :(read only): fetch error laser and wipe
        self.identity :(read only): fetch laser identity
    Utilities:
        self._open: flag if opening of laser successful 
        self._dev : laser usb socket
        self._buff : buffer reading the laser status
        self._is_changing_lbd : track if wavelength is still 
                                changing after the user set a
                                wavelength
        self._is_scaning : track in background if the scan is 
                           still ongoing
        self._lbdscan: fetch in background the laser lbd during
                       a scan

    Example:
        import time
        import numpy as np
        import matplotlib.pyplot as plt
        from NewFocus6700 import NewFocus6700

        idLaser = 4106
        DeviceKey = '6700 SN10027'
        laser = NewFocus6700(id =idLaser, key = DeviceKey)
        laser.connected = True
        old_lbd = laser.lbd
        print('Laser wavelength:')
        print("\t{}".format(old_lbd))
        laser.scan_lim = [1520, 1550]
        laser.scan_speed = 10
        laser.lbd = laser.scan_lim[0]
        print('waiting until laser parked at correct lbd')
        while laser._is_changing_lbd:
            time.sleep(0.25)
        print('Current wavelength:')
        print('\t{}nm'.format(laser.lbd))
        laser.output = True
        t = np.array([])
        lbd = np.array([])
        print('Starting scan')
        laser.scan = True
        while laser._is_scaning:
            t = np.append(t, time.time())
            lbd = np.append(lbd, laser._lbdscan)
        laser.output = False
        print('Ploting')
        f, ax = plt.subplots()
        ax.plot(t-t[0], lbd)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Wavelength (nm)')
        f.show()
    ''' 

    __author__ = "Gregory Moille"
    __copyright__ = "Copyright 2018, NIST"
    __credits__ = ["Gregory Moille",
                   "Xiyuan Lu",
                   "Kartik Srinivasan"]
    __license__ = "GPL"
    __version__ = "1.0.0"
    __maintainer__ = "Gregory Moille"
    __email__ = "gregory.moille@mist.gov"
    __status__ = "Development"

    def __init__(self, **kwargs):
        super(NewFocus6700, self).__init__()
        # Load usb ddl Newport
        try:

            dllpath = 'C:\\Anaconda3\\DLLs\\'
            Assembly.LoadFile(dllpath + 'UsbDllWrap.dll')
            clr.AddReference(r'UsbDllWrap')
            import Newport
            self._dev = Newport.USBComm.USB()
        except:
            self._dev = None
        # Laser state
        self._open = False
        self._DeviceKey = kwargs.get('key', None)
        self._idLaser = kwargs.get('id', None)
        # Laser properties
        self._lbd = '0'
        self._cc = 0
        self._scan_lim = []
        self._scan_speed = 0
        self._scan = 0
        self._beep = 0
        self._output = 0
        self._is_scaning = False
        self._is_changing_lbd = False
        instr._no_error = '0....'
        # Miscs
        self._buff = StringBuilder(64)

    # -- Decorators --
    # ---------------------------------------------------------
    def Checkopen(fun):
        def wrapper(*args, **kwargs):
            self = args[0]
            # if self._open and self._DeviceKey:
            if self._open and self._DeviceKey:
                out = fun(*args, **kwargs)
                return out
            else:
                pass
        return wrapper

    # -- Methods --
    # ---------------------------------------------------------

    def Querry(self, word):
        self._buff.Clear()
        self._dev.Query(self._DeviceKey, word , self._buff)
        return self._buff.ToString()


    # -- Properties --
    # ---------------------------------------------------------
    @property
    @InOut.output(bool)
    def connected(self):
        return self._open

    @connected.setter
    @InOut.accepts(bool)
    def connected(self,value):
        # ipdb.set_trace()
        if value:
            if self._DeviceKey:
                try: 
                    out = self._dev.OpenDevices(self._idLaser, True)
                    dum = self._dev.Query('',self._DeviceKey, self._buff)
                    if out :
                        self._open = True
                        print('Laser Connected')
                except:
                    pass
            time.sleep(0.2)
        else:
            self._dev.CloseDevices()
            self._open = False

    @property
    @InOut.output(bool)
    def output(self):
        word = 'OUTPut:STATe?'
        self._output = self.Querry(word)
        return self._output

    @output.setter
    @InOut.accepts(bool)
    def output(self,value):
        word = "OUTPut:STATe {}".format(int(value))
        self.Querry(word)
        self._output = value

    @property
    @InOut.output(float)
    def lbd(self):
        word = 'SENSe:WAVElength?'
        self._lbd = self.Querry(word)
        return self._lbd

    @lbd.setter
    @ChangeState.lbd
    @InOut.accepts(float)
    def lbd(self, value):
        self._targetlbd = value
        self.Querry('OUTP:TRACK 1')
        word =  'SOURCE:WAVE {}'.format(value)
        self.Querry(word)
        self._lbd = value

    @property
    @InOut.output(float)
    def current(self):
        word = ''
        self._cc = self.Querry(word)
        return self._cc

    @current.setter
    @InOut.accepts(float)
    def current(self, value):
        word = ''.format(value)
        self._cc = value

    @property
    @InOut.output(float,float)
    def scan_limit(self):
        word1 = 'SOUR:WAVE:START?'
        word2 = 'SOUR:WAVE:STOP?'
        self._scan_lim = [self.Querry(word1),
                        self.Querry(word2)]
        return self._scan_lim

    @scan_limit.setter
    @InOut.accepts(list)
    def scan_limit(self, value):
        start = value[0]
        stop = value[1]
        word1 = 'SOUR:WAVE:START {}'.format(start)
        self.Querry(word1)
        word2 = 'SOUR:WAVE:STOP {}'.format(stop)
        self.Querry(word2)
        self._scan_lim = value

    @property
    @InOut.output(float,float)
    def scan_speed(self):
        word1 = 'SOUR:WAVE:SLEW:FORW?'
        word2 = 'SOUR:WAVE:SLEW:RET?'
        self._scan_speed = [self.Querry(word1),
                        self.Querry(word2)]
        return self._scan_speed

    @scan_speed.setter
    @InOut.accepts(float)
    def scan_speed(self, value):
        word = 'SOUR:WAVE:SLEW:FORW {}'.format(value)
        self.Querry(word)
        word = 'SOUR:WAVE:SLEW:RET {}'.format(0.1)
        self.Querry(word)
        self._scan_speed = value

    @property
    @InOut.output(float)
    def scan(self):
        word = 'SOUR:WAVE:DESSCANS?'
        self._scan = self.Querry(word)
        return self._scan

    @scan.setter
    @ChangeState.scan("OUTPut:SCAN:START",'OUTPut:SCAN:STOP')
    @InOut.accepts(bool)
    def scan(self, value):
        self.Querry('SOUR:WAVE:DESSCANS 1')
        self._scan = value
        if self._scan:
            self.Querry("OUTPut:SCAN:START")
        else:
            self.Querry("OUTPut:SCAN:STOP")


    @property
    @InOut.output(float)
    def pzt(self):
        word = 'SOUR:VOLT:PIEZ?'
        self._pzt = self.Querry(word)
        return self._pzt

    @pzt.setter
    @InOut.accepts(float)
    def pzt(self, value):
        word = 'SOUR:VOLT:PIEZ {}'.format(value)
        self.Querry(word)
        self._pzt = value

    @property
    @InOut.output(bool)
    def beep(self):
        word = 'BEEP?'
        self._beep = self.Querry(word)
        return self.beep

    @beep.setter
    @InOut.accepts(bool)
    def beep(self, value):
        word = 'BEEP '.format(int(value))
        self.Querry(word)
        self._beep = value

    @property
    def identity(self):
        word = "*IDN?"
        self._id = self.Querry(word)
        return self._id

    @property
    def error(self):
        word = 'ERRSTR?'
        self._error = self.Querry(word)
        return self._error


if __name__ == '__main__':
    idLaser = 4106
    DeviceKey = '6700 SN10027'
    laser = NewFocus6700(id =idLaser, key = DeviceKey)
    laser.beep = False
    laser.connected = True
    old_lbd = laser.lbd
    print('Laser wavelength:')
    print("\t{}".format(old_lbd))