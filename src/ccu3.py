import xmlrpc.client

from .parser import DAYS, MAX_SLOTS

XMLRPC_PORT = 2010

DAY_NAMES = {
    "Mo": "MONDAY",
    "Di": "TUESDAY",
    "Mi": "WEDNESDAY",
    "Do": "THURSDAY",
    "Fr": "FRIDAY",
    "Sa": "SATURDAY",
    "So": "SUNDAY",
}


class CCU3Client:
    def __init__(self, host: str, port: int = 8181, user: str = "", password: str = ""):
        self._rega_base = f"http://{host}:{port}"
        auth = f"{user}:{password}@" if user else ""
        self._rpc = xmlrpc.client.ServerProxy(f"http://{auth}{host}:{XMLRPC_PORT}/")

    def _rega(self, script: str) -> str:
        import requests
        oneliner = " ".join(line.strip() for line in script.splitlines() if line.strip())
        resp = requests.post(
            f"{self._rega_base}/tclrega.exe",
            data=oneliner.encode("utf-8"),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.text

    def find_bwth_devices(self) -> dict[str, str]:
        """Return {room_name: channel_address} for all HmIP-BWTH channel 1 devices."""
        # Step 1: get BWTH device IDs via ReGaHSS
        dev_ids = [
            line.strip()
            for line in self._rega(
                'string sID; foreach(sID, dom.GetObject(ID_DEVICES).EnumIDs()) '
                '{ object o = dom.GetObject(sID); if(o.HssType() == "HmIP-BWTH") { WriteLine(sID); } }'
            ).splitlines()
            if line.strip().isdigit()
        ]
        if not dev_ids:
            return {}

        # Step 2: per device, get all channel addresses (filter :1 in Python)
        chan_id_to_addr: dict[str, str] = {}
        for dev_id in dev_ids:
            for line in self._rega(
                f'string sID; foreach(sID, dom.GetObject({dev_id}).Channels().EnumIDs()) '
                f'{{ object o = dom.GetObject(sID); WriteLine(sID # "\\t" # o.Address()); }}'
            ).splitlines():
                line = line.strip()
                if "\t" not in line or line.startswith("<"):
                    continue
                chan_id, addr = line.split("\t", 1)
                if addr.strip().endswith(":1"):
                    chan_id_to_addr[chan_id.strip()] = addr.strip()

        if not chan_id_to_addr:
            return {}

        # Step 3: map room names to channel addresses via EnumUsedIDs
        result: dict[str, str] = {}
        for line in self._rega(
            'string sRoomID; foreach(sRoomID, dom.GetObject(ID_ROOMS).EnumIDs()) '
            '{ object oRoom = dom.GetObject(sRoomID); string sUsedID; '
            'foreach(sUsedID, oRoom.EnumUsedIDs()) { WriteLine(oRoom.Name() # "\\t" # sUsedID); } }'
        ).splitlines():
            line = line.strip()
            if "\t" not in line or line.startswith("<"):
                continue
            room_name, used_id = line.split("\t", 1)
            used_id = used_id.strip()
            if used_id in chan_id_to_addr and room_name not in result:
                result[room_name] = chan_id_to_addr[used_id]
        return result

    def read_schedule(self, channel_address: str) -> dict[str, list[tuple[int, float]]]:
        """Read P1 week schedule via XML-RPC getParamset (MASTER paramset)."""
        params = self._rpc.getParamset(channel_address, "MASTER")
        result: dict[str, list[tuple[int, float]]] = {}
        for day in DAYS:
            day_en = DAY_NAMES[day]
            slots = []
            for n in range(1, MAX_SLOTS + 1):
                et = params.get(f"P1_ENDTIME_{day_en}_{n}")
                temp = params.get(f"P1_TEMPERATURE_{day_en}_{n}")
                if et is None or temp is None:
                    break
                slots.append((int(et), float(temp)))
            result[day] = slots
        return result

    def write_day(self, channel_address: str, day: str, slots: list[tuple[int, float]]) -> None:
        """Write all MAX_SLOTS entries for one day via XML-RPC putParamset."""
        day_en = DAY_NAMES[day]
        params = {}
        for n, (endtime, temp) in enumerate(slots, start=1):
            params[f"P1_ENDTIME_{day_en}_{n}"] = endtime
            params[f"P1_TEMPERATURE_{day_en}_{n}"] = temp
        self._rpc.putParamset(channel_address, "MASTER", params)
