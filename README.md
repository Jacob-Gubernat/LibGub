# LibGub

This is a system designed to efficiently retrieve the md5 hash of books on Library Genesis given the book's title and author.

The entire system is self contained and makes use of a simplified version of the [Library Genesis database](https://libgen.li/dirlist.php?dir=dbdumps) in order to reduce the storage requirements and to make it easier for people to use. By only storing the columns that are relevant to performing searches and encoding the database as a compressed parquet file, I've managed to reduce the storage requirements from 22.25 GB down to only 217 MB while still retaining all entries from the original. The database is still too big to be posted on GitHub but it could be [downloaded here](https://drive.google.com/drive/folders/1yvEC2mNyGaF0XjYql9DlN6dEEKk_ke1u?usp=sharing).

When you run the build.py script, it will decompress the libgub.zstd.parquet file and then begin building a MySQL database with indexes over the Title and Author fields. Once the database is built, you will be able to use the search.py script to determine the md5's of your books at a speed of about 3.9 seconds per 100 books. The search was designed to be accurate despite its resilience to typos in both in the title of the book and in the names of the authors. If there are many books of with the same title and author in the database, the default behavior is to retrieve the most recent edition. 

Future plans for this project include broadening the search space to include other metadata databases offered by LibGen as well as automating the updating of each.

---
### Repository Structure

```
LibGub/
  read.me
  build.py
  search.py

  benchmarks/
    fallbacks.txt
    lookups.txt

  demo/
    input_books.csv
    saved_books.csv
    missing_books.csv

  database/
    libgub.zstd.parquet
```

---
### Input Schema

```
id: int64
title: string
author: string
doi: string (optional)
type: string (optional)
```
---
### Database Schema

```
ID: int64
Title: string
Author: string
Year: string
Edition: string
MD5: string
Filesize: int64
Identifier: string
```
---
### Search Example

```
Searching for title='Invisible Man'  author='Ralph Ellison'

Tier 1 → Title FT returned 10 hit(s) in 3.4 ms
    [Rejected] ID=2725: author mismatch → 'Rita S. Brause'
    [Rejected] ID=55189: author mismatch → 'Tim Dobbert'
    [Rejected] ID=57248: author mismatch → 'J.J. Luna'
    [Rejected] ID=58290: author mismatch → 'John Purcell'
    [Rejected] ID=62272: author mismatch → 'Keith Devlin'
    [Rejected] ID=62574: author mismatch → 'David S. Evans, Andrei Hagiu, Richard Schmalensee'
    [Rejected] ID=79869: author mismatch → 'George Lazarides (auth.), Lefteris Papantonopoulos (eds.)'
    [Rejected] ID=109892: author mismatch → 'Ashida Kim'
    [Rejected] ID=114509: author mismatch → 'Ulrich van Suntum'
    [Rejected] ID=116134: author mismatch → ''

Tier 2 → Author FT returned 4 hit(s) in 5.5 ms
    [Accepted] ID=639908: 'Invisible Man'  by 'Ralph Ellison'
    [Rejected] ID=2435449: title below threshold ('Homme invisible, pour qui chantes-tu?')
    [Rejected] ID=2573131: title below threshold ("'Bitter with the past but sweet with the dream: communism in the African American imaginary: representations of the Communist Party, 1940-1952")
    [Rejected] ID=3107519: title below threshold ('Homem Invisível')

→ Found acceptable candidate(s).
```

Built by Jacob Gubernat
