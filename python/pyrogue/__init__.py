#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module
#-----------------------------------------------------------------------------
# File       : pyrogue/__init__.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-09-29
# Last update: 2016-09-29
#-----------------------------------------------------------------------------
# Description:
# Module containing the top functions and classes within the pyrouge library
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
import textwrap
import yaml
import threading
import time
import math
import collections
import datetime
import traceback

def streamConnect(source, dest):
    """
    Attach the passed dest object to the source a stream.
    Connect source and destination stream devices.
    source is either a stream master sub class or implements
    the _getStreamMaster call to return a contained master.
    Similiarly dest is either a stream slave sub class or implements
    the _getStreamSlave call to return a contained slave.
    """

    # Is object a native master or wrapped?
    if isinstance(source,rogue.interfaces.stream.Master):
        master = source
    else:
        master = source._getStreamMaster()

    # Is object a native slave or wrapped?
    if isinstance(dest,rogue.interfaces.stream.Slave):
        slave = dest
    else:
        slave = dest._getStreamSlave()

    master._setSlave(slave)


def streamTap(source, tap):
    """
    Attach the passed dest object to the source for a streams
    as a secondary destination.
    Connect source and destination stream devices.
    source is either a stream master sub class or implements
    the _getStreamMaster call to return a contained master.
    Similiarly dest is either a stream slave sub class or implements
    the _getStreamSlave call to return a contained slave.
    """

    # Is object a native master or wrapped?
    if isinstance(source,rogue.interfaces.stream.Master):
        master = source
    else:
        master = source._getStreamMaster()

    # Is object a native slave or wrapped?
    if isinstance(tap,rogue.interfaces.stream.Slave):
        slave = tap
    else:
        slave = tap._getStreamSlave()

    master._addSlave(slave)


def streamConnectBiDir(deviceA, deviceB):
    """
    Attach the passed dest object to the source a stream.
    Connect source and destination stream devices.
    source is either a stream master sub class or implements
    the _getStreamMaster call to return a contained master.
    Similiarly dest is either a stream slave sub class or implements
    the _getStreamSlave call to return a contained slave.
    """

    """
    Connect deviceA and deviceB as end points to a
    bi-directional stream. This method calls the
    streamConnect method to perform the actual connection. 
    See streamConnect description for object requirements.
    """

    streamConnect(deviceA,deviceB)
    streamConnect(deviceB,deviceA)


def busConnect(source,dest):
    """
    Connect the source object to the dest object for 
    memory accesses. 
    source is either a memory master sub class or implements
    the _getMemoryMaster call to return a contained master.
    Similiarly dest is either a memory slave sub class or implements
    the _getMemorySlave call to return a contained slave.
    """

    # Is object a native master or wrapped?
    if isinstance(source,rogue.interfaces.stream.Master):
        master = source
    else:
        master = source._getMemoryMaster()

    # Is object a native slave or wrapped?
    if isinstance(dest,rogue.interfaces.stream.Slave):
        slave = dest
    else:
        slave = dest._getMemorySlave()

    master._setSlave(slave)


class VariableError(Exception):
    """ Exception for variable access errors."""
    pass


class NodeError(Exception):
    """ Exception for node manipulation errors."""
    pass


