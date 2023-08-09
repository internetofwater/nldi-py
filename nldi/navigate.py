# =================================================================
#
# Author: Benjamin Webb <bwebb@lincolninst.edu>
#
# Copyright (c) 2023 Benjamin Webb
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# =================================================================

"""Module containing the models for NLDI Navigation"""

from enum import Enum
import logging
from sqlalchemy import text
from typing import Any

LOGGER = logging.getLogger(__name__)


class NavigationModes(str, Enum):
    DM = 'DM'
    DD = 'DD'
    UM = 'UM'
    UT = 'UT'
    PP = 'PP'


def navigate(nav_mode: str, comid: int, distance: float = None,
             coastal_fcode: int = None) -> Any:
    LOGGER.debug(f'Doing navigation for {comid} with mode {nav_mode}')
    if nav_mode == NavigationModes.DM:
        return navigate_dm(comid, distance, coastal_fcode)
    elif nav_mode == NavigationModes.DD:
        return navigate_dd(comid, distance, coastal_fcode)
    elif nav_mode == NavigationModes.UM:
        return navigate_um(comid, distance, coastal_fcode)
    elif nav_mode == NavigationModes.UT:
        return navigate_ut(comid, distance, coastal_fcode)


def navigate_dm(comid, distance=None, coastal_fcode=None):
    return text('''
        with
        recursive nav(comid, terminalpathid, dnhydroseq, fcode, stoplength)
            as (select comid, terminalpathid, dnhydroseq, fcode,
                pathlength + lengthkm - :distance as stoplength
            from nhdplus.plusflowlinevaa_np21
                where comid = :comid
            union all
            select x.comid, x.terminalpathid, x.dnhydroseq, x.fcode,
                    nav.stoplength
                from nhdplus.plusflowlinevaa_np21 x,
                    nav
                where x.hydroseq = nav.dnhydroseq
                    and x.terminalpathid = nav.terminalpathid
                    and x.fcode != :coastal_fcode
                    and x.pathlength + x.lengthkm >= nav.stoplength
            ) select comid from nav
        ''').bindparams(
        distance=distance,
        comid=comid,
        coastal_fcode=coastal_fcode
    )


def navigate_dd(comid, distance=None, coastal_fcode=None):
    return text('''
        with
        recursive nav(comid, dnhydroseq, dnminorhyd, fcode, stoplength,
                      terminalflag)
            as (select comid, dnhydroseq, dnminorhyd, fcode,
                pathlength + lengthkm - :distance stoplength, terminalflag
            from nhdplus.plusflowlinevaa_np21
                where comid = :comid
            union all
            select x.comid, x.dnhydroseq, x.dnminorhyd, x.fcode,
                    nav.stoplength, x.terminalflag
                from nhdplus.plusflowlinevaa_np21 x,
                    nav
                where (x.hydroseq = nav.dnhydroseq or
                    (nav.dnminorhyd != 0 and x.hydroseq = nav.dnminorhyd))
                    and x.fcode != :coastal_fcode
                    and nav.terminalflag != 1
                    and x.pathlength + x.lengthkm >= nav.stoplength
            ) select comid from nav
        ''').bindparams(
        distance=distance,
        comid=comid,
        coastal_fcode=coastal_fcode
    )


def navigate_um(comid, distance=0, coastal_fcode=None):
    return text('''
        with
        recursive nav(comid, levelpathid, uphydroseq, fcode, stoplength)
            as (select comid, levelpathid, uphydroseq, fcode,
                pathlength + :distance as stoplength
            from nhdplus.plusflowlinevaa_np21
                where comid = :comid
            union all
            select x.comid, x.levelpathid, x.uphydroseq, x.fcode,
                   nav.stoplength
                from nhdplus.plusflowlinevaa_np21 x,
                    nav
                where x.hydroseq = nav.uphydroseq
                    and x.levelpathid = nav.levelpathid
                    and x.fcode != :coastal_fcode
                    and x.pathlength + x.lengthkm >= nav.stoplength
                ) select comid from nav
        ''').bindparams(
        distance=distance,
        comid=comid,
        coastal_fcode=coastal_fcode
    )


def navigate_ut(comid, distance=0, coastal_fcode=None):
    return text('''
        with
        recursive nav(comid, hydroseq, startflag, fcode, stoplength)
                as (select comid, hydroseq, startflag, fcode,
                    pathlength + :distance as stoplength
                from nhdplus.plusflowlinevaa_np21
                    where comid = :comid
                union all
                select x.comid, x.hydroseq, x.startflag, x.fcode,
                       nav.stoplength
                    from nhdplus.plusflowlinevaa_np21 x,
                        nav
                    where nav.startflag != 1
                        and (x.dnhydroseq = nav.hydroseq
                        or (x.dnminorhyd != 0
                        and x.dnminorhyd = nav.hydroseq))
                        and x.fcode != :coastal_fcode
                        and x.pathlength <= nav.stoplength
                ) select comid from nav
        ''').bindparams(
        distance=distance,
        comid=comid,
        coastal_fcode=coastal_fcode
    )
