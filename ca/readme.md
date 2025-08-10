Creating a local Certificate Authority (CA) and using `acme.sh` with it is a great way to manage certificates for your homelab.

## 1\. Create a Local Certificate Authority

This section walks you through creating your own self-signed root CA certificate. This certificate will be used to sign other certificates for your local devices.

1.  **Create a directory** to store your CA files and navigate into it.

    ```bash
    mkdir -p ~/local-ca
    cd ~/local-ca
    ```

2.  **Generate a private key** for your CA. This will be the `ca.key` file. The `4096` value specifies a strong key length.

    ```bash
    openssl genrsa -out ca.key 4096
    ```

3.  **Create the root CA certificate** (`ca.pem`). This command uses the private key you just created to generate a self-signed certificate. The `-subj` flag pre-fills the subject information, which is important for identifying the certificate. The `-days 3650` option makes the certificate valid for 10 years.

    ```bash
    openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 \
      -out ca.pem -subj "/C=DE/ST=Germany/L=LAN/O=Homelab CA/CN=Homelab Root CA"
    ```

4.  **Install the CA certificate** on your system. This step tells your operating system to trust the certificates signed by your new CA. The `sudo update-ca-certificates` command refreshes the certificate store.

    ```bash
    sudo cp ca.pem /usr/local/share/ca-certificates/ca-lan.crt
    sudo update-ca-certificates
    ```

## 2\. Install and Configure acme.sh

`acme.sh` is a popular shell script for managing certificates from various CAs, including your own.

1.  **Install `socat`**, a utility that `acme.sh` uses for some challenge types.

    ```bash
    sudo apt-get install socat
    ```

2.  **Download and install `acme.sh`**. This command fetches the installation script from GitHub and runs it. It will set up the necessary files and add an alias to your `.bashrc` or a similar shell configuration file.

    ```bash
    curl https://get.acme.sh | sh
    ```

3.  **Reload your shell environment** to make the `acme.sh` command available.

    ```bash
    source ~/.bashrc
    ```

4.  **Set the default CA to local**. This is the crucial step that tells `acme.sh` to use your newly created CA for signing certificates by default.

    ```bash
    acme.sh --set-default-ca --server local
    ```

You can now use `acme.sh` to generate certificates signed by your own local CA for your homelab devices.
