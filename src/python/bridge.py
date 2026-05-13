import zmq
import json
import time

class SignalPublisher:
    """
    Broadcasts live execution tickets to the C++ engine via ZeroMQ.
    Uses a PUB/SUB pattern for low-latency, one-to-many distribution.
    """
    def __init__(self, port=5555):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.setsockopt(zmq.LINGER, 1000) # Ensure messages are flushed before close
        self.socket.bind(f"tcp://*:{port}")
        print(f"ZeroMQ Signal Bridge active on port {port}")

    def publish_tickets(self, tickets):
        """
        Serializes and sends execution tickets.
        Topic: 'trading.signals'
        """
        if not tickets:
            return

        message = {
            'timestamp': time.time(),
            'count': len(tickets),
            'tickets': tickets
        }
        
        # Send as Multi-part message: [Topic, Payload]
        self.socket.send_string("trading.signals", zmq.SNDMORE)
        self.socket.send_string(json.dumps(message))
        print(f"Published {len(tickets)} tickets to C++ bridge.")

    def close(self):
        self.socket.close()
        self.context.term()
