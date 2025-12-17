import asyncio
import serial_asyncio



class BrooksSLA:


    def __init__(self, port: str, baud: int) -> None:
        self._port = port
        self._baud = baud

