#!/usr/bin/env arista-python
# Copyright (c) 2007, 2008, 2009, 2010 Arista Networks, Inc.  All rights reserved.
# Arista Networks, Inc. Confidential and Proprietary.

from __future__ import absolute_import, division, print_function
import errno, mmap, os, re, struct, sys

class Address( object ):
   """Represents a PCI device address as a (domain, bus, slot, function) tuple."""

   def __init__( self, domain=0, bus=0, slot=0, function=0 ):
      """Construct an Address from separate domain, bus, slot, function values.
      Also accepts a single string with format [[DDDD:]BB:]SS[.F], an
      Inventory::PciAddress value, or an Address."""
      try:
         domain, bus, slot, function = re.match(
            "(?:(?:(\w+):)?(\w+):)?(\w+)(?:\.(\w+))?$", domain ).groups()
      except TypeError:
         pass
      # handle first arg of type Inventory::PciAddress without dragging in Tac
      self.domain, self.bus, self.slot, self.function = (
         getattr( domain, "domain", _hexnum( domain ) ),
         getattr( domain, "bus", _hexnum( bus ) ),
         getattr( domain, "slot", _hexnum( slot ) ),
         getattr( domain, "function", _hexnum( function ) ) )
      # assert self.domain >= 0 and self.domain <= 0xffff
      # TODO: This assertion causes container to fail
      assert self.bus >= 0 and self.bus <= 0x100
      assert self.slot >= 0 and self.slot <= 0x1f
      assert self.function >= 0 and self.function <= 7

   def value( self ):
      """Convert the address to an Inventory::PciAddress value."""
      import Tac
      return Tac.Value(
         "Inventory::PciAddress",
         domain=self.domain, bus=self.bus, slot=self.slot, function=self.function )

   def devfn( self ):
      """Return the slot and function packed into a single byte."""
      return ( self.slot << 3 ) | self.function

   def __str__( self ):
      return "%04x:%02x:%02x.%01x" % ( self.domain, self.bus,
                                       self.slot, self.function )

   def __repr__( self ):
      return "Pci.Address( %s )" % self
   
   # __hash__ and __cmp__ are needed for set element identity
   def __hash__( self ):
      return hash( repr( self ) )

   def __eq__( self, other ):
      return repr( self ) == repr( other )

   def __ne__( self, other ):
      return repr( self ) != repr( other )

   def __lt__( self, other ):
      return repr( self ) < repr( other )

   def __le__( self, other ):
      return repr( self ) <= repr( other )

   def __gt__( self, other ):
      return repr( self ) > repr( other )

   def __ge__( self, other ):
      return repr( self ) >= repr( other )

class Id( object ):
   """Represents a PCI device or subsystem ID as a (vendor, device) tuple."""

   def __init__( self, vendor=0, device=0 ):
      """Construct an Id from separate vendor, device values. Also accepts a
      single string with format VVVV:DDDD, an Inventory::PciId value, or an Id."""
      try:
         vendor, device = re.match( "(\w+):(\w+)$", vendor ).groups()
      except TypeError:
         pass
      # handle first arg of type Inventory::PciId without dragging in Tac
      self.vendor, self.device = (
         getattr( vendor, "vendor", _hexnum( vendor ) ),
         getattr( vendor, "device", _hexnum( device ) ) )
      assert self.vendor >= 0 and self.vendor <= 0xffff
      assert self.device >= 0 and self.device <= 0xffff

   def value( self ):
      """Convert the ID to an Inventory::PciId value."""
      import Tac
      return Tac.Value( "Inventory::PciId", vendor=self.vendor, device=self.device )

   def __str__( self ):
      return "%04x:%04x" % (self.vendor, self.device)

   def __repr__( self ):
      return "Pci.Id( %s )" % self
   
   # __hash__ and __cmp__ are needed for set element identity
   def __hash__( self ):
      return hash( repr( self ) )

   def __eq__( self, other ):
      return repr( self ) == repr( other )

   def __ne__( self, other ):
      return repr( self ) != repr( other )

   def __lt__( self, other ):
      return repr( self ) < repr( other )

   def __le__( self, other ):
      return repr( self ) <= repr( other )

   def __gt__( self, other ):
      return repr( self ) > repr( other )

   def __ge__( self, other ):
      return repr( self ) >= repr( other )

