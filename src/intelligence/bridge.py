import zmq
import json
import time
import logging

logger = logging.getLogger(__name__)

class SignalPublisher:
    """
    Broadcasts live execution tickets to the C++ engine via ZeroMQ.
    Uses a PUSH/PULL pattern to ensure discrete signals are buffered
    if the consumer is briefly busy, unlike PUB/SUB which is lossy.
    """
    def __init__(self, port=5555):
        try:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.PUSH)
            self.socket.setsockopt(zmq.SNDHWM, 1000) # High Water Mark
            self.socket.setsockopt(zmq.IPV4ONLY, 1)  # IPv4 only for security
            self.socket.bind(f"tcp://127.0.0.1:{port}")
            self.sequence_id = 0
            self.port = port
            print(f"ZeroMQ Hardened Signal Bridge (PUSH) active on port {port}")
            logger.info(f"Signal Publisher initialized on port {port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to initialize ZeroMQ socket on port {port}: {e}")
            raise RuntimeError(f"Cannot bind to port {port}. Already in use? Error: {e}")

    def publish_tickets(self, tickets):
        """
        Serializes and sends execution tickets with a monotonic sequence ID.
        Handles transmission errors gracefully.
        """
        if not tickets:
            logger.debug("No tickets to publish")
            return

        try:
            self.sequence_id += 1
            message = {
                'timestamp': time.time(),
                'sequence_id': self.sequence_id,
                'count': len(tickets),
                'tickets': tickets
            }
            
            payload = json.dumps(message)
            self.socket.send_string(payload, zmq.NOBLOCK)
            print(f"Sent Packet #{self.sequence_id} with {len(tickets)} tickets.")
            logger.info(f"Published packet #{self.sequence_id} with {len(tickets)} tickets")
        except zmq.error.Again:
            logger.warning(f"Socket buffer full (EAGAIN) for packet #{self.sequence_id}")
            # Retry with blocking mode
            try:
                self.socket.send_string(payload)
                print(f"[RETRY] Sent Packet #{self.sequence_id} with {len(tickets)} tickets.")
            except zmq.error.ZMQError as e:
                logger.error(f"Failed to send packet #{self.sequence_id}: {e}")
                raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to serialize tickets: {e}")
            raise
        except zmq.error.ZMQError as e:
            logger.error(f"ZMQ transmission error: {e}")
            raise

    def close(self):
        try:
            self.socket.close()
            self.context.term()
            logger.info("Signal Publisher closed")
        except Exception as e:
            logger.error(f"Error closing Signal Publisher: {e}")
