# Optimizing Pandas Performance - Memory

In the [previous post](TODO) we discussed how you can make Pandas code run faster. In this blog post we'll see how you can reduce its memory footprint.

Before you begin, the easiest way is ... to get a machine with more memory. This sounds obvious but most people tend to ignore it. You can lease a machine with several *terabytes* of memory from most of the big cloud providers. Tell me your data doesn't fit in a couple of terabytes of memory!

The reason we'd like to reduce Pandas memory footprint is to be able to stay in the single machine boundary. Moving to processing data on multiple machines is a long and painful project.

### Measuring Memory

Measuring memory in Python, where everything is a reference, can be tricky. Pandas makes life easier for use with the `memory_usage` method.

Let's load part of the [NYC Taxi Dataset](https://www1.nyc.gov/site/tlc/about/tlc-trip-record-data.page) and see.

**Listing 1: Measuring Memory**

```
In [1]: from pathlib import Path
In [2]: csv_file = 'taxi-01-2020-sample.csv.xz'
In [3]: mb = 1<<20
In [4]: Path(csv_file).stat().st_size / mb
Out[4]: 11.03564453125
In [5]: import pandas as pd
In [6]: df = pd.read_csv(csv_file)
In [7]: df.memory_usage(deep=True)/mb
Out[7]:
Index                     0.000122
VendorID                  7.629395
tpep_pickup_datetime     72.479248
tpep_dropoff_datetime    72.479248
passenger_count           7.629395
trip_distance             7.629395
RatecodeID                7.629395
store_and_fwd_flag       55.313110
PULocationID              7.629395
DOLocationID              7.629395
payment_type              7.629395
fare_amount               7.629395
extra                     7.629395
mta_tax                   7.629395
tip_amount                7.629395
tolls_amount              7.629395
improvement_surcharge     7.629395
total_amount              7.629395
congestion_surcharge      7.629395
In [8]: df.memory_usage(deep=True).sum()/mb
Out[8]: 314.712646484375
```

Listing 1 shows how to measure memory using `memory_usage`.

* `[1]-[4]` We find the size on disk in megabytes
* `[6]` We load the data from the CSV file into a `DataFrame`
* `[7]` We use `memory_usage` to see how much each row 
* `[8]` We measure the total memory consumed

We went from 11MB compressed on disk to 314MB in memory!

### Load Only the Data You Need

It seems trivial, but you should load only the data you need. Let's say we'd like to measure the average daily revenue. We need only the `tpep_pickup_datetime` and the `total_amount` columns.

**Listing 2: Load 2 Columns**

```
In [1]: import pandas as pd
In [2]: df = pd.read_csv(csv_file, usecols=['tpep_pickup_datetime', 'total_amount'])
In [3]: df.memory_usage(deep=True).sum()/mb
Out[3]: 
80.1087646484375
```

Listing 2 shows how to load only the columns we need.

* `[2]` We use the `usecols` argument to specify the columns we're interested in
* `[3]` We can see we're down to 7.6MB

### Use the Right Types

We'd like to calculate how many rides we have per `VendorID`, we need to load only this column.

**Listing 3: Loading VendorID**

```
In [1]: import pandas as pd
In [2]: df = pd.read_csv(csv_file, usecols=['VendorID'])
In [2]: df.memory_usage(deep=True).sum()/mb
Out[2]: 7.6295166015625
```

Listing 3 shows the memory consumed by loading the `VendorID` column.

However we can look at how many distinct values we have in `VendorID`:

**Listing 4: Distinct Values**

```
In [3]: df['VendorID'].unique()
Out[3]: array([2, 1])
```

Listing 4 shows we have only two small distinct values, we can reduce memory by using a smaller data type.

**Listing 5: Using `int8` Data Type**

```
In [4]: df = pd.read_csv(csv_file, usecols=['VendorID'], dtype={'VendorID': 'int8'})
In [5]: df.memory_usage(deep=True).sum()/mb
Out[5]: 0.95379638671875
```

Listing 5 shows the memory consumption when loading the `VendorID` as `int8` dtype. We went down to 0.9MB from the original 7.6MB.

Pandas also has a [categorial](https://pandas.pydata.org/pandas-docs/stable/user_guide/categorical.html) data type that can help reduce memory in string data that repeats itself a lot.

### Iterative Calculations

Sometimes you don't need to load the whole data at once to run a calculation. Say you'd like to calculate revenue by `VendorID`. You can iterate over the data in chunks, every time calculating the revenue per `VendorID` and update a global counter.

**Listing 6: Iterating Over Data**

```
In [1]: import pandas as pd
In [2]: from collections import Counter
In [3]: dfs = pd.read_csv(csv_file, usecols=['VendorID', 'total_amount'], chunksize=10_000)
In [4]: revenue = Counter()
In [5]: for df in dfs:
    ...:     by_vendor = df.groupby('VendorID')['total_amount'].sum()
    ...:     revenue.update(by_vendor.to_dict())
    ...: 
In [6]: revenue
Out[6]: Counter({1: 5978392.140000124, 2: 12491742.88000057})
```

Listing 6 shows how to iterate over the data in chunks.

* `[3]` We use the `chunksize` argument to get an iterator over parts of data
* `[4]` We create a global revenue counter
* `[5]` We iterate over the chunks, calculating revenue per vendor and updating the global `revenue` counter

### Conclusion

Pandas has several utilities that can reduce memory consumption significantly. This will allow you to stay in a single machine, which in turn will simplify your data analysis workflow.

If you want to learn more, you can have a look at the [Enhancing Performance](https://pandas.pydata.org/pandas-docs/stable/user_guide/enhancingperf.html) section of the pandas documentation. You can also check out my [Faster Pandas](https://www.linkedin.com/learning/faster-pandas/) online course which has more tips & tricks.