class Node(object):
    """
    Class which serves as a managed obect within the pyrogue package. 
    Each node has the following public fields:
        name: Global name of object
        description: Description of the object.
        hidden: Flag to indicate if object should be hidden from external interfaces.
        classtype: text string matching name of node sub-class
        path: Full path to the node (ie. node1.node2.node3)

    Each node is associated with a parent and has a link to the top node of a tree.
    A node has a list of sub-nodes as well as each sub-node being attached as an
    attribute. This allows tree browsing using: node1.node2.node3
    """

    def __init__(self, name, description, hidden, classType):
        """Init the node with passed attributes"""

        # Public attributes
        self.name        = name     
        self.description = description
        self.hidden      = hidden
        self.classType   = classType
        self.path        = self.name

        # Tracking
        self._parent = None
        self._root   = self
        self._nodes  = collections.OrderedDict()

    def add(self,node):
        """Add node as sub-node"""

        # Names of all sub-nodes must be unique
        if node.name in self._nodes:
            raise NodeError('Error adding %s with name %s to %s. Name collision.' % 
                             (node.classType,node.name,self.name))

        # Attach directly as attribute and add to ordered node dictionary
        setattr(self,node.name,node)
        self._nodes[node.name] = node

        # Update path related attributes
        node._updateTree(self)

    def _updateTree(self,parent):
        """
        Update tree. In some cases nodes such as variables, commands and devices will
        be added to a device before the device is inserted into a tree. This call
        ensures the nodes and sub-nodes attached to a device can be updated as the tree
        gets created.
        """
        self._parent = parent
        self._root   = self._parent._root
        self.path    = self._parent.path + '.' + self.name

        for key,value in self._nodes.iteritems():
            value._updateTree(self)

    def _getNodeAtPath(self,path):
        """
        Return node at given path, recursing when neccessary.
        Called from getAtPath in the root node.
        """
        if not '.' in path:
            node = path
            rest = None
        else:
            node = path[:path.find('.')]
            rest = path[path.find('.')+1:]

        if node not in self._nodes:
            return None
        elif rest:
            return self._nodes[node]._getNodeAtPath(rest)
        else:
            return self._nodes[node]

    def _getStructure(self):
        """
        Get structure starting from this level.
        Attributes that are Nodes are recursed.
        Called from getDictStructure in the root node.
        """
        data = {}
        for key,value in self.__dict__.iteritems():
            if not key.startswith('_'):
                if isinstance(value,Node):
                    data[key] = value._getStructure()
                else:
                    data[key] = value

        return data

    def _getVariables(self,modes):
        """
        Get variable values in a dictionary starting from this level.
        Attributes that are Nodes are recursed.
        modes is a list of variable modes to include.
        Called from getDictVariables in the root node.
        """
        data = {}
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                data[key] = value._getVariables(modes)
            elif isinstance(value,Variable) and (value.mode in modes):
                data[key] = value._rawGet()

        return data

    def _setVariables(self,d,modes):
        """
        Set variable values from a dictionary starting from this level.
        Attributes that are Nodes are recursed.
        modes is a list of variable modes to act on
        Called from setDictVariables in the root node.
        """
        for key, value in d.iteritems():

            # Entry is in node list
            if key in self._nodes:

                # If entry is a device, recurse
                if isinstance(self._nodes[key],Device):
                    self._nodes[key]._setVariables(value,modes)

                # Set value if variable with enabled mode
                elif isinstance(self._nodes[key],Variable) and (self._nodes[key].mode in modes):
                    self._nodes[key]._rawSet(value)


