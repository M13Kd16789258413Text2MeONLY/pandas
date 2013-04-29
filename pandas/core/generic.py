# pylint: disable=W0231,E1101

import operator
import numpy as np

from pandas.core.index import MultiIndex
import pandas.core.indexing as indexing
from pandas.core.indexing import _maybe_convert_indices
from pandas.tseries.index import DatetimeIndex
from pandas.core.internals import BlockManager
from pandas.core.indexing import _NDFrameIndexer
import pandas.core.common as com
import pandas.lib as lib
from pandas.util import py3compat

class PandasError(Exception):
    pass


class PandasObject(object):

    #----------------------------------------------------------------------
    # Construction

    @property
    def _constructor(self):
        raise NotImplementedError

    @property
    def _constructor_sliced(self):
        raise NotImplementedError

    #----------------------------------------------------------------------
    # Axis

    @classmethod
    def _setup_axes(cls, axes, info_axis = None, stat_axis = None, aliases = None, slicers = None,
                    axes_are_reversed = False, build_axes = True):
        """ provide axes setup for the major PandasObjects

            axes : the names of the axes in order (lowest to highest)
            info_axis_num : the axis of the selector dimension (int)
            stat_axis_num : the number of axis for the default stats (int)
            aliases : other names for a single axis (dict)
            slicers : how axes slice to others (dict)
            axes_are_reversed : boolean whether to treat passed axes as reversed (DataFrame)
            build_axes : setup the axis properties (default True)
            """

        cls._AXIS_ORDERS  = axes
        cls._AXIS_NUMBERS = dict([(a, i) for i, a in enumerate(axes) ])
        cls._AXIS_LEN     = len(axes)
        cls._AXIS_ALIASES = aliases or dict()
        cls._AXIS_NAMES   = dict([(i, a) for i, a in enumerate(axes) ])
        cls._AXIS_SLICEMAP = slicers or None
        cls._AXIS_REVERSED = axes_are_reversed

        # indexing support
        cls._ix = None

        if info_axis is not None:
            cls._info_axis_number = info_axis
            cls._info_axis_name   = axes[info_axis]

        if stat_axis is not None:
            cls._stat_axis_number = stat_axis
            cls._stat_axis_name   = axes[stat_axis]

        # setup the actual axis
        if build_axes:
            if axes_are_reversed:
                m = cls._AXIS_LEN-1
                for i, a in cls._AXIS_NAMES.items():
                    setattr(cls,a,lib.AxisProperty(m-i))
            else:
                for i, a in cls._AXIS_NAMES.items():
                    setattr(cls,a,lib.AxisProperty(i))

    def _construct_axes_dict(self, axes=None, **kwargs):
        """ return an axes dictionary for myself """
        d = dict([(a, getattr(self, a)) for a in (axes or self._AXIS_ORDERS)])
        d.update(kwargs)
        return d

    @staticmethod
    def _construct_axes_dict_from(self, axes, **kwargs):
        """ return an axes dictionary for the passed axes """
        d = dict([(a, ax) for a, ax in zip(self._AXIS_ORDERS, axes)])
        d.update(kwargs)
        return d

    def _construct_axes_dict_for_slice(self, axes=None, **kwargs):
        """ return an axes dictionary for myself """
        d = dict([(self._AXIS_SLICEMAP[a], getattr(self, a))
                 for a in (axes or self._AXIS_ORDERS)])
        d.update(kwargs)
        return d

    @classmethod
    def _from_axes(cls, data, axes):
        # for construction from BlockManager
        if isinstance(data, BlockManager):
            return cls(data)
        else:
            if cls._AXIS_REVERSED:
                axes = axes[::-1]
            d = cls._construct_axes_dict_from(cls, axes, copy=False)
            return cls(data, **d)

    def _get_axis_number(self, axis):
        axis = self._AXIS_ALIASES.get(axis, axis)
        if com.is_integer(axis):
            if axis in self._AXIS_NAMES:
                return axis
        else:
            try:
                return self._AXIS_NUMBERS[axis]
            except:
                pass
        raise ValueError('No axis named %s' % axis)

    def _get_axis_name(self, axis):
        axis = self._AXIS_ALIASES.get(axis, axis)
        if isinstance(axis, basestring):
            if axis in self._AXIS_NUMBERS:
                return axis
        else:
            try:
                return self._AXIS_NAMES[axis]
            except:
                pass
        raise ValueError('No axis named %s' % axis)

    def _get_axis(self, axis):
        name = self._get_axis_name(axis)
        return getattr(self, name)

    @property
    def _info_axis(self):
        return getattr(self, self._info_axis_name)

    @property
    def _stat_axis(self):
        return getattr(self, self._stat_axis_name)

    #----------------------------------------------------------------------
    # Indexers
    @classmethod
    def _create_indexer(cls, name, indexer):
        """ create an indexer like _name in the class """
        iname = '_%s' % name
        setattr(cls,iname,None)

        def _indexer(self):
            if getattr(self,iname,None) is None:
                setattr(self,iname,indexer(self, name))
            return getattr(self,iname)

        setattr(cls,name,property(_indexer))

    #----------------------------------------------------------------------
    # Reconstruction

    def save(self, path):
        com.save(self, path)

    @classmethod
    def load(cls, path):
        return com.load(path)

    #----------------------------------------------------------------------
    # Comparisons

    def _indexed_same(self, other):
        return all([getattr(self, a).equals(getattr(other, a)) for a in self._AXIS_ORDERS])

    def reindex(self, *args, **kwds):
        raise NotImplementedError

    def __neg__(self):
        arr = operator.neg(self.values)
        return self._wrap_array(arr, self.axes, copy=False)

    def __invert__(self):
        arr = operator.inv(self.values)
        return self._wrap_array(arr, self.axes, copy=False)

    #----------------------------------------------------------------------
    # Iteration

    def __iter__(self):
        """
        Iterate over infor axis
        """
        return iter(self._info_axis)

    def keys(self):
        """ return the info axis names """
        return self._info_axis

    def iteritems(self):
        for h in self._info_axis:
            yield h, self[h]

    # Name that won't get automatically converted to items by 2to3. items is
    # already in use for the first axis.
    iterkv = iteritems

    def __len__(self):
        """Returns length of info axis """
        return len(self._info_axis)

    def __contains__(self, key):
        """True if the key is in the info axis """
        return key in self._info_axis

    @property
    def empty(self):
        return not all(len(getattr(self, a)) > 0 for a in self._AXIS_ORDERS)

    #----------------------------------------------------------------------
    # Formatting

    def __unicode__(self):
        raise NotImplementedError

    def __str__(self):
        """
        Return a string representation for a particular Object

        Invoked by str(df) in both py2/py3.
        Yields Bytestring in Py2, Unicode String in py3.
        """

        if py3compat.PY3:
            return self.__unicode__()
        return self.__bytes__()

    def __bytes__(self):
        """
        Return a string representation for a particular Object

        Invoked by bytes(df) in py3 only.
        Yields a bytestring in both py2/py3.
        """
        encoding = com.get_option("display.encoding")
        return self.__unicode__().encode(encoding, 'replace')

    def __repr__(self):
        """
        Return a string representation for a particular Object

        Yields Bytestring in Py2, Unicode String in py3.
        """
        return str(self)

    #----------------------------------------------------------------------
    # Methods

    def abs(self):
        """
        Return an object with absolute value taken. Only applicable to objects
        that are all numeric

        Returns
        -------
        abs: type of caller
        """
        return np.abs(self)

    def get(self, key, default=None):
        """
        Get item from object for given key (DataFrame column, Panel slice,
        etc.). Returns default value if not found

        Parameters
        ----------
        key : object

        Returns
        -------
        value : type of items contained in object
        """
        try:
            return self[key]
        except KeyError:
            return default

    def groupby(self, by=None, axis=0, level=None, as_index=True, sort=True,
                group_keys=True):
        """
        Group series using mapper (dict or key function, apply given function
        to group, return result as series) or by a series of columns

        Parameters
        ----------
        by : mapping function / list of functions, dict, Series, or tuple /
            list of column names.
            Called on each element of the object index to determine the groups.
            If a dict or Series is passed, the Series or dict VALUES will be
            used to determine the groups
        axis : int, default 0
        level : int, level name, or sequence of such, default None
            If the axis is a MultiIndex (hierarchical), group by a particular
            level or levels
        as_index : boolean, default True
            For aggregated output, return object with group labels as the
            index. Only relevant for DataFrame input. as_index=False is
            effectively "SQL-style" grouped output
        sort : boolean, default True
            Sort group keys. Get better performance by turning this off
        group_keys : boolean, default True
            When calling apply, add group keys to index to identify pieces

        Examples
        --------
        # DataFrame result
        >>> data.groupby(func, axis=0).mean()

        # DataFrame result
        >>> data.groupby(['col1', 'col2'])['col3'].mean()

        # DataFrame with hierarchical index
        >>> data.groupby(['col1', 'col2']).mean()

        Returns
        -------
        GroupBy object
        """
        from pandas.core.groupby import groupby
        axis = self._get_axis_number(axis)
        return groupby(self, by, axis=axis, level=level, as_index=as_index,
                       sort=sort, group_keys=group_keys)

    def asfreq(self, freq, method=None, how=None, normalize=False):
        """
        Convert all TimeSeries inside to specified frequency using DateOffset
        objects. Optionally provide fill method to pad/backfill missing values.

        Parameters
        ----------
        freq : DateOffset object, or string
        method : {'backfill', 'bfill', 'pad', 'ffill', None}
            Method to use for filling holes in reindexed Series
            pad / ffill: propagate last valid observation forward to next valid
            backfill / bfill: use NEXT valid observation to fill methdo
        how : {'start', 'end'}, default end
            For PeriodIndex only, see PeriodIndex.asfreq
        normalize : bool, default False
            Whether to reset output index to midnight

        Returns
        -------
        converted : type of caller
        """
        from pandas.tseries.resample import asfreq
        return asfreq(self, freq, method=method, how=how,
                      normalize=normalize)

    def at_time(self, time, asof=False):
        """
        Select values at particular time of day (e.g. 9:30AM)

        Parameters
        ----------
        time : datetime.time or string

        Returns
        -------
        values_at_time : type of caller
        """
        try:
            indexer = self.index.indexer_at_time(time, asof=asof)
            return self.take(indexer, convert=False)
        except AttributeError:
            raise TypeError('Index must be DatetimeIndex')

    def between_time(self, start_time, end_time, include_start=True,
                     include_end=True):
        """
        Select values between particular times of the day (e.g., 9:00-9:30 AM)

        Parameters
        ----------
        start_time : datetime.time or string
        end_time : datetime.time or string
        include_start : boolean, default True
        include_end : boolean, default True

        Returns
        -------
        values_between_time : type of caller
        """
        try:
            indexer = self.index.indexer_between_time(
                start_time, end_time, include_start=include_start,
                include_end=include_end)
            return self.take(indexer, convert=False)
        except AttributeError:
            raise TypeError('Index must be DatetimeIndex')

    def resample(self, rule, how=None, axis=0, fill_method=None,
                 closed=None, label=None, convention='start',
                 kind=None, loffset=None, limit=None, base=0):
        """
        Convenience method for frequency conversion and resampling of regular
        time-series data.

        Parameters
        ----------
        rule : the offset string or object representing target conversion
        how : string, method for down- or re-sampling, default to 'mean' for
              downsampling
        axis : int, optional, default 0
        fill_method : string, fill_method for upsampling, default None
        closed : {'right', 'left'}
            Which side of bin interval is closed
        label : {'right', 'left'}
            Which bin edge label to label bucket with
        convention : {'start', 'end', 's', 'e'}
        kind: "period"/"timestamp"
        loffset: timedelta
            Adjust the resampled time labels
        limit: int, default None
            Maximum size gap to when reindexing with fill_method
        base : int, default 0
            For frequencies that evenly subdivide 1 day, the "origin" of the
            aggregated intervals. For example, for '5min' frequency, base could
            range from 0 through 4. Defaults to 0
        """
        from pandas.tseries.resample import TimeGrouper
        axis = self._get_axis_number(axis)
        sampler = TimeGrouper(rule, label=label, closed=closed, how=how,
                              axis=axis, kind=kind, loffset=loffset,
                              fill_method=fill_method, convention=convention,
                              limit=limit, base=base)
        return sampler.resample(self)

    def first(self, offset):
        """
        Convenience method for subsetting initial periods of time series data
        based on a date offset

        Parameters
        ----------
        offset : string, DateOffset, dateutil.relativedelta

        Examples
        --------
        ts.last('10D') -> First 10 days

        Returns
        -------
        subset : type of caller
        """
        from pandas.tseries.frequencies import to_offset
        if not isinstance(self.index, DatetimeIndex):
            raise NotImplementedError

        if len(self.index) == 0:
            return self

        offset = to_offset(offset)
        end_date = end = self.index[0] + offset

        # Tick-like, e.g. 3 weeks
        if not offset.isAnchored() and hasattr(offset, '_inc'):
            if end_date in self.index:
                end = self.index.searchsorted(end_date, side='left')

        return self.ix[:end]

    def last(self, offset):
        """
        Convenience method for subsetting final periods of time series data
        based on a date offset

        Parameters
        ----------
        offset : string, DateOffset, dateutil.relativedelta

        Examples
        --------
        ts.last('5M') -> Last 5 months

        Returns
        -------
        subset : type of caller
        """
        from pandas.tseries.frequencies import to_offset
        if not isinstance(self.index, DatetimeIndex):
            raise NotImplementedError

        if len(self.index) == 0:
            return self

        offset = to_offset(offset)

        start_date = start = self.index[-1] - offset
        start = self.index.searchsorted(start_date, side='right')
        return self.ix[start:]

    def select(self, crit, axis=0):
        """
        Return data corresponding to axis labels matching criteria

        Parameters
        ----------
        crit : function
            To be called on each index (label). Should return True or False
        axis : int

        Returns
        -------
        selection : type of caller
        """
        axis_name = self._get_axis_name(axis)
        axis = self._get_axis(axis)

        if len(axis) > 0:
            new_axis = axis[np.asarray([bool(crit(label)) for label in axis])]
        else:
            new_axis = axis

        return self.reindex(**{axis_name: new_axis})

    def drop(self, labels, axis=0, level=None):
        """
        Return new object with labels in requested axis removed

        Parameters
        ----------
        labels : array-like
        axis : int
        level : int or name, default None
            For MultiIndex

        Returns
        -------
        dropped : type of caller
        """
        axis_name = self._get_axis_name(axis)
        axis, axis_ = self._get_axis(axis), axis

        if axis.is_unique:
            if level is not None:
                if not isinstance(axis, MultiIndex):
                    raise AssertionError('axis must be a MultiIndex')
                new_axis = axis.drop(labels, level=level)
            else:
                new_axis = axis.drop(labels)
            dropped = self.reindex(**{axis_name: new_axis})
            try:
                dropped.axes[axis_].names = axis.names
            except AttributeError:
                pass
            return dropped

        else:
            if level is not None:
                if not isinstance(axis, MultiIndex):
                    raise AssertionError('axis must be a MultiIndex')
                indexer = -lib.ismember(axis.get_level_values(level),
                                        set(labels))
            else:
                indexer = -axis.isin(labels)

            slicer = [slice(None)] * self.ndim
            slicer[self._get_axis_number(axis_name)] = indexer

            return self.ix[tuple(slicer)]

    def sort_index(self, axis=0, ascending=True):
        """
        Sort object by labels (along an axis)

        Parameters
        ----------
        axis : {0, 1}
            Sort index/rows versus columns
        ascending : boolean, default True
            Sort ascending vs. descending

        Returns
        -------
        sorted_obj : type of caller
        """
        axis = self._get_axis_number(axis)
        axis_name = self._get_axis_name(axis)
        labels = self._get_axis(axis)

        sort_index = labels.argsort()
        if not ascending:
            sort_index = sort_index[::-1]

        new_axis = labels.take(sort_index)
        return self.reindex(**{axis_name: new_axis})

    def tshift(self, periods=1, freq=None, **kwds):
        """
        Shift the time index, using the index's frequency if available

        Parameters
        ----------
        periods : int
            Number of periods to move, can be positive or negative
        freq : DateOffset, timedelta, or time rule string, default None
            Increment to use from datetools module or time rule (e.g. 'EOM')

        Notes
        -----
        If freq is not specified then tries to use the freq or inferred_freq
        attributes of the index. If neither of those attributes exist, a
        ValueError is thrown

        Returns
        -------
        shifted : Series
        """
        if freq is None:
            freq = getattr(self.index, 'freq', None)

        if freq is None:
            freq = getattr(self.index, 'inferred_freq', None)

        if freq is None:
            msg = 'Freq was not given and was not set in the index'
            raise ValueError(msg)

        return self.shift(periods, freq, **kwds)

    def pct_change(self, periods=1, fill_method='pad', limit=None, freq=None,
                   **kwds):
        """
        Percent change over given number of periods

        Parameters
        ----------
        periods : int, default 1
            Periods to shift for forming percent change
        fill_method : str, default 'pad'
            How to handle NAs before computing percent changes
        limit : int, default None
            The number of consecutive NAs to fill before stopping
        freq : DateOffset, timedelta, or offset alias string, optional
            Increment to use from time series API (e.g. 'M' or BDay())

        Returns
        -------
        chg : Series or DataFrame
        """
        if fill_method is None:
            data = self
        else:
            data = self.fillna(method=fill_method, limit=limit)
        rs = data / data.shift(periods=periods, freq=freq, **kwds) - 1
        if freq is None:
            mask = com.isnull(self.values)
            np.putmask(rs.values, mask, np.nan)
        return rs

    def to_hdf(self, path_or_buf, key, **kwargs):
        """ activate the HDFStore """
        from pandas.io import pytables
        return pytables.to_hdf(path_or_buf, key, self, **kwargs)

