# get a gps module
GPS-Modul VK-162 with TCXO EEPROM

## install tools
```bash
sudo apt update
sudo apt install gpsd gpsd-clients chrony pps-tools
```

## find device
```bash
ls /dev/ttyA* /dev/ttyU*
ls: Zugriff auf '/dev/ttyU*' nicht möglich: Datei oder Verzeichnis nicht gefunden
 /dev/ttyACM0

```

## config server
```bash
sudo nano /etc/default/gpsd

START_DAEMON="true"
USBAUTO="false"
DEVICES="/dev/ttyACM0"
GPSD_OPTIONS="-n"
```

## if it failes - maybe you have deactivated ipv6 due to your isp provider
```bash
sudo systemctl edit gpsd.socket

[Socket]
ListenStream=
ListenStream=/run/gpsd.sock
ListenStream=127.0.0.1:2947
BindIPv6Only=no

sudo systemctl daemon-reload
sudo systemctl restart gpsd.socket
``

## check gps status
```bash
gpsmon

#or

gpspipe -w | grep TPV

#"mode":3 is important
#0	Unknown -> no data
#1	No Fix -> time, satellite data, but no gps data
#2	2D Fix -> At least 3 satellites found
#3  3D Fix -> At least 4 satellites found
```

## configure chrony to use gps to get the time
```bash
sudo nano /etc/chrony/chrony.conf

# GPS timeing source with Shared Memory (SHM)
refclock SHM 0 refid GPS precision 1e-3 offset 0.0668 delay 0.1 poll 3 filter 16 trust prefer
# Local network access
allow 192.168.178.0/24

sudo systemctl restart chrony
```
## parameters explained
| Parameter | Value | Description |
| :--- | :--- | :--- |
| **`refclock`** | `SHM 0` | Interface to the **Shared Memory** segment (NTP0) provided by `gpsd`. |
| **`refid`** | `GPS` | A unique 4-character ID displayed in `chronyc sources`. |
| **`precision`** | `1e-3` | Declared precision ($10^{-3}$s). |
| **`offset`** | `0.0668` | **Calibration:** Static compensation (66.8ms) for USB bus latency and processing time. |
| **`delay`** | `0.1` | Estimated fixed delay. Low values prioritize local hardware over network peers. |
| **`poll`** | `3` | Polling interval ($2^3 = 8$ seconds) for synchronization of a large value sample. |
| **`filter`** | `16` | **Median Filter:** Uses the last 16 samples to eliminate USB-scheduling jitter. |
| **`trust`** | *N/A* | Trusted local timing source |
| **`prefer`** | *N/A* | Ensures the GPS remains the primary time source over network-based servers. |

## check chrony sources
```bash
chronyc sources -v


  .-- Source mode  '^' = server, '=' = peer, '#' = local clock.
 / .- Source state '*' = current best, '+' = combined, '-' = not combined,
| /             'x' = may be in error, '~' = too variable, '?' = unusable.
||                                                 .- xxxx [ yyyy ] +/- zzzz
||      Reachability register (octal) -.           |  xxxx = adjusted offset,
||      Log2(Polling interval) --.      |          |  yyyy = measured offset,
||                                \     |          |  zzzz = estimated error.
||                                 |    |           \
MS Name/IP address         Stratum Poll Reach LastRx Last sample               
===============================================================================
#? GPS                           0   4     0     -     +0ns[   +0ns] +/-    0ns
```
-> Chrony knows about the source but does not get any information

## set groups right
```bash
sudo usermod -aG dialout gpsd
sudo systemctl restart gpsd
sudo systemctl restart chrony
```

## check if data is coming through shared memory
```bash
sudo ntpshmmon
```

## check chrony sources
```bash
chronyc sources -v

  .-- Source mode  '^' = server, '=' = peer, '#' = local clock.
 / .- Source state '*' = current best, '+' = combined, '-' = not combined,
| /             'x' = may be in error, '~' = too variable, '?' = unusable.
||                                                 .- xxxx [ yyyy ] +/- zzzz
||      Reachability register (octal) -.           |  xxxx = adjusted offset,
||      Log2(Polling interval) --.      |          |  yyyy = measured offset,
||                                \     |          |  zzzz = estimated error.
||                                 |    |           \
MS Name/IP address         Stratum Poll Reach LastRx Last sample               
===============================================================================
#* GPS                           0   3   377     5   +549us[+1029us] +/-   51ms
^- xxxxxxxxxxxxxxxxxxxxxxxx>     2   6   377    37  +1455us[ +257us] +/- 9430us
^- xxxxxxxxxxxxxxxxxxxxxxxx>     2   6   377    36  +2361us[+1129us] +/- 9321us
^- xxxxxxxxxxxxxxxxxxxxxxxx>     3   6   377    38  +1414us[ +237us] +/-   19ms
```

## check statistics for your own to optimize config values
```bash
cat /var/log/chrony/statistics.log | grep GPS
```

## check statistics with simple script
```bash
./chrony/stats.sh
```