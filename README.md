# This is the very first commit so nothing has working yet

# dropbox-kindle-client
Dropbox client for Amazon Kindle
Based on Seafile client https://github.com/trap000d/seafile-kindle-client
 
### Installation

- Your kindle must be jailbroken
- Install python for kindle http://www.mobileread.com/forums/showthread.php?t=225030
- Copy the contents of KUAL/dropbox directory into /mnt/us/extensions/dropbox
- Copy dropbox.cfg.example to dropbox.cfg, set folder name to sync, and your Dropbox token (see howto get token here: )
```
[server]
library = MyBooks
token = s7ergngt3y3fhdsnvjdnvnjfbfywfgywgcsdsdbsd

[kindle]
local = /mnt/us/documents/Dropbox
upload = /MyKindle_1
; screen dimensions in chars: 68x60 for PW3/KV, 48x42 for PW2
width  = 68
height = 60
```
Run it via KUAL menu:
- KUAL -> Dropbox Sync -> Synchronize
or
- KUAL -> Dropbox Sync -> Push to server

