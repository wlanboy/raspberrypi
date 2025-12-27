# Switch to xfce4
Commands to switch to xfce4 environment.

## install
```
sudo apt install -y xserver-xorg xfce4 xfce4-goodies
```

## switch
```
sudo systemctl get-default
sudo systemctl set-default graphical.target.
sudo dpkg-reconfigure lightdm
sudo update-alternatives --config x-session-manager # -> startxfce4
sudo update-alternatives --config x-window-manager #-> xfwm4
```
