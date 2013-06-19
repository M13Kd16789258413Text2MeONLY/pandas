import unittest
import nose
from datetime import datetime

import pandas as pd
import pandas.io.data as web
from pandas.util.testing import (network, assert_series_equal)
from numpy.testing.decorators import slow
import numpy as np

import urllib2


class TestGoogle(unittest.TestCase):

    @network
    def test_google(self):
        # asserts that google is minimally working and that it throws
        # an excecption when DataReader can't get a 200 response from
        # google
        start = datetime(2010, 1, 1)
        end = datetime(2013, 01, 27)

        try:
            self.assertEquals(
                web.DataReader("F", 'google', start, end)['Close'][-1],
                13.68)
        except urllib2.URLError:
            try:
                urllib2.urlopen('http://www.google.com')
            except urllib2.URLError:
                raise nose.SkipTest
            else:
                raise

    @network
    def test_google_non_existent(self):
        # asserts that google is minimally working and that it throws
        # an excecption when DataReader can't get a 200 response from
        # google
        start = datetime(2010, 1, 1)
        end = datetime(2013, 01, 27)

        try:
            self.assertRaises(
                Exception,
                lambda: web.DataReader("NON EXISTENT TICKER", 'google',
                                      start, end))
        except urllib2.URLError:
            try:
                urllib2.urlopen('http://www.google.com')
            except urllib2.URLError:
                raise nose.SkipTest
            else:
                raise


    @network
    def test_get_quote(self):
        self.assertRaises(NotImplementedError,
                lambda: web.get_quote_google(pd.Series(['GOOG', 'AAPL', 'GOOG'])))

    @network
    def test_get_goog_volume(self):
        try:
            df = web.get_data_google('GOOG')
            assert df.Volume.ix['OCT-08-2010'] == 2863473
        except IOError:
            try:
                urllib2.urlopen('http://www.google.com')
            except IOError:
                raise nose.SkipTest
            else:
                raise

    @network
    def test_get_multi1(self):
        try:
            sl = ['AAPL', 'AMZN', 'GOOG']
            pan = web.get_data_google(sl, '2012')
            ts = pan.Close.GOOG.index[pan.Close.AAPL > pan.Close.GOOG]
            assert ts[0].dayofyear == 96
        except IOError:
            try:
                urllib2.urlopen('http://www.google.com')
            except IOError:
                raise nose.SkipTest
            else:
                raise

    @network
    def test_get_multi2(self):
        try:
            pan = web.get_data_google(['GE', 'MSFT', 'INTC'], 'JAN-01-12', 'JAN-31-12')
            expected = [19.02, 28.23, 25.39]
            result = pan.Close.ix['01-18-12'][['GE', 'MSFT', 'INTC']].tolist()
            assert result == expected

            # sanity checking
            t= np.array(result)
            assert     np.issubdtype(t.dtype, np.floating)
            assert     t.shape == (3,)

            expected = [[ 18.99,  28.4 ,  25.18],
                        [ 18.58,  28.31,  25.13],
                        [ 19.03,  28.16,  25.52],
                        [ 18.81,  28.82,  25.87]]
            result = pan.Open.ix['Jan-15-12':'Jan-20-12'][['GE', 'MSFT', 'INTC']].values
            assert (result == expected).all()

            # sanity checking
            t= np.array(pan)
            assert     np.issubdtype(t.dtype, np.floating)
        except IOError:
            try:
                urllib2.urlopen('http://www.google.com')
            except IOError:
                raise nose.SkipTest
            else:
                raise

if __name__ == '__main__':
    nose.runmodule(argv=[__file__, '-vvs', '-x', '--pdb', '--pdb-failure'],
                   exit=False)