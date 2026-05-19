"""Stub bleak_retry_connector for tests."""
from bleak import BleakClient


class BleakClientWithServiceCache(BleakClient):
    pass


class BleakNotFoundError(Exception):
    pass


async def establish_connection(client_class, ble_device, name, **kwargs):
    client = client_class(ble_device)
    await client.connect()
    return client
