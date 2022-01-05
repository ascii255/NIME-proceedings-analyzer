# NIME Proceedings Analyzer (NIME PA)
# Copyright (C) 2022 Jackson Goode, Stefano Fasciani

# The NIME PA is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# The NIME PA is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# If you use the NIME Proceedings Analyzer or any part of it in any program or
# publication, please acknowledge its authors by adding a reference to:

# J. Goode, S. Fasciani, A Toolkit for the Analysis of the NIME Proceedings
# Archive, submitted to 2022 International Conference on New Interfaces for
# Musical Expression, Auckland, New Zealand, 2022.

# Native
import sys
if sys.version_info < (3, 7):
    print("Please upgrade Python to version 3.7.0 or higher")
    sys.exit()
import io
import os
from os import path
import random
import argparse
import requests

# External
from tqdm import tqdm
import orjson

# Helper
import pa_print
from pa_utils import csv_save, calculate_carbon, fill_empty, doc_quality, post_processing, boolify
from pa_request import request_location, request_scholar, request_uni
from pa_extract import extract_text, extract_author_info, extract_grobid
from pa_load import prep, load_unidomains, load_bibtex, extract_bibtex, check_grobid


# Variables/paths
bibtex_path = os.getcwd()+'/cache/bibtex/nime_papers.bib'
unidomains_path = os.getcwd()+'/cache/json/unidomains.json'

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Analyse a publication given a BibTeX and directory of pdf documents')
    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        help='prints out operations')
    parser.add_argument('-c', '--citations', action='store_true', default=False,
                        help='bypass cache to retrieve new citations')
    parser.add_argument('-g', '--grobid', action='store_true', default=False,
                        help='forces repopulation of Grobid files')
    parser.add_argument('-r', '--redo', action='store_true', default=False,
                        help='deletes cache')
    parser.add_argument('-n', '--nime', action='store_true', default=False,
                        help='uses NIME based corrections')

    args = parser.parse_args()

    # * Prepare cache, etc.
    prep(args)

    # * Set global print command
    pa_print.init(args)

    # Print notice
    pa_print.lprint()

    # * Load database for email handle to uni matching
    unidomains = load_unidomains(unidomains_path)

    # * Load and extract BibTeX
    bib_db = load_bibtex(bibtex_path)
    bib_db = extract_bibtex(bib_db, args)

    # * Loop here for Grobid/PDF population
    if args.grobid:
        check_grobid(bib_db, True)

    # * Parse data through pdfs
    print('\nExtracting and parsing publication data...')
    iterator = tqdm(bib_db)
    for _, pub in enumerate(iterator):
        pa_print.tprint(f"\n--- Now on: {pub['title']} ---")

        # Extract text from pdf, regardless
        doc = extract_text(pub)
        errored = doc_quality(doc, pub, 'text') # check for errors

        # Only extract header meta-data if not errored
        if not errored:
            author_info = extract_author_info(doc, pub)
        else:
            author_info = []

        # Extract doc from Grobid
        doc = extract_grobid(pub, bib_db, iterator)
        doc_quality(doc, pub, 'grobid')

        # Get university from various sources
        request_uni(unidomains, author_info, args, pub)

        # Get location from API and query
        request_location(author_info, args, pub)

        # Use location for footprint calculation
        calculate_carbon(pub)

        # Get citations from Semantic Scholar
        request_scholar(pub, args)

        # Post processing modifications
        post_processing(pub)

        # Save for every paper
        csv_save(bib_db)
