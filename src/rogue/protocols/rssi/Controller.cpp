
/**
 *-----------------------------------------------------------------------------
 * Title      : RSSI Controller
 * ----------------------------------------------------------------------------
 * File       : Controller.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * RSSI Controller
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
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/protocols/rssi/Header.h>
#include <rogue/protocols/rssi/Controller.h>
#include <rogue/protocols/rssi/Transport.h>
#include <rogue/protocols/rssi/Application.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <boost/pointer_cast.hpp>
#include <rogue/common.h>
#include <sys/syscall.h>
#include <math.h>

namespace rpr = rogue::protocols::rssi;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rpr::ControllerPtr rpr::Controller::create ( uint32_t segSize, 
                                             rpr::TransportPtr tran, 
                                             rpr::ApplicationPtr app ) {
   rpr::ControllerPtr r = boost::make_shared<rpr::Controller>(segSize,tran,app);
   return(r);
}

void rpr::Controller::setup_python() {
   // Nothing to do
}

//! Creator
rpr::Controller::Controller ( uint32_t segSize, rpr::TransportPtr tran, rpr::ApplicationPtr app ) {
   app_  = app;
   tran_ = tran;

   dropCount_   = 0;
   nextSeqRx_   = 0;
   lastAckRx_   = 0;
   tranBusy_    = false;

   lastSeqRx_   = 0;

   state_       = StClosed;
   gettimeofday(&stTime_,NULL);
   prevAckRx_   = 0;
   downCount_   = 0;
   retranCount_ = 0;

   txListCount_ = 0;
   lastAckTx_   = 0;
   locSequence_ = 100;
   gettimeofday(&txTime_,NULL);

   locConnId_     = 0x12345678;
   remMaxBuffers_ = 0;
   remMaxSegment_ = 100;
   retranTout_    = ReqRetranTout;
   cumAckTout_    = ReqCumAckTout;
   nullTout_      = ReqNullTout;
   maxRetran_     = ReqMaxRetran;
   maxCumAck_     = ReqMaxCumAck;
   remConnId_     = 0;
   segmentSize_   = segSize;

   // Start read thread
   thread_ = new boost::thread(boost::bind(&rpr::Controller::runThread, this));
}

//! Destructor
rpr::Controller::~Controller() { 
   thread_->interrupt();
   thread_->join();
}

//! Transport frame allocation request
ris::FramePtr rpr::Controller::reqFrame ( uint32_t size, uint32_t maxBuffSize ) {
   ris::FramePtr  frame;
   ris::BufferPtr buffer;
   uint32_t       nSize;

   // Request only single buffer frames.
   // Frame size returned is never greater than remote max size
   // or local segment size
   nSize = size + rpr::Header::HeaderSize;
   if ( nSize > remMaxSegment_ && remMaxSegment_ > 0 ) nSize = remMaxSegment_;
   if ( nSize > segmentSize_  ) nSize = segmentSize_;

   // Forward frame request to transport slave
   frame = tran_->reqFrame (nSize, false, nSize);
   buffer = frame->getBuffer(0);

   // Make sure there is enough room in first buffer for our header
   if ( buffer->getAvailable() < rpr::Header::HeaderSize )
      throw(rogue::GeneralError::boundary("rss::Controller::reqFrame",
                                          rpr::Header::HeaderSize,
                                          buffer->getAvailable()));

   // Update first buffer to include our header space.
   buffer->setHeadRoom(buffer->getHeadRoom() + rpr::Header::HeaderSize);

   // Trim multi buffer frames
   if ( frame->getCount() > 1 ) {
      frame = ris::Frame::create();
      frame->appendBuffer(buffer);
   }

   //printf("RSSI returning frame with size = %i\n",frame->getAvailable());

   // Return frame
   return(frame);
}

//! Frame received at transport interface
void rpr::Controller::transportRx( ris::FramePtr frame ) {

   rpr::HeaderPtr head = rpr::Header::create(frame);

   if ( frame->getCount() == 0 || ! head->verify() ) dropCount_++;

   //printf("Got frame: \n%s\n",head->dump().c_str());

   // Ack set
   if ( head->getAck() ) lastAckRx_ = head->getAcknowledge();

   // Update busy bit
   tranBusy_ = head->getBusy();

   // Syn frame and resets go to state machine if state = open 
   // or we are waiting for ack replay
   if ( ( state_ == StOpen || state_ == StWaitSyn) && 
        ( head->getSyn() || head->getRst() ) ) {
      PyRogue_BEGIN_ALLOW_THREADS;
      stQueue_.push(head);
      PyRogue_END_ALLOW_THREADS;
   }

   // Data or NULL in the correct sequence or syn go to application
   // Syn is passed to update sequence receive tracking
   if ( head->getSyn() || ( state_ == StOpen && 
       (head->getNul() || frame->getPayload() > rpr::Header::HeaderSize ) &&
       (head->getSequence() == nextSeqRx_ ) ) ) {

      if ( head->getSyn() ) nextSeqRx_ = head->getSequence()+1;
      else nextSeqRx_++;

      PyRogue_BEGIN_ALLOW_THREADS;
      appQueue_.push(head);
      PyRogue_END_ALLOW_THREADS;
   }

   stCond_.notify_all();
}

//! Frame transmit at application interface
// Called by application class thread
ris::FramePtr rpr::Controller::applicationTx() {
   ris::FramePtr  frame;
   rpr::HeaderPtr head;

   while(!frame) {

      PyRogue_BEGIN_ALLOW_THREADS;
      head = appQueue_.pop();
      PyRogue_END_ALLOW_THREADS;

      lastSeqRx_ = head->getSequence();
      stCond_.notify_all();

      if ( ! ( head->getNul() || head->getSyn() ) ) {
         frame = head->getFrame();
         frame->getBuffer(0)->setHeadRoom(frame->getBuffer(0)->getHeadRoom() + rpr::Header::HeaderSize);
      }
   }
   return(frame);
}

//! Frame received at application interface
void rpr::Controller::applicationRx ( ris::FramePtr frame ) {
   ris::FramePtr tranFrame;

   if ( frame->getCount() == 0 ) 
      throw(rogue::GeneralError("rss::Controller::applicationRx","Frame must not be empty"));

   // First buffer of frame does not have enough room for header
   if ( frame->getBuffer(0)->getHeadRoom() < rpr::Header::HeaderSize )
      throw(rogue::GeneralError::boundary("rss::Controller::applicationRx",
                                          rpr::Header::HeaderSize,
                                          frame->getBuffer(0)->getHeadRoom()));

   // Adjust header in first buffer
   frame->getBuffer(0)->setHeadRoom(frame->getBuffer(0)->getHeadRoom() - rpr::Header::HeaderSize);

   // Map to RSSI 
   rpr::HeaderPtr head = rpr::Header::create(frame);
   head->txInit(false,false);
   head->setAck(true);

   PyRogue_BEGIN_ALLOW_THREADS;

   // Wait while busy either by flow control or buffer starvation
   while ( txListCount_ >= remMaxBuffers_ && state_ == StOpen ) usleep(10);

   // Connection is closed
   if ( state_ != StOpen ) return;

   // Transmit
   boost::unique_lock<boost::mutex> lock(txMtx_);
   transportTx(head,true);
   lock.unlock();

   PyRogue_END_ALLOW_THREADS;
   stCond_.notify_all();
}

//! Get state
bool rpr::Controller::getOpen() {
   return(state_ == StOpen );
}

//! Get Down Count
uint32_t rpr::Controller::getDownCount() {
   return(downCount_);
}

//! Get Drop Count
uint32_t rpr::Controller::getDropCount() {
   return(dropCount_);
}

//! Get Retran Count
uint32_t rpr::Controller::getRetranCount() {
   return(retranCount_);
}

//! Get busy
bool rpr::Controller::getBusy() {
   return(appQueue_.size() > BusyThold);
}

// Method to transit a frame with proper updates
void rpr::Controller::transportTx(rpr::HeaderPtr head, bool seqUpdate) {
   head->setSequence(locSequence_);

   // Update sequence numbers
   if ( seqUpdate ) {
      txList_[locSequence_] = head;
      txListCount_++;
      locSequence_++;
   }

   // Setup header
   head->setAcknowledge(lastSeqRx_);
   head->setBusy(appQueue_.size() > BusyThold);
   head->update();

   lastAckTx_ = lastSeqRx_;

   // Track last tx time
   gettimeofday(&txTime_,NULL);

   // Send frame
   //printf("Sending frame: \n%s\n",head->dump().c_str());
   tran_->sendFrame(head->getFrame());
}

//! Convert rssi time to microseconds
uint32_t rpr::Controller::convTime ( uint32_t rssiTime ) {
   return(rssiTime * std::pow(10,TimeoutUnit));
}

//! Helper function to determine if time has elapsed
bool rpr::Controller::timePassed ( struct timeval *lastTime, uint32_t rssiTime ) {
   struct timeval endTime;
   struct timeval sumTime;
   struct timeval currTime;

   uint32_t usec = convTime(rssiTime);

   gettimeofday(&currTime,NULL);

   sumTime.tv_sec = (usec / 1000000);
   sumTime.tv_usec = (usec % 1000000);
   timeradd(lastTime,&sumTime,&endTime);

   return(timercmp(&currTime,&endTime,>));
}

//! Background thread
void rpr::Controller::runThread() {
   uint32_t wait;

   wait = 0;

   printf("RSSI::Controller PID=%i, TID=%li\n",getpid(),syscall(SYS_gettid));

   try {
      while(1) {

         // Lock context
         if ( wait > 0 ) {
            // Wait on condition or timeout
            boost::unique_lock<boost::mutex> lock(stMtx_);

            // Adjustable wait
            stCond_.timed_wait(lock,boost::posix_time::microseconds(wait));
         }

         switch(state_) {

            case StClosed  :
            case StWaitSyn :
               wait = stateClosedWait();
               break;

            case StSendSeqAck :
               wait = stateSendSeqAck();
               break;

            case StOpen :
               wait = stateOpen();
               break;

            case StError :
               wait = stateError();
               break;
            default :
               break;
         }    
      }
   } catch (boost::thread_interrupted&) { }

   // Send reset on exit
   stateError();
}

//! Closed/Waiting for Syn
uint32_t rpr::Controller::stateClosedWait () {
   rpr::HeaderPtr head;

   // got syn or reset
   if ( ! stQueue_.empty() ) {
      head = stQueue_.pop();

      // Reset
      if ( head->getRst() ) state_ = StClosed;

      // Syn ack
      else if ( head->getSyn() && head->getAck() ) {
         remMaxBuffers_ = head->getMaxOutstandingSegments();
         remMaxSegment_ = head->getMaxSegmentSize();
         retranTout_    = head->getRetransmissionTimeout();
         cumAckTout_    = head->getCumulativeAckTimeout();
         nullTout_      = head->getNullTimeout();
         maxRetran_     = head->getMaxRetransmissions();
         maxCumAck_     = head->getMaxCumulativeAck();
         prevAckRx_     = head->getAcknowledge();
         state_         = StSendSeqAck;
         gettimeofday(&stTime_,NULL);
      }
   }

   // Generate syn after try period passes
   else if ( timePassed(&stTime_,TryPeriod) ) {

      // Allocate frame
      head = rpr::Header::create(tran_->reqFrame(rpr::Header::SynSize,false,rpr::Header::SynSize));

      // Set frame
      head->txInit(true,true);
      head->setVersion(Version);
      head->setChk(true);
      head->setMaxOutstandingSegments(LocMaxBuffers);
      head->setMaxSegmentSize(segmentSize_);
      head->setRetransmissionTimeout(retranTout_);
      head->setCumulativeAckTimeout(cumAckTout_);
      head->setNullTimeout(nullTout_);
      head->setMaxRetransmissions(maxRetran_);
      head->setMaxCumulativeAck(maxCumAck_);
      head->setTimeoutUnit(TimeoutUnit);
      head->setConnectionId(locConnId_);

      boost::unique_lock<boost::mutex> lock(txMtx_);
      transportTx(head,true);
      lock.unlock();

      // Update state
      gettimeofday(&stTime_,NULL);
      state_ = StWaitSyn;
   }

   return(convTime(TryPeriod) / 4);
}

//! Send sequence ack
uint32_t rpr::Controller::stateSendSeqAck () {

   // Allocate frame
   rpr::HeaderPtr ack = rpr::Header::create(tran_->reqFrame(rpr::Header::HeaderSize,false,rpr::Header::HeaderSize));

   // Setup frame
   ack->txInit(false,true);
   ack->setAck(true);
   ack->setNul(false);

   boost::unique_lock<boost::mutex> lock(txMtx_);
   transportTx(ack,false);
   lock.unlock();

   // Update state
   state_ = StOpen;
   //printf("RSSI State = Open\n");
   return(convTime(cumAckTout_/2));
}

//! Idle with open state
uint32_t rpr::Controller::stateOpen () {
   rpr::HeaderPtr head;
   uint8_t idx;
   bool doNull;
   uint8_t locAckRx;
   uint8_t locSeqRx;
   uint8_t locSeqTx;
   uint8_t ackPend;
   struct timeval locTime;

   // Sample once
   locAckRx = lastAckRx_; // Sample once
   locSeqRx = lastSeqRx_; // Sample once
   locSeqTx = locSequence_-1;

   // Pending frame is an error
   if ( ! stQueue_.empty() ) {
      head = stQueue_.pop();
      state_ = StError;
      gettimeofday(&stTime_,NULL);
      return(0);
   }

   // Update ack states
   if ( locAckRx != prevAckRx_ ) {
      boost::unique_lock<boost::mutex> lock(txMtx_);
      while ( locAckRx != prevAckRx_ ) {
         prevAckRx_++;
         txList_[prevAckRx_].reset();
         txListCount_--;
      }
      lock.unlock();
   }

   // Retransmission processing
   if ( locAckRx != locSeqTx ) {
      boost::unique_lock<boost::mutex> lock(txMtx_);

      // Walk through each frame in list, looking for first expired
      for ( idx=locAckRx+1; idx != ((locSeqTx+1)%256); idx++ ) {
         head = txList_[idx];

         // Busy set, reset timeout
         if ( tranBusy_ ) head->rstTime();

         else if ( timePassed(head->getTime(),retranTout_) ) {

            // Max retran count reached, close connection
            if ( head->count() >= maxRetran_ ) {
               state_ = StError;
               gettimeofday(&stTime_,NULL);
               return(0);
            }
            else {

               //printf("RSSI Retran. Seq=%i, Ack=%i\n",head->getSequence(),head->getAcknowledge());
               transportTx(head,false);
               retranCount_++;
            }
         }
      }
      lock.unlock();
   }

   // Sample transmit time and compute pending ack count under lock
   {
      boost::unique_lock<boost::mutex> lock(txMtx_);
      locTime = txTime_;

      ackPend = 0;
      for (idx = lastAckTx_; idx != locSeqRx; idx++) ackPend++;
   }

   // NULL required
   if ( timePassed(&locTime,nullTout_/3) ) doNull = true;
   else doNull = false;

   // Outbound frame required
   if ( ( doNull || ackPend >= maxCumAck_ || 
        ((ackPend > 0 || appQueue_.size() > BusyThold) && timePassed(&locTime,cumAckTout_)) ) ) {
      //printf("ack pend = %i, do Null = %i, size = %i\n",ackPend,doNull,appQueue_.size());

      head = rpr::Header::create(tran_->reqFrame(rpr::Header::HeaderSize,false,rpr::Header::HeaderSize));
      head->txInit(false,true);
      head->setAck(true);
      head->setNul(doNull);

      boost::unique_lock<boost::mutex> lock(txMtx_);
      transportTx(head,doNull);
      lock.unlock();
   }

   return(convTime(cumAckTout_/2));
}

//! Error
uint32_t rpr::Controller::stateError () {
   rpr::HeaderPtr rst;
   uint32_t x;

   rst = rpr::Header::create(tran_->reqFrame(rpr::Header::HeaderSize,false,rpr::Header::HeaderSize));
   rst->txInit(false,true);
   rst->setRst(true);
   //printf("Sending RST:\n%s\n",rst->dump().c_str());

   boost::unique_lock<boost::mutex> lock(txMtx_);
   transportTx(rst,true);

   // Reset tx list
   for (x=0; x < 256; x++) txList_[x].reset();
   txListCount_ = 0;

   lock.unlock();

   //printf("RSSI state set to closed\n");
   downCount_++;
   state_ = StClosed;

   // Resest queues
   appQueue_.reset();
   stQueue_.reset();

   gettimeofday(&stTime_,NULL);
   return(convTime(TryPeriod));
}
