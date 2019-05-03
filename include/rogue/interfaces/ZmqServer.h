/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue Shared Memory Interface
 * ----------------------------------------------------------------------------
 * File       : ZmqServer.h
 * Created    : 2019-05-02
 * ----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the rogue software platform, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
**/
#ifndef __ROGUE_ZMQ_SERVER_H__
#define __ROGUE_ZMQ_SERVER_H__
#include <thread>

#ifndef NO_PYTHON
#include <boost/python.hpp>
#endif

namespace rogue {
   namespace interfaces {

      //! Logging
      class ZmqServer {

            // Zeromq Context
            void * zmqCtx_;

            // Zeromq publish port
            void * zmqPub_;

            // Zeromq response port
            void * zmqRep_;

            std::thread   * thread_;
            bool threadEn_;

            void runThread();

         public:

            static std::shared_ptr<rogue::interfaces::ZmqServer> create(std::string addr, uint16_t port);

            //! Setup class in python
            static void setup_python();

            ZmqServer (std::string addr, uint16_t port);
            virtual ~ZmqServer();

            void publish(std::string value);

            virtual std::string doRequest (std::string type, std::string path, std::string arg );
      };
      typedef std::shared_ptr<rogue::interfaces::ZmqServer> ZmqServerPtr;

#ifndef NO_PYTHON

      //! Stream slave class, wrapper to enable pyton overload of virtual methods
      class ZmqServerWrap : 
         public rogue::interfaces::ZmqServer, 
         public boost::python::wrapper<rogue::interfaces::ZmqServer> {

         public:

            ZmqServerWrap (std::string addr, uint16_t port);

            std::string doRequest ( std::string type, std::string path, std::string arg );

            std::string defDoRequest ( std::string type, std::string path, std::string arg );
      };

      typedef std::shared_ptr<rogue::interfaces::ZmqServerWrap> ZmqServerWrapPtr;
#endif
   }
}

#endif

