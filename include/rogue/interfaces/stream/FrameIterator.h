/**
 *-----------------------------------------------------------------------------
 * Title      : Stream frame iterator
 * ----------------------------------------------------------------------------
 * File       : FrameIterator.h
 * Created    : 2018-03-06
 * ----------------------------------------------------------------------------
 * Description:
 * Stream frame iterator
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
#ifndef __ROGUE_INTERFACES_STREAM_FRAME_ITERATOR_H__
#define __ROGUE_INTERFACES_STREAM_FRAME_ITERATOR_H__
#include <stdint.h>
#include <vector>

namespace rogue {
   namespace interfaces {
      namespace stream {

         //! Frame iterator
         /** The FrameIterator class imeplements a C++ standard random access iterator
          * with a base type of uint8_t.
          *
          * This class is not available in Python.
          */
         class FrameIterator : public std::iterator<std::random_access_iterator_tag, uint8_t> {

            friend class Frame;

               // write flag
               bool write_;

               // Associated frame
               boost::shared_ptr<rogue::interfaces::stream::Frame> frame_;

               // Frame position
               uint32_t framePos_;

               // Frame size
               uint32_t frameSize_;

               // current buffer
               std::vector<boost::shared_ptr<rogue::interfaces::stream::Buffer> >::iterator buff_;

               // Buffer position
               uint32_t buffPos_;

               // Buffer size
               uint32_t buffSize_;

               // Current buffer iterator
               uint8_t * data_;

               // Creator
               FrameIterator(boost::shared_ptr<rogue::interfaces::stream::Frame> frame, bool write, bool end);

               // adjust position
               void adjust(int32_t diff);

            public:

               //! Create an empty iterator for later assignment.
               FrameIterator();

               //! Copy assignment
               /** Copy the state of another iterator into the current iterator.
                */
               const rogue::interfaces::stream::FrameIterator operator =(
                     const rogue::interfaces::stream::FrameIterator &rhs);

               //! Get iterator marking the end fo the current Buffer
               /** The returned iterator is an end marker for the current buffer, and
                * possibly the end of the frame. If the current Buffer is followed by 
                * another buffer containing valid data for a Read or available space for a write,
                * the returned iterator will mark the start of the next Buffer. Having this
                * iterator is usefull when iterating through contigous memory blocks for more 
                * effeciant data copying when using std::copy().
                * @return Iterator marking the end of the current Buffer
                */
               rogue::interfaces::stream::FrameIterator endBuffer();

               //! Get remaining bytes in current buffer
               /** Similiar to the endBuffer() call, this method returns the remaining bytes
                * in the current Buffer. 
                * @return Remaining bytes in the current Buffer.
                */
               uint32_t remBuffer();

               //! De-reference
               /** This allows data at the current iterator position to be accessed
                * using a *it de-reference
                */
               uint8_t & operator *() const;

               //uint8_t * operator ->() const;

               //! Return uint8_t pointer to current position
               /**
                * @return uint8_t pointer to current position
                */
               uint8_t * ptr() const;

               //! De-reference by index
               /** Returns the data value at the passed releative offset
                * @param offset Relative offset to access
                * @return Data value at passed offset
                */
               uint8_t operator [](const uint32_t &offset) const;

               //! Pre-increment the iterator position
               /** Increment the current iterator position by a single location
                * and return a reference to the current iterator.
                * @return Reference to iterator at the new position.
                */
               const rogue::interfaces::stream::FrameIterator & operator ++();

               //! Post-increment the iterator position
               /** Increment the current iterator position by a single location
                * and return a reference to the previous iterator position. This
                * results in a copy of the iterator being created before the increment.
                * @return Reference to iterator at the old position.
                */
               rogue::interfaces::stream::FrameIterator operator ++(int);

               //! Pre-decrement the iterator position
               /** Decrement the current iterator position by a single location
                * and return a reference to the current iterator.
                * @return Reference to iterator at the new position.
                */
               const rogue::interfaces::stream::FrameIterator & operator --();

               //! Post-decrement the iterator position
               /** Decrement the current iterator position by a single location
                * and return a reference to the previous iterator position. This
                * results in a copy of the iterator being created before the decrement.
                * @return Reference to iterator at the old position.
                */
               rogue::interfaces::stream::FrameIterator operator --(int);

               //! Not Equal
               /** Compare this iterator to another iterator and return True if they are at
                * different positions.
                * @return True if the two iterators are not equal
                */
               bool operator !=(const rogue::interfaces::stream::FrameIterator & other) const;

               //! Equal
               /** Compare this iterator to another iterator and return True if they are 
                * reference the same position within the Frame.
                * @return True if the two iterators are equal
                */
               bool operator ==(const rogue::interfaces::stream::FrameIterator & other) const;

               //! Less than
               /** Compare this iterator to another iterator and return True if the local
                * interator (left of <) is less than the iterator being compare against.
                * @return True if the left iterator is less than the right.
                */
               bool operator <(const rogue::interfaces::stream::FrameIterator & other) const;

               //! Greater than
               /** Compare this iterator to another iterator and return True if the local
                * interator (left of >) is greater than the iterator being compare against.
                * @return True if the left iterator is greater than the right.
                */
               bool operator >(const rogue::interfaces::stream::FrameIterator & other) const;

               //! Less than or equal to
               /** Compare this iterator to another iterator and return True if the local
                * interator (left of <=) is less than or equal to the iterator being compare against.
                * @return True if the left iterator is less than or equal to the right.
                */
               bool operator <=(const rogue::interfaces::stream::FrameIterator & other) const;

               //! Greater than or equal to
               /** Compare this iterator to another iterator and return True if the local
                * interator (left of >=) is greater than or equal to the iterator being compare against.
                * @return True if the left iterator is greater than or equal to the right.
                */
               bool operator >=(const rogue::interfaces::stream::FrameIterator & other) const;

               //! Increment by value
               /** Create a new iterator and increment its position by the passed value.
                * @param add Positive or negative value to increment the current postion by.
                * @return New iterator at the new position
                */
               rogue::interfaces::stream::FrameIterator operator +(const int32_t &add) const;

               //! Decrement by value
               /** Create a new iterator and decrement its position by the passed value.
                * @param sub Positive or negative value to decrement the current postion by.
                * @return New iterator at the new position
                */
               rogue::interfaces::stream::FrameIterator operator -(const int32_t &sub) const;

               //! Subtract incrementers
               /** Return the difference between the current incrmentor position (left of -) and
                * the compared incrementer position.
                * @return Different of the two postions as a int32_t
                */
               int32_t operator -(const rogue::interfaces::stream::FrameIterator &other) const;

               //! Increment by value
               /** Increment the current interator by the passed value
                * @param add Positive or negative value to increment the current postion by.
                * @return Reference to current intertor at the new position
                */
               rogue::interfaces::stream::FrameIterator & operator +=(const int32_t &add);

               //! Decrement by value
               /** Decrement the current interator by the passed value
                * @param sub Positive or negative value to decrement the current postion by.
                * @return Reference to current intertor at the new position
                */
               rogue::interfaces::stream::FrameIterator & operator -=(const int32_t &sub);

         };

         //! Inline helper function to copy values to a frame iterator
         /** This helper function copies from the passed data pointer into the 
          * Frame at the iterator position. The iterator is incremented by the copy size.
          * @param iter FrameIterator at position to copy the data to
          * @param size The number of bytes to copy
          * @param src Pointer to data source
          */
         inline void toFrame ( rogue::interfaces::stream::FrameIterator & iter, uint32_t size, void * src) {
            iter = std::copy((uint8_t*)src, ((uint8_t*)src)+size, iter);
         }

         //! Inline helper function to copy values from a frame iterator
         /** This helper function copies data Frame at the iterator location
          * into the passed data pointer. The iterator is updated by tye copy size.
          * @param iter FrameIterator at position to copy the data from
          * @param size The number of bytes to copy
          * @param dst Pointer to data destination
          */
         inline void fromFrame ( rogue::interfaces::stream::FrameIterator & iter, uint32_t size, void * dst) {
            std::copy(iter,iter+size,(uint8_t*)dst);
            iter += size;
         }
      }
   }
}

#endif