class Root(rogue.interfaces.stream.Master,Node):
    """
    Class which serves as the root of a tree of nodes.
    The root is the interface point for tree level access and updats.
    The root is a stream master which generates frames containing tree
    configuration and status values. This allows confiuration and status
    to be stored in data files.
    """

    def __init__(self, name, description):
        """Init the node with passed attributes"""

        rogue.interfaces.stream.Master.__init__(self)
        Node.__init__(self, name, description, False, 'root')

        # Polling period. Set to None to exit. 0 = don't poll
        self._pollPeriod = 0

        # Keep of list of errors, exposed as a variable
        self._systemLog = ""
        self._sysLogLock = threading.Lock()

        # Add poller
        self._pollThread = None

        # Variable update list
        self._updatedDict = {}
        self._updatedLock = threading.Lock()

        # Commands

        self.add(Command(name='writeConfig', base='string', function=self._writeConfig,
            description='Write configuration to passed filename in YAML format'))

        self.add(Command(name='readConfig', base='string', function=self._readConfig,
            description='Read configuration from passed filename in YAML format'))

        self.add(Command(name='hardReset', base='None', function=self._hardReset,
            description='Generate a hard reset to each device in the tree'))

        self.add(Command(name='softReset', base='None', function=self._softReset,
            description='Generate a soft reset to each device in the tree'))

        self.add(Command(name='countReset', base='None', function=self._countReset,
            description='Generate a count reset to each device in the tree'))

        self.add(Command(name='clearLog', base='None', function=self._clearLog,
            description='Clear the message log cntained in the systemLog variable'))

        # Variables

        self.add(Variable(name='systemLog', base='string', mode='RO', hidden=True,
            setFunction=None, getFunction='value=dev._systemLog',
            description='String containing newline seperated system logic entries'))

        self.add(Variable(name='pollPeriod', base='float', mode='RW',
            setFunction=self._setPollPeriod, getFunction='value=dev._pollPeriod',
            description='Polling period for pollable variables. Set to 0 to disable polling'))

    def stop(self):
        """Stop the polling thread. Must be called for clean exit."""
        self._pollPeriod=0

    def _setPollPeriod(self,dev,var,value):
        old = self._pollPeriod
        self._pollPeriod = value

        # Start thread
        if old == 0 and value != 0:
            self._pollThread = threading.Thread(target=self._runPoll)
            self._pollThread.start()

        # Stop thread
        elif old != 0 and value == 0:
            self._pollThread.join()
            self._pollThread = None

    def _runPoll(self):
        while(self._pollPeriod != 0):
            time.sleep(self._pollPeriod)
            self._poll()

    def _getAtPath(self,path):
        """Get node using path"""
        if not '.' in path:
            if path == self.name: 
                return self
            else:
                return None
        else:
            base = path[:path.find('.')]
            rest = path[path.find('.')+1:]

            if base == self.name:
                return(self._getPath(rest))
            else:
                return None

    def _getDictStructure(self):
        """Get structure as a dictionary"""
        return {self.name:self._getStructure()}

    def _getYamlStructure(self):
        """Get structure as a yaml string"""
        return yaml.dump(self._getDictStructure(),default_flow_style=False)

    def _getDictVariables(self,modes=['RW']):
        """
        Get tree variable current values as a dictionary.
        modes is a list of variable modes to include.
        Vlist can contain an optional list of variale paths to include in the
        dict. If this list is not NULL only these variables will be included.
        """
        return {self.name:self._getVariables(modes)}

    def _getYamlVariables(self,modes=['RW']):
        """
        Get tree variable current values as a dictionary.
        modes is a list of variable modes to include.
        Vlist can contain an optional list of variale paths to include in the
        yaml. If this list is not NULL only these variables will be included.
        """
        return yaml.dump(self._getDictVariables(modes),default_flow_style=False)

    def _setDictVariables(self,d,modes=['RW']):
        """
        Set variable values from a dictionary.
        modes is a list of variable modes to act on
        """
        self._initUpdatedVars()

        for key, value in d.iteritems():
            if key == self.name:
                self._setVariables(value,modes)

        self._streamUpdatedVars()

    def _setYamlVariables(self,yml,modes=['RW']):
        """
        Set variable values from a dictionary.
        modes is a list of variable modes to act on
        """
        d = yaml.load(yml)
        self._setDictVariables(d,modes)

    def _streamYamlDict(self,d):
        """
        Generate a frame containing the passed dictionary in yaml format.
        """
        if not d: return

        yml = yaml.dump(d,default_flow_style=False)
        frame = self._reqFrame(len(yml),True,0)
        b = bytearray()
        b.extend(yml)
        frame.write(b,0)
        self._sendFrame(frame)

    def _streamYamlVariables(self,modes=['RW','RO']):
        """
        Generate a frame containing all variables values in yaml format.
        A hardware read is not generated before the frame is generated.
        Vlist can contain an optional list of variale paths to include in the
        stream. If this list is not NULL only these variables will be included.
        """
        d = self._getDictVariables(modes)
        self._streamYamlDict(d)

    def _initUpdatedVars(self):
        """Initialize the update tracking log before a bulk variable update"""
        self._updatedLock.acquire()
        self._updatedDict = {}
        self._updatedLock.release()

    def _streamUpdatedVars(self):
        """Stream the results of a bulk variable update"""
        self._updatedLock.acquire()
        self._streamYamlDict(self._updatedDict)
        self._updatedDict = None
        self._updatedLock.release()

    def _write(self):
        """Write all blocks"""

        try:
            for key,value in self._nodes.iteritems():
                if isinstance(value,Device):
                    value._write()
            for key,value in self._nodes.iteritems():
                if isinstance(value,Device):
                    value._verify()
            for key,value in self._nodes.iteritems():
                if isinstance(value,Device):
                    value._check()
        except Exception as e:
            self._root._logException(e)

    def _read(self):
        """Read all blocks"""

        self._initUpdatedVars()

        try:
            for key,value in self._nodes.iteritems():
                if isinstance(value,Device):
                    value._read()
            for key,value in self._nodes.iteritems():
                if isinstance(value,Device):
                    value._check()
        except Exception as e:
            self._root._logException(e)

        self._streamUpdatedVars()

    def _poll(self):
        """Read pollable blocks"""

        self._initUpdatedVars()

        try:
            for key,value in self._nodes.iteritems():
                if isinstance(value,Device):
                    value._poll()
            for key,value in self._nodes.iteritems():
                if isinstance(value,Device):
                    value._check()
        except Exception as e:
            self._root._logException(e)

        self._streamUpdatedVars()

    def _writeConfig(self,dev,cmd,arg):
        """Write YAML configuration to a file. Called from command"""
        self._read()
        try:
            with open(arg,'w') as f:
                f.write(self._getYamlVariables(modes=['RW']))
        except Exception as e:
            self._root._logException(e)

    def _readConfig(self,dev,cmd,arg):
        """Read YAML configuration from a file. Called from command"""

        try:
            with open(arg,'r') as f:
                self._setYamlVariables(f.read(),modes=['RW'])
        except Exception as e:
            self._root._logException(e)

        self._write()

    def _softReset(self,dev,cmd,arg):
        """Generate a soft reset on all devices"""
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._devReset('soft')

    def _hardReset(self,dev,cmd,arg):
        """Generate a hard reset on all devices"""
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._devReset('hard')
        self._clearLog(dev,cmd,arg)

    def _countReset(self,dev,cmd,arg):
        """Generate a count reset on all devices"""
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._devReset('count')

    def _clearLog(self,dev,cmd,arg):
        """Clear the system log"""
        self._sysLogLock.acquire()
        self._systemLog = ""
        self._sysLogLock.release()
        self.systemLog._updated()

    def _logException(self,exception):
        """Add an exception to the log"""
        #traceback.print_exc(limit=1)
        traceback.print_exc()
        self._addToLog(str(exception))

    def _addToLog(self,string):
        """Add an string to the log"""
        self._sysLogLock.acquire()
        self._systemLog += string
        self._systemLog += '\n'
        self._sysLogLock.release()

        self.systemLog._updated()

    def _varUpdated(self,var,value):
        """ Log updated variables"""

        self._updatedLock.acquire()

        # Log is active add to log
        if self._updatedDict != None:
            addPathToDict(self._updatedDict,var.path,value)

        # Otherwise stream directly
        else:
            d = {}
            addPathToDict(d,var.path,value)
            self._streamYamlDict(d)

        self._updatedLock.release()


