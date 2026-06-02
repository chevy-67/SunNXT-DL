import subprocess
from idna import idnadata
import requests,subprocess,os,json,binascii,base64,re,urllib.request
from os import terminal_size
from pywidevine.decrypt.wvdecrypt import WvDecrypt

video_enc = './temp/vid_enc.mp4'
audio_enc = './temp/aud_enc.m4a'
audio_dec = './temp/aud_dec.m4a'
video_dec = './temp/vid_dec.mp4'
cookies_file = "./cookies/cookies.txt"
mp4decrypt = "./binaries/mp4decrypt"
mp4dump = "./binaries/mp4dump"
yt_dlp = './binaries/yt-dlp_linux'
mkvmerge = './binaries/mkvmerge'
ffmpeg = './binaries/ffmpeg'

def parseCookieFile(cookiefile):
    cookies = {}
    with open (cookies_file, 'r') as fp:
        for line in fp:
            if not re.match(r'^\#', line):
                lineFields = line.strip().split('\t')
                if len(lineFields) < 7:
                    continue
                cookies[lineFields[5]] = lineFields[6]
    return cookies
    
cookies = parseCookieFile(cookies_file)

MPD = str(input('Enter MPD : ')).strip()

try:
    width = os.get_terminal_size().columns
except OSError:
    width = 80

BLUE = "\033[34m"
BOLD = "\033[1m"
RESET = "\033[0m"

divider = f"{BOLD}{BLUE}{'═' * width}{RESET}"

print(divider)  
subprocess.run([yt_dlp,'--allow-unplayable-formats','-F','-q','--no-warnings',MPD], check=True, text=True)
print(divider)

video_format = str(input('\nEnter video format : '))
audio_format = str(input('Enter audio format : '))

if not os.path.exists(audio_enc) and not os.path.exists(audio_dec):
    print(f'\n{BOLD}{BLUE}Downloading Audio...{RESET}\n')
    subprocess.run([yt_dlp,'--allow-unplayable-formats','-f', audio_format, '--fixup', 'never', MPD, '-o', audio_enc])
else:
    pass

if not os.path.exists(video_enc) and not os.path.exists(video_dec):
    print(f'\n{BOLD}{BLUE}Downloading Video...{RESET}\n')
    subprocess.run([yt_dlp,'--allow-unplayable-formats','-f', video_format, '--fixup', 'never', MPD, '-o', video_enc])
else:
    pass

                    
def extract_drm_from_mpd(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            mpd_data = response.read().decode('utf-8')
    except Exception as e:
        print(f"Failed to download MPD: {e}")
        return None
    
    pssh_list = re.findall(r"<(?:\w+:)?pssh>\s*([^<]+?)\s*</(?:\w+:)?pssh>",mpd_data,re.IGNORECASE)
    kid_matches = re.findall(r'default_KID="([^"]+)"', mpd_data, re.IGNORECASE)
    
    pssh_out = None
    kid_out = None
    if pssh_list:
        raw_pssh = pssh_list[0].strip()
        #print("raw pssh : ",raw_pssh)
        data = base64.b64decode(raw_pssh)
        payload = data[-16:]
        if(raw_pssh.endswith("==")):
            pssh_out = base64.b64encode(data).decode()
        else:
            pssh_out = base64.b64encode(payload).decode()
    if kid_matches:
        kid_out = kid_matches[0].replace('-', '').lower()

    return pssh_out, kid_out
pssh, kid = extract_drm_from_mpd(MPD)
print(f"KID    :  {kid}")
print(f"PSSH   : {pssh}")

lic_header = {
       "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Content-Length": "1719",
    "Host": "pwaapi.sunnxt.com",
    "Origin": "https://www.sunnxt.com",
    "Referer": "https://www.sunnxt.com/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "sec-ch-ua": "\"Chromium\";v=\"148\", \"Google Chrome\";v=\"148\", \"Not/A)Brand\";v=\"99\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "Linux"
}

licurl = 'https://pwaapi.sunnxt.com/licenseproxy/v3/modularLicense/?content_id=250710'

def do_decrypt(pssh, licurl):
    wvdecrypt = WvDecrypt(pssh)
    chal = wvdecrypt.get_challenge()
    resp = requests.post(url=licurl, data=chal, headers=lic_header, cookies=cookies)
    license_decoded = resp.content
    license_b64 = base64.b64encode(license_decoded)
    wvdecrypt.update_license(license_b64)
    keys = wvdecrypt.start_process()
    return keys

def keysOnly(keys):
    for key in keys:
        if key.type == 'CONTENT':
            key = ('{}:{}'.format(key.kid.hex(), key.key.hex()))

    return key

print('\nGetting Keys...')
KEYS = do_decrypt(licurl=licurl, pssh=pssh)

print(keysOnly(KEYS))

def proper(keys):
    commandline = [mp4decrypt]
    for key in keys:
        if key.type == 'CONTENT':
            commandline.append('--key')
            commandline.append('{}:{}'.format(key.kid.hex(), key.key.hex()))

    return commandline

def decrypt(keys_, inputt, output):
    Commmand = proper(keys_)
    Commmand.append(inputt)
    Commmand.append(output)

    wvdecrypt_process = subprocess.Popen(Commmand)
    stdoutdata, stderrdata = wvdecrypt_process.communicate()
    wvdecrypt_process.wait()

    return

def keysOnly(keys):
    for key in keys:
        if key.type == 'CONTENT':
            key = ('{}:{}'.format(key.kid.hex(), key.key.hex()))

    return key


print("\nDecrypting video...")
subprocess.run([mp4decrypt,'--show-progress','--key',keysOnly(KEYS),video_enc,video_dec],capture_output=True,text=True)
print("\nDecrypting audio...")
subprocess.run([mp4decrypt,'--show-progress','--key',keysOnly(KEYS),audio_enc,audio_dec],capture_output=True,text=True)

print('\nMerging video and audio...')
subprocess.run([ffmpeg,'--hide-banner','-y','-i',video_dec,'-i',audio_dec,'-c:v','copy','-c:a','copy','-map','0:v:0?','-map','1:a:0?','final.mkv'])

print("\nClearing temp files")
os.remove(video_dec)
os.remove(audio_dec)
os.remove(video_enc)
os.remove(audio_enc)

print("\nAll done!")