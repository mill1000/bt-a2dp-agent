#!/usr/bin/env python3

import argparse
import asyncio
import logging

from dbus_fast import BusType, DBusError, Variant
from dbus_fast.aio import MessageBus
from dbus_fast.service import ServiceInterface, method

_LOGGER = logging.getLogger("a2dp-agent")

A2DP_UUID = "0000110d-0000-1000-8000-00805f9b34fb"

DBUS_PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"

BLUEZ_AGENT_INTERFACE = "org.bluez.Agent1"
BLUEZ_AGENT_MANAGER_INTERFACE = "org.bluez.AgentManager1"
BLUEZ_ADAPTER_INTERFACE = "org.bluez.Adapter1"

BLUEZ_BUS_NAME = "org.bluez"
BLUEZ_BUS_PATH = "/org/bluez"

AGENT_PATH = "/local/ad2pagent"


class A2dpAgent(ServiceInterface):
    def __init__(self):
        super().__init__(BLUEZ_AGENT_INTERFACE)

    @method()
    def Release(self):
        pass

    @method()
    def AuthorizeService(self, device: 'o', uuid: 's'):
        _LOGGER.debug("Authorize Service Device: %s, UUID: %s", device, uuid)
        if uuid == A2DP_UUID:
            _LOGGER.info("Authorized A2DP service from device: %s.", device)
            return

        print("Rejecting non-A2DP service from device %s.", device)
        raise DBusError('org.bluez.Error.Rejected', 'Connection rejected')

    @method()
    def RequestPinCode(self, device: 'o') -> 's':
        _LOGGER.debug("Request Pin Code Device: %s", device)
        return "0000"

    @method()
    def DisplayPinCode(self, device: 'o', pincode: 's'):
        _LOGGER.debug("Display Pin Code Device: %s, Code: %s", device, pincode)

    @method()
    def RequestPasskey(self, device: 'o') -> 'u':
        _LOGGER.debug("Request Passkey Device: %s", device)
        return 0000

    @method()
    def DisplayPasskey(self, device: 'o', passkey: 'u', _entered: 'q'):
        _LOGGER.debug("Display Passkey Device: %s, Passkey: %s",
                      device, passkey)

    @method()
    def RequestConfirmation(self, device: 'o', passkey: 'u'):
        _LOGGER.debug(
            "Request Confirmation Device: %s, Passkey: %s", device, passkey)

    @method()
    def RequestAuthorization(self, device: 'o'):
        _LOGGER.debug("Request Authorization Device: %s", device)
        raise DBusError('org.bluez.Error.Rejected', 'Connection rejected')

    @method()
    def Cancel(self):
        pass


async def _run(args):
    _LOGGER.info("Connecting to system bus.")
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

    device_path = f"{BLUEZ_BUS_PATH}/{args.device}"

    introspection = await bus.introspect(BLUEZ_BUS_NAME, device_path)
    proxy_object = bus.get_proxy_object(
        BLUEZ_BUS_NAME, device_path, introspection)
    properties = proxy_object.get_interface(DBUS_PROPERTIES_INTERFACE)

    _LOGGER.info("Enabling infinite discovery on device: %s.", args.device)
    await properties.call_set(BLUEZ_ADAPTER_INTERFACE, "DiscoverableTimeout", Variant('u', 0))
    await properties.call_set(BLUEZ_ADAPTER_INTERFACE, "Discoverable", Variant('b', True))

    # Get agent manager from bluez
    introspection = await bus.introspect(BLUEZ_BUS_NAME, BLUEZ_BUS_PATH)
    proxy_object = bus.get_proxy_object(
        BLUEZ_BUS_NAME, BLUEZ_BUS_PATH, introspection)
    manager = proxy_object.get_interface(BLUEZ_AGENT_MANAGER_INTERFACE)

    # Create agent
    agent = A2dpAgent()
    bus.export(AGENT_PATH, agent)

    # Register agent and set as default
    _LOGGER.info("Registering agent.")
    await manager.call_register_agent(AGENT_PATH, "NoInputNoOutput")
    await manager.call_request_default_agent(AGENT_PATH)

    await bus.wait_for_disconnect()


def main():
    # Basic log config
    logging.basicConfig(level=logging.INFO)

    # Argument parsing
    parser = argparse.ArgumentParser(
        description="Bluetooth agent that accepts A2DP connections.")
    parser.add_argument(
        "--verbose", help="Enable debug messages.", action="store_true")
    parser.add_argument("device", help="Bluetooth device.")
    args = parser.parse_args()

    if args.verbose:
        _LOGGER.setLevel(logging.DEBUG)

    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