class Variable(Node):
    """
    Variable holder.
    A variable can be associated with a block of real memory or just manage a local variable.

    offset: offset is the memory offset (in bytes) if the associated with memory. 
            This offset must be aligned to the minimum accessable memory entry for 
            the underlying hardware. Variables with the same offset value will be 
            associated with the same block object. 
    bitSize: The size in bits of the variable entry if associated with memory.
    bitOffset: The offset in bits from the byte offset if associated with memory.
    pollEn: Set to true to enable polling of the associated memory.
    base: This defined the type of entry tracked by this variable.
          hex = An ukisngd integer in hex form
          uint = An unsigned integer
          enum = An enum with value,key pairs passed
          bool = A True,False value
          range = An unsigned integer with a bounded range
          string = A string value
          float = A float value
    mode: Access mode of the variable
          RW = Read/Write
          RO = Read Only
          WR = Write Only
          CMD = A variable only used to perform commands. Can be WO or RW.
    enum: A dictionary of index:value pairs ie {0:'Zero':0,'One'}
    minimum: Minimum value for base=range
    maximum: Maximum value for base=range
    setFunction: Function to call to set the value. dev, var, value passed.
    getFunction: Function to call to set the value. dev, var passed. Return value.
    hidden: Variable is hidden

    The set and get functions can be in one of two forms. They can either be a series 
    of python commands in a string or a pointer to a class function. When defining 
    pythone functions in a string the get function must update the 'value' variable with
    the variable value. For the set function the variable 'value' is set in the value 
    variable. ie setFunction='_someVariable = value', getFunction='value = _someVariable'
    The string function is executed in the context of the variable object with 'dev' set
    to the parent device object.
    """
    def __init__(self, name, description, offset=None, bitSize=32, bitOffset=0, pollEn=False,
                 base='hex', mode='RW', enum=None, hidden=False, minimum=None, maximum=None,
                 setFunction=None, getFunction=None):
        """Initialize variable class"""

        Node.__init__(self,name,description,hidden,'variable')

        # Public Attributes
        self.offset    = offset
        self.bitSize   = bitSize
        self.bitOffset = bitOffset
        self.pollEn    = pollEn
        self.base      = base      
        self.mode      = mode
        self.enum      = enum
        self.minimum   = minimum # For base='range'
        self.maximum   = maximum # For base='range'

        # Check modes
        if (self.mode != 'RW') and (self.mode != 'RO') and \
           (self.mode != 'WO') and (self.mode != 'CMD'):
            raise VariableError('Invalid variable mode %s. Supported: RW, RO, WO, CMD' % (self.mode))

        # Tracking variables
        self._block       = None
        self._setFunction = setFunction
        self._getFunction = getFunction
        self.__listeners  = []

    def _addListener(self, func):
        """
        Add a listener function to call when variable changes. 
        Variable will be passed as an arg:  func(self)
        """
        self.__listeners.append(func)

    def _updated(self):
        """Variable has been updated. Inform listeners."""
        
        # Don't generate updates for CMD and WO variables
        if self.mode == 'WO' or self.mode == 'CMD': return

        value = self._rawGet()

        for func in self.__listeners:
            func(self,value)

        # Root variable update log
        self._root._varUpdated(self,value)

    def _rawSet(self,value):
        """
        Raw set method. This is called by the set() method in order to convert the passed
        variable to a value which can be written to a local container (block or local variable).
        The set function defaults to setting a string value to the local block if mode='string'
        or an integer value for mode='hex', mode='uint' or mode='bool'. All others will default to
        a uint set. 
        The user can use the setFunction attribute to pass a string containing python commands or
        a specific method to call. When using a python string the code will find the passed value
        as the variable 'value'. A passed method will accept the variable object and value as args.
        Listeners will be informed of the update.
        _rawSet() is called during bulk configuration loads with a seperate hardware access generated later.
        """
        if self._setFunction != None:
            if callable(self._setFunction):
                self._setFunction(self._parent,self,value)
            else:
                dev = self._parent
                exec(textwrap.dedent(self._setFunction))

        elif self._block:        
            if self.base == 'string':
                self._block.setString(value)
            else:
                if self.base == 'bool':
                    if value: ivalue = 1
                    else: ivalue = 0
                elif self.base == 'enum':
                    ivalue = {value: key for key,value in self.enum.iteritems()}[value]
                else:
                    ivalue = int(value)
                self._block.setUInt(self.bitOffset,self.bitSize,ivalue)

        # Inform listeners
        self._updated()
                
    def _rawGet(self):
        """
        Raw get method. This is called by the get() method in order to convert the local
        container value (block or local variable) to a value returned to the caller.
        The set function defaults to getting a string value from the local block if mode='string'
        or an integer value for mode='hex', mode='uint' or mode='bool'. All others will default to
        a uint get. 
        The user can use the getFunction attribute to pass a string containing python commands or
        a specific method to call. When using a python string the code will set the 'value' variable
        with the value to return. A passed method will accept the variable as an arg and return the
        resulting value.
        _rawGet() can be called from other levels to get current value without generating a hardware access.
        """
        if self._getFunction != None:
            if callable(self._getFunction):
                return(self._getFunction(self._parent,self))
            else:
                value = None
                dev = self._parent
                exec(textwrap.dedent(self._getFunction))
                return value

        elif self._block:        
            if self.base == 'string':
                return(self._block.getString())
            else:
                ivalue = self._block.getUInt(self.bitOffset,self.bitSize)

                if self.base == 'bool':
                    return(ivalue != 0)
                elif self.base == 'enum':
                    return self.enum[ivalue]
                else:
                    return ivalue
        else:
            return None

    def set(self,value):
        """
        Set the value and write to hardware if applicable
        Writes to hardware are blocking. An error will result in a logged exception.
        """
        try:
            self._rawSet(value)
            if self._block and self._block.mode != 'RO':
                self._block.blockingWrite()
                #self._block.block.blockingVerify() # Not yet implemented in memory::Block
        except Exception as e:
            self._root._logException(e)

    def post(self,value):
        """
        Set the value and write to hardware if applicable using a posted write.
        Writes to hardware are posted.
        """
        try:
            self._rawSet(value)
            if self._block and self._block.mode != 'RO':
                self._block.postedWrite()
        except Exception as e:
            self._root._logException(e)

    def get(self):
        """ 
        Return the value after performing a read from hardware if applicable.
        Hardware read is blocking. An error will result in a logged exception.
        Listeners will be informed of the update.
        """
        try:
            if self._block and self._block.mode != 'WO':
                self._block.blockingRead()
            ret = self._rawGet()
        except Exception as e:
            self._root._logException(e)

        # Update listeners for all variables in the block
        if self._block:
            self._block._updated()
        else:
            self._updated()
        return ret

