import sys

from tqdm import tqdm

from .threaded_queue import ThreadedQueue, DEFAULT_THREADS
from .lib import STRING_TYPES

DEFAULT_THREADS = 20

def schedule_threaded_jobs(
    fns, concurrency=DEFAULT_THREADS, 
    progress=None, total=None, batch_size=1
  ):
  
  if total is None:
    try:
      total = len(fns)
    except TypeError: # generators don't have len
      pass
  
  desc = progress if isinstance(progress, STRING_TYPES) else None

  pbar = tqdm(total=total, desc=desc, disable=(not progress))
  results = []
  
  def updatefn(fn):
    def realupdatefn(iface):
      ct = fn()
      pbar.update(ct)
      results.append(ct) # cPython list append is thread safe
    return realupdatefn

  with ThreadedQueue(n_threads=concurrency) as tq:
    for fn in fns:
      tq.put(updatefn(fn))

  return results

def schedule_green_jobs(
    fns, concurrency=DEFAULT_THREADS, 
    progress=None, total=None, batch_size=1
  ):
  import gevent.pool

  if total is None:
    try:
      total = len(fns)
    except TypeError: # generators don't have len
      pass

  desc = progress if isinstance(progress, STRING_TYPES) else None

  pbar = tqdm(total=total, desc=desc, disable=(not progress))
  results = []
  
  def updatefn(fn):
    def realupdatefn():
      res = fn()
      pbar.update(batch_size)
      results.append(res)
    return realupdatefn

  pool = gevent.pool.Pool(concurrency)
  for fn in fns:
    pool.spawn( updatefn(fn) )

  pool.join()
  pool.kill()
  pbar.close()

  return results

def schedule_jobs(
    fns, concurrency=DEFAULT_THREADS, 
    progress=None, total=None, green=False,
    batch_size=1
  ):
  """
  Given a list of functions, execute them concurrently until
  all complete. 

  fns: iterable of functions
  concurrency: number of threads
  progress: Falsey (no progress), String: Progress + description
  total: If fns is a generator, this is the number of items to be generated.
  green: If True, use green threads.

  Return: list of results
  """
  if concurrency < 0:
    raise ValueError("concurrency value cannot be negative: {}".format(concurrency))
  elif concurrency == 0 or total == 1:
    return [ fn() for fn in tqdm(fns, disable=(not progress or total == 1), desc=progress) ]

  if green:
    return schedule_green_jobs(fns, concurrency, progress, total, batch_size)

  return schedule_threaded_jobs(fns, concurrency, progress, total, batch_size)


