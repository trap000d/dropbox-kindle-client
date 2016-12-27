#! /mnt/us/python/bin/python2.7
# -*- coding:utf-8 -*-

import threading
import time

import requests
import requests.packages.urllib3
from requests.packages.urllib3.packages import six
import email.utils
import mimetypes
import json

import ConfigParser
import os
import sys
import shutil
import socket
from subprocess import call, Popen, PIPE
from re import findall

def spinning_cursor():
    while True:
        for cursor in '+*':
            yield cursor

def spinner():
    s = spinning_cursor()
    while True:
        call(['eips', '1 ', str(1+max_y-3),  s.next() ])
        time.sleep(1)

def utf8_format_header_param(name, value):
    """
    Helper function to format and quote a single header parameter.

    Particularly useful for header parameters which might contain
    non-ASCII values, like file names. This follows RFC 2231, as
    suggested by RFC 2388 Section 4.4.
    Modified to encode utf-8 by default Standard function
    from `requests` should be monkeypatched as:
    `requests.packages.urllib3.fields.format_header_param = utf8_format_header_param`

    :param name:
        The name of the parameter, a string expected to be ASCII only.
    :param value:
        The value of the parameter, provided as a unicode string.
    """
    if not any(ch in value for ch in '"\\\r\n'):
        result = '%s="%s"' % (name, value)
        try:
            result.encode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
        else:
            return result
    if not six.PY3 and isinstance(value, six.text_type):  # Python 2:
        value = value.encode('utf-8')
    value = email.utils.encode_rfc2231(value, 'utf-8')
    value = '%s*=%s' % (name, value)
    return value

def safe_str(obj):
    """ return the byte string representation of obj """
    try:
        return str(obj)
    except UnicodeEncodeError:
        # obj is unicode
        return unicode(obj).encode('unicode_escape')

def safe_unicode(str):
    try:
        return str.decode('utf-8')
    except UnicodeEncodeError:
        return str

def cprint(s, ypos):
    call(['eips', '3 ', str(ypos+max_y-3), safe_str(s)[:max_x-4] ] )
    return;

def cclear(xpos, ypos, len):
    call(['eips', str(xpos), str(ypos+max_y-3), ' ' * len])
    return;

def cout(xpos, ypos, c):
    call(['eips', str(xpos), str(ypos+max_y-3), ' '])
    call(['eips', str(xpos+1), str(ypos+max_y-3),  c ])
    return;

def db_authping():
    data = {
        'path': '/'+lib
    }
    try:
        r = requests.post(url+'/files/get_metadata', headers=hdr, data=json.dumps(data), timeout=30)
        r.raise_for_status()

    except requests.exceptions.Timeout:
        return 'Timeout'

    except ( requests.exceptions.HTTPError, requests.exceptions.RequestException ) as e:
        print e
        try:
            jResp = r.json()
        except ValueError:
            return str(e)
        else:
            if 'error_summary' not in jResp:
                jResp['error_summary'] == 'Unknown error'
            return 'Connection Error:' + jResp['error_summary']

    if r.status_code == 200:
        jResp = r.json()
        if 'error_summary' not in jResp:
            cprint('Connected to Dropbox',1)
            return ''
        return jResp['error_summary'];
    return 'Unknown error';

def db_ls_lib(dir_entry='/'):

    data = {
        'path' : '/' + lib + dir_entry
    }
    r = requests.post( url + '/files/list_folder', headers = hdr, data=json.dumps(data))
    return r.json();

