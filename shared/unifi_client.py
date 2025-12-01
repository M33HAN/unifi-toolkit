"""
UniFi API client wrapper using aiounifi
"""
from typing import Optional, Dict, List
import aiohttp
from aiounifi.controller import Controller
from aiounifi.models.client import Client
import ssl
import logging

logger = logging.getLogger(__name__)


class UniFiClient:
    """
    Wrapper around aiounifi for interacting with UniFi controller
    Supports both legacy (username/password) and UniFi OS (API key) authentication
    """

    def __init__(
        self,
        host: str,
        username: str = None,
        password: str = None,
        api_key: str = None,
        site: str = "default",
        verify_ssl: bool = False
    ):
        """
        Initialize UniFi client

        Args:
            host: UniFi controller URL (e.g., https://192.168.1.1:8443)
            username: UniFi username (legacy auth)
            password: UniFi password (legacy auth)
            api_key: UniFi API key (UniFi OS auth)
            site: UniFi site ID (default: "default")
            verify_ssl: Whether to verify SSL certificates
        """
        self.host = host
        self.username = username
        self.password = password
        self.api_key = api_key
        self.site = site
        self.verify_ssl = verify_ssl
        self.controller: Optional[Controller] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self.is_unifi_os = api_key is not None  # UniFi OS if using API key

    async def connect(self) -> bool:
        """
        Connect to the UniFi controller

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Create SSL context
            ssl_context = None
            if not self.verify_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            # Create aiohttp session
            connector = aiohttp.TCPConnector(ssl=ssl_context)

            # Add API key header if using UniFi OS
            headers = {}
            if self.api_key:
                headers['X-API-KEY'] = self.api_key

            self._session = aiohttp.ClientSession(
                connector=connector,
                headers=headers
            )

            if self.is_unifi_os:
                # UniFi OS - test connection with API key
                test_url = f"{self.host}/proxy/network/api/s/{self.site}/stat/device"
                async with self._session.get(test_url) as resp:
                    if resp.status != 200:
                        logger.error(f"UniFi OS API connection failed: {resp.status}")
                        await self.disconnect()
                        return False
                logger.info(f"Successfully connected to UniFi OS at {self.host}")
                return True
            else:
                # Legacy - use aiounifi Controller
                self.controller = Controller(
                    host=self.host,
                    session=self._session,
                    username=self.username,
                    password=self.password,
                    site=self.site,
                    ssl_context=ssl_context
                )

                # Login to controller
                await self.controller.login()
                logger.info(f"Successfully connected to UniFi controller at {self.host}")
                return True

        except Exception as e:
            logger.error(f"Failed to connect to UniFi controller: {e}")
            await self.disconnect()
            return False

    async def disconnect(self):
        """
        Disconnect from the UniFi controller
        """
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None
        self.controller = None

    async def get_clients(self) -> Dict:
        """
        Get all active clients from the UniFi controller

        Returns:
            Dictionary of clients indexed by MAC address
        """
        if not self._session:
            raise RuntimeError("Not connected to UniFi controller. Call connect() first.")

        try:
            if self.is_unifi_os:
                # UniFi OS - make direct API call
                url = f"{self.host}/proxy/network/api/s/{self.site}/stat/sta"
                async with self._session.get(url) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to get clients: {resp.status}")
                        raise RuntimeError(f"API request failed: {resp.status}")

                    data = await resp.json()
                    clients_list = data.get('data', [])

                    # Convert to dictionary indexed by MAC
                    clients_dict = {}
                    for client in clients_list:
                        mac = client.get('mac', '').lower()
                        if mac:
                            # Convert tx/rx rates from Kbps to Mbps
                            tx_rate = client.get('tx_rate')
                            rx_rate = client.get('rx_rate')
                            tx_rate_mbps = round(tx_rate / 1000, 1) if tx_rate else None
                            rx_rate_mbps = round(rx_rate / 1000, 1) if rx_rate else None

                            # Convert to simple dict with needed fields
                            clients_dict[mac] = {
                                'mac': mac,
                                'ap_mac': client.get('ap_mac'),
                                'ip': client.get('ip'),
                                'last_seen': client.get('last_seen'),
                                'rssi': client.get('rssi'),
                                'hostname': client.get('hostname'),
                                'name': client.get('name'),
                                'tx_rate': tx_rate_mbps,
                                'rx_rate': rx_rate_mbps,
                                'channel': client.get('channel'),
                                'radio': client.get('radio'),
                                'uptime': client.get('uptime'),
                                'tx_bytes': client.get('tx_bytes'),
                                'rx_bytes': client.get('rx_bytes'),
                                'blocked': client.get('blocked', False)
                            }

                    return clients_dict
            else:
                # Legacy - use aiounifi Controller
                if not self.controller:
                    raise RuntimeError("Controller not initialized")

                # Initialize/update controller data
                await self.controller.initialize()

                # Return clients dictionary
                return self.controller.clients

        except Exception as e:
            logger.error(f"Failed to get clients from UniFi controller: {e}")
            raise

    async def get_client_by_mac(self, mac_address: str):
        """
        Get a specific client by MAC address

        Args:
            mac_address: MAC address to search for (normalized format)

        Returns:
            Client object/dict if found, None otherwise
        """
        clients = await self.get_clients()
        # Normalize MAC address for lookup (lowercase, colon-separated)
        normalized_mac = mac_address.lower().replace("-", ":").replace(".", ":")
        return clients.get(normalized_mac)

    async def get_access_points(self) -> Dict:
        """
        Get all access points from the UniFi controller

        Returns:
            Dictionary of access points indexed by MAC address
        """
        if not self._session:
            raise RuntimeError("Not connected to UniFi controller. Call connect() first.")

        try:
            if self.is_unifi_os:
                # UniFi OS - make direct API call
                url = f"{self.host}/proxy/network/api/s/{self.site}/stat/device"
                async with self._session.get(url) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to get devices: {resp.status}")
                        raise RuntimeError(f"API request failed: {resp.status}")

                    data = await resp.json()
                    devices_list = data.get('data', [])

                    # Convert to dictionary indexed by MAC, filter for APs
                    aps_dict = {}
                    for device in devices_list:
                        # Only include access points (type 'uap')
                        if device.get('type') == 'uap':
                            mac = device.get('mac', '').lower()
                            if mac:
                                aps_dict[mac] = {
                                    'mac': mac,
                                    'name': device.get('name'),
                                    'model': device.get('model'),
                                    'type': device.get('type')
                                }

                    return aps_dict
            else:
                # Legacy - use aiounifi Controller
                if not self.controller:
                    raise RuntimeError("Controller not initialized")

                # Initialize/update controller data
                await self.controller.initialize()

                # Return devices (access points)
                return self.controller.devices

        except Exception as e:
            logger.error(f"Failed to get access points from UniFi controller: {e}")
            raise

    async def get_ap_name_by_mac(self, ap_mac: str) -> Optional[str]:
        """
        Get the friendly name of an access point by its MAC address

        Args:
            ap_mac: AP MAC address

        Returns:
            AP name if found, None otherwise
        """
        try:
            aps = await self.get_access_points()
            normalized_mac = ap_mac.lower().replace("-", ":").replace(".", ":")
            ap = aps.get(normalized_mac)
            if ap:
                # Handle both dict (UniFi OS) and object (aiounifi) formats
                if isinstance(ap, dict):
                    return ap.get('name') or ap.get('model') or normalized_mac
                else:
                    return ap.name or ap.model or normalized_mac
            return normalized_mac
        except Exception as e:
            logger.error(f"Failed to get AP name for {ap_mac}: {e}")
            return ap_mac

    async def block_client(self, mac_address: str) -> bool:
        """
        Block a client device

        Args:
            mac_address: MAC address of client to block

        Returns:
            True if successful, False otherwise
        """
        if not self._session:
            raise RuntimeError("Not connected to UniFi controller. Call connect() first.")

        try:
            if self.is_unifi_os:
                url = f"{self.host}/proxy/network/api/s/{self.site}/cmd/stamgr"
            else:
                url = f"{self.host}/api/s/{self.site}/cmd/stamgr"

            payload = {
                "cmd": "block-sta",
                "mac": mac_address.lower()
            }

            async with self._session.post(url, json=payload) as resp:
                if resp.status == 200:
                    logger.info(f"Successfully blocked client {mac_address}")
                    return True
                else:
                    logger.error(f"Failed to block client {mac_address}: {resp.status}")
                    return False

        except Exception as e:
            logger.error(f"Error blocking client {mac_address}: {e}")
            return False

    async def unblock_client(self, mac_address: str) -> bool:
        """
        Unblock a client device

        Args:
            mac_address: MAC address of client to unblock

        Returns:
            True if successful, False otherwise
        """
        if not self._session:
            raise RuntimeError("Not connected to UniFi controller. Call connect() first.")

        try:
            if self.is_unifi_os:
                url = f"{self.host}/proxy/network/api/s/{self.site}/cmd/stamgr"
            else:
                url = f"{self.host}/api/s/{self.site}/cmd/stamgr"

            payload = {
                "cmd": "unblock-sta",
                "mac": mac_address.lower()
            }

            async with self._session.post(url, json=payload) as resp:
                if resp.status == 200:
                    logger.info(f"Successfully unblocked client {mac_address}")
                    return True
                else:
                    logger.error(f"Failed to unblock client {mac_address}: {resp.status}")
                    return False

        except Exception as e:
            logger.error(f"Error unblocking client {mac_address}: {e}")
            return False

    async def set_client_name(self, mac_address: str, name: str) -> bool:
        """
        Set friendly name for a client in UniFi

        Args:
            mac_address: MAC address of client
            name: Friendly name to set

        Returns:
            True if successful, False otherwise
        """
        if not self._session:
            raise RuntimeError("Not connected to UniFi controller. Call connect() first.")

        try:
            if self.is_unifi_os:
                url = f"{self.host}/proxy/network/api/s/{self.site}/rest/user"
            else:
                url = f"{self.host}/api/s/{self.site}/rest/user"

            # First, find the user ID for this MAC
            async with self._session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    users = data.get('data', [])
                    user = next((u for u in users if u.get('mac', '').lower() == mac_address.lower()), None)

                    if user:
                        user_id = user.get('_id')
                        # Update the user's name
                        update_url = f"{url}/{user_id}"
                        payload = {"name": name}

                        async with self._session.put(update_url, json=payload) as update_resp:
                            if update_resp.status == 200:
                                logger.info(f"Successfully set name for {mac_address} to '{name}'")
                                return True
                    else:
                        # User doesn't exist yet, create it
                        payload = {
                            "mac": mac_address.lower(),
                            "name": name
                        }
                        async with self._session.post(url, json=payload) as create_resp:
                            if create_resp.status == 200:
                                logger.info(f"Successfully created user and set name for {mac_address} to '{name}'")
                                return True

            logger.error(f"Failed to set name for {mac_address}")
            return False

        except Exception as e:
            logger.error(f"Error setting name for {mac_address}: {e}")
            return False

    async def test_connection(self) -> Dict:
        """
        Test the connection to the UniFi controller

        Returns:
            Dictionary with connection status and controller info
        """
        try:
            connected = await self.connect()
            if not connected:
                return {
                    "connected": False,
                    "error": "Failed to connect to UniFi controller"
                }

            # Get controller info
            clients = await self.get_clients()
            aps = await self.get_access_points()

            return {
                "connected": True,
                "client_count": len(clients),
                "ap_count": len(aps),
                "site": self.site
            }

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                "connected": False,
                "error": str(e)
            }
        finally:
            await self.disconnect()

    def __del__(self):
        """
        Cleanup when object is destroyed
        """
        # Note: Can't use await in __del__, so we just close the session
        if self._session and not self._session.closed:
            # Schedule the close operation
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._session.close())
            except:
                pass
