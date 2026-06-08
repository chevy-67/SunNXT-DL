import subprocess
import requests,subprocess,os,base64,re,urllib.request
from pywidevine.decrypt.wvdecrypt import WvDecrypt

video_enc = './output/temp/vid_enc.mp4'
audio_enc = './output/temp/aud_enc.m4a'
audio_dec = './output/temp/aud_dec.m4a'
video_dec = './output/temp/vid_dec.mp4'
subtitle = './output/temp/{}.srt'
cookies_file = "./cookies/cookies.txt"
mp4decrypt = "./binaries/mp4decrypt"
yt_dlp = './binaries/yt-dlp_linux'
ffmpeg = './binaries/ffmpeg'
keys_cache = './KEYS.txt'

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
INFO_URL = "https://pwaapi.sunnxt.com/content/v3/contentDetail/{}/?fields=generalInfo,subtitles"
headers = {'User-Agent': 'Mozilla/5.0'}
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

MPD = str(input('Enter MPD : ')).strip()

try:
    width = os.get_terminal_size().columns
except OSError:
    width = 80

BLUE = "\033[34m"
BOLD = "\033[1m"
RESET = "\033[0m"

divider = f"{BOLD}{BLUE}{'═' * width}{RESET}"

def mpd_to_id(mpd):
    return mpd.split('?')[0].split('/')[-1].split('_')[0]

CONTENT_ID = mpd_to_id(MPD)

def get_metadata():
    resp = requests.get(INFO_URL.format(CONTENT_ID),headers=headers)
    title = resp.json()['results'][0]['generalInfo']['title']
    year = resp.json()['results'][0]['generalInfo']['displayTitle'][-4:]
    return title,year

title,year = get_metadata()
print(divider)
print(f"\nRipping : {title} ({year})\n")
print(divider)  
subprocess.run([yt_dlp,'--allow-unplayable-formats','-F','-q','--no-warnings',MPD], check=True, text=True)
print(divider)

video_format = str(input('\nEnter video format : '))
audio_format = str(input('Enter audio format : '))

if not os.path.exists(audio_enc) and not os.path.exists(audio_dec):
    print(f'\n{BOLD}{BLUE}Downloading Audio...{RESET}\n')
    subprocess.run([yt_dlp,'--allow-unplayable-formats','-f', audio_format, '--fixup', 'never', MPD, '-o', audio_enc])
else:
    print("\nAudio Already Downloaded")

if not os.path.exists(video_enc) and not os.path.exists(video_dec):
    print(f'\n{BOLD}{BLUE}Downloading Video...{RESET}\n')
    subprocess.run([yt_dlp,'--allow-unplayable-formats','-f', video_format, '--fixup', 'never', MPD, '-o', video_enc])
else:
    print("\nVideo Already Downloaded")

def get_subtitle():
    resp = requests.get(INFO_URL.format(CONTENT_ID),headers=headers)
    try:
        subtitles = resp.json()['results'][0]['subtitles']['values']
        subs = {}
        for sub in subtitles:
            subs[sub['language']] = sub['link_sub']+'.srt'
        return subs
    except:
        return None

subs = get_subtitle()
subtitles = []

if subs:
    print("\nDownloading subtitle...")
    for lang,link in subs.items():
        PATH = subtitle.format(lang)
        subprocess.run([yt_dlp,'--allow-unplayable-formats','-k', link, '--fixup', 'never', '-o', PATH])
        subtitles.append(PATH)
else:
    print("\nNo subtitle found!")
                 
def extract_drm_from_mpd(url):
    try:
        req = urllib.request.Request(url, headers=headers)
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

licurl = f'https://pwaapi.sunnxt.com/licenseproxy/v3/modularLicense/?content_id={CONTENT_ID}'

def do_decrypt(pssh, licurl):
    wvdecrypt = WvDecrypt(pssh)
    chal = wvdecrypt.get_challenge()
    resp = requests.post(url=licurl, data=chal, headers=lic_header)
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
print("\nChecking Cache...")

def save_keys(KEYS):
    with open(keys_cache,'a') as file:
        file.write(title+'\n') 
        file.write(KEYS+'\n')
        file.write('\n')

KEYS = None

if os.path.exists(keys_cache):
    with open(keys_cache,'r') as file:
        for line in file:
            if kid in line:
                print("Key found in cache")
                KEYS = line
                break
if not KEYS:
    KEYS = do_decrypt(licurl=licurl, pssh=pssh)
    KEYS = keysOnly(KEYS)
    save_keys(KEYS)

print(f"\nKEY : {KEYS}")

print("\nDecrypting video...")
subprocess.run([mp4decrypt,'--show-progress','--key',KEYS,video_enc,video_dec],capture_output=True,text=True)
print("\nDecrypting audio...")
subprocess.run([mp4decrypt,'--show-progress','--key',KEYS,audio_enc,audio_dec],capture_output=True,text=True)

print('\nMerging video and audio...')
cmd = [ffmpeg,'-hide_banner','-y','-i',video_dec,'-i',audio_dec]

if subs:
    for subtitle in subtitles:
        cmd.extend(['-i',subtitle])
cmd.extend(['-map', '0:v', '-map', '1:a'])
cmd.extend(['-c:v', 'copy', '-c:a', 'copy', '-c:s', 'srt'])

if subs:
    input_index = 2
    track_index = 0
    for subtitle in subtitles:
        lang = os.path.splitext(os.path.basename(subtitle))[0]
        cmd.extend(['-map', str(input_index)])
        cmd.extend([
            f'-metadata:s:s:{track_index}', f'language={lang}',
            f'-metadata:s:s:{track_index}', f'title=R4'#f'{lang.upper()}'
        ])
        
        input_index += 1
        track_index += 1

cmd.append(f'./output/{title} ({year}).mkv')

print("Running command:", cmd)

subprocess.run(cmd, check=True)

print("\nClearing temp files")
os.remove(video_dec)
os.remove(audio_dec)
os.remove(video_enc)
os.remove(audio_enc)
for i in subtitles:
    os.remove(i)

print("\nAll done!")