def db_get_modified(dir_entry='/'):
    """ Returns 4 lists a,b,c,d : a - directories to erase, b - filenames to erase, c - files to download d - hashes to update """
    h_lcl={}
    h_srv={}
    h1=[]
    h2=[]
    d=os.path.normpath(dir_local + dir_entry)
    try:
        os.makedirs(d)
    except OSError:
        if not os.path.isdir(d):
            raise

    with open(d + '/.hash','a+') as f:
        for row in f:
            hash = row.split(' ', 1 )
            name = hash[1].rstrip()
            h_lcl[hash[0]]=name
            h1.append(hash[0])
    f.close()
    subdirs_local = [safe_unicode(name) for name in os.listdir(d) if os.path.isdir(os.path.join(d, name)) and not name.endswith('.sdr')]

    jl=db_ls_lib(dir_entry)
    subdirs_srv=[]
    for i in jl['entries']:
        if i['.tag'] == 'file':
            h_srv[i['rev']]=i['name']
            h2.append(str(i['rev']))
        elif i['.tag'] == 'folder':
            p=dir_entry+i['name']
            subdirs_srv.append(i['name'])
            dr,rm,dl,up=db_get_modified(p+'/')
            db_dr(p,dr)
            db_rm(p,rm)
            db_dl(p,dl)
            db_up(p,up)

    f_lcl = set(h1)
    f_srv = set(h2)

    d_lcl = set(subdirs_local)
    d_srv = set(subdirs_srv)

    dir_to_erase= d_lcl - d_srv
    d_rm = list(dir_to_erase)

    to_erase    = f_lcl - f_srv
    to_download = f_srv - f_lcl

    f_rm=[]
    f_dl=[]
    for i in list(to_erase):
        if i in h_lcl.keys():
            f_rm.append(h_lcl[i])

    for i in list(to_download):
        if i in h_srv.keys():
            f_dl.append(h_srv[i])

    return d_rm, f_rm , f_dl, h_srv;


def db_get_ul(dir_entry='/'):
    """ 
    :param dir_entry:
        Relative path to directory 
    :return: 
        two lists: first of files to upload, second - files to remove on the server
    """
    fl=[]
    d=os.path.normpath(dir_local + dir_entry)

    try:
        os.makedirs(d)
    except OSError:
        if not os.path.isdir(d):
            raise

    with open(d + '/.hash','a+') as f:
        for row in f:
            hash = row.split(' ', 1 )
            name = hash[1].rstrip()
            fl.append(safe_unicode(name))
    f.close()
    files_real = [safe_unicode(name) for name in os.listdir(d) if os.path.isfile(os.path.join(d, name)) and not name.startswith('.')]

    jl=db_ls_lib(dir_entry)
    for i in jl['entries']:
        if i['.tag'] == 'folder':
            p=dir_entry+i['name']
            ul,rms=db_get_ul(p+'/')
            db_ul(p+'/',ul)
            db_rm_srv(p+'/', rms)

    f_hash = set(fl)
    f_real = set(files_real)
    to_upload   = f_real - f_hash
    to_remove_srv = f_hash - f_real
    f_ul = list(to_upload)
    f_rm_srv = list(to_remove_srv)
    return f_ul, f_rm_srv;

def db_dl(dir_entry, dl_list):
    """ 
    :param dir_entry:
        Relative path to directory
    :param dl_list:
        list of files to download
    """
    if not dl_list:
        return
    cclear (2,1,max_x-3)
    for idx,fname in enumerate(dl_list):
        cprint ('Downloading file '+ str(idx + 1) +' of ' + str(len(dl_list)) ,1)
        hdr_dl = {
            'Authorization'  : 'Bearer ' + token ,
            'Dropbox-API-Arg': safe_str('{"path":' + '"/' + lib + dir_entry + '/' + fname + '"}')
        }
        r = requests.post('https://content.dropboxapi.com/2/files/download', headers=hdr_dl)
        d = dir_local + dir_entry
        try:
            os.makedirs(d)
        except OSError:
            if not os.path.isdir(d):
                raise
        with open( d + '/' + fname, 'wb' ) as f:
            f.write(r.content)
    return;

def db_rm(dir_entry, rm_list):
    if not rm_list:
        return
    cclear (2,1,max_x-3)
    for idx,fname in enumerate(rm_list):
        cprint ('Removing '+ str(idx) +' file of ' + str(len(rm_list)), 1)
        f = safe_unicode(fname.rstrip())
        try:
            os.remove(dir_local + dir_entry + '/' + f)
        except OSError:
            pass
    return;

