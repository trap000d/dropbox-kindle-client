# dropbox-kindle-client
Dropbox client for Amazon Kindle
Based on Seafile client https://github.com/trap000d/seafile-kindle-client
 
### Installation

- Your kindle must be jailbroken
- Install python for kindle http://www.mobileread.com/forums/showthread.php?t=225030
- Copy/unpack the contents of KUAL/dropbox directory to /mnt/us/extensions/dropbox
- Copy dropbox.cfg.example to dropbox.cfg, set Dropbox folder to sync, as well as your Dropbox token (see howto generate token here: https://www.dropbox.com/developers/reference/oauth-guide#setting-up-your-app)

```
[server]
; Dropbox folder to synchronize
library = MyBooks
; Dropbox API Token
token = s7ergngt3y3fhdsnvjdnvnjfbfywfgywgcsdsdbsd

[kindle]
; Local Kindle directory to synchronize
local = /mnt/us/documents/Dropbox
; contents of /mnt/us/documents/Dropbox/MyKindle_1 ("local"+"upload") will be forced to upload
upload = /MyKindle_1
```

### Run 

Via KUAL menu:
- KUAL -> Dropbox Sync -> Synchronize
or
- KUAL -> Dropbox Sync -> Push to server
In this case all the contents of directory 'local+upload' will be forced to upload into Dropbox (useful e.g. for notes synchronization).

Via command line:

```
/mnt/us/extensions/dropbox/bin/dbcli.py
``` 
for sync 

```
/mnt/us/extensions/dropbox/bin/dbcli.py push 
```

for upload

### Known Issues/Bugs/Limitations

- One'n'half-way synchronization (only newly created local files are uploaded to server). As ID of file is generated on the server, there is no reliable way to determine if file is changed locally by it's ID. File timestamp doesn't look good too as kindle clock might reset after cold restart.

| Event | Supported |
| ---   | ---       |
| File created on Kindle | Y |
| File removed on Kindle | Y |
| File changed on Kindle | N |
| File created on server | Y |
| File removed on server | Y |
| File changed on server | Y |

- There is an option for uploading of the particular directory contents (useful e.g. for notes synchronization). As all files in that directory have to be uploaded to the server you should be careful: it could take much time.
- Directory for uploads must exist on the server. You have to create it there (e.g. via web interface or with official Dropbox client) and perform synchronization (download) at least once before upload.
- Upload directory must be a sub-folder in directory tree, e.g. /mnt/us/documents/Dropbox/MyKindle_1. In config it should be defined as relative path to the base directory
- Just rudimentary checks of internet/WiFi availability/file operations
- Hidden files/folders are not synchronized as well as bookmarks/statistics (*.sdr). It's because client has keeping actual state in hidden files ".hash", also some FUSE FS garbage often present as .fuse_hiddenXXXXXX.
