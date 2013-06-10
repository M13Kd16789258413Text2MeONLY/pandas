from vbench.api import Benchmark
from datetime import datetime

start_date = datetime(2013, 5, 1)

common_setup = """from pandas_vb_common import *
import os
import pandas as pd
from pandas.core import common as com

f = '__test__.msg'
def remove(f):
   try:
       os.remove(f)
   except:
       pass

index = date_range('20000101',periods=250000,freq='H')
df = DataFrame({'float1' : randn(250000),
                'float2' : randn(250000)},
               index=index)
"""

#----------------------------------------------------------------------
# read a msgpack

setup1 = common_setup + """
remove(f)
pd.to_msgpack(f,df)
"""

packers_read_msgpack = Benchmark("pd.read_msgpack(f)", setup1, 
                          start_date=start_date)


#----------------------------------------------------------------------
# write to a msgpack

setup2 = common_setup + """
remove(f)
"""

packers_write_msgpack = Benchmark(
    "pd.to_msgpack(f,df)", setup2, cleanup="remove(f)",
    start_date=start_date)

#----------------------------------------------------------------------
# read a hdfstore

setup1 = common_setup + """
remove(f)
df.to_hdf(f,'df')
"""

packers_read_hdf_store = Benchmark("pd.read_hdf(f,'df')", setup1, 
                          start_date=start_date)


#----------------------------------------------------------------------
# write to a hdfstore

setup2 = common_setup + """
remove(f)
"""

packers_write_hdf_store = Benchmark(
    "df.to_hdf(f,'df')", setup2, cleanup="remove(f)",
    start_date=start_date)

#----------------------------------------------------------------------
# read a hdfstore table

setup1 = common_setup + """
remove(f)
df.to_hdf(f,'df',table=True)
"""

packers_read_hdf_table = Benchmark("pd.read_hdf(f,'df')", setup1, 
                          start_date=start_date)


#----------------------------------------------------------------------
# write to a hdfstore table

setup2 = common_setup + """
remove(f)
"""

packers_write_hdf_table = Benchmark(
    "df.to_hdf(f,'df',table=True)", setup2, cleanup="remove(f)",
    start_date=start_date)

#----------------------------------------------------------------------
# read a csv

setup1 = common_setup + """
remove(f)
df.to_csv(f)
"""

packers_read_csv = Benchmark("pd.read_csv(f,index_col=0)", setup1, 
                       start_date=start_date)


#----------------------------------------------------------------------
# write to a csv

setup2 = common_setup + """
remove(f)
"""

packers_write_csv = Benchmark(
    "df.to_csv(f)", setup2, cleanup="remove(f)",
    start_date=start_date)

#----------------------------------------------------------------------
# read a pickle

setup1 = common_setup + """
remove(f)
df.save(f)
"""

packers_read_pickle = Benchmark("com.load(f)", setup1, 
                       start_date=start_date)


#----------------------------------------------------------------------
# write to a pickle

setup2 = common_setup + """
remove(f)
"""

packers_write_pickle = Benchmark(
    "df.save(f)", setup2, cleanup="remove(f)",
    start_date=start_date)
