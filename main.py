import websocket
import requests
import rel
import json
from enum import Enum
from typing import List

# The IP address or hostname of the board client.
API_URL = "localhost"
# The port of the board client. Default is 3180.
API_PORT = "3180"


# The possible event types that the board can send.
class EventType(Enum):
    STARTING = "Starting"
    STARTED = "Started"
    STOPPING = "Stopping"
    STOPPED = "Stopped"
    THROW_DETECTED = "Throw detected"
    TAKEOUT_STARTED = "Takeout started"
    TAKEOUT_FINISHED = "Takeout finished"
    MANUAL_RESET = "Manual reset"
    CALIBRATION_STARTED = "Calibration started"
    CALIBRATION_FINISHED = "Calibration finished"
    CALIBRATION_FAILED = "Calibration failed"


# The possible status types that the board can have.
class StatusType(Enum):
    STARTING = "Starting"
    STOPPING = "Stopping"
    STOPPED = "Stopped"
    THROW = "Throw"
    TAKEOUT = "Takeout"
    TAKEOUT_IN_PROGRESS = "Takeout in progress"
    CALIBRATING = "Calibrating"


# The possible beds of a segment.
class SegmentBed(Enum):
    SINGLE_INNER = "SingleInner"
    SINGLE_OUTER = "SingleOuter"
    DOUBLE = "Double"
    TRIPLE = "Triple"
    OUTSIDE = "Outside"


# The segment of a dart board. This is the smallest unit of the board.
class Segment:
    # The bed of the segment. See SegmentBed for possible values.
    bed: SegmentBed
    # The multiplier of the segment. 1 for single, 2 for double, 3 for triple, 0 for miss.
    multiplier: int
    # The number of the segment. 1-20 for the standard segments, 25 for the bullseye, 0 for miss.
    number: int
    # The name of the segment. This is a human-readable name of the segment like "T20" or "S1".
    name: str

    def __init__(self, bed, multiplier, number, name):
        self.bed = bed
        self.multiplier = multiplier
        self.number = number
        self.name = name


# A throw that was detected by the board.
class Throw:
    segment: Segment

    def __init__(self, segment):
        self.segment = segment


# The message that the board sends.
class Message:
    # Indicates whether Auto
    running: bool = False
    # Indicates whether the detection loop is running or paused
    connected: bool = False

    # The current status of the board
    status: StatusType
    # The event type of the message
    event: EventType

    # The number of throws the system has detected and "knows" about
    num_throws: int = 0
    # The list of throws in memory. This field will be ommited if `numThrows` is 0.
    # The last entry in the list is the latest throw that was detected.
    throws: List[Throw]

    def __init__(self, data):
        self.connected = data["connected"]
        self.running = data["running"]
        self.status = StatusType(data["status"])
        self.event = EventType(data["event"])
        self.num_throws = data["numThrows"]
        if "throws" in data:
            self.throws = [
                Throw(
                    Segment(
                        SegmentBed(t["segment"]["bed"]),
                        t["segment"]["multiplier"],
                        t["segment"]["number"],
                        t["segment"]["name"],
                    )
                )
                for t in data["throws"]
            ]


# Handler for the WebSocket messages.
def on_message(ws, message):
    data = json.loads(message)

    if data["type"] != "state":
        return

    # See `example.jsonc` for reference.

    msg = Message(data["data"])
    if msg.event == EventType.THROW_DETECTED:
        segment = msg.throws[len(msg.throws) - 1].segment
        score = segment.multiplier * segment.number
        print(msg.event, msg.status, msg.num_throws, segment.name, score)
    else:
        print(msg.event, msg.status)


# Handler for the WebSocket errors.
def on_error(ws, error):
    print("error:", error)


# Handler for the WebSocket close event.
def on_close(ws, close_status_code, close_msg):
    print("### closed ###")


# Handler for the WebSocket open event.
def on_open(ws):
    print("### opened ###")


# The board can be started with this request.
# PUT /api/start
def start_board():
    requests.put(f"http://{API_URL}:{API_PORT}/api/start")


# The board can be stopped (think paused) with this request.
# PUT /api/stop
def stop_board():
    requests.put(f"http://{API_URL}:{API_PORT}/api/stop")


# If the board ever gets stuck, you can reset it with this request.
# POST /api/reset
def reset_board():
    requests.post(f"http://{API_URL}:{API_PORT}/api/reset")


if __name__ == "__main__":
    # Initialize the WebSocket connection.
    ws = websocket.WebSocketApp(
        # The base url is /api/events to connect to the WebSocket.
        # You can use the `type` query parameter to filter the events you want to receive.
        # The type you are interested in is `state`.
        f"ws://{API_URL}:{API_PORT}/api/events?type=state",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )

    # Run forever with reconnects.
    ws.run_forever(dispatcher=rel, reconnect=5)

    # Keyboard interrupt to stop the program.
    rel.signal(2, rel.abort)
    rel.dispatch()
