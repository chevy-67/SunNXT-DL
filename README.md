# SunNXT-DL
A simple tool to download videos from [SunNXT](https://www.sunnxt.com) platform

## version - 0.0.1
## About the tool
- This tool utilizes pywidevine to obtain widevine keys using L3 CDM
- It requires MPD, currently cookies feature not implemented
- It automatically scraps Title, year and subtitles from content id

## Usage
 - Install the necessarry packages from requirements.txt
   `pip install -r requirements.txt`
 - Run `main.py`
 - Obtain MPD from the browser and paste there
 - Enter the audio and video id from list of availabe
 - It starts download the content, decrypts and muxes it, thats all :)

## Note
  - Currently Sunnxt uses L3 CDM upto FHD, new L3 CDM needed if existing gets revoked
  - Dump your own L3 CDM if existing revoked, [Take your coffee](https://github.com/hyugogirubato/KeyDive)

## Contribution
  Contributions are hearty welcomed. A simple PR makes it robust

# Thanks
  This project was made successful by referencing various private scripts and replicating some of the existing modules and implementations

  # DISCLAIMER
   This project serves strictly as an educational proof-of-concept regarding bypass and decryption methodology. Unauthorized downloading or distribution of SunNXT proprietary media is unlawful. I accepts no liability for misuse, copyright infringement or damages resulting from the tool.
