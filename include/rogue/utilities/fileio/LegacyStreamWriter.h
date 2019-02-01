/**
 *-----------------------------------------------------------------------------
 * Title         : Data file writer utility.
 * ----------------------------------------------------------------------------
 * File          : LegacyStreamWriter.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/28/2016
 * Last update   : 09/28/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    Class to coordinate data file writing.
 *    This class writes files using the legacy data format of XmlDaq
 *
 *       headerA:
 *          [31:28] = Type
 *          [27:0]  = Size
 *
 *-----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
    * https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the rogue software platform, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 *-----------------------------------------------------------------------------
**/
#ifndef __ROGUE_UTILITIES_FILEIO_LEGACY_STREAM_WRITER_H__
#define __ROGUE_UTILITIES_FILEIO_LEGACY_STREAM_WRITER_H__
#include <rogue/utilities/fileio/StreamWriter.h>
#include <boost/enable_shared_from_this.hpp>
#include <rogue/interfaces/stream/Frame.h>
#include <stdint.h>
#include <boost/thread.hpp>
#include <map>

namespace rogue {
   namespace utilities {
      namespace fileio {

         class StreamWriterChannel;

         //! Stream writer central class
         class LegacyStreamWriter : public StreamWriter {

            protected:

               //! Write data to file. Called from StreamWriterChannel
               virtual void writeFile ( uint8_t channel, boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

            public:
               
               // Data types. 
               // Count is n*32bits for type = 0, byte count for all others
               enum DataType {
                 RawData     = 0,
                 XmlConfig   = 1,
                 XmlStatus   = 2,
                 XmlRunStart = 3,
                 XmlRunStop  = 4,
                 XmlRunTime  = 5,
                 YamlData    = 6
               };

               //! Class creation
               static boost::shared_ptr<rogue::utilities::fileio::LegacyStreamWriter> create ();

               //! Setup class in python
               static void setup_python();

               //! Creator
               LegacyStreamWriter();

               //! Deconstructor
               ~LegacyStreamWriter();

               //! Get a port
               boost::shared_ptr<rogue::utilities::fileio::StreamWriterChannel> getDataChannel();
               boost::shared_ptr<rogue::utilities::fileio::StreamWriterChannel> getYamlChannel();               

            
         };

         // Convienence
         typedef boost::shared_ptr<rogue::utilities::fileio::LegacyStreamWriter> LegacyStreamWriterPtr;
      }
   }
}
#endif

