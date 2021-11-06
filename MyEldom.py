"""Library for connecting to MyEldom cloud service."""
# Based on https://github.com/Danielhiversen/pymill/blob/master/mill/__init__.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
import json
import logging

import aiohttp
import async_timeout

API_ENDPOINT_1 = "https://myeldom.com"
ELDOM_DEVICE_TYPE_HEATER = 4
DEFAULT_TIMEOUT = 10

_LOGGER = logging.getLogger(__name__)


@dataclass
class EldomDevice:
    """Eldom Device."""

    hw_version: str | None = None
    sw_version: str | None = None

    id: int | None = None
    last_updated: datetime | None = None
    name: str | None = None
    real_device_id: str | None = None

    available: bool | None = None


@dataclass
class Heater(EldomDevice):
    """Representation of heater."""

    raw_data: str | None = None
    state: int | None = None
    power: float | None = None

    current_temp: float | None = None
    set_temp: float | None = None
    pcb_temp: float | None = None

    open_window: int | None = None

    energy_day: float | None = None
    energy_night: float | None = None
    energy_total: float | None = None


class MyEldom:
    """MyEldom Custom Class."""

    def __init__(
        self,
        email: str,
        password: str,
        timeout: int = DEFAULT_TIMEOUT,
        debug: bool = False,
    ):
        """Initialize the MyEldom connection."""
        _LOGGER.info("MyEldom __init__")

        self._email = email
        self._password = password
        self._timeout = timeout

        self.user_info = None
        self.groups = None
        self.devices = None

        self.debug = debug

        if self.debug:
            _LOGGER.setLevel(logging.DEBUG)

        self.heaters: dict[str, Heater] = {}

        self.last_login_attempt = datetime.utcnow()

        _LOGGER.info("MyEldom Created")

    async def connect(self, websession: aiohttp.ClientSession = None, retry: int = 2):
        """Connect to myeldom server."""
        if websession is None:
            self.websession = aiohttp.ClientSession(
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1",
                    "Cache-Control": "max-age=0",
                }
            )
        else:
            self.websession = websession
        if await self._do_login(retry):
            # await self.get_devices()
            # await self.update_all_devices()
            # await self.run_websocket()
            # self.update_device_status()
            # if self._client_session is not None:
            #     self.start_websocket()
            return True
        return False

    async def disconnect(self):
        """Disconnect from myeldom server."""
        # await self.ws_disconnect()
        await self._do_logout()

    async def _do_login(self, retry: int = 2):
        """Login to server."""
        url = API_ENDPOINT_1 + r"/Account/Login"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Connection": "Keep-Alive",
        }

        self.last_login_attempt = datetime.utcnow()
        login_data = {"Email": self._email, "Password": self._password}

        if self.debug:
            _LOGGER.debug(f"Attempting Login to {url} with credentials: {login_data}")

        try:
            with async_timeout.timeout(self._timeout):
                resp = await self.websession.post(
                    url, data=login_data, headers=headers, allow_redirects=False
                )
        except (asyncio.TimeoutError, aiohttp.ClientError):
            if retry < 1:
                _LOGGER.error("Error connecting to MyEldom", exc_info=True)
                return False
            return await self._do_login(retry - 1)

        if self.debug:
            _LOGGER.debug(f"Response Status: {resp.status}")
            _LOGGER.debug(f"Response Text: {await resp.text()}")

        if resp.status == 302:
            # Login Success!
            _LOGGER.info("Login Successful!")
            return True
        else:
            # Login Error!
            _LOGGER.error("Error While Logging in to MyEldom!")
        return False

    async def _do_logout(self):
        """Logout from server."""
        if self.websession is not None:
            async with self.websession.get(
                f"{API_ENDPOINT_1}/account/logout", allow_redirects=False
            ) as response:
                if response.status == 302:
                    # Logout Success!
                    _LOGGER.info("Logout Success!")
            await self.websession.close()
            self.websession = None

    async def _get_request(self, command: str, payload: dict = {}, retry: int = 3):
        """Execute http GET request."""

        url = API_ENDPOINT_1 + command

        if self.debug:
            _LOGGER.debug(f"Request '{url}' With payload: {payload}")

        headers = {
            "Content-Type": "application/json",
            "Connection": "Keep-Alive",
        }

        try:
            with async_timeout.timeout(self._timeout):
                # GET http request
                resp = await self.websession.get(
                    url,
                    data=json.dumps(payload),
                    headers=headers,
                    allow_redirects=False,
                )
        except asyncio.TimeoutError:
            if retry < 1:
                _LOGGER.error("Timed out sending command to MyEldom: %s", command)
                return None
            return await self._get_request(command, payload, retry - 1)
        except aiohttp.ClientError:
            _LOGGER.error(
                "Error sending command to MyEldom: %s", command, exc_info=True
            )
            return None

        result = await resp.text()
        if not result:
            return None

        #  Return response
        try:
            data = json.loads(result)
            return data
        except json.decoder.JSONDecodeError as json_err:
            _LOGGER.debug(result)
            _LOGGER.error(f"Unable to decode JSON response: {json_err}")
            return None

    async def _post_request(self, command: str, payload: dict = {}, retry: int = 3):
        """Execute http POST request."""

        url = API_ENDPOINT_1 + command

        if self.debug:
            _LOGGER.debug(f"Request '{url}' With payload: {payload}")

        headers = {
            "Content-Type": "application/json",
            "Connection": "Keep-Alive",
        }

        try:
            with async_timeout.timeout(self._timeout):
                # GET http request
                resp = await self.websession.post(
                    url,
                    data=json.dumps(payload),
                    headers=headers,
                    allow_redirects=False,
                )
        except asyncio.TimeoutError:
            if retry < 1:
                _LOGGER.error("Timed out sending command to MyEldom: %s", command)
                return None
            return await self._get_request(command, payload, retry - 1)
        except aiohttp.ClientError:
            _LOGGER.error(
                "Error sending command to MyEldom: %s", command, exc_info=True
            )
            return None

        result = await resp.text()
        if not result:
            return None

        #  Return response
        try:
            data = json.loads(result)
            return data
        except json.decoder.JSONDecodeError as json_err:
            if self.debug:
                _LOGGER.debug(result)
            _LOGGER.error(f"Unable to decode JSON response: {json_err}")
            return None

    async def fetch_all_heaters(self):
        """Request data."""
        if not self.heaters:
            self.heaters = {}
            # list is empty
            device_list = await self.get_device_list()
            if device_list is not None:
                for device in device_list:
                    if device.get("deviceType") == ELDOM_DEVICE_TYPE_HEATER:
                        if self.debug:
                            _LOGGER.debug(f"Found heater: {device.get('name')}")
                        # Heater device found, add it to list
                        _id = device.get("realDeviceId")
                        heater = self.heaters.get(_id, Heater())
                        heater.hw_version = str(device.get("hwVersion"))
                        heater.id = device.get("id")
                        if device.get("lastDataRefreshDate"):
                            heater.last_updated = datetime.strptime(
                                device.get("lastDataRefreshDate")[:19],
                                "%Y-%m-%dT%H:%M:%S",
                            )
                            heater.available = True
                        else:
                            heater.available = False
                        heater.name = device.get("name")
                        heater.real_device_id = device.get("realDeviceId")
                        heater.swVersion = device.get("swVersion")
                        self.heaters[_id] = heater

        # Retrieve data from all heaters
        tasks = []
        for heater in self.heaters.values():
            tasks.append(self.fetch_heater_data(heater))
        await asyncio.gather(*tasks)

        return {**self.heaters}

    async def fetch_heater_data(self, heater: Heater):
        """Fetach status of a single heater."""
        # Get heater status
        heater_data = await self._get_request(f"/api/panelconvector/{heater.id}")
        if heater_data is not None:
            heater_status_json = json.loads(heater_data["objectJson"])
            # _LOGGER.debug(f"Device Status: {heater_status_json}")
            # Update heater attributes
            heater.raw_data = json.dumps(heater_status_json)
            heater.state = heater_status_json.get("State")
            heater.power = heater_status_json.get("Power")

            heater.current_temp = heater_status_json.get("AmbientTemp")

            if "TimerSTempA" in heater_data["objectJson"]:
                heater.set_temp = float(heater_status_json.get("TimerSTempA"))
            else:
                heater.set_temp = float(heater_status_json.get("SetTemp"))

            heater.pcb_temp = float(heater_status_json.get("PCBTemp"))

            heater.open_window = heater_status_json.get("OpenWindow")

            heater.energy_day = float(heater_status_json.get("EnergyD"))
            heater.energy_night = float(heater_status_json.get("EnergyN"))
            heater.energy_total = float(heater.energy_day) + float(heater.energy_night)
            if heater_status_json.get("LastRefreshDate"):
                heater.last_updated = datetime.strptime(
                    heater_status_json.get("LastRefreshDate")[:19], "%Y-%m-%dT%H:%M:%S"
                )
                heater.available = True
            else:
                heater.available = False
            return True
        else:
            heater.available = False
        return False

    async def get_user_info(self):
        """Get user info from server."""
        user_info = await self._get_request(r"/api/user/get")
        if user_info is not None:
            if self.debug:
                _LOGGER.debug(f"MyEldom User Info: {user_info}")
        else:
            _LOGGER.error("Unable to retrieve MyEldom User Info!")
        return user_info

    async def get_device_groups(self):
        """Get device groups from server."""
        groups = await self._get_request(r"/api/device/getmygroups")
        if groups is not None:
            if self.debug:
                _LOGGER.debug(f"MyEldom Device Groups: {groups}")
        else:
            _LOGGER.error("Unable to retrieve device groups!")
        return groups

    async def get_device_list(self):
        """Get list of devices from server."""
        device_list = await self._get_request(r"/api/device/getmy")
        if device_list is not None:
            if self.debug:
                _LOGGER.debug(f"MyEldom Device List: {device_list}")
        else:
            _LOGGER.error("Unable to retrieve device list!")
        return device_list

    # async def update_device_stats(self, device):
    #     """Update statistics of device."""
    #     if self.websession is not None:
    #         dev_id = str(device["Info"]["id"])
    #         # Get Device Statistics
    #         error = False
    #         device["TodaykWh"] = 0.0
    #         device["YesterdaykWh"] = 0.0
    #         device["MonthkWh"] = 0.0
    #         device["LastMonthkWh"] = 0.0
    #         async with self.websession.post(
    #             f"{self._url}/api/device/getstat",
    #             json={"deviceId": dev_id},
    #             allow_redirects=False,
    #         ) as response:
    #             if response and response.status == 200:
    #                 # [{"id":387138,"deviceId":611,"statInformation":"0:36;1:36;2:36;3:35;4:35;5:35;6:35;7:35;8:35;9:34;10:34;11:34;12:34;13:35;14:35;15:35;16:34;17:34;18:35;19:34;20:34;21:34;22:34;23:34;24:34;25:34;26:35;27:36;28:37;29:37","date":"2019-12-09T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:12:09"},{"id":386491,"deviceId":611,"statInformation":"0:35;1:35;2:35;3:35;4:34;5:34;6:34;7:34;8:35;9:35;10:36;11:37;12:37;13:37;14:37;15:38;16:38;17:39;18:39;19:40;20:41;21:41;22:41;23:41;24:41;25:40;26:40;27:40;28:39;29:39;30:40;31:40;32:40;33:40;34:39;35:39;36:38;37:38;38:38;39:38;40:38;41:38;42:38;43:38;44:38;45:37;46:37;47:37","date":"2019-12-08T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:12:08"},{"id":385771,"deviceId":611,"statInformation":"0:36;1:36;2:35;3:35;4:35;5:35;6:35;7:35;8:34;9:34;10:34;11:34;12:34;13:34;14:34;15:36;16:37;17:38;18:39;19:40;20:40;21:40;22:39;23:39;24:39;25:39;26:39;27:39;28:39;29:39;30:39;31:39;32:38;33:38;34:38;35:38;36:38;37:37;38:37;39:37;40:37;41:37;42:37;43:36;44:36;45:36;46:36;47:36","date":"2019-12-07T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:12:07"},{"id":385067,"deviceId":611,"statInformation":"0:32;1:32;2:33;3:33;4:34;5:34;6:33;7:33;8:33;9:33;10:32;11:33;12:33;13:33;14:33;15:33;16:32;17:33;18:34;19:35;20:35;21:35;22:34;23:34;24:34;25:33;26:33;27:33;28:33;29:33;30:33;31:34;32:35;33:36;34:36;35:37;36:37;37:38;38:38;39:39;40:38;41:38;42:38;43:38;44:38;45:38;46:37;47:36","date":"2019-12-06T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:12:06"},{"id":385066,"deviceId":611,"statInformation":"0:34;1:33;2:33;3:33;4:32;5:32;6:33;7:33;8:34;9:35;10:34;11:35;12:35;13:35;14:34;15:34;16:34;17:33;18:33;19:34;20:34;21:35;22:35;23:35;24:35;25:35;26:35;27:34;28:34;29:35;30:34;31:34;32:34;33:34;34:34;35:34;36:34;37:34;38:34;39:34;40:34;41:34;42:34;43:34;44:33;45:33;46:33;47:32","date":"2019-12-05T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:12:05"},{"id":383122,"deviceId":611,"statInformation":"16:3","date":"2019-12-03T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:12:03"},{"id":383018,"deviceId":611,"statInformation":"0:34;1:35;2:35;3:36;4:36;5:36;6:36;7:35;8:35;9:35;10:35;11:35;12:35;13:35;14:34;15:34;16:34;17:33;18:33;19:33;20:33;21:33;22:34;23:35;24:36;25:36;26:36;27:35;28:35;29:35;30:35;31:34;32:41;33:41","date":"2019-12-03T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:12:03"},{"id":383012,"deviceId":611,"statInformation":"16:3;17:4;18:4;19:4;20:4;21:4","date":"2019-12-02T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:12:02"},{"id":382347,"deviceId":611,"statInformation":"0:35;1:35;2:35;3:34;4:34;5:33;6:33;7:33;8:32;9:32;10:33;11:33;12:35;13:36;14:36;15:36;16:35;17:35;18:35;19:35;20:35;21:34;22:34;23:34;24:34;25:34;26:35;27:35;28:36;29:37;30:37;31:37;32:43;33:41;34:43;35:41;36:43;37:41;38:43;39:41;40:43;41:41;42:43;43:41;44:36;45:36;46:35;47:35","date":"2019-12-02T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:12:02"},{"id":381540,"deviceId":611,"statInformation":"0:33;1:33;2:33;3:33;4:33;5:32;6:32;7:33;8:34;9:34;10:34;11:33;12:33;13:33;14:34;15:36;16:37;17:38;18:39;19:39;20:39;21:38;22:38;23:37;24:37;25:38;26:39;27:38;28:37;29:37;30:37;31:37;32:37;33:37;34:37;35:36;36:36;37:36;38:35;39:35;40:34;41:34;42:34;43:34;44:35;45:35;46:36;47:36","date":"2019-12-01T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:12:01"},{"id":381023,"deviceId":611,"statInformation":"0:34;1:34;2:34;3:35;4:36;5:35;6:35;7:35;8:35;9:34;10:34;11:33;12:33;13:33;14:32;15:33;16:37;17:38;18:38;19:39;20:39;21:39;22:39;23:39;24:39;25:39;26:39;27:38;28:38;29:37;30:37;31:37;32:37;33:37;34:37;35:37;36:36;37:36;38:36;39:36;40:36;41:35;42:35;43:35;44:34;45:34;46:34;47:34","date":"2019-11-30T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:30"},{"id":381009,"deviceId":611,"statInformation":"8:1","date":"2019-11-30T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:30"},{"id":381008,"deviceId":611,"statInformation":"16:3;17:1","date":"2019-11-29T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:29"},{"id":380413,"deviceId":611,"statInformation":"0:35;1:35;2:35;3:35;4:34;5:34;6:34;7:34;8:34;9:33;10:33;11:34;12:34;13:34;14:35;15:36;16:36;17:36;18:36;19:36;20:37;21:38;22:37;23:37;24:36;25:36;26:36;27:36;28:35;29:35;30:35;31:35;32:43;33:43;34:42;35:40;36:39;37:39;38:38;39:37;40:37;41:36;42:36;43:35;44:35;45:35;46:34;47:34","date":"2019-11-29T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:29"},{"id":380404,"deviceId":611,"statInformation":"16:4;17:3;18:3;19:3;20:3;21:3","date":"2019-11-28T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:28"},{"id":379838,"deviceId":611,"statInformation":"0:35;1:35;2:35;3:34;4:34;5:34;6:34;7:34;8:34;9:34;10:34;11:34;12:34;13:34;14:34;15:34;16:34;17:34;18:34;19:34;20:34;21:33;22:33;23:33;24:33;25:33;26:33;27:33;28:34;29:35;30:36;31:36;32:41;33:43;34:42;35:42;36:43;37:41;38:43;39:42;40:41;41:43;42:41;43:43;44:37;45:37;46:36;47:35","date":"2019-11-28T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:28"},{"id":379828,"deviceId":611,"statInformation":"16:6;17:4;18:4;19:4;20:4;21:4","date":"2019-11-27T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:27"},{"id":379270,"deviceId":611,"statInformation":"0:36;1:36;2:35;3:35;4:35;5:35;6:35;7:35;8:35;9:35;10:34;11:34;12:35;13:35;14:34;15:34;16:34;17:34;18:34;19:35;20:35;21:35;22:35;23:34;24:34;25:34;26:34;27:34;28:34;29:34;30:34;31:34;32:41;33:41;34:42;35:42;36:41;37:43;38:41;39:42;40:41;41:43;42:41;43:43;44:36;45:36;46:36;47:35","date":"2019-11-27T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:27"},{"id":379264,"deviceId":611,"statInformation":"16:6;17:4;18:3;19:4;20:3;21:3","date":"2019-11-26T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:26"},{"id":378698,"deviceId":611,"statInformation":"0:37;1:37;2:38;3:37;4:37;5:37;6:36;7:36;8:36;9:36;10:36;11:36;12:36;13:36;14:36;15:36;16:35;17:35;18:35;19:35;20:35;21:35;22:35;23:35;24:35;25:35;26:35;27:35;28:35;29:35;30:35;31:34;32:42;33:41;34:42;35:41;36:43;37:42;38:41;39:43;40:42;41:41;42:41;43:43;44:37;45:37;46:36;47:36","date":"2019-11-26T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:26"},{"id":378687,"deviceId":611,"statInformation":"16:5;17:4;18:4;19:4;20:4;21:4","date":"2019-11-25T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:25"},{"id":378182,"deviceId":611,"statInformation":"0:39;1:38;2:38;3:37;4:37;5:37;6:37;7:36;8:36;9:36;10:35;11:35;12:35;13:35;14:35;15:35;16:35;17:34;18:34;19:35;20:35;21:36;22:37;23:37;24:37;25:37;26:37;27:36;28:36;29:36;30:35;31:35;32:43;33:43;34:43;35:42;36:43;37:42;38:41;39:42;40:41;41:43;42:41;43:42;44:37;45:36;46:36;47:36","date":"2019-11-25T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:25"},{"id":377622,"deviceId":611,"statInformation":"0:35;1:34;2:34;3:34;4:34;5:33;6:33;7:33;8:33;9:33;10:35;11:35;12:36;13:35;14:36;15:36;16:39;17:39;18:39;19:39;20:39;21:39;22:38;23:39;24:39;25:39;26:40;27:39;28:39;29:39;30:39;31:39;32:43;33:43;34:43;35:43;36:42;37:43;38:43;39:42;40:43;41:43;42:43;43:42;44:39;45:39;46:39;47:39","date":"2019-11-24T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:24"},{"id":377613,"deviceId":611,"statInformation":"8:1;16:3;17:2;18:3;19:2;20:2;21:2","date":"2019-11-24T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:24"},{"id":377037,"deviceId":611,"statInformation":"0:35;1:35;2:35;3:36;4:37;5:38;6:37;7:37;8:36;9:35;10:35;11:35;12:35;13:34;14:34;15:35;16:39;17:39;18:39;19:39;20:39;21:39;22:39;23:39;24:39;25:39;26:39;27:39;28:39;29:39;30:39;31:39;32:43;33:43;34:43;35:43;36:42;37:44;38:41;39:43;40:43;41:43;42:43;43:42;44:36;45:36;46:36;47:35","date":"2019-11-23T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:23"},{"id":377025,"deviceId":611,"statInformation":"8:1;16:4;17:3;18:4;19:4;20:4;21:4","date":"2019-11-23T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:23"},{"id":377024,"deviceId":611,"statInformation":"16:6;17:4;18:4;19:4;20:5;21:5","date":"2019-11-22T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:22"},{"id":376460,"deviceId":611,"statInformation":"0:33;1:33;2:34;3:35;4:35;5:35;6:34;7:34;8:34;9:33;10:33;11:34;12:34;13:34;14:33;15:33;16:33;17:33;18:33;19:33;20:34;21:35;22:35;23:35;24:36;25:38;26:38;27:38;28:37;29:37;30:36;31:36;32:45;33:44;34:45;35:45;36:45;37:45;38:45;39:45;40:43;41:46;42:44;43:45;44:37;45:37;46:36;47:36","date":"2019-11-22T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:22"},{"id":375915,"deviceId":611,"statInformation":"0:33;1:32;2:32;3:32;4:31;5:31;6:31;7:30;8:30;9:32;10:31;11:33;12:31;13:31;14:31;15:32;16:33;17:33;18:33;19:33;20:33;21:32;22:32;23:32;24:32;25:32;26:31;27:31;28:31;29:31;30:31;31:31;32:42;33:42;34:43;35:43;36:42;37:43;38:42;39:43;40:43;41:43;42:42;43:43;44:35;45:34;46:34;47:33","date":"2019-11-21T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:21"},{"id":375905,"deviceId":611,"statInformation":"5:1;16:8;17:5;18:5;19:5;20:5;21:5","date":"2019-11-21T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:21"},{"id":375904,"deviceId":611,"statInformation":"16:7;17:6;18:6;19:6;20:6;21:6","date":"2019-11-20T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:20"},{"id":375400,"deviceId":611,"statInformation":"0:33;1:33;2:33;3:32;4:32;5:32;6:32;7:31;8:31;9:31;10:31;11:31;12:31;13:31;14:31;15:32;16:33;17:33;18:34;19:34;20:35;21:36;22:36;23:36;24:36;25:36;26:35;27:35;28:34;29:34;30:33;31:33;32:43;33:42;34:43;35:43;36:43;37:43;38:41;39:41;40:43;41:43;42:43;43:42;44:34;45:34;46:33;47:33","date":"2019-11-20T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:20"},{"id":375392,"deviceId":611,"statInformation":"16:7;17:5;18:5;19:5;20:6;21:5","date":"2019-11-19T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:19"},{"id":374865,"deviceId":611,"statInformation":"0:35;1:34;2:34;3:33;4:33;5:33;6:33;7:33;8:33;9:32;10:32;11:33;12:33;13:33;14:33;15:34;16:35;17:35;18:35;19:35;20:35;21:35;22:35;23:35;24:36;25:36;26:36;27:35;28:35;29:35;30:34;31:34;32:43;33:42;34:43;35:43;36:42;37:43;38:41;39:43;40:44;41:42;42:41;43:43;44:36;45:34;46:34;47:34","date":"2019-11-19T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:19"},{"id":374857,"deviceId":611,"statInformation":"16:6;17:4;18:5;19:5;20:4;21:4","date":"2019-11-18T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:18"},{"id":374344,"deviceId":611,"statInformation":"0:37;1:37;2:36;3:36;4:36;5:35;6:35;7:35;8:35;9:34;10:34;11:35;12:36;13:37;14:37;15:37;16:37;17:36;18:36;19:36;20:35;21:35;22:35;23:35;24:35;25:35;26:35;27:35;28:35;29:34;30:34;31:34;32:42;33:43;34:42;35:43;36:44;37:41;38:43;39:42;40:42;41:43;42:41;43:44;44:37;45:36;46:35;47:35","date":"2019-11-18T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:18"},{"id":373844,"deviceId":611,"statInformation":"0:37;1:37;2:37;3:36;4:36;5:35;6:35;7:36;8:37;9:37;10:37;11:37;12:36;13:36;14:35;15:36;16:39;17:39;18:38;19:39;20:39;21:39;22:39;23:39;24:39;25:39;26:39;27:39;28:39;29:39;30:39;31:39;32:45;33:44;34:45;35:45;36:43;37:44;38:45;39:44;40:44;41:45;42:44;43:45;44:40;45:39;46:39;47:38","date":"2019-11-17T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:17"},{"id":373834,"deviceId":611,"statInformation":"8:1;9:1;14:1;15:1;16:6;17:6;18:5;19:6;20:5;21:4","date":"2019-11-17T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:17"},{"id":373293,"deviceId":611,"statInformation":"0:35;1:35;2:34;3:35;4:36;5:36;6:36;7:36;8:36;9:35;10:35;11:35;12:34;13:34;14:35;15:36;16:39;17:39;18:39;19:39;20:39;21:39;22:39;23:39;24:39;25:39;26:39;27:39;28:39;29:38;30:39;31:39;32:42;33:45;34:45;35:44;36:45;37:44;38:45;39:44;40:44;41:45;42:43;43:46;44:40;45:40;46:39;47:38","date":"2019-11-16T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:16"},{"id":373283,"deviceId":611,"statInformation":"8:1;16:5;17:6;18:6;19:5;20:5;21:4","date":"2019-11-16T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:16"},{"id":373282,"deviceId":611,"statInformation":"16:5;17:2;18:2;19:3;20:3;21:2","date":"2019-11-15T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:15"},{"id":372774,"deviceId":611,"statInformation":"0:37;1:36;2:36;3:35;4:35;5:35;6:34;7:34;8:34;9:33;10:33;11:33;12:33;13:33;14:34;15:35;16:36;17:36;18:36;19:36;20:35;21:35;22:35;23:35;24:35;25:34;26:34;27:34;28:34;29:34;30:34;31:33;32:40;33:42;34:41;35:41;36:41;37:41;38:41;39:40;40:40;41:41;42:41;43:41;44:36;45:36;46:35;47:35","date":"2019-11-15T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:15"},{"id":372423,"deviceId":611,"statInformation":"16:4;17:4;18:3;19:4;20:3;21:4","date":"2019-11-14T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:14"},{"id":372254,"deviceId":611,"statInformation":"0:34;1:34;2:33;3:33;4:33;5:33;6:33;7:33;8:32;9:32;10:32;11:32;12:33;13:32;14:32;15:32;16:32;17:32;18:32;19:33;20:34;21:35;22:35;23:35;24:35;25:35;26:35;27:35;28:34;29:34;30:34;31:34;32:40;33:41;34:40;35:41;36:41;37:41;38:40;39:41;40:42;41:41;42:40;43:42;44:37;45:38;46:38;47:37","date":"2019-11-14T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:14"},{"id":372246,"deviceId":611,"statInformation":"16:4;17:4;18:3;19:4;20:4;21:3","date":"2019-11-13T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:13"},{"id":371768,"deviceId":611,"statInformation":"0:34;1:34;2:33;3:33;4:33;5:33;6:33;7:33;8:33;9:32;10:32;11:33;12:33;13:33;14:33;15:33;16:34;17:35;18:36;19:36;20:36;21:36;22:36;23:36;24:35;25:35;26:35;27:35;28:35;29:35;30:34;31:34;32:40;33:41;34:40;35:41;36:40;37:41;38:42;39:40;40:42;41:41;42:41;43:42;44:35;45:35;46:35;47:34","date":"2019-11-13T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:13"},{"id":371756,"deviceId":611,"statInformation":"16:4;17:2;18:3;19:4;20:4;21:4","date":"2019-11-12T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:12"},{"id":371287,"deviceId":611,"statInformation":"0:35;1:36;2:36;3:36;4:35;5:35;6:35;7:35;8:34;9:34;10:34;11:34;12:34;13:34;14:34;15:34;16:33;17:33;18:33;19:33;20:33;21:34;22:35;23:37;24:37;25:37;26:37;27:36;28:36;29:35;30:35;31:35;32:41;33:40;34:40;35:41;36:41;37:42;38:40;39:41;40:40;41:41;42:41;43:41;44:35;45:35;46:34;47:34","date":"2019-11-12T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:12"},{"id":371283,"deviceId":611,"statInformation":"16:3;17:3;18:3;19:3;20:3;21:3","date":"2019-11-11T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:11"},{"id":370815,"deviceId":611,"statInformation":"0:34;1:34;2:33;3:33;4:33;5:33;6:32;7:32;8:32;9:32;10:32;11:32;12:32;13:33;14:33;15:32;16:33;17:33;18:33;19:33;20:34;21:34;22:34;23:35;24:35;25:36;26:37;27:38;28:37;29:37;30:37;31:36;32:42;33:42;34:40;35:42;36:41;37:41;38:42;39:40;40:42;41:40;42:42;43:40;44:36;45:35;46:35;47:35","date":"2019-11-11T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:11"},{"id":370334,"deviceId":611,"statInformation":"0:37;1:37;2:37;3:37;4:37;5:37;6:37;7:36;8:37;9:38;10:38;11:37;12:36;13:37;14:38;15:37;16:39;17:41;18:40;19:41;20:41;21:39;22:39;23:39;24:39;25:38;26:39;27:38;28:38;29:39;30:39;31:39;32:40;33:41;34:41;35:41;36:40;37:42;38:41;39:40;40:41;41:41;42:40;43:41;44:35;45:35;46:34;47:34","date":"2019-11-10T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:10"},{"id":370333,"deviceId":611,"statInformation":"0:2;1:2;2:2;3:3;4:3;5:3;6:4;7:3;8:6;9:5;10:2;11:1;13:1;14:1;15:1;16:3;17:3;18:3;19:3;20:3;21:4","date":"2019-11-10T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:10"},{"id":369890,"deviceId":611,"statInformation":"0:37;1:37;2:37;3:36;4:37;5:38;6:37;7:36;8:37;9:38;10:38;11:38;12:36;13:36;14:37;15:38;16:41;17:41;18:40;19:40;20:41;21:40;22:41;23:41;24:40;25:41;26:41;27:41;28:43;29:42;30:43;31:43;32:43;33:43;34:39;35:42;36:41;37:41;38:41;39:41;40:40;41:41;42:41;43:40;44:37;45:37;46:36;47:37","date":"2019-11-09T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:09"},{"id":369883,"deviceId":611,"statInformation":"0:1;1:1;2:2;3:1;4:2;5:2;6:1;7:2;8:5;9:4;10:3;11:2;12:2;13:2;14:3;15:4;16:3;17:3;18:2;19:2;20:3;21:3;22:1;23:1","date":"2019-11-09T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:09"},{"id":369434,"deviceId":611,"statInformation":"0:37;1:37;2:38;3:38;4:38;5:37;6:36;7:36;8:37;9:37;10:37;11:37;12:36;13:37;14:37;15:37;16:37;17:37;18:36;19:37;20:37;21:37;22:37;23:37;24:37;25:37;26:37;27:37;28:36;29:36;30:37;31:37;32:45;33:45;34:45;35:45;36:45;37:44;38:44;39:43;40:43;41:42;42:43;43:42;44:37;45:36;46:37;47:37","date":"2019-11-08T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:08"},{"id":369428,"deviceId":611,"statInformation":"0:1;1:1;2:2;3:2;4:2;5:2;6:1;7:2;8:1;9:1;16:8;17:6;18:6;19:5;20:4;21:4;23:1","date":"2019-11-08T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:08"},{"id":368956,"deviceId":611,"statInformation":"0:36;1:37;2:36;3:38;4:37;5:38;6:36;7:37;8:37;9:37;10:36;11:38;12:37;13:37;14:37;15:36;16:38;17:37;18:38;19:37;20:37;21:37;22:36;23:37;24:36;25:37;26:36;27:38;28:36;29:38;30:37;31:37;32:43;33:42;34:43;35:42;36:43;37:42;38:43;39:43;40:43;41:43;42:42;43:44;44:37;45:36;46:37;47:36","date":"2019-11-07T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:07"},{"id":368950,"deviceId":611,"statInformation":"4:1;5:1;9:1;10:1;11:1;12:1;13:1;14:1;15:1;16:6;17:5;18:4;19:4;20:4;21:4","date":"2019-11-07T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:07"},{"id":368949,"deviceId":611,"statInformation":"16:5;17:4;18:4;19:4;20:3;21:4","date":"2019-11-06T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:06"},{"id":368540,"deviceId":611,"statInformation":"0:37;1:37;2:37;3:36;4:37;5:37;6:37;7:38;8:37;9:36;10:37;11:37;12:37;13:37;14:37;15:36;16:37;17:37;18:37;19:37;20:36;21:37;22:37;23:37;24:36;25:37;26:37;27:37;28:36;29:37;30:37;31:36;32:43;33:43;34:42;35:43;36:42;37:43;38:43;39:42;40:44;41:43;42:43;43:44;44:38;45:37;46:37;47:37","date":"2019-11-06T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:06"},{"id":368125,"deviceId":611,"statInformation":"0:37;1:37;2:37;3:36;4:37;5:37;6:36;7:36;8:36;9:37;10:36;11:37;12:37;13:37;14:37;15:37;16:36;17:37;18:37;19:37;20:37;21:37;22:36;23:37;24:37;25:37;26:37;27:36;28:37;29:37;30:37;31:37;32:43;33:43;34:43;35:44;36:41;37:44;38:43;39:42;40:44;41:43;42:42;43:44;44:38;45:38;46:37;47:37","date":"2019-11-05T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:05"},{"id":368118,"deviceId":611,"statInformation":"10:1;11:1;12:1;14:1;16:5;17:4;18:4;19:4;20:3;21:4","date":"2019-11-05T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:05"},{"id":368124,"deviceId":611,"statInformation":"23:38;24:38;25:38;26:37;27:37;28:37;29:37;30:37;31:37;32:42;33:42;34:43;35:42;36:42;37:43;38:42;39:43;40:43;41:43;42:43;43:43;44:39;45:38;46:38;47:37","date":"2019-11-04T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:04"},{"id":368117,"deviceId":611,"statInformation":"16:4;17:3;18:3;19:3;20:3;21:2","date":"2019-11-04T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:04"},{"id":367247,"deviceId":611,"statInformation":"0:37;1:37;2:37;3:37;4:37;5:36;6:36;7:37;8:37;9:36;10:36;11:36;12:37;13:36;14:36;15:36;16:41;17:40;18:42;19:41;20:40;21:41","date":"2019-11-03T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:03"},{"id":367242,"deviceId":611,"statInformation":"8:4;9:2;10:3;11:1","date":"2019-11-03T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:03"},{"id":366774,"deviceId":611,"statInformation":"0:38;1:38;2:38;3:38;4:37;5:37;6:37;7:37;8:37;9:37;10:37;11:37;12:37;13:37;14:36;15:37;16:41;17:40;18:41;19:41;20:41;21:40;22:40;23:40;24:41;25:40;26:40;27:40;28:41;29:41;30:41;31:41;32:43;33:42;34:43;35:42;36:43;37:42;38:43;39:43;40:42;41:43;42:42;43:43;44:39;45:38;46:38;47:38","date":"2019-11-02T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:02"},{"id":366770,"deviceId":611,"statInformation":"8:3;9:2;10:2;11:2;12:2;13:1;14:1;15:2;16:3;17:3;18:2;19:3;20:3;21:3","date":"2019-11-02T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:02"},{"id":366326,"deviceId":611,"statInformation":"0:37;1:37;2:37;3:38;4:37;5:37;6:36;7:37;8:37;9:37;10:37;11:37;12:36;13:37;14:36;15:38;16:37;17:37;18:37;19:36;20:37;21:36;22:38;23:37;24:37;25:38;26:38;27:38;28:37;29:37;30:37;31:37;32:44;33:44;34:45;35:45;36:45;37:45;38:45;39:42;40:43;41:43;42:42;43:43;44:39;45:38;46:38;47:38","date":"2019-11-01T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:11:01"},{"id":366320,"deviceId":611,"statInformation":"9:1;10:1;16:6;17:5;18:4;19:3;20:2;21:2","date":"2019-11-01T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:11:01"},{"id":365895,"deviceId":611,"statInformation":"0:36;1:37;2:37;3:37;4:37;5:36;6:37;7:36;8:37;9:38;10:36;11:37;12:37;13:38;14:37;15:37;16:37;17:36;18:37;19:37;20:37;21:39;22:39;23:40;24:40;25:39;26:39;27:39;28:38;29:38;30:37;31:37;32:42;33:43;34:43;35:43;36:42;37:43;38:43;39:43;40:43;41:43;42:43;43:43;44:38;45:37;46:36;47:37","date":"2019-10-31T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:31"},{"id":365893,"deviceId":611,"statInformation":"4:1;5:1;6:1;7:2;8:1;9:1;16:4;17:4;18:3;19:4;20:4;21:3","date":"2019-10-31T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:31"},{"id":365476,"deviceId":611,"statInformation":"0:38;1:37;2:37;3:36;4:37;5:36;6:37;7:36;8:36;9:36;10:38;11:37;12:37;13:37;14:37;15:37;16:38;17:36;18:37;19:37;20:37;21:37;22:37;23:38;24:36;25:38;26:36;27:37;28:37;29:37;30:37;31:36;32:43;33:42;34:43;35:43;36:43;37:43;38:43;39:42;40:43;41:43;42:43;43:43;44:39;45:38;46:38;47:37","date":"2019-10-30T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:30"},{"id":365472,"deviceId":611,"statInformation":"7:1;8:1;9:1;10:1;11:1;12:1;13:1;14:1;15:1;16:5;17:3;18:1;19:1;20:1;21:2","date":"2019-10-30T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:30"},{"id":365070,"deviceId":611,"statInformation":"0:37;1:37;2:37;3:37;4:36;5:37;6:37;7:37;8:37;9:37;10:37;11:36;12:37;13:37;14:36;15:38;16:37;17:37;18:37;19:37;20:37;21:38;22:38;23:38;24:38;25:38;26:38;27:38;28:37;29:37;30:37;31:37;32:45;33:44;34:45;35:44;36:45;37:45;38:43;39:43;40:43;41:43;42:43;43:42;44:40;45:39;46:38;47:38","date":"2019-10-29T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:29"},{"id":365066,"deviceId":611,"statInformation":"7:1;16:6;17:5;18:4;19:1;20:2;21:2","date":"2019-10-29T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:29"},{"id":364702,"deviceId":611,"statInformation":"0:38;1:38;2:37;3:37;4:37;5:37;6:36;7:37;8:37;9:37;10:37;11:37;12:37;13:36;14:37;15:37;16:36;17:36;18:36;19:37;20:37;21:37;22:38;23:38;24:37;25:37;26:37;27:37;28:37;29:37;30:37;31:37;32:45;33:44;34:45;35:45;36:44;37:45;38:45;39:44;40:45;41:44;42:45;43:45;44:39;45:39;46:38;47:38","date":"2019-10-28T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:28"},{"id":364698,"deviceId":611,"statInformation":"7:1;16:6;17:5;18:5;19:5;20:5;21:4","date":"2019-10-28T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:28"},{"id":364311,"deviceId":611,"statInformation":"8:2;9:1;10:1;11:1;12:2;13:2;14:2;15:2;16:4;17:4;18:4;19:3;20:4;21:4","date":"2019-10-27T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:27"},{"id":364237,"deviceId":611,"statInformation":"0:41;1:41;2:40;3:40;4:40;5:40;6:39;7:39;8:39;9:39;10:38;11:38;12:38;13:38;14:38;15:38;16:41;17:40;18:41;19:41;20:41;21:41;22:41;23:44;24:43;25:43;26:43;27:42;28:42;29:42;30:43;31:43;32:45;33:44;34:44;35:44;36:44;37:45;38:45;39:45;40:44;41:45;42:45;43:45;44:40;45:39;46:39;47:38","date":"2019-10-27T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:27"},{"id":363905,"deviceId":611,"statInformation":"0:43;1:43;2:43;3:42;4:43;5:43;6:42;7:43;8:43;9:42;10:43;11:42;12:43;13:42;14:41;15:39;16:39;17:39;18:39;19:39;20:39;21:40;22:41;23:41;24:41;25:41;26:41;27:41;28:41;29:41;30:40;31:40;32:44;33:45;34:45;35:45;36:45;37:45;38:45;39:44;40:45;41:45;42:45;43:45;44:42;45:41;46:41;47:41","date":"2019-10-26T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:26"},{"id":363904,"deviceId":611,"statInformation":"0:2;1:2;2:2;3:3;4:2;5:2;6:3;7:1;16:4;17:3;18:2;19:2;20:3;21:2","date":"2019-10-26T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:26"},{"id":363903,"deviceId":611,"statInformation":"16:5;17:3;18:3;19:3;20:3;21:3;22:1;23:2","date":"2019-10-25T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:25"},{"id":363653,"deviceId":611,"statInformation":"0:39;1:39;2:39;3:39;4:39;5:39;6:39;7:39;8:39;9:39;10:39;11:38;12:38;13:38;14:38;15:38;16:38;17:38;18:38;19:38;20:38;21:39;22:39;23:40;24:40;25:40;26:40;27:39;28:39;29:39;30:39;31:39;32:45;33:44;34:43;35:45;36:45;37:45;38:44;39:45;40:45;41:44;42:44;43:44;44:42;45:42;46:42;47:42","date":"2019-10-25T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:25"},{"id":363648,"deviceId":611,"statInformation":"16:5;17:4;18:3;19:3;20:4;21:3","date":"2019-10-24T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:24"},{"id":363336,"deviceId":611,"statInformation":"0:39;1:39;2:39;3:39;4:39;5:39;6:39;7:39;8:38;9:38;10:38;11:38;12:38;13:38;14:38;15:38;16:38;17:37;18:38;19:38;20:38;21:38;22:38;23:38;24:38;25:38;26:38;27:39;28:39;29:39;30:39;31:39;32:45;33:45;34:45;35:44;36:45;37:44;38:44;39:45;40:45;41:45;42:44;43:44;44:41;45:40;46:40;47:40","date":"2019-10-24T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:24"},{"id":363112,"deviceId":611,"statInformation":"16:5;17:4;18:4;19:3;20:4;21:3","date":"2019-10-23T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:23"},{"id":363018,"deviceId":611,"statInformation":"0:39;1:39;2:39;3:38;4:38;5:38;6:38;7:38;8:38;9:38;10:38;11:38;12:37;13:37;14:37;15:37;16:37;17:37;18:37;19:37;20:37;21:37;22:37;23:38;24:38;25:39;26:39;27:38;28:39;29:38;30:38;31:38;32:45;33:45;34:45;35:44;36:44;37:45;38:44;39:45;40:44;41:45;42:45;43:44;44:41;45:40;46:40;47:40","date":"2019-10-23T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:23"},{"id":363017,"deviceId":611,"statInformation":"16:5;17:5;18:4;19:4;20:4;21:4","date":"2019-10-22T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:22"},{"id":362629,"deviceId":611,"statInformation":"0:38;1:38;2:38;3:38;4:38;5:38;6:38;7:38;8:38;9:38;10:37;11:37;12:37;13:37;14:37;15:37;16:37;17:37;18:37;19:37;20:37;21:37;22:37;23:37;24:37;25:38;26:38;27:38;28:38;29:38;30:38;31:38;32:45;33:44;34:44;35:45;36:44;37:44;38:45;39:45;40:45;41:45;42:44;43:44;44:40;45:39;46:39;47:39","date":"2019-10-22T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:22"},{"id":362628,"deviceId":611,"statInformation":"16:4;17:3;18:2;19:3;20:3;21:2","date":"2019-10-21T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:21"},{"id":362425,"deviceId":611,"statInformation":"0:39;1:39;2:39;3:38;4:38;5:38;6:38;7:38;8:38;9:38;10:38;11:37;12:37;13:37;14:37;15:37;16:37;17:37;18:37;19:38;20:38;21:38;22:38;23:38;24:38;25:38;26:38;27:38;28:37;29:37;30:37;31:37;32:43;33:42;34:43;35:42;36:43;37:42;38:43;39:43;40:43;41:43;42:43;43:42;44:40;45:39;46:39;47:39","date":"2019-10-21T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:21"},{"id":362120,"deviceId":611,"statInformation":"0:39;1:39;2:39;3:39;4:39;5:39;6:38;7:38;8:38;9:38;10:38;11:38;12:38;13:38;14:37;15:37;16:41;17:40;18:41;19:41;20:41;21:41;22:41;23:41;24:41;25:40;26:41;27:40;28:41;29:40;30:41;31:40;32:44;33:44;34:45;35:45;36:45;37:44;38:44;39:44;40:44;41:45;42:45;43:45;44:40;45:40;46:39;47:39","date":"2019-10-20T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:20"},{"id":362115,"deviceId":611,"statInformation":"8:2;9:1;10:1;11:1;12:1;13:1;14:1;15:1;16:5;17:4;18:4;19:4;20:4;21:3","date":"2019-10-20T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:20"},{"id":361811,"deviceId":611,"statInformation":"8:2;9:1;10:2;11:1;12:2;13:1;14:3;15:4;16:4;17:3;18:3;19:3;20:3;21:3","date":"2019-10-19T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:19"},{"id":361751,"deviceId":611,"statInformation":"0:38;1:38;2:38;3:38;4:38;5:38;6:38;7:38;8:38;9:38;10:38;11:37;12:37;13:37;14:37;15:37;16:42;17:40;18:40;19:41;20:41;21:41;22:40;23:41;24:41;25:40;26:41;27:41;28:41;29:45;30:45;31:45;32:45;33:45;34:45;35:44;36:44;37:45;38:45;39:45;40:44;41:44;42:45;43:45;44:41;45:40;46:40;47:39","date":"2019-10-19T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:19"},{"id":361750,"deviceId":611,"statInformation":"16:3;17:2;18:2;19:2;20:2","date":"2019-10-18T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:18"},{"id":361509,"deviceId":611,"statInformation":"0:40;1:40;2:39;3:39;4:39;5:39;6:39;7:39;8:39;9:39;10:39;11:39;12:39;13:39;14:39;15:39;16:39;17:39;18:39;19:39;20:39;21:39;22:38;23:39;24:39;25:39;26:39;27:39;28:39;29:39;30:39;31:39;32:45;33:42;34:42;35:42;36:42;37:42;38:43;39:43;40:43;41:43;42:40;43:39;44:39;45:39;46:39;47:38","date":"2019-10-18T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:18"},{"id":361505,"deviceId":611,"statInformation":"16:4;17:3;18:3;19:3;20:3;21:3","date":"2019-10-17T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:17"},{"id":361171,"deviceId":611,"statInformation":"0:41;1:41;2:40;3:40;4:40;5:40;6:40;7:40;8:40;9:40;10:40;11:40;12:39;13:39;14:39;15:39;16:39;17:39;18:39;19:39;20:39;21:39;22:39;23:39;24:39;25:40;26:40;27:40;28:40;29:40;30:40;31:40;32:44;33:45;34:45;35:45;36:45;37:44;38:45;39:44;40:45;41:44;42:45;43:45;44:41;45:41;46:40;47:40","date":"2019-10-17T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:17"},{"id":361073,"deviceId":611,"statInformation":"16:3;17:2;18:2;19:2;20:2;21:2","date":"2019-10-16T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:16"},{"id":360958,"deviceId":611,"statInformation":"0:42;1:42;2:42;3:41;4:41;5:41;6:41;7:41;8:41;9:40;10:40;11:40;12:40;13:40;14:40;15:40;16:40;17:40;18:40;19:40;20:41;21:40;22:41;23:41;24:41;25:41;26:40;27:40;28:40;29:40;30:40;31:40;32:45;33:44;34:45;35:45;36:45;37:45;38:45;39:44;40:44;41:44;42:44;43:45;44:42;45:41;46:41;47:41","date":"2019-10-16T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:16"},{"id":360956,"deviceId":611,"statInformation":"16:3;17:1","date":"2019-10-15T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:15"},{"id":360715,"deviceId":611,"statInformation":"0:42;1:42;2:42;3:42;4:42;5:41;6:41;7:41;8:41;9:41;10:41;11:41;12:41;13:41;14:41;15:41;16:41;17:41;18:41;19:41;20:41;21:40;22:41;23:41;24:41;25:41;26:41;27:41;28:41;29:41;30:41;31:41;32:44;33:45;34:45;35:45;36:45;37:45;38:44;39:45;40:45;41:45;42:45;43:45;44:43;45:43;46:43;47:42","date":"2019-10-15T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:15"},{"id":360712,"deviceId":611,"statInformation":"16:2;17:1;18:1;19:1;20:1;21:1","date":"2019-10-14T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:14"},{"id":360369,"deviceId":611,"statInformation":"0:42;1:41;2:41;3:41;4:41;5:41;6:41;7:41;8:41;9:41;10:40;11:40;12:40;13:40;14:40;15:40;16:40;17:40;18:40;19:40;20:40;21:41;22:41;23:41;24:41;25:41;26:41;27:42;28:42;29:42;30:42;31:42;32:45;33:44;34:44;35:45;36:45;37:45;38:45;39:45;40:45;41:45;42:45;43:44;44:43;45:43;46:43;47:42","date":"2019-10-14T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:14"},{"id":360143,"deviceId":611,"statInformation":"0:41;1:41;2:41;3:41;4:41;5:41;6:41;7:40;8:40;9:40;10:40;11:40;12:40;13:40;14:40;15:40;16:45;17:44;18:45;19:45;20:45;21:42;22:42;23:42;24:42;25:42;26:42;27:42;28:42;29:42;30:42;31:42;32:47;33:45;34:45;35:45;36:46;37:46;38:44;39:44;40:45;41:45;42:45;43:45;44:43;45:43;46:42;47:42","date":"2019-10-13T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:13"},{"id":360142,"deviceId":611,"statInformation":"8:4;9:3;10:1;16:3;17:2;18:2;19:1;20:1;21:1","date":"2019-10-13T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:13"},{"id":359871,"deviceId":611,"statInformation":"0:40;1:40;2:40;3:40;4:39;5:39;6:39;7:39;8:39;9:39;10:39;11:39;12:39;13:39;14:39;15:39;16:45;17:45;18:45;19:45;20:40;21:39;22:39;23:40;24:39;25:39;26:39;27:46;28:45;29:45;30:44;31:45;32:46;33:47;34:46;35:47;36:46;37:47;38:47;39:46;40:46;41:46;42:47;43:47;44:47;45:43;46:42;47:42","date":"2019-10-12T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:12"},{"id":359870,"deviceId":611,"statInformation":"8:5;9:4;13:1;14:4;15:3;16:6;17:5;18:5;19:4;20:4;21:4;22:2","date":"2019-10-12T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:12"},{"id":359703,"deviceId":611,"statInformation":"16:6;17:2;18:2;19:2;20:3;21:3;22:1","date":"2019-10-11T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:11"},{"id":359539,"deviceId":611,"statInformation":"0:39;1:38;2:38;3:38;4:38;5:38;6:38;7:38;8:38;9:37;10:37;11:37;12:37;13:37;14:37;15:37;16:37;17:37;18:37;19:37;20:37;21:37;22:37;23:37;24:37;25:37;26:37;27:37;28:37;29:37;30:37;31:37;32:44;33:45;34:44;35:45;36:45;37:45;38:45;39:45;40:44;41:45;42:44;43:45;44:44;45:42;46:41;47:41","date":"2019-10-11T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:11"},{"id":359538,"deviceId":611,"statInformation":"16:5;17:4;18:4;19:4;20:4;21:4","date":"2019-10-10T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:10"},{"id":359333,"deviceId":611,"statInformation":"0:39;1:39;2:39;3:39;4:39;5:39;6:38;7:38;8:38;9:38;10:38;11:37;12:37;13:37;14:37;15:37;16:37;17:37;18:37;19:37;20:37;21:38;22:38;23:39;24:39;25:39;26:39;27:39;28:39;29:39;30:39;31:39;32:45;33:45;34:45;35:45;36:45;37:45;38:45;39:44;40:44;41:45;42:45;43:45;44:40;45:39;46:39;47:39","date":"2019-10-10T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:10"},{"id":359330,"deviceId":611,"statInformation":"16:6;17:2;18:2;19:2;20:2;21:3","date":"2019-10-09T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:09"},{"id":359051,"deviceId":611,"statInformation":"0:40;1:40;2:39;3:39;4:39;5:39;6:39;7:39;8:39;9:38;10:38;11:38;12:38;13:38;14:38;15:38;16:38;17:37;18:37;19:38;20:37;21:37;22:37;23:37;24:37;25:37;26:37;27:38;28:38;29:38;30:38;31:38;32:45;33:45;34:45;35:44;36:45;37:44;38:44;39:45;40:44;41:45;42:45;43:44;44:41;45:40;46:40;47:40","date":"2019-10-09T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:09"},{"id":359048,"deviceId":611,"statInformation":"16:6;17:3;18:1;19:1;20:1;21:2","date":"2019-10-08T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:08"},{"id":358773,"deviceId":611,"statInformation":"0:39;1:38;2:38;3:38;4:38;5:38;6:38;7:38;8:38;9:37;10:37;11:37;12:37;13:37;14:37;15:37;16:37;17:37;18:37;19:37;20:37;21:37;22:37;23:37;24:37;25:37;26:37;27:37;28:37;29:37;30:37;31:37;32:45;33:45;34:45;35:45;36:45;37:45;38:45;39:44;40:44;41:44;42:44;43:44;44:42;45:41;46:41;47:40","date":"2019-10-08T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:08"},{"id":358592,"deviceId":611,"statInformation":"16:8;17:6;18:5;19:4;20:4;21:4","date":"2019-10-07T00:00:00Z","statisticType":0,"splitType":1,"dateData":"2019:10:07"},{"id":358540,"deviceId":611,"statInformation":"0:39;1:39;2:39;3:38;4:38;5:38;6:38;7:37;8:37;9:37;10:37;11:37;12:37;13:38;14:39;15:39;16:39;17:39;18:39;19:39;20:38;21:38;22:38;23:38;24:38;25:38;26:38;27:38;28:38;29:38;30:38;31:38;32:46;33:47;34:46;35:47;36:47;37:44;38:44;39:44;40:44;41:44;42:44;43:45;44:40;45:39;46:39;47:39","date":"2019-10-07T00:00:00Z","statisticType":1,"splitType":2,"dateData":"2019:10:07"}]
    #                 try:
    #                     response_json = json.loads(await response.text())
    #                     # _LOGGER.debug(f"Device Statistics: {response_json}")
    #                     today = datetime.today().replace(
    #                         hour=0, minute=0, second=0, microsecond=0
    #                     )
    #                     yesterday = (datetime.today() - timedelta(days=1)).replace(
    #                         hour=0, minute=0, second=0, microsecond=0
    #                     )
    #                     for day_stat in response_json:
    #                         if "dateData" in day_stat:
    #                             day = datetime.strptime(
    #                                 day_stat["dateData"], "%Y:%m:%d"
    #                             )
    #                             if day_stat["statisticType"] == 0:  # kWh statistics
    #                                 statisics = day_stat["statInformation"].split(";")
    #                                 sum = 0
    #                                 for stat in statisics:
    #                                     sum += float(stat.split(":")[1])
    #                                 # _LOGGER.debug(f"Day {day.strftime('%Y:%m:%d')} kWh: {sum}")
    #                                 if day == today:
    #                                     device["TodaykWh"] = sum / 10.0
    #                                 elif day == yesterday:
    #                                     device["YesterdaykWh"] = sum / 10.0
    #                                 elif day.month == today.month:
    #                                     device["MonthkWh"] += sum / 10.0
    #                                 elif (day.month == (today.month - 1)) or (
    #                                     (day.month == 12) and (today.month == 1)
    #                                 ):
    #                                     device["LastMonthkWh"] += sum / 10.0
    #                             # elif day_stat['statisticType'] == 1  # average temp statistics
    #                     device["TodaykWh"] = round(device["TodaykWh"], 2)
    #                     device["YesterdaykWh"] = round(device["YesterdaykWh"], 2)
    #                     device["MonthkWh"] = round(device["MonthkWh"], 2)
    #                     device["LastMonthkWh"] = round(device["LastMonthkWh"], 2)
    #                     # _LOGGER.debug(device)
    #                 except json.decoder.JSONDecodeError as ex:
    #                     _LOGGER.error(f"JSON Decode Error: {ex}")
    #                     _LOGGER.error(await response.text())
    #                     error = True
    #             else:
    #                 error = True
    #             if error and (datetime.utcnow() - self.last_login_attempt) > timedelta(
    #                 seconds=60
    #             ):
    #                 _LOGGER.warning(
    #                     "Error while requesting stats. Attempting re-connect!"
    #                 )
    #                 await self.connect()

    # async def update_all_devices(self):
    #     """Update all devices."""
    #     if self.websession is not None:
    #         if self.devices is not None:
    #             for device in self.devices:
    #                 # Get Device Status
    #                 await self.update_device_status(device)
    #                 # Get Device Statistics
    #                 # await self.update_device_stats(device)

    async def set_temperature(self, heater: Heater, temperature: float):
        """Set target temperature for device."""
        resp = await self._post_request(
            r"/api/panelconvector/setTemperature",
            {
                "deviceId": heater.real_device_id,
                "temperature": temperature,
            },
        )
        if resp and "status" in resp and resp["status"] is True:
            _LOGGER.debug(f"Heater '{heater.name}' temperature set to: {temperature}")
            heater.set_temp = temperature
            return True
        else:
            _LOGGER.error(
                f"Failed to set heater '{heater.name}' temperature! Response: {resp}"
            )
            return False

        # if self.websession is not None:
        #     async with self.websession.post(
        #         f"{self._url}/api/panelconvector/setTemperature",
        #         json={
        #             "deviceId": device["Info"]["real_device_id"],
        #             "temperature": temperature,
        #         },
        #         allow_redirects=False,
        #     ) as response:
        #         if response and response.status == 200:
        #             # {"objectJson":"{\"ReturnStatus\":0,\"ResponseID\":61374,\"Message\":null}","status":true,"statusMessage":null}
        #             try:
        #                 response_data = json.loads(await response.text())
        #                 _LOGGER.debug(f"setTemperature Response: {response_data}")
        #                 if "status" in response_data:
        #                     return response_data["status"]
        #             except json.decoder.JSONDecodeError as ex:
        #                 _LOGGER.error(f"JSON Decode Error: {ex}")
        #                 _LOGGER.error(await response.text())
        # return False

    async def set_state(self, heater: Heater, state: int):
        """Set state of device."""
        resp = await self._post_request(
            r"/api/panelconvector/setState",
            {
                "deviceId": heater.real_device_id,
                "state": state,
            },
        )
        if resp and "status" in resp and resp["status"] is True:
            _LOGGER.debug(f"Heater '{heater.name}' state set to: {state}")
            return True
        else:
            _LOGGER.error(
                f"Failed to set heater '{heater.name}' state! Response: {resp}"
            )
            return False

        # if self.websession is not None:
        #     async with self.websession.post(
        #         f"{self._url}/api/panelconvector/setState",
        #         json={"deviceId": device["Info"]["real_device_id"], "state": state},
        #         allow_redirects=False,
        #     ) as response:
        #         if response and response.status == 200:
        #             # {"objectJson":"{\"ReturnStatus\":0,\"ResponseID\":61374,\"Message\":null}","status":true,"statusMessage":null}
        #             try:
        #                 response_data = json.loads(await response.text())
        #                 _LOGGER.debug(f"setState Response: {response_data}")
        #                 if "status" in response_data:
        #                     return response_data["status"]
        #             except json.decoder.JSONDecodeError as ex:
        #                 _LOGGER.error(f"JSON Decode Error: {ex}")
        #                 _LOGGER.error(await response.text())
        # return False

    # Websocket interface
    async def run_websocket(self):
        """Connect to WebSocket."""
        # if self.websession is not None:
        # self.ws_thread = threading.Thread(target=self.websocket_thread)
        # self.ws_thread.daemon = True
        # self.ws_thread.start()

        await self.ws_connect()
        if self.websocket is not None:
            # Start listener and heartbeat
            # await asyncio.wait([self.ws_listener(), self.ws_heartbeat()])
            loop = asyncio.get_event_loop()
            loop.create_task(self.ws_heartbeat())
            loop.create_task(self.ws_listener())
            # await self.ws_heartbeat()
            # await self.ws_listener()

    # def websocket_thread(self):
    #   _LOGGER.info(f"Websocket Thread Started")
    #   loop = asyncio.new_event_loop()
    #   asyncio.set_event_loop(loop)
    #   loop.run_until_complete(self.ws_connect())
    #   loop.run_until_complete(
    #       asyncio.gather([self.ws_listener(), self.ws_heartbeat()])
    #   )
    #   loop.close()
    #   _LOGGER.info(f"Websocket Thread Stopped")

    async def ws_connect(self):
        """Connect to WebSocket."""
        if self.websession is not None:
            self.websocket = await self.websession.ws_connect("wss://myeldom.com")
            if self.websocket:
                _LOGGER.info("Websocket Connection Established")
                if "id" in self.user_info:
                    # await self.websocket.send('{"MessageType":"ActiveUserPing","Data":%d}' % self.user_info['id'])
                    await self.websocket.send_json(
                        {"MessageType": "ActiveUserPing", "Data": self.user_info["id"]}
                    )
                    await asyncio.sleep(0.1)

                for dev_id in self.devices:
                    # Send request for periodic (detailed) status reports (Command 2)
                    timestamp = (
                        datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
                    )
                    # msg = (
                    #     '{"MessageType":"MessageDistributor","Data":"{\"Data\":\"%s\",\"ProviderID\":6,\"Date\":\"%s\",\"Command\":2}"}'
                    #     % (dev_id, timestamp)
                    # )
                    # _LOGGER.debug(f"ws_connect: {msg}")
                    # await self.websocket.send(msg)
                    await self.websocket.send_json(
                        {
                            "MessageType": "MessageDistributor",
                            "Data": '{"Data":"%s","ProviderID":6,"Date":"%s","Command":2}'
                            % (dev_id, timestamp),
                        }
                    )
                    await asyncio.sleep(0.1)
                # Start Status Push: Command 2
                # datetime.utcnow().isoformat(timespec='milliseconds')+'Z'
                # await self.websocket.send('{"MessageType":"MessageDistributor","Data":"{\\\"Data\\\":\\\"A9D6C1CEF85A\\\",\\\"ProviderID\\\":3,\\\"Date\\\":\\\"2019-10-13T17:55:26.955Z\\\",\\\"Command\\\":2}"}')
                #                            {"MessageType":"MessageDistributor","Data":"{\\\"Data\\\":\\\"A9D6C1CEF85A\\\",\\\"ProviderID\\\":6,\\\"Date\\\":\\\"2019-10-13T18:54:35.846Z\\\",\\\"Command\\\":2}"}
                # Stop Status Push: Command 3
                # await self.websocket.send('{"MessageType":"MessageDistributor","Data":"{\\\"Data\\\":\\\"A9D6C1CEF85A\\\",\\\"ProviderID\\\":3,\\\"Date\\\":\\\"2019-10-13T18:02:39.162Z\\\",\\\"Command\\\":3}"}')
                # await self.websocket.send('{"MessageType":"MessageDistributor","Data":"{\\\"Data\\\":\\\"A9D6C1CEF85A\\\",\\\"ProviderID\\\":6,\\\"Date\\\":\\\"2019-10-13T18:02:39.427Z\\\",\\\"Command\\\":2}"}')
                # await asyncio.sleep(0.1)
                # await self.websocket.send('{"MessageType":"MessageDistributor","Data":"{\\\"Data\\\":\\\"A85161C1ED5A\\\",\\\"ProviderID\\\":3,\\\"Date\\\":\\\"2019-10-13T17:55:26.955Z\\\",\\\"Command\\\":2}"}')
                # await self.websocket.send('{"MessageType":"MessageDistributor","Data":"{\\\"Data\\\":\\\"A85161C1ED5A\\\",\\\"ProviderID\\\":3,\\\"Date\\\":\\\"2019-10-13T18:02:39.162Z\\\",\\\"Command\\\":3}"}')
                # await self.websocket.send('{"MessageType":"MessageDistributor","Data":"{\\\"Data\\\":\\\"A85161C1ED5A\\\",\\\"ProviderID\\\":6,\\\"Date\\\":\\\"2019-10-13T18:02:39.427Z\\\",\\\"Command\\\":2}"}')
                # await asyncio.sleep(0.1)
                # await self.websocket.send('{"MessageType":"MessageDistributor","Data":"{\"Data\":\"A85161C1ED5A\",\"ProviderID\":3,\"Date\":\"2019-10-13T16:15:19.589Z\",\"Command\":2}"}')
                # await self.websocket.send('{"MessageType": "MessageDistributor","Data": "{\"Data\":\"A9D6C1CEF85A\",\"ProviderID\":3,\"Date\":\"2019-10-13T17:52:29.053Z\",\"Command\":3}"}
            else:
                _LOGGER.error("Unable to Establish Websocket Connection!")
                self.websocket = None

    async def ws_disconnect(self):
        """Disconnect from WebSocket."""
        if self.websocket is not None:
            await asyncio.wait_for(self.websocket.close(), timeout=5)
            _LOGGER.info("WebSocket Connection Closed.")
            self.websocket = None

    async def ws_listener(self):
        """Websocket Listener."""
        _LOGGER.debug("ws_listener started")
        # while self.websocket is not None:
        try:
            # msg_data = await self.websocket.receive_json()
            msg_data = {}
            async for msg in self.websocket:
                _LOGGER.debug(f"ws_listener: {msg}")
                if "ProviderID" in msg_data:
                    if msg_data["ProviderID"] == 3 or msg_data["ProviderID"] == 6:
                        # "ProviderID" == 3 - Brief status message:
                        # {"ProviderID":3,"Data":[{"ID":0,"DeviceID":"A9D6C1CEF85A","Type":4,"Protocol":1,"Manifactor":1,"HardwareVersion":14,"SoftwareVersion":25,"SaveLocked":false,"LastRefreshDate":"2019-10-13T18:00:06.3048796Z"}]
                        # "ProviderID" == 6 - Detailed status message:
                        # {"ProviderID":6,"Data":[{"ID":0,"DeviceID":"A9D6C1CEF85A","Type":4,"Protocol":1,"Manifactor":1,"HardwareVersion":14,"SoftwareVersion":25,"SaveLocked":false,"LastRefreshDate":"2019-10-13T19:03:59.3499238Z","Alarms":[{"ID":0,"Enabled":true,"Begin":"2000-01-01T16:00:00Z","End":"2000-01-01T22:00:00Z","Temperature":22.0,"DaysEnabled":15},{"ID":0,"Enabled":true,"Begin":"2000-01-01T16:00:00Z","End":"2000-01-01T22:30:00Z","Temperature":22.0,"DaysEnabled":16},{"ID":0,"Enabled":false,"Begin":"2000-01-01T08:00:00Z","End":"2000-01-01T16:00:00Z","Temperature":22.0,"DaysEnabled":96},{"ID":0,"Enabled":true,"Begin":"2000-01-01T16:00:00Z","End":"2000-01-01T22:00:00Z","Temperature":22.0,"DaysEnabled":96},{"ID":0,"Enabled":false,"Begin":"2000-01-01T00:00:00Z","End":"2000-01-01T23:59:00Z","Temperature":22.0,"DaysEnabled":127},{"ID":0,"Enabled":false,"Begin":"2000-01-01T00:00:00Z","End":"2000-01-01T23:59:00Z","Temperature":24.0,"DaysEnabled":127},{"ID":0,"Enabled":false,"Begin":"2000-01-01T00:00:00Z","End":"2000-01-01T23:59:00Z","Temperature":18.0,"DaysEnabled":127}],"Rate1Start":"2000-01-01T06:00:00Z","Rate2Start":"2000-01-01T22:00:00Z","ErrorFlag":0,"State":1,"Power":7,"SetTemp":18.0,"TimerSTempA":22.0,"TimerSFI":2,"TimerNDate":"2000-01-01T22:00:00Z","TimerStartDoW":64,"EnergyDate":"0001-01-01T00:00:00Z","EnergyD":58.0,"EnergyN":5.0,"WeeklyProgramator":false,"AutomaticDatetime":true,"OpenWindow":1,"PowerIDX":1,"Date":"2019-10-13T21:03:58Z","AmbientTemp":22.2,"PCBTemp":34.0,"BoostHeating":false}]}
                        if "Data" in msg_data:
                            # print(msg_data['Data'])
                            for dev_status in msg_data["Data"]:
                                # print(dev_status)
                                if "DeviceID" in dev_status:
                                    dev_id = dev_status["DeviceID"]
                                    if dev_id in self.devices:
                                        # update device with new data
                                        self.devices[dev_id]["Status"].update(
                                            dev_status
                                        )
                                        # pprint(self.devices)
        except Exception as ex:
            _LOGGER.warning(f"ws_listener: Connection with server closed! {ex}")
            # break

    async def ws_heartbeat(self):
        """Websocket keep-alive (heartbeat)."""
        while self.websocket is not None:
            # send 'Ping' Messages every 15 seconds
            _LOGGER.debug("ws_heartbeat")
            for dev_id in self.devices:
                try:
                    await self.websocket.send_json(
                        {"MessageType": "Ping", "Data": dev_id}
                    )
                except Exception as ex:
                    _LOGGER.warning(
                        f"ws_heartbeat: Connection with server closed! {ex}"
                    )
                    return
            await asyncio.sleep(15)

    async def ws_send(self, message):
        """Send a message to the WebSocket."""
        if self.websocket is not None:
            await self.websocket.send(message)


if __name__ == "__main__":
    logging.basicConfig(
        format="[%(asctime)s][%(levelname)s] %(message)s", level=logging.DEBUG
    )
    TEST_USER = ""
    TEST_PASS = ""

    loop = asyncio.get_event_loop()
    my_eldom = MyEldom(TEST_USER, TEST_PASS)

    async def test(loop, my_eldom):
        """Test function."""
        # loop.create_task()
        await my_eldom.connect()
        # await my_eldom.get_user_info()
        # await my_eldom.get_device_groups()
        # await my_eldom.get_device_list()

        heaters = await my_eldom.fetch_all_heaters()
        for heater in heaters.values():
            print(heater)

        await asyncio.sleep(10)
        await my_eldom.disconnect()

    loop.run_until_complete(test(loop, my_eldom))
