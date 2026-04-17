Pico W setup for Sprint 2

Files:
- `main.py`: MicroPython UDP receiver for the Pico W

What to edit before upload:
- Set `WIFI_SSID` in `main.py`
- Set `WIFI_PASSWORD` in `main.py`

What this script does:
- Connects the Pico W to Wi-Fi
- Prints the Pico IP address in Thonny
- Listens for Sprint 2 UDP packets on port `5000`
- Verifies the `DPTH` header and packet size
- Prints the 5x5 matrix so you can confirm the link

Upload flow in Thonny:
1. Connect the Pico W over USB.
2. In Thonny, select the MicroPython interpreter for the Pico.
3. Open `pico_w/main.py`.
4. Fill in your Wi-Fi name and password.
5. Save it to the Pico as `/main.py`.
6. Press the Stop/Restart button in Thonny.
7. Read the printed IP address and copy it into `config_hand_tracking.py` as `PICO_IP`.
