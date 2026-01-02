# Create a virtual pdf printer for windows clients
Commands to create a virtual pdf printer for windows clients on any linux pc.
Samba should be installed. If not see this tutorial:

* [Create windows share for raid volume](https://github.com/wlanboy/raspberrypi/blob/main/windows-share.md)

## install dependencies
```bash
sudo apt update
sudo apt install cups-pdf -y
```

## Create share with permissions
```bash
sudo mkdir -p /mnt/sata/smb/pdf
sudo chown -R nobody:users /mnt/sata/smb/pdf
sudo chmod -R 777 /mnt/sata/smb/pdf
```

## Add share to smb.conf
```bash
sudo nano /etc/samba/smb.conf
```
Content:
```Plaintext
[pdf]
   comment = PDF Share
   path = /mnt/sata/smb/pdf
   browseable = yes
   read only = no
   guest ok = yes
   guest only = yes
   force user = nobody
   force group = users
   create mask = 0666
   directory mask = 0777
```

### Restart samba
```bash
sudo systemctl restart smbd
```

## Add your user to the cups admins
```bash
sudo usermod -a -G lpadmin YOUR_USER_NAME
```

## Configure CUPS-PDF Storage Path
- Open the configuration file: 
```bash
sudo nano /etc/cups/cups-pdf.conf
```
- Find the line that says 
```
Out /var/spool/cups-pdf/${USER}.
```
- Change it to: 
```
Out /mnt/sata/smb/pdf
```
- Save and exit (Ctrl+O, Enter, Ctrl+X).

## Configure CUPS
- Open the CUPS config: 
```bash
sudo nano /etc/cups/cupsd.conf
```
- Look for the line Listen ... Ensure it says: Port 631
- Add this line at the top of the file to allow your custom domain: 
```
ServerAlias gmk.lan
```
- Enable remote sharing Restart CUPS: 
```bash
sudo cupsctl --remote-any --share-printers
sudo systemctl restart cups
```

## Fix the AppArmor Block
AppArmor restricts where CUPS is allowed to write files for security reasons. It doesn't know about your /mnt/sata path yet.
- Edit the CUPS AppArmor profile: 
```bash
sudo nano /etc/apparmor.d/usr.sbin.cupsd
```
- Scroll to the bottom of the file, just before the closing bracket }.
Add these two lines (replace the path with your exact folder):
```Plaintext
  /mnt/sata/smb/pdf/ rw,
  /mnt/sata/smb/pdf/* rw,
```
- Save and exit (Ctrl+O, Enter, Ctrl+X).
- Reload AppArmor: 
```bash
sudo systemctl restart apparmor
```

## Add the Printer in CUPS Web Interface
- Go to https://gmk.lan:631/admin in your browser.
- Login with your linux account
- Go to Administration -> Add Printer.
- Select CUPS-PDF (Virtual PDF Printer) and click Continue.
- Give it a name (e.g., Network-PDF-Printer).
- Important: Check "Share This Printer".
- When asked for a Model, select Generic and then Generic CUPS-PDF Printer.

## Check for spool jobs
- Go to https://gmk.lan:631/printers/Virtual_PDF_Printer in your browser

## Connect from Windows
- In Windows, go to Printers & Scanners > Add a printer.
- Click "The printer that I want isn't listed".
- Select "Select a shared printer by name" and enter: https://gmk.lan:631/printers/Virtual_PDF_Printer
- When prompted for a driver, choose Generic -> MS Publisher Imagesetter. (This is a standard PostScript driver that works perfectly for PDF creation).

## Accessing the Files
- Now, when you print from Windows:
- The document "prints" to the Pi.
- The Pi converts it to a PDF.
- The PDF appears in the \\gmk.lan\pdf network folder.

