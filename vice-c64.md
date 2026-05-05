# C64 Emulator
How to compile vice emulator on the latest sources.


## Install build dependencies
```bash
sudo apt install build-essential automake autoconf libtool \
libreadline-dev libgtk-3-dev libvte-dev libasound2-dev \
libpulse-dev libxaw7-dev libxmu-dev libxpm-dev libxext-dev \
libcurl4-openssl-dev libpng-dev libjpeg-dev zlib1g-dev \
libglew-dev libmpg123-dev libvorbis-dev libflac-dev \
libavformat-dev libavcodec-dev libswscale-dev libavutil-dev \
libfreetype6-dev libtiff-dev libgif-dev \
flex bison dos2unix xa65 libevdev-dev
```

## Download sources
```bash
wget https://sourceforge.net/projects/vice-emu/files/releases/vice-3.10.tar.gz
tar xvf vice-3.10.tar.gz
cd vice-3.10
```

## Configure vice
```bash
./configure --with-gif
make -j$(nproc)
sudo make install
```

## Verzeichnisse anlegen
```bash
mkdir -p ~/.config/vice/C64
mkdir -p ~/.local/share/vice/C64
```

ROMs werden durch `sudo make install` nach `/usr/local/share/vice/C64/` installiert.

## Emulator starten
```bash
x64sc
```