class Device( object ):
   """Represents a PCI device and provides convenient access to sysfs properties."""
   
   def __init__( self, address ):
      """Construct a PCI device for the given address.  Attempts to convert
      address to an Address object if necessary."""
      self.address_ = Address( address )
      sys = os.environ.get( 'SIMULATION_SYS', '/sys' )
      self.sysfsBase_ = os.path.join( sys,"bus/pci/devices", str(self) )

   def address( self ):
      """Return the device's address as an Address object."""
      return self.address_

   def devfn( self ):
      """Return the device's slot and function packed into a single byte."""
      return self.address_.devfn()

   def sysfsPath( self, p ):
      """Return the full path to a sysfs property for this device."""
      return os.path.join( self.sysfsBase_, p )

   def id( self ):
      """Return the device's vendor and device ID as an Id object."""
      try:
         return Id( _hexnum( open( self.sysfsPath( "vendor" ) ).read() ),
                    _hexnum( open( self.sysfsPath( "device" ) ).read() ) )
      except IOError:
         # With hotplug this can fail if the device is in the process of being
         # detected/removed when we scan for Pci devices.
         return None

   def subsystemId( self ):
      """Return the device's subsystem vendor and device ID as an Id object."""
      try:
         return Id( _hexnum( open( self.sysfsPath( "subsystem_vendor" ) ).read() ),
                    _hexnum( open( self.sysfsPath( "subsystem_device" ) ).read() ) )
      except IOError:
         # With hotplug this can fail if the device is in the process of being
         # detected/removed when we scan for Pci devices.
         return None

   def classCode( self ):
      """Return the device's class code as an int."""
      try:
         return _hexnum( open( self.sysfsPath( "class" ) ).read() )
      except IOError:
         # With hotplug this can fail if the device is in the process of being
         # detected/removed when we scan for Pci devices.
         return None

   def resource( self, index, readOnly=False, filename=None, 
         startOffset=None, endOffset=None):
      """Return a Resource object for one of the device's I/O or memory resources."""
      if filename == None:
         filename = "resource%d" % index
      p = self.sysfsPath( filename )
      if os.path.exists( p ):
         return MmapResource( p, readOnly, startOffset, endOffset )

   def config( self, readOnly=False ):
      """Return a Resource object for the device's configuration space."""
      if os.getuid():
         sys.stderr.write( "WARNING: You are not running as root. You may only be "
                           "able to access the first 64 bytes of PCI configuration "
                           "space.\n" )
      p = self.sysfsPath( "config" )
      if os.path.exists( p ):
         return PseudoMmapResource( p, readOnly )

   def __str__( self ):
      return str( self.address_ )

   def __repr__( self ):
      return "Pci.Device( %s )" % self
   
def allDevices():
   """Return a list of all the PCI devices in the system as reported by sysfs."""
   sys = os.environ.get( "SIMULATION_SYS", "/sys" )
   pciDeviceDir = os.path.join( sys, "bus/pci/devices" )
   return [ Device( Address( x ) ) for x in os.listdir( pciDeviceDir ) ]

def deviceById( id ):
   """Return a Device object for a system device with the specified ID."""
   id = Id( id )
   deviceList = ( [ d for d in allDevices() if d.id() == id ] or [None] )
   # cannot assert here, NorCalInit requires this to work and on modular there
   # are multiple scds if the system rebooted with cards powered on, we are
   # lucky that the supe scd is always first in the list
   #assert len( deviceList ) == 1, "More than one device found with the given id"
   return deviceList[ 0 ]

def allDevicesById( id ):
   """Return all the device objects for a system device with the specified ID."""
   id = Id( id )
   deviceList = ( [ d for d in allDevices() if d.id() == id ] or [None] )
   return deviceList

class Resource( object ):
   """Abstract class representing a memory region.  Provides functions for
   reading and writing values."""

   # NOTE: The __init__ line below commented out due to pylint crashes (BUG235310)
   #       In theory, abstract classes should follow the model documented in
   #       https://docs.python.org/2/tutorial/classes.html
   #       but this code would have to be refactored substantially
   #       
   # __init__ = None

   # '<B', '<H' and '<L' mean a little-endian unsigned byte, short and long
   # respectively. PCI registers are always little-endian.
   _pci8StructDef = '<B'
   _pci16StructDef = '<H'
   _pci32StructDef = '<L'

   _mmapOffset = 0

   def mmap( self ):
      return self.mmap_
   
   def read8( self, addr, check=True ):
      """Reads an 8-bit value from the specified address in the specified PCI
      resource."""
      if check:
         self._checkAddr8( addr )
      addr = addr - self._mmapOffset 
      return struct.unpack( self._pci8StructDef,
                            self.mmap_[ addr ] )[ 0 ]

   def read16( self, addr, check=True ):
      """Reads a 16-bit value from the specified address in the specified PCI
      resource."""
      if check:
         self._checkAddr16( addr )
      addr = addr - self._mmapOffset
      return struct.unpack( self._pci16StructDef,
                            self.mmap_[ addr : addr + 2 ] )[ 0 ]

   def read32( self, addr, check=True ):
      """Reads a 32-bit value from the specified address in the specified PCI
      resource."""
      if check:
         self._checkAddr32( addr )
      addr = addr - self._mmapOffset 
      return struct.unpack( self._pci32StructDef,
                            self.mmap_[ addr : addr + 4 ] )[ 0 ]

   def write8( self, addr, value, check=True ):
      """Writes an 8-bit value to the specified address in the specified PCI
      resource."""
      if check:
         self._checkAddr8( addr )
         if not ( 0 <= value and value <= 0xff ):
            raise ValueError( 'Value %s out of range' % value )
      addr = addr - self._mmapOffset 
      self.mmap_[ addr ] = struct.pack( self._pci8StructDef, value )

   def write16( self, addr, value, check=True ):
      """Writes a 16-bit value to the specified address in the specified PCI
      resource."""
      if check:
         self._checkAddr16( addr )
         if not ( 0 <= value and value <= 0xffff ):
            raise ValueError( 'Value %s out of range' % value )
      addr = addr - self._mmapOffset
      self.mmap_[ addr: addr + 2 ] = struct.pack( self._pci16StructDef, value )

   def write32( self, addr, value, check=True ):
      """Writes a 32-bit value to the specified address in the specified PCI
      resource."""
      if check:
         self._checkAddr32( addr )
         if not ( 0 <= value and value <= 0xffffffff ):
            raise ValueError( 'Value %s out of range' % value )
      addr = addr - self._mmapOffset 
      self.mmap_[ addr: addr + 4 ] = struct.pack( self._pci32StructDef, value )

   def _checkAddr8( self, addr ):
      if ( addr < self._mmapOffset ) or ( len( self.mmap_ ) and 
            addr >= len( self.mmap_ ) + self._mmapOffset ):
         raise ValueError( 'Address %#010x out of range (resource size %#010x)' % 
                           ( addr, len( self.mmap_ ) ) )

   def _checkAddr16( self, addr ):
      if addr % 2 != 0:
         raise ValueError( 'Address %#010x is not a multiple of 2' % addr )
      if ( addr < self._mmapOffset ) or ( len( self.mmap_ ) and
            addr + 1 >= len( self.mmap_ ) + self._mmapOffset ):
         raise ValueError( 'Address %#010x out of range (resource size %#010x)' %
                           ( addr, len( self.mmap_ ) ) )

   def _checkAddr32( self, addr ):
      if addr % 4 != 0:
         raise ValueError( 'Address %#010x is not a multiple of 4' % addr )
      if ( addr < self._mmapOffset ) or ( len( self.mmap_ ) and 
            addr + 3 >= len( self.mmap_ ) + self._mmapOffset ):
         raise ValueError( 'Address %#010x out of range (resource size %#010x)' % 
                           ( addr, len( self.mmap_ ) ) )