class Command(Node):
    """Command holder: TODO: Update comments"""

    def __init__(self, name, description, base='None', function=None, hidden=False):
        """Initialize command class"""

        Node.__init__(self,name,description,hidden,'command')

        # Currently supported bases:
        #    uint, hex, string, float

        # Public attributes
        self.base = base

        # Tracking
        self._function = function

    def __call__(self,arg=None):
        """Execute command: TODO: Update comments"""
        try:
            if self._function != None:

                # Function is really a function
                if callable(self._function):
                    self._function(self._parent,self,arg)

                # Function is a CPSW sequence
                elif type(self._function) is collections.OrderedDict:
                    for key,value in self._function.iteritems():

                        # Built in
                        if key == 'usleep':
                            time.sleep(value/1e6)

                        # Determine if it is a command or variable
                        else:
                            n = self._parent._nodes[key]

                            if callable(n): 
                                n(value)
                            else: 
                                n.set(value)

                # Attempt to execute string as a python script
                else:
                    dev = self._parent
                    exec(textwrap.dedent(self._function))

        except Exception as e:
            self._root._logException(e)


class Block(rogue.interfaces.memory.Block):
    """Internal memory block holder"""

    def __init__(self,offset,size):
        """Initialize memory block class"""
        rogue.interfaces.memory.Block.__init__(self,offset,size)

        # Attributes
        self.offset    = offset # track locally because memory::Block address is global
        self.variables = []
        self.pollEn    = False
        self.mode      = ''

    def _check(self):
        if self.getUpdated(): # Throws exception if error
            self._updated()

    def _updated(self):
        for variable in self.variables:
            variable._updated()


