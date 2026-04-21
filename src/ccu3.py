import requests

from .parser import DAYS, MAX_SLOTS

DAY_INDEX = {day: i + 1 for i, day in enumerate(DAYS)}  # Mo=1 .. So=7


class CCU3Client:
    def __init__(self, host: str, port: int = 8181, user: str = "", password: str = ""):
        self.base_url = f"http://{host}:{port}"
        self.auth = (user, password) if user else None

    def _rega_script(self, script: str) -> str:
        resp = requests.post(
            f"{self.base_url}/tclrega.exe",
            data=script.encode("utf-8"),
            auth=self.auth,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.text

    def find_bwth_devices(self) -> dict[str, str]:
        """Return {room_name: channel_address} for all HmIP-BWTH channel 1 devices."""
        script = """
string sRoomID; string sDevID; string sChanID;
foreach(sRoomID, dom.GetObject(ID_ROOMS).EnumIDs()) {
  object oRoom = dom.GetObject(sRoomID);
  foreach(sDevID, oRoom.EnumUsedIDs()) {
    object oDev = dom.GetObject(sDevID);
    if(oDev.Type() == OT_DEVICE && oDev.HssType() == "HmIP-BWTH") {
      foreach(sChanID, oDev.Channels().EnumIDs()) {
        object oChan = dom.GetObject(sChanID);
        if(oChan.ChnIndex() == 1) {
          WriteLine(oRoom.Name() # "\\t" # oChan.Address());
        }
      }
    }
  }
}
"""
        output = self._rega_script(script)
        result = {}
        for line in output.splitlines():
            line = line.strip()
            if "\t" not in line:
                continue
            room, addr = line.split("\t", 1)
            if room not in result:
                result[room] = addr
        return result

    def read_schedule(self, channel_address: str) -> dict[str, list[tuple[int, float]]]:
        """Read all 13 slots × 7 days from a BWTH channel 1.

        Returns {day: [(endtime_minutes, temperature), ...]} with MAX_SLOTS entries each.
        """
        lines = []
        for day_name, day_num in DAY_INDEX.items():
            for n in range(1, MAX_SLOTS + 1):
                et_dp = f"P1_ENDTIME_{day_num}_{n}"
                temp_dp = f"P1_TEMPERATURE_{day_num}_{n}"
                lines.append(
                    f'object oET = dom.GetObject("{channel_address}:{et_dp}"); '
                    f'object oT = dom.GetObject("{channel_address}:{temp_dp}"); '
                    f'if(oET && oT) {{ WriteLine("{day_name}\\t{n}\\t" # oET.Value() # "\\t" # oT.Value()); }}'
                )
        script = "\n".join(lines)
        output = self._rega_script(script)

        result: dict[str, list[tuple[int, float]]] = {d: [] for d in DAYS}
        for line in output.splitlines():
            parts = line.strip().split("\t")
            if len(parts) != 4:
                continue
            day, _n, et_str, temp_str = parts
            try:
                endtime = int(float(et_str))
                temp = float(temp_str)
            except ValueError:
                continue
            if day in result:
                result[day].append((endtime, temp))

        return result

    def write_day(self, channel_address: str, day: str, slots: list[tuple[int, float]]) -> None:
        """Write all MAX_SLOTS entries for one day in a single ReGaHSS batch."""
        day_num = DAY_INDEX[day]
        lines = []
        for n, (endtime, temp) in enumerate(slots, start=1):
            et_dp = f"P1_ENDTIME_{day_num}_{n}"
            temp_dp = f"P1_TEMPERATURE_{day_num}_{n}"
            lines.append(
                f'dom.GetObject("{channel_address}:{et_dp}").State({endtime});'
                f'dom.GetObject("{channel_address}:{temp_dp}").State({temp:.1f});'
            )
        # Trigger a save by toggling ACTIVE_PROFILE — workaround to flush to device
        lines.append(
            f'object oChan = dom.GetObject("{channel_address}"); '
            f'if(oChan) {{ oChan.DPByAddress("P1_SCHEDULE_PROFILE_INDEX").SetValue(1); }}'
        )
        script = "\n".join(lines)
        self._rega_script(script)
