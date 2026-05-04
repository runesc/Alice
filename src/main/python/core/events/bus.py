from __future__ import annotations
import asyncio
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass(order=True)
class _Subscription:
    priority: int
    plugin_id: str
    handler: Callable = field(compare=False)
    is_async: bool = field(default=False, compare=False)


class EventBus:
    """
    Event Bus desacoplado con soporte async, prioridades y
    aislamiento por plugin.
    
    - Thread-safe: usa RLock para suscripciones
    - Async: handlers async son ejecutados en el event loop de Qt
    - Prioridades: mayor número = se ejecuta antes
    - Aislamiento: errores en un handler no bloquean los demás
    """

    def __init__(self) -> None:
        self._subscriptions: dict[str, list[_Subscription]] = defaultdict(list)
        self._lock = threading.RLock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(
        self,
        event: str,
        handler: Callable,
        plugin_id: str = "core",
        priority: int = 0,
    ) -> None:
        is_async = asyncio.iscoroutinefunction(handler)
        sub = _Subscription(priority=-priority, plugin_id=plugin_id,
                            handler=handler, is_async=is_async)
        with self._lock:
            self._subscriptions[event].append(sub)
            self._subscriptions[event].sort()  # orden por prioridad

    def unsubscribe(self, event: str, handler: Callable) -> None:
        with self._lock:
            subs = self._subscriptions.get(event, [])
            self._subscriptions[event] = [s for s in subs if s.handler != handler]

    def unsubscribe_all(self, plugin_id: str) -> None:
        """Eliminar todos los handlers de un plugin (llamado en on_disable)."""
        with self._lock:
            for event in list(self._subscriptions):
                self._subscriptions[event] = [
                    s for s in self._subscriptions[event]
                    if s.plugin_id != plugin_id
                ]

    def emit(self, event: str, payload: Any = None) -> None:
        """
        Emitir evento. Ejecuta handlers síncronos en el hilo actual,
        handlers async en el event loop configurado.
        Los errores en handlers son capturados y logeados, nunca propagados.
        """
        with self._lock:
            subs = list(self._subscriptions.get(event, []))

        for sub in subs:
            try:
                if sub.is_async:
                    if self._loop and self._loop.is_running():
                        asyncio.run_coroutine_threadsafe(
                            sub.handler(event, payload), self._loop
                        )
                    else:
                        logger.warning(f"No hay event loop para handler async de '{event}'")
                else:
                    sub.handler(event, payload)
            except Exception:
                logger.exception(
                    f"Error en handler del plugin '{sub.plugin_id}' "
                    f"para evento '{event}'"
                )

    async def emit_async(self, event: str, payload: Any = None) -> None:
        """Versión async del emit para contextos await."""
        with self._lock:
            subs = list(self._subscriptions.get(event, []))

        for sub in subs:
            try:
                if sub.is_async:
                    await sub.handler(event, payload)
                else:
                    sub.handler(event, payload)
            except Exception:
                logger.exception(
                    f"Error en handler async del plugin '{sub.plugin_id}' "
                    f"para evento '{event}'"
                )

    def once(self, event: str, handler: Callable, plugin_id: str = "core") -> None:
        """Suscribirse a un evento una sola vez."""
        def _wrapper(evt: str, payload: Any) -> None:
            self.unsubscribe(event, _wrapper)
            handler(evt, payload)
        self.subscribe(event, _wrapper, plugin_id=plugin_id)