class Device(Node,rogue.interfaces.memory.Master):
    """Device class holder. TODO: Update comments"""

    def __init__(self, name, description, size, memBase=None, offset=0, hidden=False):
        """Initialize device class"""

        Node.__init__(self,name,description,hidden,'device')
        rogue.interfaces.memory.Master.__init__(self,offset,size)

        # Blocks
        self._blocks    = []
        self._enable    = True
        self._memBase   = memBase
        self._resetFunc = None

        # Adjust position in tree
        if memBase: self._setMemBase(memBase,offset)

        # Variable interface to enable flag
        self.add(Variable(name='enable', base='bool', mode='RW',
            setFunction=self._setEnable, getFunction='value=dev._enable',
            description='Determines if device is enabled for hardware access'))

    def add(self,node):
        """
        Add node as sub-node in the object
        Device specific implementation to add blocks as required.
        """

        # Call node add
        Node.add(self,node)

        # Adding device whos membase is not yet set
        if isinstance(node,Device) and node._memBase == None:
            node._setMemBase(self)

        # Adding variable
        if isinstance(node,Variable) and node.offset != None:
            varBytes = int(math.ceil(float(node.bitOffset + node.bitSize) / 8.0))

            # First find if and existing block matches
            vblock = None
            for block in self._blocks:
                if node.offset == block.offset:
                    vblock = block

            # Create new block if not found
            if vblock == None:
                vblock = Block(node.offset,varBytes)
                vblock._inheritFrom(self)
                self._blocks.append(vblock)

            # Do association
            node._block = vblock
            vblock.variables.append(node)

            if node.pollEn: 
                vblock.pollEn = True

            if vblock.mode == '': 
                vblock.mode = node.mode
            elif vblock.mode != node.mode:
                vblock.mode = 'RW'

            # Adjust size to hold variable. Underlying class will adjust
            # size to align to minimum protocol access size 
            if vblock.getSize() < varBytes:
               vblock._setSize(varBytes)

    def setResetFunc(self,func):
        self._resetFunc = func

    def _setEnable(self, dev, var, enable):
        """
        Method to update enable in underlying block.
        May be re-implemented in some sub-class to 
        propogate enable to leaf nodes in the tree.
        """
        self._enable = enable

        for block in self._blocks:
            block.setEnable(enable)

    def _setMemBase(self,memBase,offset=None):
        """Connect to memory slave at offset. Adjusting global address."""
        self._memBase = memBase

        if offset != None: 
            self._setAddress(offset)

        # Membase is a Device
        if isinstance(memBase,Device):
            # Inhertit base address and slave pointer from one level up
            self._inheritFrom(memBase)

        # Direct connection to slave
        else:
            self._setSlave(memBase)

        # Adust address map in blocks
        for block in self._blocks:
            block._inheritFrom(self)

        # Adust address map in sub devices
        for key,dev in self._nodes.iteritems():
            if isinstance(dev,Device):
                dev._setMemBase(self)

    def _write(self):
        """ Write all blocks. """
        if not self._enable: return

        # Process local blocks
        for block in self._blocks:
            if block.mode == 'WO' or block.mode == 'RW':
                block.backgroundWrite()

        # Process reset of tree
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._write()

    def _verify(self):
        """ Verify all blocks. """
        if not self._enable: return

        # Process local blocks
        for block in self._blocks:
            if block.mode == 'WO' or block.mode == 'RW':
                #block.backgroundVerify()
                pass # Not yet implemented in memory::Block

        # Process reset of tree
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._verify()

    def _read(self):
        """Read all blocks"""
        if not self._enable: return

        # Process local blocks
        for block in self._blocks:
            if block.mode == 'RO' or block.mode == 'RW':
                block.backgroundRead()

        # Process reset of tree
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._read()

    def _poll(self):
        """Read pollable blocks"""
        if not self._enable: return

        # Process local blocks
        for block in self._blocks:
            if block.pollEn and (block.mode == 'RO' or block.mode == 'RW'):
                block.backgroundRead()

        # Process reset of tree
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._poll()

    def _check(self):
        """Check errors in all blocks and generate variable update nofifications"""
        if not self._enable: return

        # Process local blocks
        for block in self._blocks:
            block._check()

        # Process reset of tree
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._check()

    def _devReset(self,rstType):
        """Generate a count, soft or hard reset"""
        if callable(self._resetFunc):
            self._resetFunc(self,rstType)

        # process remaining blocks
        for key,value in self._nodes.iteritems():
            if isinstance(value,Device):
                value._devReset(rstType)


