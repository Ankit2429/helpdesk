import threading
from collections import defaultdict
from typing import Callable, Any, Dict, List

class EventBus:
    """Simple thread‑safe publish/subscribe event bus.

    Usage::
        bus = EventBus()
        bus.subscribe('QueryReceived', handler_func)
        bus.publish('QueryReceived', payload)
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Any], None]]] = defaultdict(list)
        self._lock = threading.RLock()

    def subscribe(self, event_name: str, handler: Callable[[Any], None]) -> None:
        """Register *handler* to be called when *event_name* is published.

        The handler receives the event payload (any python object).
        """
        with self._lock:
            self._subscribers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: Callable[[Any], None]) -> None:
        """Remove a previously registered *handler* for *event_name*.
        """
        with self._lock:
            if handler in self._subscribers[event_name]:
                self._subscribers[event_name].remove(handler)
                if not self._subscribers[event_name]:
                    del self._subscribers[event_name]

    def publish(self, event_name: str, payload: Any = None) -> None:
        """Publish an event to all subscribed handlers.

        The call is non‑blocking; each handler is invoked in its own daemon thread
        to avoid slowing down the main pipeline.
        """
        with self._lock:
            handlers = list(self._subscribers.get(event_name, []))
        for handler in handlers:
            threading.Thread(target=handler, args=(payload,), daemon=True).start()