def db_dr(dir_entry, dir_list):
    """ remove directories from list """
    if not dir_list:
        return
    cclear (2,1,max_x-3)
    for idx,dirname in enumerate(dir_list):
        cprint('Removing directory '+ str(idx)+ ' of ' + str(len(dir_list)), 1)
        try:
            shutil.rmtree(os.path.normpath(dir_local + dir_entry + '/' + dirname)) 
        except OSError:
            pass
    return;

def db_up(dir_entry, up_list):
    """ Update hash table """
    if not up_list:
        return
    cclear (2,1,max_x-3)
    cprint ('Updating hashes...', 1)
    with open(dir_local + dir_entry + '/.hash','w') as h:
        for i in up_list:
            s=i + ' ' +  up_list[i] + '\n'
            h.write(s.encode("UTF-8"))
    return;

def db_ul(dir_entry, ul_list):
    """ Upload file """
    if not ul_list:
        return
    cclear (2,1,max_x-3)
    for idx,lfile in enumerate(ul_list):
        cprint('Uploading '+ str(idx) +' new file of ' + str(len(ul_list)),1)
        hdr_ul = {
            'Authorization'  : 'Bearer ' + token ,
            'Content-type'   : 'application/octet-stream',
            'Dropbox-API-Arg': safe_str('{"path":' + '"/' + lib + dir_entry + lfile + '"}')
        }
        response = requests.post(
            'https://content.dropboxapi.com/2/files/upload',
            headers=hdr_ul,
            data=open( dir_local + dir_entry + lfile).read(),
        )
        if response.status_code == 200:
            cprint('Updating hashes...', 1)
            with open(os.path.normpath(dir_local + dir_entry) + '/.hash','a') as h:
                rj = response.json()
                s=rj['rev'] + ' ' + lfile + '\n'
                h.write(s.encode('utf-8'))
    return;

def db_rm_srv(dir_entry, rm_list):
    """Remove file(s) from rm_list at the server side
    """
    if not rm_list:
        return
    cclear (2,1,max_x-3)
    for idx,f in enumerate(rm_list):
        cprint('Removing file '+ str(idx)+' of ' + str(len(rm_list))+ ' on server...', 1)
        data = {
            'path': '/' + lib + dir_entry + f
        }
        r = requests.post(url+'/files/delete', headers=hdr, data=json.dumps(data))
        if r.status_code == 200:
            with open(os.path.normpath(dir_local + dir_entry) + '/.hash','r+') as h:
                data = h.readlines()
                h.seek(0)
                h.truncate()
                for line in data:
                    if not f in safe_unicode(line):
                        h.write(line)
    return;

def db_get_push():
    d=os.path.normpath(dir_local + dir_push)
    upfiles=[]
    for r, s, files in os.walk(d):
        s[:] = [x for x in s if not x.endswith('.sdr')]
        for f in files:
            if not f.startswith('.'):
                upfiles.append( os.path.join(r, f) )
    return upfiles;

def db_push():
    """ Push directory to the server """
    files=db_get_push()
    if not files:
        return
    hashlist=''
    cclear (2,1,max_x-3)
    for idx,f in enumerate(files):
        fn = os.path.basename(f)
        fb = safe_unicode(fn)
        cprint('Updating file '+ str(idx)+ ' of '+ str(len(files)), 1)
        dir_entry = os.path.relpath(os.path.dirname(f), dir_local)

        hdr_ul = {
            'Authorization'  : 'Bearer ' + token ,
            'Content-type'   : 'application/octet-stream',
            'Dropbox-API-Arg': safe_str('{"path":' + '"/' + lib + '/' + dir_entry + '/' + fb + '"}')
        }
        response = requests.post(
            'https://content.dropboxapi.com/2/files/upload',
            headers=hdr_ul,
            data=open( dir_local + '/' + dir_entry + '/' + fn).read(),
        )
        if response.status_code == 200:
            rj = response.json()
            hashlist = hashlist + rj['rev'] + ' ' + fb + '\n'
    with open(os.path.normpath(dir_local + dir_push) + '/.hash','w') as h:
        h.write(hashlist.encode('utf-8'))
    return;

