import time

from SpiffWorkflow.task import Task

cache_store = {}

import time

# first pass - meant to be down and dirty
def purge_cache(now):
    dellist = []
    for key in cache_store.keys():
        if cache_store[key]['timeout'] < now:
            dellist.append(key)
    for key in dellist:
        del cache_store[key]

def cache(f,timeout=60):
    """Cache the values for function for x minutes
       we still have work to do to make a optional kw argument
       to set the length of time to cache
    """
    def cached(*args, **kw):
        now = time.time()
        purge_cache(now)
        key =f.__name__+str(args)+str(kw)
        if key in cache_store.keys():
            return cache_store[key]['value']
        else:
            newtime = now+timeout*60
        result = f(*args, **kw)
        cache_store[key] ={}
        cache_store[key]['value'] = result
        cache_store[key]['timeout'] = newtime
        return result

    return cached