# Copyright (c) 2020 Sarthak Mittal
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import glob
import argparse
import pdf2image
import simplejson
from tqdm import tqdm
import PIL

from invoicenet import FIELDS, FIELD_TYPES
from invoicenet.common import util


def main():
    ap = argparse.ArgumentParser()

    ap.add_argument("--data_dir", type=str, required=True,
                    help="path to directory containing invoice document images")
    ap.add_argument("--out_dir", type=str, default='processed_data/',
                    help="path to save prepared data")
    ap.add_argument("--val_size", type=float, default=0.2,
                    help="validation split ration")

    args = ap.parse_args()

    os.makedirs(os.path.join(args.out_dir, 'train'), exist_ok=True)
    os.makedirs(os.path.join(args.out_dir, 'val'), exist_ok=True)

    filenames = [os.path.abspath(f) for f in glob.glob(args.data_dir + "**/*.pdf", recursive=True)]
    if len(filenames) < 1:
        filenames = [os.path.abspath(f) for f in glob.glob(args.data_dir + "**/*.png", recursive=True)]
        #text_json_filenames = [os.path.abspath(f) for f in glob.glob(args.data_dir + "**/*_text.json", recursive=True)]


    idx = int(len(filenames) * args.val_size)
    train_files = filenames[idx:]
    val_files = filenames[:idx]

    print("Total: {}".format(len(filenames)))
    print("Training: {}".format(len(train_files)))
    print("Validation: {}".format(len(val_files)))

    for phase, filenames in [('train', train_files), ('val', val_files)]:
        print("Preparing {} data...".format(phase))

        for filename in tqdm(filenames):
            try:
                if filename.endswith(".pdf"):
                    page = pdf2image.convert_from_path(filename)[0]
                    page.save(os.path.join(args.out_dir, phase, os.path.basename(filename)[:-3] + 'png'))
                    text_json = None
                else:
                    page = PIL.Image.open(filename)
                    text_json_file = filename.replace(".png", "_text.json")
                    text_json = simplejson.load(open(text_json_file))

                height = page.size[1]
                width = page.size[0]

                ngrams = util.create_ngrams(page, text_json=text_json)
                for ngram in ngrams:
                    if "amount" in ngram["parses"]:
                        ngram["parses"]["amount"] = util.normalize(ngram["parses"]["amount"], key="amount")
                    if "date" in ngram["parses"]:
                        ngram["parses"]["date"] = util.normalize(ngram["parses"]["date"], key="date")

                with open(filename[:-3] + 'json', 'r') as fp:
                    labels = simplejson.loads(fp.read())

                fields = {}
                for field in FIELDS:
                    if field in labels:
                        if FIELDS[field] == FIELD_TYPES["amount"]:
                            fields[field] = util.normalize(labels[field], key="amount")
                        elif FIELDS[field] == FIELD_TYPES["date"]:
                            fields[field] = util.normalize(labels[field], key="date")
                        else:
                            fields[field] = labels[field]
                    else:
                        fields[field] = ''

                data = {
                    "fields": fields,
                    "nGrams": ngrams,
                    "height": height,
                    "width": width,
                    "filename": os.path.abspath(
                        os.path.join(args.out_dir, phase, os.path.basename(filename)[:-3] + 'png'))
                }

                with open(os.path.join(args.out_dir, phase, os.path.basename(filename)[:-3] + 'json'), 'w') as fp:
                    fp.write(simplejson.dumps(data, indent=2))

            except Exception as exp:
                print("Skipping {} : {}".format(filename, exp))
                continue


if __name__ == '__main__':
    main()
