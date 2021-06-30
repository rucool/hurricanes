#! /usr/bin/env python3

"""
Author: Mike Smith
Last modified: Lori Garzio on 6/30/2021
Create surface maps of RTOFS temperature and salinity for each model forecast for today, overlaid with current storm
forecast tracks released today.
"""
import cartopy.crs as ccrs
import xarray as xr
import pandas as pd
import os
import datetime as dt
import numpy as np
from glob import glob
from src.storms import get_argo_data, forecast_storm_region
from src.storms_plt import surface_map_storm_forecast
from current_storms import current_forecast_track
import src.gliders as gld
pd.set_option('display.width', 320, "display.max_columns", 10)  # for display in pycharm console


# url = '/Users/garzio/Documents/rucool/hurricane_glider_project/RTOFS/RTOFS_6hourly_North_Atlantic/'
url = '/home/hurricaneadm/data/rtofs'  # on server
# save_dir = '/Users/garzio/Documents/rucool/hurricane_glider_project/current_storm_tracks'
save_dir = '/www/home/lgarzio/public_html/hurricane_gliders/current_storm_tracks'  # in server
#bathymetry = '/Users/garzio/Documents/rucool/hurricane_glider_project/bathymetry/GEBCO_2014_2D_-100.0_0.0_-10.0_50.0.nc'
bathymetry = False
map_projection = ccrs.PlateCarree()
argo = True
gliders = True
dpi = 150
search_time = 48  # number of hours to search previous to today's date for gliders/argo

today = dt.date.today()
sdir = os.path.join(save_dir, today.strftime('%Y%m%d'))

t0 = today - dt.timedelta(hours=search_time)
t1 = today + dt.timedelta(hours=24)

# initialize keyword arguments for map plot
kwargs = dict()
kwargs['model'] = 'rtofs'
kwargs['transform'] = map_projection
kwargs['dpi'] = dpi

if bathymetry:
    bathy = xr.open_dataset(bathymetry)
else:
    bathy = False

# get forecast tracks for today
forecast_tracks = current_forecast_track.main(today, save_dir)

if forecast_tracks:
    # get RTOFS files for today
    rtofs_files = glob(os.path.join(url, today.strftime('rtofs.%Y%m%d'), '*.nc'))

    # get RTOFS files for 0Z
    md = (today - dt.timedelta(days=1)).strftime('rtofs.%Y%m%d')
    rtofs_files.insert(0, os.path.join(url, md, 'rtofs_glo_3dz_f024_6hrly_hvr_US_east.nc'))

    for tracks in forecast_tracks.items():
        sdir_track = os.path.join(sdir, tracks[0])
        os.makedirs(sdir_track, exist_ok=True)
        kwargs['save_dir'] = sdir_track
        kwargs['forecast'] = tracks
        stm_region = forecast_storm_region(tracks[1]['forecast_track'])

        if len(stm_region) < 1:
            raise ValueError('No region found for storm: {}'.format(tracks[0]))

        # Loop through regions
        for region in stm_region.items():
            extent = region[1]['lonlat']
            if bathy:
                kwargs['bathy'] = bathy.sel(lon=slice(extent[0] - 1, extent[1] + 1),
                                            lat=slice(extent[2] - 1, extent[3] + 1))

            if argo:
                argo_data = get_argo_data(extent, t0, t1)
                if len(argo_data) > 0:
                    kwargs['argo'] = argo_data

                    argo_df = pd.DataFrame(argo_data)
                    argo_df.sort_values('time', inplace=True)
                    argo_savename = '{}_{}_argo_{}-{}.csv'.format(tracks[0], region[1]['code'],
                                                                  t0.strftime('%Y%m%d'), t1.strftime('%Y%m%d'))
                    argo_df.to_csv(os.path.join(sdir_track, argo_savename), index=False)
                else:
                    kwargs['argo'] = False

            if gliders:
                current_gliders = gld.glider_data(extent, t0, t1)
                if len(current_gliders) > 0:
                    kwargs['gliders'] = current_gliders
                    gl_savename = '{}_{}_gliders_{}-{}.csv'.format(tracks[0], region[1]['code'],
                                                                   t0.strftime('%Y%m%d'), t1.strftime('%Y%m%d'))
                    gld.glider_summary(current_gliders, os.path.join(sdir_track, gl_savename))
                else:
                    kwargs['gliders'] = False

            for f in rtofs_files:
                print(f)
                try:
                    with xr.open_dataset(f) as ds:
                        ds = ds.rename({'Longitude': 'lon', 'Latitude': 'lat', 'MT': 'time', 'Depth': 'depth'})
                        lat = ds.lat.data
                        lon = ds.lon.data

                        # subset the RTOFS grid
                        lonIndex = np.round(np.interp(extent[:2], lon[0, :], np.arange(0, len(lon[0, :])))).astype(int)
                        latIndex = np.round(np.interp(extent[2:], lat[:, 0], np.arange(0, len(lat[:, 0])))).astype(int)
                        sub = ds.sel(X=slice(lonIndex[0], lonIndex[1]), Y=slice(latIndex[0], latIndex[1]))
                        surface_map_storm_forecast(sub, region, **kwargs)
                except OSError:
                    continue
