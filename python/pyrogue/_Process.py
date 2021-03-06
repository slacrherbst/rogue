#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Process Device Class
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import threading
import time
import pyrogue as pr

class Process(pr.Device):
    """Special base class to execute processes."""

    def __init__(self, *, argVariable=None, **kwargs):

        pr.Device.__init__(self, **kwargs)

        self._lock   = threading.Lock()
        self._thread = None
        self._runEn  = False
        self._argVar = argVariable

        self.add(pr.LocalCommand(
            name='Start',
            function=self._startProcess,
            description='Start process.'))

        self.add(pr.LocalCommand(
            name='Stop',
            function=self._stopProcess,
            description='Stop process.'))

        self.add(pr.LocalVariable(
            name='Running',
            mode='RO',
            value=False,
            pollInterval=1.0,
            description='Operation is running.'))

        self.add(pr.LocalVariable(
            name='Progress',
            mode='RO',
            units='Pct',
            value=0.0,
            disp = '{:1.2f}',
            minimum=0.0,
            maximum=1.0,
            pollInterval=1.0,
            description='Percent complete: 0.0 - 1.0.'))

        self.add(pr.LocalVariable(
            name='Message',
            mode='RO',
            value='',
            pollInterval=1.0,
            description='Process status message. Prefix with Error: if an error occurred.'))

    def _startProcess(self):
        with self._lock:
            if self.Running.value() is False:
                self._runEn  = True
                self._thread = threading.Thread(target=self._run)
                self._thread.start()
            else:
                self._log.warning("Process already running!")

    def _stopProcess(self):
        with self._lock:
            self._runEn  = False

    def _stop(self):
        self._stopProcess()
        pr.Device._stop(self)

    def __call__(self,arg=None):
        with self._lock:
            if self.Running.value() is False:
                if arg is not None and self._argVar is not None:
                    self.nodes[self._argVar].setDisp(arg)

                self._runEn  = True
                self._thread = threading.Thread(target=self._run)
                self._thread.start()
            else:
                self._log.warning("Process already running!")

        return None

    def _run(self):
        self.Running.set(True)

        try:
            self._process()
        except Exception as e:
            pr.logException(self._log,e)

        self.Running.set(False)

    def _process(self):
        self.Message.setDisp("Started")
        for i in range(101):
            if self._runEn is False:
                break
            time.sleep(1)
            self.Progress.set(i/100)
            self.Message.setDisp(f"Running for {i} seconds.")
        self.Message.setDisp("Done")
