#!/usr/bin/env python

'''Simple CCSDS TDM file writer.

EISCAT UHF antenna coordinates:
05 SENTER1              7725445.727  664387.767   71.354+14.2 (pedestal foot alt + antenna height)
 
WGS84: 69.58649229 N 19.22592538 E, 71.354+14.2 m (pedestal foot alt + antenna height)
distance = d - 20.0 + 5.0 m [- subreflector round trip + elevation arm length] +/- 4 m

https://public.ccsds.org/Pubs/503x0b1c1.pdf
'''
import numpy as np
import matplotlib.pyplot as plt
import time
import datetime
import scipy.constants as consts

import os

os.environ['TZ'] = 'GMT'
time.tzset()

def date2unix(year, month, day, hour, minute, second):
    '''Convert date to unix time in seconds


    :param int year: Year as integer. Years preceding 1 A.D. should be 0 or negative. The year before 1 A.D. is 0, 10 B.C. is year -9.
    :param int month: Month as integer, Jan = 1, Feb. = 2, etc.
    :param int day:  Day
    :param int hour:  Hour in 24h format
    :param int minute:  Minute
    :param float second:  Second, may contain fractional part.
    :return: Unix time in seconds
    :rtype: float
    '''
    t = datetime.datetime(year, month, day, hour, minute, second)
    return(time.mktime(t.timetuple()))


def unix2date(unix):
    '''Convert unix time in seconds to UTC date datetime object

    :param float unix: Unix time in seconds.
    :return: Datetime object in UTC
    :rtype: datetime.datetime
    '''
    return datetime.datetime.utcfromtimestamp(unix)


def unix2datestr(unix):
    '''Convert unix time in seconds to Gregorian calendar UTC date-time formatted string
    
    **Uses:**
       * :func:`~ccsds_write.unix2date`

    :param float unix: Unix time in seconds.
    :return: Gregorian calendar UTC date-time formatted string
    :rtype: str
    '''
    return(unix2date(unix).strftime('%Y-%m-%dT%H:%M:%S'))


def unix2datestrf(x):
    '''Convert unix time in seconds to Gregorian calendar UTC date-time formatted string
    
    Different implementation?
    
    **Uses:**
       * :func:`~ccsds_write.unix2date`

    :param float unix: Unix time in seconds.
    :return: Gregorian calendar UTC date-time formatted string
    :rtype: str
    '''
    return("%s"%(unix2date(x).strftime('%Y-%m-%dT%H:%M:%S.%f')))


def write_oem(t,state,oid=42,fname="oems/state.oem"):
    '''Uses a series of unix-times and state vectors in ITRF2000 to create a CCSDS OEM file.

    **Uses:**
       * :func:`~ccsds_write.unix2datestrf`
       * :func:`~ccsds_write.unix2datestr`

    :param list/numpy.ndarray t: Vector of unix-times
    :param numpy.ndarray state: 6-D states given in SI units in the ITRF2000 frame. Rows correspond to different states and columns to dimensions.
    :param int OID: Object ID and name (written in OEM as the same but with different formating)
    :param str fname: Output file-path for OEM.
    '''
    fo=open(fname,"w")
    #print(t[0])
    fo.write("CCSDS_OEM_VERS = 2.0\n")
    fo.write("CREATION_DATE = %s\n"%(unix2datestr(t[0]))) # 1996-11-04T17:22:31
    fo.write("ORIGINATOR = SORTS\n")
    fo.write("META_START\n")
    fo.write("OBJECT_NAME = %s\n"%(oid))
    fo.write("OBJECT_ID = %d\n"%(oid))
    fo.write("CENTER_NAME = EARTH\n")
    fo.write("REF_FRAME = ITRF2000\n") # what is the difference between ECEF and ITRF
    fo.write("TIME_SYSTEM = UTC\n")
    fo.write("START_TIME = %s\n"%(unix2datestrf(t[0])))
    fo.write("USEABLE_START_TIME = %s\n"%(unix2datestrf(t[0])))
    fo.write("USEABLE_STOP_TIME = %s\n"%(unix2datestrf(t[-1])))
    fo.write("STOP_TIME = %s\n"%(unix2datestrf(t[-1])))
    fo.write("META_STOP\n")
    fo.write("COMMENT This file was produced by SORTS.\n")
    fo.write("COMMENT.\n")
    for ti in range(len(t)):
        #print(t[ti])
        fo.write("%s %1.3f %1.3f %1.3f %1.3f %1.3f %1.3f\n"%(unix2datestrf(t[ti]),state[ti,0],state[ti,1],state[ti,2],state[ti,3],state[ti,4],state[ti,5]))
    fo.close()


