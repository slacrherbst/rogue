#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue protocols / UART register protocol
#-----------------------------------------------------------------------------
# File       : pyrogue/protocols/_uart.py
# Created    : 2017-01-15
#-----------------------------------------------------------------------------
# Description:
# Module containing protocol modules
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import rogue.interfaces.memory
import pyrogue
import serial

class UartMemory(rogue.interfaces.memory.Slave):
    def __init__(self, device, timeout=1, **kwargs):
        super().__init__(4,4) # Set min and max size to 4 bytes

        self._log = pyrogue.logInit(cls=self, name=f'{device}')
        self.serialPort = serial.Serial(device, timeout=timeout, **kwargs)

    def close(self):
        self.serialPort.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


    def _doTransaction(self, transaction):
        with transaction.lock():

            # Create the command string
            if transaction.type() == rogue.interfaces.memory.Write:
                data = bytearray(transaction.size())
                transaction.getData(data, 0)
                data = int.from_bytes(data, 'little', signed=False)
                sendString = f'w {transaction.address():08x} {data:08x} \n'
                self._log.debug(f'Sending write transaction: {repr(sendString)}')
                
            elif transaction.type() == rogue.interfaces.memory.Read:
                sendString = f'r {transaction.address():08x} \n'
                self._log.debug(f'Sending read transaction: {repr(sendString)}')

            else:
                # Posted writes not supported (for now)
                transaction.done(rogue.interfaces.memory.Unsupported)
                self._log.error(f'Unsupported transaction type: {transaction.type()}')
                return
                
            # Send the command and wait for response
            self.serialPort.write(sendString)
            response = self.serialPort.readline()

            # If response is empty, a timeout occured
            if len(response == 0):
                transaction.done(rogue.interfaces.memory.TimeoutError)
                self._log.error('Empty transaction response (likely timeout) for transaction: {repr(sendString)}')
                return

            # parse the response string
            parts = response.split()
            if transaction.type() == rogue.interfaces.memory.Write:
                # Check for correct response
                if (len(parts) != 2 or
                    parts[0].lower() != 'w' or
                    int(parts[1], 16) != transaction.address()):
                    transaction.done(rogue.interfaces.memory.ProtocolError)
                    self._log.error('Malformed response: {repr(response)} to transaction: {repr(sendString)}')
                else:
                    transaction.done(0)
                    self._log.debug('Transaction: {repr(sendString)} completed successfully')
                    
            else: # if (transaction.type() == rogue.interfaces.memory.Read
                if (len(parts) != 3 or
                    parts[0].lower() != 'r' or
                    int(parts[1], 16) != transaction.address()):
                    transaction.done(rogue.interfaces.memory.ProtocolError)
                    self._log.error('Malformed response: {repr(response)} to transaction: {repr(sendString)}')                    
                else:
                    rdData = int(parts[2], 16)
                    transaction.setData(rdData.to_bytes(4, 'little', signed=False))
                    transaction.done(0)
                    self._log.debug('Transaction: {repr(sendString)} with response data: {rdData:#08x} completed successfully')

