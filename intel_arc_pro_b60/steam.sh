sudo mkdir /data/steam
sudo chown -R $USER:$USER /data/steam
sudo apt install flatpak
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub com.valvesoftware.Steam

sudo flatpak override com.valvesoftware.Steam --filesystem=/data/steam
# Entzieht den Zugriff auf den spezifischen Pfad wieder
#sudo flatpak override com.valvesoftware.Steam --nofilesystem=/data/steam