def read_oem(fname):
    meta = {'COMMENT': ''}

    _dtype = [
        ('date', 'datetime64[us]'),
        ('x', 'float64'),
        ('y', 'float64'),
        ('z', 'float64'),
        ('vx', 'float64'),
        ('vy', 'float64'),
        ('vz', 'float64'),
    ]

    raw_data = []
    DATA_ON = False
    META_ON = False
    with open(fname, 'r') as f:
        for line in f:

            if META_ON:
                if line.strip() == 'META_STOP':
                    META_ON = False
                    DATA_ON = True
                    continue

                _tmp = [x.strip() for x in line.split('=')]
                meta[_tmp[0]] = _tmp[1]
            elif DATA_ON:
                if line[:7] == 'COMMENT':
                    meta['COMMENT'] += line[7:]
                else:
                    raw_data.append(line.split(' '))
            else:
                if line.strip() == 'META_START':
                    META_ON = True
                    continue
                _tmp = [x.strip() for x in line.split('=')]
                meta[_tmp[0]] = _tmp[1]


    data_len = len(raw_data)

    data = np.empty((data_len, ), dtype=_dtype)

    for ind, row in enumerate(raw_data):
        rown = 0
        for col, dtype in _dtype:
            data[ind][col] = row[rown]
            rown += 1

    return data, meta



def write_ccsds(t_pulse,
                m_range,
                m_range_rate,
                m_range_std,
                m_range_rate_std,
                freq=230e6,
                tx_ecef=[0,0,0],
                rx_ecef=[0,0,0],
                tx="EISCAT UHF",
                rx="EISCAT UHF",
                oid="ERS-1",
                tdm_type="track",
                fname="track.tdm"):
    '''# TODO: Document function.
    '''
    fo=open(fname,"w")
    fo.write("CCSDS_TDM_VERS = 1.0\n")
    fo.write("   COMMENT MASTER ID %s\n"%(oid))
    fo.write("   COMMENT TX_ECEF (%1.12f,%1.12f,%1.12f)\n"%(tx_ecef[0],tx_ecef[1],tx_ecef[2]))
    fo.write("   COMMENT RX_ECEF (%1.12f,%1.12f,%1.12f)\n"%(rx_ecef[0],rx_ecef[1],rx_ecef[2]))
    fo.write("   COMMENT This is a simulated %s of MASTER ID %s with EISCAT 3D\n"%(tdm_type,oid))
    fo.write("   COMMENT 233 MHz, time of flight, with ionospheric corrections\n")
    fo.write("   COMMENT EISCAT 3D coordinates: \n")
    fo.write("   COMMENT Author(s): SORTS.\n")
    fo.write("   CREATION_DATE       = %s\n"%(unix2datestr(time.time())))
    fo.write("META_START\n")
    fo.write("   TIME_SYSTEM         = UTC\n")
    fo.write("   START_TIME          = %s\n"%(unix2datestrf(t_pulse[0])))
    fo.write("   STOP_TIME           = %s\n"%(unix2datestrf(t_pulse[-1])))
    fo.write("   PARTICIPANT_1       = %s\n"%(tx))
    fo.write("   PARTICIPANT_2       = %s\n"%(oid))
    fo.write("   PARTICIPANT_3       = %s\n"%(rx))
    fo.write("   MODE                = SEQUENTIAL\n")
    fo.write("   PATH                = 1,2,3\n")
    fo.write("   TRANSMIT_BAND       = %1.5f\n"%(freq))
    fo.write("   RECEIVE_BAND        = %1.5f\n"%(freq))
    fo.write("   TIMETAG_REF         = TRANSMIT\n")
    fo.write("   INTEGRATION_REF     = START\n")
    fo.write("   RANGE_MODE          = CONSTANT\n")
    fo.write("   RANGE_MODULUS       = %1.2f\n"%(128.0*20e-3))
    fo.write("   RANGE_UNITS         = KM\n")
    fo.write("   DATA_QUALITY        = VALIDATED\n")
    fo.write("   CORRECTION_RANGE    = 0.0\n")
    fo.write("   NOISE_DATA          = ON\n")
    fo.write("   CORRECTIONS_APPLIED = NO\n")
    fo.write("META_STOP\n")
    fo.write("DATA_START\n")
    for ri in range(len(t_pulse)):
        fo.write("   RANGE                   = %s %1.12f %1.12f\n"%(unix2datestrf(t_pulse[ri]),m_range[ri], m_range_std[ri]))
        fo.write("   DOPPLER_INSTANTANEOUS   = %s %1.12f %1.12f\n"%(unix2datestrf(t_pulse[ri]),m_range_rate[ri], m_range_rate_std[ri]))
    fo.write("DATA_STOP\n")
    fo.close()


