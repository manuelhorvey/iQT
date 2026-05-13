import zmq
import json
import time

class SignalPublisher:
    """
    Broadcasts live execution tickets to the C++ engine via ZeroMQ.
    Uses a PUSH/PULL pattern to ensure discrete signals are buffered
    if the consumer is briefly busy, unlike PUB/SUB which is lossy.
    """
    def __init__(self, port=5555):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUSH)
        self.socket.setsockopt(zmq.SNDHWM, 1000) # High Water Mark
        self.socket.bind(f"tcp://127.0.0.1:{port}")
        self.sequence_id = 0
        print(f"ZeroMQ Hardened Signal Bridge (PUSH) active on port {port}")

    def publish_tickets(self, tickets):
        """
        Serializes and sends execution tickets with a monotonic sequence ID.
        """
        if not tickets:
            return

        self.sequence_id += 1
        message = {
            'timestamp': time.time(),
            'sequence_id': self.sequence_id,
            'count': len(tickets),
            'tickets': tickets
        }
        
        payload = json.dumps(message)
        self.socket.send_string(payload)
        print(f"Sent Packet #{self.sequence_id} with {len(tickets)} tickets.")

    def close(self):
        self.socket.close()
        self.context.term()