class MmapResource( Resource ):
   """Resource implementation for a directly-mapped memory region."""
   
   def __init__( self, path, readOnly=False, startOffset=None, endOffset=None ):
      prot = mmap.PROT_READ
      if not readOnly:
         prot |= mmap.PROT_WRITE
      fd = os.open( path, os.O_RDWR )
      try:
         size = os.fstat( fd ).st_size

         if startOffset is None:
            startOffset = 0

         if endOffset is None:
            endOffset = size

         length = endOffset - startOffset

         if ( startOffset % mmap.PAGESIZE != 0 ):
            raise ValueError( 'Start Offset 0x%x, must be aligned to 0x%x' 
                     %(startOffset, mmap.PAGESIZE) )
         
         self._mmapOffset = startOffset

         try:
            self.mmap_ = mmap.mmap( fd, length, mmap.MAP_SHARED, prot, 
                           offset=startOffset )
         except EnvironmentError as e:
            if e.errno == errno.EINVAL:
               raise ValueError( 'Cannot memory-map resource file (is it an'
                                 ' I/O region rather than a memory region?)' )
            raise

      finally:
         try:
            # Note that closing the file descriptor has no effect on the memory map
            os.close( fd )
         except OSError:
            pass
   
   def unmap( self ):
      if self.mmap_:
         self.mmap_.close()
         self.mmap_ = None


class _PseudoMmap( object ):
   """A class that emulates an mmap object for files that are not mmap-able, by
   implementing __getitem__ and __setitem__ in terms of seek(), read() and
   write()."""

   def __init__( self, f ):
      self.f_ = f
   def _translateIndex( self, index ):
      if isinstance( index, slice ):
         indices = index.indices( len( self ) )
         if indices[ 2 ] != 1:
            raise TypeError( "_PseudoMmap doesn't support extended slices" )
         return ( indices[ 0 ], indices[ 1 ] - indices[ 0 ] )
      else:
         return ( index, 1 )
   def __getitem__( self, index ):
      ( start, num ) = self._translateIndex( index )
      self.f_.seek( start )
      return self.f_.read( num )
   def __setitem__( self, index, value ):
      ( start, num ) = self._translateIndex( index )
      assert len( value ) == num
      self.f_.seek( start )
      self.f_.write( value )
      self.f_.flush()
   def __len__( self ):
      return os.fstat( self.f_.fileno() ).st_size or sys.maxsize

class PseudoMmapResource( Resource ):
   """Resource implementation for an emulated memory region."""
   
   def __init__( self, path, readOnly=False ):
      # XXX - tonytruong
      # The file() constructor should not be called directly
      # as it is preferable to use open() according to
      # http://docs.python.org/2/library/functions.html#open
      # File is opened as unbuffered as this class is mainly used
      # for the PCI configuration and I/O spaces and we do not want to buffer them
      # since they contain some status registers
      #self.mmap_ = _PseudoMmap( file( path, readOnly and "rb" or "rb+" ) )
      self.mmap_ = _PseudoMmap( open( path, readOnly and "rb" or "rb+", 0 ) )

def _hexnum( num ):
   if type( num ) is int:
      return num
   elif type( num ) is str:
      return int( num, 16 )
   else:
      return 0