# install the indexerse
for _name, _indexer in indexing.get_indexers_list():
    PandasObject._create_indexer(_name,_indexer)

class NDFrame(PandasObject):
    """
    N-dimensional analogue of DataFrame. Store multi-dimensional in a
    size-mutable, labeled data structure

    Parameters
    ----------
    data : BlockManager
    axes : list
    copy : boolean, default False
    """

    def __init__(self, data, axes=None, copy=False, dtype=None):
        if dtype is not None:
            data = data.astype(dtype)
        elif copy:
            data = data.copy()

        if axes is not None:
            for i, ax in enumerate(axes):
                data = data.reindex_axis(ax, axis=i)

        object.__setattr__(self, '_data', data)
        object.__setattr__(self, '_item_cache', {})

    #----------------------------------------------------------------------
    # Axes

    @property
    def shape(self):
        return tuple(len(getattr(self, a)) for a in self._AXIS_ORDERS)

    @property
    def axes(self):
        """ we do it this way because if we have reversed axes, then 
        the block manager shows then reversed """
        return [getattr(self, a) for a in self._AXIS_ORDERS]

    @property
    def ndim(self):
        return self._data.ndim

    def _expand_axes(self, key):
        new_axes = []
        for k, ax in zip(key, self.axes):
            if k not in ax:
                if type(k) != ax.dtype.type:
                    ax = ax.astype('O')
                new_axes.append(ax.insert(len(ax), k))
            else:
                new_axes.append(ax)

        return new_axes

    def _set_axis(self, axis, labels):
        self._data.set_axis(axis, labels)
        self._clear_item_cache()

    def transpose(self, *args, **kwargs):
        """
        Permute the dimensions of the Object

        Parameters
        ----------
        axes : int or name (or alias)
        copy : boolean, default False
            Make a copy of the underlying data. Mixed-dtype data will
            always result in a copy

        Examples
        --------
        >>> p.transpose(2, 0, 1)
        >>> p.transpose(2, 0, 1, copy=True)

        Returns
        -------
        y : same as input
        """

        # construct the args
        args = list(args)
        for a in self._AXIS_ORDERS:
            if not a in kwargs:
                try:
                    kwargs[a] = args.pop(0)
                except (IndexError):
                    raise ValueError(
                        "not enough arguments specified to transpose!")

        axes = [self._get_axis_number(kwargs[a]) for a in self._AXIS_ORDERS]

        # we must have unique axes
        if len(axes) != len(set(axes)):
            raise ValueError('Must specify %s unique axes' % self._AXIS_LEN)

        new_axes = self._construct_axes_dict_from(
            self, [self._get_axis(x) for x in axes])
        new_values = self.values.transpose(tuple(axes))
        if kwargs.get('copy') or (len(args) and args[-1]):
            new_values = new_values.copy()
        return self._constructor(new_values, **new_axes)

    def swapaxes(self, axis1, axis2, copy=True):
        """
        Interchange axes and swap values axes appropriately

        Returns
        -------
        y : same as input
        """
        i = self._get_axis_number(axis1)
        j = self._get_axis_number(axis2)

        if i == j:
            if copy:
                return self.copy()
            return self

        mapping = {i: j, j: i}

        new_axes = (self._get_axis(mapping.get(k, k))
                    for k in range(self._AXIS_LEN))
        new_values = self.values.swapaxes(i, j)
        if copy:
            new_values = new_values.copy()

        return self._constructor(new_values, *new_axes)

    def pop(self, item):
        """
        Return item and drop from frame. Raise KeyError if not found.
        """
        result = self[item]
        del self[item]
        return result

    def squeeze(self):
        """ squeeze length 1 dimensions """
        try:
            return self.ix[tuple([ slice(None) if len(a) > 1 else a[0] for a in self.axes ])]
        except:
            return self

    def swaplevel(self, i, j, axis=0):
        """
        Swap levels i and j in a MultiIndex on a particular axis

        Parameters
        ----------
        i, j : int, string (can be mixed)
            Level of index to be swapped. Can pass level name as string.

        Returns
        -------
        swapped : type of caller (new object)
        """
        axis = self._get_axis_number(axis)
        result = self.copy()
        labels = result._data.axes[axis]
        result._data.set_axis(axis, labels.swaplevel(i, j))
        return result

    def rename_axis(self, mapper, axis=0, copy=True):
        """
        Alter index and / or columns using input function or functions.
        Function / dict values must be unique (1-to-1). Labels not contained in
        a dict / Series will be left as-is.

        Parameters
        ----------
        mapper : dict-like or function, optional
        axis : int, default 0
        copy : boolean, default True
            Also copy underlying data

        See also
        --------
        DataFrame.rename

        Returns
        -------
        renamed : type of caller
        """
        # should move this at some point
        from pandas.core.series import _get_rename_function

        mapper_f = _get_rename_function(mapper)

        if axis == 0:
            new_data = self._data.rename_items(mapper_f, copydata=copy)
        else:
            new_data = self._data.rename_axis(mapper_f, axis=axis)
            if copy:
                new_data = new_data.copy()

        return self._constructor(new_data)

    #----------------------------------------------------------------------
    # Array Interface

    def _wrap_array(self, arr, axes, copy=False):
        d = self._construct_axes_dict_from(self, axes, copy=copy)
        return self._constructor(arr, **d)

    def __array__(self, dtype=None):
        return self.values

    def __array_wrap__(self, result):
        d = self._construct_axes_dict(self._AXIS_ORDERS, copy=False)
        return self._constructor(result, **d)

    #----------------------------------------------------------------------
    # Fancy Indexing

    def __getitem__(self, item):
        return self._get_item_cache(item)

    def _get_item_cache(self, item):
        cache = self._item_cache
        try:
            return cache[item]
        except Exception:
            values = self._data.get(item)
            res = self._box_item_values(item, values)
            cache[item] = res
            return res

    def _box_item_values(self, key, values):
        raise NotImplementedError

    def _clear_item_cache(self):
        self._item_cache.clear()

    def _set_item(self, key, value):
        self._data.set(key, value)
        self._clear_item_cache()

    def __delitem__(self, key):
        """
        Delete item
        """
        deleted = False

        maybe_shortcut = False
        if hasattr(self, 'columns') and isinstance(self.columns, MultiIndex):
            try:
                maybe_shortcut = key not in self.columns._engine
            except TypeError:
                pass

        if maybe_shortcut:
            # Allow shorthand to delete all columns whose first len(key)
            # elements match key:
            if not isinstance(key, tuple):
                key = (key,)
            for col in self.columns:
                if isinstance(col, tuple) and col[:len(key)] == key:
                    del self[col]
                    deleted = True
        if not deleted:
            # If the above loop ran and didn't delete anything because
            # there was no match, this call should raise the appropriate
            # exception:
            self._data.delete(key)

        try:
            del self._item_cache[key]
        except KeyError:
            pass

    def get_dtype_counts(self):
        """ return the counts of dtypes in this frame """
        from pandas import Series
        return Series(self._data.get_dtype_counts())

    def _reindex_axis(self, new_index, fill_method, axis, copy):
        new_data = self._data.reindex_axis(new_index, axis=axis,
                                           method=fill_method, copy=copy)

        if new_data is self._data and not copy:
            return self
        else:
            return self._constructor(new_data)

    #----------------------------------------------------------------------
    # Consolidation of internals

    def _consolidate_inplace(self):
        self._clear_item_cache()
        self._data = self._data.consolidate()

    def consolidate(self, inplace=False):
        """
        Compute NDFrame with "consolidated" internals (data of each dtype
        grouped together in a single ndarray). Mainly an internal API function,
        but available here to the savvy user

        Parameters
        ----------
        inplace : boolean, default False
            If False return new object, otherwise modify existing object

        Returns
        -------
        consolidated : type of caller
        """
        if inplace:
            self._consolidate_inplace()
        else:
            cons_data = self._data.consolidate()
            if cons_data is self._data:
                cons_data = cons_data.copy()
            return self._constructor(cons_data)

    @property
    def _is_mixed_type(self):
        return self._data.is_mixed_type

    @property
    def _is_numeric_mixed_type(self):
        return self._data.is_numeric_mixed_type

    #----------------------------------------------------------------------
    # Methods

    def as_matrix(self):
        raise NotImplementedError

    @property
    def values(self):
        return self.as_matrix()

    @property
    def _get_values(self):
        # compat
        return self.values

    def as_blocks(self, columns=None):
        """
        Convert the frame to a dict of dtype -> Constructor Types that each has a homogeneous dtype.
        are presented in sorted order unless a specific list of columns is
        provided.

        NOTE: the dtypes of the blocks WILL BE PRESERVED HERE (unlike in as_matrix)

        Parameters
        ----------
        columns : array-like
            Specific column order

        Returns
        -------
        values : a list of Object
        """
        self._consolidate_inplace()

        bd = dict()
        for b in self._data.blocks:
            b = b.reindex_items_from(columns or b.items)
            bd[str(b.dtype)] = self._constructor(BlockManager([ b ], [ b.items, self.index ]))
        return bd

    @property
    def blocks(self):
        return self.as_blocks()

    def astype(self, dtype, copy = True, raise_on_error = True):
        """
        Cast object to input numpy.dtype
        Return a copy when copy = True (be really careful with this!)

        Parameters
        ----------
        dtype : numpy.dtype or Python type
        raise_on_error : raise on invalid input

        Returns
        -------
        casted : type of caller
        """

        mgr = self._data.astype(dtype, copy = copy, raise_on_error = raise_on_error)
        return self._constructor(mgr)

    def convert_objects(self, convert_dates=True, convert_numeric=True):
        """
        Attempt to infer better dtype for object columns
        Always returns a copy (even if no object columns)

        Parameters
        ----------
        convert_dates : if True, attempt to soft convert_dates, if 'coerce', force conversion (and non-convertibles get NaT)
        convert_numeric : if True attempt to coerce to numerbers (including strings), non-convertibles get NaN

        Returns
        -------
        converted : DataFrame
        """
        return self._constructor(self._data.convert(convert_dates=convert_dates, convert_numeric=convert_numeric))

    def cumsum(self, axis=None, skipna=True):
        """
        Return DataFrame of cumulative sums over requested axis.

        Parameters
        ----------
        axis : {0, 1}
            0 for row-wise, 1 for column-wise
        skipna : boolean, default True
            Exclude NA/null values. If an entire row/column is NA, the result
            will be NA

        Returns
        -------
        y : DataFrame
        """
        if axis is None:
            axis = self._stat_axis_number
        else:
            axis = self._get_axis_number(axis)

        y = self.values.copy()
        if not issubclass(y.dtype.type, np.integer):
            mask = np.isnan(self.values)

            if skipna:
                np.putmask(y, mask, 0.)

            result = y.cumsum(axis)

            if skipna:
                np.putmask(result, mask, np.nan)
        else:
            result = y.cumsum(axis)
        return self._wrap_array(result, self.axes, copy=False)

    def cumprod(self, axis=None, skipna=True):
        """
        Return cumulative product over requested axis as DataFrame

        Parameters
        ----------
        axis : {0, 1}
            0 for row-wise, 1 for column-wise
        skipna : boolean, default True
            Exclude NA/null values. If an entire row/column is NA, the result
            will be NA

        Returns
        -------
        y : DataFrame
        """
        if axis is None:
            axis = self._stat_axis_number
        else:
            axis = self._get_axis_number(axis)

        y = self.values.copy()
        if not issubclass(y.dtype.type, np.integer):
            mask = np.isnan(self.values)

            if skipna:
                np.putmask(y, mask, 1.)
            result = y.cumprod(axis)

            if skipna:
                np.putmask(result, mask, np.nan)
        else:
            result = y.cumprod(axis)
        return self._wrap_array(result, self.axes, copy=False)

    def cummax(self, axis=None, skipna=True):
        """
        Return DataFrame of cumulative max over requested axis.

        Parameters
        ----------
        axis : {0, 1}
            0 for row-wise, 1 for column-wise
        skipna : boolean, default True
            Exclude NA/null values. If an entire row/column is NA, the result
            will be NA

        Returns
        -------
        y : DataFrame
        """
        if axis is None:
            axis = self._stat_axis_number
        else:
            axis = self._get_axis_number(axis)

        y = self.values.copy()
        if not issubclass(y.dtype.type, np.integer):
            mask = np.isnan(self.values)

            if skipna:
                np.putmask(y, mask, -np.inf)

            result = np.maximum.accumulate(y, axis)

            if skipna:
                np.putmask(result, mask, np.nan)
        else:
            result = np.maximum.accumulate(y, axis)
        return self._wrap_array(result, self.axes, copy=False)

    def cummin(self, axis=None, skipna=True):
        """
        Return DataFrame of cumulative min over requested axis.

        Parameters
        ----------
        axis : {0, 1}
            0 for row-wise, 1 for column-wise
        skipna : boolean, default True
            Exclude NA/null values. If an entire row/column is NA, the result
            will be NA

        Returns
        -------
        y : DataFrame
        """
        if axis is None:
            axis = self._stat_axis_number
        else:
            axis = self._get_axis_number(axis)

        y = self.values.copy()
        if not issubclass(y.dtype.type, np.integer):
            mask = np.isnan(self.values)

            if skipna:
                np.putmask(y, mask, np.inf)

            result = np.minimum.accumulate(y, axis)

            if skipna:
                np.putmask(result, mask, np.nan)
        else:
            result = np.minimum.accumulate(y, axis)
        return self._wrap_array(result, self.axes, copy=False)

    def copy(self, deep=True):
        """
        Make a copy of this object

        Parameters
        ----------
        deep : boolean, default True
            Make a deep copy, i.e. also copy data

        Returns
        -------
        copy : type of caller
        """
        data = self._data
        if deep:
            data = data.copy()
        return self._constructor(data)

    def add_prefix(self, prefix):
        """
        Concatenate prefix string with panel items names.

        Parameters
        ----------
        prefix : string

        Returns
        -------
        with_prefix : type of caller
        """
        new_data = self._data.add_prefix(prefix)
        return self._constructor(new_data)

    def add_suffix(self, suffix):
        """
        Concatenate suffix string with panel items names

        Parameters
        ----------
        suffix : string

        Returns
        -------
        with_suffix : type of caller
        """
        new_data = self._data.add_suffix(suffix)
        return self._constructor(new_data)

    def take(self, indices, axis=0, convert=True):
        """
        Analogous to ndarray.take

        Parameters
        ----------
        indices : list / array of ints
        axis : int, default 0
        convert : translate neg to pos indices (default)

        Returns
        -------
        taken : type of caller
        """

        # check/convert indicies here
        if convert:
            axis = self._get_axis_number(axis)
            indices = _maybe_convert_indices(indices, len(self._get_axis(axis)))

        if axis == 0:
            labels = self._get_axis(axis)
            new_items = labels.take(indices)
            new_data = self._data.reindex_axis(new_items, axis=0)
        else:
            new_data = self._data.take(indices, axis=axis, verify=False)
        return self._constructor(new_data)

    def tz_convert(self, tz, axis=0, copy=True):
        """
        Convert TimeSeries to target time zone. If it is time zone naive, it
        will be localized to the passed time zone.

        Parameters
        ----------
        tz : string or pytz.timezone object
        copy : boolean, default True
            Also make a copy of the underlying data

        Returns
        -------
        """
        axis = self._get_axis_number(axis)
        ax = self._get_axis(axis)

        if not hasattr(ax, 'tz_convert'):
            ax_name = self._get_axis_name(axis)
            raise TypeError('%s is not a valid DatetimeIndex or PeriodIndex' %
                            ax_name)

        new_data = self._data
        if copy:
            new_data = new_data.copy()

        new_obj = self._constructor(new_data)
        new_ax = ax.tz_convert(tz)

        if axis == 0:
            new_obj._set_axis(1, new_ax)
        elif axis == 1:
            new_obj._set_axis(0, new_ax)
            self._clear_item_cache()

        return new_obj

    def tz_localize(self, tz, axis=0, copy=True):
        """
        Localize tz-naive TimeSeries to target time zone

        Parameters
        ----------
        tz : string or pytz.timezone object
        copy : boolean, default True
            Also make a copy of the underlying data

        Returns
        -------
        """
        axis = self._get_axis_number(axis)
        ax = self._get_axis(axis)

        if not hasattr(ax, 'tz_localize'):
            ax_name = self._get_axis_name(axis)
            raise TypeError('%s is not a valid DatetimeIndex or PeriodIndex' %
                            ax_name)

        new_data = self._data
        if copy:
            new_data = new_data.copy()

        new_obj = self._constructor(new_data)
        new_ax = ax.tz_localize(tz)

        if axis == 0:
            new_obj._set_axis(1, new_ax)
        elif axis == 1:
            new_obj._set_axis(0, new_ax)
            self._clear_item_cache()

        return new_obj

# Good for either Series or DataFrame


def truncate(self, before=None, after=None, copy=True):
    """Function truncate a sorted DataFrame / Series before and/or after
    some particular dates.

    Parameters
    ----------
    before : date
        Truncate before date
    after : date
        Truncate after date
	copy : boolean, default True

    Returns
    -------
    truncated : type of caller
    """
    from pandas.tseries.tools import to_datetime
    before = to_datetime(before)
    after = to_datetime(after)

    if before is not None and after is not None:
        if before > after:
            raise AssertionError('Truncate: %s must be after %s' %
                                 (before, after))

    result = self.ix[before:after]

    if isinstance(self.index, MultiIndex):
        result.index = self.index.truncate(before, after)

    if copy:
        result = result.copy()

    return result
