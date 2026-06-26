# 7-Inch Display Case Measurement Worksheet

Use this worksheet before designing the Bambu X1 Carbon test-fit plate or full morsePi enclosure.

Design goal:

```text
A 3D printed enclosure for the 7-inch touchscreen with enough rear depth for the Raspberry Pi 4 mounted on the back, DSI ribbon, USB speaker cable, power cable, GPIO wiring, ventilation, and service access.
```

## Tools

- Calipers, preferred
- Ruler, acceptable for rough first pass
- Paper and pencil for marking hole centers
- Photos of front, back, side, and cable exits

Record measurements in millimeters.

## Display Measurements

| Measurement | Value | Notes |
|---|---:|---|
| Overall display module width |  | Left edge to right edge |
| Overall display module height |  | Top edge to bottom edge |
| Overall display module thickness |  | Screen/front to deepest display-board point, without Pi |
| Visible screen width |  | Opening needed for active display |
| Visible screen height |  | Opening needed for active display |
| Bezel width, left |  | Module edge to visible screen |
| Bezel width, right |  | Module edge to visible screen |
| Bezel width, top |  | Module edge to visible screen |
| Bezel width, bottom |  | Module edge to visible screen |

## Mounting Holes

| Measurement | Value | Notes |
|---|---:|---|
| Mounting-hole diameter |  | Confirm screw size |
| Left-to-right hole spacing |  | Center to center |
| Top-to-bottom hole spacing |  | Center to center |
| Left hole center to left board edge |  |  |
| Right hole center to right board edge |  |  |
| Top hole center to top board edge |  |  |
| Bottom hole center to bottom board edge |  |  |
| Number of mounting holes used |  |  |

Sketch:

```text
Front view

  width = ______ mm
  +------------------------------------------------+
  | o                                          o   |
  |                                                |
  |              visible screen                    | height = ______ mm
  |                                                |
  | o                                          o   |
  +------------------------------------------------+

  hole spacing left/right = ______ mm
  hole spacing top/bottom = ______ mm
```

## Raspberry Pi Stack Depth

Measure with the Pi attached to the back of the display in the planned orientation.

| Measurement | Value | Notes |
|---|---:|---|
| Display front face to Pi board top |  | Depth before cables |
| Display front face to tallest USB plug/cable |  | Usually drives case depth |
| Display front face to tallest GPIO jumper |  | Include LED/key wiring |
| Display front face to DSI ribbon bend |  | Avoid tight folds |
| Display front face to power cable bend |  | Include 90 degree adapter if used |
| Minimum rear cavity depth needed |  | Add clearance |

Recommended starting clearance:

- Add at least `3 mm` clearance above electronics.
- Add extra room where cables bend.
- Leave room for airflow around the Pi.

## Port And Cable Exits

Mark which side each cable should exit.

| Cable/port | Preferred exit | Opening size | Notes |
|---|---|---:|---|
| USB-C power |  |  | Include 90 degree adapter if used |
| USB speaker |  |  | Which USB port will be used |
| Telegraph key cable |  |  | GPIO/key wiring exit |
| LED wires |  |  | If LED mounts on case |
| DSI ribbon | Internal |  | Needs bend radius, not an exterior opening |
| HDMI/USB service access |  |  | Decide whether service ports stay reachable |

## Ventilation

| Area | Plan |
|---|---|
| Pi CPU side |  |
| Top vents |  |
| Bottom vents |  |
| Side vents |  |
| Fan needed? | Probably no for first prototype, confirm after heat testing |

Heat test after first case prototype:

```bash
vcgencmd measure_temp
```

Run after 20 minutes of practice or station idle with browser open.

## First Prototype Plan

Print a small test-fit plate before printing the full case.

Test plate should verify:

- Screen opening size
- Display mounting-hole spacing
- Screw fit
- Bezel coverage
- Touchscreen edge clearance

Do not print the full enclosure until the test plate fits.

## Full Enclosure Design Notes

- Front bezel should not cover touchable screen edges.
- Rear shell needs enough depth for Pi and cable strain relief.
- Avoid pressing on the Pi, USB plugs, GPIO jumpers, or DSI ribbon.
- Add screw bosses or standoffs only after hole positions are confirmed.
- Keep case serviceable so the SD card, cables, and Pi can be accessed.
- Avoid blocking the USB speaker sound path.
- Consider rubber feet or a stand angle if the unit sits on a table.

## Photos To Save

Save these photos with the measurements:

- Front of display
- Back of display without Pi
- Back of display with Pi attached
- Side view showing total depth
- Close-up of mounting holes
- Close-up of DSI ribbon path
- Close-up of USB/power/speaker cable exits
