/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Master
 * ----------------------------------------------------------------------------
 * File       : Constants.h
 * Created    : 2016-12-05
 * ----------------------------------------------------------------------------
 * Description:
 * Memory error and transaction constants.
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
#ifndef __ROGUE_INTERFACES_MEMORY_ERRORS_H__
#define __ROGUE_INTERFACES_MEMORY_ERRORS_H__
#include <stdint.h>

namespace rogue {
   namespace interfaces {
      namespace memory {

         ///////////////////////////
         // Memory Error Constants
         ///////////////////////////

         /** This is a software level timeout that is triggered
          * if the memory Slave never completed the transaction.
          */
         static const uint32_t TimeoutError = 0x01000000;

         /** The readback verify value did not match the written value.
          */
         static const uint32_t VerifyError = 0x02000000;

         /** The Slave has declared an address error.
          * This can occur if the address is at an alignment not
          * support by the memory Slave
          */
         static const uint32_t AddressError = 0x03000000;

         /** A bus timeout is declared at the hardware level
          * indicating the bus transaction has timed out.
          */
         static const uint32_t BusTimeout = 0x04000000;

         /** A bus failure is declared at the hardware level.
          */
         static const uint32_t BusFail = 0x05000000;

         /** The transaction is not unsupported.
          */
         static const uint32_t Unsupported = 0x06000000;

         /** The Slave has declared a size violation. This can 
          * occur when the requested transaction size exceeds 
          * the maximum transaction supported by the Slave.
          */
         static const uint32_t SizeError = 0x07000000;

         /** The Slave has declared a protocol error. This can 
          * occur if the transaction data was corrupted while the 
          * transaction was in progress. 
          */
         static const uint32_t ProtocolError = 0x08000000;

         //////////////////////////////
         // Transaction Type Constants
         //////////////////////////////

         //! Memory read transaction
         static const uint32_t Read   = 0x1;

         //! Memory write transaction
         static const uint32_t Write  = 0x2;

         //! Memory posted write transaction
         static const uint32_t Post   = 0x3;

         //! Memory verify readback transaction
         static const uint32_t Verify = 0x4;

      }
   }
}

#endif

