# WSD for Linux

For Ubuntu 24.04 (x86-64).

## Install

Extract the downloaded package, then install:

```sh
tar -xzf wsd-1.0.0-linux-x86_64-ubuntu24.04.tar.gz
cd wsd-1.0.0-linux-x86_64-ubuntu24.04
sh install.sh
```

## Run

Monitor real disk and process activity:

```sh
~/.local/bin/wsd
```

Or try recommendations using sample data:

```sh
~/.local/bin/wsd --demo
```

On the Linux machine, open http://127.0.0.1:5000/.
Press Ctrl+C to stop.

## Access from another computer

Connect to the Linux machine with port forwarding:

```sh
ssh -L 5500:127.0.0.1:5000 user@host
```

Start WSD in that SSH session. Keep the session open, then visit
http://127.0.0.1:5500/ on your own computer.
