/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Transaction
 * ----------------------------------------------------------------------------
 * File       : Transaction.h
 * Created    : 2019-03-08
 * ----------------------------------------------------------------------------
 * Description:
 * Memory Transaction
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
#ifndef __ROGUE_INTERFACES_MEMORY_TRANSACTION_H__
#define __ROGUE_INTERFACES_MEMORY_TRANSACTION_H__
#include <boost/enable_shared_from_this.hpp>
#include <stdint.h>
#include <vector>
#include <boost/thread.hpp>

#ifndef NO_PYTHON
#include <boost/python.hpp>
#endif

namespace rogue {
   namespace interfaces {
      namespace memory {

         class TransactionLock;
         class Master;
         class Hub;

         //! Transaction Container
         /** The Transaction is passed between the Master and Slave to initiate a transaction. 
          * The Transaction class contains information about the transaction as well as the 
          * transaction data pointer. Each created transaction object has a unique 32-bit 
          * transaction ID.
          */ 
         class Transaction : public boost::enable_shared_from_this<rogue::interfaces::memory::Transaction> {
            friend class TransactionLock;
            friend class Master;
            friend class Hub;

            public: 
               
               //! Alias for using uint8_t * as Transaction::iterator
               typedef uint8_t * iterator;

            private:

               // Class instance counter
               static uint32_t classIdx_;

               // Class instance lock
               static boost::mutex classMtx_;

               // Conditional
               boost::condition_variable cond_;

            protected:

               // Transaction timeout 
               struct timeval timeout_;

               // Transaction end time
               struct timeval endTime_;

               // Transaction start time
               struct timeval startTime_;

#ifndef NO_PYTHON
               // Transaction python buffer
               Py_buffer pyBuf_;
#endif

               // Python buffer is valid
               bool pyValid_;

               // Iterator (mapped to uint8_t * for now)
               iterator iter_;

               // Transaction address
               uint64_t address_;

               // Transaction size
               uint32_t size_;

               // Transaction type
               uint32_t type_;

               // Transaction error
               uint32_t error_;

               // Transaction id
               uint32_t id_;

               // Done state
               bool done_;

               // Transaction lock
               boost::mutex lock_;

               // Create a transaction container and return a TransactionPtr, called by Master
               static boost::shared_ptr<rogue::interfaces::memory::Transaction> create (struct timeval timeout);

               // Refresh timer, called by Master
               void refreshTimer(boost::shared_ptr<rogue::interfaces::memory::Transaction> reference);

               // Wait for the transaction to complete, called by Master
               uint32_t wait();

            public:

               //! Setup class for use in python
               /* Not exposed to Python
                */
               static void setup_python();

               //! Create a Transaction
               /** Do not call directly. Only called from the Master class.
                *
                * Not available in Python
                * @param timeout Timeout value as a struct timeval
                */
               Transaction(struct timeval timeout);

               //! Destroy the Transaction.
               ~Transaction();

               //! Lock Transaction and return a TransactionLockPtr object
               /** Exposed as lock() to Python
                *  @return TransactionLock pointer (TransactonLockPtr)
                */
               boost::shared_ptr<rogue::interfaces::memory::TransactionLock> lock();

               //! Get expired flag
               /** The expired flag is set by the Master when the Transaction times out
                * and the Master is no longer wiating for the Transaction to complete.
                * Lock must be held before checking the expired status.
                *
                * Exposed as expired() to Python
                * @return True if transaction is expired.
                */
               bool expired();

               //! Get 32-bit Transaction ID
               /** Exposed as id() to Python
                * @return 32-bit transaction ID
                */
               uint32_t id();

               //! Get Transaction address
               /** Exposed as address() to Python
                * @return 64-bit Transaction ID
                */
               uint64_t address();

               //! Get Transaction size
               /** Exposed as size() to Python
                * @return 32-bit Transaction size
                */
               uint32_t size();

               //! Get Transaction type
               /** Exposed as type() to Python
                * @return 32-bit Transaction type
                */
               uint32_t type();

               //! Complete transaction with passed error
               /** Lock must be held before calling this method.
                *
                * Exposted as done() to Python
                * @param error Transaction error value or 0 for no error.
                */
               void done(uint32_t error);

               //! Get start iterator for Transaction data
               /** Not exposed to Python
                *
                * Lock must be held before calling this method and while
                * updating Transaction data.
                * @return Data iterator as Transaction::iterator
                */
               uint8_t * begin();

               //! Get end iterator for Transaction data
               /** Not exposed to Python
                *
                * Lock must be held before calling this method and while
                * updating Transaction data.
                * @return Data iterator as Transaction::iterator
                */
               uint8_t * end();

#ifndef NO_PYTHON

               //! Method for copying transaction data to Python byte array
               /** Exposted to Python as getData()
                *
                * The size of the data to be copied is defined by the size of
                * the passed data buffer.
                * @param p Python byte array object
                * @param offset Offset for Transaction data access.
                */
               void getData ( boost::python::object p, uint32_t offset );

               //! Method for copying transaction data from Python byte array
               /** Exposted to Python as setData()
                *
                * The size of the data to be copied is defined by the size of
                * the passed data buffer.
                * @param p Python byte array object
                * @param offset Offset for Transaction data access.
                */
               void setData ( boost::python::object p, uint32_t offset );
#endif
         };

         //! Alias for using shared pointer as TransactionPtr
         typedef boost::shared_ptr<rogue::interfaces::memory::Transaction> TransactionPtr;

      }
   }
}

#endif

