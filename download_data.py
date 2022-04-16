import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import argparse
from urllib.parse import urlparse
import os
from pathlib import Path
import sys
import json
import unicodedata
import re
import traceback

headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; Trident/7.0; rv:11.0) like Gecko',
          }
prefered_quality = 1080


def incremented_filename(filepath):
    path,filename = os.path.split(filepath)
    filename,ext = os.path.splitext(filename)
    inc = 0
    while True:
        if inc==0:
            if not os.path.exists(filepath):
                return filepath
        elif not os.path.exists(os.path.join(path,filename+"_"+str(inc)+ext)):
            return os.path.join(path,filename+"_"+str(inc)+ext)
        inc+=1
            

def slugify(value, allow_unicode=True):  
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')




def download_video(dlink,save_path,n_chunk=64):
    
    
    r = requests.get(dlink, stream=True)
    block_size = 1024
    file_size = int(r.headers.get('Content-Length', None))
    progress_bar = tqdm(total=file_size, unit='iB', unit_scale=True)
    
    with open(save_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=n_chunk * block_size):
            f.write(chunk)
            progress_bar.update(len(chunk))
    if os.path.getsize(save_path)==file_size:
        return True
    
def get_link(vlink):
    try:
        r = requests.get(vlink,headers=headers)        
        soup = BeautifulSoup(r.content.decode('utf8'),'lxml')
        scripts = soup.findAll('script')
        for script in scripts:
            if script.string.strip().startswith('(function(document, player)'):
                video_json = json.loads(script.string.split('var config =')[-1].split('; if (!config.request)')[0])
                
                streams = (video_json['request']['files']['progressive'])
                title = video_json.get('video',{}).get('title','')
                if not title.strip():
                    title = video_json['video']['id']
                    
                qualities = []
                for stream in streams:
                    quality = int(stream['quality'].strip('p'))
                    if quality>prefered_quality:
                        continue
                    download_url = stream['url']
                    qualities.append((quality,download_url))
                sorted_qualities = sorted(qualities, key=lambda x: x[0])[-1::]
                
                download_url = sorted_qualities[0][1]
                return str(title),download_url
    except:
        with open('log','a') as log:
            log.write(str(traceback.format_exc()))
        print(f"Failed to download \"{vlink}\".")
        print("Error logged, see log file.")
        sys.exit(0)
               
def main():
    tutorial = ''
    arg_parser = argparse.ArgumentParser(description='Download vimeo videos with HD 1080p or nearest low.',
                                        epilog="For more information and usage tutorial visit " +tutorial)
    
    arg_parser.add_argument('-l','--link',metavar=' ',type=str,
                            help='Vimeo video link, can be found in the webpage iframe source attrib.',
                            required=True)
    
    arg_parser.add_argument('-r','--referer',metavar=' ',type=str,
                            help="HTTP request header to bypass privacy setting for some embedded videos.\n\
                                e.g., http://example.com for video embedded on http://example.com/somepage.")
    
    arg_parser.add_argument('-o','--output',metavar=' ',type=str,
                            help='Output save path.\n\
                            Input ex. "{output_path}" with double quotes no brackets',
                            default=os.path.join(Path.home(), "Downloads"))
                           
    arg_parser.add_argument('-p','--print',
                            action='store_true',
                            help='Print download link only.')   
    
    
    
    args = arg_parser.parse_args()
    
    video_link = args.link.strip('"\'').strip()
    if '/video/' not in urlparse(video_link).path:
        print('Not a vimeo link.')
        sys.exit(1)
        
    referer = args.referer
    if referer is not None:
        if not referer.startswith(('http://','https://')):
            headers['Referer'] = referer
            
    output_path = args.output
    if not os.path.exists(os.path.join(output_path)):
        output_path = os.path.join(Path.home(), "Downloads")
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    
    video_title , download_url = get_link(video_link)
    video_title = slugify(video_title) 
    output_path = os.path.join(output_path,video_title+".mp4")
    output_path = incremented_filename(output_path)
    if args.print:    
        print(f"Download link for video \"{video_title}\" :\n"+download_url)
        sys.exit(0)
    else:             
        if download_video(download_url, output_path):
            print(f'Downloaded Video "{video_title}" :\n{output_path}')                 

if __name__ == '__main__':
    main()