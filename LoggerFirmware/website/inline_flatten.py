#! @file inline_flatten.py
# @brief Inline all of the CSS and JS requested by each HTML file in the current directory
#
# Due to the nature of the webserver in the firmware, if you attempt to request multiple files
# in quick succession, the server can't respond quickly enough, and the requests fail.  This code
# inlines the CSS and JS components required for each HTML file, therefore, so that you're really
# only going for a single file on each page (except for the logo).  This can make the resulting
# website a little larger than required (since you have copies of the various files in each HTML
# document), but does resolve the issue.
#
# Copyright (c) 2024, University of New Hampshire, Center for Coastal and Ocean Mapping.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software
# and associated documentation files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the Software is furnished
# to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
# OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF
# OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


from bs4 import BeautifulSoup
import re
from typing import List
import os
import shutil

def convert_file(input: str, output: str) -> None:
    inbase = os.path.split(input)[0]
    if inbase == '':
        inbase = '.'
    with open(input) as f:
        soup = BeautifulSoup(f, 'html.parser')
        links = soup.find_all('link')
        for link in links:
            ref = os.sep.join((inbase, link['href']))
            tag = soup.new_tag('style')
            with open(ref) as r:
                contents = r.read()
                contents = " ".join(contents.split())
                tag.string = contents
            link.replace_with(tag)
        scripts = soup.find_all('script')
        for script in scripts:
            try:
                src = os.sep.join((inbase, script['src']))
                print(f'Info: looking for source {src} for JavaScript.')
                compiled_src = src.replace('.js', '_compiled.js')
                if os.path.isfile(compiled_src):
                    src = compiled_src
                    print(f'Info: using compiled source {compiled_src} for JavaScript.')
                tag = soup.new_tag('script')
                with open(src) as s:
                    contents = s.read()
                    contents = re.sub(' +', ' ', contents)
                    contents = re.sub('\n+', '\n', contents)
                    tag.string = contents
                script.replace_with(tag)
            except KeyError:
                pass
    # We need to generate the output directory tree if it doesn't exist
    outbase = os.path.split(output)[0]
    os.makedirs(outbase, exist_ok=True)
    with open(output, 'w') as f:
        f.write(str(soup))

def traverse_directory(dirname: str) -> List[str]:
    targets = []
    for root, dirs, files in os.walk(dirname):
        path = root.split(os.sep)
        relative = os.sep.join(path[1:])
        for file in files:
            if file.endswith('.htm'):
                targets.append(os.path.join(relative, file))
    return targets

def convert_directory(indir: str, outdir: str) -> None:
    targets = traverse_directory(indir)
    for target in targets:
        outname = os.path.join(outdir, target)
        print(f'Converting {target} to {outname} ...')
        convert_file(target, outname)

if __name__ == "__main__":
    
    data_folder = "../data/website"
    
    # Flatten
    convert_directory(".", data_folder)

    # Copy images to the data folder
    src_images = "images"
    dest_images = os.path.join(data_folder, src_images)
    if os.path.exists(dest_images):
        shutil.rmtree(dest_images)
    shutil.copytree(src_images, dest_images)
