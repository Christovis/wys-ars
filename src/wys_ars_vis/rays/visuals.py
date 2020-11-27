from typing import Dict, List, Optional, Tuple, Type, Union

import pandas as pd
import numpy as np
from scipy import stats

import pylab
from pylab import cm
import matplotlib as mpl
from matplotlib import colors
import matplotlib.pyplot as plt
from matplotlib.pyplot import figure
from matplotlib.lines import Line2D
from colour import Color

from wys_ars.rays.dipole_finder import Dipoles
from wys_ars.rays.skys import SkyArray


def _get_velocity_field(df: pd.DataFrame, npix: int) -> tuple:
    """
    2D binning of velocity field
    """
    x_bin_edges = np.linspace(0, 20, npix)
    y_bin_edges = np.linspace(0, 20, npix)

    # Velocity
    velx_field = stats.binned_statistic_2d(
        df["x_deg"].values,
        df["y_deg"].values,
        df["x_vel"].values*df["m200"].values,
        'sum',
        bins=[x_bin_edges, y_bin_edges],
    )
    vely_field = stats.binned_statistic_2d(
        df["x_deg"].values,
        df["y_deg"].values,
        df["y_vel"].values*df["m200"].values,
        'sum',
        bins=[x_bin_edges, y_bin_edges],
    )

    x_bin_center = (velx_field.x_edge[:-1] + vely_field.x_edge[1:]) / 2
    y_bin_center = (velx_field.y_edge[:-1] + vely_field.y_edge[1:]) / 2

    indx_x, indx_y = np.nonzero(vely_field.statistic)
    coord_x = np.array([x_bin_center[indx] for indx in indx_x])
    coord_y = np.array([y_bin_center[indx] for indx in indx_y])
    vel_x = velx_field.statistic[indx_x, indx_y]
    vel_y = vely_field.statistic[indx_x, indx_y]
    return coord_x, coord_y, vel_x, vel_y


def maps_with_vel_field(
    halos: pd.DataFrame,
    filepaths_map: str,
    box_nrs: List[int],
    snap_nrs: List[int],
    redshifts: List[float],
    theta: float = 20.,
    npix: int = 40,
) -> mpl.figure.Figure:
    """
    Plot sky-data contained in filepaths_map overlayed by halo-data
    in halos
    """
    fig, axis = plt.subplots(
        1, len(redshifts),
        figsize=(16, 5),
        sharex=True, sharey=True,
        facecolor="w", edgecolor="k",
    )
    fig.subplots_adjust(hspace=0.05, wspace=0.05)

    for idx, ax in enumerate(axis.reshape(-1)):
        # Load Map
        skyarray = SkyArray.from_file(
            filepaths_map[idx],
            opening_angle=theta,
            quantity="isw_rs",
            dir_in=None,
            convert_unit=True,
        )
        skyarray.data["orig"] *= 1e6
        # Select halos
        halos_sel = halos[
            (halos["box_nr"] == box_nrs[idx]) & (halos["ray_nr"] == snap_nrs[idx])
        ]
        # get velocity field
        coord_x, coord_y, vel_x, vel_y = _get_velocity_field(halos_sel, npix)
       
        mi = np.min(skyarray.data["orig"]) * 0.9
        ma = np.max(skyarray.data["orig"]) * 0.9
        divnorm = colors.DivergingNorm(vmin=mi, vcenter=0.0, vmax=ma)

        if idx == 0:
            bkg = ax.imshow(
                skyarray.data["orig"],
                extent=[
                    0,
                    skyarray.opening_angle,
                    0,
                    skyarray.opening_angle,
                ],
                cmap=cm.RdBu_r,
                norm=divnorm,
                origin="lower",
                zorder=0,
            )
            
        else:
            ax.imshow(
                skyarray.data["orig"],
                extent=[
                    0,
                    skyarray.opening_angle,
                    0,
                    skyarray.opening_angle,
                ],
                cmap=cm.RdBu_r,
                norm=divnorm,
                origin="lower",
                zorder=0,
            )

        ax.quiver(
            coord_x, coord_y,
            vel_x, vel_y,
            zorder=1,
        )
        ax.text(
            skyarray.opening_angle/10, skyarray.opening_angle/10,
            "z=%.2f" % redshifts[idx],
            color='black', 
            bbox=dict(
                facecolor='w',
                edgecolor='w',
                alpha=0.8,
                boxstyle='round,pad=0.5',
            ),
        )
        ax.set_xlabel(r"$\theta_1$ [deg]", size=14)
        ax.set_xticks(ax.get_xticks())
        ax.set_yticks(ax.get_yticks()[::2])
    
    axis[0].set_ylabel(r"$\theta_2$ [deg]", size=14)
    axcolor = fig.add_axes([0.92,0.22,0.009,0.6])
    cbar = fig.colorbar(bkg, cax=axcolor, pad=0.1)
    cbar.set_label(r'$\Delta T_{\rm ISW} \quad [\mu {\rm K}]$')
    return fig


def dipole_maps(
    dipole_index: List[int],
    dipoles: pd.DataFrame,
    filepath_map: str,
    extent: float,
    theta: float = 20.,
) -> mpl.figure.Figure:
    """
    Plot sky-data contained in filepaths_map overlayed by halo-data
    in halos
    """
    fig, axis = plt.subplots(
        1, len(dipole_index),
        figsize=(16, 5),
        facecolor="w", edgecolor="k",
    )
    
    # Load Map
    skyarray = SkyArray.from_file(
        filepath_map,
        opening_angle=theta,
        quantity="isw_rs",
        dir_in=None,
        convert_unit=True,
    )

    for idx, ax in enumerate(axis.reshape(-1)):
        dip = dipoles[dipoles["index"] == dipole_index[idx]]
        zoom = Dipoles.get_dipole_image(
            skyarray,
            (dip.x_pix.values[0], dip.y_pix.values[0]),
            dip.r200_pix.values[0] * extent,
            dip.r200_deg.values[0] * extent,
        )
        ax.imshow(
            zoom.data["orig"] * 1e6,
            extent=[
                dip.x_deg.values[0] - dip.r200_deg.values[0]*extent,
                dip.x_deg.values[0] + dip.r200_deg.values[0]*extent,
                dip.y_deg.values[0] - dip.r200_deg.values[0]*extent,
                dip.y_deg.values[0] + dip.r200_deg.values[0]*extent,
            ],
            cmap=cm.RdBu_r,
            origin="lower",
            zorder=0,
        )
        ax.text(
            dip.x_deg.values[0] - dip.r200_deg.values[0]*extent*0.9,
            dip.y_deg.values[0] - dip.r200_deg.values[0]*extent*0.9,
            "dip.idx = %.2f" % dipole_index[idx],
            color='black', 
            bbox=dict(
                facecolor='w',
                edgecolor='w',
                alpha=0.8,
                boxstyle='round,pad=0.5',
            ),
        )
    return fig