class DataWriter(Device):
    """Special base class to control data files. TODO: Update comments"""

    def __init__(self, name, description='', hidden=False):
        """Initialize device class"""

        Device.__init__(self, name=name, description=description,
                        size=0, memBase=None, offset=0, hidden=hidden)

        self.classType    = 'dataWriter'
        self._open        = False
        self._dataFile    = ''
        self._bufferSize  = 0
        self._maxFileSize = 0

        self.add(Variable(name='dataFile', base='string', mode='RW',
            setFunction='dev._dataFile = value', getFunction='value = dev._dataFile',
            description='Data file for storing frames for connected streams.'))

        self.add(Variable(name='open', base='bool', mode='RW',
            setFunction=self._setOpen, getFunction='value = dev._open',
            description='Data file open state'))

        self.add(Variable(name='bufferSize', base='uint', mode='RW',
            setFunction=self._setBufferSize, getFunction='value = dev._bufferSize',
            description='File buffering size. Enables caching of data before call to file system.'))

        self.add(Variable(name='maxFileSize', base='uint', mode='RW',
            setFunction=self._setMaxFileSize, getFunction='value = dev._maxFileSize',
            description='Maximum size for an individual file. Setting to a non zero splits the run data into multiple files.'))

        self.add(Variable(name='fileSize', base='uint', mode='RO',
            setFunction=None, getFunction=self._getFileSize,
            description='Size of data files(s) for current open session in bytes.'))

        self.add(Variable(name='frameCount', base='uint', mode='RO',
            setFunction=None, getFunction=self._getFrameCount,
            description='Frame in data file(s) for current open session in bytes.'))

        self.add(Command(name='autoName', function=self._genFileName,
            description='Auto create data file name using data and time.'))

    def _setOpen(self,dev,var,value):
        """Set open state. Override in sub-class"""
        self._open = value

    def _setBufferSize(self,dev,var,value):
        """Set buffer size. Override in sub-class"""
        self._bufferSize = value

    def _setMaxFileSize(self,dev,var,value):
        """Set max file size. Override in sub-class"""
        self._maxFileSize = value

    def _getFileSize(self,dev,cmd):
        """get current file size. Override in sub-class"""
        return(0)

    def _getFrameCount(self,dev,cmd):
        """get current file frame count. Override in sub-class"""
        return(0)

    def _genFileName(self,dev,cmd,arg):
        """
        Auto create data file name based upon date and time.
        Preserve file's location in path.
        """
        idx = self._dataFile.rfind('/')

        if idx < 0:
            base = ''
        else:
            base = self._dataFile[:idx+1]

        self._dataFile = base
        self._dataFile += datetime.datetime.now().strftime("%Y%m%d_%H%M%S.dat") 
        self.dataFile._updated()

    def _read(self):
        """Force update of non block status variables"""
        self.fileSize.get()
        self.frameCount.get()
        Device._read(self)

    def _poll(self):
        """Force update of non block status variables"""
        self.fileSize.get()
        self.frameCount.get()
        Device._poll(self)


