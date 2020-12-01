# Optimizing Pandas Performance - CPU

[Pandas](https://pandas.pydata.org/) is a great library. Pandas is built for performance, it's written mostly in [Cython](https://cython.org/) and uses the highly optimized [numpy](https://numpy.org/) library. However like every project, you need to know how to use Pandas properly to get the best performance.

### Before You Start

The computer industry has an unhealthy obsession with speed. Modern computer are *fast*, and most of the time Pandas performance will be good enough out of the box. You should always prefer simple, well designed code to faster code. Chances are that you're the one who will maintain it for a while, so be kind to your future self.

The main question is: What is "good enough" performance? You need to get hard numbers from the product team, the operations team or anyone else who has a saying in the matter. Don't accept "make it as fast as you can" answers - demand numbers such as "a request should return under 50 milliseconds" or "processing should not consume more than 100MB of memory".

_Note: It's also important to note that you won't hit your performance goals every time. The network will get congested, disk will slow down, computer will be loaded more than usual. A better performance goal is "a request should return under 50 milliseconds 99.99% of the time". Adding 9s (e.g. moving from 99.99% to 99.999%) is very hard and might require infrastructure changes._

Once you have your performance goal, measure your code and see if it matches then. If it does - don't spend any time optimizing it. Go fix a bug or add a feature, they have actual business value.

Also, be ready with a good test suite. Every time you optimize you create tricky code that requires extra testing to mediate the extra risk.

### Measuring Speed

I prefer to use IPython's [`%timeit`](https://ipython.readthedocs.io/en/stable/interactive/magics.html#magic-timeit) magic over using the built-in [timeit](https://docs.python.org/3/library/timeit.html) directly.

Your company is implementing a [Vickrey auction](https://en.wikipedia.org/wiki/Vickrey_auction) and you need to write a function that finds the second highest value in a sequence of non-negative values. You're debating between two options - running a "for loop" or sorting.

**Listing 1: Two options for "second"**

```
1 def second_for(values):
2     first, second = -1, -1
3     for val in values:
4         if val > first:
5             first, second = val, first
6         elif val > second:
7             second = val
8     return second
9 
10 
11 def second_sort(values):
12     values = sorted(values)
13     return values[-2]
```

Listing 1 shows the two options for implementing `second`. On line 1 we have the option that uses a `for` loop and on line 11 we have the option the user sorting.

Let's load the code to IPython and measure:

**Listing 2: Using %timeit magic**

```
In [1]: from random import random
In [2]: nums = [random() * 100 for _ in range(1000)]
In [3]: %run second.py
In [4]: %timeit second_for(nums)
36.6 µs ± 111 ns per loop (mean ± std. dev. of 7 runs, 10000 loops each)
In [5]: %timeit second_sort(nums)
84.7 µs ± 77.6 ns per loop (mean ± std. dev. of 7 runs, 10000 loops each)
```

Listing 2 shows an IPython session for measuring code performance with `%timeit` magic.

* `[1] & [2]` we create a random sample of 1000 values
* `[3]` we use the [`%run`](https://ipython.readthedocs.io/en/stable/interactive/magics.html#magic-run) magic to load the code
* `[4]` We measure the performance of `second_for`
* `[5]` We measure the performance of `second_sort`

The "for loop" version of `second` is faster.

_Note: It's important to run benchmarks on data that is close to possible to the real data. If a typical auction has only 10 entries - use a list of 10 numbers._

Apart from the `%timeit` magic there are several other tools you can use:

* [`%prun`](https://ipython.readthedocs.io/en/stable/interactive/magics.html#magic-prun) magic will run code under profiler
* The third-party [line_profiler](https://github.com/pyutils/line_profiler) can generate line-by-line profiling information. When installed it adds a `%lprun` magic to IPython

### Avoid Row Iteration

Pandas store its data in columns, which means that iteration by row is slow.

For example, let's count how many rows in our `logs.db` database that contains HTTP server logs have return value indicating an error.

**Listing 3: Counting HTTP Errors**

```
In [1]: import sqlite3
In [2]: import pandas as pd
In [3]: conn = sqlite3.connect('logs.db', detect_types=sqlite3.PARSE_DECLTYPES)
In [4]: df = pd.read_sql('SELECT * FROM logs', conn)
In [5]: %%timeit
   ...: total = 0
   ...: for _, row in df.iterrows():
   ...:     if row['status_code'] >= 400:
   ...:         total += 1
   ...: 
754 ms ± 3.42 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)
In [6]: %timeit len(df[df['status_code'] >= 400])
342 µs ± 2.9 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)
```

Listing 3 shows the performance of row iteration vs boolean indexing.

* `[1]-[4]` We load the logs data from the `logs.db` SQLite database
* `[5]` We use the `%%timeit` cell magic command to measure row iteration
* `[6]` We use the `%timeit` line magic to measure boolean indexing

Note that the row iteration result is in milliseconds while the boolean indexing is in microseconds. The row iteration code is about 2200 times slower than the boolean indexing one.

### Building DataFrames

Pandas `DataFrame` build for querying and reshaping. DataFrames are not databases and adding rows is a very slow operation.

Say you have HTTP logs in a plain text file.

**Listing 4: Example Log Lines**

```
in24.inetnebr.com - - [01/Aug/1995:00:00:01 -0400] "GET /shuttle/missions/sts-68/news/sts-68-mcc-05.txt HTTP/1.0" 200 1839
uplherc.upl.com - - [01/Aug/1995:00:00:07 -0400] "GET / HTTP/1.0" 304 0
uplherc.upl.com - - [01/Aug/1995:00:00:08 -0400] "GET /images/ksclogo-medium.gif HTTP/1.0" 304 0
uplherc.upl.com - - [01/Aug/1995:00:00:08 -0400] "GET /images/MOSAIC-logosmall.gif HTTP/1.0" 304 0
uplherc.upl.com - - [01/Aug/1995:00:00:08 -0400] "GET /images/USA-logosmall.gif HTTP/1.0" 304 0
```

Listing 4 show example log lines.

You have a `parse_log` function that parses a log line into a dict called `parse_log`. Let's measure how much time it takes to create a DataFrame row by row.

**Listing 5: Creating a DataFrame Row by Row**

```
In [1]: import lzma
In [2]: with lzma.open('log.txt.xz', 'rt') as fp:
   ...:     lines = list(fp)
   ...: 
In [3]: %run parse_log.py
In [4]: %%timeit
   ...: df = pd.DataFrame()
   ...: for line in lines:
   ...:     df = df.append(parse_line(line), ignore_index=True)
   ...: 
2.45 s ± 9.7 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)
In [5]: %timeit df = pd.DataFrame.from_records(parse_line(line) for line in lines)
14.8 ms ± 116 µs per loop (mean ± std. dev. of 7 runs, 100 loops each)
```

Listing 5 compares two approaches of creating a `DataFrame` row by row.

* `[1]-[2]` We load lines into memory. We do that to get consistent measurement that does not depend on disk IO
* `[3]` We load the code to parse a log line
* `[4]` We measure the time it takes to construct a `DataFrame` using the `append` method
* `[5]` We measure the time it takes to construct a `DataFrame` using the `from_records` method

Again, not the units of measurement, the `append` code is about 165 times slower than the `from_records` one.

### Using [query](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.query.html)

Usually we select rows using [boolean indexing](https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html). In big DataFrames and complex queries using the `DataFrame.query` method might give you a performance boost. `query` uses [numexpr](https://numexpr.readthedocs.io/), make sure it's installed before you try this code.

**Listing 6: Using `query`**

```
In [1]: import sqlite3
In [2]: conn = sqlite3.connect('logs.db', detect_types=sqlite3.PARSE_DECLTYPES)
In [3]: import pandas as pd
In [4]: df = pd.read_sql('SELECT * FROM logs', conn)
In [5]: df = pd.concat([df]*1000)
In [6]: f'{len(df):,}'
Out[6]: '10,000,000'
In [7]: %timeit df[(df['method'] == 'GET') & (df['status_code'] >= 400)]
471 ms ± 3.1 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)
In [8]: %timeit df.query('method == "GET" & status_code >= 400')
265 ms ± 1.44 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)
```

Listing 6 shows how `query` can improve performance.

* `[1]-[4]` We load data from the logs database into a DataFrame
* `[5]-[6]` We make the DataFrame 1000 times bigger to a total of 10,000,000 rows
* `[7]` We measure the performance of boolean indexing
* `[8]` We measure the performance of `query`

`query` comes out about twice as fast.

### Using ufuncs

Pandas & numpy built-in functions (called `ufuncs` for "universal functions") tend to be much faster than their equivalent Python built-in functions.

**Listing 7: ufuncs Performance**

```
In [1]: import pandas as pd
In [2]: s = pd.Series(range(10_000))
In [3]: %timeit max(s)
727 µs ± 4.21 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)
In [4]: %timeit s.max()
22.3 µs ± 89 ns per loop (mean ± std. dev. of 7 runs, 10000 loops each)
In [5]: %timeit s.values.max()
8.59 µs ± 22.8 ns per loop (mean ± std. dev. of 7 runs, 100000 loops each)
```

Listing 7 shows the performance of Pandas and numpy's `ufunc`s over Python's built-ins.

* `[1]-[2]` We create a series of 10,000 numbers
* `[3]` We measure the performance of Python's built in `max`
* `[3]` We measure the performance of Pandas `Series.max`
* `[4]` We measure the performance of numpy's `ndarray.max`

You can see that numpy is faster than Pandas which is faster than Python. The `values` attribute of a pandas `Series` exposes the underlying numpy array.

### Conclusion

There are many ways you can make Pandas faster. You need to learn the tools Pandas provide and also what to avoid when working with Pandas.

If you want to learn more, you can have a look at the [Enhancing Performance](https://pandas.pydata.org/pandas-docs/stable/user_guide/enhancingperf.html) section of the pandas documentation. You can also try out my [Faster Pandas](https://www.linkedin.com/learning/faster-pandas/) online course.