def read_ccsds(fname):
    '''Just get the range data # TODO: the rest
    '''
    meta = {'COMMENT': ''}

    RANGE_UNITS = 'km'
    with open(fname, 'r') as f:
        DATA_ON = False
        META_ON = False
        data_raw = {}
        for line in f:
            if line.strip() == 'DATA_STOP':
                break

            if META_ON:
                tmp_lin = line.split('=')
                if len(tmp_lin) > 1:
                    meta[tmp_lin[0].strip()] = tmp_lin[1].strip()
                    if tmp_lin[0].strip() == 'RANGE_UNITS':
                        RANGE_UNITS = tmp_lin[1].strip().lower()
            elif DATA_ON:
                name, tmp_dat = line.split('=')

                name = name.strip().lower()
                tmp_dat = tmp_dat.strip().split(' ')

                if name in data_raw:
                    data_raw[name].append(tmp_dat)
                else:
                    data_raw[name] = [tmp_dat]
            else:
                if line.lstrip()[:7] == 'COMMENT':
                    meta['COMMENT'] += line.lstrip()[7:]
                else:
                    tmp_lin = line.split('=')
                    if len(tmp_lin) > 1:
                        meta[tmp_lin[0].strip()] = tmp_lin[1].strip()

            if line.strip() == 'META_START':
                META_ON = True
            if line.strip() == 'DATA_START':
                META_ON = False
                DATA_ON = True
    _dtype = [
        ('date', 'datetime64[us]'),
    ]

    data_len = len(data_raw[data_raw.keys()[0]])

    for name in data_raw:
        _dtype.append( (name, 'float64') )
        _dtype.append( (name + '_err', 'float64') )

    data = np.empty((data_len, ), dtype=_dtype)

    date_set = False
    for name, series in data_raw.items():
        for ind, val in enumerate(series):
            if not date_set:
                data[ind]['date'] = np.datetime64(val[0],'us')

            data[ind][name] = np.float64(val[1])
            if len(val) > 2:
                data[ind][name + '_err'] = np.float64(val[2])
            else:
                data[ind][name + '_err'] = 0.0

            if name == 'range':
                if RANGE_UNITS == 's':
                    data[ind][name] *= consts.c*1e-3

        date_set = True

    return data, meta


if __name__=='__main__':
    ccsds_file = './data/uhf_test_data/events/2002-009A-1473150428.tdm'
    data = read_ccsds(ccsds_file)
    print(data)