class RunControl(Device):
    """Special base class to control runs. TODO: Update comments."""

    def __init__(self, name, description='', hidden=False):
        """Initialize device class"""

        Device.__init__(self, name=name, description=description,
                        size=0, memBase=None, offset=0, hidden=hidden)

        self.classType = 'runControl'
        self._runState = 'Stopped'
        self._runCount = 0
        self._runRate  = '1 Hz'

        self.add(Variable(name='runState', base='enum', mode='RW', enum={0:'Stopped', 1:'Running'},
            setFunction=self._setRunState, getFunction='value = dev._runState',
            description='Run state of the system.'))

        self.add(Variable(name='runRate', base='enum', mode='RW', enum={1:'1 Hz', 10:'10 Hz'},
            setFunction=self._setRunRate, getFunction='value = dev._runRate',
            description='Run rate of the system.'))

        self.add(Variable(name='runCount', base='uint', mode='RO',
            setFunction=None, getFunction='value = dev._runCount',
            description='Run Counter updated by run thread.'))

    def _setRunState(self,dev,var,value):
        """
        Set run state. Reimplement in sub-class.
        Enum of run states can also be overriden.
        Underlying run control must update _runCount variable.
        """
        self._runState = value

    def _setRunRate(self,dev,var,value):
        """
        Set run rate. Reimplement in sub-class.
        Enum of run rates can also be overriden.
        """
        self._runRate = value

    def _read(self):
        """Force update of non block status variables"""
        self.runCount.get()
        Device._read(self)

    def _poll(self):
        """Force update of non block status variables"""
        self.runCount.get()
        Device._poll(self)


# Helper function add a path/value pair to a dictionary tree
def addPathToDict(d, path, value):
    npath = path
    sd = d

    # Transit through levels
    while '.' in npath:
        base  = npath[:npath.find('.')]
        npath = npath[npath.find('.')+1:]

        if sd.has_key(base):
           sd = sd[base]
        else:
           sd[base] = {}
           sd = sd[base]

    # Add final node
    sd[npath] = value
