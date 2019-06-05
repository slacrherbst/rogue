#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Virtual Classes
#-----------------------------------------------------------------------------
# File       : pyrogue/_Virtual.py
# Created    : 2017-05-16
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import sys
from collections import OrderedDict as odict
import logging
import inspect
import pyrogue as pr
import zmq
import rogue.interfaces
import functools as ft


def genBaseList(cls):
    ret = [str(cls)]

    for l in cls.__bases__:
        if l is not object:
            ret += genBaseList(l)

    return ret


class VirtualProperty(object):
    def __init__(self, node, attr):
        self._attr = attr
        self._node = node

    def __get__(self, obj=None, objtype=None):
        return self._node._client._remoteAttr(self._node._path, self._attr)

    def __set__(self, obj, value):
        pass


class VirtualMethod(object):
    def __init__(self, node, attr, info):
        self._attr   = attr
        self._node   = node
        self._args   = info['args']
        self._kwargs = info['kwargs']

    def __call__(self, *args, **kwargs):
        return self._node._client._remoteAttr(self._node._path, self._attr, *args, **kwargs)


def VirtualFactory(data):

    def __init__(self,data):

        # Add dynamic methods
        for k,v in data['funcs'].items():
            setattr(self.__class__,k,VirtualMethod(self,k,v))

        # Add dynamic properties
        for k in data['props']:
            setattr(self.__class__,k,VirtualProperty(self,k))

        VirtualNode.__init__(self,data)

    newclass = type('Virtual' + data['class'], (VirtualNode,), {"__init__": __init__})
    return newclass(data)


class VirtualNode(pr.Node):
    def __init__(self, attrs):
        super().__init__(name=attrs['name'], 
                         description=attrs['description'], 
                         expand=attrs['expand'], 
                         hidden=attrs['hidden'])

        self._path  = attrs['path']
        self._class = attrs['class']

        #self._nodes = odict({k:None for k in attrs['nodes']})
        self._nodes = attrs['nodes']
        self._bases = attrs['bases']

        # Tracking
        self._parent    = None
        self._root      = None
        self._client    = None
        self._functions = []

        # Setup logging
        self._log = pr.logInit(cls=self,name=self.name,path=self._path)

    def __call__(self, *args, **kwargs):
        return self._client._remoteAttr(self._path, '__call__', *args, **kwargs)

    def add(self,node):
        raise NodeError('add not supported in VirtualNode')

    def find(self, *, recurse=True, typ=None, **kwargs):
        raise NodeError('find not supported in VirtualNode')

    def callRecursive(self, func, nodeTypes=None, **kwargs):
        raise NodeError('callRecursive not supported in VirtualNode')

    def addListener(self, listener):
        self._functions.append(listener)

    def addVarListener(self,func):
        self._client._addVarListener(func)

    def _isinstance(self,typ):
        cs = str(typ)
        return cs in self._bases

    def _rootAttached(self,parent,root):
        raise NodeError('_rootAttached not supported in VirtualNode')

    def _getDict(self,modes):
        raise NodeError('_getDict not supported in VirtualNode')

    def _setDict(self,d,writeEach,modes=['RW']):
        raise NodeError('_setDict not supported in VirtualNode')

    def _doUpdate(self, val):
        for func in self._functions:
            if hasattr(func,'varListener'):
                func.varListener(self.path,val.value,val.valueDisp)
            else:
                func(self.path,val.value,val.valueDisp)

    def _virtAttached(self,parent,root,client):
        """Called once the root node is attached."""
        self._parent = parent
        self._root   = root
        self._client = client

        for key,value in self._nodes.items():
            value._virtAttached(self,root,client)


class VirtualClient(rogue.interfaces.ZmqClient):

    def __init__(self, addr="localhost", port=9099):
        rogue.interfaces.ZmqClient.__init__(self,addr,port)
        self._root = None
        self._varListeners = []
        self._ready = False

        # Setup logging
        self._log = pr.logInit(cls=self,name="VirtualClient",path=None)

        # Try to connect to root entity
        while self._root is None:
            self._root = self._remoteAttr(None, None)

        self._root._virtAttached(self._root,self._root,self)
        self._ready = True

    def _remoteAttr(self, path, attr, *args, **kwargs):
        snd = { 'path':path, 'attr':attr, 'args':args, 'kwargs':kwargs }
        y = pr.dataToYaml(snd) + '\n'
        try:
            resp = self._send(y)
            ret = pr.yamlToData(resp)
        except Exception as msg:
            print("got remote exception: {}".format(msg))
            ret = None

        return ret

    def _addVarListener(self,func):
        self._varListeners.append(func)

    def _doUpdate(self,data):
        if not self._ready:
            return

        d = pr.yamlToData(data)

        for k,val in d.items():
            n = self._root.getNode(k)
            if n is None:
                self._log.error("Failed to find node {}".format(k))
            else:
                n._doUpdate(val)

            # Call listener functions,
            for func in self._varListeners:
                func(k,val.value.val,valueDisp)

    @property
    def root(self):
        return self._root

