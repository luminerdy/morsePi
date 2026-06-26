# Bill of Materials

Parts list for the current morsePi test station.

Prices are captured estimates and may change. Equivalent parts can be used if they provide the same function.

| Item | Purpose | Link | Estimated Cost |
|---|---|---|---:|
| USB C 90 Degree Adapter | Cleaner power cable routing for the 7-inch station | [Amazon B0FYPLN6DM](https://www.amazon.com/dp/B0FYPLN6DM) | $9.99 |
| 7 Inch Touchscreen IPS DSI Display | Primary touch interface for the student station | [Amazon B0D3QB7X4Z](https://www.amazon.com/dp/B0D3QB7X4Z) | $38.99 |
| CanaKit 3.5A Raspberry Pi 4 Power Supply with PiSwitch | Stable Pi 4 power with inline switch | [Amazon B07TSFYXBC](https://www.amazon.com/dp/B07TSFYXBC) | $12.99 |
| USB Mini Speaker Computer Speaker | Station audio for prompts and keyer feedback | [Amazon B075M7FHM1](https://www.amazon.com/dp/B075M7FHM1) | $13.99 |
| Raspberry Pi 4, 2GB or more | Main station computer | Vendor of choice | $55.00 |
| TGKY01 Telegraph Key | Physical Morse key input | [Amazon B01MT3T676](https://www.amazon.com/dp/B01MT3T676) | $19.07 |
| MicroSD card, 32 GB | Raspberry Pi OS and station storage | Vendor of choice | $25.00 |
| Jumper wires | Wiring the status LED and resistor to GPIO/GND | Vendor of choice | TBD |

Estimated priced total: **$175.03**

Not included above:

- LED
- Current-limiting resistor for LED, usually 220 to 330 ohms
- Case, mount, or enclosure materials

## 3D Printed Case Notes

The Raspberry Pi mounts to the back of the 7-inch touchscreen, so the printed case needs to be more than a front bezel. It should be a full display enclosure with enough rear depth for the Raspberry Pi 4, DSI ribbon cable, GPIO wiring, USB speaker cable, power cable, and airflow.

Use [CASE_MEASUREMENT_WORKSHEET.md](CASE_MEASUREMENT_WORKSHEET.md) to collect dimensions before modeling the Bambu X1 Carbon test-fit plate or full enclosure.

Current design intent:

- Front opening sized for the 7-inch touch display.
- Rear cavity deep enough for the Raspberry Pi 4 mounted behind the display without pressing on the board, USB plugs, GPIO wires, or DSI ribbon.
- Access openings for USB power, USB speaker, telegraph key wiring, and any service ports that should remain reachable.
- Ventilation around the Pi so the case does not trap heat during long practice sessions.
- Internal strain relief or routing space so the DSI ribbon and GPIO jumper wires are not sharply bent.
- Mounting points or standoffs for the display/Pi stack once exact hole spacing is confirmed.
- Bambu X1 Carbon is the current target printer for prototypes.

Measurements still needed before modeling:

- Overall display module width, height, and thickness.
- Visible screen opening width and height.
- Display mounting-hole diameter and center-to-center spacing.
- Mounting-hole distance from each board edge.
- Total depth from the display front face to the deepest installed Pi/connector point.
- DSI ribbon exit location and bend direction.
- Power, USB speaker, telegraph key, and LED wire exit locations.
