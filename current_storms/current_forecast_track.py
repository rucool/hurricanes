#! /usr/bin/env python3

"""
Author: aristizabal
Last modified: Lori Garzio on 4/15/2021
Returns a dictionary of all forecast storm tracks, cones, and best tracks for the current day
"""
import os
import shutil
import numpy as np
import datetime as dt
import glob
import requests
import urllib.request
from bs4 import BeautifulSoup
from zipfile import ZipFile


def cleanup_dir():
    # move any files that are in the current working directory to ./archive
    for kmzf in glob.glob('*.kmz'):
        shutil.move(kmzf, './archive')

    # delete any other remaining files/folders
    os.system('rm -rf *best_track*')
    os.system('rm -rf *TRACK*')
    os.system('rm -rf *CONE*')


def download_current_kmz(tini):
    cleanup_dir()

    url_nhc = 'https://www.nhc.noaa.gov/gis/'
    r = requests.get(url_nhc)
    data = r.text

    soup = BeautifulSoup(data, 'html.parser')

    for i, s in enumerate(soup.find_all('a')):
        ff = s.get('href')
        if type(ff) == str:
            if np.logical_and('kmz' in ff, str(tini.year) in ff):
                print(i)
                if 'CONE_latest' in ff:
                    file_name = ff.split('/')[3]
                    print(ff, file_name)
                    urllib.request.urlretrieve(url_nhc[:-4] + ff, file_name)
                if 'TRACK_latest' in ff:
                    file_name = ff.split('/')[3]
                    print(ff, file_name)
                    urllib.request.urlretrieve(url_nhc[:-4] + ff, file_name)
                if 'best_track' in ff:
                    file_name = ff.split('/')[1]
                    print(ff, file_name)
                    urllib.request.urlretrieve(url_nhc + ff, file_name)


def get_cone_coordinates(kml_file):
    soup = BeautifulSoup(kml_file, 'html.parser')
    cone = dict(lon=np.array([]), lat=np.array([]))
    for i, s in enumerate(soup.find_all("coordinates")):
        coor = s.get_text('coordinates').split(',0')
        for st in coor[1:-1]:
            lon = float(st.split(',')[0])
            lat = float(st.split(',')[1])
            cone['lon'] = np.append(cone['lon'], lon)
            cone['lat'] = np.append(cone['lat'], lat)
    return cone


def get_track_coordinates(kml_file):
    soup = BeautifulSoup(kml_file, 'html.parser')
    track = dict(lon=np.array([]), lat=np.array([]))
    for i, s in enumerate(soup.find_all("point")):
        lon = float(s.get_text("coordinates").split('coordinates')[1].split(',')[0])
        lat = float(s.get_text("coordinates").split('coordinates')[1].split(',')[1])
        track['lon'] = np.append(track['lon'], lon)
        track['lat'] = np.append(track['lat'], lat)
    return track


def main(today):
    download_current_kmz(today)

    kmz_files = glob.glob('*.kmz')

    for f in kmz_files:
        os.system('cp ' + f + ' ' + f[:-3] + 'zip')
        os.system('unzip -o ' + f + ' -d ' + f[:-4])

    zip_files = glob.glob('*.zip')
    zip_files = [f for f in zip_files if np.logical_or('al' in f, 'AL' in f)]
    zip_files_track_latest = [f for f in zip_files if 'TRACK' in f]

    tracks = dict()
    for i, f in enumerate(zip_files_track_latest):
        name = f.split('_')[0]
        tracks[name] = dict()
        kmz = ZipFile(f, 'r')
        if 'TRACK' in f:
            kml_f = glob.glob(f[:-4]+'/*.kml')
            kml_track = kmz.open(kml_f[0].split('/')[1], 'r').read()

            # Get forecast track coordinates
            tracks[name]['forecast_track'] = get_track_coordinates(kml_track)

            # set forecast plotting options
            tracks[name]['forecast_track']['plt'] = dict(ls='-.', color='gold', lw=2, name='Forecast Track')

            # Get CONE coordinates
            zip_file_cone_latest = [fl for fl in zip_files if np.logical_and(f.split('_')[0][2:] in fl, 'CONE' in fl)][0]
            kmz = ZipFile(zip_file_cone_latest, 'r')
            kml_ff = glob.glob(zip_file_cone_latest[:-4]+'/*.kml')
            kml_cone_latest = kmz.open(kml_ff[0].split('/')[1], 'r').read()

            tracks[name]['forecast_cone'] = get_cone_coordinates(kml_cone_latest)

            # set cone plotting options
            tracks[name]['forecast_cone']['plt'] = dict(ls='-.', color='blue', lw=1, name='Forecast Cone')

            # Get best track coordinates
            zip_file_best_track = [fl for fl in zip_files if np.logical_and(f.split('_')[0][2:] in fl, 'best_track' in fl)][0]
            kmz = ZipFile(zip_file_best_track, 'r')
            kml_ff = glob.glob(zip_file_best_track[:-4]+'/*.kml')
            kml_best_track = kmz.open(kml_ff[0].split('/')[1], 'r').read()

            tracks[name]['best_track'] = get_track_coordinates(kml_best_track)

            # set best track plotting options
            tracks[name]['best_track']['plt'] = dict(ls=':', color='magenta', lw=3, name='Best Track')

    cleanup_dir()
    return tracks


if __name__ == '__main__':
    main(dt.date.today())