def screen_size():
    cmd = Popen('eips 99 99 " "', shell=True, stdout=PIPE)
    #eips: pixel_in_range> (1600, 2400) pixel not in range (0..1072, 0..1448)
    for line in cmd.stdout:
        l = findall(r'\d+', line)
        x = 1 + int(l[3])/( int(l[0])/100 )
        y = int(l[5])/( int(l[1])/100 )
    return x,y;

def is_connected(url='dropbox.com'):
    try:
        host = socket.gethostbyname(url)
        s = socket.create_connection((host, 80), 2)
        return True
    except:
        time.sleep(1)
        pass
    return False

def db_ping():
    for i in xrange(1, 20):
        cprint('Testing connection' + '.'*i, 1)
        if is_connected():
            return 0;
    return 1;

def wifi(enable=1):
    """ returns 0, 1 or error codes """
    status = 0
    cmd = Popen('lipc-set-prop com.lab126.cmd wirelessEnable ' + str(enable), shell=True)
    if enable == 1:
        for i in xrange(1, 20):
            """ 20 seconds timeout for starting wireless
            """
            status = wifi_status()
            cprint ('Activating wireless' + '.'*i, 1 )
            if status == 1:
                return status;
            time.sleep(1)
    return status;

def wifi_status():
    cmd = Popen('lipc-get-prop com.lab126.cmd wirelessEnable', shell=True, stdout=PIPE)
    for line in cmd.stdout:
        l = int(line)
        if l in (0, 1):
            return l;
    return 4;
    
### --- Main start

if __name__ == '__main__':

    ### Some hardcoded path
    cfg_dir='/mnt/us/extensions/dropbox'

    config = ConfigParser.RawConfigParser()
    cfg_file = cfg_dir + '/dropbox.cfg'
    config.read( cfg_file )

    url       = 'https://api.dropboxapi.com/2'
    lib       = config.get('server', 'library')
    token     = config.get('server', 'token')

    dir_local = config.get('kindle', 'local')
    dir_push  = config.get('kindle', 'upload')

    max_x,max_y = screen_size()

    cclear (0,2,max_x-1)
    cclear (0,1,max_x-1)

    t = threading.Thread(target=spinner)
    t.setDaemon(True)
    t.start()

    wifi_old = wifi_status()
    if wifi_old == 0:
        w = wifi(1)
        if w != 1:
            cprint('Can not activate wireless connection',1)
            quit()

    rc = db_ping()
    if rc:
        cprint('Connection timeout', 1)
        quit()
    
    hdr = { 'Authorization' : 'Bearer ' + token , 'Content-Type': 'application/json'}
    rc = db_authping()
    if rc:
        print('Error:'+ rc)
        cprint(rc, 1)
        quit()

    # Here we're monkeypatching system library
    requests.packages.urllib3.fields.format_header_param = utf8_format_header_param

    if len(sys.argv)>1:
        if sys.argv[1]=='push':
            push = True
            db_push()
            cclear (0,2,max_x-1)
            cclear (0,1,max_x-1)
            if wifi_old == 0:
                wifi(0)
            cprint ('Done', 1)
            quit()

    ul, rms = db_get_ul()
    db_ul('/',ul)
    db_rm_srv('/', rms)

    dr,rm,dl,up = db_get_modified()
    db_dr('/',dr)
    db_rm('/',rm)
    db_dl('',dl)
    db_up('/',up)

    cclear (0,2,max_x-1)
    cclear (0,1,max_x-1)
    if wifi_old == 0:
        wifi(0)
    cprint ('Done', 1)
