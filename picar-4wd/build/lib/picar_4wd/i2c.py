from smbus2 import SMBus
from .utils import soft_reset
import time

class I2C(object):
    MASTER = 0
    SLAVE  = 1
    RETRY = 5

    def __init__(self, *args, **kargs):    
        self._bus = 1
        self._smbus = SMBus(self._bus)

    def auto_reset(func):
        """Decorator to automatically reset the I2C bus on errors.

        The previous implementation only attempted the failing operation once
        after resetting the controller.  In practice the I2C bus can require a
        few retries before recovering, so here we try up to ``RETRY`` times
        before giving up.  Each failure triggers a soft reset and the bus is
        reinitialised.  The name of the function that failed is printed to aid
        debugging.
        """

        def wrapper(self, *args, **kw):
            last_exc = None
            for _ in range(self.RETRY):
                try:
                    return func(self, *args, **kw)
                except OSError as e:
                    last_exc = e
                    print(
                        f"I/O error in {func.__name__}: {e}, resetting I2C bus"
                    )
                    soft_reset()
                    try:
                        self._smbus.close()
                    except Exception:
                        pass
                    self._smbus = SMBus(self._bus)
                    time.sleep(0.05)
            # If all retries failed, re-raise the last exception
            raise last_exc

        return wrapper

    @auto_reset
    def _i2c_write_byte(self, addr, data):   
        # self._debug("_i2c_write_byte: [0x{:02X}] [0x{:02X}]".format(addr, data))
        return self._smbus.write_byte(addr, data)
    
    @auto_reset
    def _i2c_write_byte_data(self, addr, reg, data):
        # self._debug("_i2c_write_byte_data: [0x{:02X}] [0x{:02X}] [0x{:02X}]".format(addr, reg, data))
        return self._smbus.write_byte_data(addr, reg, data)
    
    @auto_reset
    def _i2c_write_word_data(self, addr, reg, data):
        # self._debug("_i2c_write_word_data: [0x{:02X}] [0x{:02X}] [0x{:04X}]".format(addr, reg, data))
        return self._smbus.write_word_data(addr, reg, data)
    
    @auto_reset
    def _i2c_write_i2c_block_data(self, addr, reg, data):
        # self._debug("_i2c_write_i2c_block_data: [0x{:02X}] [0x{:02X}] {}".format(addr, reg, data))
        return self._smbus.write_i2c_block_data(addr, reg, data)
    
    @auto_reset
    def _i2c_read_byte(self, addr):  
        # self._debug("_i2c_read_byte: [0x{:02X}]".format(addr))
        return self._smbus.read_byte(addr)

    @auto_reset
    def _i2c_read_i2c_block_data(self, addr, reg, num):
        # self._debug("_i2c_read_i2c_block_data: [0x{:02X}] [0x{:02X}] [{}]".format(addr, reg, num))
        return self._smbus.read_i2c_block_data(addr, reg, num)

    def is_ready(self, addr):
        addresses = self.scan()
        if addr in addresses:
            return True
        else:
            return False

    def scan(self):                            
        cmd = "i2cdetect -y %s" % self._bus
        _, output = self.run_command(cmd)          
        outputs = output.split('\n')[1:]       
       # self._debug("outputs")
        addresses = []
        for tmp_addresses in outputs:
            tmp_addresses = tmp_addresses.split(':')[1]
            tmp_addresses = tmp_addresses.strip().split(' ')    
            for address in tmp_addresses:
                if address != '--':
                    addresses.append(address)
     #   self._debug("Conneceted i2c device: %s"%addresses)                   
        return addresses

    def send(self, send, addr, timeout=0):                     
        if isinstance(send, bytearray):
            data_all = list(send)
        elif isinstance(send, int):
            data_all = []
            d = "{:X}".format(send)
            d = "{}{}".format("0" if len(d)%2 == 1 else "", d)  
            # print(d)
            for i in range(len(d)-2, -1, -2):      
                tmp = int(d[i:i+2], 16)             
                # print(tmp)
                data_all.append(tmp)                
            data_all.reverse()
        elif isinstance(send, list):
            data_all = send
        else:
            raise ValueError("send data must be int, list, or bytearray, not {}".format(type(send)))

        if len(data_all) == 1:                      
            data = data_all[0]
            self._i2c_write_byte(addr, data)
        elif len(data_all) == 2:                    
            reg = data_all[0]
            data = data_all[1]
            self._i2c_write_byte_data(addr, reg, data)
        elif len(data_all) == 3:                    
            reg = data_all[0]
            data = (data_all[2] << 8) + data_all[1]
            self._i2c_write_word_data(addr, reg, data)
        else:
            reg = data_all[0]
            data = list(data_all[1:])
            self._i2c_write_i2c_block_data(addr, reg, data)

    def recv(self, recv, addr=0x00, timeout=0):     
        if isinstance(recv, int):                   
            result = bytearray(recv)
        elif isinstance(recv, bytearray):
            result = recv
        else:
            return False
        for i in range(len(result)):
            result[i] = self._i2c_read_byte(addr)
        return result

    def mem_write(self, data, addr, memaddr, timeout=5000, addr_size=8): #memaddr match to chn
        if isinstance(data, bytearray):
            data_all = list(data)
        elif isinstance(data, int):
            data_all = []
            for i in range(0, 100):
                d = data >> (8*i) & 0xFF
                if d == 0:
                    break
                else:
                    data_all.append(d)
            data_all.reverse()
        self._i2c_write_i2c_block_data(addr, memaddr, data_all)
    
    def mem_read(self, data, addr, memaddr, timeout=5000, addr_size=8):     
        if isinstance(data, int):
            num = data
        elif isinstance(data, bytearray):
            num = len(data)
        else:
            return False
        result = bytearray(num)
        result = self._i2c_read_i2c_block_data(addr, memaddr, num)
        return result

    def test():
        a_list = [0x2d,0x64,0x0]
        b = I2C()
        b.send(a_list,0x14)