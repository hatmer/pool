from gevent.lock import BoundedSemaphore

class State:
    def __init__(self):
        self.block_headers = set()
        #self.recent_txns = []
        self.height = 0
        self.addrs = set()
        
        self.height_lock = BoundedSemaphore()
        self.header_lock = BoundedSemaphore()
        self.addr_lock = BoundedSemaphore()
       # self.txns_lock = BoundedSemaphore()






